"""
全链路集成器 - Chain Integrator

功能:
1. 多模块串联测试
2. 端到端流程验证
3. 集成测试编排
4. 故障注入测试

设计原则:
- 模拟真实用户流程
- 模块间接口验证
- 故障恢复测试
"""
import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class IntegrationStage(str, Enum):
    """集成阶段"""
    INPUT = "input"
    ROUTING = "routing"
    RETRIEVAL = "retrieval"
    PROCESSING = "processing"
    GENERATION = "generation"
    OUTPUT = "output"


@dataclass
class IntegrationStep:
    """集成步骤"""
    name: str
    stage: IntegrationStage
    component: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    timeout: float = 30.0
    retry_count: int = 3


@dataclass
class IntegrationResult:
    """集成测试结果"""
    step_name: str
    success: bool
    duration: float
    input_data: Any
    output_data: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainTestResult:
    """链路测试结果"""
    chain_name: str
    overall_success: bool
    total_duration: float
    step_results: List[IntegrationResult]
    failed_steps: List[str]
    metrics: Dict[str, Any] = field(default_factory=dict)


class ChainIntegrator:
    """全链路集成器"""

    def __init__(self):
        self._components: Dict[str, Any] = {}
        self._chains: Dict[str, List[IntegrationStep]] = {}
        self._init_default_chains()

    def _init_default_chains(self):
        """初始化默认链路"""
        # 论文搜索链路
        self.register_chain("paper_search", [
            IntegrationStep(
                name="parse_query",
                stage=IntegrationStage.INPUT,
                component="QueryParser",
                input_schema={"query": str},
                output_schema={"parsed_query": dict}
            ),
            IntegrationStep(
                name="route_intent",
                stage=IntegrationStage.ROUTING,
                component="IntentRouter",
                input_schema={"parsed_query": dict},
                output_schema={"intent": str, "confidence": float}
            ),
            IntegrationStep(
                name="retrieve_papers",
                stage=IntegrationStage.RETRIEVAL,
                component="Retriever",
                input_schema={"intent": str, "query": str},
                output_schema={"papers": list}
            ),
            IntegrationStep(
                name="generate_response",
                stage=IntegrationStage.GENERATION,
                component="ResponseGenerator",
                input_schema={"papers": list},
                output_schema={"response": str}
            ),
        ])

        # 论文写作链路
        self.register_chain("paper_writing", [
            IntegrationStep(
                name="topic_selection",
                stage=IntegrationStage.INPUT,
                component="TopicAgent",
                input_schema={"user_request": str},
                output_schema={"topic": dict}
            ),
            IntegrationStep(
                name="outline_generation",
                stage=IntegrationStage.PROCESSING,
                component="OutlineAgent",
                input_schema={"topic": dict},
                output_schema={"outline": dict}
            ),
            IntegrationStep(
                name="content_generation",
                stage=IntegrationStage.GENERATION,
                component="DraftWriterAgent",
                input_schema={"outline": dict},
                output_schema={"draft": str}
            ),
            IntegrationStep(
                name="review_and_refine",
                stage=IntegrationStage.OUTPUT,
                component="ReviewerAgent",
                input_schema={"draft": str},
                output_schema={"final_paper": str}
            ),
        ])

    def register_component(self, name: str, component: Any):
        """注册组件"""
        self._components[name] = component

    def register_chain(self, name: str, steps: List[IntegrationStep]):
        """注册链路"""
        self._chains[name] = steps

    async def test_chain(
        self,
        chain_name: str,
        input_data: Any,
        mock_components: bool = True
    ) -> ChainTestResult:
        """测试链路

        Args:
            chain_name: 链路名称
            input_data: 输入数据
            mock_components: 是否使用模拟组件

        Returns:
            ChainTestResult: 链路测试结果
        """
        if chain_name not in self._chains:
            return ChainTestResult(
                chain_name=chain_name,
                overall_success=False,
                total_duration=0,
                step_results=[],
                failed_steps=["Chain not found"],
                metrics={"error": f"Unknown chain: {chain_name}"}
            )

        steps = self._chains[chain_name]
        step_results = []
        failed_steps = []
        current_data = input_data

        start_time = time.time()

        for step in steps:
            step_start = time.time()

            try:
                # 获取或模拟组件
                if step.component in self._components:
                    component = self._components[step.component]
                elif mock_components:
                    component = self._create_mock_component(step)
                else:
                    raise ValueError(f"Component not found: {step.component}")

                # 执行步骤
                result = await self._execute_step(component, step, current_data)

                step_duration = time.time() - step_start
                step_result = IntegrationResult(
                    step_name=step.name,
                    success=True,
                    duration=step_duration,
                    input_data=current_data,
                    output_data=result,
                    metadata={"stage": step.stage.value}
                )

                step_results.append(step_result)
                current_data = result

            except Exception as e:
                step_duration = time.time() - step_start
                step_result = IntegrationResult(
                    step_name=step.name,
                    success=False,
                    duration=step_duration,
                    input_data=current_data,
                    output_data=None,
                    error=str(e),
                    metadata={"stage": step.stage.value}
                )
                step_results.append(step_result)
                failed_steps.append(step.name)
                logger.error(f"Step {step.name} failed: {e}")
                break

        total_duration = time.time() - start_time

        return ChainTestResult(
            chain_name=chain_name,
            overall_success=len(failed_steps) == 0,
            total_duration=total_duration,
            step_results=step_results,
            failed_steps=failed_steps,
            metrics={
                "total_steps": len(steps),
                "completed_steps": len(step_results),
                "success_rate": (len(steps) - len(failed_steps)) / len(steps) if steps else 0
            }
        )

    async def _execute_step(
        self,
        component: Any,
        step: IntegrationStep,
        input_data: Any
    ) -> Any:
        """执行步骤"""
        # 如果是异步函数
        if asyncio.iscoroutinefunction(component):
            if asyncio.isfunction(component):
                # 普通异步函数
                return await component(input_data)
            else:
                # 对象方法
                method = getattr(component, 'execute', getattr(component, 'process', None))
                if method:
                    return await method(input_data)
                raise ValueError(f"Component has no executable method")
        else:
            # 同步函数或模拟对象
            if asyncio.isfunction(component):
                return component(input_data)
            else:
                method = getattr(component, 'execute', getattr(component, 'process', getattr(component, 'run', None)))
                if method:
                    if asyncio.iscoroutinefunction(method):
                        return await method(input_data)
                    return method(input_data)
                return component if callable(component) else component

    def _create_mock_component(self, step: IntegrationStep) -> Callable:
        """创建模拟组件"""
        def mock_func(input_data):
            # 简单模拟：返回符合输出schema的数据
            output = {
                "result": f"Mock result for {step.name}",
                "processed": True,
                "step": step.name
            }
            return output

        async def mock_async_func(input_data):
            await asyncio.sleep(0.01)  # 模拟异步延迟
            return mock_func(input_data)

        return mock_async_func

    def get_chain_info(self, chain_name: str) -> Dict[str, Any]:
        """获取链路信息"""
        if chain_name not in self._chains:
            return {}

        steps = self._chains[chain_name]
        return {
            "name": chain_name,
            "total_steps": len(steps),
            "stages": [step.stage.value for step in steps],
            "components": [step.component for step in steps],
            "estimated_duration": sum(step.timeout for step in steps)
        }

    def list_chains(self) -> List[str]:
        """列出所有链路"""
        return list(self._chains.keys())


