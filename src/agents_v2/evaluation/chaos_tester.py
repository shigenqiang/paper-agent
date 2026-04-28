"""
混沌测试器 - Chaos Tester

功能:
1. 故障注入测试
2. 韧性测试
3. 恢复测试
4. 超时处理测试

设计原则:
- 可配置的故障场景
- 安全的故障注入
- 全面的测试报告
"""
import asyncio
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChaosAction(str, Enum):
    """混沌动作"""
    KILL_PROCESS = "kill_process"
    NETWORK_DELAY = "network_delay"
    NETWORK_PARTITION = "network_partition"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_IO_STRESS = "disk_io_stress"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    ERROR_INJECTION = "error_injection"


class ChaosTarget(str, Enum):
    """混沌目标"""
    DATABASE = "database"
    CACHE = "cache"
    API = "api"
    SEARCH = "search"
    MEMORY = "memory"
    NETWORK = "network"


@dataclass
class ChaosScenario:
    """混沌场景"""
    name: str
    action: ChaosAction
    target: ChaosTarget
    duration: float = 10.0
    intensity: float = 1.0  # 0.0 - 1.0
    probability: float = 1.0  # 触发概率
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosResult:
    """混沌测试结果"""
    scenario_name: str
    action: ChaosAction
    target: ChaosTarget
    success: bool
    duration: float
    error: Optional[str] = None
    recovery_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosTestReport:
    """混沌测试报告"""
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    average_recovery_time: float
    results: List[ChaosResult]
    recommendations: List[str]


class ChaosTester:
    """混沌测试器"""

    def __init__(self):
        self._scenarios: Dict[str, ChaosScenario] = {}
        self._active_scenarios: Set[str] = set()
        self._init_default_scenarios()

    def _init_default_scenarios(self):
        """初始化默认场景"""
        # 数据库故障场景
        self.register_scenario(ChaosScenario(
            name="db_connection_failure",
            action=ChaosAction.SERVICE_UNAVAILABLE,
            target=ChaosTarget.DATABASE,
            duration=5.0,
            probability=0.8
        ))

        # 缓存故障场景
        self.register_scenario(ChaosScenario(
            name="cache_miss_storm",
            action=ChaosAction.SERVICE_UNAVAILABLE,
            target=ChaosTarget.CACHE,
            duration=10.0,
            probability=0.9
        ))

        # 网络延迟场景
        self.register_scenario(ChaosScenario(
            name="network_latency",
            action=ChaosAction.NETWORK_DELAY,
            target=ChaosTarget.NETWORK,
            duration=5.0,
            intensity=0.5,
            probability=1.0,
            config={"delay_ms": 1000}
        ))

        # API超时场景
        self.register_scenario(ChaosScenario(
            name="api_timeout",
            action=ChaosAction.TIMEOUT,
            target=ChaosTarget.API,
            duration=3.0,
            probability=0.7
        ))

        # 搜索服务故障场景
        self.register_scenario(ChaosScenario(
            name="search_failure",
            action=ChaosAction.SERVICE_UNAVAILABLE,
            target=ChaosTarget.SEARCH,
            duration=5.0,
            probability=0.8
        ))

    def register_scenario(self, scenario: ChaosScenario):
        """注册混沌场景"""
        self._scenarios[scenario.name] = scenario

    def get_scenario(self, name: str) -> Optional[ChaosScenario]:
        """获取场景"""
        return self._scenarios.get(name)

    def list_scenarios(self) -> List[str]:
        """列出所有场景"""
        return list(self._scenarios.keys())

    async def run_scenario(
        self,
        scenario_name: str,
        target_func: Callable,
        *args,
        **kwargs
    ) -> ChaosResult:
        """运行混沌场景

        Args:
            scenario_name: 场景名称
            target_func: 目标函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            ChaosResult: 测试结果
        """
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            return ChaosResult(
                scenario_name=scenario_name,
                action=ChaosAction.ERROR_INJECTION,
                target=ChaosTarget.API,
                success=False,
                duration=0,
                error=f"Scenario {scenario_name} not found"
            )

        # 检查概率
        if random.random() > scenario.probability:
            logger.info(f"Scenario {scenario_name} skipped due to probability")
            return ChaosResult(
                scenario_name=scenario_name,
                action=scenario.action,
                target=scenario.target,
                success=True,
                duration=0,
                metadata={"skipped": True}
            )

        self._active_scenarios.add(scenario_name)
        start_time = time.time()

        try:
            # 注入故障
            await self._inject_chaos(scenario)

            # 执行目标函数
            result = await target_func(*args, **kwargs)

            # 验证结果
            recovery_time = time.time() - start_time

            return ChaosResult(
                scenario_name=scenario_name,
                action=scenario.action,
                target=scenario.target,
                success=True,
                duration=time.time() - start_time,
                recovery_time=recovery_time,
                metadata={"result": str(result)[:100]}
            )

        except Exception as e:
            error = str(e)
            logger.error(f"Chaos scenario {scenario_name} failed: {error}")

            return ChaosResult(
                scenario_name=scenario_name,
                action=scenario.action,
                target=scenario.target,
                success=False,
                duration=time.time() - start_time,
                error=error
            )

        finally:
            self._active_scenarios.discard(scenario_name)
            # 清理故障注入
            await self._cleanup_chaos(scenario)

    async def _inject_chaos(self, scenario: ChaosScenario):
        """注入故障"""
        logger.info(f"Injecting chaos: {scenario.name} ({scenario.action})")

        if scenario.action == ChaosAction.TIMEOUT:
            # 添加超时
            await asyncio.sleep(scenario.duration)

        elif scenario.action == ChaosAction.NETWORK_DELAY:
            delay = scenario.config.get("delay_ms", 1000) * scenario.intensity
            await asyncio.sleep(delay / 1000)

        elif scenario.action == ChaosAction.ERROR_INJECTION:
            # 延迟后抛出错误
            await asyncio.sleep(0.1)
            raise RuntimeError(f"Injected error for chaos scenario: {scenario.name}")

        elif scenario.action == ChaosAction.SERVICE_UNAVAILABLE:
            # 模拟服务不可用
            await asyncio.sleep(scenario.duration)
            raise ConnectionError(f"Service {scenario.target} is unavailable")

        elif scenario.action == ChaosAction.CPU_STRESS:
            # CPU压力
            duration = scenario.duration
            end_time = time.time() + duration
            while time.time() < end_time:
                _ = sum(range(10000))

        elif scenario.action == ChaosAction.MEMORY_STRESS:
            # 内存压力
            data = []
            for _ in range(int(10000 * scenario.intensity)):
                data.append("x" * 1000)
            await asyncio.sleep(min(scenario.duration, 1))
            del data

    async def _cleanup_chaos(self, scenario: ChaosScenario):
        """清理故障注入"""
        logger.info(f"Cleaning up chaos: {scenario.name}")

    async def run_resilience_test(
        self,
        scenarios: List[str],
        target_func: Callable,
        *args,
        **kwargs
    ) -> ChaosTestReport:
        """运行韧性测试

        Args:
            scenarios: 场景列表
            target_func: 目标函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            ChaosTestReport: 测试报告
        """
        results = []
        recommendations = []

        for scenario_name in scenarios:
            result = await self.run_scenario(scenario_name, target_func, *args, **kwargs)
            results.append(result)

            if not result.success:
                recommendations.append(
                    f"Scenario '{scenario_name}' failed: {result.error}"
                )

        # 计算统计数据
        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed
        recovery_times = [
            r.recovery_time for r in results
            if r.recovery_time is not None
        ]
        avg_recovery = sum(recovery_times) / len(recovery_times) if recovery_times else 0

        # 生成建议
        if failed > len(results) / 2:
            recommendations.insert(
                0, "超过50%的场景失败，系统韧性需要改进"
            )

        if avg_recovery > 5.0:
            recommendations.insert(
                0, f"平均恢复时间较长 ({avg_recovery:.2f}s)，需要优化"
            )

        return ChaosTestReport(
            total_scenarios=len(results),
            passed_scenarios=passed,
            failed_scenarios=failed,
            average_recovery_time=avg_recovery,
            results=results,
            recommendations=recommendations
        )

    def get_active_scenarios(self) -> Set[str]:
        """获取活跃场景"""
        return self._active_scenarios.copy()


