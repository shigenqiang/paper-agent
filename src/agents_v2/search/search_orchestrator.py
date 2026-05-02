"""
Search Orchestrator - 搜索编排器

协调多个搜索器，实现智能搜索策略。
"""

from src.agents_v2.logging_config import get_logging_logger

import asyncio

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any

from .base_searcher import SearchResult, SearchResponse
from .search_result_merger import SearchResultMerger, MergeConfig, MergedSearchResult
from .rate_manager import RateManager, get_rate_manager
from .cache_manager import get_cache_manager, CacheConfig

logger = get_logging_logger(__name__)


class SearchStrategy(Enum):
    """搜索策略"""
    FAST = "fast"                    # 快速 - 只用最快
    BALANCED = "balanced"           # 平衡 - 覆盖与速度兼顾
    COMPREHENSIVE = "comprehensive" # 全面 - 多源聚合
    PRECISE = "precise"             # 精准 - 多重验证


@dataclass
class SearchConfig:
    """搜索配置"""
    strategy: SearchStrategy = SearchStrategy.BALANCED
    max_results_per_source: int = 10
    max_total_results: int = 50
    timeout_per_source: float = 10.0
    enable_cache: bool = True
    cache_ttl: int = 3600
    merge_config: Optional[MergeConfig] = None


@dataclass
class OrchestratorConfig:
    """编排器配置"""
    enable_parallel: bool = True
    max_parallel_sources: int = 3
    fail_fast: bool = False
    partial_results_on_error: bool = True


