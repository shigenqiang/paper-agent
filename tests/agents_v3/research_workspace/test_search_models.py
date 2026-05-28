"""搜索模型测试"""

import pytest

from src.agents_v3.research_workspace.search.base import (
    SearchErrorInfo,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchSession,
)


class TestSearchQuery:
    def test_default_values(self):
        q = SearchQuery(query="test")
        assert q.limit == 20
        assert q.sources == ["openalex", "arxiv"]
        assert q.use_cache is True
        assert q.force_refresh is False

    def test_custom_values(self):
        q = SearchQuery(
            query="LLM",
            sources=["arxiv"],
            limit=10,
            year_from=2023,
            require_pdf=True,
        )
        assert q.sources == ["arxiv"]
        assert q.year_from == 2023
        assert q.require_pdf is True


class TestSearchResult:
    def test_auto_result_id(self):
        r = SearchResult(title="Test")
        assert r.result_id.startswith("sr_")

    def test_default_scores(self):
        r = SearchResult(title="Test")
        assert r.relevance_score == 0.0
        assert r.quality_score == 0.0
        assert r.final_score == 0.0

    def test_model_dump_roundtrip(self):
        r = SearchResult(title="Test", authors=["Alice"], year=2024, doi="10.1234/test")
        data = r.model_dump()
        r2 = SearchResult(**data)
        assert r2.title == r.title
        assert r2.doi == r.doi


class TestSearchResponse:
    def test_empty_response(self):
        q = SearchQuery(query="test")
        resp = SearchResponse(query=q)
        assert resp.results == []
        assert resp.cache_hit is False
        assert resp.elapsed_ms == 0


class TestSearchSession:
    def test_auto_session_id(self):
        s = SearchSession(project_id="proj1")
        assert s.session_id.startswith("ss_")
        assert s.status == "pending"


class TestSearchErrorInfo:
    def test_default_category(self):
        e = SearchErrorInfo(source="arxiv", message="timeout")
        assert e.category == "UNKNOWN"
        assert e.retryable is True
