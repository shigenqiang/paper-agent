"""缓存模块 - 搜索结果和报告缓存"""
from .report_cache import (
    CacheEntry,
    MemoryCache,
    CacheDecorator,
    SearchResultCache,
    ReportCache,
    get_search_cache,
    get_report_cache
)

__all__ = [
    "CacheEntry",
    "MemoryCache",
    "CacheDecorator",
    "SearchResultCache",
    "ReportCache",
    "get_search_cache",
    "get_report_cache",
]
