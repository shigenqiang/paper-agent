"""ReportService 测试 - 增强版"""

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
        content="Review content here.",
        paper_ids=["p1", "p2"],
        evidence_ids=["e1", "e2"],
        section_sources={
            "background": {"paper_ids": ["p1"], "evidence_ids": ["e1"]},
            "findings": {"paper_ids": ["p1", "p2"], "evidence_ids": ["e1", "e2"]},
        },
    )
    service.save_report(report)
    # Add paper and evidence data for source index
    service.storage.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "title": "Paper 1",
        "authors": ["Alice"], "year": 2024, "doi": "10.1234/a",
    })
    service.storage.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "title": "Paper 2",
        "authors": ["Bob"], "year": 2023,
    })
    service.storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1", "project_id": "proj1", "paper_id": "p1",
        "finding": "Improved learning", "source_quote": "found improvement",
    })
    service.storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2", "project_id": "proj1", "paper_id": "p2",
        "limitation": "Small sample", "source_quote": "limited by sample",
    })
    return report


class TestReportService:
    # ── 基础 CRUD ──────────────────────────────

    def test_save_report_persists_to_storage(self, service, sample_report):
        found = service.get_report("r1")
        assert found is not None
        assert found.title == "Test Review"

    def test_list_reports_returns_all_in_project(self, service, sample_report):
        reports = service.list_reports("proj1")
        assert len(reports) == 1

    def test_list_reports_filters_by_type(self, service, sample_report):
        reports = service.list_reports("proj1", "literature_review")
        assert len(reports) == 1
        reports = service.list_reports("proj1", "innovation_report")
        assert len(reports) == 0

    def test_list_reports_filters_by_status(self, service, sample_report):
        reports = service.list_reports("proj1", status="draft")
        assert len(reports) == 1
        reports = service.list_reports("proj1", status="archived")
        assert len(reports) == 0

    def test_get_nonexistent_returns_none(self, service):
        assert service.get_report("missing") is None

    # ── 状态管理 ──────────────────────────────

    def test_update_report_status(self, service, sample_report):
        report = service.update_report_status("r1", "final")
        assert report.status == "final"

    def test_archive_report(self, service, sample_report):
        report = service.archive_report("r1")
        assert report.status == "archived"

    def test_delete_report(self, service, sample_report):
        service.create_version("r1", "v2", "update")
        assert service.delete_report("r1") is True
        assert service.get_report("r1") is None
        assert service.list_versions("r1") == []

    # ── 版本管理 ──────────────────────────────

    def test_create_version_saves_version_content(self, service, sample_report):
        version = service.create_version("r1", "Updated content", "fix typos")
        assert version is not None
        assert version.content == "Updated content"

    def test_create_version_increments_report_version(self, service, sample_report):
        service.create_version("r1", "V2 content", "update")
        report = service.get_report("r1")
        assert report.version == 2
        assert report.content == "V2 content"

    def test_create_version_nonexistent_returns_none(self, service):
        assert service.create_version("missing", "content", "reason") is None

    def test_create_version_has_scope_snapshot(self, service, sample_report):
        version = service.create_version("r1", "v2", "update")
        assert version.version_number == 1
        assert version.paper_ids == ["p1", "p2"]
        assert "paper_ids" in version.source_snapshot

    def test_list_versions(self, service, sample_report):
        service.create_version("r1", "v2", "first update")
        service.create_version("r1", "v3", "second update")
        versions = service.list_versions("r1")
        assert len(versions) == 2
        assert versions[0].version_number < versions[1].version_number

    def test_restore_version(self, service, sample_report):
        service.create_version("r1", "V2 content", "update")
        versions = service.list_versions("r1")
        report = service.restore_version("r1", versions[0].version_id)
        assert report is not None
        # Should have auto-saved current before restore
        all_versions = service.list_versions("r1")
        assert len(all_versions) >= 2

    # ── 来源索引 ──────────────────────────────

    def test_build_source_index(self, service, sample_report):
        index = service.build_source_index("r1")
        assert index["report_id"] == "r1"
        assert len(index["paper_sources"]) == 2
        assert len(index["evidence_sources"]) == 2

    def test_source_index_paper_has_metadata(self, service, sample_report):
        index = service.build_source_index("r1")
        p1 = next(p for p in index["paper_sources"] if p["paper_id"] == "p1")
        assert p1["title"] == "Paper 1"
        assert p1["year"] == 2024
        assert p1["doi"] == "10.1234/a"

    def test_source_index_tracks_used_in_sections(self, service, sample_report):
        index = service.build_source_index("r1")
        p1 = next(p for p in index["paper_sources"] if p["paper_id"] == "p1")
        assert "background" in p1["used_in_sections"]
        assert "findings" in p1["used_in_sections"]

    def test_source_index_evidence_has_fields(self, service, sample_report):
        index = service.build_source_index("r1")
        e1 = next(e for e in index["evidence_sources"] if e["evidence_id"] == "e1")
        assert e1["paper_id"] == "p1"
        assert e1["finding"] == "Improved learning"

    # ── 校验 ──────────────────────────────────

    def test_validate_report_traceability(self, service, sample_report):
        result = service.validate_report_traceability("r1")
        assert result["valid"] is True
        assert result["source_coverage"] > 0

    def test_validate_detects_missing_paper(self, service):
        report = Report(
            report_id="r_bad", project_id="proj1", type=ReportType.LITERATURE_REVIEW,
            paper_ids=["nonexistent"], evidence_ids=[],
        )
        service.save_report(report)
        result = service.validate_report_traceability("r_bad")
        assert len(result["missing_paper_ids"]) > 0

    def test_validate_detects_scope_violation(self, service):
        report = Report(
            report_id="r_leak", project_id="proj1", type=ReportType.LITERATURE_REVIEW,
            paper_ids=["p1", "p99"],
            scope={"paper_ids": ["p1"]},
        )
        service.save_report(report)
        result = service.validate_report_traceability("r_leak")
        assert len(result["scope_violations"]) > 0

    def test_validate_section_coverage(self, service, sample_report):
        result = service.validate_report_traceability("r1")
        assert result["section_source_coverage"] > 0

    # ── 导出 ──────────────────────────────────

    def test_export_markdown_includes_content_and_metadata(self, service, sample_report):
        md = service.export_markdown("r1")
        assert "Review content" in md
        assert "报告ID" in md
        assert "论文数" in md

    def test_export_markdown_with_source_index(self, service, sample_report):
        md = service.export_markdown("r1", include_source_index=True)
        assert "来源索引" in md
        assert "Paper 1" in md

    def test_export_markdown_with_validation(self, service, sample_report):
        report = service.get_report("r1")
        report.validation_result = {"valid": True, "source_coverage": 0.9}
        service.save_report(report)
        md = service.export_markdown("r1", include_validation=True)
        assert "通过" in md

    def test_export_json(self, service, sample_report):
        import json
        data = json.loads(service.export_json("r1"))
        assert data["report_id"] == "r1"
        assert "source_index" in data
        assert len(data["paper_ids"]) == 2

    def test_export_tracks_format(self, service, sample_report):
        service.export_markdown("r1")
        report = service.get_report("r1")
        assert "markdown" in report.exported_formats

    def test_export_json_tracks_format(self, service, sample_report):
        service.export_json("r1")
        report = service.get_report("r1")
        assert "json" in report.exported_formats

    def test_export_nonexistent_returns_empty_string(self, service):
        assert service.export_markdown("missing") == ""
        assert service.export_json("missing") == "{}"
