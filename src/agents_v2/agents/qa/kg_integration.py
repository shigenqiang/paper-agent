"""
知识图谱与学术QA集成模块

功能：
1. 混合检索：向量检索 + 图检索 + KG子图上下文
2. 多跳推理增强：基于图关系的推理链构建
3. 实体链接：在答案中嵌入知识图谱实体关系
4. 子图摘要：使用GraphRAG风格的子图摘要增强上下文
"""
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


@dataclass
class KGEnhancedContext:
    """知识图谱增强上下文"""
    # 基础上下文
    base_contexts: List[str] = field(default_factory=list)

    # 图谱上下文
    subgraph_summary: str = ""
    entity_map: Dict[str, str] = field(default_factory=dict)  # entity_id -> name
    evidence: List[str] = field(default_factory=list)

    # 检索结果
    retrieved_entities: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_relations: List[Dict[str, Any]] = field(default_factory=list)

    # 统计信息
    num_entities: int = 0
    num_relations: int = 0
    retrieval_methods: Dict[str, float] = field(default_factory=dict)  # method -> score

    def to_prompt_context(self) -> str:
        """转换为prompt上下文"""
        parts = []

        if self.base_contexts:
            parts.append("=== 文档上下文 ===")
            for ctx in self.base_contexts:
                parts.append(f"- {ctx}")
            parts.append("")

        if self.entity_map:
            parts.append("=== 知识图谱实体 ===")
            for eid, name in self.entity_map.items():
                parts.append(f"- {name}")
            parts.append("")

        if self.subgraph_summary:
            parts.append("=== 子图摘要 ===")
            parts.append(self.subgraph_summary)
            parts.append("")

        if self.evidence:
            parts.append("=== 图谱证据 ===")
            for i, ev in enumerate(self.evidence, 1):
                parts.append(f"{i}. {ev}")
            parts.append("")

        return "\n".join(parts)


class KGRetrieverWrapper:
    """知识图谱检索器包装器

    将 GraphRAG 的检索能力包装为 AcademicQASystem 可用的检索器接口
    """

    def __init__(
        self,
        kg_qa: Optional[Any] = None,
        vector_weight: float = 0.3,
        graph_weight: float = 0.4,
        keyword_weight: float = 0.3
    ):
        """
        Args:
            kg_qa: GraphRAGQA 实例
            vector_weight: 向量检索权重
            graph_weight: 图检索权重
            keyword_weight: 关键词检索权重
        """
        self.kg_qa = kg_qa
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.keyword_weight = keyword_weight

    def set_kg_qa(self, kg_qa: Any) -> None:
        """设置GraphRAG QA系统"""
        self.kg_qa = kg_qa

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        include_subgraph: bool = True
    ) -> KGEnhancedContext:
        """执行知识图谱增强检索

        Args:
            query: 查询文本
            top_k: 返回数量
            include_subgraph: 是否包含子图摘要

        Returns:
            KGEnhancedContext: 知识图谱增强上下文
        """
        if not self.kg_qa:
            logger.warning("No GraphRAG QA available, returning empty context")
            return KGEnhancedContext()

        try:
            # 执行 GraphRAG 查询
            kg_context = await self._async_query(query, top_k)

            # 构建增强上下文
            return self._build_kg_context(kg_context, include_subgraph)

        except Exception as e:
            logger.error(f"KG retrieval failed: {e}")
            return KGEnhancedContext()

    async def _async_query(self, query: str, top_k: int) -> Any:
        """异步查询GraphRAG"""
        if asyncio.iscoroutinefunction(self.kg_qa.query):
            return await self.kg_qa.query(query)
        else:
            return self.kg_qa.query(query)

    def _build_kg_context(
        self,
        kg_context: Any,
        include_subgraph: bool
    ) -> KGEnhancedContext:
        """从GraphRAGContext构建KGEnhancedContext"""
        from src.agents_v2.search.sources.knowledge_graph.kg_graphrag import GraphRAGContext

        if not isinstance(kg_context, GraphRAGContext):
            return KGEnhancedContext()

        # 提取实体和关系
        retrieved_entities = []
        retrieved_relations = []

        for item in kg_context.retrieved_items:
            retrieved_entities.append({
                "entity_id": item.entity_id,
                "entity_type": item.entity_type,
                "score": item.score,
                "method": item.method,
                "content": item.content,
            })

        # 统计各检索方法的得分
        retrieval_methods: Dict[str, float] = {}
        for item in kg_context.retrieved_items:
            method = item.method
            retrieval_methods[method] = retrieval_methods.get(method, 0) + item.score

        return KGEnhancedContext(
            base_contexts=[],
            subgraph_summary=kg_context.subgraph_summary if include_subgraph else "",
            entity_map=kg_context.entity_map,
            evidence=kg_context.evidence,
            retrieved_entities=retrieved_entities,
            retrieved_relations=retrieved_relations,
            num_entities=len(kg_context.entity_map),
            num_relations=len(retrieved_relations),
            retrieval_methods=retrieval_methods,
        )


