"""搜索集成测试（使用 mock adapter）"""

import pytest

from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchQuery, SearchResult


class MockSearchAdapter(BaseSearchAdapter):
    """测试用搜索适配器"""

    def __init__(self, results: list[SearchResult] | None = None):
        self._results = results or []
        self.call_count = 0

    @property
    def source_name(self) -> str:
        return "mock"

    def search(self, query: SearchQuery) -> list[SearchResult]:
        self.call_count += 1
        return self._results[:query.limit]


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.storage._global_storage", None
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.paper_library.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return PaperLibraryService()


@pytest.fixture
def mock_adapter():
    return MockSearchAdapter(results=[
        SearchResult(
            title="Paper A",
            authors=["Alice"],
            year=2024,
            doi="10.1234/a",
            source="mock",
        ),
        SearchResult(
            title="Paper B",
            authors=["Bob"],
            year=2023,
            arxiv_id="2401.00001",
            source="mock",
        ),
        SearchResult(
            title="Paper C",
            authors=["Charlie"],
            source="mock",
        ),
    ])


class TestSearchIntegration:
    def test_search_papers_calls_adapter(self, service, mock_adapter):
        service.search_adapters = [mock_adapter]
        results = service.search_papers(SearchQuery(query="test"))
        assert len(results) == 3
        assert mock_adapter.call_count == 1

    def test_search_and_import_creates_papers(self, service, mock_adapter):
        service.search_adapters = [mock_adapter]
        papers = service.search_and_import("proj1", SearchQuery(query="test"))
        assert len(papers) == 3
        assert service.list_papers("proj1") == papers

    def test_search_dedup_skips_existing(self, service, mock_adapter):
        # First import
        service.search_adapters = [mock_adapter]
        papers1 = service.search_and_import("proj1", SearchQuery(query="test"))
        assert len(papers1) == 3

        # Second import with same results should be deduped
        papers2 = service.search_and_import("proj1", SearchQuery(query="test"))
        assert len(papers2) == 0

    def test_search_dedup_by_doi(self, service, mock_adapter):
        service.search_adapters = [mock_adapter]
        service.search_and_import("proj1", SearchQuery(query="test"))

        # Import same DOI via metadata should also be deduped
        result = service.add_paper_metadata("proj1", {
            "title": "Different Title",
            "doi": "10.1234/a",
        })
        assert result is None

    def test_search_dedup_by_arxiv_id(self, service, mock_adapter):
        service.search_adapters = [mock_adapter]
        service.search_and_import("proj1", SearchQuery(query="test"))

        result = service.add_paper_metadata("proj1", {
            "title": "Different Title",
            "arxiv_id": "2401.00001",
        })
        assert result is None

    def test_adapter_failure_doesnt_crash(self, service):
        class FailingAdapter(BaseSearchAdapter):
            @property
            def source_name(self):
                return "failing"
            def search(self, query):
                raise RuntimeError("API down")

        service.search_adapters = [FailingAdapter()]
        results = service.search_papers(SearchQuery(query="test"))
        assert results == []

    def test_search_respects_limit(self, service, mock_adapter):
        service.search_adapters = [mock_adapter]
        results = service.search_papers(SearchQuery(query="test", limit=1))
        assert len(results) == 1
