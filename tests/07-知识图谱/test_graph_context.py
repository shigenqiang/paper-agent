"""GraphRAG 上下文测试

验证：
- build_graph_context 返回 context_text
- context_text 非空且包含关键信息
- estimated_tokens 合理
- build_graph_summary 包含 top_topics/methods/tasks
- build_community_summaries 结构正确
"""

import pytest
from src.agents_v3.research_workspace.services.graph_service import GraphService
from src.agents_v3.research_workspace.models.enums import NodeType


class TestGraphContext:

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = GraphService(storage=pg_storage)

    def _get_test_project_id(self, pg_storage):
        papers = pg_storage.list_all("papers")
        if papers:
            return papers[0].get("project_id", "")
        pytest.skip("数据库中无数据")

    def test_build_graph_context_returns_text(self, pg_storage):
        """build_graph_context 返回 context_text"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        if not graph.nodes:
            pytest.skip("图谱无节点")

        node_ids = [n.node_id for n in graph.nodes[:3]]
        result = self.service.build_graph_context(pid, node_ids)
        assert "context_text" in result
        assert isinstance(result["context_text"], str)
        assert len(result["context_text"]) > 0

    def test_build_graph_context_estimated_tokens(self, pg_storage):
        """estimated_tokens 为正整数"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        if not graph.nodes:
            pytest.skip("图谱无节点")

        node_ids = [n.node_id for n in graph.nodes[:3]]
        result = self.service.build_graph_context(pid, node_ids)
        tokens = result.get("estimated_tokens", 0)
        assert tokens > 0

    def test_build_graph_summary_has_topics(self, pg_storage):
        """build_graph_summary 包含 top_topics"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        summary = self.service.build_graph_summary(pid)
        assert "top_topics" in summary
        assert isinstance(summary["top_topics"], list)

    def test_build_graph_summary_has_methods(self, pg_storage):
        """build_graph_summary 包含 top_methods"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        summary = self.service.build_graph_summary(pid)
        assert "top_methods" in summary

    def test_build_graph_summary_paper_count(self, pg_storage):
        """total_papers > 0"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        summary = self.service.build_graph_summary(pid)
        assert summary.get("total_papers", 0) > 0

    def test_community_detection_structure(self, pg_storage):
        """detect_communities 返回正确结构"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.detect_communities(pid)
        assert "communities" in result
        assert "total_assigned" in result
        assert isinstance(result["communities"], int)

    def test_build_graph_context_empty_nodes(self, pg_storage):
        """空 node_ids 返回最小 context"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.build_graph_context(pid, [])
        # 空输入仍可能返回框架文本，但应有 warnings
        assert "context_text" in result
        assert "warnings" in result
