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
"""
from typing import Any, Dict, List, Optional, Callable, Type
import logging
import time
import asyncio

from .state_model import (
    PaperState, PhaseStatus, QualityLevel, ProblemType,
    PhaseResult, DiagnosticResult, QualityScore, AgentResult
)
from .phase_supervisor import PhaseSupervisor
from .circuit_breaker import MultiCircuitBreaker, CircuitBreakerOpen
from .error_handler import FallbackHandler, ErrorAccumulator, ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)


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

    # 质量阈值
    QUALITY_THRESHOLDS = {
        "diagnostic": 6.0,  # 诊断阶段不需要太高
        "topic": 7.0,
        "literature": 7.0,
        "methodology": 7.0,
        "writing": 7.0,
        "polish": 8.0  # 最终润色需要更高
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

        # 配置
        self.max_iterations = 3
        self.enable_diagnostic = True

        logger.info("MasterSupervisor initialized")

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
                MethodologyAdvisorAgent,
                ArgumentBuilderAgent,
                SectionDifferentiatorAgent,
                DiscussionDeepenerAgent,
                ChartFormatterAgent,
                LanguagePolisherAgent,
                PlagiarismCheckerAgent
            )

            # 诊断类Agent
            self.agents["topic_refiner"] = TopicRefinerAgent(self.llm_config)
            self.agents["literature_mapper"] = LiteratureMapperAgent(self.llm_config)
            self.agents["methodology_advisor"] = MethodologyAdvisorAgent(self.llm_config)

            # 写作类Agent
            self.agents["argument_builder"] = ArgumentBuilderAgent(self.llm_config)
            self.agents["section_diff"] = SectionDifferentiatorAgent(self.llm_config)
            self.agents["discussion_deepener"] = DiscussionDeepenerAgent(self.llm_config)

            # 完善类Agent
            self.agents["chart_formatter"] = ChartFormatterAgent(self.llm_config)
            self.agents["language_polisher"] = LanguagePolisherAgent(self.llm_config)
            self.agents["plagiarism_checker"] = PlagiarismCheckerAgent(self.llm_config)

            logger.info("Problem-oriented agents registered")
        except ImportError as e:
            logger.warning(f"Could not import problem-oriented agents: {e}")

    def register_pipeline_agents(self):
        """注册Pipeline型Agent"""
        try:
            from ..paper_agents import (
                TopicAgent,
                LiteratureAgent,
                ThesisAgent,
                OutlineAgent,
                DraftWriterAgent,
                EditorAgent,
                ReviewerAgent
            )

            self.agents["topic"] = TopicAgent(self.llm_config)
            self.agents["literature"] = LiteratureAgent(self.llm_config)
            self.agents["thesis"] = ThesisAgent(self.llm_config)
            self.agents["outline"] = OutlineAgent(self.llm_config)
            self.agents["draft"] = DraftWriterAgent(self.llm_config)
            self.agents["editor"] = EditorAgent(self.llm_config)
            self.agents["reviewer"] = ReviewerAgent(self.llm_config)

            logger.info("Pipeline agents registered")
        except ImportError as e:
            logger.warning(f"Could not import pipeline agents: {e}")

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
            elif task_type == "problem_focused":
                return await self._run_problem_focused(input_data)
            else:
                return await self._run_custom_flow(task_type, input_data)

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

        for phase in phases_to_run:
            if phase not in self.phase_supervisors:
                continue

            self.state.current_phase = phase
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

            # 质量检查
            if result.quality_score and result.quality_score.score < self.QUALITY_THRESHOLDS.get(phase, 7.0):
                logger.warning(f"Phase {phase} quality below threshold: {result.quality_score.score}")

                # 如果有诊断问题，转到完善阶段
                if result.diagnostic and result.diagnostic.problems_found:
                    await self._apply_fixes(result.diagnostic)

            # 更新上下文
            if result.output:
                self.state.context.update(result.output)

            # 检查是否需要迭代
            if self._should_iterate(result, phase):
                await self._iterate_phase(phase, result, input_data)

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

    async def _run_problem_focused(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        问题聚焦流程 - 针对特定问题运行

        输入需要包含:
        - problems: 问题类型列表
        - content: 需要修复的内容
        """
        problems = input_data.get("problems", [])
        content = input_data.get("content", {})

        logger.info(f"Problem-focused flow for: {[p.value if isinstance(p, ProblemType) else p for p in problems]}")

        fixes_applied = []

        for problem in problems:
            fix_result = await self._apply_single_fix(problem, content)
            fixes_applied.append(fix_result)

        return {
            "success": True,
            "fixes_applied": fixes_applied,
            "problem_count": len(problems)
        }

    async def _apply_single_fix(
        self,
        problem: ProblemType,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """对单个问题应用修复"""
        # 映射问题类型到对应的Agent
        problem_agent_map = {
            ProblemType.TOPIC_VAGUE: "topic_refiner",
            ProblemType.TOPIC_TOO_BROAD: "topic_refiner",
            ProblemType.LITERATURE_INSUFFICIENT: "literature_mapper",
            ProblemType.ARGUMENT_WEAK: "argument_builder",
            ProblemType.ABSTRACT_REPEATS_CONCLUSION: "section_diff",
            ProblemType.DISCUSSION_SHALLOW: "discussion_deepener",
            ProblemType.CHART_POOR: "chart_formatter",
            ProblemType.LANGUAGE_POOR: "language_polisher",
            ProblemType.PLAGIARISM_RISK: "plagiarism_checker"
        }

        agent_name = problem_agent_map.get(problem)
        if not agent_name or agent_name not in self.agents:
            return {"success": False, "error": f"No agent for problem {problem.value}"}

        agent = self.agents[agent_name]
        agent_input = self._prepare_agent_input(problem, content)

        try:
            if hasattr(agent, 'execute'):
                result = await agent.execute(agent_input)
            else:
                result = await agent(agent_input)

            return {
                "success": True,
                "problem": problem.value,
                "agent": agent_name,
                "result": result
            }
        except Exception as e:
            logger.error(f"Failed to apply fix for {problem.value}: {e}")
            return {"success": False, "error": str(e), "problem": problem.value}

    async def _apply_fixes(self, diagnostic: DiagnosticResult):
        """根据诊断结果应用修复"""
        logger.info(f"Applying fixes for {len(diagnostic.problems_found)} problems")

        for problem in diagnostic.problems_found:
            severity = diagnostic.severity.get(problem, 0.5)

            # 只修复严重的问题
            if severity >= 0.6:
                await self._apply_single_fix(problem, self.state.context)

    def _get_phase_agents(self, phase: str) -> List[Callable]:
        """获取指定阶段的Agent列表"""
        if phase == "diagnostic":
            return [
                self.agents.get("topic_refiner"),
                self.agents.get("literature_mapper"),
                self.agents.get("methodology_advisor")
            ]
        elif phase == "topic":
            return [self.agents.get("topic")]
        elif phase == "literature":
            return [self.agents.get("literature")]
        elif phase == "methodology":
            return [
                self.agents.get("methodology_advisor"),
                self.agents.get("argument_builder")
            ]
        elif phase == "writing":
            return [
                self.agents.get("thesis"),
                self.agents.get("outline"),
                self.agents.get("draft")
            ]
        elif phase == "polish":
            return [
                self.agents.get("chart_formatter"),
                self.agents.get("language_polisher"),
                self.agents.get("plagiarism_checker")
            ]

        return []

    def _prepare_phase_input(self, phase: str, original_input: Dict[str, Any]) -> Dict[str, Any]:
        """准备阶段的输入数据"""
        if phase == "diagnostic":
            return original_input
        elif phase == "topic":
            return {"user_request": original_input.get("user_request", original_input.get("topic", ""))}
        elif phase == "literature":
            return {"topic": self.state.context.get("topic", {})}
        elif phase == "writing":
            return {
                "topic": self.state.context.get("topic", {}),
                "literature_result": self.state.context.get("literature_result", {}),
                "thesis_statement": self.state.context.get("thesis_statement", "")
            }
        else:
            return self.state.context

    def _prepare_agent_input(self, problem: ProblemType, content: Dict[str, Any]) -> Dict[str, Any]:
        """为特定问题准备Agent输入"""
        # 问题导向Agent接受的输入格式
        return content

    def _should_iterate(self, result: PhaseResult, phase: str) -> bool:
        """判断是否需要迭代"""
        if result.status == PhaseStatus.FAILED:
            return True

        if result.quality_score and result.quality_score.score < self.QUALITY_THRESHOLDS.get(phase, 7.0):
            return self.state.iteration < self.state.max_iterations

        return False

    async def _iterate_phase(self, phase: str, result: PhaseResult, original_input: Dict[str, Any]):
        """迭代阶段执行"""
        logger.info(f"Iterating phase {phase}, iteration {self.state.iteration + 1}")

        self.state.iteration += 1

        supervisor = self.phase_supervisors.get(phase)
        if not supervisor:
            return

        # 使用前一次的输出作为输入
        iteration_input = result.output or self.state.context

        new_result = await supervisor.run_agents(
            self._get_phase_agents(phase),
            iteration_input,
            self.state.context
        )

        self.state.update_phase(f"{phase}_iter_{self.state.iteration}", new_result)

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
            final_paper = self.state.phase_results["polish"].output or {}
            final_paper = final_paper.get("polished_text", final_paper.get("text", ""))

        if not final_paper and "writing" in self.state.phase_results:
            final_paper = self.state.phase_results["writing"].output or {}
            final_paper = final_paper.get("report", final_paper.get("draft", ""))

        return {
            "success": True,
            "phases_completed": phases_completed,
            "final_paper": final_paper,
            "quality_history": quality_history,
            "final_quality": self.state.quality_history[-1].score if self.state.quality_history else 0.0,
            "quality_level": self.state.get_quality_level().value,
            "problems_identified": [p.value for p in self.state.problems],
            "iterations": self.state.iteration,
            "state": self.state.to_dict()
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