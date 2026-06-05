"""P2 单元测试：报告版本与导出增强 — Diff + DOCX Export + CitationFormatter

不依赖真实 PostgreSQL / python-docx。
使用 MockStorage + 内存数据。
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agents_v3.research_workspace.services.report_service import ReportService
from src.agents_v3.research_workspace.services.citation_formatter import CitationFormatter


# ── Mock Storage ──────────────────────────────────────


class MockStorage:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get_item(self, table: str, item_id: str):
        return self._data.get(table, {}).get(item_id)

    def upsert_item(self, table: str, item_id: str, item: dict):
        self._data.setdefault(table, {})[item_id] = item

    def query(self, table: str, filters: dict):
        items = self._data.get(table, {}).values()
        result = []
        for item in items:
            match = True
            for k, v in filters.items():
                if isinstance(v, list):
                    if item.get(k) not in v:
                        match = False
                        break
                elif item.get(k) != v:
                    match = False
                    break
            if match:
                result.append(item)
        return result

    def list_all(self, table: str):
        return list(self._data.get(table, {}).values())


# ── Fixtures ──────────────────────────────────────────


def _make_report(report_id: str = "r1", content: str = "") -> dict:
    """DB 格式：大部分字段嵌套在 metadata 中"""
    return {
        "report_id": report_id,
        "project_id": "proj1",
        "report_type": "literature_review",
        "title": "Test Report",
        "content": content or "# Introduction\n\nThis is the introduction.\n\n## Methods\n\nWe used method A.\n\n## Results\n\nResults show improvement.",
        "metadata": {
            "scope": {},
            "paper_ids": ["p1", "p2"],
            "evidence_ids": ["ev1"],
            "graph_node_ids": [],
            "status": "draft",
            "section_sources": {"s1": {"paper_ids": ["p1"]}},
            "validation_result": {},
            "exported_formats": [],
            "version": 3,
        },
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


def _make_version(version_id: str, report_id: str, version_number: int, content: str) -> dict:
    return {
        "version_id": version_id,
        "report_id": report_id,
        "version_number": version_number,
        "content": content,
        "reason": f"version {version_number}",
        "scope_snapshot": {},
        "source_snapshot": {},
        "paper_ids": ["p1"],
        "evidence_ids": ["ev1"],
        "validation_result": {},
        "created_at": "2026-01-01T00:00:00",
    }


def _make_paper(pid: str = "p1") -> dict:
    return {
        "paper_id": pid,
        "title": f"Paper {pid}",
        "authors": [{"name": "Alice Smith"}, {"name": "Bob Jones"}],
        "dates": {"year": 2025},
        "source": {"venue": "ICML 2025"},
        "identifiers": {"doi": "10.1234/test"},
        "url": "https://example.com",
    }


# ── Test Version Diff ────────────────────────────────


class TestDiffVersions:

    def test_basic_diff(self):
        """两个版本有差异应返回 diff 统计"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1")},
            "report_versions": {
                "v1": _make_version("v1", "r1", 1, "# Intro\n\nOld intro.\n\n## Methods\n\nOld method."),
                "v2": _make_version("v2", "r1", 2, "# Intro\n\nNew intro with more detail.\n\n## Methods\n\nOld method.\n\n## Results\n\nNew results section."),
            },
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.diff_versions("r1", 1, 2)
        assert result is not None
        assert result["stats"]["added"] > 0 or result["stats"]["changed"] > 0

    def test_identical_versions(self):
        """相同版本 diff 应为零"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1")},
            "report_versions": {
                "v1": _make_version("v1", "r1", 1, "Same content."),
                "v2": _make_version("v2", "r1", 2, "Same content."),
            },
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.diff_versions("r1", 1, 2)
        assert result is not None
        assert result["stats"]["added"] == 0
        assert result["stats"]["removed"] == 0
        assert result["stats"]["changed"] == 0

    def test_missing_version_returns_none(self):
        """不存在的版本号返回 None"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1")},
            "report_versions": {},
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.diff_versions("r1", 1, 999)
        assert result is None

    def test_unified_diff_format(self):
        """unified_diff 字段应包含标准 diff 标记"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1")},
            "report_versions": {
                "v1": _make_version("v1", "r1", 1, "Line A\n\nLine B"),
                "v2": _make_version("v2", "r1", 2, "Line A\n\nLine C"),
            },
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.diff_versions("r1", 1, 2)
        assert result is not None
        diff_text = result["unified_diff"]
        assert "---" in diff_text
        assert "+++" in diff_text

    def test_current_version_included(self):
        """当前版本（未快照）也应参与 diff"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1", content="Current content.")},
            "report_versions": {
                "v1": _make_version("v1", "r1", 1, "Old content."),
            },
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        # report.version=3 → current_ver = 2 (next-to-assign - 1)
        result = svc.diff_versions("r1", 1, 2)
        assert result is not None
        assert result["stats"]["changed"] > 0