class RecoveryTester:
    """恢复测试器"""

    def __init__(self):
        self.recovery_times: List[float] = []

    async def test_recovery(
        self,
        failure_func: Callable,
        recovery_func: Callable,
        num_attempts: int = 5
    ) -> Dict[str, Any]:
        """测试恢复能力

        Args:
            failure_func: 触发故障的函数
            recovery_func: 执行恢复的函数
            num_attempts: 测试次数

        Returns:
            Dict: 测试结果
        """
        recovery_times = []

        for i in range(num_attempts):
            # 触发故障
            await failure_func()

            # 测量恢复时间
            start = time.time()
            await recovery_func()
            recovery_time = time.time() - start
            recovery_times.append(recovery_time)

        return {
            "attempts": num_attempts,
            "average_recovery_time": sum(recovery_times) / len(recovery_times),
            "min_recovery_time": min(recovery_times),
            "max_recovery_time": max(recovery_times),
            "recovery_times": recovery_times
        }


class TimeoutHandler:
    """超时处理器"""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout

    async def with_timeout(
        self,
        func: Callable,
        timeout: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """带超时的执行

        Args:
            func: 目标函数
            timeout: 超时时间
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数结果

        Raises:
            asyncio.TimeoutError: 超时
        """
        timeout = timeout or self.default_timeout

        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Function {func.__name__} timed out after {timeout}s")
            raise


# 便捷函数
async def run_chaos_test(
    scenario_name: str,
    target_func: Callable,
    *args,
    **kwargs
) -> ChaosResult:
    """便捷混沌测试函数"""
    tester = ChaosTester()
    return await tester.run_scenario(scenario_name, target_func, *args, **kwargs)


async def test_system_resilience(
    scenarios: List[str],
    target_func: Callable,
    *args,
    **kwargs
) -> ChaosTestReport:
    """便捷韧性测试函数"""
    tester = ChaosTester()
    return await tester.run_resilience_test(scenarios, target_func, *args, **kwargs)
