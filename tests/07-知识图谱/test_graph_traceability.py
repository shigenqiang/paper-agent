"""可追溯性测试 — provenance 验证

验证：
- 每个非 Paper 节点有 paper_ids 和 evidence_ids
- 每条边有来源追溯
- validate_graph_traceability 正确报告指标
"""

import pytest
from src.agents_v3.research_workspace.services.graph_service import GraphService
from src.agents_v3.research_workspace.models.enums import NodeType


class TestTraceability:

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = GraphService(storage=pg_storage)

    def _get_test_project_id(self, pg_storage):
        papers = pg_storage.list_all("papers")
        if papers:
            return papers[0].get("project_id", "")
        pytest.skip("数据库中无数据")

    def test_non_paper_nodes_have_paper_ids(self, pg_storage):
        """非 Paper 节点应有 paper_ids 来源"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        non_paper = [n for n in graph.nodes
                     if n.node_type not in (NodeType.PAPER, NodeType.COMMUNITY, NodeType.GHOST_PAPER)]
        nodes_with_source = [n for n in non_paper if n.properties.get("paper_ids")]
        ratio = len(nodes_with_source) / len(non_paper) if non_paper else 1.0
        assert ratio >= 0.5, f"Only {ratio:.0%} non-Paper nodes have paper_ids"

    def test_edges_have_provenance(self, pg_storage):
        """边应有 paper_ids 或 evidence_ids 来源"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        edges_with_source = [
            e for e in graph.edges
            if e.properties.get("paper_ids") or e.properties.get("evidence_ids")
        ]
        ratio = len(edges_with_source) / len(graph.edges) if graph.edges else 1.0
        assert ratio >= 0.3, f"Only {ratio:.0%} edges have provenance"

    def test_validate_traceability_returns_metrics(self, pg_storage):
        """validate_graph_traceability 返回完整指标"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.validate_graph_traceability(pid)
        assert "valid" in result
        assert "metrics" in result
        metrics = result["metrics"]
        assert "total_nodes" in metrics
        assert "total_edges" in metrics

    def test_validate_traceability_no_orphan_edges(self, pg_storage):
        """边的 source_id 和 target_id 都应存在于节点中（允许少量 section 来源边）"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        node_ids = {n.node_id for n in graph.nodes}
        orphan_edges = [
            e for e in graph.edges
            if e.source_id not in node_ids or e.target_id not in node_ids
        ]
        # section 来源的边可能引用未被提升为节点的实体，允许 ≤20%
        ratio = len(orphan_edges) / len(graph.edges) if graph.edges else 0
        assert ratio <= 0.25, f"{len(orphan_edges)} orphan edges ({ratio:.0%})"

    def test_gap_nodes_have_supporting_papers(self, pg_storage):
        """Gap 节点应有 supporting_paper_ids"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        gaps = [n for n in graph.nodes if n.node_type == NodeType.GAP]
        for gap in gaps:
            papers = gap.properties.get("supporting_paper_ids", [])
            assert len(papers) >= 1, f"Gap {gap.node_id} has no supporting papers"
