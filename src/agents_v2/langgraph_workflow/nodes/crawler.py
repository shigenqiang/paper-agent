"""
Crawler Agent - LangGraph 工作流节点

职责：
- 多源论文搜索（arXiv, Semantic Scholar, PubMed）
- 通过引用网络扩展
- 去重与合并

集成现有的 SearchFactory 和 SearchResult。
"""
import logging
import time
from typing import Dict, List, Optional

from ...search.search_factory import SearchFactory
from ...search.base_searcher import SearchResult
from ..state import PaperAgentState, Paper

logger = logging.getLogger(__name__)


class CrawlerAgent:
    """论文爬取 Agent - LangGraph 节点"""

    def __init__(
        self,
        sources: Optional[List[str]] = None,
        max_per_source: int = 15,
        enable_enhanced_retrieval: bool = True,
        retriever=None,
        llm=None,
    ):
        """
        Args:
            sources: 搜索源列表，默认 ["arxiv", "semantic_scholar"]
            max_per_source: 每个源的最大结果数
            enable_enhanced_retrieval: 是否启用增强检索（SELF-RAG 等）
            retriever: 外部检索器（可选，与 sources 互斥）
            llm: LLM 实例（用于增强检索的 SELF-RAG）
        """
        self.sources = sources or ["arxiv", "semantic_scholar"]
        self.max_per_source = max_per_source
        self.enable_enhanced_retrieval = enable_enhanced_retrieval
        self.retriever = retriever
        self.llm = llm
        self._enhanced_pipeline = None

    def _get_enhanced_pipeline(self):
        """懒加载增强检索管道"""
        if self._enhanced_pipeline is None and self.retriever and self.llm:
            from ...retrieval.enhanced_retrieval_pipeline import EnhancedRetrievalPipeline, PipelineConfig
            config = PipelineConfig(
                enable_query_rewrite=True,
                enable_query_expansion=True,
                enable_reranking=True,
                enable_self_rag=True,
                final_top_k=20,
            )
            self._enhanced_pipeline = EnhancedRetrievalPipeline(
                retriever=self.retriever,
                llm=self.llm,
                config=config,
            )
        return self._enhanced_pipeline

    def _search_result_to_paper(self, result: SearchResult) -> Paper:
        """将 SearchResult 转换为 Paper"""
        return Paper(
            id=result.paper_id,
            title=result.title,
            authors=result.authors or [],
            abstract=result.abstract,
            url=result.url,
            year=result.year,
            citations=result.citations,
            venue=result.venue,
        )

    def _search_source(self, source_name: str, query: str) -> List[Paper]:
        """搜索单个源，失败时返回空列表"""
        try:
            searcher = SearchFactory.get(source_name)
            if searcher is None:
                logger.warning(f"搜索源 {source_name} 不可用")
                return []

            import asyncio
            response = asyncio.get_event_loop().run_until_complete(
                searcher.search(query, max_results=self.max_per_source)
            )
            papers = [self._search_result_to_paper(r) for r in response.results]
            logger.info(f"[Crawler] {source_name}: 找到 {len(papers)} 篇论文")
            return papers
        except Exception as e:
            logger.error(f"[Crawler] {source_name} 搜索失败: {e}")
            return []

    def expand_via_citations(self, papers: List[Paper], max_per_paper: int = 5) -> List[Paper]:
        """通过引用网络扩展论文列表

        取引用数最高的3篇论文，获取其引用文献进行扩展。
        """
        if not papers:
            return []

        all_papers = list(papers)
        seen_ids = {p.id for p in papers}

        top_by_citations = sorted(papers, key=lambda p: p.citations, reverse=True)[:3]

        for paper in top_by_citations:
            try:
                ss_searcher = SearchFactory.get("semantic_scholar")
                if ss_searcher is None:
                    continue

                import asyncio
                response = asyncio.get_event_loop().run_until_complete(
                    ss_searcher.search(paper.title, max_results=max_per_paper)
                )
                for result in response.results:
                    if result.paper_id not in seen_ids:
                        seen_ids.add(result.paper_id)
                        all_papers.append(self._search_result_to_paper(result))
            except Exception as e:
                logger.debug(f"[Crawler] 扩展引用失败: {e}")

        return all_papers

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """LangGraph 节点入口

        Args:
            state: 当前工作流状态

        Returns:
            更新后的状态（仅返回 papers 字段）
        """
        query = state.user_query
        logger.info(f"[Crawler] 开始爬取论文: {query}")
        start = time.time()

        final_papers: List[Paper] = []

        # 优先使用增强检索管道（如果可用）
        if self.enable_enhanced_retrieval and self.retriever and self.llm:
            pipeline = self._get_enhanced_pipeline()
            if pipeline:
                final_papers = self._search_via_enhanced(query)
            else:
                final_papers = self._search_basic(query)
        else:
            final_papers = self._search_basic(query)

        elapsed = time.time() - start
        logger.info(f"[Crawler] 完成，共找到 {len(final_papers)} 篇论文，耗时 {elapsed:.2f}s")

        state.papers = final_papers
        state.current_phase = "select"
        return state

    def _search_via_enhanced(self, query: str) -> List[Paper]:
        """通过增强检索管道搜索"""
        import asyncio
        from ...retrieval.enhanced_retrieval_pipeline import enhanced_retrieve

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                enhanced_retrieve(
                    query=query,
                    retriever=self.retriever,
                    llm=self.llm,
                    top_k=20,
                    enable_all_optimizations=True,
                )
            )
            # 将检索结果转换为 Paper
            papers = []
            for doc in result.documents:
                papers.append(Paper(
                    id=f"retrieved_{hash(doc)}",
                    title=doc[:200],
                    authors=[],
                    abstract=doc,
                    url="",
                ))
            logger.info(f"[Crawler] 增强检索返回 {len(papers)} 篇论文")
            return papers
        except Exception as e:
            logger.error(f"[Crawler] 增强检索失败，回退到基础搜索: {e}")
            return self._search_basic(query)

    def _search_basic(self, query: str) -> List[Paper]:
        """基础多源搜索"""
        # 多源搜索
        all_papers: List[Paper] = []
        for source in self.sources:
            all_papers.extend(self._search_source(source, query))

        # 去重
        seen = set()
        unique_papers = []
        for p in all_papers:
            if p.id not in seen:
                seen.add(p.id)
                unique_papers.append(p)

        # 通过引用网络扩展
        if len(unique_papers) > 0:
            expanded = self.expand_via_citations(unique_papers)
            unique_papers = expanded

        # 再次去重
        seen = set()
        final_papers = []
        for p in unique_papers:
            if p.id not in seen:
                seen.add(p.id)
                final_papers.append(p)

        return final_papers
