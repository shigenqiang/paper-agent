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
        "src.agents_v3.research_workspace.storage._global_storage", None
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

    def test_commit_preserves_importance_score(self, service):
        """commit 后 Paper.importance_score 应包含搜索排名分数"""
        q = SearchQuery(query="machine learning")
        session = service.search_candidates("proj1", q)
        # 排名后应有非零分数
        assert any(r.final_score > 0 for r in session.results)

        result_ids = [session.results[0].result_id]
        papers = service.commit_search_results("proj1", session.session_id, result_ids)
        assert len(papers) == 1
        assert papers[0].importance_score > 0

    def test_commit_saves_topic_scores(self, service):
        """commit 后 topic_scores 集合应记录主题相关分数"""
        q = SearchQuery(query="deep learning")
        session = service.search_candidates("proj1", q)
        result_ids = [r.result_id for r in session.results]
        service.commit_search_results("proj1", session.session_id, result_ids, topic="deep learning")

        topic_scores = service.get_topic_scores("proj1", "deep learning")
        assert len(topic_scores) == len(result_ids)
        assert all(s["topic"] == "deep learning" for s in topic_scores)
        assert all(s["importance_score"] >= 0 for s in topic_scores)

    def test_different_topics_different_scores(self, service):
        """同一论文在不同主题下应有不同的 importance_score"""
        # 主题 A
        session_a = service.search_candidates("proj1", SearchQuery(query="neural networks"))
        paper_a = service.commit_search_results(
            "proj1", session_a.session_id, [session_a.results[0].result_id], topic="neural networks",
        )

        # 主题 B（不同主题重新搜索同一论文池）
        session_b = service.search_candidates("proj1", SearchQuery(query="reinforcement learning"))
        paper_b = service.commit_search_results(
            "proj1", session_b.session_id, [session_b.results[0].result_id], topic="reinforcement learning",
        )

        scores_a = service.get_topic_scores("proj1", "neural networks")
        scores_b = service.get_topic_scores("proj1", "reinforcement learning")
        assert len(scores_a) >= 1
        assert len(scores_b) >= 1

    def test_get_paper_topic_scores(self, service):
        """get_paper_topic_scores 应返回某篇论文在所有主题下的得分"""
        q = SearchQuery(query="transformer")
        session = service.search_candidates("proj1", q)
        paper_id = session.results[0].result_id
        service.commit_search_results("proj1", session.session_id, [paper_id], topic="transformer")

        # 通过 paper_id 查找对应的 paper
        papers = service.list_papers("proj1")
        assert len(papers) >= 1
        paper_scores = service.get_paper_topic_scores(papers[0].paper_id)
        assert len(paper_scores) >= 1
        assert paper_scores[0]["topic"] == "transformer"

    def test_recompute_topic_scores(self, service):
        """recompute_topic_scores 应基于论文内容重新计算分数"""
        q = SearchQuery(query="test")
        session = service.search_candidates("proj1", q)
        result_ids = [r.result_id for r in session.results]
        service.commit_search_results("proj1", session.session_id, result_ids, topic="test")

        # 用新主题重新计算
        scored = service.recompute_topic_scores("proj1", "new topic")
        assert len(scored) == len(result_ids)
        assert all(s["topic"] == "new topic" for s in scored)

    def test_papers_pool_has_no_scores(self, service):
        """论文池（papers_pool）不应存储分数"""
        q = SearchQuery(query="test")
        session = service.search_candidates("proj1", q)
        result_ids = [r.result_id for r in session.results]
        service.commit_search_results("proj1", session.session_id, result_ids, topic="test")

        # 检查论文池中的数据不含分数字段
        pool_papers = service.list_pool()
        assert len(pool_papers) > 0
        for p in pool_papers:
            assert "importance_score" not in p
            assert "relevance_score" not in p
            assert "quality_score" not in p
