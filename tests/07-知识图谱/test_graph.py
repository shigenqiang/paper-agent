"""模块07 知识图谱 — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 至少有证据记录
"""

import pytest

from src.agents_v3.research_workspace.graph_service import GraphService


class TestGraphServiceE2E:
    """GraphService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = GraphService(storage=pg_storage)

    def test_build_graph_for_project(self, pg_storage):
        """为项目构建知识图谱"""
        evidence = pg_storage.list_all("evidence_records")
        if not evidence:
            pytest.skip("数据库中无证据记录")

        project_ids = {e["project_id"] for e in evidence}
        pid = list(project_ids)[0]

        graph = self.service.build_for_project(pid)
        assert graph is not None
        print(f"\n[graph] 项目 {pid}: {len(graph.nodes)} 节点, {len(graph.edges)} 边")

    def test_graph_nodes_have_stable_ids(self, pg_storage):
        """图谱节点应有稳定 ID"""
        evidence = pg_storage.list_all("evidence_records")
        if not evidence:
            pytest.skip("数据库中无证据记录")

        project_ids = {e["project_id"] for e in evidence}
        pid = list(project_ids)[0]

        graph = self.service.build_for_project(pid)
        for node in graph.nodes:
            assert node.node_id
            assert node.label

    def test_graph_edges_have_types(self, pg_storage):
        """图谱边应有类型"""
        evidence = pg_storage.list_all("evidence_records")
        if not evidence:
            pytest.skip("数据库中无证据记录")

        project_ids = {e["project_id"] for e in evidence}
        pid = list(project_ids)[0]

        graph = self.service.build_for_project(pid)
        for edge in graph.edges:
            assert edge.edge_type
