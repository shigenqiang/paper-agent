"""搜索暂存和提交流程测试"""

import pytest

from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.search.base import (
    BaseSearchAdapter,
    SearchQuery,
    SearchResult,
)


class MockAdapter(BaseSearchAdapter):
    def __init__(self):
        self._results = [
            SearchResult(title="Paper A", authors=["Alice"], doi="10.1/a", source="mock"),
            SearchResult(title="Paper B", authors=["Bob"], arxiv_id="2401.00001", source="mock"),
            SearchResult(title="Paper C", authors=["Charlie"], source="mock"),
        ]

    @property
    def source_name(self) -> str:
        return "mock"

    def search(self, query: SearchQuery) -> list[SearchResult]:
        return self._results[:query.limit]


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.storage._storage", None
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.paper_library.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return PaperLibraryService(search_adapters=[MockAdapter()])


class TestSearchSession:
    def test_search_candidates_creates_session(self, service):
        q = SearchQuery(query="test")
        session = service.search_candidates("proj1", q)
        assert session.session_id.startswith("ss_")
        assert len(session.results) == 3
        assert session.status == "pending"

    def test_get_search_session(self, service):
        q = SearchQuery(query="test")
        session = service.search_candidates("proj1", q)
        found = service.get_search_session(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_list_search_sessions(self, service):
        service.search_candidates("proj1", SearchQuery(query="a"))
        service.search_candidates("proj1", SearchQuery(query="b"))
        sessions = service.list_search_sessions("proj1")
        assert len(sessions) == 2

    def test_commit_search_results(self, service):
        q = SearchQuery(query="test")
        session = service.search_candidates("proj1", q)
        result_ids = [session.results[0].result_id, session.results[1].result_id]
        papers = service.commit_search_results("proj1", session.session_id, result_ids)
        assert len(papers) == 2

        # Session should be committed
        updated = service.get_search_session(session.session_id)
        assert updated.status == "committed"

    def test_commit_only_selected(self, service):
        q = SearchQuery(query="test")
        session = service.search_candidates("proj1", q)
        # Only commit first result
        papers = service.commit_search_results("proj1", session.session_id, [session.results[0].result_id])
        assert len(papers) == 1
        # Project should have only 1 paper
        assert len(service.list_papers("proj1")) == 1

    def test_commit_with_invalid_session(self, service):
        papers = service.commit_search_results("proj1", "nonexistent", ["r1"])
        assert papers == []
