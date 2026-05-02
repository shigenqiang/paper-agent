"""
Crawler Agent - LangGraph 工作流节点

职责：
- 多源论文并行搜索（使用SearchOrchestrator）
- 通过引用网络扩展
- 去重与合并

核心优化：使用 SearchOrchestrator 实现多源并行搜索。
"""
from src.agents_v2.logging_config import get_logging_logger
import time
import asyncio
import os
from typing import Dict, List, Optional

from ...search.search_factory import SearchFactory
from ...search.base_searcher import SearchResult
from ..state import PaperAgentState, Paper

logger = get_logging_logger(__name__)


class CrawlerAgent:
    """论文爬取 Agent - LangGraph 节点"""

    def __init__(
        self,
        sources: Optional[List[str]] = None,
        max_per_source: int = 15,
        enable_enhanced_retrieval: bool = None,
        retriever=None,
        llm=None,
    ):
        """
        Args:
            sources: 搜索源列表，默认 ["arxiv", "semantic_scholar"]
            max_per_source: 每个源的最大结果数
            enable_enhanced_retrieval: 是否启用增强检索（SELF-RAG 等）
                - True: 启用 QueryRewriter 等优化
                - False: 禁用，不进行查询改写
                - None: 根据环境变量 ENABLE_QUERY_REWRITE 设置（默认 True）
            retriever: 外部检索器（可选，与 sources 互斥）
            llm: LLM 实例（用于增强检索的 SELF-RAG）
        """
        # 环境变量控制是否启用查询改写（默认启用）
        if enable_enhanced_retrieval is None:
            enable_enhanced_retrieval = os.getenv("ENABLE_QUERY_REWRITE", "true").lower() in ("true", "1", "yes")

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

            response = asyncio.get_event_loop().run_until_complete(
                searcher.search(query, max_results=self.max_per_source)
            )
            papers = [self._search_result_to_paper(r) for r in response.results]
            logger.info(f"[Crawler] {source_name}: 找到 {len(papers)} 篇论文")
            return papers
        except Exception as e:
            logger.error(f"[Crawler] {source_name} 搜索失败: {e}")
            return []

    async def _search_sources_parallel(self, query: str) -> List[Paper]:
        """使用 SearchOrchestrator 并行搜索多个源

        核心优化：将串行搜索改为并行搜索，显著减少搜索时间。
        """
        try:
            # 延迟导入避免循环依赖
            from ...search.search_orchestrator import (
                SearchOrchestrator,
                SearchConfig,
                SearchStrategy,
            )
            from ...search.openalex_searcher import OpenAlexSearcher
            from ...search.arxiv_searcher import ArxivSearcher
            from ...search.semantic_scholar_searcher import SemanticScholarSearcher

            # 创建搜索器映射
            searchers = {}
            for source in self.sources:
                searcher = SearchFactory.get(source)
                if searcher:
                    searchers[source] = searcher

            if not searchers:
                logger.warning("[Crawler] 没有可用的搜索源")
                return []

            # 创建编排器
            orchestrator = SearchOrchestrator(searchers)

            # 并行搜索
            config = SearchConfig(
                strategy=SearchStrategy.BALANCED,
                max_results_per_source=self.max_per_source,
                enable_cache=True,
            )

            results = await orchestrator.search(query, config)

            # 转换为 Paper 对象
            papers = []
            for r in results:
                papers.append(Paper(
                    id=r.paper_id or f"paper_{hash(r.title)}",
                    title=r.title,
                    authors=r.authors or [],
                    abstract=r.abstract or "",
                    url=r.url or "",
                    year=r.year or 2024,
                    citations=r.citations or 0,
                    venue=r.venue or "",
                ))

            logger.info(f"[Crawler] 并行搜索返回 {len(papers)} 篇论文")
            return papers

        except ImportError as e:
            logger.warning(f"[Crawler] 并行搜索模块导入失败: {e}")
            return []
        except Exception as e:
            logger.error(f"[Crawler] 并行搜索失败: {e}")
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
        """LangGraph 节点入口"""
        query = state.user_query
        logger.info(f"[Crawler] 开始爬取论文: {query}")
        start = time.time()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            # 尝试使用增强检索
            if self.enable_enhanced_retrieval and self.retriever and self.llm:
                pipeline = self._get_enhanced_pipeline()
                if pipeline:
                    final_papers = loop.run_until_complete(
                        self._search_via_enhanced_async(query)
                    )
                else:
                    final_papers = loop.run_until_complete(
                        self._search_basic_async(query)
                    )
            else:
                final_papers = loop.run_until_complete(
                    self._search_basic_async(query)
                )
        except Exception as e:
            logger.error(f"[Crawler] 搜索失败: {e}")
            final_papers = []

        elapsed = time.time() - start
        logger.info(f"[Crawler] 完成，共找到 {len(final_papers)} 篇论文，耗时 {elapsed:.2f}s")

        state.papers = final_papers
        state.current_phase = "select"
        return state

    async def _search_basic_async(self, query: str) -> List[Paper]:
        """异步基础搜索：并行搜索 + 并行扩展"""
        try:
            # 使用并行搜索
            papers = await self._search_sources_parallel(query)
            if not papers:
                return []
        except Exception as e:
            logger.debug(f"[Crawler] 并行搜索失败，回退: {e}")
            papers = []

        if not papers:
            return []

        # 异步扩展引用
        papers = await self._expand_via_citations_async(papers)

        # 去重
        seen = set()
        final_papers = []
        for p in papers:
            if p.id not in seen:
                seen.add(p.id)
                final_papers.append(p)

        return final_papers

    async def _search_via_enhanced_async(self, query: str) -> List[Paper]:
        """异步增强检索"""
        from ...retrieval.enhanced_retrieval_pipeline import enhanced_retrieve

        try:
            result = await enhanced_retrieve(
                query=query,
                retriever=self.retriever,
                llm=self.llm,
                top_k=20,
                enable_all_optimizations=True,
            )
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
            logger.error(f"[Crawler] 增强检索失败: {e}")
            return []

    def _search_basic(self, query: str) -> List[Paper]:
        """基础多源并行搜索"""
        try:
            # 尝试使用并行搜索
            papers = asyncio.get_event_loop().run_until_complete(
                self._search_sources_parallel(query)
            )
            if papers:
                return papers
        except Exception as e:
            logger.debug(f"[Crawler] 并行搜索回退到串行: {e}")

        # 回退到串行搜索
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

        return unique_papers

    async def _expand_via_citations_async(self, papers: List[Paper], max_per_paper: int = 5) -> List[Paper]:
        """异步扩展引用网络"""
        if not papers:
            return []

        all_papers = list(papers)
        seen_ids = {p.id for p in papers}
        top_by_citations = sorted(papers, key=lambda p: p.citations, reverse=True)[:3]

        # 并行获取每篇高引用论文的引用
        semaphore = asyncio.Semaphore(2)

        async def fetch_citations(paper: Paper) -> List[Paper]:
            async with semaphore:
                try:
                    ss_searcher = SearchFactory.get("semantic_scholar")
                    if ss_searcher is None:
                        return []

                    response = await ss_searcher.search(paper.title, max_results=max_per_paper)
                    new_papers = []
                    for result in response.results:
                        if result.paper_id not in seen_ids:
                            seen_ids.add(result.paper_id)
                            new_papers.append(self._search_result_to_paper(result))
                    return new_papers
                except Exception as e:
                    logger.debug(f"[Crawler] 扩展引用失败: {e}")
                    return []

        # 并行执行
        tasks = [fetch_citations(p) for p in top_by_citations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)

        return all_papers
