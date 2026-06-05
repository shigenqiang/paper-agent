"""多源搜索编排器"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.search.base import (
    BaseSearchAdapter,
    SearchErrorInfo,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from src.agents_v3.research_workspace.search.merger import SearchResultMerger
from src.agents_v3.research_workspace.search.rate_limit import RateManager


class SearchCache:
    """内存 LRU + TTL 搜索缓存"""

    def __init__(self, max_entries: int = 256, ttl: int = 3600):
        self.max_entries = max_entries
        self.ttl = ttl
        self._store: OrderedDict[str, tuple[float, SearchResponse]] = OrderedDict()
        self._lock = Lock()

    @staticmethod
    def _make_key(query: SearchQuery) -> str:
        raw = f"{query.query}|{query.sources}|{query.limit}|{query.offset}|{query.year_from}|{query.year_to}|{query.field}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, query: SearchQuery) -> SearchResponse | None:
        key = self._make_key(query)
        with self._lock:
            if key not in self._store:
                return None
            ts, resp = self._store[key]
            if time.time() - ts > self.ttl:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            cached = resp.model_copy()
            cached.cache_hit = True
            return cached

    def put(self, query: SearchQuery, response: SearchResponse) -> None:
        key = self._make_key(query)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (time.time(), response)
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)


class SearchOrchestrator:
    """多源搜索编排器"""

    def __init__(
        self,
        adapters: dict[str, BaseSearchAdapter],
        rate_manager: RateManager | None = None,
        merger: SearchResultMerger | None = None,
        cache: SearchCache | None = None,
    ):
        self.adapters = adapters
        self.rate_manager = rate_manager or RateManager()
        self.merger = merger or SearchResultMerger()
        self.cache = cache

    def _search_single_source(
        self, source_name: str, adapter: BaseSearchAdapter, query: SearchQuery
    ) -> tuple[list[SearchResult], SearchErrorInfo | None, dict[str, dict[str, Any]]]:
        """搜索单个源（线程安全）"""
        source_start = time.time()

        if not self.rate_manager.is_available(source_name):
            return (
                [],
                SearchErrorInfo(
                    source=source_name,
                    category="RATE_LIMIT",
                    message=f"Source {source_name} is temporarily unavailable",
                    retryable=True,
                ),
                {source_name: {"success": False, "count": 0, "error": "rate_limited"}},
            )

        try:
            self.rate_manager.acquire(source_name)
            results = adapter.search(query)
            self.rate_manager.record_success(source_name)
            elapsed = int((time.time() - source_start) * 1000)
            return (
                results,
                None,
                {source_name: {"success": True, "count": len(results), "elapsed_ms": elapsed}},
            )
        except Exception as e:
            self.rate_manager.record_error(source_name)
            elapsed = int((time.time() - source_start) * 1000)
            logger.error(f"Source {source_name} failed: {e}")
            return (
                [],
                SearchErrorInfo(
                    source=source_name,
                    category="NETWORK_ERROR",
                    message=str(e),
                    retryable=True,
                ),
                {source_name: {"success": False, "count": 0, "elapsed_ms": elapsed, "error": str(e)}},
            )

    def search(self, query: SearchQuery) -> SearchResponse:
        """执行多源搜索"""
        # 检查缓存
        if self.cache and query.use_cache and not query.force_refresh:
            cached = self.cache.get(query)
            if cached:
                logger.info(f"Search cache hit for: {query.query}")
                return cached

        start = time.time()
        errors: list[SearchErrorInfo] = []
        source_stats: dict[str, dict[str, Any]] = {}

        # Select adapters
        sources = query.sources or list(self.adapters.keys())
        active_adapters = {s: self.adapters[s] for s in sources if s in self.adapters}

        if not active_adapters:
            errors.append(SearchErrorInfo(
                source="orchestrator",
                category="API_ERROR",
                message=f"No adapters found for sources: {sources}",
                retryable=False,
            ))
            return SearchResponse(query=query, errors=errors)

        # Search each source in parallel
        all_results: list[SearchResult] = []
        with ThreadPoolExecutor(max_workers=len(active_adapters)) as executor:
            futures = {
                executor.submit(self._search_single_source, name, adapter, query): name
                for name, adapter in active_adapters.items()
            }
            for future in as_completed(futures):
                src_results, error, stats = future.result()
                all_results.extend(src_results)
                if error:
                    errors.append(error)
                source_stats.update(stats)

        # Merge and dedup
        merged = self.merger.merge(all_results)

        total_elapsed = int((time.time() - start) * 1000)

        response = SearchResponse(
            query=query,
            results=merged,
            source_stats=source_stats,
            errors=errors,
            cache_hit=False,
            elapsed_ms=total_elapsed,
        )

        # 写入缓存
        if self.cache and not errors:
            self.cache.put(query, response)

        logger.info(f"Search complete: {len(merged)} results from {len(active_adapters)} sources in {total_elapsed}ms")
        return response