class KGAnswerEnricher:
    """知识图谱答案增强器

    在答案生成后，使用知识图谱进行增强：
    1. 实体关系补充
    2. 子图路径添加
    3. 知识链接嵌入
    """

    def __init__(self, kg_qa: Optional[Any] = None):
        """初始化增强器

        Args:
            kg_qa: GraphRAGQA 实例
        """
        self.kg_qa = kg_qa

    def set_kg_qa(self, kg_qa: Any) -> None:
        """设置GraphRAG QA系统"""
        self.kg_qa = kg_qa

    async def enrich_answer(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        top_k: int = 5
    ) -> str:
        """增强答案

        Args:
            query: 问题
            answer: 原始答案
            contexts: 上下文列表
            top_k: 知识图谱检索数量

        Returns:
            str: 增强后的答案
        """
        if not self.kg_qa:
            return answer

        try:
            # 从答案中提取潜在实体
            entities = self._extract_potential_entities(answer)

            if not entities:
                return answer

            # 查询知识图谱
            kg_context = await self._async_query(query, top_k)

            if not kg_context or not kg_context.entity_map:
                return answer

            # 构建知识图谱增强文本
            kg_enrichment = self._build_enrichment_text(kg_context, entities)

            # 追加到答案
            if kg_enrichment:
                return f"{answer}\n\n--- 知识图谱补充 ---\n{kg_enrichment}"

            return answer

        except Exception as e:
            logger.error(f"Answer enrichment failed: {e}")
            return answer

    def _extract_potential_entities(self, text: str) -> List[str]:
        """从文本中提取潜在实体"""
        import re

        # 提取带引号的实体
        quoted = re.findall(r'["\"]([^"\"]+)["\"]', text)

        # 提取大写开头的词组（可能是实体名）
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

        entities = list(set(quoted + capitalized))
        return entities[:10]  # 限制数量

    async def _async_query(self, query: str, top_k: int) -> Any:
        """异步查询GraphRAG"""
        if asyncio.iscoroutinefunction(self.kg_qa.query):
            return await self.kg_qa.query(query)
        else:
            return self.kg_qa.query(query)

    def _build_enrichment_text(
        self,
        kg_context: Any,
        entities: List[str]
    ) -> str:
        """构建增强文本"""
        from src.agents_v2.search.sources.knowledge_graph.kg_graphrag import GraphRAGContext

        if not isinstance(kg_context, GraphRAGContext):
            return ""

        parts = []

        # 添加实体信息
        if kg_context.entity_map:
            parts.append("相关实体关系:")
            for eid, name in list(kg_context.entity_map.items())[:5]:
                parts.append(f"- {name}")

        # 添加证据
        if kg_context.evidence:
            parts.append("\n图谱证据:")
            for i, ev in enumerate(kg_context.evidence[:3], 1):
                parts.append(f"{i}. {ev}")

        return "\n".join(parts)


