"""模块14 API任务与前端联调 — 真实 FastAPI 测试

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - FastAPI app 可启动
"""

import pytest
from fastapi.testclient import TestClient


class TestAPIE2E:
    """API 端到端测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.agents_v3.research_workspace.api.app import create_app
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_health_endpoint(self):
        """健康检查接口"""
        resp = self.client.get("/api/rw/health")
        assert resp.status_code == 200
        print(f"\n[api] health: {resp.json()}")

    def test_create_project_via_api(self):
        """通过 API 创建项目"""
        resp = self.client.post("/api/rw/projects", json={
            "name": "API测试项目",
            "description": "通过API创建",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "API测试项目"
        print(f"\n[api] 创建项目: {data['project_id']}")

    def test_list_projects_via_api(self):
        """通过 API 列出项目"""
        resp = self.client.get("/api/rw/projects")
        assert resp.status_code == 200

    def test_search_via_api(self):
        """通过 API 搜索论文"""
        resp = self.client.post("/api/rw/search", json={
            "query": "transformer attention",
            "limit": 3,
        })
        # 可能返回 200 或异步任务 202
        assert resp.status_code in (200, 202)
