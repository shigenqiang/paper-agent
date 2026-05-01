"""
API Server 集成测试

使用 aiohttp test client 直接测试，不需要手动启动服务器。

运行方式:
    python -m pytest tests/test_api_server.py -v -s
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiohttp.test_utils import AioHTTPTestCase
from aiohttp import web


class TestAPIServer(AioHTTPTestCase):

    async def get_application(self):
        from src.agents_v2.api_server import create_app
        return create_app()

    # ===== 公开端点（不需要 API Key）=====

    async def test_root(self):
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        data = await resp.json()
        assert data["name"] == "Paper Research API"
        assert "version" in data

    async def test_health(self):
        resp = await self.client.request("GET", "/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "healthy"

    async def test_docs(self):
        resp = await self.client.request("GET", "/docs")
        assert resp.status == 200
        assert "text/html" in resp.content_type

    # ===== 认证测试 =====

    async def test_missing_api_key_returns_401(self):
        resp = await self.client.request("POST", "/api/search", json={"query": "test"})
        assert resp.status == 401
        data = await resp.json()
        assert "Missing API key" in data["error"]

    async def test_invalid_api_key_returns_401(self):
        resp = await self.client.request(
            "POST", "/api/search",
            json={"query": "test"},
            headers={"X-API-Key": "wrong-key"}
        )
        assert resp.status == 401
        data = await resp.json()
        assert "Invalid API key" in data["error"]

    # ===== 搜索接口 =====

    async def test_search_missing_query(self):
        resp = await self.client.request(
            "POST", "/api/search",
            json={},
            headers={"X-API-Key": "dev-api-key"}
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["success"] is False

    async def test_search_arxiv(self):
        resp = await self.client.request(
            "POST", "/api/search",
            json={"query": "deep learning", "source": "arxiv", "max_results": 3},
            headers={"X-API-Key": "dev-api-key"}
        )
        assert resp.status == 200
        data = await resp.json()
        assert "papers" in data

    # ===== 意图路由接口 =====

    async def test_route_missing_request(self):
        resp = await self.client.request(
            "POST", "/api/route",
            json={},
            headers={"X-API-Key": "dev-api-key"}
        )
        assert resp.status == 400

    async def test_route_intent(self):
        resp = await self.client.request(
            "POST", "/api/route",
            json={"user_request": "帮我搜索关于深度学习的论文"},
            headers={"X-API-Key": "dev-api-key"}
        )
        assert resp.status == 200
        data = await resp.json()
        assert "confidence" in data
        assert "suggested_agents" in data

    # ===== 文献综述接口 =====

    async def test_literature_missing_topic(self):
        resp = await self.client.request(
            "POST", "/api/literature",
            json={},
            headers={"X-API-Key": "dev-api-key"}
        )
        assert resp.status == 400

    # ===== 开题报告接口 =====

    async def test_proposal_missing_topic(self):
        resp = await self.client.request(
            "POST", "/api/proposal",
            json={},
            headers={"X-API-Key": "dev-api-key"}
        )
        assert resp.status == 400

    # ===== 批量接口 =====

    async def test_batch_missing_requests(self):
        resp = await self.client.request(
            "POST", "/api/batch",
            json={},
            headers={"X-API-Key": "dev-api-key"}
        )
        assert resp.status == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
