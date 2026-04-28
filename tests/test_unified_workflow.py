"""
测试统一工作流 - 单元测试

测试所有新增的工作流节点和路由功能
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch


class TestRouteNode:
    """测试路由节点"""

    @pytest.mark.asyncio
    async def test_route_search_intent(self):
        """测试搜索意图路由"""
        from src.agents_v2.langgraph_workflow.nodes.router import RouteNode

        router = RouteNode()
        state = {"user_query": "搜索深度学习相关论文"}
        result = await router(state)

        assert "route_path" in result
        assert result["route_path"] == "search"
        assert result["intent"] in ["literature_search", "unknown"]

    @pytest.mark.asyncio
    async def test_route_writing_intent(self):
        """测试写作意图路由"""
        from src.agents_v2.langgraph_workflow.nodes.router import RouteNode

        router = RouteNode()
        state = {"user_query": "帮我写一篇关于因果推断的综述"}
        result = await router(state)

        assert "route_path" in result
        assert result["route_path"] == "writing"

    @pytest.mark.asyncio
    async def test_route_empty_query(self):
        """测试空查询"""
        from src.agents_v2.langgraph_workflow.nodes.router import RouteNode

        router = RouteNode()
        state = {"user_query": ""}
        result = await router(state)

        assert result["route_path"] == "search"  # 默认路由


class TestReportNodes:
    """测试报告工作流节点"""

    @pytest.mark.asyncio
    async def test_report_crawl_empty_keywords(self):
        """测试报告爬取 - 空关键词"""
        from src.agents_v2.langgraph_workflow.nodes.report_crawl import ReportCrawlNode

        node = ReportCrawlNode()
        state = {"report_type": "daily", "keywords": [], "user_query": ""}
        result = await node(state)

        assert "papers" in result
        assert result["papers"] == []

    @pytest.mark.asyncio
    async def test_report_analyze_empty_papers(self):
        """测试报告分析 - 空论文列表"""
        from src.agents_v2.langgraph_workflow.nodes.report_analyze import ReportAnalyzeNode

        node = ReportAnalyzeNode()
        state = {"papers": []}
        result = await node(state)

        assert "report_stats" in result
        assert result["report_stats"]["total_papers"] == 0

    @pytest.mark.asyncio
    async def test_report_analyze_with_papers(self):
        """测试报告分析 - 有论文"""
        from src.agents_v2.langgraph_workflow.nodes.report_analyze import ReportAnalyzeNode

        node = ReportAnalyzeNode()
        papers = [
            {
                "title": "Paper 1",
                "authors": ["Author A", "Author B"],
                "year": 2023,
                "venue": "NeurIPS",
                "citations": 100,
            },
            {
                "title": "Paper 2",
                "authors": ["Author A", "Author C"],
                "year": 2024,
                "venue": "ICML",
                "citations": 50,
            },
        ]
        state = {"papers": papers}
        result = await node(state)

        assert result["report_stats"]["total_papers"] == 2
        assert "Author A" in result["report_stats"]["authors"]
        assert len(result["report_stats"]["venues"]) == 2

    @pytest.mark.asyncio
    async def test_report_gen_empty_papers(self):
        """测试报告生成 - 空论文列表"""
        from src.agents_v2.langgraph_workflow.nodes.report_gen import ReportGenNode

        node = ReportGenNode()
        state = {"report_type": "daily", "papers": [], "report_stats": {}}
        result = await node(state)

        assert "report_content" in result
        assert "暂无数据" in result["report_content"]


class TestQANodes:
    """测试问答工作流节点"""

    @pytest.mark.asyncio
    async def test_qa_search_empty_query(self):
        """测试问答搜索 - 空查询"""
        from src.agents_v2.langgraph_workflow.nodes.qa_search import QASearchNode

        node = QASearchNode()
        state = {"user_query": ""}
        result = await node(state)

        assert "papers" in result
        assert result["papers"] == []

    @pytest.mark.asyncio
    async def test_qa_synthesize_empty_papers(self):
        """测试问答综合 - 空论文列表"""
        from src.agents_v2.langgraph_workflow.nodes.qa_synthesize import QASynthesizeNode

        node = QASynthesizeNode()
        state = {"papers": [], "question_type": "BASIC_QUERY", "user_query": "test"}
        result = await node(state)

        assert "qa_synthesis" in result
        assert "未找到相关论文" in result["qa_synthesis"]["summary"]

    @pytest.mark.asyncio
    async def test_qa_answer_empty_synthesis(self):
        """测试问答回答 - 空综合数据"""
        from src.agents_v2.langgraph_workflow.nodes.qa_answer import QAAnswerNode

        node = QAAnswerNode()
        state = {"qa_synthesis": {}, "user_query": "test", "papers": []}
        result = await node(state)

        assert "answer" in result
        assert "抱歉" in result["answer"]


class TestRevisionNodes:
    """测试修改工作流节点"""

    @pytest.mark.asyncio
    async def test_revise_empty_draft(self):
        """测试修改 - 空草稿"""
        from src.agents_v2.langgraph_workflow.nodes.revise import ReviseNode

        node = ReviseNode()
        state = {"draft": ""}
        result = await node(state)

        assert "revised_draft" in result
        assert result["revised_draft"] == ""

    @pytest.mark.asyncio
    async def test_revise_with_draft(self):
        """测试修改 - 有草稿"""
        from src.agents_v2.langgraph_workflow.nodes.revise import ReviseNode

        node = ReviseNode()
        draft = "This  is  a  test  draft  with  extra  spaces."
        state = {"draft": draft}
        result = await node(state)

        assert "revised_draft" in result
        assert "  " not in result["revised_draft"]  # 多余空格应被移除

    @pytest.mark.asyncio
    async def test_refine_empty_draft(self):
        """测试精炼 - 空草稿"""
        from src.agents_v2.langgraph_workflow.nodes.refine import RefineNode

        node = RefineNode()
        state = {"draft": ""}
        result = await node(state)

        assert "refined_draft" in result
        assert result["refined_draft"] == ""

    @pytest.mark.asyncio
    async def test_polish_empty_draft(self):
        """测试润色 - 空草稿"""
        from src.agents_v2.langgraph_workflow.nodes.polish import PolishNode

        node = PolishNode()
        state = {"draft": ""}
        result = await node(state)

        assert "polished_draft" in result
        assert result["polished_draft"] == ""


class TestEdges:
    """测试边和路由函数"""

    def test_route_by_intent_search(self):
        """测试意图路由 - 搜索"""
        from src.agents_v2.langgraph_workflow.edges import route_by_intent

        state = {"route_path": "search"}
        result = route_by_intent(state)
        assert result == "search"

    def test_route_by_intent_writing(self):
        """测试意图路由 - 写作"""
        from src.agents_v2.langgraph_workflow.edges import route_by_intent

        state = {"route_path": "writing"}
        result = route_by_intent(state)
        assert result == "writing"

    def test_route_by_intent_report(self):
        """测试意图路由 - 报告"""
        from src.agents_v2.langgraph_workflow.edges import route_by_intent

        state = {"route_path": "report"}
        result = route_by_intent(state)
        assert result == "report"

    def test_route_by_intent_qa(self):
        """测试意图路由 - 问答"""
        from src.agents_v2.langgraph_workflow.edges import route_by_intent

        state = {"route_path": "qa"}
        result = route_by_intent(state)
        assert result == "qa"

    def test_route_by_intent_revision(self):
        """测试意图路由 - 修改"""
        from src.agents_v2.langgraph_workflow.edges import route_by_intent

        state = {"route_path": "revision"}
        result = route_by_intent(state)
        assert result == "revision"

    def test_route_by_intent_default(self):
        """测试意图路由 - 默认"""
        from src.agents_v2.langgraph_workflow.edges import route_by_intent

        state = {"route_path": "unknown"}
        result = route_by_intent(state)
        assert result == "search"  # 默认路由到搜索


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
