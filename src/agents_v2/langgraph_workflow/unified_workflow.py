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
from .edges import should_continue, route_by_intent, diagnostic_quality_gate, is_hitl_interrupted
from .nodes.router import RouteNode
from .nodes.diagnostic import DiagnosticNode, get_diagnostic_node
from .nodes.topic import TopicNode, get_topic_node
from .nodes.literature import LiteratureNode, get_literature_node
from .nodes.methodology import MethodologyNode, get_methodology_node
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
from .nodes.writing import get_writing_node
from .observability.tracer import create_tracer
from ..writing.diff_manager import DiffManager
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
    "after_diagnostic_topic": "diagnostic",  # 诊断发现选题问题后
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
        max_writing_iterations: int = 2,
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
            max_writing_iterations: 最大写作迭代次数，默认2（减少时间）
        """
        self.llm = llm
        self.enable_memory = enable_memory
        self.enable_multimodal = enable_multimodal
        self.enable_kg = enable_kg
        self.enable_evaluation = enable_evaluation
        self.enable_hitl = enable_hitl
        self.hitl_interrupt_after = hitl_interrupt_after or ["outline", "review"]
        self.max_writing_iterations = max_writing_iterations
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

        # 诊断节点
        self.diagnostic = get_diagnostic_node(llm=self.llm)

        # paper 流程节点（diagnostic 后）
        self.topic = get_topic_node(llm=self.llm)
        self.literature = get_literature_node(llm=self.llm)
        self.methodology = get_methodology_node(llm=self.llm)
        self.writing_node = get_writing_node(llm=self.llm)

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

        # 添加诊断节点
        workflow.add_node("diagnostic", self._diagnostic_node)

        # 添加 paper 流程节点（diagnostic 后的 6 个步骤）
        workflow.add_node("topic", self._topic_node)
        workflow.add_node("literature", self._literature_node)
        workflow.add_node("methodology", self._methodology_node)

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
                "writing": "diagnostic",  # 写作流程从诊断开始
                "report": "report_crawl",
                "qa": "qa_search",
                "revision": "revise",
            },
        )

        # 诊断节点后的质量门禁
        workflow.add_conditional_edges(
            "diagnostic",
            diagnostic_quality_gate,
            {
                "topic": "topic",  # 诊断完成，进入选题阶段
                "hitl_intervene": "hitl_intervene",  # 需要人工介入
            },
        )

        # HITL 中断节点（暂停等待人工响应）
        workflow.add_node("hitl_intervene", self._hitl_intervene_node)

        # HITL 恢复后根据决策分流
        workflow.add_conditional_edges(
            "hitl_intervene",
            self._hitl_decision_router,
            {
                "continue": "topic",  # 批准继续，进入选题阶段
                "revise": "diagnostic",  # 需要修改，退回诊断
                "terminate": END,  # 终止流程
            },
        )

        # Paper 流程: topic → literature → methodology → outline → writing → review → polish
        workflow.add_edge("topic", "literature")
        workflow.add_edge("literature", "methodology")
        workflow.add_edge("methodology", "outline")
        workflow.add_edge("outline", "writing")
        workflow.add_edge("writing", "review")

        # 搜索工作流路径
        workflow.add_edge("crawler", "selector")
        workflow.add_edge("selector", END)

        if self.enable_evaluation:
            workflow.add_edge("review", "evaluator")
            workflow.add_conditional_edges(
                "evaluator",
                should_continue,
                {
                    "write": "writing",
                    "done": "polish" if self.enable_memory else "polish",
                },
            )
        else:
            workflow.add_conditional_edges(
                "review",
                should_continue,
                {
                    "write": "writing",
                    "done": "polish" if self.enable_memory else "polish",
                },
            )

        # Polish 节点
        workflow.add_edge("polish", "memory_remember" if self.enable_memory else END)

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
        self.tracer.start_node("crawler")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.crawler.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _selector_node(self, state: dict) -> dict:
        self.tracer.start_node("selector")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.selector.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _outline_node(self, state: dict) -> dict:
        self.tracer.start_node("outline")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.outline.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _writer_node(self, state: dict) -> dict:
        """写作节点入口"""
        self.tracer.start_node("writer")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.writer.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _reviewer_node(self, state: dict) -> dict:
        self.tracer.start_node("reviewer")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.reviewer.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _diagnostic_node(self, state: dict) -> dict:
        """诊断节点入口"""
        self.tracer.start_node("diagnostic")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.diagnostic.execute(agent_state)
            if hasattr(result, 'paper_count'):
                self.tracer.record_paper_count(result.paper_count)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _topic_node(self, state: dict) -> dict:
        """选题节点入口"""
        self.tracer.start_node("topic")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.topic.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _literature_node(self, state: dict) -> dict:
        """文献节点入口"""
        self.tracer.start_node("literature")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.literature.execute(agent_state)
            if hasattr(result, 'paper_count'):
                self.tracer.record_paper_count(result.paper_count)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    def _methodology_node(self, state: dict) -> dict:
        """方法论节点入口"""
        self.tracer.start_node("methodology")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.methodology.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")

    async def _hitl_intervene_node(self, state: dict) -> dict:
        """
        HITL 中断处理节点

        当触发 HITL 中断时，此节点会：
        1. 标记中断状态
        2. 等待外部响应（通过 HITLManager）
        3. 将响应结果注入状态
        """
        from src.agents_v2.unified.hitl_manager import get_hitl_manager

        hitl_manager = get_hitl_manager()

        # 获取诊断问题信息
        diagnostic = state.get("diagnostic_result", {})
        problems = diagnostic.get("problems", [])
        severity = diagnostic.get("severity", {})

        # 请求人工介入
        intervention = await hitl_manager.request_intervention(
            intervention_type="approval",
            agent_id="diagnostic_phase",
            description=f"选题问题需要人工审核: {problems}",
            options=["批准继续", "修改选题方向", "终止流程"],
            context={
                "problems": problems,
                "severity": severity,
                "recommendations": diagnostic.get("recommendations", [])
            },
            priority="high"
        )

        # 将干预结果注入状态
        state["hitl_response"] = {
            "approved": intervention.approved,
            "selected_option": intervention.selected_option,
            "feedback": intervention.feedback,
            "responder": intervention.responder
        }

        # 根据决策设置后续流转标记
        state["hitl_decision"] = intervention.selected_option or ("approve" if intervention.approved else "reject")

        return state

    def _hitl_decision_router(self, state: dict) -> str:
        """
        根据 HITL 决策路由到下一步

        Args:
            state: 包含 hitl_decision 的状态

        Returns:
            "continue" - 批准继续
            "revise" - 需要修改
            "terminate" - 终止
        """
        decision = state.get("hitl_decision", "approve")
        if decision in ("批准继续", "approve", "continue"):
            return "continue"
        elif decision in ("修改选题方向", "revise"):
            return "revise"
        else:
            return "terminate"

    def _evaluator_node(self, state: dict) -> dict:
        self.tracer.start_node("evaluator")
        try:
            agent_state = PaperAgentState()
            agent_state.update(state)
            result = self.evaluator.execute(agent_state)
            return dict(result)
        except Exception as e:
            self.tracer.end_node(status="failed", error=str(e))
            raise
        finally:
            self.tracer.end_node(status="completed")
        return dict(result)

    async def _memory_recall_node(self, state: dict) -> dict:
        import asyncio
        # 在线程池中运行同步的 memory 函数
        return await asyncio.to_thread(self.memory.recall_before_search, state)

    async def _memory_remember_node(self, state: dict) -> dict:
        import asyncio
        # 在线程池中运行同步的 memory 函数
        return await asyncio.to_thread(self.memory.remember_after_selection, state)

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
        route_path: str = "search",  # 工作流路径: search/writing/report/qa/revision
        enable_hitl: bool = None,   # 是否启用 HITL，覆盖默认值
    ):
        """运行统一工作流

        Args:
            query: 用户查询
            user_id: 用户 ID
            session_id: 会话 ID
            report_type: 报告类型（daily/weekly/monthly）
            keywords: 关键词列表（用于报告）
            thread_id: LangGraph 线程 ID（用于 HITL checkpoint 恢复）
            route_path: 工作流路径，默认 search
            enable_hitl: 是否启用 HITL，覆盖实例初始化时的设置

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

        # 启用 HITL 覆盖
        hitl_enabled = enable_hitl if enable_hitl is not None else self.enable_hitl

        initial_state = {
            "user_query": query,
            "user_id": user_id,
            "session_id": session_id,
            "report_type": report_type,
            "keywords": keywords or [],
            "route_path": route_path,  # 设置工作流路径
            "_route_path_set": True,   # 标记 route_path 是外部传入的，router 应尊重
            "papers": [],
            "selected_papers": [],
            "outline": {},
            "draft": "",
            "feedback": [],
            "errors": [],
            "hitl_enabled": hitl_enabled,
            "thread_id": thread_id,
            "iteration": 0,
            "max_iterations": self.max_writing_iterations,
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
