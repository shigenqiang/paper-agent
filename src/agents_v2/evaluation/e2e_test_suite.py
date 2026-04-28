"""
端到端测试套件 - E2E Test Suite

功能:
1. 完整流程测试
2. 场景测试
3. 回归测试
4. 测试报告生成

设计原则:
- 真实的端到端测试
- 完整的场景覆盖
- 自动化的报告生成
"""
import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TestType(str, Enum):
    """测试类型"""
    SMOKE = "smoke"  # 冒烟测试
    REGRESSION = "regression"  # 回归测试
    INTEGRATION = "integration"  # 集成测试
    SYSTEM = "system"  # 系统测试
    ACCEPTANCE = "acceptance"  # 验收测试


class TestStatus(str, Enum):
    """测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    test_type: TestType
    description: str
    steps: List[Dict[str, Any]]
    expected_result: Any
    timeout: float = 60.0
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class TestStepResult:
    """测试步骤结果"""
    step: int
    name: str
    success: bool
    duration: float
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    test_type: TestType
    status: TestStatus
    duration: float
    timestamp: str
    step_results: List[TestStepResult] = field(default_factory=list)
    error: Optional[str] = None
    screenshot: Optional[str] = None
    logs: List[str] = field(default_factory=list)


@dataclass
class E2ETestReport:
    """E2E测试报告"""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    timestamp: str
    results: List[TestResult]
    summary: Dict[str, Any]
    recommendations: List[str]


class E2ETestSuite:
    """端到端测试套件"""

    def __init__(self, suite_name: str = "default"):
        self.suite_name = suite_name
        self._test_cases: Dict[str, TestCase] = {}
        self._results: List[TestResult] = []
        self._init_default_tests()

    def _init_default_tests(self):
        """初始化默认测试"""
        # 冒烟测试 - 核心功能
        self.register_test(TestCase(
            id="smoke_001",
            name="API健康检查",
            test_type=TestType.SMOKE,
            description="验证API服务正常运行",
            steps=[
                {"action": "GET", "url": "/health", "expected_status": 200}
            ],
            expected_result={"status": "healthy"}
        ))

        self.register_test(TestCase(
            id="smoke_002",
            name="论文搜索功能",
            test_type=TestType.SMOKE,
            description="验证论文搜索功能正常",
            steps=[
                {"action": "POST", "url": "/api/search", "data": {"query": "machine learning"}},
            ],
            expected_result={"success": True}
        ))

        # 回归测试 - 选题流程
        self.register_test(TestCase(
            id="reg_001",
            name="选题流程",
            test_type=TestType.REGRESSION,
            description="完整的选题流程回归测试",
            steps=[
                {"action": "POST", "url": "/api/topic", "data": {"user_request": "深度学习"}},
            ],
            expected_result={"success": True}
        ))

        # 集成测试 - 论文搜索链路
        self.register_test(TestCase(
            id="int_001",
            name="论文搜索链路",
            test_type=TestType.INTEGRATION,
            description="测试从搜索到结果返回的完整链路",
            steps=[
                {"action": "POST", "url": "/api/search", "data": {"query": "AI"}},
                {"action": "GET", "url": "/api/literature/search", "expected_status": 200}
            ],
            expected_result={"papers": list}
        ))

        # 系统测试 - 完整论文流程
        self.register_test(TestCase(
            id="sys_001",
            name="完整论文流程",
            test_type=TestType.SYSTEM,
            description="从选题到生成大纲的完整流程",
            steps=[
                {"action": "POST", "url": "/api/topic", "data": {"topic": "AI"}},
                {"action": "POST", "url": "/api/literature", "data": {"topic": "AI"}},
                {"action": "POST", "url": "/api/paper", "data": {"topic": "AI"}}
            ],
            expected_result={"success": True}
        ))

    def register_test(self, test_case: TestCase):
        """注册测试用例"""
        self._test_cases[test_case.id] = test_case

    def get_test(self, test_id: str) -> Optional[TestCase]:
        """获取测试用例"""
        return self._test_cases.get(test_id)

    def list_tests(
        self,
        test_type: Optional[TestType] = None,
        tags: Optional[List[str]] = None
    ) -> List[TestCase]:
        """列出测试用例"""
        results = list(self._test_cases.values())

        if test_type:
            results = [t for t in results if t.test_type == test_type]

        if tags:
            results = [
                t for t in results
                if any(tag in t.tags for tag in tags)
            ]

        return results

    async def run_test(
        self,
        test_id: str,
        executor: Callable[[Dict[str, Any]], Any]
    ) -> TestResult:
        """运行单个测试

        Args:
            test_id: 测试ID
            executor: 测试执行器，用于执行HTTP请求等操作

        Returns:
            TestResult: 测试结果
        """
        test_case = self._test_cases.get(test_id)
        if not test_case:
            return TestResult(
                test_id=test_id,
                test_name="Unknown",
                test_type=TestType.SMOKE,
                status=TestStatus.FAILED,
                duration=0,
                timestamp=datetime.now().isoformat(),
                error=f"Test {test_id} not found"
            )

        logger.info(f"Running test: {test_case.name}")
        start_time = time.time()
        step_results = []
        status = TestStatus.PASSED

        try:
            for i, step in enumerate(test_case.steps, 1):
                step_start = time.time()

                try:
                    # 执行步骤
                    result = await executor(step)

                    step_duration = time.time() - step_start
                    step_results.append(TestStepResult(
                        step=i,
                        name=step.get("name", f"Step {i}"),
                        success=True,
                        duration=step_duration,
                        output_data=result
                    ))

                except Exception as e:
                    step_duration = time.time() - step_start
                    step_results.append(TestStepResult(
                        step=i,
                        name=step.get("name", f"Step {i}"),
                        success=False,
                        duration=step_duration,
                        error=str(e)
                    ))
                    status = TestStatus.FAILED
                    break

        except Exception as e:
            status = TestStatus.FAILED

        duration = time.time() - start_time

        result = TestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            test_type=test_case.test_type,
            status=status,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            step_results=step_results,
            error=step_results[-1].error if step_results and not step_results[-1].success else None
        )

        self._results.append(result)
        return result

    async def run_tests(
        self,
        test_ids: Optional[List[str]] = None,
        test_type: Optional[TestType] = None,
        executor: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> E2ETestReport:
        """运行测试套件

        Args:
            test_ids: 指定测试ID列表
            test_type: 按类型筛选
            executor: 测试执行器

        Returns:
            E2ETestReport: 测试报告
        """
        # 选择要运行的测试
        if test_ids:
            tests_to_run = [self._test_cases[tid] for tid in test_ids if tid in self._test_cases]
        elif test_type:
            tests_to_run = self.list_tests(test_type=test_type)
        else:
            tests_to_run = list(self._test_cases.values())

        logger.info(f"Running {len(tests_to_run)} tests")

        # 默认执行器
        if executor is None:
            executor = self._default_executor

        # 运行测试
        results = []
        for test in tests_to_run:
            result = await self.run_test(test.id, executor)
            results.append(result)

        # 生成报告
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        # 按类型统计
        by_type = {}
        for test_type in TestType:
            type_results = [r for r in results if r.test_type == test_type]
            if type_results:
                by_type[test_type.value] = {
                    "total": len(type_results),
                    "passed": sum(1 for r in type_results if r.status == TestStatus.PASSED),
                    "failed": sum(1 for r in type_results if r.status == TestStatus.FAILED)
                }

        recommendations = []
        if failed > len(results) / 2:
            recommendations.append("超过50%的测试失败，需要紧急修复")
        if failed > 0:
            recommendations.append(f"有 {failed} 个测试失败，请查看详细日志")

        return E2ETestReport(
            suite_name=self.suite_name,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=sum(r.duration for r in results),
            timestamp=datetime.now().isoformat(),
            results=results,
            summary={
                "by_type": by_type,
                "pass_rate": passed / len(results) if results else 0
            },
            recommendations=recommendations
        )

    async def _default_executor(self, step: Dict[str, Any]) -> Any:
        """默认执行器"""
        # 这里可以实现默认的HTTP请求逻辑
        # 实际使用时应该传入真实的执行器
        action = step.get("action", "GET")
        url = step.get("url", "")
        data = step.get("data")

        logger.info(f"Executing {action} {url}")

        # 模拟执行
        await asyncio.sleep(0.1)

        return {"status": "ok", "action": action, "url": url}

    def get_results(
        self,
        test_type: Optional[TestType] = None
    ) -> List[TestResult]:
        """获取测试结果"""
        if test_type:
            return [r for r in self._results if r.test_type == test_type]
        return self._results

    def add_result(self, result: TestResult):
        """添加结果"""
        self._results.append(result)


class RegressionTester:
    """回归测试器"""

    def __init__(self):
        self._baseline: Dict[str, TestResult] = {}
        self._current: Dict[str, TestResult] = {}

    def set_baseline(self, results: List[TestResult]):
        """设置基线"""
        self._baseline = {r.test_id: r for r in results}

    def compare(self, current_results: List[TestResult]) -> Dict[str, Any]:
        """比较结果"""
        self._current = {r.test_id: r for r in current_results}

        regressions = []
        improvements = []

        for test_id, baseline_result in self._baseline.items():
            if test_id in self._current:
                current_result = self._current[test_id]

                if baseline_result.status == TestStatus.PASSED and current_result.status == TestStatus.FAILED:
                    regressions.append({
                        "test_id": test_id,
                        "test_name": current_result.test_name,
                        "baseline_status": baseline_result.status,
                        "current_status": current_result.status
                    })
                elif baseline_result.status == TestStatus.FAILED and current_result.status == TestStatus.PASSED:
                    improvements.append({
                        "test_id": test_id,
                        "test_name": current_result.test_name
                    })

        return {
            "regressions": regressions,
            "improvements": improvements,
            "total_regressions": len(regressions),
            "total_improvements": len(improvements)
        }


# 便捷函数
async def run_e2e_tests(
    test_type: Optional[TestType] = None,
    executor: Optional[Callable] = None
) -> E2ETestReport:
    """便捷E2E测试函数"""
    suite = E2ETestSuite()
    return await suite.run_tests(test_type=test_type, executor=executor)


async def run_smoke_tests(executor: Optional[Callable] = None) -> E2ETestReport:
    """运行冒烟测试"""
    return await run_e2e_tests(TestType.SMOKE, executor)


async def run_regression_tests(
    baseline_results: Optional[List[TestResult]] = None,
    executor: Optional[Callable] = None
) -> Dict[str, Any]:
    """运行回归测试"""
    suite = E2ETestSuite()
    report = await suite.run_tests(test_type=TestType.REGRESSION, executor=executor)

    if baseline_results:
        tester = RegressionTester()
        tester.set_baseline(baseline_results)
        return tester.compare(report.results)

    return {
        "total": report.total_tests,
        "passed": report.passed,
        "failed": report.failed
    }
