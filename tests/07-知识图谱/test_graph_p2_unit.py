"""P2 单元测试：图谱增强 — remove_paper + local_search

不依赖真实 LLM API / PostgreSQL。
使用 FakeLLMService + 内存 mock storage。
"""

import pytest

from src.agents_v3.research_workspace.models import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
    EdgeType,
)
from src.agents_v3.research_workspace.services.graph_builders import GraphBuilderMixin
from src.agents_v3.research_workspace.services.graph_query import GraphQueryMixin


# ── Mock Storage ──────────────────────────────────────


class MockStorage:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get_item(self, table: str, item_id: str):
        return self._data.get(table, {}).get(item_id)

    def upsert_item(self, table: str, item_id: str, item: dict):
        self._data.setdefault(table, {})[item_id] = item

    def query(self, table: str, filters: dict):
        items = self._data.get(table, {}).values()
        result = []
        for item in items:
            match = True
            for k, v in filters.items():
                if isinstance(v, list):
                    if item.get(k) not in v:
                        match = False
                        break
                elif item.get(k) != v:
                    match = False
                    break
            if match:
                result.append(item)
        return result

    def list_all(self, table: str):
        return list(self._data.get(table, {}).values())


# ── Helpers ───────────────────────────────────────────


def _make_graph():
    """构建测试图谱：paper1 → topic:A, paper1 → method:X, paper2 → topic:A, paper2 → dataset:D"""
    nodes = [
        GraphNode(node_id="paper:p1", node_type=NodeType.PAPER, label="Paper 1",
                  properties={"paper_ids": ["p1"], "evidence_ids": ["ev1"]}),
        GraphNode(node_id="paper:p2", node_type=NodeType.PAPER, label="Paper 2",
                  properties={"paper_ids": ["p2"], "evidence_ids": ["ev2"]}),
        GraphNode(node_id="topic:A", node_type=NodeType.TOPIC, label="Topic A",
                  properties={"paper_ids": ["p1", "p2"], "evidence_ids": ["ev1", "ev2"]}),
        GraphNode(node_id="method:X", node_type=NodeType.METHOD, label="Method X",
                  properties={"paper_ids": ["p1"], "evidence_ids": ["ev1"]}),
        GraphNode(node_id="dataset:D", node_type=NodeType.DATASET, label="Dataset D",
                  paper_ids=["p2"], evidence_ids=["ev2"]),
        GraphNode(node_id="gap:G1", node_type=NodeType.GAP, label="Gap G1",
                  properties={"paper_ids": ["p1"], "evidence_ids": ["ev1"], "confidence": 0.7}),
    ]
    # Fix dataset node
    nodes[4] = GraphNode(node_id="dataset:D", node_type=NodeType.DATASET, label="Dataset D",
                         properties={"paper_ids": ["p2"], "evidence_ids": ["ev2"]})

    edges = [
        GraphEdge(edge_id="e1", source_id="paper:p1", target_id="topic:A",
                  edge_type=EdgeType.BELONGS_TO_TOPIC, properties={"paper_ids": ["p1"]}),
        GraphEdge(edge_id="e2", source_id="paper:p1", target_id="method:X",
                  edge_type=EdgeType.USES_METHOD, properties={"paper_ids": ["p1"]}),
        GraphEdge(edge_id="e3", source_id="paper:p2", target_id="topic:A",
                  edge_type=EdgeType.BELONGS_TO_TOPIC, properties={"paper_ids": ["p2"]}),
        GraphEdge(edge_id="e4", source_id="paper:p2", target_id="dataset:D",
                  edge_type=EdgeType.USES_DATASET, properties={"paper_ids": ["p2"]}),
        GraphEdge(edge_id="e5", source_id="gap:G1", target_id="topic:A",
                  edge_type=EdgeType.SUGGESTS_GAP, properties={"paper_ids": ["p1"]}),
    ]
    return KnowledgeGraph(project_id="proj1", nodes=nodes, edges=edges)


class GraphBuilderForTest(GraphBuilderMixin):
    """Mixin 测试桩"""
    def __init__(self, graph):
        self._graph = graph

    def get_graph(self, project_id):
        return self._graph

    def _save_graph(self, project_id, graph):
        self._graph = graph


class GraphQueryForTest(GraphQueryMixin):
    """Mixin 测试桩"""
    def __init__(self, graph):
        self._graph = graph

    def get_graph(self, project_id):
        return self._graph


# ── remove_paper 测试 ────────────────────────────────


class TestRemovePaper:

    def test_removes_paper_node(self):
        graph = _make_graph()
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")
        node_ids = [n.node_id for n in result.nodes]
        assert "paper:p1" not in node_ids
        assert "paper:p2" in node_ids

    def test_removes_orphan_topic(self):
        """method:X 只有 p1，p1 移除后 method:X 应被清理"""
        graph = _make_graph()
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")
        node_ids = [n.node_id for n in result.nodes]
        assert "method:X" not in node_ids  # orphan

    def test_keeps_shared_topic(self):
        """topic:A 有 p1 和 p2，移除 p1 后 topic:A 应保留"""
        graph = _make_graph()
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")
        node_ids = [n.node_id for n in result.nodes]
        assert "topic:A" in node_ids
        # paper_ids 应只剩 p2
        topic_a = next(n for n in result.nodes if n.node_id == "topic:A")
        assert topic_a.properties["paper_ids"] == ["p2"]

    def test_removes_associated_edges(self):
        graph = _make_graph()
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")
        edge_ids = [e.edge_id for e in result.edges]
        assert "e1" not in edge_ids  # p1→topic:A
        assert "e2" not in edge_ids  # p1→method:X
        assert "e3" in edge_ids      # p2→topic:A

    def test_removes_orphan_edge(self):
        """孤立节点的边应被移除"""
        graph = _make_graph()
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")
        edge_ids = [e.edge_id for e in result.edges]
        assert "e5" not in edge_ids  # gap:G1 被移除，e5 也随之移除

    def test_returns_updated_graph(self):
        graph = _make_graph()
        original_count = len(graph.nodes)
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")
        assert isinstance(result, KnowledgeGraph)
        assert len(result.nodes) < original_count


# ── local_search 测试 ────────────────────────────────


class TestLocalSearch:

    def test_returns_empty_for_empty_graph(self):
        empty_graph = KnowledgeGraph(project_id="proj1", nodes=[], edges=[])
        query = GraphQueryForTest(empty_graph)
        from unittest.mock import patch, MagicMock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = ""
        with patch("src.agents_v3.research_workspace.llm.service.get_llm_service", return_value=mock_llm):
            result = query.local_search("proj1", "test question", ["topic:A"])
        assert result["sources"] == []

    def test_returns_related_papers_and_evidence(self):
        """local_search 应返回关联的 paper 和 evidence IDs"""
        graph = _make_graph()
        query = GraphQueryForTest(graph)
        from unittest.mock import patch, MagicMock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Test answer about Topic A"
        with patch("src.agents_v3.research_workspace.llm.service.get_llm_service", return_value=mock_llm):
            result = query.local_search("proj1", "what is Topic A?", ["topic:A"])
        assert result["answer"] == "Test answer about Topic A"
        assert "p1" in result["sources"] or "p2" in result["sources"]

    def test_uses_seed_nodes_for_subgraph(self):
        graph = _make_graph()
        query = GraphQueryForTest(graph)
        from unittest.mock import patch, MagicMock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Answer"
        with patch("src.agents_v3.research_workspace.llm.service.get_llm_service", return_value=mock_llm):
            result = query.local_search("proj1", "test", ["method:X"], hops=1)
        assert "p1" in result["sources"]
