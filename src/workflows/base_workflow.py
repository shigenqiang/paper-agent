"""工作流基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
import logging

logger = logging.getLogger(__name__)


class BaseWorkflow(ABC):
    """工作流基类"""

    def __init__(self, name: str):
        self.name = name
        self.workflow = None
        self.graph = None

    @abstractmethod
    def build_workflow(self) -> StateGraph:
        """构建工作流"""
        pass

    def compile(self):
        """编译工作流"""
        if self.workflow is None:
            self.workflow = self.build_workflow()
            self.graph = self.workflow.compile()

        return self.graph

    async def run(self, state: Dict[str, Any], config: Optional[Dict] = None) -> Dict[str, Any]:
        """运行工作流"""
        if self.graph is None:
            self.compile()

        logger.info(f"Running workflow: {self.name}")

        if config is None:
            config = {"configurable": {}}

        result = await self.graph.ainvoke(state, config=config)
        return result

    def get_graph(self):
        """获取工作流图"""
        if self.graph is None:
            self.compile()
        return self.graph

    def visualize(self):
        """可视化工作流"""
        if self.graph is None:
            self.compile()
        self.graph.get_graph().print_ascii()
