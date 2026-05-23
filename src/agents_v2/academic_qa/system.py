"""
学术QA系统 - Academic QA System

集成所有学术QA模块的统一系统。
提供完整的问答能力，包括：
- 多跳推理
- 引用溯源
- 幻觉检测
- 置信度校准
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


@dataclass
class AcademicQAConfig:
    """学术QA系统配置"""
    # LLM 配置
    llm: Optional[Any] = None

    # 检索配置
    vector_store: Optional[Any] = None
    bm25_index: Optional[Any] = None
    embedding_model: Optional[Any] = None

    # 检索参数
    top_k: int = 20
    rerank_top_k: int = 5
    vector_weight: float = 0.7
    keyword_weight: float = 0.3

    # 生成参数
    temperature: float = 0.3
    max_tokens: int = 2000

    # 严格性配置
    enable_crag: bool = True
    enable_self_rag: bool = True
    enable_hallucination_detection: bool = True
    enable_confidence_calibration: bool = True

    # 多跳配置
    enable_multi_hop: bool = True
    max_sub_questions: int = 5

    # 引用配置
    citation_style: str = "gb7714"  # "gb7714", "apa", "plain"
    max_citations: int = 10


@dataclass
class AcademicQAResult:
    """学术QA系统结果"""
    answer: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    hallucination_score: float = 0.0
    hallucination_risk: str = "unknown"
    reasoning_chain: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 评估指标
    ragas_metrics: Optional[Dict[str, float]] = None

    # 错误信息
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": self.citations,
            "confidence": self.confidence,
            "hallucination_score": self.hallucination_score,
            "hallucination_risk": self.hallucination_risk,
            "reasoning_chain": self.reasoning_chain,
            "metadata": self.metadata,
            "ragas_metrics": self.ragas_metrics,
            "errors": self.errors,
        }


class AcademicQASystem:
    """学术QA系统 - 整合所有模块的统一系统

    使用方式:
    ```python
    system = AcademicQASystem(config=AcademicQAConfig(llm=llm))
    result = await system.ask("问题", documents=[...])
    ```
    """

    def __init__(self, config: Optional[AcademicQAConfig] = None):
        """初始化学术QA系统

        Args:
            config: 系统配置
        """
        self.config = config or AcademicQAConfig()
        self._init_components()

    def _init_components(self):
        """初始化所有组件"""
        from ..academic_qa import (
            DocumentParser, AcademicChunker, HybridRetriever, CitationTracker,
            AnswerGenerator, CRAGEvaluator, SelfRAGController,
            HallucinationDetector, ConfidenceCalibrator,
            QueryDecomposer, MultiHopReasoner, RAGAsEvaluator, AnswerAggregator,
        )

        # 文档处理组件（如果提供了文档）
        self.doc_parser = DocumentParser()
        self.chunker = AcademicChunker(
            chunk_size=512,
            chunk_overlap=100,
            split_by="semantic"
        )

        # 检索器
        self.retriever = HybridRetriever(
            vector_store=self.config.vector_store,
            bm25_index=self.config.bm25_index,
            embedding_model=self.config.embedding_model,
            vector_weight=self.config.vector_weight,
            keyword_weight=self.config.keyword_weight,
        )

        # 引用溯源
        self.citation_tracker = CitationTracker(
            style=self.config.citation_style,
            max_citations=self.config.max_citations,
        )

        # 答案生成
        self.answer_generator = AnswerGenerator(
            llm=self.config.llm,
            max_context_docs=self.config.rerank_top_k,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # CRAG 评估器
        self.crag = CRAGEvaluator(
            llm=self.config.llm,
        )

        # Self-RAG 控制器
        self.self_rag = SelfRAGController(
            llm=self.config.llm,
            retriever=self._async_retriever,
        )

        # 幻觉检测器
        self.hallucination_detector = HallucinationDetector(
            llm=self.config.llm,
            num_samples=5,
        )

        # 置信度校准器
        self.confidence_calibrator = ConfidenceCalibrator(
            llm=self.config.llm,
        )

        # 多跳推理组件
        if self.config.enable_multi_hop:
            self.query_decomposer = QueryDecomposer(
                llm=self.config.llm,
                max_sub_questions=self.config.max_sub_questions,
            )
            self.multi_hop_reasoner = MultiHopReasoner(
                llm=self.config.llm,
                retriever=self._async_retriever,
            )
            self.answer_aggregator = AnswerAggregator(
                llm=self.config.llm,
            )

        # RAGAs 评估器
        self.ragas_evaluator = RAGAsEvaluator(
            llm=self.config.llm,
        )

        logger.info("AcademicQASystem initialized")

    async def _async_retriever(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """异步检索器包装

        将同步/异步检索器统一为异步接口。
        """
        if self.retriever:
            results = await self.retriever.retrieve(query, top_k=top_k, rerank=True)
            return [
                {
                    "content": r.content,
                    "chunk_id": r.chunk_id,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in results
            ]
        return []

    async def ask(
        self,
        query: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        contexts: Optional[List[str]] = None,
        mode: str = "strict",
    ) -> AcademicQAResult:
        """执行学术问答

        Args:
            query: 用户问题
            documents: 可选，文档列表（将用于检索）
            contexts: 可选，直接提供的上下文
            mode: 模式 - "strict"（严格）/ "balanced"（平衡）/ "fast"（快速）

        Returns:
            AcademicQAResult: 问答结果
        """
        errors = []
        reasoning_chain = []
        citations = []
        confidence = 0.0
        hallucination_score = 0.0
        hallucination_risk = "unknown"

        try:
            # 1. 确定是否是多跳问题
            is_multi_hop = await self._is_multi_hop(query)

            if is_multi_hop and self.config.enable_multi_hop:
                # 多跳推理模式
                result = await self._multi_hop_answer(query, contexts)
            else:
                # 单跳模式
                result = await self._single_hop_answer(query, documents, contexts)

            # 2. 应用严格性增强
            if mode == "strict" and self.config.enable_crag:
                result = await self._apply_crag(result, query)

            # 3. 幻觉检测 - 仅在严格模式下启用
            if mode == "strict" and self.config.enable_hallucination_detection:
                try:
                    h_report = await self.hallucination_detector.detect(query, result.answer)
                    hallucination_score = h_report.overall_score
                    hallucination_risk = h_report.risk_level
                    result.hallucination_score = hallucination_score
                    result.hallucination_risk = hallucination_risk
                except Exception as e:
                    logger.warning(f"Hallucination detection skipped: {e}")

            # 4. 置信度校准 - 仅在严格模式下启用
            if mode == "strict" and self.config.enable_confidence_calibration:
                try:
                    conf_score = await self.confidence_calibrator.calibrate(
                        query, result.answer, contexts or []
                    )
                    confidence = conf_score.overall
                    result.confidence = confidence
                except Exception as e:
                    logger.warning(f"Confidence calibration skipped: {e}")

            # 5. RAGAs 评估 - 仅当明确请求且有上下文时
            if mode == "strict" and contexts:
                try:
                    metrics = await self.ragas_evaluator.evaluate(
                        query, result.answer, contexts
                    )
                    result.ragas_metrics = {
                        "faithfulness": metrics.faithfulness,
                        "answer_relevance": metrics.answer_relevance,
                        "context_precision": metrics.context_precision,
                        "avg_score": metrics.avg_score,
                    }
                except Exception as e:
                    logger.warning(f"RAGAs evaluation skipped: {e}")

            return result

        except Exception as e:
            logger.error(f"AcademicQA ask failed: {e}")
            errors.append(str(e))
            return AcademicQAResult(
                answer="抱歉，处理问题时发生错误。",
                errors=errors,
            )

    async def _is_multi_hop(self, query: str) -> bool:
        """判断是否是多跳问题"""
        if not self.config.enable_multi_hop:
            return False

        if self.query_decomposer:
            sub_questions = await self.query_decomposer.decompose(query)
            return len(sub_questions) > 1

        # 简单的启发式判断
        multi_hop_indicators = [
            "和", "与", "比较", "关系",
            "why", "how", "compare", "relationship"
        ]
        score = sum(1 for ind in multi_hop_indicators if ind in query.lower())
        return score >= 2

    async def _single_hop_answer(
        self,
        query: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        contexts: Optional[List[str]] = None,
    ) -> AcademicQAResult:
        """单跳问答

        Args:
            query: 问题
            documents: 文档列表
            contexts: 直接提供的上下文

        Returns:
            AcademicQAResult: 问答结果
        """
        reasoning_chain = []
        citations = []

        # 确定上下文
        if contexts:
            docs_for_answer = [{"content": ctx} for ctx in contexts]
        elif documents:
            docs_for_answer = documents
        else:
            # 从向量存储检索
            docs_for_answer = await self._async_retriever(query, self.config.top_k)

        # Self-RAG 反思生成
        if self.config.enable_self_rag and self.self_rag:
            rag_result = await self.self_rag.reflective_generate(query)
            answer = rag_result.answer
            reasoning_chain.append({
                "step": "self_rag",
                "used_retrieval": rag_result.used_retrieval,
                "reflection_log": rag_result.reflection_log,
            })

            # 更新上下文
            if rag_result.context:
                # 将字符串上下文转换为字典格式
                if rag_result.context and isinstance(rag_result.context[0], str):
                    docs_for_answer = [{"content": ctx} for ctx in rag_result.context]
                else:
                    docs_for_answer = rag_result.context

            # 如果 Self-RAG 返回空答案，fallback 到 AnswerGenerator
            if not answer:
                gen_result = await self.answer_generator.generate(
                    query, docs_for_answer, include_citations=True
                )
                answer = gen_result.answer
        else:
            # 直接生成
            gen_result = await self.answer_generator.generate(
                query, docs_for_answer, include_citations=True
            )
            answer = gen_result.answer

        # 引用溯源
        if docs_for_answer:
            # 确保 docs_for_answer 是字典列表
            if docs_for_answer and isinstance(docs_for_answer[0], str):
                docs_for_answer = [{"content": ctx} for ctx in docs_for_answer]
            traced = self.citation_tracker.trace_content(answer, docs_for_answer)
            for tc in traced:
                if tc.source_citation:
                    citations.append({
                        "source_id": tc.source_citation.source_id,
                        "source_title": tc.source_citation.source_title,
                        "relevance": tc.confidence,
                        "quoted_text": tc.source_citation.quoted_text,
                    })

        # 获取置信度
        try:
            confidence = gen_result.confidence if hasattr(gen_result, 'confidence') and gen_result else 0.5
        except NameError:
            confidence = 0.5

        return AcademicQAResult(
            answer=answer,
            citations=citations,
            confidence=confidence,
            reasoning_chain=reasoning_chain,
        )

    async def _multi_hop_answer(
        self,
        query: str,
        contexts: Optional[List[str]] = None,
    ) -> AcademicQAResult:
        """多跳问答

        Args:
            query: 问题
            contexts: 上下文

        Returns:
            AcademicQAResult: 问答结果
        """
        # 1. 分解问题
        sub_questions = await self.query_decomposer.decompose(query)

        # 2. 多跳推理
        reasoner_result = await self.multi_hop_reasoner.reason(query, top_k=self.config.top_k)

        # 3. 聚合结果
        aggregator_result = await self.answer_aggregator.aggregate(
            query, sub_questions, reasoner_result.sub_answers
        )

        # 4. 构建引用
        citations = []
        for cit in aggregator_result.all_citations[:self.config.max_citations]:
            citations.append({
                "source_id": cit.get("source_id", ""),
                "source_title": cit.get("source_title", ""),
                "relevance": cit.get("relevance", 0.8),
            })

        return AcademicQAResult(
            answer=aggregator_result.final_answer,
            citations=citations,
            confidence=aggregator_result.overall_confidence,
            reasoning_chain=[
                {
                    "step": i + 1,
                    "question": step.question,
                    "answer": step.answer,
                    "confidence": step.confidence,
                }
                for i, step in enumerate(aggregator_result.reasoning_chain)
            ],
        )

    async def _apply_crag(
        self,
        result: AcademicQAResult,
        query: str,
    ) -> AcademicQAResult:
        """应用 CRAG 纠错

        Args:
            result: 当前结果
            query: 问题

        Returns:
            AcademicQAResult: 纠错后的结果
        """
        # 构建检索结果格式
        retrieved_docs = [
            {"content": cit.get("quoted_text", ""), "score": cit.get("relevance", 0.5)}
            for cit in result.citations
        ]

        # CRAG 评估
        crag_result = await self.crag.evaluate(query, retrieved_docs)

        # 根据质量决定是否需要重新生成
        if crag_result.quality.value in ["low", "empty"]:
            logger.warning(f"CRAG quality low: {crag_result.quality.value}")
            # 可以选择降级或重试，此处保持原答案
            result.metadata["crag_quality"] = crag_result.quality.value

        return result

    async def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        chunk_size: int = 512,
    ) -> Dict[str, Any]:
        """文档 ingestion

        将文档分块并索引到向量存储。

        Args:
            documents: 文档列表，每项需包含 content 字段
            chunk_size: 块大小

        Returns:
            Dict[str, Any]: ingestion 结果
        """
        # 使用retriever的index_documents直接完成分块+存储
        result = await self.retriever.index_documents(
            documents=documents,
            chunk_size=512,
            chunk_overlap=100,
        )

        logger.info(f"Ingested {result['num_chunks']} chunks from {result['num_documents']} documents")

        return result

    def format_answer_with_citations(self, result: AcademicQAResult) -> str:
        """格式化带引用的答案

        Args:
            result: 问答结果

        Returns:
            str: 格式化的答案文本
        """
        parts = [result.answer]

        if result.citations:
            parts.append("\n\n## 参考文献\n")
            for i, cit in enumerate(result.citations, 1):
                title = cit.get("source_title", "未知")
                parts.append(f"[{i}] {title}")

        if result.confidence > 0:
            parts.append(f"\n\n置信度: {result.confidence:.2f}")

        if result.hallucination_risk != "unknown":
            parts.append(f" 幻觉风险: {result.hallucination_risk}")

        return "".join(parts)


async def create_academic_qa_system(
    llm: Any,
    vector_store: Optional[Any] = None,
    **kwargs
) -> AcademicQASystem:
    """创建学术QA系统的便捷函数

    Args:
        llm: LLM 实例
        vector_store: 向量存储实例
        **kwargs: 其他配置

    Returns:
        AcademicQASystem: 系统实例
    """
    config = AcademicQAConfig(
        llm=llm,
        vector_store=vector_store,
        **kwargs
    )
    return AcademicQASystem(config=config)