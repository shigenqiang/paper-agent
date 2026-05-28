"""ReportService 测试"""

import pytest

from src.agents_v3.research_workspace.report_service import ReportService
from src.agents_v3.research_workspace.models import Report, ReportType


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.report_service.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return ReportService()


@pytest.fixture
def sample_report(service):
    report = Report(
        report_id="r1",
        project_id="proj1",
        type=ReportType.LITERATURE_REVIEW,
        title="Test Review",
        content="Review content",
        paper_ids=["p1", "p2"],
        evidence_ids=["e1"],
    )
    service.save_report(report)
    return report


class TestReportService:
    def test_save_report(self, service, sample_report):
        found = service.get_report("r1")
        assert found is not None
        assert found.title == "Test Review"

    def test_list_reports(self, service, sample_report):
        reports = service.list_reports("proj1")
        assert len(reports) == 1

    def test_list_reports_by_type(self, service, sample_report):
        reports = service.list_reports("proj1", "literature_review")
        assert len(reports) == 1
        reports = service.list_reports("proj1", "innovation_report")
        assert len(reports) == 0

    def test_get_nonexistent(self, service):
        assert service.get_report("missing") is None

    def test_create_version(self, service, sample_report):
        version = service.create_version("r1", "Updated content", "fix typos")
        assert version is not None
        assert version.content == "Updated content"

    def test_version_updates_report(self, service, sample_report):
        service.create_version("r1", "V2 content", "update")
        report = service.get_report("r1")
        assert report.version == 2
        assert report.content == "V2 content"

    def test_create_version_nonexistent(self, service):
        assert service.create_version("missing", "content", "reason") is None

    def test_export_markdown(self, service, sample_report):
        md = service.export_markdown("r1")
        assert "Review content" in md
        assert "报告ID" in md
        assert "论文数" in md

    def test_export_nonexistent(self, service):
        assert service.export_markdown("missing") == ""
