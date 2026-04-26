"""
Citation Graph 单元测试

测试引用图谱功能
"""
import pytest

from src.agents_v2.tools.citation_graph import (
    CitationGraph,
    CitationNode,
    CitationEdge,
    create_citation_graph
)


class TestCitationGraph:
    """CitationGraph 测试"""

    def setup_method(self):
        self.graph = CitationGraph()

    def test_initialization(self):
        """测试初始化"""
        assert len(self.graph.nodes) == 0
        assert len(self.graph.edges) == 0

    def test_add_paper(self):
        """测试添加论文"""
        node = self.graph.add_paper(
            paper_id="paper1",
            title="Test Paper",
            authors=["Author 1", "Author 2"],
            year=2024
        )

        assert node.paper_id == "paper1"
        assert node.title == "Test Paper"
        assert len(self.graph.nodes) == 1

    def test_add_citation(self):
        """测试添加引用"""
        self.graph.add_paper("paper1", "Paper 1", [])
        self.graph.add_paper("paper2", "Paper 2", [])

        self.graph.add_citation("paper1", "paper2")

        assert len(self.graph.edges) == 1
        assert self.graph.nodes["paper1"].references_count == 1
        assert self.graph.nodes["paper2"].citations_count == 1

    def test_get_citations(self):
        """测试获取引用"""
        self.graph.add_paper("paper1", "Paper 1", [])
        self.graph.add_paper("paper2", "Paper 2", [])
        self.graph.add_paper("paper3", "Paper 3", [])

        self.graph.add_citation("paper1", "paper2")
        self.graph.add_citation("paper1", "paper3")

        citations = self.graph.get_citations("paper1")
        assert len(citations) == 2
        assert "paper2" in citations
        assert "paper3" in citations

    def test_get_references(self):
        """测试获取参考文献"""
        self.graph.add_paper("paper1", "Paper 1", [])
        self.graph.add_paper("paper2", "Paper 2", [])

        self.graph.add_citation("paper1", "paper2")

        references = self.graph.get_references("paper2")
        assert "paper1" in references

    def test_get_common_citations(self):
        """测试获取共同引用"""
        self.graph.add_paper("paper1", "Paper 1", [])
        self.graph.add_paper("paper2", "Paper 2", [])
        self.graph.add_paper("paper3", "Paper 3", [])
        self.graph.add_paper("paper4", "Paper 4", [])

        self.graph.add_citation("paper1", "paper3")
        self.graph.add_citation("paper1", "paper4")
        self.graph.add_citation("paper2", "paper3")

        common = self.graph.get_common_citations("paper1", "paper2")
        assert "paper3" in common

    def test_get_influential_papers(self):
        """测试获取高影响力论文"""
        self.graph.add_paper("paper1", "Paper 1", [])
        self.graph.add_paper("paper2", "Paper 2", [])

        # paper2被10篇论文引用
        for i in range(3, 13):
            self.graph.add_paper(f"paper{i}", f"Paper {i}", [])
            self.graph.add_citation(f"paper{i}", "paper2")

        influential = self.graph.get_influential_papers(min_citations=10)
        assert len(influential) == 1
        assert influential[0].paper_id == "paper2"

    def test_get_statistics(self):
        """测试获取统计信息"""
        self.graph.add_paper("paper1", "Paper 1", [], year=2024)
        self.graph.add_paper("paper2", "Paper 2", [], year=2024)
        self.graph.add_citation("paper1", "paper2")

        stats = self.graph.get_statistics()

        assert stats["total_papers"] == 2
        assert stats["total_citations"] == 1


class TestCitationNode:
    """CitationNode 测试"""

    def test_create_node(self):
        """测试创建节点"""
        node = CitationNode(
            paper_id="paper1",
            title="Test",
            authors=["Author 1"]
        )

        assert node.paper_id == "paper1"
        assert node.citations_count == 0


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_create_citation_graph(self):
        """测试创建图谱"""
        graph = create_citation_graph()
        assert isinstance(graph, CitationGraph)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])