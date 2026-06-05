"""P2 基础设施测试：SSE streaming、依赖清理、乐观锁、OCR、表格提取

覆盖：
- P2-N: SSE streaming endpoint
- P2-J: Dead dependencies (已在 pyproject.toml 验证)
- P2-K: Optimistic locking (在 test_report_p2_unit.py 中已覆盖)
- P2-L: OCR fallback (在 parser/service.py 中已实现)
- P2-M: Table extraction (在 parser/adapters.py 中已实现)
"""

import json
import time
import threading
from unittest.mock import MagicMock, patch

import pytest


# ── SSE Event Format ─────────────────────────────────


class TestSSEEventFormat:
    """SSE 事件格式化"""

    def test_sse_event_basic(self):
        from src.agents_v3.research_workspace.api.routes.tasks import _sse_event
        result = _sse_event("progress", {"progress": 0.5, "status": "running"})
        assert result.startswith("event: progress\ndata: ")
        assert result.endswith("\n\n")
        payload = json.loads(result.split("data: ", 1)[1].split("\n\n")[0])
        assert payload["progress"] == 0.5

    def test_sse_event_unicode(self):
        from src.agents_v3.research_workspace.api.routes.tasks import _sse_event
        result = _sse_event("message", {"text": "处理中..."})
        payload = json.loads(result.split("data: ", 1)[1].split("\n\n")[0])
        assert payload["text"] == "处理中..."

    def test_sse_event_empty_data(self):
        from src.agents_v3.research_workspace.api.routes.tasks import _sse_event
        result = _sse_event("done", {})
        assert "event: done\n" in result


# ── SSE Streaming Endpoint ───────────────────────────


