"""RetrievalScopeService 测试 - 增强版"""

import pytest

from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.models import ScopeType


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._global_storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.scope.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return RetrievalScopeService()


@pytest.fixture
def sample_data(service):
    storage = service.storage
    storage.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "year": 2023, "included": True, "title": "Paper 1",
    })
    storage.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "year": 2024, "included": True, "title": "Paper 2",
    })
    storage.upsert_item("papers", "p3", {
        "paper_id": "p3", "project_id": "proj1", "year": 2022, "included": False, "title": "Paper 3",
    })
    storage.upsert_item("papers", "p_other", {
        "paper_id": "p_other", "project_id": "other_proj", "year": 2024, "included": True, "title": "Other Paper",
    })
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1", "project_id": "proj1", "paper_id": "p1", "topic": "feedback",
        "method": "experiment", "source_quote": "found improvement",
    })
    storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2", "project_id": "proj1", "paper_id": "p2", "topic": "feedback",
        "method": "survey",
    })
    return storage


class TestRetrievalScopeService:
    # ── 基础解析 ──────────────────────────────────

    def test_resolve_all_project_includes_only_included(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        assert len(scope.paper_ids) == 2
        assert "p3" not in scope.paper_ids  # excluded

    def test_resolve_selected_papers(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1"],
        })
        assert scope.paper_ids == ["p1"]

    def test_resolve_topic_group(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "topic_group",
            "selected_topic_ids": ["feedback"],
        })
        assert len(scope.paper_ids) == 2

    def test_resolve_year_range(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "year_range",
            "time_range": ["2023", "2024"],
        })
        assert len(scope.paper_ids) == 2

    # ── 项目边界安全 ──────────────────────────────

    def test_selected_papers_filters_other_project(self, service, sample_data):
        """其他项目论文不能进入 selected scope"""
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1", "p_other"],
        })
        assert "p1" in scope.paper_ids
        assert "p_other" not in scope.paper_ids
        invalid = scope.metadata.get("invalid_selection", [])
        assert any(v["id"] == "p_other" for v in invalid)

    def test_selected_papers_filters_excluded(self, service, sample_data):
        """excluded 论文不能进入 selected scope"""
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1", "p3"],
        })
        assert "p1" in scope.paper_ids
        assert "p3" not in scope.paper_ids
        invalid = scope.metadata.get("invalid_selection", [])
        assert any(v["id"] == "p3" and v["reason"] == "excluded" for v in invalid)

    def test_selected_papers_filters_nonexistent(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1", "nonexistent"],
        })
        assert scope.paper_ids == ["p1"]
        invalid = scope.metadata.get("invalid_selection", [])
        assert any(v["id"] == "nonexistent" and v["reason"] == "not_found" for v in invalid)

    # ── 空范围处理 ────────────────────────────────

    def test_empty_project_returns_empty_reason(self, service):
        scope = service.resolve("empty_proj", {"type": "all_project"})
        assert scope.paper_ids == []
        assert scope.metadata.get("empty_reason") == "no_included_papers"

    def test_empty_scope_to_evidence_returns_empty(self, service, sample_data):
        """空 scope 不会 fallback 到全项目 evidence"""
        scope = service.resolve("empty_proj", {"type": "all_project"})
        records = service.to_evidence_records(scope)
        assert records == []

    def test_all_excluded_returns_empty_reason(self, service):
        service.storage.upsert_item("papers", "px", {
            "paper_id": "px", "project_id": "proj_excluded", "included": False,
        })
        scope = service.resolve("proj_excluded", {"type": "all_project"})
        assert scope.metadata.get("empty_reason") == "no_included_papers"

    # ── Scope metadata ────────────────────────────

    def test_resolve_has_empty_reason(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "topic_group",
            "selected_topic_ids": ["nonexistent_topic"],
        })
        assert scope.metadata.get("empty_reason") == "no_matching_topic"

    def test_resolve_has_suggested_actions(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "topic_group",
            "selected_topic_ids": ["nonexistent_topic"],
        })
        assert len(scope.metadata.get("suggested_actions", [])) > 0

    def test_resolve_has_explain(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        explain = scope.metadata.get("explain", {})
        assert "papers" in explain
        assert len(explain["papers"]) == 2

    def test_resolve_has_warnings_key(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        assert "warnings" in scope.metadata

    # ── ScopeGuard ────────────────────────────────

    def test_build_scope_guard(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        guard = service.build_scope_guard(scope)
        assert "allowed_paper_ids" in guard
        assert "allowed_evidence_ids" in guard
        assert "p1" in guard["allowed_paper_ids"]

    def test_validate_against_scope_passes(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        guard = service.build_scope_guard(scope)
        result = service.validate_against_scope(guard, {
            "paper_ids": ["p1"],
            "evidence_ids": ["e1"],
        })
        assert result["valid"] is True

    def test_validate_against_scope_fails_for_out_of_scope(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1"],
        })
        guard = service.build_scope_guard(scope)
        result = service.validate_against_scope(guard, {
            "paper_ids": ["p1", "p2"],  # p2 not in scope
        })
        assert result["valid"] is False
        assert result["scope_leak_count"] == 1

    # ── 交叉过滤 ──────────────────────────────────

    def test_topic_and_year_intersection(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "all_project",
            "selected_topic_ids": ["feedback"],
            "time_range": ["2024", "2024"],
        })
        # Only p2 matches topic=feedback AND year=2024
        assert scope.paper_ids == ["p2"]

    # ── to_paper_cards ────────────────────────────

    def test_to_paper_cards(self, service, sample_data):
        service.storage.upsert_item("paper_cards", "c1", {
            "card_id": "c1", "paper_id": "p1", "active": True, "project_id": "proj1",
        })
        scope = service.resolve("proj1", {"type": "all_project"})
        cards = service.to_paper_cards(scope)
        assert len(cards) == 1

    # ── get_scope_filters ─────────────────────────

    def test_get_scope_filters(self, service, sample_data):
        filters = service.get_scope_filters("proj1")
        assert "papers" in filters
        assert "topics" in filters
        assert "methods" in filters
        assert "years" in filters
        # 只包含 included 论文
        paper_ids = [p["id"] for p in filters["papers"]]
        assert "p3" not in paper_ids

    # ── graph_hops 限制 ───────────────────────────

    def test_graph_hops_clamped(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "graph_subgraph",
            "selected_graph_node_ids": ["nonexistent"],
            "graph_hops": 10,
        })
        warnings = scope.metadata.get("warnings", [])
        assert any("clamped" in w for w in warnings)

    # ── Summary ───────────────────────────────────

    def test_summarize_all_project(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        assert "全项目" in scope.summary

    def test_summarize_selected_papers(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1"],
        })
        assert "1 篇" in scope.summary

    def test_summarize_topic_group(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "topic_group",
            "selected_topic_ids": ["feedback"],
        })
        assert "主题" in scope.summary
