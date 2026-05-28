"""LiteratureReviewGenerator 测试"""

import pytest

from src.agents_v3.research_workspace.review_generator import LiteratureReviewGenerator
from src.agents_v3.research_workspace.models import ReportType


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.review_generator.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.scope.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return LiteratureReviewGenerator()


@pytest.fixture
def sample_data(service):
    storage = service.storage
    storage.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "title": "Paper 1", "included": True,
    })
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1",
        "project_id": "proj1",
        "paper_id": "p1",
        "topic": "feedback",
        "method": "experiment",
        "finding": "Improved learning",
        "limitation": "Small sample",
        "future_work": "Extend to other subjects",
    })
    storage.upsert_item("paper_cards", "card1", {
        "card_id": "card1",
        "paper_id": "p1",
        "project_id": "proj1",
        "title": "Paper 1",
    })
    return storage


class TestLiteratureReviewGenerator:
    def test_generate_review(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert report.type == ReportType.LITERATURE_REVIEW
        assert report.content
        assert len(report.paper_ids) > 0

    def test_review_has_scope_summary(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "生成范围" in report.content

    def test_review_has_paper_count(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "使用论文数量" in report.content

    def test_review_has_sections(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "研究背景" in report.content
        assert "主要研究方法" in report.content
        assert "主要发现" in report.content

    def test_collect_materials(self, service, sample_data):
        from src.agents_v3.research_workspace.models import RetrievalScope, ScopeType
        scope = RetrievalScope(scope_type=ScopeType.ALL_PROJECT, project_id="proj1", paper_ids=["p1"])
        materials = service.collect_materials(scope)
        assert materials["paper_count"] == 1

    def test_validate_review(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        result = service.validate_review(report)
        assert result["valid"] is True

    def test_validate_review_missing_scope(self, service):
        from src.agents_v3.research_workspace.models import Report
        report = Report(report_id="r1", project_id="proj1", type=ReportType.LITERATURE_REVIEW)
        result = service.validate_review(report)
        assert result["valid"] is False