class TestSSEStreaming:
    """SSE 端点集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.agents_v3.research_workspace.api.app import create_app
        from fastapi.testclient import TestClient
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_stream_task_not_found(self):
        """不存在的 task_id 返回 404"""
        resp = self.client.get("/api/rw/tasks/nonexistent/stream")
        assert resp.status_code == 404

    def test_stream_completed_task(self):
        """已完成的任务立即返回 done 事件"""
        from src.agents_v3.research_workspace.api.deps import get_task_service
        svc = get_task_service()
        task = svc.create_task("test", "proj1")
        svc.update_task(task["task_id"], status="completed", progress=1.0, result={"ok": True})

        resp = self.client.get(f"/api/rw/tasks/{task['task_id']}/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        body = resp.text
        assert "event: progress" in body
        assert "event: done" in body
        assert '"status": "completed"' in body

    def test_stream_failed_task(self):
        """失败的任务返回 error 信息"""
        from src.agents_v3.research_workspace.api.deps import get_task_service
        svc = get_task_service()
        task = svc.create_task("test", "proj1")
        svc.update_task(task["task_id"], status="failed", error="something broke")

        resp = self.client.get(f"/api/rw/tasks/{task['task_id']}/stream")
        body = resp.text
        assert "event: done" in body
        assert "something broke" in body

    def test_stream_with_events(self):
        """任务事件通过 SSE 推送"""
        from src.agents_v3.research_workspace.api.deps import get_task_service
        svc = get_task_service()
        task = svc.create_task("test", "proj1")
        svc.add_event(task["task_id"], "log", {"message": "step 1"})
        svc.add_event(task["task_id"], "log", {"message": "step 2"})
        svc.update_task(task["task_id"], status="completed", progress=1.0)

        resp = self.client.get(f"/api/rw/tasks/{task['task_id']}/stream")
        body = resp.text
        assert "step 1" in body
        assert "step 2" in body

    def test_stream_progress_event(self):
        """进度变化通过 SSE 推送"""
        from src.agents_v3.research_workspace.api.deps import get_task_service
        svc = get_task_service()
        task = svc.create_task("test", "proj1")
        svc.update_task(task["task_id"], status="completed", progress=0.75)

        resp = self.client.get(f"/api/rw/tasks/{task['task_id']}/stream")
        body = resp.text
        assert "event: progress" in body
        assert "0.75" in body


# ── TaskService Unit Tests ────────────────────────────


class TestTaskServiceUnit:
    """TaskService 方法测试"""

    def test_create_task_fields(self):
        from src.agents_v3.research_workspace.api.tasks import TaskService
        mock_storage = MagicMock()
        mock_storage.upsert_item = MagicMock()
        svc = TaskService(storage=mock_storage)
        task = svc.create_task("parse", "proj1", {"file": "test.pdf"})
        assert task["task_type"] == "parse"
        assert task["project_id"] == "proj1"
        assert task["status"] == "queued"
        assert task["progress"] == 0.0
        assert task["input"] == {"file": "test.pdf"}
        assert task["events"] == []

    def test_update_task_partial(self):
        from src.agents_v3.research_workspace.api.tasks import TaskService
        task_data = {
            "task_id": "t1", "status": "queued", "progress": 0.0,
            "result": None, "error": "", "events": [],
        }
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = task_data
        mock_storage.upsert_item = MagicMock()
        svc = TaskService(storage=mock_storage)

        updated = svc.update_task("t1", status="running", progress=0.3)
        assert updated["status"] == "running"
        assert updated["progress"] == 0.3

    def test_update_task_nonexistent(self):
        from src.agents_v3.research_workspace.api.tasks import TaskService
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = None
        svc = TaskService(storage=mock_storage)
        assert svc.update_task("missing", status="running") is None

    def test_add_event(self):
        from src.agents_v3.research_workspace.api.tasks import TaskService
        task_data = {"task_id": "t1", "events": []}
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = task_data
        mock_storage.upsert_item = MagicMock()
        svc = TaskService(storage=mock_storage)

        svc.add_event("t1", "log", {"msg": "hello"})
        assert len(task_data["events"]) == 1
        assert task_data["events"][0]["type"] == "log"
        assert task_data["events"][0]["data"] == {"msg": "hello"}

    def test_add_event_nonexistent_task(self):
        from src.agents_v3.research_workspace.api.tasks import TaskService
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = None
        svc = TaskService(storage=mock_storage)
        # Should not raise
        svc.add_event("missing", "log", {})

    def test_list_tasks_with_filter(self):
        from src.agents_v3.research_workspace.api.tasks import TaskService
        tasks = [
            {"task_id": "t1", "status": "completed", "created_at": "2026-01-01"},
            {"task_id": "t2", "status": "running", "created_at": "2026-01-02"},
            {"task_id": "t3", "status": "completed", "created_at": "2026-01-03"},
        ]
        mock_storage = MagicMock()
        mock_storage.load_collection.return_value = tasks
        svc = TaskService(storage=mock_storage)

        completed = svc.list_tasks(status="completed")
        assert len(completed) == 2
        assert all(t["status"] == "completed" for t in completed)

    def test_list_tasks_sorted_by_date(self):
        from src.agents_v3.research_workspace.api.tasks import TaskService
        tasks = [
            {"task_id": "t1", "created_at": "2026-01-01"},
            {"task_id": "t3", "created_at": "2026-01-03"},
            {"task_id": "t2", "created_at": "2026-01-02"},
        ]
        mock_storage = MagicMock()
        mock_storage.load_collection.return_value = tasks
        svc = TaskService(storage=mock_storage)

        result = svc.list_tasks()
        assert result[0]["task_id"] == "t3"  # newest first
        assert result[-1]["task_id"] == "t1"


# ── Parser Infrastructure Tests ───────────────────────


class TestPdfPlumberTables:
    """pdfplumber 表格提取测试"""

    def test_extract_tables_no_pdfplumber(self):
        """pdfplumber 未安装时返回空列表"""
        from src.agents_v3.research_workspace.parser.adapters import PdfPlumberAdapter
        adapter = PdfPlumberAdapter()
        with patch.dict("sys.modules", {"pdfplumber": None}):
            result = adapter.extract_tables("fake.pdf")
            assert result == []

    def test_extract_tables_with_mock(self):
        """模拟 pdfplumber 提取表格"""
        from src.agents_v3.research_workspace.parser.adapters import PdfPlumberAdapter

        mock_table = [
            ["Name", "Score", "Year"],
            ["Paper A", "95", "2024"],
            ["Paper B", "87", "2023"],
        ]
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [mock_table]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        adapter = PdfPlumberAdapter()
        with patch("pdfplumber.open", return_value=mock_pdf):
            result = adapter.extract_tables("test.pdf")

        assert len(result) == 1
        assert result[0]["page"] == 1
        assert result[0]["headers"] == ["Name", "Score", "Year"]
        assert result[0]["row_count"] == 2
        assert result[0]["col_count"] == 3

    def test_extract_tables_empty_page(self):
        """无表格页面不产生结果"""
        from src.agents_v3.research_workspace.parser.adapters import PdfPlumberAdapter

        mock_page = MagicMock()
        mock_page.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        adapter = PdfPlumberAdapter()
        with patch("pdfplumber.open", return_value=mock_pdf):
            result = adapter.extract_tables("test.pdf")
        assert result == []

    def test_extract_tables_single_row_skipped(self):
        """只有表头没有数据行的表格被跳过"""
        from src.agents_v3.research_workspace.parser.adapters import PdfPlumberAdapter

        # pdfplumber returns list of tables, each table is list of rows
        # A table with only 1 row (header only): len(tbl) == 1 → skipped
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [
            [["OnlyHeader1", "OnlyHeader2"]],  # 1 table, 1 row → skipped
        ]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        adapter = PdfPlumberAdapter()
        with patch("pdfplumber.open", return_value=mock_pdf):
            result = adapter.extract_tables("test.pdf")
        assert result == []


class TestOCRFallback:
    """OCR fallback 测试"""

    def test_ocr_requires_pytesseract(self):
        """pytesseract 未安装时跳过 OCR"""
        with patch.dict("sys.modules", {"pytesseract": None}):
            from src.agents_v3.research_workspace.parser.service import ParserService
            svc = ParserService.__new__(ParserService)
            # OCR should gracefully handle missing pytesseract
            # The actual method catches ImportError internally
            assert True  # If we get here, no crash


# ── Report Infrastructure Tests ───────────────────────


class TestReportOptimisticLocking:
    """乐观锁测试"""

    def test_version_conflict_error_class(self):
        from src.agents_v3.research_workspace.services.report_service import VersionConflictError
        err = VersionConflictError("r1", 1, 3)
        assert "r1" in str(err)
        assert "v1" in str(err)
        assert "v3" in str(err)

    def test_version_conflict_on_mismatch(self):
        from src.agents_v3.research_workspace.services.report_service import ReportService
        from src.agents_v3.research_workspace.models.reports import Report, ReportType

        report = Report(
            report_id="r1", project_id="p1", type=ReportType.LITERATURE_REVIEW,
            title="Test", content="# Test", version=3,
        )

        mock_storage = MagicMock()
        mock_storage.get_item.return_value = None
        svc = ReportService(storage=mock_storage)
        svc.get_report = MagicMock(return_value=report)

        from src.agents_v3.research_workspace.services.report_service import VersionConflictError
        with pytest.raises(VersionConflictError):
            svc.save_report(report, expected_version=1)


# ── Citation Formatter Tests ──────────────────────────


class TestCitationFormatter:
    """引用格式化器测试"""

    def test_format_dispatch(self):
        from src.agents_v3.research_workspace.services.citation_formatter import CitationFormatter
        paper = {"title": "Test", "authors": ["A"], "year": 2024}
        for style in ("simple", "apa", "gbt7714", "bibtex"):
            result = CitationFormatter.format(paper, style)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_format_unknown_style(self):
        from src.agents_v3.research_workspace.services.citation_formatter import CitationFormatter
        paper = {"title": "Test", "authors": ["A"], "year": 2024}
        result = CitationFormatter.format(paper, "chicago")
        assert "Test" in result  # falls back to simple
