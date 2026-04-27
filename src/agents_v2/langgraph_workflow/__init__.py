"""
LangGraph Workflow - Paper Agent 工作流编排

提供基于 LangGraph 的多智能体论文调研与写作工作流。

使用示例:
    from agents_v2.langgraph_workflow import create_workflow

    workflow = create_workflow(llm=your_llm)
    app = workflow.compile()
    result = workflow.run("deep learning in medical imaging")
"""
from .state import PaperAgentState, Paper, create_initial_state
from .edges import should_continue, route_by_phase
from .workflow import PaperAgentWorkflow, create_workflow
from .nodes.crawler import CrawlerAgent
from .nodes.selector import SelectorAgent
from .nodes.outline import OutlineAgent
from .nodes.writer import WriterAgent
from .nodes.reviewer import ReviewerAgent
from .nodes.memory import MemoryNode, create_memory_node

__all__ = [
    "PaperAgentState",
    "Paper",
    "create_initial_state",
    "should_continue",
    "route_by_phase",
    "PaperAgentWorkflow",
    "create_workflow",
    "CrawlerAgent",
    "SelectorAgent",
    "OutlineAgent",
    "WriterAgent",
    "ReviewerAgent",
    "MemoryNode",
    "create_memory_node",
]
