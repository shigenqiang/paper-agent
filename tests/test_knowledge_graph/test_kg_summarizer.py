"""
知识图谱子图摘要生成测试
"""
import pytest
from src.agents_v2.knowledge_graph import kg_summarizer


class TestGraphNode:
    """GraphNode类测试"""

    def test_creation(self):
        """测试创建"""
        node = kg_summarizer.GraphNode(
            id="paper_1",
            type="Paper",
            properties={"title": "Deep Learning", "year": 2024}
        )
        assert node.id == "paper_1"
        assert node.type == "Paper"
        assert node.properties["title"] == "Deep Learning"

    def test_default_properties(self):
        """测试默认属性"""
        node = kg_summarizer.GraphNode(id="e1", type="Author")
        assert node.properties == {}


class TestGraphEdge:
    """GraphEdge类测试"""

    def test_creation(self):
        """测试创建"""
        edge = kg_summarizer.GraphEdge(
            source="paper_1",
            target="author_1",
            relation="AUTHORED_BY"
        )
        assert edge.source == "paper_1"
        assert edge.target == "author_1"
        assert edge.relation == "AUTHORED_BY"


class TestSubgraph:
    """Subgraph类测试"""

    def test_empty_subgraph(self):
        """测试空子图"""
        subgraph = kg_summarizer.Subgraph(nodes={}, edges=[])
        assert len(subgraph.nodes) == 0
        assert len(subgraph.edges) == 0

    def test_get_node(self):
        """测试获取节点"""
        node = kg_summarizer.GraphNode(id="e1", type="Paper")
        subgraph = kg_summarizer.Subgraph(nodes={"e1": node}, edges=[])

        assert subgraph.get_node("e1") == node
        assert subgraph.get_node("nonexistent") is None

    def test_get_neighbors(self):
        """测试获取邻居"""
        edges = [
            kg_summarizer.GraphEdge("e1", "e2", "CITES"),
            kg_summarizer.GraphEdge("e1", "e3", "AUTHORED_BY")
        ]
        subgraph = kg_summarizer.Subgraph(nodes={}, edges=edges)

        neighbors = subgraph.get_neighbors("e1")
        assert set(neighbors) == {"e2", "e3"}

    def test_get_outgoing_relations(self):
        """测试获取出边"""
        edges = [
            kg_summarizer.GraphEdge("e1", "e2", "CITES"),
            kg_summarizer.GraphEdge("e1", "e3", "AUTHORED_BY")
        ]
        subgraph = kg_summarizer.Subgraph(nodes={}, edges=edges)

        outgoing = subgraph.get_outgoing_relations("e1")
        assert set(outgoing) == {("CITES", "e2"), ("AUTHORED_BY", "e3")}

    def test_get_incoming_relations(self):
        """测试获取入边"""
        edges = [
            kg_summarizer.GraphEdge("e2", "e1", "CITES"),
            kg_summarizer.GraphEdge("e3", "e1", "AUTHORED_BY")
        ]
        subgraph = kg_summarizer.Subgraph(nodes={}, edges=edges)

        incoming = subgraph.get_incoming_relations("e1")
        assert set(incoming) == {("CITES", "e2"), ("AUTHORED_BY", "e3")}