# ── Test Export DOCX ──────────────────────────────────


class TestExportDocx:

    def test_returns_none_for_missing_report(self):
        storage = MockStorage({"reports": {}, "papers": {}, "evidence_records": {}})
        svc = ReportService(storage=storage)
        assert svc.export_docx("nonexistent") is None

    def test_returns_bytes_when_docx_installed(self):
        """python-docx 已安装时返回 bytes"""
        storage = MockStorage({
            "reports": {"r1": _make_report()},
            "papers": {"p1": _make_paper("p1"), "p2": _make_paper("p2")},
            "evidence_records": {"ev1": {"evidence_id": "ev1", "paper_id": "p1", "finding": "test"}},
        })
        svc = ReportService(storage=storage)
        result = svc.export_docx("r1")
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 100  # DOCX 文件应有一定大小

    def test_tracks_docx_format(self):
        """导出后应记录 docx 格式"""
        storage = MockStorage({
            "reports": {"r1": _make_report()},
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        svc.export_docx("r1")
        report = svc.get_report("r1")
        assert "docx" in report.exported_formats


# ── Test CitationFormatter ────────────────────────────


class TestCitationFormatter:

    def test_simple_format(self):
        paper = {
            "paper_id": "p1",
            "title": "Deep Learning for NLP",
            "authors": ["Alice Smith", "Bob Jones"],
            "year": 2025,
            "doi": "10.1234/test",
        }
        result = CitationFormatter.format_simple(paper)
        assert "[p1]" in result
        assert "Alice Smith" in result
        assert "2025" in result
        assert "Deep Learning for NLP" in result
        assert "10.1234/test" in result

    def test_apa_format(self):
        paper = {
            "paper_id": "p1",
            "title": "Deep Learning for NLP",
            "authors": ["Alice Smith", "Bob Jones"],
            "year": 2025,
            "venue": "ICML",
            "doi": "10.1234/test",
        }
        result = CitationFormatter.format_apa(paper)
        assert "Smith, A." in result
        assert "Jones, B." in result
        assert "(2025)" in result
        assert "ICML" in result
        assert "doi.org" in result

    def test_gbt7714_format(self):
        paper = {
            "paper_id": "p1",
            "title": "深度学习方法研究",
            "authors": ["张三", "李四"],
            "year": 2025,
            "venue": "计算机学报",
            "doi": "10.1234/test",
        }
        result = CitationFormatter.format_gbt7714(paper)
        assert "张三" in result
        assert "深度学习方法研究" in result
        assert "[J]" in result
        assert "2025" in result

    def test_bibtex_format(self):
        paper = {
            "paper_id": "p1",
            "title": "Deep Learning",
            "authors": ["Alice Smith"],
            "year": 2025,
            "venue": "ICML",
            "doi": "10.1234/test",
        }
        result = CitationFormatter.format_bibtex(paper)
        assert "@article{" in result
        assert "title = {Deep Learning}" in result
        assert "author = {Alice Smith}" in result
        assert "year = {2025}" in result

    def test_format_dispatch(self):
        paper = {"paper_id": "p1", "title": "T", "authors": ["A"], "year": 2025}
        assert CitationFormatter.format(paper, "simple") == CitationFormatter.format_simple(paper)
        assert CitationFormatter.format(paper, "apa") == CitationFormatter.format_apa(paper)
        assert CitationFormatter.format(paper, "bibtex") == CitationFormatter.format_bibtex(paper)

    def test_empty_authors(self):
        paper = {"paper_id": "p1", "title": "No Authors", "year": 2025}
        result = CitationFormatter.format_simple(paper)
        assert "No Authors" in result

    def test_many_authors_apa(self):
        paper = {
            "paper_id": "p1",
            "title": "Many Authors",
            "authors": [f"Author{i} Last{i}" for i in range(10)],
            "year": 2025,
        }
        result = CitationFormatter.format_apa(paper)
        assert "..." in result  # APA truncates after 7

    def test_many_authors_gbt7714_chinese(self):
        paper = {
            "paper_id": "p1",
            "title": "多作者论文",
            "authors": ["张三", "李四", "王五", "赵六"],
            "year": 2025,
        }
        result = CitationFormatter.format_gbt7714(paper)
        assert "等" in result  # Chinese "et al"

    def test_many_authors_gbt7714_english(self):
        paper = {
            "paper_id": "p1",
            "title": "Many Authors Paper",
            "authors": ["Alice Smith", "Bob Jones", "Charlie Brown", "Dave Wilson"],
            "year": 2025,
        }
        result = CitationFormatter.format_gbt7714(paper)
        assert "et al" in result

    def test_gbt7714_dispatch(self):
        paper = {"paper_id": "p1", "title": "T", "authors": ["A"], "year": 2025}
        assert CitationFormatter.format(paper, "gbt7714") == CitationFormatter.format_gbt7714(paper)

    def test_unknown_style_fallback(self):
        paper = {"paper_id": "p1", "title": "T", "authors": ["A"], "year": 2025}
        assert CitationFormatter.format(paper, "unknown") == CitationFormatter.format_simple(paper)

    def test_bibtex_no_authors(self):
        paper = {"paper_id": "p1:abc", "title": "No Authors", "year": 2025}
        result = CitationFormatter.format_bibtex(paper)
        assert "@article{" in result
        assert "p1_abc" in result  # fallback key from pid


# ── Test Diff Edge Cases ─────────────────────────────


class TestDiffEdgeCases:

    def test_delete_only_diff(self):
        """旧版本有内容，新版本删除了段落"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1", content="Keep this.")},
            "report_versions": {
                "v1": _make_version("v1", "r1", 1, "Keep this.\n\nThis will be deleted."),
                "v2": _make_version("v2", "r1", 2, "Keep this."),
            },
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.diff_versions("r1", 1, 2)
        assert result is not None
        assert result["stats"]["removed"] > 0

    def test_both_versions_missing(self):
        """两个版本都不存在返回 None"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1")},
            "report_versions": {},
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.diff_versions("r1", 99, 100)
        assert result is None

    def test_reversed_order(self):
        """version_a > version_b 也能工作"""
        storage = MockStorage({
            "reports": {"r1": _make_report("r1")},
            "report_versions": {
                "v1": _make_version("v1", "r1", 1, "Old."),
                "v2": _make_version("v2", "r1", 2, "New."),
            },
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.diff_versions("r1", 2, 1)
        assert result is not None
        # 反向 diff 应该有 removed（旧内容在 fromfile）
        assert result["version_a"] == 2
        assert result["version_b"] == 1


# ── Test DOCX Content Parsing ─────────────────────────


class TestDocxContentParsing:

    def test_with_table_markdown(self):
        """Markdown 表格应转换为 DOCX 表格"""
        content = "# Report\n\n| Col A | Col B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        storage = MockStorage({
            "reports": {"r1": _make_report("r1", content=content)},
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.export_docx("r1", include_source_index=False)
        assert result is not None
        assert len(result) > 200

    def test_with_headings_and_lists(self):
        """标题和列表应正确转换"""
        content = "# Title\n\n## Subtitle\n\n- Item 1\n- Item 2\n  - Nested item\n\n---\n\nParagraph."
        storage = MockStorage({
            "reports": {"r1": _make_report("r1", content=content)},
            "papers": {},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.export_docx("r1", include_source_index=False)
        assert result is not None

    def test_without_source_index(self):
        """include_source_index=False 不包含来源索引"""
        storage = MockStorage({
            "reports": {"r1": _make_report()},
            "papers": {"p1": _make_paper("p1")},
            "evidence_records": {},
        })
        svc = ReportService(storage=storage)
        result = svc.export_docx("r1", include_source_index=False)
        assert result is not None
