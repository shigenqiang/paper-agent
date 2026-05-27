"""
Enhanced Retrieval Pipeline - 增强检索管道

整合Query改写、扩展、SELF-RAG、Cross-Encoder重排序等功能，
提供统一的检索优化接口。

阶段1-Week1: 检索优化集成
"""

from src.agents_v2.logging_config import get_logging_logger

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import asyncio

from .query_rewriter import QueryRewriter, RewriteResult
from .query_expander import QueryExpander, ExpansionResult
from .cross_encoder_reranker import CrossEncoderReranker, RerankedDoc
from .self_rag_controller import SELF_RAGController, RAGResponse

logger = get_logging_logger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    query: str
    documents: List[str]
    scores: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 优化信息
    query_rewritten: bool = False
    query_expanded: bool = False
    reranked: bool = False
    self_rag_applied: bool = False

    # 性能指标
    total_time: float = 0.0
    retrieval_time: float = 0.0
    rerank_time: float = 0.0


@dataclass
class PipelineConfig:
    """管道配置"""
    # Query优化
    enable_query_rewrite: bool = True
    enable_query_expansion: bool = True

    # 检索策略
    initial_top_k: int = 100  # 初始检索数量
    final_top_k: int = 20     # 最终返回数量

    # 重排序
    enable_reranking: bool = True
    rerank_top_k: int = 50    # 重排序前保留的文档数

    # SELF-RAG
    enable_self_rag: bool = True
    relevance_threshold: float = 0.7

    # 迭代检索
    enable_iterative: bool = False
    max_iterations: int = 3
    min_relevant_docs: int = 5