class TestSubgraphExtractor:
    """SubgraphExtractor类测试"""

    def test_empty_extractor(self):
        """测试空提取器"""
        extractor = kg_summarizer.SubgraphExtractor()
        subgraph = extractor.extract_subgraph(["e1"])
        assert len(subgraph.nodes) == 0

    def test_add_node(self):
        """测试添加节点"""
        extractor = kg_summarizer.SubgraphExtractor()
        extractor.add_node("paper_1", "Paper", {"title": "Test Paper"})

        assert "paper_1" in extractor._nodes
        assert extractor._nodes["paper_1"].type == "Paper"

    def test_add_edge(self):
        """测试添加边"""
        extractor = kg_summarizer.SubgraphExtractor()
        extractor.add_node("paper_1", "Paper")
        extractor.add_node("author_1", "Author")
        extractor.add_edge("paper_1", "author_1", "AUTHORED_BY")

        assert len(extractor._edges) == 1
        assert extractor._edges[0].relation == "AUTHORED_BY"

    def test_extract_subgraph_single_node(self):
        """测试提取单节点子图"""
        extractor = kg_summarizer.SubgraphExtractor()
        extractor.add_node("paper_1", "Paper", {"title": "Test"})
        extractor.add_edge("paper_1", "author_1", "AUTHORED_BY")

        subgraph = extractor.extract_subgraph(["paper_1"], depth=0)

        assert "paper_1" in subgraph.nodes
        assert len(subgraph.edges) == 0

    def test_extract_subgraph_with_depth(self):
        """测试带深度提取"""
        extractor = kg_summarizer.SubgraphExtractor()
        extractor.add_node("paper_1", "Paper")
        extractor.add_node("author_1", "Author")
        extractor.add_node("venue_1", "Venue")
        extractor.add_edge("paper_1", "author_1", "AUTHORED_BY")
        extractor.add_edge("paper_1", "venue_1", "PUBLISHED_IN")

        subgraph = extractor.extract_subgraph(["paper_1"], depth=1)

        assert "paper_1" in subgraph.nodes
        assert "author_1" in subgraph.nodes
        assert "venue_1" in subgraph.nodes

    def test_extract_ego_network(self):
        """测试ego网络提取"""
        extractor = kg_summarizer.SubgraphExtractor()
        extractor.add_node("e1", "Paper")
        extractor.add_node("e2", "Author")
        extractor.add_node("e3", "Venue")
        extractor.add_edge("e1", "e2", "AUTHORED_BY")
        extractor.add_edge("e1", "e3", "PUBLISHED_IN")

        ego = extractor.extract_ego_network("e1", depth=1)

        assert "e1" in ego.nodes
        assert "e2" in ego.nodes
        assert "e3" in ego.nodes


class TestGraphSentenceGenerator:
    """GraphSentenceGenerator类测试"""

    def test_generation(self):
        """测试句子生成"""
        gen = kg_summarizer.GraphSentenceGenerator()
        sentence = gen.generate_sentence("Paper A", "CITES", "Paper B")
        assert "Paper A" in sentence
        assert "Paper B" in sentence
        assert "引用" in sentence

    def test_unknown_relation(self):
        """测试未知关系"""
        gen = kg_summarizer.GraphSentenceGenerator()
        sentence = gen.generate_sentence("E1", "UNKNOWN_REL", "E2")
        assert "E1" in sentence
        assert "E2" in sentence

    def test_entity_description(self):
        """测试实体描述生成"""
        gen = kg_summarizer.GraphSentenceGenerator()
        node = kg_summarizer.GraphNode(
            id="paper_1",
            type="Paper",
            properties={"title": "Deep Learning", "year": 2024, "citation_count": 100}
        )

        desc = gen.generate_entity_description(
            node,
            [("CITES", "paper_2")],
            [("AUTHORED_BY", "author_1")]
        )

        assert "paper_1" in desc or "Deep Learning" in desc
        assert "Paper" in desc
        assert "2024" in desc

    def test_subgraph_description(self):
        """测试子图描述生成"""
        gen = kg_summarizer.GraphSentenceGenerator()
        nodes = {
            "e1": kg_summarizer.GraphNode(id="e1", type="Paper"),
            "e2": kg_summarizer.GraphNode(id="e2", type="Author"),
            "e3": kg_summarizer.GraphNode(id="e3", type="Paper")
        }
        edges = [
            kg_summarizer.GraphEdge("e1", "e2", "AUTHORED_BY"),
            kg_summarizer.GraphEdge("e1", "e3", "CITES")
        ]
        subgraph = kg_summarizer.Subgraph(nodes=nodes, edges=edges)

        desc = gen.generate_subgraph_description(subgraph)

        assert "3" in desc
        assert "2" in desc


