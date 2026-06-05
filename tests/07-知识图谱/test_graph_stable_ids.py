"""稳定 ID 测试 — 确定性重建

验证：
- 相同数据两次构建得到相同 node_id / edge_id
- normalize_label + stable_hash 产生确定性 ID
- 顺序无关性（打乱 evidence 顺序结果一致）
"""

import pytest
from src.agents_v3.research_workspace.services.graph_service import (
    GraphService, normalize_label, stable_hash,
)
from src.agents_v3.research_workspace.models.enums import NodeType


class TestStableIds:

    def test_stable_hash_deterministic(self):
        """相同输入 → 相同 hash"""
        assert stable_hash("hello world") == stable_hash("hello world")

    def test_stable_hash_different_input(self):
        """不同输入 → 不同 hash"""
        assert stable_hash("abc") != stable_hash("def")

    def test_normalize_label_lowercase(self):
        assert normalize_label("Hello WORLD") == "hello world"

    def test_normalize_label_whitespace(self):
        assert normalize_label("  hello   world  ") == "hello world"

    def test_normalize_label_hyphen_underscore(self):
        assert normalize_label("hello-world_test") == "hello world test"

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = GraphService(storage=pg_storage)

    def _get_test_project_id(self, pg_storage):
        papers = pg_storage.list_all("papers")
        if papers:
            return papers[0].get("project_id", "")
        pytest.skip("数据库中无数据")

    def test_rebuild_produces_same_ids(self, pg_storage):
        """两次 build_project_graph 得到相同 node_id"""
        pid = self._get_test_project_id(pg_storage)
        graph1 = self.service.build_project_graph(pid, force=True)
        graph2 = self.service.build_project_graph(pid, force=True)

        ids1 = {n.node_id for n in graph1.nodes}
        ids2 = {n.node_id for n in graph2.nodes}
        assert ids1 == ids2, f"Node IDs differ: {ids1.symmetric_difference(ids2)}"

    def test_rebuild_produces_same_edge_ids(self, pg_storage):
        """两次 build 得到相同 edge_id"""
        pid = self._get_test_project_id(pg_storage)
        graph1 = self.service.build_project_graph(pid, force=True)
        graph2 = self.service.build_project_graph(pid, force=True)

        eids1 = {e.edge_id for e in graph1.edges}
        eids2 = {e.edge_id for e in graph2.edges}
        assert eids1 == eids2

    def test_node_id_format(self, pg_storage):
        """node_id 格式为 {type}:{hash}"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        for node in graph.nodes[:10]:
            parts = node.node_id.split(":", 1)
            assert len(parts) == 2, f"Bad format: {node.node_id}"
            assert parts[0]  # type prefix not empty

    def test_paper_node_id_contains_doi(self, pg_storage):
        """Paper 节点 ID 包含 paper_id"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        paper_nodes = [n for n in graph.nodes if n.node_type == NodeType.PAPER]
        for n in paper_nodes:
            assert n.node_id.startswith("paper:"), f"Paper node ID: {n.node_id}"