class EnhancedRetrievalPipeline:
    """增强检索管道

    整合多种检索优化技术：
    1. Query改写和扩展
    2. 多源检索
    3. Cross-Encoder重排序
    4. SELF-RAG质量评估
    5. 迭代检索优化
    """

    def __init__(
        self,
        retriever: Any,
        llm: Any = None,
        config: Optional[PipelineConfig] = None
    ):
        """初始化增强检索管道

        Args:
            retriever: 基础检索器（需要有retrieve方法）
            llm: LLM实例（用于SELF-RAG）
            config: 管道配置
        """
        self.retriever = retriever
        self.llm = llm
        self.config = config or PipelineConfig()

        # 初始化组件
        self.query_rewriter = QueryRewriter(llm=llm)
        self.query_expander = QueryExpander()
        self.reranker = CrossEncoderReranker()

        if llm and self.config.enable_self_rag:
            self.self_rag = SELF_RAGController(
                llm=llm,
                relevance_threshold=self.config.relevance_threshold
            )
        else:
            self.self_rag = None

        logger.info("增强检索管道初始化完成")

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        enable_optimization: bool = True
    ) -> RetrievalResult:
        """执行增强检索

        Args:
            query: 查询字符串
            top_k: 返回文档数量（覆盖配置）
            enable_optimization: 是否启用优化

        Returns:
            RetrievalResult: 检索结果
        """
        start_time = time.time()
        top_k = top_k or self.config.final_top_k

        logger.info(f"开始增强检索: '{query}'")

        # 阶段1: Query优化
        optimized_queries = await self._optimize_query(query, enable_optimization)

        # 阶段2: 多查询检索
        retrieval_start = time.time()
        all_docs = await self._multi_query_retrieve(optimized_queries)
        retrieval_time = time.time() - retrieval_start

        if not all_docs:
            logger.warning("检索返回空结果")
            return RetrievalResult(
                query=query,
                documents=[],
                scores=[],
                total_time=time.time() - start_time,
                retrieval_time=retrieval_time
            )

        # 阶段3: 重排序
        rerank_start = time.time()
        if enable_optimization and self.config.enable_reranking:
            reranked_docs = await self._rerank_documents(query, all_docs)
        else:
            reranked_docs = [(doc, 1.0) for doc in all_docs[:top_k]]
        rerank_time = time.time() - rerank_start

        # 阶段4: SELF-RAG质量评估（可选）
        if enable_optimization and self.config.enable_self_rag and self.self_rag:
            filtered_docs = await self._apply_self_rag(query, reranked_docs)
        else:
            filtered_docs = reranked_docs

        # 构建结果
        final_docs = [doc for doc, score in filtered_docs[:top_k]]
        final_scores = [score for doc, score in filtered_docs[:top_k]]

        result = RetrievalResult(
            query=query,
            documents=final_docs,
            scores=final_scores,
            query_rewritten=self.config.enable_query_rewrite and enable_optimization,
            query_expanded=self.config.enable_query_expansion and enable_optimization,
            reranked=self.config.enable_reranking and enable_optimization,
            self_rag_applied=self.config.enable_self_rag and enable_optimization and self.self_rag is not None,
            total_time=time.time() - start_time,
            retrieval_time=retrieval_time,
            rerank_time=rerank_time,
            metadata={
                "optimized_queries": optimized_queries,
                "total_candidates": len(all_docs),
                "final_count": len(final_docs)
            }
        )

        logger.info(f"检索完成: 返回{len(final_docs)}个文档，耗时{result.total_time:.2f}s")
        return result

    async def _optimize_query(
        self,
        query: str,
        enable_optimization: bool
    ) -> List[str]:
        """优化查询

        Args:
            query: 原始查询
            enable_optimization: 是否启用优化

        Returns:
            List[str]: 优化后的查询列表
        """
        queries = [query]  # 始终包含原查询

        if not enable_optimization:
            return queries

        # Query改写
        if self.config.enable_query_rewrite:
            try:
                rewrite_result = self.query_rewriter.rewrite(query, rewrite_type="auto")
                if rewrite_result.rewritten_query != query:
                    queries.append(rewrite_result.rewritten_query)
                    logger.debug(f"Query改写: '{query}' -> '{rewrite_result.rewritten_query}'")
            except Exception as e:
                logger.error(f"Query改写失败: {e}")

        # Query扩展
        if self.config.enable_query_expansion:
            try:
                expansion_result = self.query_expander.expand(query)
                # 添加前3个扩展查询
                for expanded_q in expansion_result.expanded_queries[:3]:
                    if expanded_q not in queries:
                        queries.append(expanded_q)
                logger.debug(f"Query扩展: 生成{len(expansion_result.expanded_queries)}个扩展")
            except Exception as e:
                logger.error(f"Query扩展失败: {e}")

        return queries

    async def _multi_query_retrieve(
        self,
        queries: List[str]
    ) -> List[str]:
        """多查询检索

        Args:
            queries: 查询列表

        Returns:
            List[str]: 去重后的文档列表
        """
        all_docs = []
        seen = set()

        for q in queries:
            try:
                # 调用基础检索器
                if hasattr(self.retriever, 'retrieve'):
                    docs = await self.retriever.retrieve(q, top_k=self.config.initial_top_k)
                elif hasattr(self.retriever, 'search'):
                    docs = await self.retriever.search(q, top_k=self.config.initial_top_k)
                else:
                    logger.error("检索器没有retrieve或search方法")
                    continue

                # 去重
                for doc in docs:
                    doc_str = str(doc)
                    if doc_str not in seen:
                        seen.add(doc_str)
                        all_docs.append(doc_str)

                logger.debug(f"查询'{q[:50]}...'检索到{len(docs)}个文档")

            except Exception as e:
                logger.error(f"检索查询'{q}'失败: {e}")

        return all_docs

    async def _rerank_documents(
        self,
        query: str,
        documents: List[str]
    ) -> List[Tuple[str, float]]:
        """重排序文档

        Args:
            query: 查询
            documents: 文档列表

        Returns:
            List[Tuple[str, float]]: (文档, 分数)列表
        """
        try:
            # 限制重排序的文档数量
            docs_to_rerank = documents[:self.config.rerank_top_k]

            # 使用Cross-Encoder重排序
            reranked = await self.reranker.rerank(
                query=query,
                candidates=docs_to_rerank,
                top_k=len(docs_to_rerank)
            )

            # 转换为(doc, score)格式
            result = [(r.doc, r.score) for r in reranked]

            # 添加未重排序的文档（如果有）
            if len(documents) > self.config.rerank_top_k:
                remaining = documents[self.config.rerank_top_k:]
                result.extend([(doc, 0.5) for doc in remaining])

            logger.debug(f"重排序完成: {len(docs_to_rerank)}个文档")
            return result

        except Exception as e:
            logger.error(f"重排序失败: {e}")
            # 失败时返回原顺序
            return [(doc, 1.0) for doc in documents]

    async def _apply_self_rag(
        self,
        query: str,
        documents: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """应用SELF-RAG质量评估

        Args:
            query: 查询
            documents: (文档, 分数)列表

        Returns:
            List[Tuple[str, float]]: 过滤后的文档列表
        """
        try:
            docs = [doc for doc, score in documents]

            # 评估文档相关性
            evaluations = await self.self_rag.evaluate_documents(docs, query)

            # 过滤相关文档
            filtered = []
            for i, eval_result in enumerate(evaluations):
                if eval_result.should_use and i < len(documents):
                    doc, original_score = documents[i]
                    # 结合原始分数和相关性分数
                    combined_score = (original_score + eval_result.relevance_score) / 2
                    filtered.append((doc, combined_score))

            logger.debug(f"SELF-RAG过滤: {len(docs)} -> {len(filtered)}个文档")

            # 如果过滤后文档太少，保留原结果
            if len(filtered) < 3:
                logger.warning("SELF-RAG过滤后文档太少，使用原结果")
                return documents

            return filtered

        except Exception as e:
            logger.error(f"SELF-RAG评估失败: {e}")
            return documents

    async def iterative_retrieve(
        self,
        query: str,
        max_iterations: Optional[int] = None
    ) -> RetrievalResult:
        """迭代检索

        持续检索直到找到足够的相关文档或达到最大迭代次数。

        Args:
            query: 查询
            max_iterations: 最大迭代次数

        Returns:
            RetrievalResult: 检索结果
        """
        max_iterations = max_iterations or self.config.max_iterations
        start_time = time.time()

        all_results = []
        current_query = query

        for iteration in range(max_iterations):
            logger.info(f"迭代检索 {iteration + 1}/{max_iterations}")

            # 执行检索
            result = await self.retrieve(current_query, enable_optimization=True)

            # 收集结果
            for doc, score in zip(result.documents, result.scores):
                if doc not in [d for d, s in all_results]:
                    all_results.append((doc, score))

            # 检查是否足够
            if len(all_results) >= self.config.min_relevant_docs:
                logger.info(f"找到足够文档({len(all_results)})，停止迭代")
                break

            # 改写查询继续检索
            if iteration < max_iterations - 1:
                try:
                    rewrite_result = self.query_rewriter.rewrite(
                        current_query,
                        rewrite_type="expansion"
                    )
                    current_query = rewrite_result.rewritten_query
                    logger.debug(f"查询改写: '{query}' -> '{current_query}'")
                except Exception as e:
                    logger.error(f"查询改写失败: {e}")
                    break

        # 构建最终结果
        final_docs = [doc for doc, score in all_results[:self.config.final_top_k]]
        final_scores = [score for doc, score in all_results[:self.config.final_top_k]]

        return RetrievalResult(
            query=query,
            documents=final_docs,
            scores=final_scores,
            query_rewritten=True,
            query_expanded=True,
            reranked=True,
            self_rag_applied=self.self_rag is not None,
            total_time=time.time() - start_time,
            metadata={
                "iterations": iteration + 1,
                "total_candidates": len(all_results)
            }
        )


# 便捷函数
async def enhanced_retrieve(
    query: str,
    retriever: Any,
    llm: Any = None,
    top_k: int = 20,
    enable_all_optimizations: bool = True
) -> RetrievalResult:
    """增强检索的便捷函数

    Args:
        query: 查询
        retriever: 检索器
        llm: LLM实例
        top_k: 返回文档数
        enable_all_optimizations: 是否启用所有优化

    Returns:
        RetrievalResult: 检索结果
    """
    config = PipelineConfig(
        enable_query_rewrite=enable_all_optimizations,
        enable_query_expansion=enable_all_optimizations,
        enable_reranking=enable_all_optimizations,
        enable_self_rag=enable_all_optimizations and llm is not None,
        final_top_k=top_k
    )

    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        llm=llm,
        config=config
    )

    return await pipeline.retrieve(query)
