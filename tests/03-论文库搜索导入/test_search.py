"""模块03 论文库搜索导入 — 真实 API + PostgreSQL

当前代码功能（search_candidates 一步到位）：
  search_papers()  → 多源搜索 + HybridRanker 排序 + 写 papers_pool
  search_candidates() → search_papers + 直接入库（papers/queries/paper_queries/topic_scores/Qdrant）

前置条件:
    - Docker 容器 postgres (5432) + qdrant (6333) 运行中
    - 网络可达 openalex / arxiv / semantic scholar API
"""

import pytest

from src.agents_v3.research_workspace.search.base import SearchQuery


class TestSearchPipeline:
    """主搜索流水线 — search_papers()

    验证：多源并行搜索 → 去重合并 → HybridRanker 排序 → papers_pool 写入
    """

    PROJECT_ID = "e2e_test_project"

    @pytest.fixture(autouse=True)
    def setup_project(self, pg_storage):
        """确保测试项目存在，测试后清理"""
        pg_storage.upsert_item("projects", self.PROJECT_ID, {
            "project_id": self.PROJECT_ID,
            "name": "E2E 测试项目",
            "description": "搜索联调自动创建",
        })
        yield
        try:
            papers = pg_storage.query("papers", {"project_id": self.PROJECT_ID})
            for p in papers:
                pg_storage.delete_item("papers", p["paper_id"])
            pg_storage.delete_item("projects", self.PROJECT_ID)
        except Exception:
            pass

    def test_01_search_returns_results(self, service):
        """search_papers 能从真实 API 拿到结果"""
        query = SearchQuery(query="large language model", limit=5)
        results = service.search_papers(query)

        print(f"\n[search_papers] 搜索 'large language model' 返回 {len(results)} 条结果")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. [{r.source}] {r.title[:60]}... (citations={r.citations})")

        assert len(results) > 0, "搜索应返回至少 1 条结果"
        r = results[0]
        assert r.title, "结果应有标题"
        assert r.source, "结果应有来源"

    def test_02_results_stored_in_pool(self, pg_storage, service):
        """搜索结果应存入 papers_pool（全局论文池）"""
        query = SearchQuery(query="transformer attention mechanism", limit=3)
        service.search_papers(query)

        pool_items = pg_storage.list_all("papers_pool")
        print(f"\n[papers_pool] 共 {len(pool_items)} 条记录")
        assert len(pool_items) > 0, "papers_pool 应非空"

    def test_03_pool_paper_id_attached(self, service):
        """搜索结果应携带 pool_paper_id（用于后续入库关联）"""
        query = SearchQuery(query="chain of thought prompting", limit=3)
        results = service.search_papers(query)

        for r in results:
            pool_id = r.source_payload.get("pool_paper_id")
            print(f"\n[pool_id] {r.title[:40]}... -> {pool_id}")
            assert pool_id, "每个结果应有 pool_paper_id"

    def test_04_multi_adapter_coverage(self, service, adapters):
        """多个适配器应覆盖不同来源"""
        query = SearchQuery(query="BERT pre-training", limit=10)
        results = service.search_papers(query)

        sources = {r.source for r in results}
        print(f"\n[multi-adapter] 来源覆盖: {sources}")
        print(f"  总结果 {len(results)} 条, 来自 {len(sources)} 个数据源")
        assert len(sources) >= 1

    def test_05_hybrid_ranker_scores(self, service):
        """HybridRanker 应为每篇结果分配 dense_score 和 quality_score"""
        query = SearchQuery(query="retrieval augmented generation", limit=5)
        results = service.search_papers(query)

        print(f"\n[HybridRanker] {len(results)} 条结果:")
        for r in results[:3]:
            print(f"  dense={r.dense_score:.3f}  quality={r.quality_score:.3f}  final={r.final_score:.4f}  {r.title[:50]}")

        assert len(results) > 0
        for r in results:
            assert r.dense_score is not None, "应有 dense_score（余弦相似度）"
            assert r.quality_score is not None, "应有 quality_score（引用+时效）"


