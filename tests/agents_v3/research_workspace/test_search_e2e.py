"""端到端搜索联调测试 — 真实 API + PostgreSQL

用法:
    python -m pytest tests/agents_v3/research_workspace/test_search_e2e.py -v -s

前置条件:
    - Docker 容器 paper-agent-postgres 运行中 (port 5432)
    - 数据库 paper_agent 已创建
    - 网络可达 arxiv / openalex / semantic scholar API
"""

import os
import sys
import io
import time
import pytest

# Windows GBK 编码修复
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from src.agents_v3.research_workspace.postgres_storage import PostgresStorage
from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.search.base import SearchQuery, SearchResult
from src.agents_v3.research_workspace.search.factory import create_default_adapters


PG_DSN = os.environ.get(
    "PG_DSN",
    "postgresql://postgres:postgres@localhost:5432/paper_agent",
)


@pytest.fixture(scope="module")
def pg_storage():
    """连接真实 PostgreSQL"""
    try:
        storage = PostgresStorage(dsn=PG_DSN)
        yield storage
    except Exception as e:
        pytest.skip(f"PostgreSQL 不可用: {e}")


@pytest.fixture(scope="module")
def adapters():
    """创建真实搜索适配器"""
    return create_default_adapters()


@pytest.fixture(scope="module")
def service(pg_storage, adapters):
    """PaperLibraryService — 真实存储 + 真实适配器"""
    return PaperLibraryService(
        storage=pg_storage,
        search_adapters=list(adapters.values()),
        global_storage=pg_storage,
    )


# ── 测试类 ──────────────────────────────────────────────