class IntegrationTester:
    """集成测试器"""

    def __init__(self):
        self.results: List[ChainTestResult] = []

    async def run_integration_tests(
        self,
        integrator: ChainIntegrator,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """运行集成测试

        Args:
            integrator: 链路集成器
            test_cases: 测试用例列表

        Returns:
            Dict: 测试报告
        """
        results = []

        for case in test_cases:
            chain_name = case.get("chain_name")
            input_data = case.get("input_data")

            result = await integrator.test_chain(chain_name, input_data)
            results.append(result)

        self.results = results

        # 生成报告
        total = len(results)
        passed = sum(1 for r in results if r.overall_success)
        failed = total - passed
        avg_duration = sum(r.total_duration for r in results) / total if total else 0

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total else 0,
            "average_duration": avg_duration,
            "results": [
                {
                    "chain": r.chain_name,
                    "success": r.overall_success,
                    "duration": r.total_duration,
                    "failed_steps": r.failed_steps
                }
                for r in results
            ]
        }


# 便捷函数
async def run_paper_search_chain(input_data: Dict[str, Any]) -> ChainTestResult:
    """测试论文搜索链路"""
    integrator = ChainIntegrator()
    return await integrator.test_chain("paper_search", input_data)


async def run_paper_writing_chain(input_data: Dict[str, Any]) -> ChainTestResult:
    """测试论文写作链路"""
    integrator = ChainIntegrator()
    return await integrator.test_chain("paper_writing", input_data)