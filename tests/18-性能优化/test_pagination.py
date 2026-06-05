"""模块18 分页测试

验证 API 列表端点支持分页参数。
"""

import pytest
from unittest.mock import MagicMock


class TestPagination:
    """API 分页端点测试"""

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
        self.client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(self.app)

    def test_tasks_default_pagination(self):
        """默认分页参数: page=1, page_size=20"""
        resp = self.client.get("/api/rw/tasks")
        assert resp.status_code == 200
        body = resp.json()
        assert "pagination" in body
        pg = body["pagination"]
        assert pg["page"] == 1
        assert pg["page_size"] == 20
        assert "total" in pg
        assert "has_next" in pg

    def test_tasks_custom_page_size(self):
        """自定义 page_size"""
        resp = self.client.get("/api/rw/tasks?page=2&page_size=5")
        assert resp.status_code == 200
        pg = resp.json()["pagination"]
        assert pg["page"] == 2
        assert pg["page_size"] == 5

    def test_tasks_page_size_clamped(self):
        """page_size 超过 100 应被截断"""
        resp = self.client.get("/api/rw/tasks?page_size=500")
        assert resp.status_code == 200
        pg = resp.json()["pagination"]
        assert pg["page_size"] == 100

    def test_tasks_page_minimum_one(self):
        """page < 1 应被修正为 1"""
        resp = self.client.get("/api/rw/tasks?page=0")
        assert resp.status_code == 200
        pg = resp.json()["pagination"]
        assert pg["page"] == 1

    def test_list_paginated_storage_method(self):
        """PostgresStorage.list_paginated 方法签名正确"""
        from src.agents_v3.research_workspace.storage.postgres import PostgresStorage
        assert hasattr(PostgresStorage, "list_paginated")
        import inspect
        sig = inspect.signature(PostgresStorage.list_paginated)
        params = list(sig.parameters.keys())
        assert "table" in params
        assert "page" in params
        assert "page_size" in params
        assert "filters" in params
        assert "order_by" in params
