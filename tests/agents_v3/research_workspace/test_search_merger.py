"""搜索结果合并器测试"""

import pytest

from src.agents_v3.research_workspace.search.base import SearchResult
from src.agents_v3.research_workspace.search.merger import SearchResultMerger


@pytest.fixture
def merger():
    return SearchResultMerger()


class TestSearchResultMerger:
    def test_empty_input(self, merger):
        assert merger.merge([]) == []

    def test_single_result_unchanged(self, merger):
        r = SearchResult(title="Test", source="arxiv")
        result = merger.merge([r])
        assert len(result) == 1
        assert result[0].title == "Test"

    def test_same_doi_merges(self, merger):
        r1 = SearchResult(title="Paper A", doi="10.1234/a", source="openalex", abstract="Short")
        r2 = SearchResult(title="Paper A", doi="10.1234/a", source="arxiv", abstract="Longer abstract text here")
        result = merger.merge([r1, r2])
        assert len(result) == 1
        # Should take longer abstract
        assert "Longer" in result[0].abstract

    def test_same_arxiv_id_merges(self, merger):
        r1 = SearchResult(title="Paper A", arxiv_id="2401.00001", source="arxiv")
        r2 = SearchResult(title="Paper A", arxiv_id="2401.00001v2", source="arxiv")
        result = merger.merge([r1, r2])
        assert len(result) == 1

    def test_different_papers_no_merge(self, merger):
        r1 = SearchResult(title="Paper A", doi="10.1234/a", source="arxiv")
        r2 = SearchResult(title="Paper B", doi="10.1234/b", source="arxiv")
        result = merger.merge([r1, r2])
        assert len(result) == 2

    def test_pdf_url_prefers_arxiv(self, merger):
        r1 = SearchResult(title="Paper", doi="10.1234/a", source="openalex", pdf_url="http://openalex.pdf")
        r2 = SearchResult(title="Paper", doi="10.1234/a", source="arxiv", pdf_url="http://arxiv.pdf")
        result = merger.merge([r1, r2])
        assert result[0].pdf_url == "http://arxiv.pdf"

    def test_citations_takes_max(self, merger):
        r1 = SearchResult(title="Paper", doi="10.1234/a", source="openalex", citations=10)
        r2 = SearchResult(title="Paper", doi="10.1234/a", source="arxiv", citations=50)
        result = merger.merge([r1, r2])
        assert result[0].citations == 50
