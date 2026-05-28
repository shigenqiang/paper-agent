"""GraphService 测试"""

import pytest

from src.agents_v3.research_workspace.graph_service import GraphService
from src.agents_v3.research_workspace.models import NodeType, EdgeType


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.graph_service.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return GraphService()


@pytest.fixture
def sample_evidence(service):
    storage = service.storage
    # 创建论文记录（build 需要 papers 来过滤 included）
    storage.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "title": "Paper 1", "included": True,
    })
    storage.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "title": "Paper 2", "included": True,
    })
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1",
        "project_id": "proj1",
        "paper_id": "p1",
        "topic": "feedback mechanism",
        "method": "experiment",
        "finding": "Improved learning outcomes significantly",
        "limitation": "Small sample size in the study",
        "source_chunk_id": "chunk_p1_0",
        "source_quote": "improved learning",
    })
    storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2",
        "project_id": "proj1",
        "paper_id": "p2",
        "topic": "feedback mechanism",
        "method": "survey",
        "finding": "Higher engagement observed in treatment group",
        "limitation": "Short duration of the intervention",
        "source_chunk_id": "chunk_p2_0",
        "source_quote": "higher engagement",
    })
    return storage


class TestGraphService:
    def test_build_empty_graph_returns_empty(self, service):
        graph = service.build_project_graph("empty")
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_build_graph_with_evidence_creates_nodes_and_edges(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_build_graph_creates_paper_nodes(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        paper_nodes = [n for n in graph.nodes if n.node_type == NodeType.PAPER]
        assert len(paper_nodes) == 2

    def test_build_graph_creates_topic_nodes(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        topic_nodes = [n for n in graph.nodes if n.node_type == NodeType.TOPIC]
        assert len(topic_nodes) >= 1

    def test_build_graph_creates_method_nodes(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        method_nodes = [n for n in graph.nodes if n.node_type == NodeType.METHOD]
        assert len(method_nodes) >= 1

    def test_stable_ids_are_deterministic(self, service, sample_evidence):
        """重复构图，节点 ID 不变"""
        graph1 = service.build_project_graph("proj1")
        graph2 = service.build_project_graph("proj1")
        ids1 = {n.node_id for n in graph1.nodes}
        ids2 = {n.node_id for n in graph2.nodes}
        assert ids1 == ids2

    def test_finding_ids_are_stable(self, service, sample_evidence):
        """Finding 不再使用随机 UUID"""
        graph = service.build_project_graph("proj1")
        finding_nodes = [n for n in graph.nodes if n.node_type == NodeType.FINDING]
        for n in finding_nodes:
            assert "finding:" in n.node_id
            # 不应包含随机 uuid 特征（长度 > 20）
            assert len(n.node_id) < 40

    def test_nodes_have_provenance(self, service, sample_evidence):
        """非 Paper 节点应有 evidence_ids 和 paper_ids"""
        graph = service.build_project_graph("proj1")
        for node in graph.nodes:
            if node.node_type == NodeType.PAPER:
                continue
            assert node.properties.get("paper_ids"), f"Node {node.node_id} missing paper_ids"

    def test_edges_have_provenance(self, service, sample_evidence):
        """非结构性边应有 evidence_ids"""
        graph = service.build_project_graph("proj1")
        for edge in graph.edges:
            if edge.edge_type in (EdgeType.BELONGS_TO_TOPIC, EdgeType.USES_METHOD,
                                  EdgeType.REPORTS_FINDING, EdgeType.HAS_LIMITATION):
                assert edge.properties.get("evidence_ids"), f"Edge {edge.edge_id} missing evidence_ids"

    def test_get_graph_returns_saved_graph(self, service, sample_evidence):
        service.build_project_graph("proj1")
        graph = service.get_graph("proj1")
        assert graph.project_id == "proj1"

    def test_get_node_returns_matching_node(self, service, sample_evidence):
        service.build_project_graph("proj1")
        node = service.get_node("proj1", "paper:p1")
        assert node is not None
        assert node.node_type == NodeType.PAPER

    def test_get_neighbors_returns_connected_nodes(self, service, sample_evidence):
        service.build_project_graph("proj1")
        result = service.get_neighbors("proj1", "paper:p1", hops=1)
        assert len(result["nodes"]) > 0

    def test_get_neighbors_with_type_filter(self, service, sample_evidence):
        service.build_project_graph("proj1")
        result = service.get_neighbors("proj1", "paper:p1", hops=1, node_types=["Topic"])
        # 起始节点(Paper)也会在 visited 中，但 filter 只影响扩展的邻居
        topic_nodes = [n for n in result["nodes"] if n["node_type"] == "Topic"]
        assert len(topic_nodes) >= 1

    def test_get_subgraph_returns_related_ids(self, service, sample_evidence):
        """get_subgraph 应返回 related_paper_ids"""
        service.build_project_graph("proj1")
        result = service.get_subgraph("proj1", ["paper:p1"], hops=1)
        assert "related_paper_ids" in result
        assert "related_evidence_ids" in result
        assert "p1" in result["related_paper_ids"]

    def test_find_paths_returns_explanation(self, service, sample_evidence):
        service.build_project_graph("proj1")
        paths = service.find_paths("proj1", "paper:p1", "paper:p2", max_hops=3)
        assert len(paths) > 0
        assert "explanation" in paths[0]
        assert "node_ids" in paths[0]
        assert "edge_ids" in paths[0]

    def test_validate_traceability(self, service, sample_evidence):
        service.build_project_graph("proj1")
        result = service.validate_graph_traceability("proj1")
        assert "valid" in result
        assert "metrics" in result
        assert result["metrics"]["traceability_coverage"] > 0

    def test_get_stats_enhanced(self, service, sample_evidence):
        service.build_project_graph("proj1")
        stats = service.get_stats("proj1")
        assert "total_nodes" in stats
        assert "avg_degree" in stats
        assert "paper_count" in stats

    def test_excluded_paper_not_in_graph(self, service):
        storage = service.storage
        storage.upsert_item("papers", "p1", {"paper_id": "p1", "project_id": "proj1", "included": True})
        storage.upsert_item("papers", "p2", {"paper_id": "p2", "project_id": "proj1", "included": False})
        storage.upsert_item("evidence_records", "e1", {
            "evidence_id": "e1", "project_id": "proj1", "paper_id": "p1",
            "topic": "T", "finding": "F",
        })
        storage.upsert_item("evidence_records", "e2", {
            "evidence_id": "e2", "project_id": "proj1", "paper_id": "p2",
            "topic": "T", "finding": "G",
        })
        graph = service.build_project_graph("proj1")
        paper_ids = [n.node_id for n in graph.nodes if n.node_type == NodeType.PAPER]
        assert "paper:p1" in paper_ids
        assert "paper:p2" not in paper_ids
