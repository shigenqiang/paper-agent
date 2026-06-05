"""P3-A 异步任务编排测试

覆盖：
- 报告生成端点返回 202 + task_id
- 任务完成/失败状态
- SSE 流式推送
- 图谱构建端点返回 202
- 证据构建端点返回 202
"""

import time
import threading
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def mock_app():
    """创建带 mock storage 的 FastAPI app"""
    from src.agents_v3.research_workspace.api.app import create_app
    mock_storage = MagicMock()
    app = create_app(storage=mock_storage)
    return app


@pytest.fixture()
def mock_task_service():
    """创建 mock 的 TaskService"""
    from src.agents_v3.research_workspace.api.tasks import TaskService
    mock_storage = MagicMock()
    return TaskService(storage=mock_storage)


class TestReportAsyncTask:
    """报告生成异步任务测试"""

    def test_review_returns_202_with_task_id(self, mock_app):
        """综述生成返回 202 和 task_id"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.reports._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_review_generator") as mock_gen, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_svc = MagicMock()
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {"title": "Test Review", "sections": []}
            mock_svc.generate.return_value = mock_result
            mock_gen.return_value = mock_svc

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_test123", "status": "queued", "progress": 0.0}

            resp = client.post("/api/rw/projects/proj1/reports/literature-review", json={
                "scope": {"project_id": "proj1"},
            })
            assert resp.status_code == 202
            data = resp.json()
            assert "task_id" in data.get("data", {})
            assert data["data"]["status"] == "queued"

    def test_innovation_returns_202_with_task_id(self, mock_app):
        """创新点报告生成返回 202 和 task_id"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.reports._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_innovation_generator") as mock_gen, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_svc = MagicMock()
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {"title": "Test Innovation", "points": []}
            mock_svc.generate.return_value = mock_result
            mock_gen.return_value = mock_svc

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_innov123", "status": "queued", "progress": 0.0}

            resp = client.post("/api/rw/projects/proj1/reports/innovation", json={
                "scope": {"project_id": "proj1"},
            })
            assert resp.status_code == 202

    def test_review_task_completes(self, mock_app):
        """综述生成任务最终完成"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.reports._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_review_generator") as mock_gen, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_svc = MagicMock()
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {"title": "Test", "sections": []}
            mock_svc.generate.return_value = mock_result
            mock_gen.return_value = mock_svc

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_test123", "status": "queued", "progress": 0.0}
            real_ts.update_task = MagicMock()
            real_ts.add_event = MagicMock()

            resp = client.post("/api/rw/projects/proj1/reports/literature-review", json={
                "scope": {"project_id": "proj1"},
            })
            assert resp.status_code == 202

            # Wait for background thread to complete
            time.sleep(0.5)

            # Verify update_task was called with completed status
            calls = real_ts.update_task.call_args_list
            status_calls = [c for c in calls if c.kwargs.get("status") == "completed"]
            assert len(status_calls) > 0

    def test_review_task_failure(self, mock_app):
        """综述生成任务失败时状态为 failed"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.reports._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_review_generator") as mock_gen, \
             patch("src.agents_v3.research_workspace.api.routes.reports.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_svc = MagicMock()
            mock_svc.generate.side_effect = RuntimeError("LLM timeout")
            mock_gen.return_value = mock_svc

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_fail123", "status": "queued", "progress": 0.0}
            real_ts.update_task = MagicMock()
            real_ts.add_event = MagicMock()

            resp = client.post("/api/rw/projects/proj1/reports/literature-review", json={
                "scope": {"project_id": "proj1"},
            })
            assert resp.status_code == 202

            time.sleep(0.5)

            calls = real_ts.update_task.call_args_list
            fail_calls = [c for c in calls if c.kwargs.get("status") == "failed"]
            assert len(fail_calls) > 0
            assert "LLM timeout" in fail_calls[0].kwargs.get("error", "")


class TestKnowledgeAsyncTask:
    """知识图谱异步任务测试"""

    def test_graph_build_returns_202(self, mock_app):
        """图谱构建返回 202"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.knowledge._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_graph_service") as mock_gs, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_svc = MagicMock()
            mock_graph = MagicMock()
            mock_graph.nodes = [1, 2, 3]
            mock_graph.edges = [1, 2]
            mock_svc.build_project_graph.return_value = mock_graph
            mock_gs.return_value = mock_svc

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_kg1", "status": "queued", "progress": 0.0}

            resp = client.post("/api/rw/projects/proj1/kg/build")
            assert resp.status_code == 202
            assert "task_id" in resp.json().get("data", {})

    def test_evidence_build_returns_202(self, mock_app):
        """证据构建返回 202"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.knowledge._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_evidence_service") as mock_es, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_svc = MagicMock()
            mock_svc.build_for_project.return_value = []
            mock_es.return_value = mock_svc

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_ev1", "status": "queued", "progress": 0.0}

            resp = client.post("/api/rw/projects/proj1/evidence/build")
            assert resp.status_code == 202

    def test_graph_rebuild_returns_202(self, mock_app):
        """图谱全量重建返回 202"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.knowledge._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_graph_service") as mock_gs, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_svc = MagicMock()
            mock_graph = MagicMock()
            mock_graph.nodes = []
            mock_graph.edges = []
            mock_svc.build_project_graph.return_value = mock_graph
            mock_gs.return_value = mock_svc

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_kg2", "status": "queued", "progress": 0.0}

            resp = client.post("/api/rw/projects/proj1/kg/rebuild")
            assert resp.status_code == 202

    def test_extract_entities_returns_202(self, mock_app):
        """实体提取返回 202"""
        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.knowledge._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_graph_extractor") as mock_ge, \
             patch("src.agents_v3.research_workspace.api.routes.knowledge.get_task_service") as mock_ts:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_ext = MagicMock()
            mock_ext.extract_from_project.return_value = {"papers": 5, "entities": 20}
            mock_ge.return_value = mock_ext

            real_ts = mock_ts.return_value
            real_ts.create_task.return_value = {"task_id": "task_ext1", "status": "queued", "progress": 0.0}

            resp = client.post("/api/rw/projects/proj1/kg/extract")
            assert resp.status_code == 202


class TestSSEAsyncIntegration:
    """SSE + 异步任务集成测试"""

    def test_sse_streams_task_progress(self, mock_app):
        """SSE 能推送异步任务的进度"""
        from src.agents_v3.research_workspace.api.tasks import TaskService
        # Use a dict-backed mock so data persists across calls
        _store: dict = {}
        mock_storage = MagicMock()
        mock_storage.upsert_item.side_effect = lambda t, tid, d: _store.update({tid: dict(d)})
        mock_storage.get_item.side_effect = lambda t, tid: _store.get(tid)
        svc = TaskService(storage=mock_storage)
        task = svc.create_task("test_async", "proj1")

        # Simulate async work
        svc.update_task(task["task_id"], status="running", progress=0.5)
        svc.add_event(task["task_id"], "stage", {"name": "processing"})
        svc.update_task(task["task_id"], status="completed", progress=1.0, result={"ok": True})

        client = TestClient(mock_app)
        with patch("src.agents_v3.research_workspace.api.routes.tasks.get_task_service", return_value=svc):
            resp = client.get(f"/api/rw/tasks/{task['task_id']}/stream")
            body = resp.text
            assert "event: progress" in body
            assert "event: stage" in body
            assert "event: done" in body
            assert "completed" in body
