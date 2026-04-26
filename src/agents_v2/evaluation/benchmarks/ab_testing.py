"""
A/B测试框架 - Agent策略对比与统计检验

功能:
- 策略对比（不同Agent配置）
- 统计显著性检验
- 在线/离线评估
"""
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
import random
import math

logger = logging.getLogger(__name__)


class TestTypeEnum(Enum):
    """测试类型"""
    OFFLINE = "offline"  # 离线测试
    ONLINE = "online"     # 在线测试
    SIMULATION = "simulation"  # 模拟测试


@dataclass
class AgentConfig:
    """Agent配置"""
    config_id: str
    name: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    memory_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestTask:
    """测试任务"""
    task_id: str
    description: str
    expected_output: Any = None
    difficulty: str = "medium"  # easy/medium/hard
    category: str = "general"
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    config_id: str
    success: bool
    output: Any
    latency: float
    error: str = ""
    timestamp: float = field(default_factory=time.time)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """A/B测试结果"""
    experiment_id: str
    control_config: AgentConfig
    treatment_config: AgentConfig
    control_results: List[TaskResult]
    treatment_results: List[TaskResult]
    control_mean: float
    treatment_mean: float
    improvement: float  # 相对提升百分比
    absolute_difference: float
    p_value: float
    is_significant: bool
    confidence_level: float
    test_type: TestTypeEnum
    timestamp: float = field(default_factory=time.time)


