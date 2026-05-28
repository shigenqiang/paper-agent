"""InnovationReportGenerator 测试"""

import pytest

from src.agents_v3.research_workspace.innovation_generator import InnovationReportGenerator
from src.agents_v3.research_workspace.models import ReportType, EvidenceRecord


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.innovation_generator.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.scope.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return InnovationReportGenerator()


@pytest.fixture
def sample_data(service):
    storage = service.storage
    storage.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "included": True,
    })
    storage.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "included": True,
    })
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1",
        "project_id": "proj1",
        "paper_id": "p1",
        "topic": "feedback",
        "finding": "Improved learning",
        "limitation": "Small sample size",
        "future_work": "Extend to K-12",
    })
    storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2",
        "project_id": "proj1",
        "paper_id": "p2",
        "topic": "feedback",
        "finding": "Higher engagement",
        "limitation": "Small sample size",
    })
    return storage


class TestInnovationReportGenerator:
    def test_generate_report(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert report.type == ReportType.INNOVATION_REPORT
        assert report.content

    def test_report_has_innovations(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert "创新点" in report.content or "创新方向" in report.content

    def test_aggregate_limitations(self, service, sample_data):
        evidence = [
            EvidenceRecord(evidence_id="e1", project_id="p", paper_id="p1", limitation="A"),
            EvidenceRecord(evidence_id="e2", project_id="p", paper_id="p2", limitation="A"),
            EvidenceRecord(evidence_id="e3", project_id="p", paper_id="p3", limitation="B"),
        ]
        result = service.aggregate_limitations(evidence)
        assert result[0]["count"] == 2

    def test_score_candidates(self, service):
        from src.agents_v3.research_workspace.models import InnovationPoint
        candidates = [
            InnovationPoint(
                innovation_id="ip1",
                name="Test",
                gap="Specific gap",
                supporting_papers=["p1", "p2"],
            ),
        ]
        scored = service.score_candidates(candidates)
        assert len(scored) == 1
        assert scored[0].scores

    def test_is_generic(self, service):
        assert service._is_generic("使用深度学习") is True
        assert service._is_generic("改进反馈机制") is False

    def test_report_paper_ids(self, service, sample_data):
        report = service.generate("proj1", {"type": "all_project"})
        assert len(report.paper_ids) > 0
