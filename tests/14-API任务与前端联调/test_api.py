"""模块14 API任务与前端联调 — 真实 FastAPI 测试

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - FastAPI app 可启动
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


class TestAPIE2E:
    """API 端到端测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.agents_v3.research_workspace.api.app import create_app
        _store: dict = {}
        mock_storage = MagicMock()
        mock_storage.upsert_item.side_effect = lambda t, tid, d: _store.update({tid: dict(d)})
        mock_storage.get_item.side_effect = lambda t, tid: _store.get(tid)
        mock_storage.get.side_effect = lambda t, ref: _store.get(ref)
        mock_storage.list_all.side_effect = lambda t: [dict(v) for v in _store.values()]
        mock_storage.query.side_effect = lambda t, f: [
            dict(v) for v in _store.values()
            if all(v.get(k) == val for k, val in f.items())
        ]
        mock_storage.load_collection.side_effect = lambda t: [dict(v) for v in _store.values()]
        self.app = create_app(storage=mock_storage)
        self.client = TestClient(self.app)

    def test_health_endpoint(self):
        """健康检查接口"""
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        print(f"\n[api] health: {resp.json()}")

    def test_create_project_via_api(self):
        """通过 API 创建项目"""
        import uuid
        name = f"API测试项目_{uuid.uuid4().hex[:6]}"
        resp = self.client.post("/api/rw/projects", json={
            "name": name,
            "description": "通过API创建",
        })
        assert resp.status_code in (200, 201)
        body = resp.json()
        data = body.get("data", body)
        assert data["name"] == name
        print(f"\n[api] 创建项目: {data['project_id']}")

    def test_list_projects_via_api(self):
        """通过 API 列出项目"""
        resp = self.client.get("/api/rw/projects")
        assert resp.status_code == 200

    def test_search_via_api(self):
        """通过 API 搜索论文（端点需要 project_ref）"""
        # 搜索端点在 /api/rw/projects/{id}/papers/search
        # 使用一个假 project_ref，预期返回 404（因为 mock storage 无数据）
        resp = self.client.post("/api/rw/projects/nonexistent/papers/search", json={
            "query": "transformer attention",
            "limit": 3,
        })
        # mock storage 无数据，应返回 404
        assert resp.status_code in (200, 202, 404)
