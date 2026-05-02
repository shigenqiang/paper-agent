"""
Search模块 - 学术论文搜索

提供多源学术搜索功能。
"""
from .base_searcher import BaseSearcher, SearchResult, SearchResponse
from .arxiv_searcher import ArxivSearcher
from .pubmed_searcher import PubmedSearcher
from .semantic_scholar_searcher import SemanticScholarSearcher
from .openalex_searcher import OpenAlexSearcher
from .search_factory import SearchFactory, get_searcher, search_all
from .query_parser import QueryParser, QueryIntent, ParsedQuery, parse_query
from .search_result_merger import (
    SearchResultMerger,
    MergedSearchResult,
    MergeConfig,
    merge_search_results,
    deduplicate_by_doi,
)

# 新增模块
from .rate_manager import RateManager, get_rate_manager, PlatformConfig
from .enhanced_base_searcher import EnhancedBaseSearcher, RetryConfig
from .cache_manager import SearchCache, SearchCacheManager, get_cache_manager, CacheConfig, cached_search
from .search_orchestrator import (
    SearchOrchestrator,
    SearchStrategy,
    SearchConfig,
    OrchestratorConfig,
    get_orchestrator,
    quick_search,
)
from .strategies import (
    SearchScenario,
    ScenarioConfig,
    get_search_config,
    get_orchestrator_config,
    get_sources_for_scenario,
    search_for_scenario,
)

__all__ = [
    # 基类
    "BaseSearcher",
    "SearchResult",
    "SearchResponse",

    # 搜索器
    "ArxivSearcher",
    "PubmedSearcher",
    "SemanticScholarSearcher",
    "OpenAlexSearcher",

    # 工厂
    "SearchFactory",
    "get_searcher",
    "search_all",

    # 查询解析
    "QueryParser",
    "QueryIntent",
    "ParsedQuery",
    "parse_query",

    # 结果合并与排序
    "SearchResultMerger",
    "MergedSearchResult",
    "MergeConfig",
    "merge_search_results",
    "deduplicate_by_doi",

    # 频率管理
    "RateManager",
    "get_rate_manager",
    "PlatformConfig",

    # 增强基类
    "EnhancedBaseSearcher",
    "RetryConfig",

    # 缓存
    "SearchCache",
    "SearchCacheManager",
    "get_cache_manager",
    "CacheConfig",
    "cached_search",

    # 编排器
    "SearchOrchestrator",
    "SearchStrategy",
    "SearchConfig",
    "OrchestratorConfig",
    "get_orchestrator",
    "quick_search",

    # 策略
    "SearchScenario",
    "ScenarioConfig",
    "get_search_config",
    "get_orchestrator_config",
    "get_sources_for_scenario",
    "search_for_scenario",
]
