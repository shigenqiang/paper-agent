"""Scope 解析测试 — 图谱范围

验证：
- to_graph_context 返回非 Paper 节点
- graph_subgraph scope 走 get_subgraph
- selected_papers scope 返回 Paper + 1-hop
- project_id 字段注入
- 空 scope 返回空结果
"""

import pytest
from src.agents_v3.research_workspace.services.graph_service import GraphService
from src.agents_v3.research_workspace.services.scope import RetrievalScopeService
from src.agents_v3.research_workspace.models.reports import RetrievalScope
from src.agents_v3.research_workspace.models.enums import NodeType


class TestGraphScope:

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.gs = GraphService(storage=pg_storage)
        self.scope_svc = RetrievalScopeService(storage=pg_storage)

    def _get_test_project_id(self, pg_storage):
        papers = pg_storage.list_all("papers")
        if papers:
            return papers[0].get("project_id", "")
        pytest.skip("数据库中无数据")

    def test_to_graph_context_returns_non_paper_nodes(self, pg_storage):
        """selected_papers scope 返回 Paper + 1-hop 非 Paper 节点"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.gs.build_project_graph(pid, force=True)

        # 找有邻居的 Paper 节点
        adj = {}
        for e in graph.edges:
            adj.setdefault(e.source_id, []).append(e.target_id)
            adj.setdefault(e.target_id, []).append(e.source_id)
        connected_papers = [
            n.node_id.replace("paper:", "") for n in graph.nodes
            if n.node_type == NodeType.PAPER and adj.get(n.node_id)
        ]
        if not connected_papers:
            pytest.skip("无连接的 Paper 节点")

        scope = RetrievalScope(
            scope_type="selected_papers",
            project_id=pid,
            paper_ids=connected_papers[:2],
        )
        ctx = self.scope_svc.to_graph_context(scope)
        nodes = ctx.get("nodes", [])
        non_paper = [n for n in nodes if not n.get("node_id", "").startswith("paper:")]
        assert len(non_paper) > 0, "Should return non-Paper nodes"

    def test_to_graph_context_has_project_id(self, pg_storage):
        """to_graph_context 返回值包含 project_id"""
        pid = self._get_test_project_id(pg_storage)
        self.gs.build_project_graph(pid, force=True)

        papers = pg_storage.query("papers", {"project_id": pid})
        scope = RetrievalScope(
            scope_type="selected_papers",
            project_id=pid,
            paper_ids=[papers[0]["paper_id"]],
        )
        ctx = self.scope_svc.to_graph_context(scope)
        assert ctx.get("project_id") == pid

    def test_to_graph_context_edges_within_selected(self, pg_storage):
        """返回的边的两端都在 selected 节点内"""
        pid = self._get_test_project_id(pg_storage)
        self.gs.build_project_graph(pid, force=True)

        papers = pg_storage.query("papers", {"project_id": pid})
        scope = RetrievalScope(
            scope_type="selected_papers",
            project_id=pid,
            paper_ids=[p["paper_id"] for p in papers[:3]],
        )
        ctx = self.scope_svc.to_graph_context(scope)
        node_ids = {n.get("node_id") for n in ctx.get("nodes", [])}
        for e in ctx.get("edges", []):
            assert e.get("source_id") in node_ids, f"Edge source {e.get('source_id')} not in nodes"
            assert e.get("target_id") in node_ids, f"Edge target {e.get('target_id')} not in nodes"

    def test_to_graph_context_empty_paper_ids(self, pg_storage):
        """空 paper_ids 返回空结果"""
        pid = self._get_test_project_id(pg_storage)
        scope = RetrievalScope(
            scope_type="selected_papers",
            project_id=pid,
            paper_ids=[],
        )
        ctx = self.scope_svc.to_graph_context(scope)
        assert len(ctx.get("nodes", [])) == 0

    def test_to_graph_context_graph_subgraph(self, pg_storage):
        """graph_subgraph scope 走 get_subgraph 路径"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.gs.build_project_graph(pid, force=True)
        if not graph.nodes:
            pytest.skip("图谱无节点")

        node_ids = [graph.nodes[0].node_id]
        scope = RetrievalScope(
            scope_type="graph_subgraph",
            project_id=pid,
            graph_node_ids=node_ids,
        )
        ctx = self.scope_svc.to_graph_context(scope)
        assert "nodes" in ctx
        assert "edges" in ctx
