"""搜索去重测试 - 增强版"""

import pytest

from src.agents_v3.research_workspace.search.dedup import (
    DedupDecision,
    DedupService,
    _jaccard_similarity,
    build_existing_keys,
    first_author_key,
    is_duplicate,
    make_dedup_key,
    normalize_arxiv_id,
    normalize_author,
    normalize_doi,
    normalize_title,
)


class TestNormalizeDoi:
    def test_strips_prefix(self):
        assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"

    def test_strips_doi_prefix(self):
        assert normalize_doi("doi:10.1234/test") == "10.1234/test"

    def test_lowercases(self):
        assert normalize_doi("10.1234/TEST") == "10.1234/test"

    def test_strips_whitespace(self):
        assert normalize_doi("  10.1234/test  ") == "10.1234/test"


class TestNormalizeArxivId:
    def test_strips_version(self):
        assert normalize_arxiv_id("2401.00001v2") == "2401.00001"

    def test_strips_url_prefix(self):
        assert normalize_arxiv_id("https://arxiv.org/abs/2401.00001v1") == "2401.00001"

    def test_no_version_no_change(self):
        assert normalize_arxiv_id("2401.00001") == "2401.00001"


class TestNormalizeAuthor:
    def test_simple_name(self):
        result = normalize_author("John Smith")
        assert "smith" in result

    def test_last_first_format(self):
        result = normalize_author("Smith, John")
        assert "smith" in result


class TestFirstAuthorKey:
    def test_returns_first_author(self):
        key = first_author_key(["Alice Smith", "Bob Jones"])
        assert "smith" in key or "alice" in key.lower()

    def test_empty_list(self):
        assert first_author_key([]) == ""


class TestNormalizeTitle:
    def test_lowercases_and_strips(self):
        assert normalize_title("  Hello World  ") == "hello world"

    def test_removes_punctuation(self):
        assert normalize_title("AI: A Survey (2024)") == "ai a survey 2024"

    def test_collapses_whitespace(self):
        assert normalize_title("hello   world") == "hello world"


class TestMakeDedupKey:
    def test_doi_takes_priority(self):
        paper = {"doi": "10.1234/test", "arxiv_id": "2401.00001", "title": "X", "year": 2024}
        assert make_dedup_key(paper) == "doi:10.1234/test"

    def test_arxiv_id_second_priority(self):
        paper = {"doi": "", "arxiv_id": "2401.00001", "title": "X", "year": 2024}
        assert make_dedup_key(paper) == "arxiv:2401.00001"

    def test_title_year_author_third_priority(self):
        paper = {"doi": "", "arxiv_id": "", "title": "Test Paper", "year": 2024, "authors": ["Alice Smith"]}
        key = make_dedup_key(paper)
        assert key.startswith("tya:")

    def test_title_year_fallback(self):
        paper = {"doi": "", "arxiv_id": "", "title": "Test Paper", "year": 2024, "authors": []}
        assert make_dedup_key(paper) == "title_year:test paper|2024"

    def test_title_only_fallback(self):
        paper = {"doi": "", "arxiv_id": "", "title": "Test Paper", "year": None}
        assert make_dedup_key(paper) == "title:test paper"

    def test_empty_returns_none(self):
        assert make_dedup_key({"title": "", "year": None}) is None


class TestIsDuplicate:
    def test_detects_doi_dup(self):
        paper = {"doi": "10.1234/a"}
        existing = {"doi:10.1234/a", "doi:10.1234/b"}
        assert is_duplicate(paper, existing) is True

    def test_no_dup_returns_false(self):
        paper = {"doi": "10.1234/c"}
        existing = {"doi:10.1234/a", "doi:10.1234/b"}
        assert is_duplicate(paper, existing) is False


class TestBuildExistingKeys:
    def test_builds_from_paper_list(self):
        papers = [
            {"doi": "10.1234/a"},
            {"arxiv_id": "2401.00001"},
            {"title": "Test", "year": 2024},
        ]
        keys = build_existing_keys(papers)
        assert "doi:10.1234/a" in keys
        assert "arxiv:2401.00001" in keys


class TestJaccardSimilarity:
    def test_identical(self):
        assert _jaccard_similarity("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        assert _jaccard_similarity("hello world", "foo bar") == 0.0

    def test_partial_overlap(self):
        sim = _jaccard_similarity("hello world", "hello there")
        assert 0.0 < sim < 1.0


class TestDedupService:
    def test_detects_duplicate_doi(self):
        svc = DedupService()
        result = {"result_id": "r1", "doi": "10.1234/a", "title": "Test"}
        existing = [{"paper_id": "p1", "doi": "10.1234/a", "title": "Test"}]
        decision = svc.check_against_existing(result, existing)
        assert decision.action == "duplicate"
        assert decision.matched_paper_id == "p1"

    def test_new_result(self):
        svc = DedupService()
        result = {"result_id": "r1", "doi": "10.1234/c", "title": "New"}
        existing = [{"paper_id": "p1", "doi": "10.1234/a"}]
        decision = svc.check_against_existing(result, existing)
        assert decision.action == "new"

    def test_merge_same_doi(self):
        svc = DedupService()
        a = {"result_id": "r1", "doi": "10.1234/a", "title": "Test"}
        b = {"result_id": "r2", "doi": "10.1234/a", "title": "Test"}
        decision = svc.check_result_pair(a, b)
        assert decision.action == "merge"

    def test_possible_duplicate_similar_title(self):
        svc = DedupService()
        a = {"result_id": "r1", "title": "Large Language Models for Education", "year": 2024, "authors": ["Alice Smith"]}
        b = {"result_id": "r2", "title": "Large Language Models for Education", "year": 2024, "authors": ["Bob Jones"]}
        decision = svc.check_result_pair(a, b)
        assert decision.action in ("merge", "possible_duplicate")
