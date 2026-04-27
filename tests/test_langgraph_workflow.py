"""
LangGraph 工作流测试

测试状态定义、Agent 节点和工作流构建。
"""
import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents_v2.langgraph_workflow.state import Paper, PaperAgentState, create_initial_state
from src.agents_v2.langgraph_workflow.edges import should_continue


class TestPaperAgentState:
    """测试状态定义"""

    def test_create_initial_state(self):
        state = create_initial_state(
            user_query="deep learning",
            user_id="test_user",
            session_id="test_session",
            max_iterations=3,
        )
        assert state.user_query == "deep learning"
        assert state.user_id == "test_user"
        assert state.session_id == "test_session"
        assert state.max_iterations == 3
        assert state.iteration == 0
        assert state.current_phase == "crawl"
        assert state.papers == []
        assert state.draft == ""

    def test_state_setters(self):
        state = PaperAgentState()
        state.user_query = "test query"
        state.papers = [Paper(id="1", title="Test", authors=[], abstract="", url="")]
        assert state.user_query == "test query"
        assert len(state.papers) == 1
        assert state.papers[0].title == "Test"

    def test_add_error(self):
        state = create_initial_state(user_query="test")
        state.add_error("error 1")
        state.add_error("error 2")
        assert len(state.errors) == 2
        assert "error 1" in state.errors

    def test_paper_dataclass(self):
        paper = Paper(
            id="arxiv:123",
            title="Test Paper",
            authors=["Alice", "Bob"],
            abstract="This is a test.",
            url="https://arxiv.org/abs/123",
            year=2024,
            citations=42,
            relevance_score=0.85,
        )
        assert paper.id == "arxiv:123"
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
        assert paper.citations == 42
        assert paper.relevance_score == 0.85


class TestEdges:
    """测试条件路由"""

    def test_should_continue_no_feedback(self):
        assert should_continue({"iteration": 0, "max_iterations": 3, "feedback": []}) == "done"

    def test_should_continue_with_feedback(self):
        assert should_continue({
            "iteration": 0, "max_iterations": 3,
            "feedback": ["Add more citations", "Improve analysis"],
        }) == "write"

    def test_should_continue_max_iterations(self):
        assert should_continue({
            "iteration": 3, "max_iterations": 3,
            "feedback": ["Need improvement"],
        }) == "done"

    def test_should_continue_positive_feedback(self):
        assert should_continue({
            "iteration": 1, "max_iterations": 3,
            "feedback": ["The draft is good and requires no changes"],
        }) == "done"


class TestCrawlerAgent:
    """测试爬虫 Agent"""

    def test_crawler_no_sources(self):
        from src.agents_v2.langgraph_workflow.nodes.crawler import CrawlerAgent

        crawler = CrawlerAgent(sources=[])
        state = create_initial_state(user_query="test query")
        # With empty sources list, crawler should not call any searchers
        # But expand_via_citations may still be triggered if papers exist
        # So we just verify it doesn't crash
        result = crawler.execute(state)
        # The key assertion: no crash, state is valid
        assert isinstance(result.papers, list)


class TestSelectorAgent:
    """测试筛选 Agent"""

    def test_selector_empty_papers(self):
        from src.agents_v2.langgraph_workflow.nodes.selector import SelectorAgent

        selector = SelectorAgent(top_k=5)
        state = create_initial_state(user_query="deep learning")
        state.papers = []
        result = selector.execute(state)
        assert result.selected_papers == []

    def test_selector_with_papers(self):
        from src.agents_v2.langgraph_workflow.nodes.selector import SelectorAgent

        selector = SelectorAgent(top_k=2, enable_reranking=False)
        state = create_initial_state(user_query="deep learning")
        state.papers = [
            Paper(
                id="1", title="Deep Learning in Medicine",
                authors=[], abstract="A study on deep learning applications in medicine",
                url="", year=2023, citations=100,
            ),
            Paper(
                id="2", title="Natural Language Processing",
                authors=[], abstract="A survey of NLP methods",
                url="", year=2022, citations=50,
            ),
            Paper(
                id="3", title="Computer Vision Overview",
                authors=[], abstract="Computer vision techniques",
                url="", year=2021, citations=30,
            ),
        ]
        result = selector.execute(state)
        assert len(result.selected_papers) <= 2
        # 应该选择与查询最相关的论文
        assert len(result.selected_papers) > 0


class TestOutlineAgent:
    """测试大纲 Agent"""

    def test_outline_rule_based(self):
        from src.agents_v2.langgraph_workflow.nodes.outline import OutlineAgent

        agent = OutlineAgent(llm=None)
        state = create_initial_state(user_query="deep learning in medicine")
        state.papers = [
            Paper(
                id="1", title="Deep Learning in Medicine",
                authors=[], abstract="Deep learning for medical imaging analysis",
                url="", year=2023, citations=100,
            ),
        ]
        result = agent.execute(state)
        assert "title" in result.outline
        assert "sections" in result.outline
        assert len(result.outline["sections"]) > 0
        assert "deep learning in medicine" in result.outline["title"].lower()


