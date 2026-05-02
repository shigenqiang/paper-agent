"""
PhaseSupervisor - 阶段协调器

负责单个阶段内的Agent协调:
1. 并行/串行执行决策
2. Agent结果聚合
3. 阶段质量评估
"""
from typing import Any, Dict, List, Optional, Callable

from src.agents_v2.logging_config import get_logging_logger

import time
import asyncio

from .state_model import PhaseResult, PhaseStatus, QualityScore, QualityLevel, AgentResult, DiagnosticResult, ProblemType
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from .error_handler import FallbackHandler, ErrorContext, ErrorSeverity
from ..problem_oriented.base_problem_agent import AgentOutput as ProblemAgentOutput
from ..paper_agents.base_paper_agent import AgentOutput as PaperAgentOutput
from ..writing.base_writing_agent import WritingOutput

logger = get_logging_logger(__name__)


class PhaseSupervisor:
    """
    PhaseSupervisor - 单阶段协调器

    职责：
    1. 调度阶段内的多个Agent
    2. 聚合Agent结果
    3. 评估阶段质量
    4. 决定是否需要诊断修复

    使用方式:
    supervisor = PhaseSupervisor("writing")
    result = await supervisor.run_agents(agents, input_data)
    """

    def __init__(
        self,
        phase_name: str,
        execution_mode: str = "parallel",  # "parallel" | "sequential" | "adaptive"
        quality_threshold: float = 7.0
    ):
        self.phase_name = phase_name
        self.execution_mode = execution_mode
        self.quality_threshold = quality_threshold

        self.circuit_breaker = CircuitBreaker(name=f"phase_{phase_name}")
        self.fallback_handler = FallbackHandler()

        logger.debug(f"PhaseSupervisor for '{phase_name}' initialized, mode={execution_mode}")

    async def run_agents(
        self,
        agents: List[Callable],
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> PhaseResult:
        """
        运行阶段内的多个Agent

        Args:
            agents: Agent列表，每个是一个可调用的async函数
            input_data: 输入数据
            context: 上下文

        Returns:
            PhaseResult: 阶段结果
        """
        cls_name = self.__class__.__name__
        start_time = time.time()
        agent_results: List[AgentResult] = []
        output: Dict[str, Any] = {}

        logger.debug(f"Phase {self.phase_name} starting with {len(agents)} agents")

        try:
            if self.execution_mode == "parallel":
                agent_results = await self._run_parallel(agents, input_data, context)
            elif self.execution_mode == "sequential":
                agent_results = await self._run_sequential(agents, input_data, context)
            else:  # adaptive
                agent_results = await self._run_adaptive(agents, input_data, context)

            # 聚合输出
            output = self._aggregate_outputs(agent_results)

        except Exception as e:
            logger.error(f"Phase {self.phase_name} failed: {type(e).__name__}: {e}")
            # 使用降级处理
            output = self.fallback_handler.get_fallback(self.phase_name, context or {}, e)

        execution_time = time.time() - start_time

        # 评估质量
        quality_score = self._evaluate_quality(agent_results, output)

        # 诊断问题
        diagnostic = self._diagnose_problems(agent_results, output)

        result = PhaseResult(
            phase_name=self.phase_name,
            status=PhaseStatus.COMPLETED if quality_score.score >= self.quality_threshold else PhaseStatus.FAILED,
            agent_results=agent_results,
            diagnostic=diagnostic,
            output=output,
            quality_score=quality_score,
            execution_time=execution_time
        )

        return result

    async def _run_parallel(
        self,
        agents: List[Callable],
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[AgentResult]:
        """并行运行所有Agent"""
        cls_name = self.__class__.__name__

        tasks = []
        for agent in agents:
            task = self._run_single_agent(agent, input_data, context)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_results = []
        for i, result in enumerate(results):
            agent_name = getattr(agents[i], "__name__", None) or getattr(agents[i], "__class__", type(agents[i])).__name__
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_name} raised exception: {type(result).__name__}: {result}")
                agent_results.append(AgentResult(
                    agent_name=agent_name,
                    success=False,
                    error=str(result)
                ))
            else:
                logger.info(f"Agent {agent_name} completed, success={result.success}, quality={result.quality_score:.2f}")
                agent_results.append(result)

        logger.debug(f"Parallel execution completed, {len(agent_results)} results")
        return agent_results

    async def _run_sequential(
        self,
        agents: List[Callable],
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[AgentResult]:
        """顺序运行所有Agent"""
        agent_results = []
        current_input = input_data

        for agent in agents:
            result = await self._run_single_agent(agent, current_input, context)
            agent_results.append(result)

            # 如果失败且不可跳过，停止
            if not result.success and not self._is_optional(agent):
                logger.warning(f"Required agent {result.agent_name} failed, stopping sequence")
                break

            # 更新输入为前一个Agent的输出
            if result.result:
                current_input = result.result

        return agent_results

    async def _run_adaptive(
        self,
        agents: List[Callable],
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[AgentResult]:
        """
        自适应运行 - 根据结果动态决定

        策略:
        1. 先运行最重要的Agent
        2. 根据结果决定是否需要运行其他Agent
        3. 如果质量已达标，跳过剩余Agent
        """
        agent_results = []
        current_input = input_data

        # 按优先级排序 (假设agents列表已按优先级排序)
        for i, agent in enumerate(agents):
            result = await self._run_single_agent(agent, current_input, context)
            agent_results.append(result)

            # 检查是否已达标
            if result.quality_score >= 8.5:
                logger.info(f"Quality threshold met at agent {i}, skipping remaining")
                break

            # 更新输入
            if result.result:
                current_input = result.result

            # 如果失败且关键，停止
            if not result.success and self._is_critical(agent):
                break

        return agent_results

    async def _run_single_agent(
        self,
        agent: Callable,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> AgentResult:
        """运行单个Agent"""
        # 获取agent名称 - 支持类实例和函数
        agent_name = getattr(agent, "__name__", None) or getattr(agent, "__class__", type(agent)).__name__
        start_time = time.time()

        try:
            # 通过熔断器执行，支持agent对象(有.execute方法)和普通函数
            async def _invoke_agent(*args, **kwargs):
                if hasattr(agent, 'execute'):
                    return await agent.execute(input_data, context)
                else:
                    return await agent(input_data, context)

            result = await self.circuit_breaker.call(_invoke_agent)

            # 处理ProblemAgent返回的AgentOutput
            if isinstance(result, ProblemAgentOutput):
                return AgentResult(
                    agent_name=agent_name,
                    success=result.success,
                    result=result.result,
                    quality_score=result.quality_score,
                    execution_time=time.time() - start_time,
                    error=result.error
                )

            # 处理PaperAgent返回的AgentOutput
            if isinstance(result, PaperAgentOutput):
                return AgentResult(
                    agent_name=agent_name,
                    success=result.success,
                    result=result.result,
                    quality_score=result.quality_score,
                    execution_time=time.time() - start_time,
                    error=result.error
                )

            # 处理WritingOutput (writing模块的agent返回格式)
            if isinstance(result, WritingOutput):
                # 从WritingOutput中提取结果
                output_data = {}
                if result.result:
                    output_data = result.result if isinstance(result.result, dict) else {"text": result.result}
                    # WritingOutput使用polished_text字段，映射到标准格式
                    if "polished_text" in output_data:
                        output_data["text"] = output_data["polished_text"]
                return AgentResult(
                    agent_name=agent_name,
                    success=result.success,
                    result=output_data,
                    quality_score=result.quality_score,
                    execution_time=time.time() - start_time,
                    error=result.error
                )

            if isinstance(result, AgentResult):
                return result

            # 如果返回的是dict，包装为AgentResult
            if isinstance(result, dict):
                return AgentResult(
                    agent_name=agent_name,
                    success=True,
                    result=result,
                    quality_score=result.get("quality_score", 7.0),
                    execution_time=time.time() - start_time
                )

            return AgentResult(
                agent_name=agent_name,
                success=True,
                result={"output": result},
                execution_time=time.time() - start_time
            )

        except CircuitBreakerOpen:
            cls_name = self.__class__.__name__
            logger.warning(f"[{cls_name}:252] Circuit breaker open for {agent_name}")
            return AgentResult(
                agent_name=agent_name,
                success=False,
                error="Circuit breaker open",
                execution_time=time.time() - start_time
            )

        except Exception as e:
            cls_name = self.__class__.__name__
            logger.error(f"[{cls_name}:261] Agent {agent_name} failed: {type(e).__name__}: {e}")

            # 对于polish阶段，如果agent失败，返回原始文本作为降级处理
            if self.phase_name == "polish" and isinstance(input_data, dict):
                original_text = input_data.get("text", "")
                if original_text:
                    logger.warning(f"[{cls_name}:304] Polish agent failed, returning original text as fallback")
                    return AgentResult(
                        agent_name=agent_name,
                        success=False,
                        result={"text": original_text, "polished_text": original_text, "fallback": True},
                        quality_score=0.3,  # 低质量分表示使用了降级处理
                        execution_time=time.time() - start_time,
                        error=str(e)
                    )

            return AgentResult(
                agent_name=agent_name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def _aggregate_outputs(self, agent_results: List[AgentResult]) -> Dict[str, Any]:
        """聚合多个Agent的输出"""
        outputs = [r.result for r in agent_results if r.result]

        if not outputs:
            return {}

        # 简单合并
        aggregated = {}
        for output in outputs:
            if isinstance(output, dict):
                aggregated.update(output)

        return aggregated

    def _evaluate_quality(self, agent_results: List[AgentResult], output: Dict[str, Any]) -> QualityScore:
        """评估阶段质量"""
        if not agent_results:
            return QualityScore(score=0.0, level=QualityLevel.POOR, details="No agent results")

        # 计算平均质量分
        scores = [r.quality_score for r in agent_results if r.quality_score > 0]
        if not scores:
            avg_score = 5.0
        else:
            avg_score = sum(scores) / len(scores)

        # 检查成功率
        success_count = sum(1 for r in agent_results if r.success)
        success_rate = success_count / len(agent_results) if agent_results else 0

        # 综合评分
        final_score = avg_score * success_rate

        # 确定等级
        if final_score >= 9.0:
            level = QualityLevel.EXCELLENT
        elif final_score >= 7.0:
            level = QualityLevel.GOOD
        elif final_score >= 5.0:
            level = QualityLevel.ACCEPTABLE
        else:
            level = QualityLevel.POOR

        details = f"agents:{len(agent_results)}, success:{success_count}, avg_score:{avg_score:.1f}"

        return QualityScore(score=final_score, level=level, details=details)

    def _diagnose_problems(
        self,
        agent_results: List[AgentResult],
        output: Dict[str, Any]
    ) -> Optional[DiagnosticResult]:
        """诊断阶段内的问题"""
        problems = []
        severity: Dict[ProblemType, float] = {}

        for result in agent_results:
            if not result.success:
                # 映射到问题类型
                if "topic" in result.agent_name.lower():
                    problems.append(ProblemType.TOPIC_VAGUE)
                    severity[ProblemType.TOPIC_VAGUE] = 0.8
                elif "literature" in result.agent_name.lower():
                    problems.append(ProblemType.LITERATURE_INSUFFICIENT)
                    severity[ProblemType.LITERATURE_INSUFFICIENT] = 0.7
                elif "argument" in result.agent_name.lower():
                    problems.append(ProblemType.ARGUMENT_WEAK)
                    severity[ProblemType.ARGUMENT_WEAK] = 0.8

            # 检查质量问题
            if result.quality_score < 6.0:
                if "language" in result.agent_name.lower():
                    problems.append(ProblemType.LANGUAGE_POOR)
                    severity[ProblemType.LANGUAGE_POOR] = 0.6
                elif "chart" in result.agent_name.lower():
                    problems.append(ProblemType.CHART_POOR)
                    severity[ProblemType.CHART_POOR] = 0.6

        if not problems:
            return None

        recommendations = []
        for p in problems:
            recommendations.extend(self._get_recommendations_for_problem(p))

        return DiagnosticResult(
            problems_found=problems,
            severity=severity,
            recommendations=recommendations,
            affected_phases=[self.phase_name]
        )

    def _get_recommendations_for_problem(self, problem: ProblemType) -> List[str]:
        """获取问题的推荐解决方案"""
        recommendations_map = {
            ProblemType.TOPIC_VAGUE: ["明确研究范围", "聚焦具体问题"],
            ProblemType.LITERATURE_INSUFFICIENT: ["扩大文献搜索", "补充关键文献"],
            ProblemType.ARGUMENT_WEAK: ["重构论证框架", "补充论据支持"],
            ProblemType.LANGUAGE_POOR: ["语言润色", "语法修正"],
            ProblemType.CHART_POOR: ["图表规范化", "信息呈现优化"]
        }
        return recommendations_map.get(problem, ["请人工检查"])

    def _is_optional(self, agent: Callable) -> bool:
        """判断Agent是否是可选的"""
        optional_agents = ["polish", "format", "grammar"]
        agent_name = getattr(agent, "__name__", "").lower()
        return any(opt in agent_name for opt in optional_agents)

    def _is_critical(self, agent: Callable) -> bool:
        """判断Agent是否是关键的"""
        critical_agents = ["topic", "thesis", "argument", "conclusion"]
        agent_name = getattr(agent, "__name__", "").lower()
        return any(crit in agent_name for crit in critical_agents)