class TestSearchDirectImport:
    """搜索直接入库 — search_candidates()

    验证：search_papers + 直接写入 papers/queries/paper_queries/topic_scores/Qdrant
    当前设计：搜索即入库，无两步提交
    """

    PROJECT_ID = "e2e_import_project"

    @pytest.fixture(autouse=True)
    def setup_project(self, pg_storage):
        """确保测试项目存在，测试后清理"""
        pg_storage.upsert_item("projects", self.PROJECT_ID, {
            "project_id": self.PROJECT_ID,
            "name": "导入测试项目",
            "description": "搜索导入自动创建",
        })
        yield
        try:
            for t in ["paper_queries", "topic_scores"]:
                items = pg_storage.list_all(t)
                for item in items:
                    pk = item.get("paper_id") or item.get(list(item.keys())[0])
                    try:
                        pg_storage.delete_item(t, pk)
                    except Exception:
                        pass
            papers = pg_storage.query("papers", {"project_id": self.PROJECT_ID})
            for p in papers:
                pg_storage.delete_item("papers", p["paper_id"])
            queries = pg_storage.list_all("queries")
            for q in queries:
                pg_storage.delete_item("queries", q["query_id"])
            pg_storage.delete_item("projects", self.PROJECT_ID)
        except Exception:
            pass

    def test_01_search_writes_papers_table(self, service, pg_storage):
        """search_candidates 应将论文写入 PostgreSQL papers 表"""
        query = SearchQuery(query="large language model", limit=3)
        response = service.search_candidates(self.PROJECT_ID, query, min_score=0.3)

        stored = pg_storage.query("papers", {"project_id": self.PROJECT_ID})
        print(f"\n[papers] 入库 {len(stored)} 篇论文")
        for p in stored[:3]:
            print(f"  - {p['paper_id']}: dense_score={p.get('dense_score', 'N/A')}")

        assert len(stored) > 0, "搜索后应有论文写入 papers 表"
        assert len(stored) <= len(response.results), "入库数不应超过搜索结果数"

    def test_02_search_writes_queries_table(self, service, pg_storage):
        """search_candidates 应写入 queries 表（查询记录）"""
        query = SearchQuery(query="transformer attention", limit=3)
        service.search_candidates(self.PROJECT_ID, query, min_score=0.3)

        queries = pg_storage.list_all("queries")
        matching = [q for q in queries if q.get("query_text") == "transformer attention"]
        print(f"\n[queries] 匹配查询: {len(matching)} 条")
        assert len(matching) >= 1, "应写入 queries 表记录"
        assert matching[0]["query_id"], "应有 query_id"

    def test_03_search_writes_paper_queries(self, service, pg_storage):
        """search_candidates 应写入 paper_queries 关联表"""
        query = SearchQuery(query="knowledge graph embedding", limit=3)
        service.search_candidates(self.PROJECT_ID, query, min_score=0.3)

        links = pg_storage.list_all("paper_queries")
        print(f"\n[paper_queries] 关联记录: {len(links)} 条")
        for link in links[:3]:
            print(f"  - paper={link['paper_id']} query={link['query_id']} score={link.get('score', 'N/A')}")

        assert len(links) > 0, "应写入 paper_queries 关联记录"

    def test_04_search_saves_topic_scores(self, service, pg_storage):
        """search_candidates 应保存 topic_scores（主题相关性分）"""
        query = SearchQuery(query="retrieval augmented generation", limit=3)
        service.search_candidates(self.PROJECT_ID, query, min_score=0.3)

        scores = pg_storage.list_all("topic_scores")
        project_papers = {p["paper_id"] for p in pg_storage.query("papers", {"project_id": self.PROJECT_ID})}
        matching = [s for s in scores if s.get("paper_id") in project_papers]
        print(f"\n[topic_scores] 主题分数记录: {len(matching)} 条")
        for s in matching[:3]:
            print(f"  - {s['paper_id']}: dense={s.get('dense_score', 'N/A')}, quality={s.get('quality_score', 'N/A')}")

        assert len(matching) > 0, "应保存 topic_scores 记录"

    def test_05_min_score_threshold(self, service, pg_storage):
        """min_score 应过滤掉 dense_score 低于阈值的论文"""
        query = SearchQuery(query="BERT pre-training", limit=10)

        # 高阈值：只保留高相关性论文
        response_high = service.search_candidates(self.PROJECT_ID, query, min_score=0.8)
        stored_high = pg_storage.query("papers", {"project_id": self.PROJECT_ID})

        # 清理后用低阈值
        for p in stored_high:
            pg_storage.delete_item("papers", p["paper_id"])

        response_low = service.search_candidates(self.PROJECT_ID, query, min_score=0.1)
        stored_low = pg_storage.query("papers", {"project_id": self.PROJECT_ID})

        print(f"\n[min_score] 高阈值(0.8): {len(stored_high)} 篇, 低阈值(0.1): {len(stored_low)} 篇")
        assert len(stored_low) >= len(stored_high), "低阈值应入库更多论文"

    def test_06_dedup_on_reimport(self, service, pg_storage):
        """重复搜索同一查询不应创建重复论文"""
        query = SearchQuery(query="retrieval augmented generation", limit=3)

        service.search_candidates(self.PROJECT_ID, query, min_score=0.3)
        papers_after_first = pg_storage.query("papers", {"project_id": self.PROJECT_ID})
        count_first = len(papers_after_first)

        service.search_candidates(self.PROJECT_ID, query, min_score=0.3)
        papers_after_second = pg_storage.query("papers", {"project_id": self.PROJECT_ID})
        count_second = len(papers_after_second)

        print(f"\n[dedup] 第一次: {count_first} 篇, 第二次: {count_second} 篇")
        assert count_second == count_first, "重复搜索不应创建重复论文"

    def test_07_search_response_structure(self, service):
        """search_candidates 应返回正确的 SearchResponse 结构"""
        query = SearchQuery(query="chain of thought prompting", limit=5)
        response = service.search_candidates(self.PROJECT_ID, query, min_score=0.3)

        assert response.query is not None, "应有 query"
        assert response.total_count >= 0, "应有 total_count"
        assert isinstance(response.results, list), "results 应为列表"

        if response.results:
            r = response.results[0]
            assert r.title, "结果应有标题"
            assert r.source, "结果应有来源"
            assert r.dense_score is not None, "应有 dense_score"
            print(f"\n[response] {len(response.results)} 条结果, total={response.total_count}")

    def test_08_search_papers_pool_populated(self, service, pg_storage):
        """search_candidates 内部应先写 papers_pool（全局论文池）"""
        query = SearchQuery(query="prompt engineering", limit=3)
        service.search_candidates(self.PROJECT_ID, query, min_score=0.3)

        pool = pg_storage.list_all("papers_pool")
        print(f"\n[papers_pool] 全局论文池: {len(pool)} 条")
        assert len(pool) > 0, "search_candidates 应先写入 papers_pool"


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