class SearchOrchestrator:
    """搜索编排器 - 协调多个搜索源"""

    # 默认搜索源优先级
    DEFAULT_SOURCE_ORDER = [
        "openalex",      # 免费、数据全面
        "arxiv",         # CS/物理预印本
        "semantic_scholar",  # 有引用分析
        "crossref",      # 元数据
        "pubmed",        # 生物医学
    ]

    def __init__(
        self,
        searchers: Dict[str, Any] = None,
        config: Optional[OrchestratorConfig] = None,
        rate_manager: RateManager = None,
        merge_config: Optional[MergeConfig] = None
    ):
        self.searchers = searchers or {}
        self.config = config or OrchestratorConfig()
        self.rate_manager = rate_manager or get_rate_manager()
        self.merger = SearchResultMerger(merge_config)
        self.cache_manager = get_cache_manager()

    def register_searcher(self, name: str, searcher: Any):
        """注册搜索器"""
        self.searchers[name] = searcher
        logger.info(f"Registered searcher: {name}")

    def unregister_searcher(self, name: str):
        """取消注册搜索器"""
        if name in self.searchers:
            del self.searchers[name]
            logger.info(f"Unregistered searcher: {name}")

    async def search(
        self,
        query: str,
        config: Optional[SearchConfig] = None,
        sources: List[str] = None
    ) -> List[MergedSearchResult]:
        """执行搜索

        Args:
            query: 搜索查询
            config: 搜索配置
            sources: 指定搜索源（覆盖策略）

        Returns:
            合并排序后的搜索结果
        """
        config = config or SearchConfig()

        # 选择搜索源
        if sources:
            active_sources = sources
        else:
            active_sources = self._select_sources(config.strategy)

        logger.info(f"Searching '{query}' with strategy {config.strategy.value}")
        logger.info(f"Active sources: {active_sources}")

        # 并行执行多个搜索
        responses = await self._search_parallel(
            active_sources,
            query,
            config
        )

        # 合并结果
        merged = await self._merge_results(responses, config)

        # 限制结果数量
        return merged[:config.max_total_results]

    def _select_sources(self, strategy: SearchStrategy) -> List[str]:
        """根据策略选择搜索源"""
        all_sources = list(self.searchers.keys())

        if strategy == SearchStrategy.FAST:
            # 只用最快最可靠的源
            return ["openalex", "arxiv"]

        elif strategy == SearchStrategy.BALANCED:
            # 平衡策略：核心源 + 1-2个扩展源
            return ["openalex", "arxiv", "semantic_scholar"]

        elif strategy == SearchStrategy.COMPREHENSIVE:
            # 全面策略：所有源
            return all_sources

        elif strategy == SearchStrategy.PRECISE:
            # 精准策略：先去重，再扩展
            return ["openalex", "crossref", "semantic_scholar"]

        return all_sources

    async def _search_parallel(
        self,
        sources: List[str],
        query: str,
        config: SearchConfig
    ) -> List[SearchResponse]:
        """并行执行多个搜索"""
        tasks = []
        semaphore = asyncio.Semaphore(self.config.max_parallel_sources)

        async def search_with_semaphore(source: str) -> Optional[SearchResponse]:
            async with semaphore:
                searcher = self.searchers.get(source)
                if not searcher:
                    logger.warning(f"Searcher {source} not found")
                    return None

                try:
                    # 使用缓存
                    if config.enable_cache:
                        result = await self._search_with_cache(
                            source, query, config.max_results_per_source, searcher
                        )
                    else:
                        # 带超时的搜索
                        result = await asyncio.wait_for(
                            searcher.search(query, config.max_results_per_source),
                            timeout=config.timeout_per_source
                        )
                    return result

                except asyncio.TimeoutError:
                    logger.warning(f"{source} search timeout")
                    return None

                except Exception as e:
                    logger.error(f"{source} search failed: {e}")
                    if self.config.fail_fast:
                        raise
                    return None

        # 创建所有搜索任务
        for source in sources:
            tasks.append(search_with_semaphore(source))

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤失败的结果
        responses = []
        for i, result in enumerate(results):
            source = sources[i] if i < len(sources) else "unknown"
            if isinstance(result, SearchResponse):
                responses.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Search exception for {source}: {result}")
                if not self.config.partial_results_on_error:
                    raise

        return responses

    async def _search_with_cache(
        self,
        source: str,
        query: str,
        max_results: int,
        searcher: Any
    ) -> SearchResponse:
        """使用缓存的搜索"""
        cache_key = f"{source}:{query}:{max_results}"

        # 尝试从缓存获取
        cached = await self.cache_manager.cache.get(source, query, max_results)
        if cached is not None:
            logger.debug(f"Cache hit for {source}: {query[:30]}...")
            return cached

        # 执行搜索
        result = await searcher.search(query, max_results)

        # 缓存结果
        if result and not result.error:
            await self.cache_manager.cache.set(
                source, query, max_results, result, ttl=config.cache_ttl
            )

        return result

    async def _merge_results(
        self,
        responses: List[SearchResponse],
        config: SearchConfig
    ) -> List[MergedSearchResult]:
        """合并搜索结果"""
        if not responses:
            return []

        merge_config = config.merge_config or MergeConfig()
        return self.merger.merge(responses)

    async def search_by_doi(
        self,
        doi: str,
        sources: List[str] = None
    ) -> Optional[MergedSearchResult]:
        """根据DOI搜索论文

        Args:
            doi: DOI标识
            sources: 搜索源列表

        Returns:
            MergedSearchResult or None
        """
        responses = []
        sources = sources or list(self.searchers.keys())

        for source in sources:
            searcher = self.searchers.get(source)
            if not searcher:
                continue

            try:
                result = await searcher.search(f"doi:{doi}", max_results=1)
                if result.results:
                    responses.append(result)
            except Exception as e:
                logger.warning(f"Search by DOI failed for {source}: {e}")

        if not responses:
            return None

        merged = await self._merge_results(responses, SearchConfig())
        return merged[0] if merged else None

    async def get_paper_details(
        self,
        paper_id: str,
        source: str = None
    ) -> Optional[SearchResult]:
        """获取论文详情

        Args:
            paper_id: 论文ID
            source: 指定源（不指定则尝试所有）

        Returns:
            SearchResult or None
        """
        sources = [source] if source else list(self.searchers.keys())

        for src in sources:
            searcher = self.searchers.get(src)
            if not searcher or not hasattr(searcher, 'get_paper'):
                continue

            try:
                result = await searcher.get_paper(paper_id)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Get paper failed for {src}: {e}")

        return None

    def get_available_sources(self) -> List[Dict]:
        """获取可用搜索源信息"""
        sources = []
        for name, searcher in self.searchers.items():
            stats = self.rate_manager.get_stats(name)
            sources.append({
                "name": name,
                "available": True,
                "requests_last_hour": stats.get("requests_last_hour", 0),
                "in_backoff": stats.get("in_backoff", False),
            })
        return sources

    async def health_check(self) -> Dict[str, bool]:
        """检查所有搜索源的健康状态"""
        results = {}
        for name, searcher in self.searchers.items():
            try:
                if hasattr(searcher, 'health_check'):
                    results[name] = await searcher.health_check()
                else:
                    # 简单测试搜索
                    result = await searcher.search("test", max_results=1)
                    results[name] = result.error == "" or len(result.results) >= 0
            except Exception:
                results[name] = False
        return results

    async def invalidate_cache(self, source: str = None):
        """使缓存失效"""
        if source:
            await self.cache_manager.invalidate_source(source)
        else:
            await self.cache_manager.clear_all()

    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return self.cache_manager.get_stats()

    def get_rate_stats(self) -> Dict[str, Dict]:
        """获取频率限制统计"""
        return self.rate_manager.get_all_stats()


# 便捷函数
_orchestrator: Optional[SearchOrchestrator] = None


def get_orchestrator(
    searchers: Dict[str, Any] = None,
    config: OrchestratorConfig = None
) -> SearchOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SearchOrchestrator(searchers, config)
    elif searchers:
        # 更新搜索器
        for name, searcher in searchers.items():
            _orchestrator.register_searcher(name, searcher)
    return _orchestrator


async def quick_search(
    query: str,
    strategy: SearchStrategy = SearchStrategy.BALANCED,
    max_results: int = 20
) -> List[MergedSearchResult]:
    """快速搜索 - 使用默认编排器"""
    orchestrator = get_orchestrator()
    config = SearchConfig(
        strategy=strategy,
        max_total_results=max_results,
        max_results_per_source=max_results // 3
    )
    return await orchestrator.search(query, config)