"""Gap 检测测试 — 边界用例

验证：
- find_gaps 返回结构正确
- find_research_gaps_enhanced 返回 sparse matrix + sparse regions
- Gap 节点 confidence 在合理范围
- 无 Gap 时返回空列表而非报错
- _aggregate_gaps 跨论文聚合逻辑
"""

import pytest
from src.agents_v3.research_workspace.services.graph_service import (
    GraphService, stable_hash,
)
from src.agents_v3.research_workspace.models.enums import NodeType
from src.agents_v3.research_workspace.models.knowledge_graph import GraphNode


class TestGapDetection:

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = GraphService(storage=pg_storage)

    def _get_test_project_id(self, pg_storage):
        papers = pg_storage.list_all("papers")
        if papers:
            return papers[0].get("project_id", "")
        pytest.skip("数据库中无数据")

    def test_find_gaps_returns_list(self, pg_storage):
        """find_gaps 返回列表"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        gaps = self.service.find_gaps(pid, min_confidence=0.0)
        assert isinstance(gaps, list)

    def test_find_gaps_confidence_range(self, pg_storage):
        """Gap confidence 在 [0, 1] 范围"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        gaps = self.service.find_gaps(pid, min_confidence=0.0)
        for g in gaps:
            conf = g.get("confidence", 0)
            assert 0 <= conf <= 1, f"Gap confidence={conf} out of range"

    def test_find_research_gaps_enhanced_structure(self, pg_storage):
        """find_research_gaps_enhanced 返回完整结构"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.find_research_gaps_enhanced(pid)
        assert "gaps" in result
        assert "method_dataset_matrix" in result
        assert "sparse_regions" in result

    def test_enhanced_gaps_has_sparse_pairs(self, pg_storage):
        """sparse_pairs 包含 method + dataset 字段"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.find_research_gaps_enhanced(pid)
        pairs = result["method_dataset_matrix"].get("sparse_pairs", [])
        for p in pairs[:3]:
            assert "method" in p
            assert "dataset" in p

    def test_enhanced_sparse_regions_have_degree(self, pg_storage):
        """sparse_regions 节点有 degree 字段"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.find_research_gaps_enhanced(pid)
        nodes = result["sparse_regions"].get("nodes", [])
        for n in nodes[:3]:
            assert "degree" in n
            assert "node_type" in n
            assert "label" in n

    def test_aggregate_gaps_cross_paper(self, pg_storage):
        """_aggregate_gaps: ≥2 篇论文共指的 limitation 创建聚合 Gap"""
        from src.agents_v3.research_workspace.models.knowledge_graph import GraphEdge
        from src.agents_v3.research_workspace.models.enums import EdgeType

        nodes = {}
        edges = {}
        # 创建 2 个相同 normalized_label 的 limitation 节点（不同论文）
        norm = "sample size limitation"
        for i, pid in enumerate(["paper_a", "paper_b"]):
            nid = f"limitation:test{i}"
            nodes[nid] = GraphNode(
                node_id=nid,
                node_type=NodeType.LIMITATION,
                label="small sample size",
                properties={
                    "normalized_label": norm,
                    "claim": "The study has a small sample size",
                    "paper_ids": [pid],
                    "evidence_ids": [f"ev_{pid}"],
                },
            )

        self.service._aggregate_gaps(nodes, edges, [])

        agg_gaps = [n for n in nodes.values()
                    if n.node_type == NodeType.GAP and n.properties.get("aggregated")]
        assert len(agg_gaps) == 1, f"Expected 1 aggregated gap, got {len(agg_gaps)}"
        gap = agg_gaps[0]
        assert "paper_a" in gap.properties["supporting_paper_ids"]
        assert "paper_b" in gap.properties["supporting_paper_ids"]

    def test_aggregate_gaps_same_paper_ignored(self, pg_storage):
        """同一论文内的重复 limitation 不聚合"""
        from src.agents_v3.research_workspace.models.knowledge_graph import GraphNode

        nodes = {}
        edges = {}
        norm = "same paper limitation"
        for i in range(3):
            nid = f"limitation:same{i}"
            nodes[nid] = GraphNode(
                node_id=nid,
                node_type=NodeType.LIMITATION,
                label="same paper limit",
                properties={
                    "normalized_label": norm,
                    "claim": "same paper limit",
                    "paper_ids": ["paper_x"],
                    "evidence_ids": [f"ev_{i}"],
                },
            )

        self.service._aggregate_gaps(nodes, edges, [])
        agg = [n for n in nodes.values()
               if n.node_type == NodeType.GAP and n.properties.get("aggregated")]
        assert len(agg) == 0, "Same-paper limitations should not be aggregated"
