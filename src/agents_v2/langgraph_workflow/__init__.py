"""
LangGraph Workflow - Paper Agent 工作流编排

提供基于 LangGraph 的多智能体论文调研与写作工作流。

使用示例:
    from agents_v2.langgraph_workflow import create_workflow

    workflow = create_workflow(llm=your_llm)
    app = workflow.compile()
    result = workflow.run("deep learning in medical imaging")
    trace = workflow.get_trace_summary()
"""
from .state import PaperAgentState, Paper, create_initial_state
from .edges import should_continue, route_by_phase, route_by_intent
from .workflow import PaperAgentWorkflow, create_workflow
from .nodes.crawler import CrawlerAgent
from .nodes.selector import SelectorAgent
from .nodes.outline import OutlineAgent
from .nodes.writer import WriterAgent
from .nodes.reviewer import ReviewerAgent
from .nodes.memory import MemoryNode, create_memory_node
from .nodes.multimodal import MultimodalNode, create_multimodal_node
from .nodes.knowledge_graph import KnowledgeGraphNode, create_knowledge_graph_node
from .nodes.evaluator import (
    EvaluatorNode,
    RetrievalMetrics,
    WritingMetrics,
    WorkflowReport,
    create_evaluator_node,
)
from .observability.tracer import (
    WorkflowTracer,
    NodeSpan,
    WorkflowTrace,
    NodeTimingMiddleware,
    create_tracer,
)

__all__ = [
    "PaperAgentState",
    "Paper",
    "create_initial_state",
    "should_continue",
    "route_by_phase",
    "route_by_intent",
    "PaperAgentWorkflow",
    "create_workflow",
    "CrawlerAgent",
    "SelectorAgent",
    "OutlineAgent",
    "WriterAgent",
    "ReviewerAgent",
    "MemoryNode",
    "create_memory_node",
    "MultimodalNode",
    "create_multimodal_node",
    "KnowledgeGraphNode",
    "create_knowledge_graph_node",
    "EvaluatorNode",
    "RetrievalMetrics",
    "WritingMetrics",
    "WorkflowReport",
    "create_evaluator_node",
    "WorkflowTracer",
    "NodeSpan",
    "WorkflowTrace",
    "NodeTimingMiddleware",
    "create_tracer",
]
