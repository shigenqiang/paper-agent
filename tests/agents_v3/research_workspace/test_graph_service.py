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
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1",
        "project_id": "proj1",
        "paper_id": "p1",
        "topic": "feedback mechanism",
        "method": "experiment",
        "finding": "Improved learning",
        "limitation": "Small sample",
    })
    storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2",
        "project_id": "proj1",
        "paper_id": "p2",
        "topic": "feedback mechanism",
        "method": "survey",
        "finding": "Higher engagement",
        "limitation": "Short duration",
    })
    return storage


class TestGraphService:
    def test_build_empty_graph(self, service):
        graph = service.build_project_graph("empty")
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_build_graph_with_evidence(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_paper_nodes_created(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        paper_nodes = [n for n in graph.nodes if n.node_type == NodeType.PAPER]
        assert len(paper_nodes) == 2

    def test_topic_nodes_created(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        topic_nodes = [n for n in graph.nodes if n.node_type == NodeType.TOPIC]
        assert len(topic_nodes) >= 1

    def test_method_nodes_created(self, service, sample_evidence):
        graph = service.build_project_graph("proj1")
        method_nodes = [n for n in graph.nodes if n.node_type == NodeType.METHOD]
        assert len(method_nodes) == 2

    def test_get_graph(self, service, sample_evidence):
        service.build_project_graph("proj1")
        graph = service.get_graph("proj1")
        assert graph.project_id == "proj1"

    def test_get_node(self, service, sample_evidence):
        service.build_project_graph("proj1")
        node = service.get_node("proj1", "paper:p1")
        assert node is not None
        assert node.node_type == NodeType.PAPER

    def test_get_neighbors(self, service, sample_evidence):
        service.build_project_graph("proj1")
        result = service.get_neighbors("proj1", "paper:p1", hops=1)
        assert len(result["nodes"]) > 0

    def test_get_subgraph(self, service, sample_evidence):
        service.build_project_graph("proj1")
        result = service.get_subgraph("proj1", ["paper:p1"], hops=1)
        assert len(result["nodes"]) > 0

    def test_find_paths(self, service, sample_evidence):
        service.build_project_graph("proj1")
        paths = service.find_paths("proj1", "paper:p1", "paper:p2", max_hops=3)
        # Both papers connect to same topic, so path exists
        assert len(paths) > 0