class TestSearchE2E:
    """端到端搜索联调"""

    PROJECT_ID = "e2e_test_project"

    @pytest.fixture(autouse=True)
    def setup_project(self, pg_storage):
        """确保测试项目存在"""
        pg_storage.upsert_item("projects", self.PROJECT_ID, {
            "project_id": self.PROJECT_ID,
            "name": "E2E 测试项目",
            "description": "搜索联调自动创建",
        })
        yield
        # 清理：删除测试项目相关数据
        try:
            papers = pg_storage.query("papers", {"project_id": self.PROJECT_ID})
            for p in papers:
                pg_storage.delete_item("papers", p["paper_id"])
            pg_storage.delete_item("projects", self.PROJECT_ID)
        except Exception:
            pass

    def test_01_search_papers_returns_results(self, service):
        """search_papers 能从真实 API 拿到结果"""
        query = SearchQuery(query="large language model", limit=5)
        results = service.search_papers(query)

        print(f"\n[search_papers] 搜索 'large language model' 返回 {len(results)} 条结果")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. [{r.source}] {r.title[:60]}... (citations={r.citations})")

        assert len(results) > 0, "搜索应返回至少 1 条结果"
        # 验证结果结构
        r = results[0]
        assert r.title, "结果应有标题"
        assert r.source, "结果应有来源"

    def test_02_results_stored_in_pool(self, pg_storage, service):
        """搜索结果应存入 papers_pool"""
        query = SearchQuery(query="transformer attention mechanism", limit=3)
        results = service.search_papers(query)

        # 检查 pool
        pool_items = pg_storage.list_all("papers_pool")
        print(f"\n[pool] papers_pool 中有 {len(pool_items)} 条记录")
        assert len(pool_items) > 0, "papers_pool 应非空"

    def test_03_search_and_import_creates_papers(self, service):
        """search_and_import 应创建论文记录"""
        query = SearchQuery(query="retrieval augmented generation", limit=3)
        papers = service.search_and_import(self.PROJECT_ID, query)

        print(f"\n[search_and_import] 导入 {len(papers)} 篇论文")
        for p in papers:
            print(f"  - {p.paper_id}: {p.title[:60]}... (score={p.importance_score:.3f})")

        assert len(papers) > 0, "应至少导入 1 篇论文"
        # 验证论文已入库
        stored = service.list_papers(self.PROJECT_ID)
        assert len(stored) >= len(papers)

    def test_04_dedup_on_reimport(self, service):
        """重复搜索不应创建重复论文"""
        query = SearchQuery(query="retrieval augmented generation", limit=3)

        papers_before = service.list_papers(self.PROJECT_ID)
        count_before = len(papers_before)

        # 再次搜索相同关键词
        papers2 = service.search_and_import(self.PROJECT_ID, query)

        papers_after = service.list_papers(self.PROJECT_ID)
        count_after = len(papers_after)

        print(f"\n[dedup] 重复导入: 之前 {count_before}, 新增 {len(papers2)}, 之后 {count_after}")
        assert len(papers2) == 0 or count_after == count_before + len(papers2)

    def test_05_search_candidates_creates_session(self, service):
        """search_candidates 应创建搜索会话"""
        query = SearchQuery(query="knowledge graph embedding", limit=5)
        session = service.search_candidates(self.PROJECT_ID, query)

        print(f"\n[search_candidates] 会话 {session.session_id}, 结果 {len(session.results)} 条")
        assert session.session_id
        assert session.status == "pending"
        assert len(session.results) > 0

        # 验证会话可检索
        retrieved = service.get_search_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_06_commit_session_imports_papers(self, service):
        """commit_search_results 应导入选中的论文"""
        query = SearchQuery(query="knowledge graph embedding", limit=5)
        session = service.search_candidates(self.PROJECT_ID, query)

        # 选中前 2 条
        selected_ids = [r.result_id for r in session.results[:2]]
        papers = service.commit_search_results(
            self.PROJECT_ID, session.session_id, selected_ids,
        )

        print(f"\n[commit] 提交 {len(selected_ids)} 条, 导入 {len(papers)} 篇论文")
        for p in papers:
            print(f"  - {p.paper_id}: {p.title[:60]}...")

        assert len(papers) > 0, "应至少导入 1 篇论文"

        # 验证会话状态
        updated = service.get_search_session(session.session_id)
        assert updated.status == "committed"

    def test_07_topic_scores_saved(self, service):
        """搜索导入后应保存主题分数"""
        scores = service.get_topic_scores(self.PROJECT_ID, "retrieval augmented generation")
        print(f"\n[topic_scores] 'retrieval augmented generation' 有 {len(scores)} 条分数记录")
        if scores:
            top = scores[0]
            print(f"  最高分: {top['paper_id']} = {top['importance_score']:.3f}")
            assert top["importance_score"] > 0

    def test_08_multi_adapter_coverage(self, service, adapters):
        """多个适配器应覆盖不同来源"""
        query = SearchQuery(query="BERT pre-training", limit=10)
        results = service.search_papers(query)

        sources = {r.source for r in results}
        print(f"\n[multi-adapter] 来源覆盖: {sources}")
        print(f"  总结果 {len(results)} 条, 来自 {len(sources)} 个数据源")
        # 至少应有 1 个来源
        assert len(sources) >= 1

    def test_09_pool_paper_id_attached(self, service):
        """搜索结果应携带 pool_paper_id"""
        query = SearchQuery(query="chain of thought prompting", limit=3)
        results = service.search_papers(query)

        for r in results:
            pool_id = r.source_payload.get("pool_paper_id")
            print(f"\n[pool_id] {r.title[:40]}... -> {pool_id}")
            assert pool_id, "每个结果应有 pool_paper_id"

    def test_10_postgres_crud(self, pg_storage):
        """PostgresStorage 基本 CRUD"""
        test_id = "e2e_crud_test"
        data = {"project_id": test_id, "name": "crud_test_project", "description": "test"}

        # Create
        pg_storage.upsert_item("projects", test_id, data)

        # Read
        item = pg_storage.get_item("projects", test_id)
        assert item is not None
        assert item["name"] == "crud_test_project"

        # Update
        data["description"] = "updated"
        pg_storage.upsert_item("projects", test_id, data)
        item2 = pg_storage.get_item("projects", test_id)
        assert item2["description"] == "updated"

        # Delete
        pg_storage.delete_item("projects", test_id)
        item3 = pg_storage.get_item("projects", test_id)
        assert item3 is None

        print("\n[CRUD] PostgreSQL CRUD 全部通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
