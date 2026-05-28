"""排序服务测试"""

import pytest

from src.agents_v3.research_workspace.search.base import SearchResult
from src.agents_v3.research_workspace.search.ranking import RankingService


@pytest.fixture
def ranking():
    return RankingService()


class TestRankingService:
    def test_rank_sorts_by_score(self, ranking):
        r1 = SearchResult(title="", source="arxiv")
        r2 = SearchResult(title="Paper", authors=["A"], year=2024, doi="10.x", abstract="text", source="openalex", venue="Conf")
        ranked = ranking.rank([r1, r2])
        assert ranked[0].final_score >= ranked[1].final_score

    def test_recent_paper_scores_higher(self, ranking):
        r_old = SearchResult(title="Old", authors=["A"], year=2000, source="arxiv")
        r_new = SearchResult(title="New", authors=["A"], year=2024, source="arxiv")
        ranked = ranking.rank([r_old, r_new])
        # New paper should score higher
        assert ranked[0].year == 2024

    def test_more_citations_scores_higher(self, ranking):
        r1 = SearchResult(title="A", authors=["A"], year=2024, source="arxiv", citations=100)
        r2 = SearchResult(title="B", authors=["A"], year=2024, source="arxiv", citations=0)
        ranked = ranking.rank([r1, r2])
        assert ranked[0].citations == 100

    def test_rrf_fuse(self, ranking):
        r1 = SearchResult(title="A", source="arxiv")
        r2 = SearchResult(title="B", source="openalex")
        r3 = SearchResult(title="C", source="arxiv")

        ranking1 = [r1, r2, r3]  # r1 rank 1
        ranking2 = [r2, r1, r3]  # r2 rank 1

        fused = ranking.rrf_fuse([ranking1, ranking2])
        # r1 and r2 should be at top (both ranked #1 in different sources)
        top_ids = {fused[0].result_id, fused[1].result_id}
        assert r1.result_id in top_ids
        assert r2.result_id in top_ids
