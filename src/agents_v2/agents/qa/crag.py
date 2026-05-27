"""
CRAG 评估器 - Corrective RAG Evaluator

CRAG (Corrective RAG) 纠错型检索增强生成。
根据检索质量决定处理策略：
- HIGH: 直接使用检索结果
- MEDIUM: 纠错后使用
- LOW: 重新检索或降级
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


class RetrievalQuality(Enum):
    """检索质量等级"""
    HIGH = "high"       # 检索结果完全正确
    MEDIUM = "medium"   # 检索结果可能包含正确答案
    LOW = "low"         # 检索结果不包含答案
    EMPTY = "empty"     # 无检索结果


@dataclass
class CRAGResult:
    """CRAG 评估结果"""
    quality: RetrievalQuality
    evaluation: str  # 评估说明
    source: str  # "direct_retrieval", "corrected_retrieval", "retry_retrieval", "fallback"
    corrected_docs: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CRAGEvaluator:
    """CRAG 评估器

    轻量级检索质量评估，决定后续处理策略。
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        quality_threshold: float = 0.5,
        max_retry: int = 2,
    ):
        """初始化 CRAG 评估器

        Args:
            llm: LLM 实例（用于评估）
            quality_threshold: 质量阈值
            max_retry: 最大重试次数
        """
        self.llm = llm
        self.quality_threshold = quality_threshold
        self.max_retry = max_retry

    async def evaluate(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        retriever: Optional[Callable] = None,
    ) -> CRAGResult:
        """评估检索质量并决定处理策略

        Args:
            query: 用户查询
            retrieved_docs: 检索到的文档
            retriever: 可选的检索器（用于重新检索）

        Returns:
            CRAGResult: 评估结果和处理建议
        """
        if not retrieved_docs:
            return CRAGResult(
                quality=RetrievalQuality.EMPTY,
                evaluation="未检索到任何文档",
                source="fallback",
                confidence=0.0,
            )

        # 评估检索质量
        quality, evaluation = await self._evaluate_retrieval_quality(
            query, retrieved_docs
        )

        logger.info(f"CRAG evaluation: quality={quality.value}, evaluation={evaluation}")

        # 根据质量决定处理策略
        if quality == RetrievalQuality.HIGH:
            return CRAGResult(
                quality=quality,
                evaluation=evaluation,
                source="direct_retrieval",
                corrected_docs=retrieved_docs[:5],
                confidence=0.9,
            )

        elif quality == RetrievalQuality.MEDIUM:
            # 尝试纠错
            corrected = await self._correct_retrieval(query, retrieved_docs)
            return CRAGResult(
                quality=quality,
                evaluation=f"已纠错: {evaluation}",
                source="corrected_retrieval",
                corrected_docs=corrected[:5],
                confidence=0.7,
            )

        elif quality == RetrievalQuality.LOW:
            # 尝试重新检索
            if retriever:
                for attempt in range(self.max_retry):
                    new_docs = await self._retry_retrieval(query, retriever)
                    if new_docs:
                        # 重新评估
                        new_quality, new_eval = await self._evaluate_retrieval_quality(
                            query, new_docs
                        )
                        if new_quality != RetrievalQuality.LOW:
                            return CRAGResult(
                                quality=new_quality,
                                evaluation=f"重检成功: {new_eval}",
                                source="retry_retrieval",
                                corrected_docs=new_docs[:5],
                                confidence=0.6,
                            )

            return CRAGResult(
                quality=quality,
                evaluation=f"重检失败: {evaluation}",
                source="fallback",
                corrected_docs=[],
                confidence=0.3,
            )

        return CRAGResult(
            quality=quality,
            evaluation=evaluation,
            source="fallback",
            corrected_docs=[],
            confidence=0.0,
        )

    async def _evaluate_retrieval_quality(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
    ) -> tuple:
        """评估检索结果质量

        Args:
            query: 查询
            retrieved_docs: 检索结果

        Returns:
            tuple: (RetrievalQuality, evaluation_string)
        """
        if not retrieved_docs:
            return RetrievalQuality.EMPTY, "未检索到文档"

        # 使用 LLM 进行轻量级评估
        if self.llm:
            return await self._llm_evaluate(query, retrieved_docs)

        # 降级：使用简单启发式方法
        return self._heuristic_evaluate(query, retrieved_docs)

    async def _llm_evaluate(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
    ) -> tuple:
        """使用 LLM 评估检索质量"""
        # 构建评估 prompt
        docs_content = "\n\n".join([
            f"[文档 {i+1}]\n{doc.get('content', doc.get('page_content', ''))[:300]}"
            for i, doc in enumerate(retrieved_docs[:3])
        ])

        prompt = f"""评估以下检索结果是否能回答用户问题。

用户问题: {query}

检索结果:
{docs_content}

请判断检索质量（只输出一个词）：
- correct: 检索结果包含正确答案
- incorrect: 检索结果不包含答案
- partial: 检索结果可能包含答案（不完整或不直接）

输出词:"""

        try:
            response = await self._call_llm(prompt)
            response = response.strip().lower()

            if "correct" in response:
                return RetrievalQuality.HIGH, "检索结果完全正确"
            elif "incorrect" in response:
                return RetrievalQuality.LOW, "检索结果不包含答案"
            else:
                return RetrievalQuality.MEDIUM, "检索结果可能包含答案（不完整）"

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return self._heuristic_evaluate(query, retrieved_docs)

    def _heuristic_evaluate(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
    ) -> tuple:
        """启发式评估检索质量

        基于关键词重叠和相关性分数。
        """
        query_terms = set(query.lower().split())

        relevance_scores = []
        for doc in retrieved_docs:
            content = doc.get("content", doc.get("page_content", str(doc))).lower()
            doc_terms = set(content.split())

            # 计算重叠度
            overlap = len(query_terms & doc_terms)
            if query_terms:
                score = overlap / len(query_terms)
            else:
                score = 0.5

            # 考虑元数据中的相关性分数
            if "score" in doc:
                score = (score + doc["score"]) / 2

            relevance_scores.append(score)

        avg_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

        if avg_score >= 0.6:
            return RetrievalQuality.HIGH, f"平均相关度: {avg_score:.2f}"
        elif avg_score >= 0.3:
            return RetrievalQuality.MEDIUM, f"平均相关度: {avg_score:.2f}"
        else:
            return RetrievalQuality.LOW, f"平均相关度: {avg_score:.2f}"

    async def _correct_retrieval(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """纠错检索结果

        对 MEDIUM 质量的检索结果进行纠错和优化。
        """
        if not retrieved_docs:
            return []

        # 重写查询
        if self.llm:
            try:
                new_query = await self._rewrite_query(query, retrieved_docs)
                logger.info(f"Query rewritten: {query} -> {new_query}")
            except Exception as e:
                logger.error(f"Query rewrite failed: {e}")
                new_query = query
        else:
            new_query = query

        # 过滤低相关片段
        corrected = []
        query_terms = set(new_query.lower().split())

        for doc in retrieved_docs:
            content = doc.get("content", doc.get("page_content", str(doc)))
            content_lower = content.lower()
            content_terms = set(content_lower.split())

            # 计算相关性
            overlap = len(query_terms & content_terms)
            if query_terms:
                relevance = overlap / len(query_terms)
            else:
                relevance = 0.5

            # 相关性达标的保留
            if relevance >= 0.2:
                doc["relevance_score"] = relevance
                corrected.append(doc)

        # 按相关性排序
        corrected.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return corrected

    async def _rewrite_query(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
    ) -> str:
        """重写查询

        基于已有检索结果，生成更精准的查询。
        """
        docs_summary = "\n".join([
            f"- {doc.get('content', '')[:100]}..."
            for doc in retrieved_docs[:2]
        ])

        prompt = f"""基于以下检索结果，为用户问题生成一个更好的搜索查询。

用户问题: {query}

当前检索到的内容:
{docs_summary}

请生成一个更好的搜索查询（只输出查询词，不要解释）："""

        try:
            response = await self._call_llm(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            return query

    async def _retry_retrieval(
        self,
        query: str,
        retriever: Callable,
    ) -> List[Dict[str, Any]]:
        """重新检索

        使用重写后的查询重新检索。
        """
        try:
            # 扩展查询
            expanded_query = await self._expand_query(query)
            logger.info(f"Retry with expanded query: {expanded_query}")

            # 执行检索
            if asyncio.iscoroutinefunction(retriever):
                results = await retriever(expanded_query, top_k=10)
            else:
                results = retriever(expanded_query, top_k=10)

            return results if results else []

        except Exception as e:
            logger.error(f"Retry retrieval failed: {e}")
            return []

    async def _expand_query(self, query: str) -> str:
        """扩展查询

        添加同义词或相关概念。
        """
        if not self.llm:
            return query

        prompt = f"""为以下学术查询添加相关术语（只输出扩展后的查询）：

原始查询: {query}

扩展要求：
1. 添加同义词
2. 添加上位词（如"机器学习"添加"人工智能"）
3. 添加相关概念

输出查询词:"""

        try:
            response = await self._call_llm(prompt)
            return response.strip()
        except Exception:
            return query

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if hasattr(self.llm, 'agenerate'):
                result = await self.llm.agenerate([prompt])
                return result.generations[0][0].text.strip()
            elif hasattr(self.llm, 'generate'):
                result = self.llm.generate([prompt])
                return result.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


# 便捷函数
async def crag_evaluate(
    query: str,
    retrieved_docs: List[Dict[str, Any]],
    llm: Optional[Any] = None,
    **kwargs
) -> CRAGResult:
    """CRAG 评估的便捷函数"""
    evaluator = CRAGEvaluator(llm=llm, **kwargs)
    return await evaluator.evaluate(query, retrieved_docs)