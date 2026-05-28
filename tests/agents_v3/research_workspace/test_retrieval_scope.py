"""RetrievalScopeService 测试"""

import pytest

from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.models import ScopeType


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.scope.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return RetrievalScopeService()


@pytest.fixture
def sample_data(service):
    storage = service.storage
    # Papers
    storage.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "year": 2023, "included": True,
    })
    storage.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "year": 2024, "included": True,
    })
    storage.upsert_item("papers", "p3", {
        "paper_id": "p3", "project_id": "proj1", "year": 2022, "included": False,
    })
    # Evidence
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1", "project_id": "proj1", "paper_id": "p1", "topic": "feedback",
    })
    storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2", "project_id": "proj1", "paper_id": "p2", "topic": "feedback",
    })
    return storage


class TestRetrievalScopeService:
    def test_resolve_all_project(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        assert scope.scope_type == ScopeType.ALL_PROJECT
        assert len(scope.paper_ids) == 2  # Only included papers

    def test_resolve_selected_papers(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1"],
        })
        assert scope.scope_type == ScopeType.SELECTED_PAPERS
        assert scope.paper_ids == ["p1"]

    def test_resolve_topic_group(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "topic_group",
            "selected_topic_ids": ["feedback"],
        })
        assert scope.scope_type == ScopeType.TOPIC_GROUP
        assert len(scope.paper_ids) == 2

    def test_resolve_year_range(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "year_range",
            "time_range": ["2023", "2024"],
        })
        assert scope.scope_type == ScopeType.YEAR_RANGE
        assert len(scope.paper_ids) == 2

    def test_to_paper_ids(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        paper_ids = service.to_paper_ids(scope)
        assert len(paper_ids) == 2

    def test_to_evidence_records(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        records = service.to_evidence_records(scope)
        assert len(records) == 2

    def test_summarize_all_project(self, service, sample_data):
        scope = service.resolve("proj1", {"type": "all_project"})
        assert "全项目" in scope.summary

    def test_summarize_selected_papers(self, service, sample_data):
        scope = service.resolve("proj1", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1"],
        })
        assert "1 篇" in scope.summary
