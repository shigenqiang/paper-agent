"""P3-D 结构化日志集成测试

覆盖：
- 请求中间件绑定 request_id
- 请求中间件提取 project_id
- log_operation 计时
- sanitize_payload 清洗敏感字段
- clear_context 清理
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents_v3.research_workspace.evaluation.logging_utils import (
    bind_context,
    clear_context,
    get_context,
    log_operation,
    sanitize_payload,
)


class TestLoggingContext:
    """日志上下文测试"""

    def test_bind_context_sets_fields(self):
        """bind_context 设置上下文字段"""
        bind_context(request_id="req_123", project_id="proj1", task_id="task_1")
        ctx = get_context()
        assert ctx["request_id"] == "req_123"
        assert ctx["project_id"] == "proj1"
        assert ctx["task_id"] == "task_1"
        clear_context()

    def test_clear_context_resets_all(self):
        """clear_context 重置所有字段"""
        bind_context(request_id="req_123", project_id="proj1")
        clear_context()
        ctx = get_context()
        assert ctx["request_id"] == ""
        assert ctx["project_id"] == ""

    def test_bind_context_partial_update(self):
        """bind_context 只更新非空字段"""
        bind_context(request_id="req_1")
        bind_context(project_id="proj1")
        ctx = get_context()
        assert ctx["request_id"] == "req_1"
        assert ctx["project_id"] == "proj1"
        clear_context()


class TestLogOperation:
    """log_operation 测试"""

    def test_log_operation_success(self):
        """成功操作记录 started 和 completed"""
        with patch("src.agents_v3.research_workspace.evaluation.logging_utils.log_event") as mock_log:
            with log_operation("test.op", project_id="proj1"):
                pass

        calls = [c[0][0] for c in mock_log.call_args_list]
        assert "test.op.started" in calls
        assert "test.op.completed" in calls

    def test_log_operation_failure(self):
        """失败操作记录 started 和 failed"""
        with patch("src.agents_v3.research_workspace.evaluation.logging_utils.log_event") as mock_log:
            with pytest.raises(ValueError):
                with log_operation("test.op"):
                    raise ValueError("boom")

        calls = [c[0][0] for c in mock_log.call_args_list]
        assert "test.op.started" in calls
        assert "test.op.failed" in calls

    def test_log_operation_timing(self):
        """completed 事件包含 elapsed_ms"""
        import time
        with patch("src.agents_v3.research_workspace.evaluation.logging_utils.log_event") as mock_log:
            with log_operation("test.op"):
                time.sleep(0.01)

        completed_call = [c for c in mock_log.call_args_list if c[0][0] == "test.op.completed"]
        assert len(completed_call) == 1
        assert completed_call[0].kwargs.get("elapsed_ms", 0) >= 0


class TestSanitizePayload:
    """payload 清洗测试"""

    def test_removes_sensitive_keys(self):
        """移除敏感字段"""
        data = {"api_key": "sk-123", "title": "Test", "password": "secret"}
        result = sanitize_payload(data)
        assert "api_key" not in result
        assert "password" not in result
        assert result["title"] == "Test"

    def test_hashes_long_strings(self):
        """长字符串被哈希"""
        data = {"content": "x" * 600}
        result = sanitize_payload(data)
        assert len(result["content"]) < len(data["content"])

    def test_nested_dict_sanitized(self):
        """嵌套字典也被清洗"""
        data = {"outer": {"api_key": "sk-123", "name": "test"}}
        result = sanitize_payload(data)
        assert "api_key" not in result["outer"]
        assert result["outer"]["name"] == "test"


class TestRequestMiddleware:
    """请求中间件集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.agents_v3.research_workspace.api.app import create_app
        from fastapi.testclient import TestClient
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_request_id_header(self):
        """响应包含 X-Request-ID header"""
        resp = self.client.get("/api/health")
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"].startswith("req_")

    def test_duration_header(self):
        """响应包含 X-Duration-Ms header"""
        resp = self.client.get("/api/health")
        assert "X-Duration-Ms" in resp.headers
        assert int(resp.headers["X-Duration-Ms"]) >= 0
