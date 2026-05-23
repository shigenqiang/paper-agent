"""
MasterSupervisor - 全局协调器

核心职责：
1. 管理全局状态 (PaperState)
2. 路由到正确的PhaseSupervisor
3. 处理阶段间的流转
4. 协调诊断-执行-完善流程

设计原则：
1. 问题导向：先诊断，后治疗
2. 质量驱动：不达标则迭代
3. 错误隔离：单阶段失败不影响全局

阶段流程定义:
- diagnostic: 问题诊断 (问题导向Agent并行)
- topic: 选题阶段 (Pipeline Agent)
- literature: 文献阶段 (Pipeline Agent)
- methodology: 方法阶段 (问题导向Agent指导)
- writing: 写作阶段 (Pipeline Agent)
- polish: 润色阶段 (问题导向Agent)
"""
from typing import Any, Dict, List, Optional, Callable, Type

from src.agents_v2.logging_config import get_logging_logger

import time
import asyncio

from .state_model import (
    PaperState, PhaseStatus, QualityLevel, ProblemType,
    PhaseResult as StatePhaseResult, DiagnosticResult, QualityScore, AgentResult
)
from .phase_supervisor import PhaseSupervisor
from .circuit_breaker import MultiCircuitBreaker, CircuitBreakerOpen
from .error_handler import FallbackHandler, ErrorAccumulator, ErrorContext, ErrorSeverity
from .hitl_manager import HITLManager, InterventionType, InterventionPriority

# 导入预定义的阶段模型
from .phase_models import (
    DiagnosticInput,
    TopicInput,
    LiteratureInput,
    MethodologyInput,
    WritingInput,
    PolishInput,
)

logger = get_logging_logger(__name__)


