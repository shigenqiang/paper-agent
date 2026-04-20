"""论文调研工作流"""
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from src.workflows.base_workflow import BaseWorkflow
from src.core.state_model import State
from src.agents.search.search_agent import search_node
from src.agents.reading.reading_agent import reading_node
from src.agents.analysis.analysis_agent import analyse_node
from src.agents.writing.writing_agent import writing_node
from src.agents.report.report_agent import report_node
import logging

logger = logging.getLogger(__name__)


class PaperWorkflow(BaseWorkflow):
    """论文调研工作流"""

    def __init__(self):
        super().__init__("paper_workflow")

    def build_workflow(self) -> StateGraph:
        """构建论文调研工作流"""
        builder = StateGraph(State)

        # 添加节点
        builder.add_node("search_node", search_node)
        builder.add_node("reading_node", reading_node)
        builder.add_node("analyse_node", analyse_node)
        builder.add_node("writing_node", writing_node)
        builder.add_node("report_node", report_node)

        # 设置入口点
        builder.add_edge(START, "search_node")

        # 定义工作流路径
        builder.add_edge("search_node", "reading_node")
        builder.add_edge("reading_node", "analyse_node")
        builder.add_edge("analyse_node", "writing_node")
        builder.add_edge("writing_node", "report_node")
        builder.add_edge("report_node", END)

        logger.info("Paper workflow built successfully")
        return builder
