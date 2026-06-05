"""模块03 论文库搜索导入 — 真实 HTTP API + PostgreSQL

测试全部通过 HTTP API 走真实链路：
  POST /api/rw/projects                → 创建项目
  POST /api/rw/projects/{id}/papers/search → 搜索入库

前置条件:
    - Docker 容器 postgres (5432) + qdrant (6333) 运行中
    - 服务运行在 http://localhost:8000
    - 网络可达 openalex / arxiv / semantic scholar API
"""

import time

import pytest
import requests

BASE = "http://localhost:8000"


def api(method: str, path: str, body: dict | None = None) -> dict:
    """调用真实 HTTP API"""
    url = f"{BASE}{path}"
    resp = requests.request(method, url, json=body, timeout=300)
    resp.raise_for_status()
    return resp.json()


def wait_for_service(max_wait: int = 15) -> bool:
    """等待服务就绪"""
    for _ in range(max_wait):
        try:
            r = requests.get(f"{BASE}/api/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="module", autouse=True)
def ensure_service():
    """确保服务可用"""
    if not wait_for_service():
        pytest.skip("服务未启动，请先运行 python -m src.service")


@pytest.fixture(scope="module")
def project_id():
    """通过 API 创建测试项目，返回 project_id"""
    name = f"search_test_{int(time.time())}"
    result = api("POST", "/api/rw/projects", {"name": name})
    pid = result["data"]["project_id"]
    print(f"\n[setup] 创建项目: {pid}")
    yield pid
    # 不清理，保留入库数据


class TestSearchViaAPI:
    """通过真实 HTTP API 测试搜索入库全流程"""

    def test_01_search_returns_results(self, project_id):
        """POST /papers/search 能从真实 API 拿到结果"""
        body = {"query": "large language model", "limit": 5}
        result = api("POST", f"/api/rw/projects/{project_id}/papers/search", body)
        data = result["data"]

        results = data["results"]
        print(f"\n[search] 'large language model' 返回 {len(results)} 条")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. [{r.get('source', '')}] {r.get('title', '')[:60]}...")

        assert len(results) > 0, "搜索应返回至少 1 条结果"
        assert results[0].get("title"), "结果应有标题"

    def test_02_papers_written_to_db(self, project_id, pg_storage):
        """搜索后论文应写入 papers 表"""
        body = {"query": "BERT pre-training", "limit": 3}
        api("POST", f"/api/rw/projects/{project_id}/papers/search", body)

        stored = pg_storage.query("papers", {"project_id": project_id})
        print(f"\n[papers] 入库 {len(stored)} 篇论文")
        for p in stored[:3]:
            print(f"  - {p['paper_id']}")

        assert len(stored) > 0, "搜索后应有论文写入 papers 表"

    def test_03_queries_written_to_db(self, project_id, pg_storage):
        """搜索后查询记录应写入 queries 表"""
        body = {"query": "transformer attention", "limit": 3}
        api("POST", f"/api/rw/projects/{project_id}/papers/search", body)

        queries = pg_storage.list_all("queries")
        matching = [q for q in queries if q.get("query_text") == "transformer attention"]
        print(f"\n[queries] 匹配查询: {len(matching)} 条")
        assert len(matching) >= 1, "应写入 queries 表记录"
        assert matching[0]["query_id"], "应有 query_id"

    def test_04_topic_scores_written(self, project_id, pg_storage):
        """搜索后 topic_scores 应记录 paper-query 关联"""
        body = {"query": "knowledge graph embedding", "limit": 3}
        api("POST", f"/api/rw/projects/{project_id}/papers/search", body)

        scores = pg_storage.list_all("topic_scores")
        with_query = [s for s in scores if s.get("query_id")]
        print(f"\n[topic_scores] 带 query_id 的记录: {len(with_query)} 条")
        for s in with_query[:3]:
            print(f"  - paper={s['paper_id'][:30]} query={s['query_id']} dense={s.get('dense_score', 0):.3f}")

        assert len(with_query) > 0, "应写入 topic_scores 记录"

    def test_05_dedup_on_reimport(self, project_id, pg_storage):
        """重复搜索同一查询不应创建重复论文"""
        body = {"query": "retrieval augmented generation", "limit": 3}

        api("POST", f"/api/rw/projects/{project_id}/papers/search", body)
        count_first = len(pg_storage.query("papers", {"project_id": project_id}))

        api("POST", f"/api/rw/projects/{project_id}/papers/search", body)
        count_second = len(pg_storage.query("papers", {"project_id": project_id}))

        print(f"\n[dedup] 第一次: {count_first} 篇, 第二次: {count_second} 篇")
        assert count_second == count_first, "重复搜索不应创建重复论文"

    def test_06_response_structure(self, project_id):
        """API 返回正确的响应结构"""
        body = {"query": "chain of thought prompting", "limit": 5}
        result = api("POST", f"/api/rw/projects/{project_id}/papers/search", body)
        data = result["data"]

        assert "query" in data, "应有 query 字段"
        assert "results" in data, "应有 results 字段"
        assert "result_count" in data, "应有 result_count 字段"
        assert isinstance(data["results"], list), "results 应为列表"

        if data["results"]:
            r = data["results"][0]
            assert r.get("title"), "结果应有标题"
            assert r.get("source"), "结果应有来源"
            print(f"\n[response] {len(data['results'])} 条结果, total={data['result_count']}")

    def test_07_papers_pool_populated(self, project_id, pg_storage):
        """搜索后 papers_pool 应有数据"""
        body = {"query": "prompt engineering", "limit": 3}
        api("POST", f"/api/rw/projects/{project_id}/papers/search", body)

        pool = pg_storage.list_all("papers_pool")
        print(f"\n[papers_pool] 全局论文池: {len(pool)} 条")
        assert len(pool) > 0, "应写入 papers_pool"


class TestPostgresCRUD:
    """PostgresStorage 基本 CRUD 操作"""

    def test_crud_operations(self, pg_storage):
        """CREATE / READ / UPDATE / DELETE 全流程"""
        test_id = "e2e_crud_test"
        data = {"project_id": test_id, "name": "crud_test_project", "description": "test"}

        # CREATE
        pg_storage.upsert_item("projects", test_id, data)

        # READ
        item = pg_storage.get_item("projects", test_id)
        assert item is not None
        assert item["name"] == "crud_test_project"

        # UPDATE
        data["description"] = "updated"
        pg_storage.upsert_item("projects", test_id, data)
        item2 = pg_storage.get_item("projects", test_id)
        assert item2["description"] == "updated"

        # DELETE
        pg_storage.delete_item("projects", test_id)
        item3 = pg_storage.get_item("projects", test_id)
        assert item3 is None

        print("\n[CRUD] PostgreSQL CRUD 全部通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
