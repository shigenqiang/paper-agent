"""
LangGraph 工作流构建器

组装所有 Agent 节点，定义边和条件路由，编译为可执行应用。
"""
import logging
from typing import Optional

from langgraph.graph import StateGraph, END

from .state import PaperAgentState
from .edges import should_continue
from .nodes.crawler import CrawlerAgent
from .nodes.selector import SelectorAgent
from .nodes.outline import OutlineAgent
from .nodes.writer import WriterAgent
from .nodes.reviewer import ReviewerAgent

logger = logging.getLogger(__name__)


class PaperAgentWorkflow:
    """Paper Agent LangGraph 工作流"""

    def __init__(
        self,
        llm=None,
        crawler_sources=None,
        selector_top_k: int = 20,
        max_iterations: int = 3,
        enable_enhanced_retrieval: bool = True,
        retriever=None,
    ):
        """
        Args:
            llm: LangChain LLM 实例
            crawler_sources: 爬虫数据源列表
            selector_top_k: 选择器 Top-K
            max_iterations: 最大迭代次数
            enable_enhanced_retrieval: 是否启用增强检索
            retriever: 外部检索器实例
        """
        self.llm = llm
        self.max_iterations = max_iterations

        # 初始化 Agent 节点
        self.crawler = CrawlerAgent(
            sources=crawler_sources,
            enable_enhanced_retrieval=enable_enhanced_retrieval,
            retriever=retriever,
            llm=llm,
        )
        self.selector = SelectorAgent(top_k=selector_top_k)
        self.outline = OutlineAgent(llm=llm)
        self.writer = WriterAgent(llm=llm)
        self.reviewer = ReviewerAgent(llm=llm)

        self.app = None

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        # 使用 Python dict 作为状态（兼容 LangGraph 的 TypedDict 模式）
        workflow = StateGraph(dict)

        # 添加节点
        workflow.add_node("crawler", self._crawler_node)
        workflow.add_node("selector", self._selector_node)
        workflow.add_node("outline", self._outline_node)
        workflow.add_node("writing", self._writer_node)
        workflow.add_node("review", self._reviewer_node)

        # 添加边
        workflow.set_entry_point("crawler")
        workflow.add_edge("crawler", "selector")
        workflow.add_edge("selector", "outline")
        workflow.add_edge("outline", "writing")
        workflow.add_edge("writing", "review")

        # 条件边：审查后决定是否回到写作
        workflow.add_conditional_edges(
            "review",
            should_continue,
            {
                "write": "writing",
                "done": END,
            },
        )

        return workflow

    def _crawler_node(self, state: dict) -> dict:
        """LangGraph 兼容的爬虫节点"""
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.crawler.execute(agent_state)
        return dict(result)

    def _selector_node(self, state: dict) -> dict:
        """LangGraph 兼容的选择器节点"""
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.selector.execute(agent_state)
        return dict(result)

    def _outline_node(self, state: dict) -> dict:
        """LangGraph 兼容的大纲节点"""
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.outline.execute(agent_state)
        return dict(result)

    def _writer_node(self, state: dict) -> dict:
        """LangGraph 兼容的写作节点"""
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.writer.execute(agent_state)
        return dict(result)

    def _reviewer_node(self, state: dict) -> dict:
        """LangGraph 兼容的审查节点"""
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.reviewer.execute(agent_state)
        return dict(result)

    def compile(self):
        """编译工作流"""
        graph = self._build_graph()
        self.app = graph.compile()
        logger.info("LangGraph 工作流编译完成")
        return self.app

    def run(
        self,
        query: str,
        user_id: str = "",
        session_id: str = "",
        max_iterations: int = 3,
        stream: bool = True,
    ):
        """运行工作流

        Args:
            query: 用户查询
            user_id: 用户 ID
            session_id: 会话 ID
            max_iterations: 最大迭代次数
            stream: 是否流式输出

        Returns:
            最终状态
        """
        if self.app is None:
            self.compile()

        import time

        initial_state = {
            "user_query": query,
            "user_id": user_id,
            "session_id": session_id,
            "max_iterations": max_iterations,
            "iteration": 0,
            "current_phase": "crawl",
            "timestamp": time.time(),
            "papers": [],
            "selected_papers": [],
            "outline": {},
            "draft": "",
            "feedback": [],
            "errors": [],
        }

        if stream:
            return self._run_stream(initial_state)
        else:
            return self._run_sync(initial_state)

    def _run_sync(self, initial_state: dict) -> dict:
        """同步运行"""
        result = self.app.invoke(initial_state)
        return result

    def _run_stream(self, initial_state: dict) -> dict:
        """流式运行，打印每个节点的执行信息"""
        final_state = None
        for event in self.app.stream(initial_state):
            for node_name, node_output in event.items():
                phase = node_output.get("current_phase", node_name)
                paper_count = len(node_output.get("papers", []) or node_output.get("selected_papers", []))
                logger.info(f"[Workflow] 节点 {node_name} 完成 -> {phase}")

                if paper_count > 0:
                    logger.info(f"  论文数量: {paper_count}")

            final_state = node_output

        return final_state


def create_workflow(
    llm=None,
    sources=None,
    top_k: int = 20,
    max_iterations: int = 3,
    enable_enhanced_retrieval: bool = True,
    retriever=None,
) -> PaperAgentWorkflow:
    """便捷函数：创建工作流

    Args:
        llm: LangChain LLM
        sources: 爬虫数据源
        top_k: 选择论文数
        max_iterations: 最大写作迭代数
        enable_enhanced_retrieval: 是否启用增强检索
        retriever: 外部检索器实例

    Returns:
        PaperAgentWorkflow 实例
    """
    return PaperAgentWorkflow(
        llm=llm,
        crawler_sources=sources,
        selector_top_k=top_k,
        max_iterations=max_iterations,
        enable_enhanced_retrieval=enable_enhanced_retrieval,
        retriever=retriever,
    )
