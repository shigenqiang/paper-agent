"""
端到端集成测试 - LangGraph 工作流

测试完整的论文调研工作流：
用户查询 -> 爬取 -> 筛选 -> 大纲 -> 写作 -> 审查 -> (迭代)

使用模拟组件，不依赖外部服务。
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===== 模拟组件 =====

class MockSearchResult:
    def __init__(self, idx, query):
        self.paper_id = f"mock_{idx}"
        self.title = f"{query} - Paper {idx}: Advances and Applications"
        self.authors = [f"Author {idx}A", f"Author {idx}B"]
        self.abstract = f"This paper presents novel methods for {query}. " \
                        f"We propose a comprehensive framework that achieves state-of-the-art results. " \
                        f"Experimental evaluation shows significant improvements over baseline methods."
        self.url = f"https://arxiv.org/abs/2301.{idx:05d}"
        self.year = 2020 + (idx % 5)
        self.venue = ["NeurIPS", "ICML", "ICLR", "AAAI", "CVPR"][idx % 5]
        self.citations = 100 - idx * 5
        self.doi = f"10.1234/{idx}"
        self.raw_data = {}


class MockSearchResponse:
    def __init__(self, query, count=10):
        self.query = query
        self.total = count
        self.results = [MockSearchResult(i, query) for i in range(count)]
        self.source = "mock"
        self.error = ""


class MockSearcher:
    def __init__(self, name="mock"):
        self.name = name
        self.max_results = 10

    async def search(self, query, max_results=10):
        return MockSearchResponse(query, min(max_results, 10))


class MockLLM:
    """模拟 LLM，返回合理的内容"""
    async def ainvoke(self, messages):
        content = messages[-1].content if messages else ""

        if "survey" in content.lower() or "outline" in content.lower():
            return type('Response', (), {
                'content': '''{
                    "title": "A Comprehensive Survey on Test Topic",
                    "sections": [
                        {"title": "Introduction", "description": "Overview of the field", "key_points": ["motivation", "scope"], "references": []},
                        {"title": "Methods", "description": "Key methods", "key_points": ["approach1", "approach2"], "references": []},
                        {"title": "Conclusion", "description": "Summary", "key_points": ["findings"], "references": []}
                    ],
                    "keywords": ["deep learning", "neural networks"]
                }'''
            })()
        elif "write" in content.lower() or "section" in content.lower():
            return type('Response', (), {
                'content': '## Introduction\n\nThis survey provides an overview of recent advances in the field. '
                           'According to [Mock Paper 1, 2023], significant progress has been made. '
                           'However, challenges remain as noted by [Mock Paper 2, 2022].\n\n'
                           'Compared to traditional approaches, modern methods show substantial improvements. '
                           'The limitation of current work includes scalability issues and generalization gaps.'
            })()
        elif "review" in content.lower() or "feedback" in content.lower():
            return type('Response', (), {
                'content': '- The introduction is well-structured\n'
                           '- Add more comparison between methods\n'
                           '- The draft is good and requires no changes'
            })()
        else:
            return type('Response', (), {'content': 'No specific response needed.'})()


# ===== 测试 =====

class TestEndToEndWorkflow:
    """端到端工作流测试"""

    def _patch_search_factory(self):
        """替换 SearchFactory 中的搜索器为模拟版本"""
        from src.agents_v2.search.search_factory import SearchFactory

        SearchFactory._searchers["arxiv"] = MockSearcher("arxiv")
        SearchFactory._searchers["semantic_scholar"] = MockSearcher("semantic_scholar")
        SearchFactory._searchers["pubmed"] = MockSearcher("pubmed")

    def test_full_workflow_no_llm(self):
        """测试完整工作流（无 LLM，使用规则生成）"""
        from src.agents_v2.langgraph_workflow import create_workflow

        self._patch_search_factory()

        workflow = create_workflow(
            llm=None,
            sources=["arxiv"],
            top_k=5,
            max_iterations=1,
        )

        result = workflow.run(
            query="deep learning",
            user_id="test_user",
            session_id="test_session",
            max_iterations=1,
            stream=False,
        )

        # 验证工作流完成
        assert result is not None
        assert "papers" in result
        assert "selected_papers" in result
        assert "outline" in result
        assert "draft" in result

        # 验证各阶段输出
        papers = result["papers"]
        assert isinstance(papers, list)

        selected = result["selected_papers"]
        assert isinstance(selected, list)

        outline = result["outline"]
        assert isinstance(outline, dict)
        assert "title" in outline or "sections" in outline

        draft = result["draft"]
        assert isinstance(draft, str)

        print(f"\n[E2E 结果]")
        print(f"  论文: {len(papers)}")
        print(f"  选中: {len(selected)}")
        print(f"  大纲章节: {len(outline.get('sections', []))}")
        print(f"  草稿长度: {len(draft)}")
        print(f"  迭代次数: {result.get('iteration', 0)}")

    def test_full_workflow_with_llm(self):
        """测试完整工作流（模拟 LLM）"""
        from src.agents_v2.langgraph_workflow import create_workflow

        self._patch_search_factory()
        mock_llm = MockLLM()

        workflow = create_workflow(
            llm=mock_llm,
            sources=["arxiv", "semantic_scholar"],
            top_k=5,
            max_iterations=1,
        )

        result = workflow.run(
            query="transformer architecture in NLP",
            user_id="test_user",
            session_id="test_session",
            max_iterations=1,
            stream=False,
        )

        assert result is not None
        assert "draft" in result
        assert len(result["draft"]) > 0

        # LLM 模式应该生成更详细的大纲
        outline = result["outline"]
        if "sections" in outline:
            assert len(outline["sections"]) > 0

    def test_workflow_with_memory(self):
        """测试工作流 + 记忆系统集成"""
        from src.agents_v2.langgraph_workflow import create_workflow
        from src.agents_v2.langgraph_workflow.nodes.memory import MemoryNode

        self._patch_search_factory()

        # 创建记忆节点
        memory_node = MemoryNode(storage_path=".test_e2e_memory")

        # 准备初始状态
        from src.agents_v2.langgraph_workflow.state import create_initial_state
        state = create_initial_state(
            user_query="machine learning",
            user_id="memory_test_user",
            session_id="memory_test_session",
        )

        # 测试记忆召回
        state = memory_node.recall_before_search(state)
        assert "user_query" in state

        # 运行工作流
        workflow = create_workflow(llm=None, sources=["arxiv"], top_k=3, max_iterations=1)
        result = workflow.run(
            query="machine learning",
            user_id="memory_test_user",
            session_id="memory_test_session",
            max_iterations=1,
            stream=False,
        )

        # 记住检索结果
        from src.agents_v2.langgraph_workflow.state import Paper
        papers_data = result.get("selected_papers", [])
        if papers_data:
            result_state = create_initial_state(
                user_query="machine learning",
                user_id="memory_test_user",
            )
            result_state.selected_papers = papers_data
            result_state = memory_node.remember_after_selection(result_state)
            assert result_state.get("metadata", {}).get("remembered_papers", 0) > 0

    def test_workflow_graph_compilation(self):
        """测试工作流图编译"""
        from src.agents_v2.langgraph_workflow import create_workflow

        workflow = create_workflow(llm=None, sources=[], top_k=5)

        # 编译
        app = workflow.compile()
        assert app is not None

        # 检查图结构
        graph = app.get_graph()
        node_names = [n.name for n in graph.nodes.values() if hasattr(n, 'name')]
        assert "crawler" in node_names
        assert "selector" in node_names
        assert "outline" in node_names
        assert "writing" in node_names
        assert "review" in node_names

    def test_workflow_iteration_control(self):
        """测试迭代控制（审查 -> 重新写作 -> 再审查）"""
        from src.agents_v2.langgraph_workflow.edges import should_continue
        from src.agents_v2.langgraph_workflow.state import create_initial_state

        # 第一次审查后有反馈 -> 继续
        assert should_continue({
            "iteration": 1, "max_iterations": 3,
            "feedback": ["Add more analysis", "Improve citations"],
        }) == "write"

        # 达到最大迭代 -> 停止
        assert should_continue({
            "iteration": 3, "max_iterations": 3,
            "feedback": ["Need improvement"],
        }) == "done"

        # 无反馈 -> 停止
        assert should_continue({
            "iteration": 1, "max_iterations": 3,
            "feedback": [],
        }) == "done"

    def test_state_persistence(self):
        """测试状态持久化"""
        from src.agents_v2.langgraph_workflow.state import (
            PaperAgentState, Paper, create_initial_state
        )

        # 创建复杂状态
        state = create_initial_state(
            user_query="knowledge graph embedding",
            user_id="persist_test",
            session_id="persist_session",
            max_iterations=2,
        )

        # 添加论文
        state.papers = [
            Paper(
                id="p1", title="Paper 1", authors=["A", "B"],
                abstract="Abstract 1", url="http://p1",
                year=2023, citations=50, relevance_score=0.9,
            ),
            Paper(
                id="p2", title="Paper 2", authors=["C"],
                abstract="Abstract 2", url="http://p2",
                year=2022, citations=30, relevance_score=0.7,
            ),
        ]

        # 转换为纯 dict
        state_dict = dict(state)

        # 从 dict 恢复
        restored = PaperAgentState()
        restored.update(state_dict)

        assert restored.user_query == "knowledge graph embedding"
        assert len(restored.papers) == 2
        assert restored.papers[0].title == "Paper 1"


class TestWorkflowPerformance:
    """工作流性能测试"""

    def test_selector_performance(self):
        """测试筛选器处理大量论文的性能"""
        from src.agents_v2.langgraph_workflow.nodes.selector import SelectorAgent
        from src.agents_v2.langgraph_workflow.state import create_initial_state, Paper

        selector = SelectorAgent(top_k=20, enable_reranking=False)

        # 生成 100 篇论文
        papers = []
        for i in range(100):
            papers.append(Paper(
                id=f"p_{i}",
                title=f"Paper about deep learning method {i}",
                authors=["Author"],
                abstract=f"Abstract for paper {i} about neural networks and deep learning",
                url="",
                year=2020 + (i % 5),
                citations=i * 10,
            ))

        state = create_initial_state(user_query="deep learning")
        state.papers = papers

        start = time.time()
        result = selector.execute(state)
        elapsed = time.time() - start

        assert len(result.selected_papers) <= 20
        assert elapsed < 2.0  # 应在 2 秒内完成
        print(f"\n[性能] 筛选 100 篇论文耗时: {elapsed:.3f}s")

    def test_outline_performance(self):
        """测试大纲生成性能"""
        from src.agents_v2.langgraph_workflow.nodes.outline import OutlineAgent
        from src.agents_v2.langgraph_workflow.state import create_initial_state, Paper

        agent = OutlineAgent(llm=None)

        papers = [
            Paper(
                id=f"p_{i}",
                title=f"Survey Paper {i}",
                authors=["Author"],
                abstract=f"About transformer and attention mechanism {i}",
                url="",
                year=2023,
                citations=i * 100,
            )
            for i in range(20)
        ]

        state = create_initial_state(user_query="transformer attention")
        state.selected_papers = papers

        start = time.time()
        result = agent.execute(state)
        elapsed = time.time() - start

        assert "sections" in result.outline
        assert len(result.outline["sections"]) > 0
        assert elapsed < 1.0
        print(f"\n[性能] 20 篇论文大纲生成耗时: {elapsed:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
