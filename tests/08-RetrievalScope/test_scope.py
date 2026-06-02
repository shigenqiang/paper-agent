"""模块08 RetrievalScope — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 项目中有论文数据
"""

import pytest

from src.agents_v3.research_workspace.services.scope import RetrievalScopeService
from src.agents_v3.research_workspace.models import ScopeType


class TestRetrievalScopeE2E:
    """RetrievalScopeService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = RetrievalScopeService(storage=pg_storage)

    def _find_project_with_papers(self, pg_storage):
        """找到一个有论文的项目"""
        papers = pg_storage.list_all("papers")
        if not papers:
            return None
        return papers[0].get("project_id")

    def test_resolve_all_project_scope(self, pg_storage):
        """全项目范围应包含所有论文"""
        pid = self._find_project_with_papers(pg_storage)
        if not pid:
            pytest.skip("数据库中无论文")

        scope = self.service.resolve(pid, ScopeType.ALL_PROJECT)
        assert scope is not None
        assert len(scope.paper_ids) > 0
        print(f"\n[scope] 全项目: {len(scope.paper_ids)} 篇论文")

    def test_resolve_topic_group_scope(self, pg_storage):
        """主题分组范围应过滤论文"""
        pid = self._find_project_with_papers(pg_storage)
        if not pid:
            pytest.skip("数据库中无论文")

        # 获取可用主题
        papers = pg_storage.query("papers", {"project_id": pid})
        topics = set()
        for p in papers:
            if p.get("topics"):
                topics.update(p["topics"])

        if not topics:
            pytest.skip("论文无主题标签")

        topic = list(topics)[0]
        scope = self.service.resolve(pid, ScopeType.TOPIC_GROUP, topic_ids=[topic])
        assert scope is not None
        print(f"\n[scope] 主题 '{topic}': {len(scope.paper_ids)} 篇论文")

    def test_resolve_year_range_scope(self, pg_storage):
        """年份范围应过滤论文"""
        pid = self._find_project_with_papers(pg_storage)
        if not pid:
            pytest.skip("数据库中无论文")

        scope = self.service.resolve(pid, ScopeType.YEAR_RANGE, time_range=["2023", "2025"])
        assert scope is not None
        print(f"\n[scope] 年份 2023-2025: {len(scope.paper_ids)} 篇论文")
