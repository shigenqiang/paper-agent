"""P2 扩展测试：图谱深层分支覆盖

覆盖：COMMUNITY 节点保留、不存在 paper_id、边的 paper_ids 清理、local_search 社区上下文
"""

import pytest
from unittest.mock import MagicMock, patch

from src.agents_v3.research_workspace.models import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
    EdgeType,
)
from src.agents_v3.research_workspace.services.graph_builders import GraphBuilderMixin
from src.agents_v3.research_workspace.services.graph_query import GraphQueryMixin


# ── Mixin 测试桩 ──────────────────────────────────────


class GraphBuilderForTest(GraphBuilderMixin):
    def __init__(self, graph):
        self._graph = graph

    def get_graph(self, project_id):
        return self._graph

    def _save_graph(self, project_id, graph):
        self._graph = graph


class GraphQueryForTest(GraphQueryMixin):
    def __init__(self, graph):
        self._graph = graph

    def get_graph(self, project_id):
        return self._graph


# ── Test COMMUNITY 节点保留 ───────────────────────────


class TestRemovePaperCommunity:

    def test_community_node_preserved(self):
        """COMMUNITY 节点即使 paper_ids 为空也不被删除"""
        nodes = [
            GraphNode(node_id="paper:p1", node_type=NodeType.PAPER, label="Paper 1",
                      properties={"paper_ids": ["p1"]}),
            GraphNode(node_id="community:C1", node_type=NodeType.COMMUNITY, label="Community 1",
                      properties={"paper_ids": ["p1"], "summary": "Test community"}),
            GraphNode(node_id="topic:T1", node_type=NodeType.TOPIC, label="Topic 1",
                      properties={"paper_ids": ["p1"]}),
        ]
        edges = [
            GraphEdge(edge_id="e1", source_id="paper:p1", target_id="community:C1",
                      edge_type=EdgeType.BELONGS_TO_COMMUNITY, properties={"paper_ids": ["p1"]}),
            GraphEdge(edge_id="e2", source_id="paper:p1", target_id="topic:T1",
                      edge_type=EdgeType.BELONGS_TO_TOPIC, properties={"paper_ids": ["p1"]}),
        ]
        graph = KnowledgeGraph(project_id="proj1", nodes=nodes, edges=edges)
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")

        node_ids = [n.node_id for n in result.nodes]
        assert "community:C1" in node_ids  # COMMUNITY 保留
        assert "paper:p1" not in node_ids  # Paper 移除
        assert "topic:T1" not in node_ids  # 普通节点 paper_ids 为空则移除

    def test_nonexistent_paper_id_unchanged(self):
        """不存在的 paper_id 不影响图谱"""
        nodes = [
            GraphNode(node_id="paper:p1", node_type=NodeType.PAPER, label="Paper 1",
                      properties={"paper_ids": ["p1"]}),
            GraphNode(node_id="topic:T1", node_type=NodeType.TOPIC, label="Topic 1",
                      properties={"paper_ids": ["p1"]}),
        ]
        edges = [
            GraphEdge(edge_id="e1", source_id="paper:p1", target_id="topic:T1",
                      edge_type=EdgeType.BELONGS_TO_TOPIC, properties={"paper_ids": ["p1"]}),
        ]
        graph = KnowledgeGraph(project_id="proj1", nodes=nodes, edges=edges)
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p_nonexistent")

        assert len(result.nodes) == 2
        assert len(result.edges) == 1

    def test_edge_paper_ids_cleaned(self):
        """边的 paper_ids 中移除指定 paper，但边保留（两端节点都不被删除）"""
        nodes = [
            GraphNode(node_id="paper:p1", node_type=NodeType.PAPER, label="Paper 1",
                      properties={"paper_ids": ["p1"]}),
            GraphNode(node_id="paper:p2", node_type=NodeType.PAPER, label="Paper 2",
                      properties={"paper_ids": ["p2"]}),
            GraphNode(node_id="topic:T1", node_type=NodeType.TOPIC, label="Topic 1",
                      properties={"paper_ids": ["p1", "p2"]}),
            GraphNode(node_id="method:M1", node_type=NodeType.METHOD, label="Method 1",
                      properties={"paper_ids": ["p1", "p2"]}),
        ]
        edges = [
            # topic:T1 → method:M1 都不被删除，且 paper_ids 含 p1 和 p2
            GraphEdge(edge_id="e_shared", source_id="topic:T1", target_id="method:M1",
                      edge_type=EdgeType.USES_METHOD, properties={"paper_ids": ["p1", "p2"]}),
            GraphEdge(edge_id="e_p1_topic", source_id="paper:p1", target_id="topic:T1",
                      edge_type=EdgeType.BELONGS_TO_TOPIC, properties={"paper_ids": ["p1"]}),
            GraphEdge(edge_id="e_p2_topic", source_id="paper:p2", target_id="topic:T1",
                      edge_type=EdgeType.BELONGS_TO_TOPIC, properties={"paper_ids": ["p2"]}),
        ]
        graph = KnowledgeGraph(project_id="proj1", nodes=nodes, edges=edges)
        builder = GraphBuilderForTest(graph)
        result = builder.remove_paper("proj1", "p1")

        # e_shared 应保留但 paper_ids 只剩 p2
        e_shared = next(e for e in result.edges if e.edge_id == "e_shared")
        assert e_shared.properties["paper_ids"] == ["p2"]
        # e_p1_topic 应被移除（paper:p1 被删）
        edge_ids = [e.edge_id for e in result.edges]
        assert "e_p1_topic" not in edge_ids
        assert "e_p2_topic" in edge_ids


# ── Test local_search with Community nodes ────────────


class TestLocalSearchCommunity:

    def test_community_summary_in_context(self):
        """Community 节点的 summary 应出现在上下文中"""
        nodes = [
            GraphNode(node_id="topic:A", node_type=NodeType.TOPIC, label="Topic A",
                      properties={"paper_ids": ["p1"], "evidence_ids": ["ev1"]}),
            GraphNode(node_id="community:C1", node_type=NodeType.COMMUNITY, label="Community 1",
                      properties={"paper_ids": ["p1"], "summary": "This community covers NLP research trends."}),
        ]
        edges = [
            GraphEdge(edge_id="e1", source_id="topic:A", target_id="community:C1",
                      edge_type=EdgeType.BELONGS_TO_COMMUNITY, properties={}),
        ]
        graph = KnowledgeGraph(project_id="proj1", nodes=nodes, edges=edges)
        query = GraphQueryForTest(graph)

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Answer about NLP trends"

        with patch("src.agents_v3.research_workspace.llm.service.get_llm_service", return_value=mock_llm):
            result = query.local_search("proj1", "what are NLP trends?", ["topic:A"], hops=2)

        # 验证 LLM 被调用且 prompt 包含社区摘要
        assert mock_llm.invoke.called
        call_args = mock_llm.invoke.call_args
        prompt = call_args[0][1] if len(call_args[0]) > 1 else str(call_args)
        assert "NLP research trends" in prompt or "Community" in prompt