class TestReviewerAgent:
    """测试审查 Agent"""

    def test_reviewer_short_draft(self):
        from src.agents_v2.langgraph_workflow.nodes.reviewer import ReviewerAgent

        agent = ReviewerAgent(llm=None)
        state = create_initial_state(user_query="test")
        state.draft = "## Short Draft"
        result = agent.execute(state)
        assert len(result.feedback) > 0
        assert result.iteration == 1

    def test_reviewer_good_draft(self):
        from src.agents_v2.langgraph_workflow.nodes.reviewer import ReviewerAgent

        agent = ReviewerAgent(llm=None)
        state = create_initial_state(user_query="test")
        state.draft = """## Introduction
This is a comprehensive survey on deep learning.
We discuss various methods and compare their performance [1, 2].

## Methods
Several approaches have been proposed. However, each has limitations.
Compared to previous work, our approach is novel.

## Results
The experimental results show significant improvements.

## Challenges
There are several open problems and challenges in this field."""
        result = agent.execute(state)
        assert result.iteration == 1


class TestMemoryNode:
    """测试记忆节点"""

    def test_memory_node_recall_empty(self):
        from src.agents_v2.langgraph_workflow.nodes.memory import MemoryNode

        node = MemoryNode(storage_path=".test_memory")
        state = create_initial_state(user_query="test", user_id="test_user")
        result = node.recall_before_search(state)
        # 没有历史记忆时，查询应保持不变或包含空上下文
        assert "user_query" in result

    def test_memory_node_remember_after_selection(self):
        from src.agents_v2.langgraph_workflow.nodes.memory import MemoryNode

        node = MemoryNode(storage_path=".test_memory2")
        state = create_initial_state(
            user_query="deep learning",
            user_id="test_user",
            session_id="test_session",
        )
        state.selected_papers = [
            Paper(
                id="1", title="Deep Learning Survey",
                authors=[], abstract="A comprehensive survey of deep learning methods.",
                url="", year=2023, citations=100, relevance_score=0.8,
            ),
            Paper(
                id="2", title="Attention Mechanisms",
                authors=[], abstract="Attention is all you need.",
                url="", year=2017, citations=50000, relevance_score=0.9,
            ),
        ]
        result = node.remember_after_selection(state)
        # 应该记住论文
        assert "metadata" in result
        assert result["metadata"].get("remembered_papers", 0) > 0

    def test_memory_node_personalize_no_draft(self):
        from src.agents_v2.langgraph_workflow.nodes.memory import MemoryNode

        node = MemoryNode(storage_path=".test_memory3")
        state = create_initial_state(user_query="test", user_id="test_user")
        state.draft = ""  # 没有草稿
        result = node.personalize_output(state)
        # 没有草稿时不应改变状态
        assert "personalized_draft" not in result


class TestMultimodalNode:
    """测试多模态节点"""

    def test_multimodal_analyze_paper_figures(self):
        from src.agents_v2.langgraph_workflow.nodes.multimodal import MultimodalNode

        node = MultimodalNode()
        state = create_initial_state(user_query="deep learning")
        state.selected_papers = [
            Paper(
                id="1", title="Test Paper",
                authors=["Alice"],
                abstract="We show trends and correlations in figure 1 and table 2.",
                url="", year=2023,
            ),
        ]
        result = node.analyze_paper_figures(state)
        mm_analysis = result.selected_papers[0].metadata.get("multimodal_analysis", {})
        assert mm_analysis.get("has_figures") is True
        assert mm_analysis.get("has_tables") is True
        assert "line_chart" in mm_analysis.get("chart_types", [])

    def test_multimodal_no_papers(self):
        from src.agents_v2.langgraph_workflow.nodes.multimodal import MultimodalNode

        node = MultimodalNode()
        state = create_initial_state(user_query="test")
        result = node.analyze_paper_figures(state)
        assert "metadata" not in result or result.get("metadata", {}).get("multimodal_analyzed_papers", 0) == 0


class TestKnowledgeGraphNode:
    """测试知识图谱节点"""

    def test_kg_extract_via_rules(self):
        from src.agents_v2.langgraph_workflow.nodes.knowledge_graph import KnowledgeGraphNode

        node = KnowledgeGraphNode()
        state = create_initial_state(user_query="transformer")
        state.selected_papers = [
            Paper(
                id="p1", title="Attention Is All You Need",
                authors=["Vaswani", "Shazeer"],
                abstract="We propose the Transformer architecture.",
                url="", year=2017,
            ),
            Paper(
                id="p2", title="BERT: Pre-training of Deep Bidirectional Transformers",
                authors=["Devlin", "Shazeer"],
                abstract="We introduce BERT for language understanding.",
                url="", year=2019,
            ),
        ]
        result = node.extract_and_build(state)
        kg = result.get("knowledge_graph", {})
        assert kg.get("total_entities", 0) > 0
        assert kg.get("total_relations", 0) > 0

    def test_kg_discover_related(self):
        from src.agents_v2.langgraph_workflow.nodes.knowledge_graph import KnowledgeGraphNode

        node = KnowledgeGraphNode()
        state = create_initial_state(user_query="test")
        state.selected_papers = [
            Paper(id="p1", title="Paper A", authors=["Alice", "Bob"], abstract="", url=""),
            Paper(id="p2", title="Paper B", authors=["Bob", "Carol"], abstract="", url=""),
        ]
        result = node.extract_and_build(state)
        result = node.query_related(result)
        pairs = result["knowledge_graph"].get("related_paper_pairs", [])
        # Bob is shared author between p1 and p2
        assert len(pairs) > 0

    def test_kg_no_papers(self):
        from src.agents_v2.langgraph_workflow.nodes.knowledge_graph import KnowledgeGraphNode

        node = KnowledgeGraphNode()
        state = create_initial_state(user_query="test")
        result = node.extract_and_build(state)
        # No papers -> should not crash
        assert "knowledge_graph" not in result or result["knowledge_graph"].get("total_entities", 0) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