class ABTestFramework:
    """A/B测试框架"""

    def __init__(self, significance_level: float = 0.05):
        """初始化A/B测试框架

        Args:
            significance_level: 显著性水平 (默认0.05)
        """
        self.significance_level = significance_level
        self.experiments: Dict[str, ABTestResult] = {}

    def create_config(self,
                     name: str,
                     llm_provider: str = "openai",
                     llm_model: str = "gpt-4",
                     **kwargs) -> AgentConfig:
        """创建Agent配置

        Args:
            name: 配置名称
            llm_provider: LLM提供商
            llm_model: LLM模型
            **kwargs: 其他配置参数

        Returns:
            AgentConfig: Agent配置
        """
        return AgentConfig(
            config_id=str(uuid.uuid4())[:8],
            name=name,
            llm_provider=llm_provider,
            llm_model=llm_model,
            **kwargs
        )

    def create_task(self,
                   description: str,
                   expected_output: Any = None,
                   difficulty: str = "medium",
                   **kwargs) -> TestTask:
        """创建测试任务

        Args:
            description: 任务描述
            expected_output: 期望输出
            difficulty: 难度等级
            **kwargs: 其他参数

        Returns:
            TestTask: 测试任务
        """
        return TestTask(
            task_id=str(uuid.uuid4())[:8],
            description=description,
            expected_output=expected_output,
            difficulty=difficulty,
            **kwargs
        )

    async def run_experiment(
        self,
        control_config: AgentConfig,
        treatment_config: AgentConfig,
        test_tasks: List[TestTask],
        agent_factory: Callable[[AgentConfig], Any],
        test_type: TestTypeEnum = TestTypeEnum.SIMULATION,
        parallel: bool = True
    ) -> ABTestResult:
        """运行A/B测试实验

        Args:
            control_config: 对照组配置
            treatment_config: 实验组配置
            test_tasks: 测试任务列表
            agent_factory: Agent工厂函数，接收AgentConfig返回Agent实例
            test_type: 测试类型
            parallel: 是否并行执行

        Returns:
            ABTestResult: 测试结果
        """
        experiment_id = str(uuid.uuid4())[:8]
        logger.info(f"开始A/B测试实验 {experiment_id}")
        logger.info(f"  对照组: {control_config.name}")
        logger.info(f"  实验组: {treatment_config.name}")
        logger.info(f"  任务数: {len(test_tasks)}")

        # 创建Agent实例
        control_agent = agent_factory(control_config)
        treatment_agent = agent_factory(treatment_config)

        # 执行对照组
        logger.info("执行对照组...")
        control_results = await self._run_tasks(
            control_agent, test_tasks, control_config.config_id, parallel
        )

        # 执行实验组
        logger.info("执行实验组...")
        treatment_results = await self._run_tasks(
            treatment_agent, test_tasks, treatment_config.config_id, parallel
        )

        # 计算统计数据
        control_scores = [self._extract_score(r) for r in control_results]
        treatment_scores = [self._extract_score(r) for r in treatment_results]

        control_mean = sum(control_scores) / len(control_scores) if control_scores else 0
        treatment_mean = sum(treatment_scores) / len(treatment_scores) if treatment_scores else 0

        improvement = ((treatment_mean - control_mean) / control_mean * 100) if control_mean != 0 else 0
        absolute_difference = treatment_mean - control_mean

        # 统计检验
        p_value = self._t_test(control_scores, treatment_scores)
        is_significant = p_value < self.significance_level

        # 构建结果
        result = ABTestResult(
            experiment_id=experiment_id,
            control_config=control_config,
            treatment_config=treatment_config,
            control_results=control_results,
            treatment_results=treatment_results,
            control_mean=control_mean,
            treatment_mean=treatment_mean,
            improvement=improvement,
            absolute_difference=absolute_difference,
            p_value=p_value,
            is_significant=is_significant,
            confidence_level=1 - p_value,
            test_type=test_type
        )

        self.experiments[experiment_id] = result

        logger.info(f"实验完成: {'显著' if is_significant else '不显著'} (p={p_value:.4f})")

        return result

    async def _run_tasks(
        self,
        agent,
        tasks: List[TestTask],
        config_id: str,
        parallel: bool
    ) -> List[TaskResult]:
        """执行任务列表

        Args:
            agent: Agent实例
            tasks: 任务列表
            config_id: 配置ID
            parallel: 是否并行

        Returns:
            List[TaskResult]: 结果列表
        """
        if parallel:
            import asyncio
            results = await asyncio.gather(
                *[self._run_single_task(agent, task, config_id) for task in tasks],
                return_exceptions=True
            )
            # 处理异常
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(TaskResult(
                        task_id=tasks[i].task_id,
                        config_id=config_id,
                        success=False,
                        output=None,
                        latency=0,
                        error=str(result)
                    ))
                else:
                    processed_results.append(result)
            return processed_results
        else:
            results = []
            for task in tasks:
                result = await self._run_single_task(agent, task, config_id)
                results.append(result)
            return results

    async def _run_single_task(self, agent, task: TestTask, config_id: str) -> TaskResult:
        """执行单个任务

        Args:
            agent: Agent实例
            task: 测试任务
            config_id: 配置ID

        Returns:
            TaskResult: 任务结果
        """
        start_time = time.time()

        try:
            # 执行任务（带超时）
            output = await self._execute_with_timeout(
                agent, task.description, task.timeout
            )

            # 评估成功与否
            success = self._evaluate_output(output, task.expected_output)

            return TaskResult(
                task_id=task.task_id,
                config_id=config_id,
                success=success,
                output=output,
                latency=time.time() - start_time,
                metrics={"quality_score": self._calculate_quality_score(output)}
            )

        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                config_id=config_id,
                success=False,
                output=None,
                latency=time.time() - start_time,
                error=str(e)
            )

    async def _execute_with_timeout(self, agent, prompt: str, timeout: float) -> Any:
        """带超时的执行"""
        import asyncio

        try:
            if hasattr(agent, 'run'):
                result = await asyncio.wait_for(
                    agent.run(prompt),
                    timeout=timeout
                )
            elif hasattr(agent, 'execute'):
                result = await asyncio.wait_for(
                    agent.execute(prompt),
                    timeout=timeout
                )
            else:
                result = await asyncio.wait_for(
                    agent(prompt),
                    timeout=timeout
                )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"任务执行超时 ({timeout}s)")

    def _evaluate_output(self, output: Any, expected: Any) -> bool:
        """评估输出是否正确"""
        if expected is None:
            return output is not None

        output_str = str(output).lower()
        expected_str = str(expected).lower()

        # 检查关键词重叠
        expected_words = set(expected_str.split())
        output_words = set(output_str.split())

        if not expected_words:
            return True

        overlap = len(expected_words & output_words)
        return overlap >= len(expected_words) * 0.3

    def _extract_score(self, result: TaskResult) -> float:
        """从结果中提取分数"""
        if not result.success:
            return 0.0

        # 从metrics中获取分数
        if result.metrics and "quality_score" in result.metrics:
            return result.metrics["quality_score"]

        # 基于延迟的分数（越快越好）
        max_latency = 30.0
        latency_score = max(0, 1 - result.latency / max_latency)

        return latency_score

    def _calculate_quality_score(self, output: Any) -> float:
        """计算输出质量分数"""
        if output is None:
            return 0.0

        output_str = str(output)

        # 基于输出长度的分数（合理范围）
        length = len(output_str)
        if 100 < length < 5000:
            length_score = 1.0
        elif length <= 100:
            length_score = 0.3
        else:
            length_score = 0.8

        # 基于内容完整性的分数
        completeness_score = 1.0 if len(output_str) > 50 else 0.5

        return (length_score + completeness_score) / 2

    def _t_test(self, control: List[float], treatment: List[float]) -> float:
        """独立样本t检验

        Args:
            control: 对照组分数
            treatment: 实验组分数

        Returns:
            float: p值
        """
        n1, n2 = len(control), len(treatment)
        if n1 < 2 or n2 < 2:
            return 1.0  # 样本太小，无法检验

        mean1, mean2 = sum(control) / n1, sum(treatment) / n2
        var1 = sum((x - mean1) ** 2 for x in control) / (n1 - 1)
        var2 = sum((x - mean2) ** 2 for x in treatment) / (n2 - 1)

        # 合并方差
        pooled_var = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)

        # t统计量
        if pooled_var == 0:
            return 1.0

        se = math.sqrt(pooled_var * (1/n1 + 1/n2))
        if se == 0:
            return 1.0

        t_stat = (mean2 - mean1) / se

        # 简化版p值计算（使用正态近似）
        # 实际应用中应使用t分布表
        p_value = 2 * (1 - self._normal_cdf(abs(t_stat)))

        return max(0.0001, min(1.0, p_value))

    def _normal_cdf(self, x: float) -> float:
        """标准正态分布CDF近似"""
        # 使用erf近似
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def generate_report(self, result: ABTestResult) -> str:
        """生成A/B测试报告

        Args:
            result: 测试结果

        Returns:
            str: 格式化报告
        """
        significance = "✓ 统计显著" if result.is_significant else "✗ 不显著"

        lines = [
            "=" * 60,
            "A/B 测试报告",
            "=" * 60,
            f"\n实验ID: {result.experiment_id}",
            f"测试类型: {result.test_type.value}",
            f"置信度: {result.confidence_level:.1%}",
            f"显著性: {significance} (p={result.p_value:.4f})",
            "\n" + "-" * 40,
            "配置对比:",
            f"  对照组: {result.control_config.name}",
            f"  实验组: {result.treatment_config.name}",
            "\n" + "-" * 40,
            "结果对比:",
            f"  对照组平均分: {result.control_mean:.4f}",
            f"  实验组平均分: {result.treatment_mean:.4f}",
            f"  绝对差异:   {result.absolute_difference:+.4f}",
            f"  相对提升:   {result.improvement:+.2f}%",
            "\n" + "-" * 40,
            "任务统计:",
            f"  对照组成功: {sum(1 for r in result.control_results if r.success)}/{len(result.control_results)}",
            f"  实验组成功: {sum(1 for r in result.treatment_results if r.success)}/{len(result.treatment_results)}",
            "\n" + "-" * 40,
            "结论:",
        ]

        if result.is_significant:
            if result.improvement > 0:
                lines.append(f"  实验组显著优于对照组，提升 {result.improvement:.2f}%")
            else:
                lines.append(f"  实验组显著差于对照组，降低 {abs(result.improvement):.2f}%")
        else:
            lines.append("  两组之间没有统计显著差异")

        lines.append("=" * 60)

        return "\n".join(lines)


# 便捷函数
async def run_ab_test(
    control_config: AgentConfig,
    treatment_config: AgentConfig,
    tasks: List[TestTask],
    agent_factory: Callable[[AgentConfig], Any]
) -> ABTestResult:
    """运行A/B测试的便捷函数

    Args:
        control_config: 对照组配置
        treatment_config: 实验组配置
        tasks: 测试任务
        agent_factory: Agent工厂函数

    Returns:
        ABTestResult: 测试结果
    """
    framework = ABTestFramework()
    result = await framework.run_experiment(
        control_config, treatment_config, tasks, agent_factory
    )
    print(framework.generate_report(result))
    return result
