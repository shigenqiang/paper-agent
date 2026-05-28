"""搜索编排器测试"""

import pytest

from src.agents_v3.research_workspace.search.base import (
    BaseSearchAdapter,
    SearchQuery,
    SearchResult,
)
from src.agents_v3.research_workspace.search.cache import SearchCache
from src.agents_v3.research_workspace.search.merger import SearchResultMerger
from src.agents_v3.research_workspace.search.orchestrator import SearchOrchestrator
from src.agents_v3.research_workspace.search.rate_limit import RateManager
from src.agents_v3.research_workspace.search.ranking import RankingService


class MockAdapter(BaseSearchAdapter):
    def __init__(self, name: str, results: list[SearchResult] | None = None, fail: bool = False):
        self._name = name
        self._results = results or []
        self._fail = fail
        self.call_count = 0

    @property
    def source_name(self) -> str:
        return self._name

    def search(self, query: SearchQuery) -> list[SearchResult]:
        self.call_count += 1
        if self._fail:
            raise RuntimeError(f"{self._name} is down")
        return self._results[:query.limit]


@pytest.fixture
def orchestrator():
    adapters = {
        "openalex": MockAdapter("openalex", [
            SearchResult(title="Paper A", doi="10.1/a", source="openalex"),
            SearchResult(title="Paper B", doi="10.1/b", source="openalex"),
        ]),
        "arxiv": MockAdapter("arxiv", [
            SearchResult(title="Paper A", doi="10.1/a", source="arxiv"),
            SearchResult(title="Paper C", arxiv_id="2401.00001", source="arxiv"),
        ]),
    }
    return SearchOrchestrator(
        adapters=adapters,
        rate_manager=RateManager(),
        cache=SearchCache(),
        merger=SearchResultMerger(),
        ranking=RankingService(),
    )


class TestSearchOrchestrator:
    def test_search_returns_results(self, orchestrator):
        q = SearchQuery(query="test", sources=["openalex", "arxiv"])
        resp = orchestrator.search(q)
        assert len(resp.results) > 0
        assert resp.elapsed_ms >= 0

    def test_search_merges_duplicates(self, orchestrator):
        q = SearchQuery(query="test", sources=["openalex", "arxiv"])
        resp = orchestrator.search(q)
        # Paper A appears in both sources, should be merged
        dois = [r.doi for r in resp.results]
        assert dois.count("10.1/a") == 1

    def test_search_records_source_stats(self, orchestrator):
        q = SearchQuery(query="test", sources=["openalex", "arxiv"])
        resp = orchestrator.search(q)
        assert "openalex" in resp.source_stats
        assert "arxiv" in resp.source_stats

    def test_search_handles_adapter_failure(self):
        adapters = {
            "good": MockAdapter("good", [SearchResult(title="OK", source="good")]),
            "bad": MockAdapter("bad", fail=True),
        }
        orch = SearchOrchestrator(adapters=adapters, rate_manager=RateManager())
        q = SearchQuery(query="test", sources=["good", "bad"])
        resp = orch.search(q)
        assert len(resp.results) == 1
        assert len(resp.errors) == 1
        assert resp.errors[0].source == "bad"

    def test_search_cache_hit(self, orchestrator):
        q = SearchQuery(query="test", sources=["openalex"], use_cache=True)
        resp1 = orchestrator.search(q)
        assert resp1.cache_hit is False
        resp2 = orchestrator.search(q)
        assert resp2.cache_hit is True

    def test_search_no_adapters_returns_error(self):
        orch = SearchOrchestrator(adapters={})
        q = SearchQuery(query="test", sources=["nonexistent"])
        resp = orch.search(q)
        assert len(resp.errors) > 0
