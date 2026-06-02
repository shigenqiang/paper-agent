"""模块01 核心模型与存储 — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中 (port 5432)
    - 数据库 paper_agent 已创建
"""

import pytest


class TestPostgresStorage:
    """PostgresStorage 真实链路测试"""

    def test_table_exists(self, pg_storage):
        """核心表应存在"""
        core_tables = ["projects", "papers", "papers_pool", "paper_chunks", "evidence_records"]
        for table in core_tables:
            count = pg_storage.list_all(table)
            print(f"\n[table] {table}: {len(count)} rows")

    def test_upsert_and_get(self, pg_storage):
        """upsert 写入后 get_item 能读回"""
        test_id = "storage_test_01"
        pg_storage.upsert_item("projects", test_id, {
            "project_id": test_id, "name": "存储测试", "description": "test",
        })
        item = pg_storage.get_item("projects", test_id)
        assert item is not None
        assert item["name"] == "存储测试"
        pg_storage.delete_item("projects", test_id)

    def test_query_by_field(self, pg_storage):
        """query 按字段过滤"""
        pg_storage.upsert_item("projects", "q_test_1", {
            "project_id": "q_test_1", "name": "query_test", "description": "a",
        })
        pg_storage.upsert_item("projects", "q_test_2", {
            "project_id": "q_test_2", "name": "query_test", "description": "b",
        })
        results = pg_storage.query("projects", {"name": "query_test"})
        assert len(results) >= 2
        pg_storage.delete_item("projects", "q_test_1")
        pg_storage.delete_item("projects", "q_test_2")

    def test_column_filtering(self, pg_storage):
        """upsert 应过滤掉表中不存在的列"""
        test_id = "storage_test_col"
        pg_storage.upsert_item("projects", test_id, {
            "project_id": test_id,
            "name": "列过滤测试",
            "nonexistent_field": "should_be_ignored",
        })
        item = pg_storage.get_item("projects", test_id)
        assert item is not None
        assert "nonexistent_field" not in item
        pg_storage.delete_item("projects", test_id)

    def test_papers_pool_table(self, pg_storage):
        """papers_pool 表应可读写"""
        pool_id = "pool_test_001"
        pg_storage.upsert_item("papers_pool", pool_id, {
            "paper_id": pool_id,
            "pool_paper_id": pool_id,
            "title": "Pool Test Paper",
            "source_platform": "test",
        })
        item = pg_storage.get_item("papers_pool", pool_id)
        assert item is not None
        assert item["title"] == "Pool Test Paper"
        pg_storage.delete_item("papers_pool", pool_id)
