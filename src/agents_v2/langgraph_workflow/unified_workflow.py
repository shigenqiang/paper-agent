"""
统一工作流 - Unified Workflow

整合所有工作流路径（搜索/写作/报告/问答/修改）的统一入口。

功能：
1. 路由层：根据意图分发到不同工作流
2. 搜索工作流：crawl → select
3. 写作工作流：crawl → select → outline → write → review
4. 报告工作流：report_crawl → report_analyze → report_gen
5. 问答工作流：qa_search → qa_synthesize → qa_answer
6. 修改工作流：revise → refine → polish

设计原则：
- 统一入口，多路径分发
- 复用现有节点
- 保持状态一致性
"""

from src.agents_v2.logging_config import get_logging_logger

import uuid
from typing import Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import PaperAgentState, create_initial_state
from .edges import should_continue, route_by_intent
from .nodes.router import RouteNode
from .nodes.crawler import CrawlerAgent
from .nodes.selector import SelectorAgent
from .nodes.outline import OutlineAgent
from .nodes.writer import WriterAgent
from .nodes.reviewer import ReviewerAgent
from .nodes.evaluator import EvaluatorNode
from .nodes.memory import MemoryNode
from .nodes.multimodal import MultimodalNode
from .nodes.knowledge_graph import KnowledgeGraphNode
from .nodes.report_crawl import ReportCrawlNode
from .nodes.report_analyze import ReportAnalyzeNode
from .nodes.report_gen import ReportGenNode
from .nodes.qa_search import QASearchNode
from .nodes.qa_synthesize import QASynthesizeNode
from .nodes.qa_answer import QAAnswerNode
from .nodes.revise import ReviseNode
from .nodes.refine import RefineNode
from .nodes.polish import PolishNode
from .observability.tracer import create_tracer
from ..writing.diff_manager import DiffManager

logger = get_logging_logger(__name__)

# HITL 中断点定义：在哪些节点前暂停等待人工审核
HITL_INTERRUPT_POINTS = {
    "after_outline": "outline",        # 大纲生成后、写作前
    "after_review": "review",          # 审查后、评估前
    "after_polish": "polish",          # 润色后（修改工作流终点前）
}