class KGMultiHopReasoner:
    """知识图谱多跳推理器

    利用知识图谱的图结构进行多跳推理
    """

    def __init__(self, kg_qa: Optional[Any] = None):
        """初始化推理器

        Args:
            kg_qa: GraphRAGQA 实例
        """
        self.kg_qa = kg_qa

    def set_kg_qa(self, kg_qa: Any) -> None:
        """设置GraphRAG QA系统"""
        self.kg_qa = kg_qa

    async def reason_with_graph(
        self,
        query: str,
        sub_questions: List[Any],
        sub_answers: List[Any],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """基于知识图谱的推理链增强

        Args:
            query: 原始问题
            sub_questions: 子问题列表
            sub_answers: 子答案列表
            top_k: 检索数量

        Returns:
            增强后的推理链
        """
        if not self.kg_qa:
            return self._build_simple_chain(sub_questions, sub_answers)

        try:
            # 查询知识图谱获取上下文
            kg_context = await self._async_query(query, top_k)

            # 构建增强推理链
            chain = self._build_enhanced_chain(
                sub_questions, sub_answers, kg_context
            )

            return chain

        except Exception as e:
            logger.error(f"KG multi-hop reasoning failed: {e}")
            return self._build_simple_chain(sub_questions, sub_answers)

    async def _async_query(self, query: str, top_k: int) -> Any:
        """异步查询GraphRAG"""
        if asyncio.iscoroutinefunction(self.kg_qa.query):
            return await self.kg_qa.query(query)
        else:
            return self.kg_qa.query(query)

    def _build_simple_chain(
        self,
        sub_questions: List[Any],
        sub_answers: List[Any]
    ) -> List[Dict[str, Any]]:
        """构建简单推理链"""
        chain = []

        for i, (sq, sa) in enumerate(zip(sub_questions, sub_answers)):
            chain.append({
                "step": i + 1,
                "question": sq.text if hasattr(sq, 'text') else str(sq),
                "answer": sa.answer if hasattr(sa, 'answer') else str(sa),
                "kg_context": None,
            })

        return chain

    def _build_enhanced_chain(
        self,
        sub_questions: List[Any],
        sub_answers: List[Any],
        kg_context: Any
    ) -> List[Dict[str, Any]]:
        """构建增强推理链"""
        from src.agents_v2.search.sources.knowledge_graph.kg_graphrag import GraphRAGContext

        chain = []

        for i, (sq, sa) in enumerate(zip(sub_questions, sub_answers)):
            step = {
                "step": i + 1,
                "question": sq.text if hasattr(sq, 'text') else str(sq),
                "answer": sa.answer if hasattr(sa, 'answer') else str(sa),
            }

            # 添加图谱上下文
            if isinstance(kg_context, GraphRAGContext):
                step["kg_context"] = {
                    "entities": list(kg_context.entity_map.values()),
                    "evidence": kg_context.evidence[:2] if kg_context.evidence else [],
                }

            chain.append(step)

        return chain


class AcademicQAKGIntegration:
    """学术QA与知识图谱集成

    整合 AcademicQASystem 和 GraphRAG，提供增强的问答能力：
    1. 混合检索：文档检索 + 知识图谱检索
    2. 子图增强：在上下文中包含知识图谱子图
    3. 答案增强：使用图谱关系补充答案
    4. 多跳推理：利用图结构增强多跳推理
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        kg_qa: Optional[Any] = None,
        enable_kg_retrieval: bool = True,
        enable_kg_enrichment: bool = True,
        enable_kg_multihop: bool = True,
        vector_weight: float = 0.3,
        graph_weight: float = 0.4,
        keyword_weight: float = 0.3,
    ):
        """初始化集成系统

        Args:
            llm: LLM 实例
            kg_qa: GraphRAGQA 实例
            enable_kg_retrieval: 启用知识图谱检索
            enable_kg_enrichment: 启用答案增强
            enable_kg_multihop: 启用图谱多跳推理
            vector_weight: 向量检索权重
            graph_weight: 图检索权重
            keyword_weight: 关键词检索权重
        """
        self.llm = llm
        self.kg_qa = kg_qa
        self.enable_kg_retrieval = enable_kg_retrieval
        self.enable_kg_enrichment = enable_kg_enrichment
        self.enable_kg_multihop = enable_kg_multihop

        # 初始化组件
        self._init_components(vector_weight, graph_weight, keyword_weight)

    def _init_components(
        self,
        vector_weight: float,
        graph_weight: float,
        keyword_weight: float
    ):
        """初始化组件"""
        from ..academic_qa import AcademicQASystem, AcademicQAConfig

        # KG检索器包装器
        self.kg_retriever = KGRetrieverWrapper(
            kg_qa=self.kg_qa,
            vector_weight=vector_weight,
            graph_weight=graph_weight,
            keyword_weight=keyword_weight,
        )

        # KG答案增强器
        self.kg_enricher = KGAnswerEnricher(kg_qa=self.kg_qa)

        # KG多跳推理器
        self.kg_multihop = KGMultiHopReasoner(kg_qa=self.kg_qa)

        # AcademicQA配置（不启用内部检索，使用KG检索器）
        self.academic_qa_config = AcademicQAConfig(
            llm=self.llm,
            enable_multi_hop=self.enable_kg_multihop,
            # 禁用内部检索，使用KG检索器
            vector_store=None,
            bm25_index=None,
        )

        # AcademicQA系统
        self.academic_qa = AcademicQASystem(config=self.academic_qa_config)

    def set_kg_qa(self, kg_qa: Any) -> None:
        """设置GraphRAG QA系统"""
        self.kg_qa = kg_qa
        self.kg_retriever.set_kg_qa(kg_qa)
        self.kg_enricher.set_kg_qa(kg_qa)
        self.kg_multihop.set_kg_qa(kg_qa)

    async def ask(
        self,
        query: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        contexts: Optional[List[str]] = None,
        mode: str = "strict"
    ) -> Dict[str, Any]:
        """执行知识图谱增强的学术问答

        Args:
            query: 问题
            documents: 文档列表
            contexts: 上下文列表
            mode: 模式

        Returns:
            包含答案和图谱上下文的字典
        """
        # 1. 获取知识图谱上下文
        kg_context = None
        if self.enable_kg_retrieval and self.kg_qa:
            kg_context = await self.kg_retriever.retrieve(query, top_k=10)

        # 2. 合并上下文
        combined_contexts = contexts or []
        if kg_context:
            kg_prompt_context = kg_context.to_prompt_context()
            if kg_prompt_context:
                combined_contexts.append(kg_prompt_context)

        # 3. 执行学术问答
        if documents:
            qa_result = await self.academic_qa.ask(
                query=query,
                documents=documents,
                contexts=combined_contexts if combined_contexts else None,
                mode=mode
            )
        else:
            qa_result = await self.academic_qa.ask(
                query=query,
                contexts=combined_contexts if combined_contexts else None,
                mode=mode
            )

        # 4. 答案增强
        final_answer = qa_result.answer
        if self.enable_kg_enrichment and kg_context:
            final_answer = await self.kg_enricher.enrich_answer(
                query, final_answer, combined_contexts
            )

        # 5. 构建返回结果
        return {
            "answer": final_answer,
            "citations": qa_result.citations,
            "confidence": qa_result.confidence,
            "hallucination_score": qa_result.hallucination_score,
            "hallucination_risk": qa_result.hallucination_risk,
            "reasoning_chain": qa_result.reasoning_chain,
            "ragas_metrics": qa_result.ragas_metrics,
            "kg_context": {
                "entity_map": kg_context.entity_map if kg_context else {},
                "subgraph_summary": kg_context.subgraph_summary if kg_context else "",
                "evidence": kg_context.evidence if kg_context else [],
                "num_entities": kg_context.num_entities if kg_context else 0,
            } if kg_context else None,
            "errors": qa_result.errors,
        }

    def format_answer_with_citations(self, result: Dict[str, Any]) -> str:
        """格式化带引用的答案"""
        parts = [result["answer"]]

        if result.get("citations"):
            parts.append("\n\n## 参考文献\n")
            for i, cit in enumerate(result["citations"], 1):
                title = cit.get("source_title", "未知")
                parts.append(f"[{i}] {title}")

        if result.get("confidence", 0) > 0:
            parts.append(f"\n\n置信度: {result['confidence']:.2f}")

        if result.get("hallucination_risk") != "unknown":
            parts.append(f" 幻觉风险: {result['hallucination_risk']}")

        # 添加知识图谱上下文
        kg_ctx = result.get("kg_context")
        if kg_ctx and kg_ctx.get("entity_map"):
            parts.append("\n\n## 知识图谱实体\n")
            for eid, name in list(kg_ctx["entity_map"].items())[:10]:
                parts.append(f"- {name}")

        return "".join(parts)


async def create_kg_enhanced_qa_system(
    llm: Any,
    kg_qa: Any,
    **kwargs
) -> AcademicQAKGIntegration:
    """创建知识图谱增强的学术QA系统

    Args:
        llm: LLM 实例
        kg_qa: GraphRAGQA 实例
        **kwargs: 其他配置参数

    Returns:
        AcademicQAKGIntegration: 集成系统实例
    """
    return AcademicQAKGIntegration(
        llm=llm,
        kg_qa=kg_qa,
        **kwargs
    )
