"""多源搜索编排器"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.search.base import (
    BaseSearchAdapter,
    SearchErrorInfo,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from src.agents_v3.research_workspace.search.cache import SearchCache
from src.agents_v3.research_workspace.search.merger import SearchResultMerger
from src.agents_v3.research_workspace.search.rate_limit import RateManager
from src.agents_v3.research_workspace.search.ranking import RankingService


class SearchOrchestrator:
    """多源搜索编排器"""

    def __init__(
        self,
        adapters: dict[str, BaseSearchAdapter],
        rate_manager: RateManager | None = None,
        cache: SearchCache | None = None,
        merger: SearchResultMerger | None = None,
        ranking: RankingService | None = None,
    ):
        self.adapters = adapters
        self.rate_manager = rate_manager or RateManager()
        self.cache = cache or SearchCache()
        self.merger = merger or SearchResultMerger()
        self.ranking = ranking or RankingService()

    def search(self, query: SearchQuery) -> SearchResponse:
        """执行多源搜索"""
        start = time.time()
        errors: list[SearchErrorInfo] = []
        source_stats: dict[str, dict[str, Any]] = {}

        # Cache check
        if query.use_cache and not query.force_refresh:
            cache_key = SearchCache.make_key(
                query.query, query.sources, query.limit,
                query.year_from, query.year_to, query.field,
            )
            cached = self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for query: {query.query[:50]}")
                resp = SearchResponse(**cached)
                resp.cache_hit = True
                return resp

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

        # Search each source
        all_results: list[SearchResult] = []
        for source_name, adapter in active_adapters.items():
            source_start = time.time()

            # Rate limit
            if not self.rate_manager.is_available(source_name):
                errors.append(SearchErrorInfo(
                    source=source_name,
                    category="RATE_LIMIT",
                    message=f"Source {source_name} is temporarily unavailable",
                    retryable=True,
                ))
                source_stats[source_name] = {"success": False, "count": 0, "error": "rate_limited"}
                continue

            try:
                self.rate_manager.acquire(source_name)
                results = adapter.search(query)
                self.rate_manager.record_success(source_name)

                elapsed = int((time.time() - source_start) * 1000)
                source_stats[source_name] = {"success": True, "count": len(results), "elapsed_ms": elapsed}
                all_results.extend(results)

            except Exception as e:
                self.rate_manager.record_error(source_name)
                elapsed = int((time.time() - source_start) * 1000)
                errors.append(SearchErrorInfo(
                    source=source_name,
                    category="NETWORK_ERROR",
                    message=str(e),
                    retryable=True,
                ))
                source_stats[source_name] = {"success": False, "count": 0, "elapsed_ms": elapsed, "error": str(e)}
                logger.error(f"Source {source_name} failed: {e}")

        # Merge and dedup
        merged = self.merger.merge(all_results)

        # Rank (pass query for relevance scoring)
        ranked = self.ranking.rank(merged, query=query.query)

        total_elapsed = int((time.time() - start) * 1000)

        response = SearchResponse(
            query=query,
            results=ranked,
            source_stats=source_stats,
            errors=errors,
            cache_hit=False,
            elapsed_ms=total_elapsed,
        )

        # Write cache
        if query.use_cache:
            cache_key = SearchCache.make_key(
                query.query, query.sources, query.limit,
                query.year_from, query.year_to, query.field,
            )
            ttl = SearchCache.get_ttl_for_query(query.query, query.sources)
            self.cache.set(cache_key, response.model_dump(), ttl=ttl)

        logger.info(f"Search complete: {len(ranked)} results from {len(active_adapters)} sources in {total_elapsed}ms")
        return response
