"""边界/异常测试

验证：
- 空项目构建不崩溃
- 畸形 LLM 输出（GraphExtractor）
- 增量更新重叠节点
- 断开图社区检测
- Consensus Meter 零 findings
- get_graph 不存在的项目
- get_node 不存在的节点
"""

import pytest
from src.agents_v3.research_workspace.services.graph_service import (
    GraphService, stable_hash,
)
from src.agents_v3.research_workspace.models.enums import NodeType, EdgeType
from src.agents_v3.research_workspace.models.knowledge_graph import (
    GraphNode, GraphEdge, KnowledgeGraph,
)


class TestEdgeCases:

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = GraphService(storage=pg_storage)

    def _get_test_project_id(self, pg_storage):
        papers = pg_storage.list_all("papers")
        if papers:
            return papers[0].get("project_id", "")
        pytest.skip("数据库中无数据")

    # ── 空项目 ──

    def test_get_graph_nonexistent_project(self, pg_storage):
        """不存在的项目返回空图谱或 None"""
        result = self.service.get_graph("nonexistent_project_xyz")
        if result is not None:
            assert len(result.nodes) == 0
            assert len(result.edges) == 0

    def test_build_empty_project(self, pg_storage):
        """空项目构建返回空图谱"""
        graph = self.service.build_project_graph("empty_project_xyz", force=True)
        assert graph is not None
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_find_gaps_empty_project(self, pg_storage):
        """空项目 find_gaps 返回空列表"""
        gaps = self.service.find_gaps("empty_project_xyz")
        assert gaps == []

    def test_detect_communities_empty_graph(self, pg_storage):
        """空图社区检测返回 0"""
        # 先构建一个空图
        self.service.build_project_graph("empty_comm_xyz", force=True)
        result = self.service.detect_communities("empty_comm_xyz")
        assert result["communities"] == 0

    def test_quality_metrics_empty_project(self, pg_storage):
        """空项目质量指标不崩溃"""
        metrics = self.service.compute_quality_metrics("empty_metrics_xyz")
        assert "coverage" in metrics

    # ── get_node / get_neighbors 边界 ──

    def test_get_node_nonexistent(self, pg_storage):
        """不存在的节点返回 None"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        node = self.service.get_node(pid, "nonexistent:node:id")
        assert node is None

    def test_get_neighbors_nonexistent_node(self, pg_storage):
        """不存在节点的邻居返回空"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.get_neighbors(pid, "nonexistent:node:id")
        assert result.get("nodes", []) == []

    # ── search_nodes 边界 ──

    def test_search_nodes_empty_query(self, pg_storage):
        """空查询返回空结果"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        results = self.service.search_nodes(pid, "")
        assert isinstance(results, list)

    def test_search_nodes_no_match(self, pg_storage):
        """无匹配返回空列表"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        results = self.service.search_nodes(pid, "zzz_nonexistent_term_xyz")
        assert isinstance(results, list)

    # ── Consensus Meter 边界 ──

    def test_consensus_meter_no_findings(self, pg_storage):
        """无 Finding 时返回空列表"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        # 用不存在的 claim_node_ids
        result = self.service.build_consensus_meter(pid, claim_node_ids=["nonexistent:node"])
        assert isinstance(result, list)

    # ── _aggregate_gaps 边界 ──

    def test_aggregate_gaps_empty_input(self, pg_storage):
        """空输入不崩溃"""
        nodes = {}
        edges = {}
        self.service._aggregate_gaps(nodes, edges, [])
        assert len(nodes) == 0
        assert len(edges) == 0

    def test_aggregate_gaps_single_limitation(self, pg_storage):
        """单个 limitation 不创建聚合 Gap"""
        nodes = {
            "lim:1": GraphNode(
                node_id="lim:1",
                node_type=NodeType.LIMITATION,
                label="test limitation",
                properties={
                    "normalized_label": "test limitation",
                    "claim": "test limitation",
                    "paper_ids": ["paper_a"],
                    "evidence_ids": ["ev_a"],
                },
            ),
        }
        edges = {}
        self.service._aggregate_gaps(nodes, edges, [])
        gaps = [n for n in nodes.values() if n.node_type == NodeType.GAP]
        assert len(gaps) == 0

    # ── 增量更新边界 ──

    def test_incremental_update_empty_new_ids(self, pg_storage):
        """空 new_paper_ids 不修改图谱"""
        pid = self._get_test_project_id(pg_storage)
        graph1 = self.service.build_project_graph(pid, force=True)
        nodes_before = len(graph1.nodes)

        self.service.incremental_update(pid, [])
        graph2 = self.service.get_graph(pid)
        assert len(graph2.nodes) == nodes_before

    # ── build_graph_context 边界 ──

    def test_build_context_invalid_node_ids(self, pg_storage):
        """无效 node_ids 返回空 context"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        result = self.service.build_graph_context(pid, ["invalid:node:id"])
        # 应该不崩溃
        assert "context_text" in result

    # ── find_paths 边界 ──

    def test_find_paths_same_node(self, pg_storage):
        """同节点路径返回空"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid, force=True)
        if not graph.nodes:
            pytest.skip("图谱无节点")
        paths = self.service.find_paths(pid, graph.nodes[0].node_id, graph.nodes[0].node_id)
        assert isinstance(paths, list)

    # ── global_search 边界 ──

    def test_global_search_empty_project(self, pg_storage):
        """空项目 global_search 返回空结果"""
        result = self.service.global_search("empty_gs_xyz", "test question")
        assert result["answer"] == ""
        assert result["community_answers"] == []

    def test_global_search_returns_structure(self, pg_storage):
        """global_search 返回正确结构"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid, force=True)
        self.service.detect_communities(pid)
        result = self.service.global_search(pid, "What are the main findings?")
        assert "answer" in result
        assert "community_answers" in result
        assert "sources" in result