class TestEntityDescriptionGenerator:
    """EntityDescriptionGenerator类测试"""

    def test_paper_description(self):
        """测试论文描述"""
        gen = kg_summarizer.EntityDescriptionGenerator()
        node = kg_summarizer.GraphNode(
            id="paper_1",
            type="Paper",
            properties={"title": "Deep Learning", "year": 2024, "citation_count": 100}
        )

        desc = gen.generate_description(node, [])

        assert "论文" in desc
        assert "2024" in desc
        assert "100" in desc

    def test_author_description(self):
        """测试作者描述"""
        gen = kg_summarizer.EntityDescriptionGenerator()
        node = kg_summarizer.GraphNode(
            id="author_1",
            type="Author",
            properties={"name": "John Doe", "institution": "MIT", "h_index": 50}
        )

        desc = gen.generate_description(node, [])

        assert "作者" in desc
        assert "MIT" in desc
        assert "50" in desc

    def test_with_context(self):
        """测试带上下文描述"""
        gen = kg_summarizer.EntityDescriptionGenerator()
        node = kg_summarizer.GraphNode(
            id="paper_1",
            type="Paper",
            properties={"title": "Test Paper"}
        )

        context = [
            ("CITES", "Other Paper", "out"),
            ("AUTHORED_BY", "John Doe", "in")
        ]

        desc = gen.generate_description(node, context)

        assert "Test Paper" in desc
        assert "CITES" in desc


class TestSubgraphSummarizer:
    """SubgraphSummarizer类测试"""

    def test_build_subgraph(self):
        """测试构建子图"""
        summarizer = kg_summarizer.SubgraphSummarizer()
        summarizer.build_subgraph(
            entities=[
                ("paper_1", "Paper", {"title": "Paper 1"}),
                ("author_1", "Author", {"name": "Author 1"})
            ],
            relations=[
                ("paper_1", "author_1", "AUTHORED_BY", {})
            ]
        )

        assert "paper_1" in summarizer.extractor._nodes
        assert "author_1" in summarizer.extractor._nodes
        assert len(summarizer.extractor._edges) == 1

    def test_summarize(self):
        """测试摘要生成"""
        summarizer = kg_summarizer.SubgraphSummarizer()
        summarizer.build_subgraph(
            entities=[
                ("paper_1", "Paper", {"title": "Paper 1", "year": 2024}),
                ("author_1", "Author", {"name": "Author 1"})
            ],
            relations=[
                ("paper_1", "author_1", "AUTHORED_BY", {})
            ]
        )

        summary = summarizer.summarize(["paper_1"], depth=1)

        assert isinstance(summary, kg_summarizer.SubgraphSummary)
        assert "paper_1" in [ctx.entity_id for ctx in summary.entity_contexts]
        assert summary.statistics["total_nodes"] >= 1

    def test_summarize_empty(self):
        """测试空实体列表"""
        summarizer = kg_summarizer.SubgraphSummarizer()
        summary = summarizer.summarize([], depth=1)

        assert summary.statistics["total_nodes"] == 0
        assert summary.summary_text == "空子图"

    def test_generate_context_for_rag(self):
        """测试GraphRAG上下文生成"""
        summarizer = kg_summarizer.SubgraphSummarizer()
        summarizer.build_subgraph(
            entities=[
                ("paper_1", "Paper", {"title": "Deep Learning"}),
                ("author_1", "Author", {"name": "John"})
            ],
            relations=[
                ("paper_1", "author_1", "AUTHORED_BY", {})
            ]
        )

        context = summarizer.generate_context_for_rag(
            query="Deep Learning",
            entities=["paper_1"],
            depth=1
        )

        assert "subgraph_summary" in context
        assert "context_text" in context
        assert "entity_map" in context
        assert "paper_1" in context["entity_map"]


class TestSubgraphSummary:
    """SubgraphSummary类测试"""

    def test_creation(self):
        """测试创建"""
        subgraph = kg_summarizer.Subgraph(nodes={}, edges=[])
        entity_ctx = kg_summarizer.EntityContext(
            entity_id="e1",
            entity_type="Paper",
            name="Test",
            description="Test paper",
            properties={},
            neighbors=[],
            relations_as_source=[],
            relations_as_target=[]
        )

        summary = kg_summarizer.SubgraphSummary(
            subgraph=subgraph,
            summary_text="Test summary",
            entity_contexts=[entity_ctx],
            key_relations=[("e1", "CITES", "e2")],
            statistics={"total_nodes": 1}
        )

        assert summary.summary_text == "Test summary"
        assert len(summary.entity_contexts) == 1
        assert len(summary.key_relations) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
