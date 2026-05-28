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
        "authors": ["Alice"], "year": 2024, "venue": "Conf A",
    })
    storage.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "title": "Paper 2", "included": True,
        "authors": ["Bob"], "year": 2023, "venue": "Conf B",
    })
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1", "project_id": "proj1", "paper_id": "p1",
        "topic": "feedback", "method": "experiment",
        "finding": "Improved learning outcomes significantly",
        "limitation": "Small sample size",
    })
    storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2", "project_id": "proj1", "paper_id": "p2",
        "topic": "feedback", "method": "survey",
        "finding": "Higher engagement observed",
        "limitation": "Short duration of study",
    })
    storage.upsert_item("paper_cards", "card1", {
        "card_id": "card1", "paper_id": "p1", "project_id": "proj1",
        "title": "Paper 1", "method": "experiment",
    })
    storage.upsert_item("paper_cards", "card2", {
        "card_id": "card2", "paper_id": "p2", "project_id": "proj1",
        "title": "Paper 2", "method": "survey",
    })
    return storage


class TestLiteratureReviewGenerator:
    def test_generate_returns_review_report(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert report.type == ReportType.LITERATURE_REVIEW
        assert report.content
        assert len(report.paper_ids) > 0

    def test_generate_includes_scope_summary(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "生成范围" in report.content

    def test_generate_includes_paper_count(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "论文数量" in report.content or "使用论文" in report.content

    def test_generate_includes_standard_sections(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "发现" in report.content
        assert "文献综述" in report.content

    def test_generate_has_section_sources(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        section_sources = report.scope.get("section_sources", {})
        assert len(section_sources) > 0

    def test_generate_has_validation_result(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        validation = report.scope.get("validation_result", {})
        assert "source_coverage" in validation

    def test_generate_references_from_paper_meta(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "Alice" in report.content or "Paper 1" in report.content

    def test_empty_scope_returns_no_generation(self, service, sample_data):
        report = service.generate("proj_empty", {"type": "all_project"})
        assert "无法生成" in report.content or "没有" in report.content

    def test_insufficient_evidence_returns_report(self, service):
        service.storage.upsert_item("papers", "p1", {
            "paper_id": "p1", "project_id": "proj_sparse", "title": "P1", "included": True,
        })
        service.storage.upsert_item("evidence_records", "e1", {
            "evidence_id": "e1", "project_id": "proj_sparse", "paper_id": "p1", "finding": "F",
        })
        report = service.generate("proj_sparse", {"type": "all_project"})
        assert "不足" in report.content or "无法生成" in report.content

    def test_collect_materials_returns_evidence_and_cards(self, service, sample_data):
        from src.agents_v3.research_workspace.models import RetrievalScope, ScopeType
        scope = RetrievalScope(scope_type=ScopeType.ALL_PROJECT, project_id="proj1", paper_ids=["p1", "p2"])
        scope.evidence_ids = ["e1", "e2"]
        materials = service.collect_materials(scope)
        assert materials["paper_count"] == 2
        assert len(materials["evidence_records"]) > 0

    def test_validate_review_passes_with_valid_report(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        result = service.validate_review(report)
        assert result["valid"] is True

    def test_validate_review_fails_without_scope(self, service):
        from src.agents_v3.research_workspace.models import Report
        report = Report(report_id="r1", project_id="proj1", type=ReportType.LITERATURE_REVIEW)
        result = service.validate_review(report)
        assert result["valid"] is False

    def test_fallback_generates_sections(self, service, sample_data):
        """LLM 失败时 fallback 仍生成可追溯综述"""
        service.llm = None
        report = service.generate("proj1", {"type": "all_project"})
        assert report.content
        assert "发现" in report.content or "不足" in report.content