class MasterSupervisor:
    """
    MasterSupervisor - 全局协调器

    工作流程:
    1. 初始化 -> 创建PaperState
    2. 诊断阶段 -> 运行诊断Agent，识别问题
    3. 执行阶段 -> 根据诊断结果路由到对应PhaseSupervisor
    4. 完善阶段 -> 针对问题进行修复
    5. 质量评估 -> 检查是否达标，不达标则迭代

    使用方式:
    supervisor = MasterSupervisor(llm_config)
    result = await supervisor.run("full_paper", {"topic": "..."})
    """

    # 定义阶段流程
    PHASES = ["diagnostic", "topic", "literature", "methodology", "writing", "polish"]

    # 质量阈值 - 统一使用0-1 scale
    QUALITY_THRESHOLDS = {
        "diagnostic": 0.6,  # 诊断阶段
        "topic": 0.7,        # 选题阶段
        "literature": 0.7,   # 文献阶段
        "methodology": 0.7,  # 方法阶段
        "writing": 0.7,      # 写作阶段
        "polish": 0.8         # 最终润色需要更高
    }

    def __init__(self, llm_config: Optional[Any] = None):
        self.llm_config = llm_config
        self.state: Optional[PaperState] = None

        # 组件
        self.multi_circuit_breaker = MultiCircuitBreaker()
        self.fallback_handler = FallbackHandler()
        self.error_accumulator = ErrorAccumulator()

        # PhaseSupervisor映射
        self.phase_supervisors: Dict[str, PhaseSupervisor] = {}
        self._init_phase_supervisors()

        # Agent注册表
        self.agents: Dict[str, Callable] = {}

        # 注册所有Agent
        self.register_problem_agents()
        self.register_pipeline_agents()
        self.register_writing_agents()

        # 配置
        self.max_iterations = 3
        self.enable_diagnostic = True

        # HITL 人机协作管理器（使用全局单例）
        from .hitl_manager import get_hitl_manager
        self.hitl_manager = get_hitl_manager()

        logger.debug("MasterSupervisor initialized")

    def _init_phase_supervisors(self):
        """初始化各阶段的PhaseSupervisor"""
        for phase in self.PHASES:
            threshold = self.QUALITY_THRESHOLDS.get(phase, 7.0)

            # 根据阶段特性选择执行模式
            if phase == "diagnostic":
                mode = "parallel"  # 诊断需要并行
            elif phase in ["topic", "literature"]:
                mode = "sequential"  # 选题和文献需要顺序
            else:
                mode = "adaptive"  # 其他阶段自适应

            self.phase_supervisors[phase] = PhaseSupervisor(
                phase_name=phase,
                execution_mode=mode,
                quality_threshold=threshold
            )

    def register_agent(self, name: str, agent: Callable):
        """注册Agent"""
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")

    def register_problem_agents(self):
        """注册问题导向Agent"""
        # 从problem_oriented模块导入
        try:
            from ..problem_oriented import (
                TopicRefinerAgent,
                LiteratureMapperAgent,
                MethodologyAdvisorAgent
            )

            # 诊断类Agent
            self.agents["topic_refiner"] = TopicRefinerAgent(self.llm_config)
            self.agents["literature_mapper"] = LiteratureMapperAgent(self.llm_config)
            self.agents["methodology_advisor"] = MethodologyAdvisorAgent(self.llm_config)

            logger.debug("Problem-oriented agents registered")
        except ImportError as e:
            logger.warning(f"Could not import problem-oriented agents: {e}")

    def register_pipeline_agents(self):
        """注册Pipeline型Agent"""
        try:
            from ..paper_agents import (
                TopicAgent,
                LiteratureAgent,
                OutlineAgent,
                DraftWriterAgent,
            )

            self.agents["topic"] = TopicAgent(self.llm_config)
            self.agents["literature"] = LiteratureAgent(self.llm_config)
            self.agents["outline"] = OutlineAgent(self.llm_config)
            self.agents["draft"] = DraftWriterAgent(self.llm_config)

            logger.debug("Pipeline agents registered")
        except ImportError as e:
            logger.warning(f"Could not import pipeline agents: {e}")

    def register_writing_agents(self):
        """注册论文写作全流程Agent"""
        try:
            from ..writing import (
                LiteratureReviewAgent,
                OutlineGeneratorAgent,
                DraftGeneratorAgent,
                ReportRefinerAgent,
                ReviewerAgent,
                ProposalGeneratorAgent,
                ReferenceProcessorAgent,
                SmartReviserAgent,
                LanguagePolisherAgent,
            )

            self.agents["literature_review"] = LiteratureReviewAgent(self.llm_config)
            self.agents["outline_generator"] = OutlineGeneratorAgent(self.llm_config)
            self.agents["draft_generator"] = DraftGeneratorAgent(self.llm_config)
            self.agents["report_refiner"] = ReportRefinerAgent(self.llm_config)
            self.agents["proposal_generator"] = ProposalGeneratorAgent(self.llm_config)
            self.agents["reference_processor"] = ReferenceProcessorAgent(self.llm_config)
            self.agents["smart_reviser"] = SmartReviserAgent(self.llm_config)
            self.agents["language_polisher_writing"] = LanguagePolisherAgent(self.llm_config)

            logger.debug("Writing agents registered")
        except ImportError as e:
            logger.warning(f"Could not import writing agents: {e}")

    async def run(
        self,
        task_type: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        运行主流程

        Args:
            task_type: 任务类型 (full_paper, diagnostic_only, etc.)
            input_data: 输入数据

        Returns:
            执行结果
        """
        user_request = input_data.get("user_request", input_data.get("topic", ""))

        # 初始化状态
        self.state = PaperState(user_request=user_request)
        self.state.max_iterations = self.max_iterations

        logger.info(f"Starting task: {task_type}, request: {user_request[:50]}...")

        try:
            if task_type == "full_paper":
                return await self._run_full_paper_flow(input_data)
            elif task_type == "diagnostic_only":
                return await self._run_diagnostic_only(input_data)
            else:
                return await self._run_full_paper_flow(input_data)

        except Exception as e:
            logger.error(f"MasterSupervisor.run failed: {e}")
            self.state.add_error(str(e))
            return {
                "success": False,
                "error": str(e),
                "state": self.state.to_dict()
            }

    async def _run_full_paper_flow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完整论文写作流程

        流程:
        1. 诊断阶段 (问题导向Agent并 行诊断)
        2. 选题阶段 (Pipeline型Agent)
        3. 文献阶段 (Pipeline型Agent)
        4. 方法阶段 (问题导向Agent指导)
        5. 写作阶段 (Pipeline型Agent)
        6. 完善阶段 (问题导向Agent针对性修复)
        """
        phases_to_run = ["diagnostic", "topic", "literature", "methodology", "writing", "polish"]

        import time
        for phase in phases_to_run:
            if phase not in self.phase_supervisors:
                continue

            self.state.current_phase = phase
            phase_start = time.time()
            logger.info(f"Starting phase: {phase}")

            # 获取该阶段的输入
            phase_input = self._prepare_phase_input(phase, input_data)

            # 运行阶段
            supervisor = self.phase_supervisors[phase]
            result = await supervisor.run_agents(
                self._get_phase_agents(phase),
                phase_input,
                self.state.context
            )

            # 更新状态
            self.state.update_phase(phase, result)

            # ===== 选题质量问题 HITL 人工介入 =====
            if phase == "diagnostic" and result.diagnostic:
                topic_problems = [p for p in result.diagnostic.problems_found
                                  if p in (ProblemType.TOPIC_VAGUE, ProblemType.TOPIC_TOO_BROAD,
                                           ProblemType.TOPIC_LACK_NOVELTY)]
                if topic_problems:
                    severity = result.diagnostic.severity
                    logger.info(f"选题质量问题 detected: {[p.value for p in topic_problems]}")
                    intervention = await self.hitl_manager.request_intervention(
                        intervention_type=InterventionType.APPROVAL,
                        agent_id="diagnostic_phase",
                        description=f"选题质量问题需要人工审核: {[p.value for p in topic_problems]}",
                        options=["批准继续", "修改选题方向", "终止流程"],
                        context={
                            "problems": [p.value for p in topic_problems],
                            "severity": {p.value: severity.get(p, 0) for p in topic_problems},
                            "recommendations": result.diagnostic.recommendations
                        },
                        priority=InterventionPriority.HIGH
                    )

                    if not intervention.approved:
                        if intervention.selected_option == "终止流程":
                            logger.warning("人工终止流程")
                            return {
                                "success": False,
                                "reason": "人工终止",
                                "feedback": intervention.feedback,
                                "state": self.state.to_dict()
                            }
                    # 将人工反馈注入上下文，供后续阶段参考
                    self.state.context["topic_feedback"] = intervention.feedback
                    self.state.context["hitl_approved"] = intervention.approved
            # ===== HITL 结束 =====

            # 阶段耗时计算
            phase_elapsed = time.time() - phase_start
            logger.info(f"Phase '{phase}' completed in {phase_elapsed:.2f}s")

            # 质量检查
            threshold = self.QUALITY_THRESHOLDS.get(phase, 7.0)
            if result.quality_score and result.quality_score.score < threshold:
                logger.warning(f"Phase {phase} quality below threshold: score={result.quality_score.score:.2f}, threshold={threshold}")

            # 更新上下文
            if result.output:
                self.state.context.update(result.output)

        return self._compile_final_result()

    async def _run_diagnostic_only(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """只运行诊断阶段"""
        self.state.current_phase = "diagnostic"

        supervisor = self.phase_supervisors["diagnostic"]
        agents = self._get_phase_agents("diagnostic")

        result = await supervisor.run_agents(agents, input_data, self.state.context)
        self.state.update_phase("diagnostic", result)

        return {
            "success": True,
            "diagnostics": result.diagnostic,
            "problems": [p.value for p in result.diagnostic.problems_found] if result.diagnostic else [],
            "recommendations": result.diagnostic.recommendations if result.diagnostic else []
        }

    def _get_phase_agents(self, phase: str) -> List[Callable]:
        """获取指定阶段的Agent列表，过滤掉未注册的None"""
        if phase == "diagnostic":
            agents = [
                self.agents.get("topic_refiner"),
                self.agents.get("literature_mapper"),
                self.agents.get("methodology_advisor")
            ]
        elif phase == "topic":
            agents = [self.agents.get("topic")]
        elif phase == "literature":
            agents = [self.agents.get("literature")]
        elif phase == "methodology":
            agents = [
                self.agents.get("methodology_advisor")
            ]
        elif phase == "writing":
            agents = [
                self.agents.get("outline"),
                self.agents.get("draft")
            ]
        elif phase == "polish":
            # Polish阶段：使用写作型agents执行润色
            writing_agents = [
                self.agents.get("language_polisher_writing"),  # writing模块的LanguagePolisherAgent
                self.agents.get("smart_reviser"),
                self.agents.get("report_refiner")
            ]
            available = [a for a in writing_agents if a is not None]
            if available:
                logger.info(f"Polish phase using agents: {[getattr(a, 'name', str(a)) for a in available]}")
            else:
                logger.warning(f"Polish phase: no writing agents available")
            return available
        elif phase == "literature_review":
            agents = [self.agents.get("literature_review")]
        elif phase == "outline_gen":
            agents = [self.agents.get("outline_generator")]
        elif phase == "draft_gen":
            agents = [self.agents.get("draft_generator")]
        elif phase == "refine":
            agents = [self.agents.get("report_refiner")]
        else:
            agents = []

        # 过滤掉未注册的Agent (None)
        filtered = [a for a in agents if a is not None]
        if len(filtered) < len(agents):
            logger.warning(f"Phase '{phase}': {len(agents) - len(filtered)} agent(s) not registered, skipping")
        return filtered

    def _prepare_phase_input(self, phase: str, original_input: Dict[str, Any]) -> Dict[str, Any]:
        """准备阶段的输入数据，使用 Pydantic 模型进行验证和转换"""
        if phase == "diagnostic":
            # 诊断阶段：使用 DiagnosticInput 模型验证
            validated = DiagnosticInput(
                user_request=original_input.get("user_request", original_input.get("topic", "")),
                user_level=original_input.get("user_level", "硕士"),
                available_time=original_input.get("available_time", "6个月"),
                available_resources=original_input.get("available_resources", "一般")
            )
            return validated.model_dump()
        elif phase == "topic":
            validated = TopicInput(
                user_request=original_input.get("user_request", original_input.get("topic", ""))
            )
            return validated.model_dump()
        elif phase == "literature":
            topic_info = self.state.context.get("topic", {})
            if not topic_info:
                topic_info = original_input.get("user_request", original_input.get("topic", ""))
            if isinstance(topic_info, dict):
                topic_info = topic_info.get("refined_topic", str(topic_info))
            validated = LiteratureInput(topic=topic_info)
            return validated.model_dump()
        elif phase == "methodology":
            topic_info = self.state.context.get("topic", {})
            if not topic_info:
                topic_info = original_input.get("user_request", original_input.get("topic", ""))
            if isinstance(topic_info, dict):
                topic_info = topic_info.get("refined_topic", str(topic_info))
            validated = MethodologyInput(
                topic=topic_info,
                literature_result=self.state.context.get("literature_result", {})
            )
            return validated.model_dump()
        elif phase == "writing":
            topic_info = self.state.context.get("topic", {})
            if not topic_info:
                topic_info = original_input.get("user_request", original_input.get("topic", ""))
            if isinstance(topic_info, dict):
                topic_info = topic_info.get("refined_topic", str(topic_info))
            validated = WritingInput(
                topic=topic_info,
                literature_result=self.state.context.get("literature_result", {}),
                thesis_statement=self.state.context.get("thesis_statement", ""),
                outline=self.state.context.get("outline")
            )
            return validated.model_dump()
        elif phase == "polish":
            writing_output = self.state.context.get("writing_output", {})
            if not writing_output and "writing" in self.state.phase_results:
                writing_output = self.state.phase_results["writing"].output or {}
            draft_text = writing_output.get("full_draft", writing_output.get("report", writing_output.get("draft", "")))
            validated = PolishInput(
                text=draft_text,
                language="zh",
                polish_level="medium"
            )
            return validated.model_dump()
        else:
            return self.state.context

    def _clean_final_paper(self, text: str) -> str:
        """清理论文文本，移除诊断标记、思考过程等干扰信息"""
        import re
        if not text:
            return text

        # 移除【...】格式的诊断标记块
        text = re.sub(r'【[^】]*】', '', text)
        # 移除```json ... ```格式的JSON块
        text = re.sub(r'```json\s*.*?\s*```', '', text, flags=re.DOTALL)
        # 移除独立存在的JSON对象
        text = re.sub(r'\{[^{}]*"[^{}]*":[^{}]*\}', '', text)
        # 移除行内诊断标记 [...]
        text = re.sub(r'\[[A-Z_]+(?:\|[^\]]+)?\]', '', text)
        # 移除思考过程块 (<think>... 和 <think>...</think>)
        text = re.sub(r'<think>[\s\S]*?', '', text)
        text = re.sub(r'<think>[\s\S]*?</think>', '', text)
        # 移除多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _compile_final_result(self) -> Dict[str, Any]:
        """编译最终结果"""
        phases_completed = list(self.state.phase_results.keys())
        quality_history = [
            {"score": q.score, "level": q.level.value, "timestamp": q.timestamp}
            for q in self.state.quality_history
        ]

        # 尝试获取最终论文
        final_paper = ""
        if "polish" in self.state.phase_results:
            output = self.state.phase_results["polish"].output
            if isinstance(output, dict):
                raw_text = output.get("polished_text", output.get("text", ""))
                final_paper = self._clean_final_paper(raw_text)
            elif isinstance(output, str) and output:
                final_paper = self._clean_final_paper(output)

        if not final_paper and "writing" in self.state.phase_results:
            output = self.state.phase_results["writing"].output
            if isinstance(output, dict):
                raw_text = output.get("full_draft", output.get("report", output.get("draft", "")))
                final_paper = self._clean_final_paper(raw_text)
            elif isinstance(output, str) and output:
                final_paper = self._clean_final_paper(output)

        # 检查是否有polish阶段的降级处理
        polish_fallback = False
        if "polish" in self.state.phase_results:
            polish_output = self.state.phase_results["polish"].output
            if isinstance(polish_output, dict) and polish_output.get("fallback"):
                polish_fallback = True
                logger.warning("Polish phase used fallback: returning original text (polish failed)")

        return {
            "success": True,
            "phases_completed": phases_completed,
            "final_paper": final_paper,
            "quality_history": quality_history,
            "final_quality": self.state.quality_history[-1].score if self.state.quality_history else 0.0,
            "quality_level": self.state.get_quality_level().value,
            "iterations": self.state.iteration,
            "polish_fallback": polish_fallback,
        }

    async def _run_custom_flow(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """运行自定义流程"""
        logger.info(f"Running custom flow: {task_type}")
        # 可以扩展以支持自定义流程
        return await self._run_full_paper_flow(input_data)


class RoutingPolicy:
    """路由策略"""

    @staticmethod
    def route_by_problem(state: PaperState) -> List[str]:
        """
        根据问题路由到对应阶段

        Returns:
            需要运行的阶段列表
        """
        phases = []

        # 检查发现的问题
        critical_problems = state.get_critical_problems()

        if ProblemType.LITERATURE_INSUFFICIENT in critical_problems:
            phases.append("literature")

        if ProblemType.ARGUMENT_WEAK in critical_problems or ProblemType.LOGIC_INCOHERENT in critical_problems:
            phases.append("argument")

        if ProblemType.DISCUSSION_SHALLOW in critical_problems:
            phases.append("discussion")

        # 如果没有特定问题，按标准流程
        if not phases:
            phases = ["topic", "literature", "methodology", "writing", "polish"]

        return phases

    @staticmethod
    def should_skip_phase(phase: str, state: PaperState) -> bool:
        """判断是否应该跳过某阶段"""
        # 如果前序阶段失败且当前阶段依赖它，跳过
        dependencies = {
            "literature": ["topic"],
            "methodology": ["topic", "literature"],
            "writing": ["topic", "literature", "methodology"],
            "polish": ["writing"]
        }

        deps = dependencies.get(phase, [])
        for dep in deps:
            if dep in state.phase_results:
                result = state.phase_results[dep]
                if result.status == PhaseStatus.FAILED:
                    return True

        return False