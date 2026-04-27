"""
Selector Agent - LangGraph 工作流节点

职责：
- 基于相关性评分筛选论文
- Cross-Encoder 重排序（如果可用）
- 选择 Top-K 高质量论文

集成现有的 CrossEncoderReranker。
"""
import logging
import time
from typing import List, Optional

from ...retrieval.cross_encoder_reranker import CrossEncoderReranker
from ..state import PaperAgentState, Paper

logger = logging.getLogger(__name__)


class SelectorAgent:
    """论文筛选 Agent - LangGraph 节点"""

    def __init__(
        self,
        top_k: int = 20,
        min_relevance: float = 0.3,
        enable_reranking: bool = True,
    ):
        """
        Args:
            top_k: 最终选择的论文数
            min_relevance: 最低相关性阈值
            enable_reranking: 是否启用 Cross-Encoder 重排序
        """
        self.top_k = top_k
        self.min_relevance = min_relevance
        self.enable_reranking = enable_reranking
        self._reranker = None

    def _get_reranker(self) -> Optional[CrossEncoderReranker]:
        if self.enable_reranking and self._reranker is None:
            try:
                self._reranker = CrossEncoderReranker()
            except Exception as e:
                logger.warning(f"Cross-Encoder 初始化失败，将使用基础筛选: {e}")
                self.enable_reranking = False
        return self._reranker

    def _compute_keyword_relevance(self, paper: Paper, query: str) -> float:
        """基于关键词匹配计算基础相关性分数"""
        query_terms = query.lower().split()
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower()

        score = 0.0
        for term in query_terms:
            if term in title_lower:
                score += 0.3
            if term in abstract_lower:
                score += 0.1

        # 归一化到 [0, 1]
        return min(score / len(query_terms), 1.0) if query_terms else 0.0

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """LangGraph 节点入口"""
        papers = state.papers
        query = state.user_query
        logger.info(f"[Selector] 开始筛选论文，候选数量: {len(papers)}")
        start = time.time()

        if not papers:
            logger.warning("[Selector] 没有候选论文")
            state.selected_papers = []
            state.current_phase = "outline"
            return state

        # Step 1: 基础相关性评分
        for paper in papers:
            paper.relevance_score = self._compute_keyword_relevance(paper, query)

        # Step 2: 过滤低相关性论文
        filtered = [p for p in papers if p.relevance_score >= self.min_relevance]

        # Step 3: Cross-Encoder 重排序
        if self.enable_reranking and len(filtered) > 1:
            reranker = self._get_reranker()
            if reranker:
                try:
                    import asyncio
                    texts = [f"{p.title}. {p.abstract}" for p in filtered]
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    reranked = loop.run_until_complete(reranker.rerank(query, texts, top_k=self.top_k))
                    for rank_item in reranked:
                        idx = rank_item.doc_index if hasattr(rank_item, "doc_index") else rank_item.get("index", 0)
                        new_score = rank_item.score if hasattr(rank_item, "score") else rank_item.get("score", 0.0)
                        if 0 <= idx < len(filtered):
                            filtered[idx].relevance_score = new_score
                except Exception as e:
                    logger.warning(f"重排序失败，使用基础评分: {e}")

        # Step 4: 综合排序 (relevance_score * 0.6 + citations_normalized * 0.4)
        max_citations = max((p.citations for p in filtered), default=1)
        for paper in filtered:
            citation_norm = paper.citations / max_citations if max_citations > 0 else 0
            paper.relevance_score = paper.relevance_score * 0.6 + citation_norm * 0.4

        filtered.sort(key=lambda p: p.relevance_score, reverse=True)
        selected = filtered[: self.top_k]

        elapsed = time.time() - start
        logger.info(
            f"[Selector] 完成，选择 {len(selected)}/{len(papers)} 篇论文，耗时 {elapsed:.2f}s"
        )

        state.selected_papers = selected
        state.current_phase = "outline"
        return state
