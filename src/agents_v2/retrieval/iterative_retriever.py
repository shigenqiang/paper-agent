"""
迭代式检索引擎 - Iterative Retriever

支持多轮检索-评估-修正循环。
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    documents: List[str]
    iterations: int
    query_history: List[str]
    total_time: float
    converged: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalStep:
    """检索步骤"""
    iteration: int
    query: str
    documents_retrieved: List[str]
    documents_used: List[str]
    evaluation_summary: Dict[str, Any]


class IterativeRetriever:
    """迭代式检索器 - 支持多轮检索-评估-修正"""

    def __init__(self,
                 base_retriever: Any,
                 self_rag_controller: Any,
                 max_iterations: int = 3,
                 min_relevant_docs: int = 5,
                 relevance_threshold: float = 0.7):
        """初始化迭代检索器

        Args:
            base_retriever: 基础检索器，需要有retrieve(query, top_k)方法
            self_rag_controller: SELF-RAG控制器
            max_iterations: 最大迭代次数
            min_relevant_docs: 最小相关文档数
            relevance_threshold: 相关性阈值
        """
        self.base_retriever = base_retriever
        self.controller = self_rag_controller
        self.max_iterations = max_iterations
        self.min_relevant_docs = min_relevant_docs
        self.relevance_threshold = relevance_threshold

        self.iteration_history: List[RetrievalStep] = []
        self.query_rewriter: Optional[Callable] = None

    def set_query_rewriter(self, rewriter: Callable[[str, List[str]], str]):
        """设置查询改写器

        Args:
            rewriter: 改写函数，输入(原始查询, 不相关文档列表)，输出改写后的查询
        """
        self.query_rewriter = rewriter

    async def retrieve(self, query: str, top_k: int = 20) -> RetrievalResult:
        """迭代检索直到满意或达到最大次数

        Args:
            query: 查询字符串
            top_k: 每轮检索的候选数量

        Returns:
            RetrievalResult: 检索结果
        """
        start_time = time.time()
        all_results: List[str] = []
        current_query = query
        query_history = [query]
        self.iteration_history = []

        logger.info(f"开始迭代检索: '{query}'")

        for iteration in range(self.max_iterations):
            iter_start = time.time()
            logger.info(f"迭代 {iteration + 1}/{self.max_iterations}")

            # 1. 检索候选文档
            try:
                candidates = await self.base_retriever.retrieve(current_query, top_k=top_k)
            except Exception as e:
                logger.error(f"检索出错: {e}")
                candidates = []

            if not candidates:
                logger.warning("检索返回空结果")
                break

            # 2. 评估文档
            evaluations = await self.controller.evaluate_documents(
                candidates, current_query
            )

            # 3. 选择相关文档
            relevant = []
            irrelevant = []

            for i, eval_result in enumerate(evaluations):
                if i < len(candidates):
                    if eval_result.should_use:
                        relevant.append(candidates[i])
                    else:
                        irrelevant.append(candidates[i])

            # 记录步骤
            step = RetrievalStep(
                iteration=iteration + 1,
                query=current_query,
                documents_retrieved=candidates,
                documents_used=relevant,
                evaluation_summary={
                    "total_candidates": len(candidates),
                    "relevant_count": len(relevant),
                    "irrelevant_count": len(irrelevant),
                    "avg_relevance": sum(e.relevance_score for e in evaluations) / len(evaluations) if evaluations else 0,
                    "iteration_time": time.time() - iter_start
                }
            )
            self.iteration_history.append(step)

            all_results.extend(relevant)

            logger.info(f"  检索到{len(candidates)}个候选，{len(relevant)}个相关")

            # 4. 检查是否收敛
            if len(relevant) >= self.min_relevant_docs:
                logger.info(f"找到足够相关文档 ({len(relevant)})，停止迭代")
                break

            # 5. 如果相关文档不足，检查是否应该继续
            if len(relevant) < 3 and iteration < self.max_iterations - 1:
                # 改写查询
                if self.query_rewriter:
                    current_query = self.query_rewriter(current_query, irrelevant)
                else:
                    current_query = await self._default_query_rewrite(current_query, irrelevant)

                query_history.append(current_query)
                logger.info(f"  查询改写为: '{current_query}'")

        # 6. 去重
        unique_results = self._deduplicate(all_results)

        total_time = time.time() - start_time

        result = RetrievalResult(
            documents=unique_results,
            iterations=len(self.iteration_history),
            query_history=query_history,
            total_time=total_time,
            converged=len(unique_results) >= self.min_relevant_docs,
            metadata={
                "total_candidates_evaluated": sum(
                    len(step.documents_retrieved) for step in self.iteration_history
                ),
                "final_relevant_count": len(unique_results),
                "iteration_summary": [
                    {
                        "iteration": step.iteration,
                        "query": step.query,
                        "relevant": len(step.documents_used),
                        "total": len(step.documents_retrieved)
                    }
                    for step in self.iteration_history
                ]
            }
        )

        logger.info(f"迭代检索完成: {len(unique_results)}个去重文档, "
                   f"{result.iterations}轮迭代, 耗时{total_time:.2f}s")

        return result

    async def _default_query_rewrite(self, original: str, irrelevant_docs: List[str]) -> str:
        """默认的查询改写方法

        Args:
            original: 原始查询
            irrelevant_docs: 不相关的文档列表

        Returns:
            str: 改写后的查询
        """
        if self.controller and hasattr(self.controller, '_rewrite_query'):
            return await self.controller._rewrite_query(original, irrelevant_docs)

        # 简单的查询扩展
        docs_sample = "\n".join([f"- {d[:80]}..." for d in irrelevant_docs[:2]])
        new_query = f"{original} [相关论文 研究 学术]"
        return new_query

    def _deduplicate(self, documents: List[str]) -> List[str]:
        """去重文档

        Args:
            documents: 文档列表

        Returns:
            List[str]: 去重后的文档
        """
        seen = set()
        unique = []

        for doc in documents:
            # 使用前100个字符作为指纹
            fingerprint = doc[:100].lower().strip()

            if fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(doc)

        return unique

    async def retrieve_with_feedback(self,
                                    query: str,
                                    feedback: str) -> RetrievalResult:
        """基于反馈的检索

        Args:
            query: 查询字符串
            feedback: 用户反馈，用于改进检索

        Returns:
            RetrievalResult: 检索结果
        """
        # 将反馈融入查询
        enhanced_query = f"{query}\n\n用户反馈: {feedback}"

        return await self.retrieve(enhanced_query)

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """获取检索统计信息

        Returns:
            Dict: 统计信息
        """
        if not self.iteration_history:
            return {"status": "no_history"}

        total_docs = sum(len(step.documents_retrieved) for step in self.iteration_history)
        total_relevant = sum(len(step.documents_used) for step in self.iteration_history)

        return {
            "total_iterations": len(self.iteration_history),
            "total_documents_retrieved": total_docs,
            "total_documents_used": total_relevant,
            "overall_relevance_rate": total_relevant / total_docs if total_docs > 0 else 0,
            "avg_iteration_time": sum(s.evaluation_summary.get("iteration_time", 0)
                                    for s in self.iteration_history) / len(self.iteration_history),
            "queries_used": [step.query for step in self.iteration_history]
        }


class AdaptiveRetriever:
    """自适应检索器 - 根据检索难度动态调整策略"""

    def __init__(self,
                 iterative_retriever: IterativeRetriever,
                 difficulty_classifier: Optional[Callable] = None):
        """初始化自适应检索器

        Args:
            iterative_retriever: 迭代检索器
            difficulty_classifier: 难度分类器，输入查询输出难度(0-1)
        """
        self.retriever = iterative_retriever
        self.difficulty_classifier = difficulty_classifier

    async def classify_difficulty(self, query: str) -> float:
        """分类查询难度

        Args:
            query: 查询字符串

        Returns:
            float: 难度分数 (0-1)，越高越难
        """
        if self.difficulty_classifier:
            return await self.difficulty_classifier(query)

        # 简单的基于规则的难度估计
        difficulty = 0.5  # 默认中等难度

        # 长度因素
        if len(query) > 50:
            difficulty += 0.1
        if len(query) > 100:
            difficulty += 0.1

        # 关键词因素
        complex_keywords = ["分析", "比较", "综合", "评估", "analyze", "compare", "evaluate"]
        if any(kw in query.lower() for kw in complex_keywords):
            difficulty += 0.2

        # 问题词因素
        question_words = ["为什么", "如何", "怎样", "why", "how"]
        if any(kw in query.lower() for kw in question_words):
            difficulty += 0.1

        return min(1.0, difficulty)

    async def retrieve(self, query: str) -> RetrievalResult:
        """自适应检索

        Args:
            query: 查询字符串

        Returns:
            RetrievalResult: 检索结果
        """
        # 评估难度
        difficulty = await self.classify_difficulty(query)
        logger.info(f"查询难度评估: {difficulty:.2f}")

        # 根据难度调整参数
        if difficulty < 0.3:
            # 简单查询，单次检索
            logger.info("简单查询，使用快速单次检索")
            result = await self.retriever.retrieve(query, top_k=10)
            result.metadata["strategy"] = "simple"
            result.metadata["difficulty"] = difficulty
            return result

        elif difficulty < 0.6:
            # 中等难度，标准迭代检索
            logger.info("中等难度，使用迭代检索")
            result = await self.retriever.retrieve(query, top_k=20)
            result.metadata["strategy"] = "iterative"
            result.metadata["difficulty"] = difficulty
            return result

        else:
            # 高难度，增强迭代检索
            logger.info("高难度，使用增强迭代检索")
            self.retriever.max_iterations = 5
            self.retriever.min_relevant_docs = 8
            result = await self.retriever.retrieve(query, top_k=30)
            result.metadata["strategy"] = "enhanced_iterative"
            result.metadata["difficulty"] = difficulty
            # 恢复默认参数
            self.retriever.max_iterations = 3
            self.retriever.min_relevant_docs = 5
            return result


# 便捷函数
async def iterative_retrieve(query: str,
                              retriever: Any,
                              max_iterations: int = 3) -> RetrievalResult:
    """迭代检索的便捷函数

    Args:
        query: 查询字符串
        retriever: 基础检索器
        max_iterations: 最大迭代次数

    Returns:
        RetrievalResult: 检索结果
    """
    from .self_rag_controller import SELF_RAGController
    from .dynamic_planner import DynamicRetrievalPlanner

    # 创建规划器
    planner = DynamicRetrievalPlanner()
    plan = await planner.plan(query)

    # 创建控制器
    controller = SELF_RAGController(llm=None)  # 简化版本

    # 创建迭代检索器
    iterative = IterativeRetriever(
        base_retriever=retriever,
        self_rag_controller=controller,
        max_iterations=min(max_iterations, plan.max_iterations)
    )

    return await iterative.retrieve(query, top_k=plan.metadata.get("top_k", 20))