class UnifiedWorkflow:
    """统一工作流 - 整合所有工作流路径"""

    def __init__(
        self,
        llm=None,
        enable_memory: bool = True,
        enable_multimodal: bool = True,
        enable_kg: bool = True,
        enable_evaluation: bool = True,
        enable_hitl: bool = False,
        hitl_interrupt_after: Optional[list] = None,
    ):
        """初始化统一工作流

        Args:
            llm: LLM 提供者
            enable_memory: 是否启用记忆节点
            enable_multimodal: 是否启用多模态节点
            enable_kg: 是否启用知识图谱节点
            enable_evaluation: 是否启用评估节点
            enable_hitl: 是否启用 HITL 人机协作
            hitl_interrupt_after: HITL 中断点列表（节点名），
                默认 ["outline", "review"]。在这些节点执行完毕后暂停等待人工审核。
        """
        self.llm = llm
        self.enable_memory = enable_memory
        self.enable_multimodal = enable_multimodal
        self.enable_kg = enable_kg
        self.enable_evaluation = enable_evaluation
        self.enable_hitl = enable_hitl
        self.hitl_interrupt_after = hitl_interrupt_after or ["outline", "review"]
        self.tracer = create_tracer()

        # HITL checkpointer（内存级，进程重启后失效）
        self._checkpointer = MemorySaver() if enable_hitl else None

        # 初始化所有节点
        self._init_nodes()

        self.app = None

    def _init_nodes(self):
        """初始化所有节点"""
        # 路由节点
        self.router = RouteNode(llm_provider=self.llm)

        # 搜索/写作工作流节点
        self.crawler = CrawlerAgent(llm=self.llm)
        self.selector = SelectorAgent()
        self.outline = OutlineAgent(llm=self.llm)
        self.writer = WriterAgent(llm=self.llm)
        self.reviewer = ReviewerAgent(llm=self.llm)

        # 扩展节点
        if self.enable_memory:
            self.memory = MemoryNode()
        if self.enable_multimodal:
            self.multimodal = MultimodalNode()
        if self.enable_kg:
            self.kg = KnowledgeGraphNode()
        if self.enable_evaluation:
            self.evaluator = EvaluatorNode()

        # 报告工作流节点
        self.report_crawl = ReportCrawlNode()
        self.report_analyze = ReportAnalyzeNode()
        self.report_gen = ReportGenNode(llm_provider=self.llm)

        # 问答工作流节点
        self.qa_search = QASearchNode()
        self.qa_synthesize = QASynthesizeNode()
        self.qa_answer = QAAnswerNode(llm_provider=self.llm)

        # 修改工作流节点
        self.revise = ReviseNode(llm_provider=self.llm)
        self.refine = RefineNode(llm_provider=self.llm)
        self.polish = PolishNode(llm_provider=self.llm)

    def _build_graph(self) -> StateGraph:
        """构建统一工作流图"""
        workflow = StateGraph(dict)

        # 添加路由节点
        workflow.add_node("router", self._router_node)

        # 添加搜索/写作工作流节点
        workflow.add_node("crawler", self._crawler_node)
        workflow.add_node("selector", self._selector_node)
        workflow.add_node("outline", self._outline_node)
        workflow.add_node("writing", self._writer_node)
        workflow.add_node("review", self._reviewer_node)

        # 添加扩展节点
        if self.enable_memory:
            workflow.add_node("memory_recall", self._memory_recall_node)
            workflow.add_node("memory_remember", self._memory_remember_node)
        if self.enable_multimodal:
            workflow.add_node("multimodal", self._multimodal_node)
        if self.enable_kg:
            workflow.add_node("kg", self._kg_node)
        if self.enable_evaluation:
            workflow.add_node("evaluator", self._evaluator_node)

        # 添加报告工作流节点
        workflow.add_node("report_crawl", self._report_crawl_node)
        workflow.add_node("report_analyze", self._report_analyze_node)
        workflow.add_node("report_gen", self._report_gen_node)

        # 添加问答工作流节点
        workflow.add_node("qa_search", self._qa_search_node)
        workflow.add_node("qa_synthesize", self._qa_synthesize_node)
        workflow.add_node("qa_answer", self._qa_answer_node)

        # 添加修改工作流节点
        workflow.add_node("revise", self._revise_node)
        workflow.add_node("refine", self._refine_node)
        workflow.add_node("polish", self._polish_node)

        # 设置入口点
        workflow.set_entry_point("router")

        # 路由分发
        workflow.add_conditional_edges(
            "router",
            route_by_intent,
            {
                "search": "crawler",
                "writing": "memory_recall" if self.enable_memory else "crawler",
                "report": "report_crawl",
                "qa": "qa_search",
                "revision": "revise",
            },
        )

        # 搜索工作流路径
        workflow.add_edge("crawler", "selector")
        workflow.add_edge("selector", END)

        # 写作工作流路径
        if self.enable_memory:
            workflow.add_edge("memory_recall", "crawler")
            workflow.add_edge("selector", "multimodal" if self.enable_multimodal else "outline")
        else:
            workflow.add_edge("selector", "outline")

        if self.enable_multimodal:
            workflow.add_edge("multimodal", "kg" if self.enable_kg else "outline")
        if self.enable_kg:
            workflow.add_edge("kg", "outline")

        workflow.add_edge("outline", "writing")
        workflow.add_edge("writing", "review")

        if self.enable_evaluation:
            workflow.add_edge("review", "evaluator")
            workflow.add_conditional_edges(
                "evaluator",
                should_continue,
                {
                    "write": "writing",
                    "done": "memory_remember" if self.enable_memory else END,
                },
            )
        else:
            workflow.add_conditional_edges(
                "review",
                should_continue,
                {
                    "write": "writing",
                    "done": "memory_remember" if self.enable_memory else END,
                },
            )

        if self.enable_memory:
            workflow.add_edge("memory_remember", END)

        # 报告工作流路径
        workflow.add_edge("report_crawl", "report_analyze")
        workflow.add_edge("report_analyze", "report_gen")
        workflow.add_edge("report_gen", END)

        # 问答工作流路径
        workflow.add_edge("qa_search", "qa_synthesize")
        workflow.add_edge("qa_synthesize", "qa_answer")
        workflow.add_edge("qa_answer", END)

        # 修改工作流路径
        workflow.add_edge("revise", "refine")
        workflow.add_edge("refine", "polish")
        workflow.add_edge("polish", END)

        return workflow

    # 节点包装方法（将 Agent 包装为 LangGraph 兼容的节点）
    async def _router_node(self, state: dict) -> dict:
        return await self.router(state)

    def _crawler_node(self, state: dict) -> dict:
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.crawler.execute(agent_state)
        return dict(result)

    def _selector_node(self, state: dict) -> dict:
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.selector.execute(agent_state)
        return dict(result)

    def _outline_node(self, state: dict) -> dict:
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.outline.execute(agent_state)
        return dict(result)

    def _writer_node(self, state: dict) -> dict:
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.writer.execute(agent_state)
        return dict(result)

    def _reviewer_node(self, state: dict) -> dict:
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.reviewer.execute(agent_state)
        return dict(result)

    def _evaluator_node(self, state: dict) -> dict:
        agent_state = PaperAgentState()
        agent_state.update(state)
        result = self.evaluator.execute(agent_state)
        return dict(result)

    async def _memory_recall_node(self, state: dict) -> dict:
        return await self.memory.recall_before_search(state)

    async def _memory_remember_node(self, state: dict) -> dict:
        return await self.memory.remember_after_selection(state)

    async def _multimodal_node(self, state: dict) -> dict:
        return await self.multimodal.analyze_paper_figures(state)

    async def _kg_node(self, state: dict) -> dict:
        return await self.kg.extract_and_build(state)

    async def _report_crawl_node(self, state: dict) -> dict:
        return await self.report_crawl(state)

    async def _report_analyze_node(self, state: dict) -> dict:
        return await self.report_analyze(state)

    async def _report_gen_node(self, state: dict) -> dict:
        return await self.report_gen(state)

    async def _qa_search_node(self, state: dict) -> dict:
        return await self.qa_search(state)

    async def _qa_synthesize_node(self, state: dict) -> dict:
        return await self.qa_synthesize(state)

    async def _qa_answer_node(self, state: dict) -> dict:
        return await self.qa_answer(state)

    async def _revise_node(self, state: dict) -> dict:
        return await self.revise(state)

    async def _refine_node(self, state: dict) -> dict:
        return await self.refine(state)

    async def _polish_node(self, state: dict) -> dict:
        return await self.polish(state)

    def compile(self):
        """编译工作流

        当 enable_hitl=True 时，会在指定节点后设置 interrupt_after，
        工作流执行到这些节点后会暂停，等待人工审核后恢复。
        需要配合 MemorySaver checkpointer 使用。
        """
        graph = self._build_graph()

        compile_kwargs = {}
        if self.enable_hitl and self._checkpointer:
            compile_kwargs["checkpointer"] = self._checkpointer
            compile_kwargs["interrupt_after"] = self.hitl_interrupt_after
            logger.info(f"HITL 已启用，中断点: {self.hitl_interrupt_after}")

        self.app = graph.compile(**compile_kwargs)
        logger.info("统一工作流编译完成")
        return self.app

    async def run(
        self,
        query: str,
        user_id: str = "",
        session_id: str = "",
        report_type: str = "daily",
        keywords: list = None,
        thread_id: str = "",
    ):
        """运行统一工作流

        Args:
            query: 用户查询
            user_id: 用户 ID
            session_id: 会话 ID
            report_type: 报告类型（daily/weekly/monthly）
            keywords: 关键词列表（用于报告）
            thread_id: LangGraph 线程 ID（用于 HITL checkpoint 恢复）

        Returns:
            dict: {
                "state": 最终状态,
                "thread_id": 线程ID（用于后续 resume）,
                "interrupted": 是否被中断,
                "interrupt_node": 中断节点名（如有）,
            }
        """
        if self.app is None:
            self.compile()

        # 开始追踪
        self.tracer.start_trace(
            query=query,
            user_id=user_id,
            session_id=session_id,
        )

        # 生成或复用 thread_id
        if not thread_id:
            thread_id = str(uuid.uuid4())

        initial_state = {
            "user_query": query,
            "user_id": user_id,
            "session_id": session_id,
            "report_type": report_type,
            "keywords": keywords or [],
            "papers": [],
            "selected_papers": [],
            "outline": {},
            "draft": "",
            "feedback": [],
            "errors": [],
            "hitl_enabled": self.enable_hitl,
            "thread_id": thread_id,
        }

        # 如果明确指定了报告类型或关键词，跳过路由直接走报告路径
        if keywords or report_type != "daily":
            initial_state["route_path"] = "report"

        config = {"configurable": {"thread_id": thread_id}}

        result = await self.app.ainvoke(initial_state, config=config)

        # 检查是否被中断
        interrupted = False
        interrupt_node = ""
        if self.enable_hitl:
            snapshot = self.app.get_state(config)
            if snapshot.next:
                interrupted = True
                interrupt_node = snapshot.next[0] if snapshot.next else ""

        # 结束追踪
        self.tracer.end_trace()

        return {
            "state": result,
            "thread_id": thread_id,
            "interrupted": interrupted,
            "interrupt_node": interrupt_node,
        }

    async def resume(
        self,
        thread_id: str,
        decision: str = "approve",
        feedback: str = "",
    ):
        """从 HITL 中断点恢复工作流

        Args:
            thread_id: 之前 run() 返回的线程 ID
            decision: 人工决策 - "approve"（批准继续）/ "revise"（需要修改）/ "reject"（拒绝）
            feedback: 人工反馈内容（decision=revise 时提供修改意见）

        Returns:
            dict: 同 run() 返回格式，额外包含 diff 信息
        """
        if self.app is None:
            raise RuntimeError("工作流未编译，请先调用 compile()")
        if not self.enable_hitl:
            raise RuntimeError("HITL 未启用，无法使用 resume()")

        config = {"configurable": {"thread_id": thread_id}}

        # 获取当前状态快照
        snapshot = self.app.get_state(config)
        if not snapshot.next:
            return {
                "state": dict(snapshot.values),
                "thread_id": thread_id,
                "interrupted": False,
                "interrupt_node": "",
            }

        # 保存恢复前的 draft/outline，用于后续 diff
        pre_state = dict(snapshot.values)
        pre_draft = pre_state.get("draft", "")
        pre_outline = pre_state.get("outline", {})

        # 将人工决策写入状态
        current_state = dict(pre_state)
        current_state["hitl_decision"] = decision
        current_state["hitl_feedback"] = feedback

        # 恢复执行
        result = await self.app.ainvoke(current_state, config=config)

        # 生成 diff 信息（draft 和 outline 的变更）
        diff_info = {}
        try:
            dm = DiffManager()
            post_draft = result.get("draft", "")
            if pre_draft and post_draft and pre_draft != post_draft:
                diff_info["draft_diff"] = dm.format_for_review(
                    pre_draft, post_draft, stage="resume"
                )
            post_outline = result.get("outline", {})
            if pre_outline and post_outline and pre_outline != post_outline:
                import json
                pre_outline_str = json.dumps(pre_outline, ensure_ascii=False, indent=2)
                post_outline_str = json.dumps(post_outline, ensure_ascii=False, indent=2)
                if pre_outline_str != post_outline_str:
                    diff_info["outline_diff"] = dm.format_for_review(
                        pre_outline_str, post_outline_str, stage="outline"
                    )
        except Exception as e:
            logger.warning(f"Failed to generate diff info: {e}")

        # 检查是否再次中断
        interrupted = False
        interrupt_node = ""
        snapshot_after = self.app.get_state(config)
        if snapshot_after.next:
            interrupted = True
            interrupt_node = snapshot_after.next[0] if snapshot_after.next else ""

        return {
            "state": result,
            "thread_id": thread_id,
            "interrupted": interrupted,
            "interrupt_node": interrupt_node,
            "diff": diff_info,
        }

    def get_interrupt_info(self, thread_id: str) -> dict:
        """获取指定线程的中断状态信息

        Args:
            thread_id: 线程 ID

        Returns:
            dict: {"interrupted": bool, "node": str, "state": dict}
        """
        if not self.enable_hitl or not self._checkpointer:
            return {"interrupted": False, "node": "", "state": {}}

        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.app.get_state(config)

        if snapshot.next:
            return {
                "interrupted": True,
                "node": snapshot.next[0] if snapshot.next else "",
                "state": dict(snapshot.values),
            }
        return {"interrupted": False, "node": "", "state": {}}

    def get_trace_summary(self) -> dict:
        """获取追踪摘要"""
        return self.tracer.get_summary()


def create_unified_workflow(
    llm=None,
    enable_memory: bool = True,
    enable_multimodal: bool = True,
    enable_kg: bool = True,
    enable_evaluation: bool = True,
    enable_hitl: bool = False,
    hitl_interrupt_after: Optional[list] = None,
) -> UnifiedWorkflow:
    """创建统一工作流

    Args:
        llm: LLM 提供者
        enable_memory: 是否启用记忆节点
        enable_multimodal: 是否启用多模态节点
        enable_kg: 是否启用知识图谱节点
        enable_evaluation: 是否启用评估节点
        enable_hitl: 是否启用 HITL 人机协作
        hitl_interrupt_after: HITL 中断点列表

    Returns:
        UnifiedWorkflow 实例
    """
    return UnifiedWorkflow(
        llm=llm,
        enable_memory=enable_memory,
        enable_multimodal=enable_multimodal,
        enable_kg=enable_kg,
        enable_evaluation=enable_evaluation,
        enable_hitl=enable_hitl,
        hitl_interrupt_after=hitl_interrupt_after,
    )
