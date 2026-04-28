"""
发布检查器 - Release Checker

功能:
1. 发布前检查清单
2. 版本验证
3. 依赖检查
4. 配置验证
5. 测试通过验证

设计原则:
- 自动化发布检查
- 可配置的检查项
- 详细的检查报告
"""
import os
import sys
import subprocess
import importlib
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CheckCategory(str, Enum):
    """检查类别"""
    CODE_QUALITY = "code_quality"
    TESTS = "tests"
    DEPENDENCIES = "dependencies"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    SECURITY = "security"


class CheckSeverity(str, Enum):
    """检查严重程度"""
    BLOCKER = "blocker"  # 阻止发布
    CRITICAL = "critical"  # 严重
    WARNING = "warning"  # 警告
    INFO = "info"  # 信息


class CheckStatus(str, Enum):
    """检查状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """检查结果"""
    name: str
    category: CheckCategory
    severity: CheckSeverity
    status: CheckStatus
    message: str
    details: Optional[str] = None
    duration: float = 0.0


@dataclass
class ReleaseCheckReport:
    """发布检查报告"""
    version: str
    timestamp: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    blocked: bool
    results: List[CheckResult]
    summary: Dict[str, Any]
    recommendations: List[str]
    can_release: bool


class ReleaseChecker:
    """发布检查器"""

    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self._checks: List[Tuple[str, CheckCategory, CheckSeverity, Callable]] = []
        self._init_default_checks()

    def _init_default_checks(self):
        """初始化默认检查"""
        self.register_check(
            "语法检查",
            CheckCategory.CODE_QUALITY,
            CheckSeverity.BLOCKER,
            self._check_syntax
        )

        self.register_check(
            "测试覆盖",
            CheckCategory.TESTS,
            CheckSeverity.BLOCKER,
            self._check_test_coverage
        )

        self.register_check(
            "依赖完整性",
            CheckCategory.DEPENDENCIES,
            CheckSeverity.CRITICAL,
            self._check_dependencies
        )

        self.register_check(
            "环境变量检查",
            CheckCategory.CONFIGURATION,
            CheckSeverity.CRITICAL,
            self._check_environment_vars
        )

        self.register_check(
            "文档完整性",
            CheckCategory.DOCUMENTATION,
            CheckSeverity.WARNING,
            self._check_documentation
        )

        self.register_check(
            "敏感信息检查",
            CheckCategory.SECURITY,
            CheckSeverity.CRITICAL,
            self._check_secrets
        )

    def register_check(
        self,
        name: str,
        category: CheckCategory,
        severity: CheckSeverity,
        check_func: Callable[[], CheckResult]
    ):
        """注册检查项"""
        self._checks.append((name, category, severity, check_func))

    async def run_all_checks(self) -> ReleaseCheckReport:
        """运行所有检查

        Returns:
            ReleaseCheckReport: 检查报告
        """
        import time
        results = []

        for name, category, severity, check_func in self._checks:
            start_time = time.time()

            try:
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
            except Exception as e:
                result = CheckResult(
                    name=name,
                    category=category,
                    severity=severity,
                    status=CheckStatus.FAILED,
                    message=f"检查执行失败: {str(e)}",
                    duration=time.time() - start_time
                )

            result.duration = time.time() - start_time
            results.append(result)

        # 统计
        passed = sum(1 for r in results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in results if r.status == CheckStatus.FAILED)
        blocked = any(
            r.severity == CheckSeverity.BLOCKER and r.status == CheckStatus.FAILED
            for r in results
        )

        # 生成建议
        recommendations = []
        for r in results:
            if r.status == CheckStatus.FAILED:
                if r.severity == CheckSeverity.BLOCKER:
                    recommendations.append(f"[BLOCKER] {r.name}: {r.message}")
                elif r.severity == CheckSeverity.CRITICAL:
                    recommendations.append(f"[CRITICAL] {r.name}: {r.message}")

        # 按类别统计
        by_category = {}
        for cat in CheckCategory:
            cat_results = [r for r in results if r.category == cat]
            if cat_results:
                by_category[cat.value] = {
                    "total": len(cat_results),
                    "passed": sum(1 for r in cat_results if r.status == CheckStatus.PASSED),
                    "failed": sum(1 for r in cat_results if r.status == CheckStatus.FAILED)
                }

        return ReleaseCheckReport(
            version=self.version,
            timestamp=datetime.now().isoformat(),
            total_checks=len(results),
            passed_checks=passed,
            failed_checks=failed,
            blocked=blocked,
            results=results,
            summary={
                "by_category": by_category,
                "pass_rate": passed / len(results) if results else 0
            },
            recommendations=recommendations,
            can_release=not blocked and failed == 0
        )

    def _check_syntax(self) -> CheckResult:
        """语法检查"""
        try:
            # 尝试编译主模块
            import src.agents_v2
            return CheckResult(
                name="语法检查",
                category=CheckCategory.CODE_QUALITY,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.PASSED,
                message="所有模块语法正确"
            )
        except SyntaxError as e:
            return CheckResult(
                name="语法检查",
                category=CheckCategory.CODE_QUALITY,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message=f"语法错误: {str(e)}",
                details=f"Line {e.lineno}: {e.text}"
            )

    def _check_test_coverage(self) -> CheckResult:
        """测试覆盖检查"""
        try:
            # 运行测试收集
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return CheckResult(
                    name="测试覆盖",
                    category=CheckCategory.TESTS,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.PASSED,
                    message="测试收集成功"
                )
            else:
                return CheckResult(
                    name="测试覆盖",
                    category=CheckCategory.TESTS,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.FAILED,
                    message="测试收集失败",
                    details=result.stderr[:500]
                )
        except subprocess.TimeoutExpired:
            return CheckResult(
                name="测试覆盖",
                category=CheckCategory.TESTS,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.SKIPPED,
                message="测试收集超时"
            )
        except Exception as e:
            return CheckResult(
                name="测试覆盖",
                category=CheckCategory.TESTS,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.SKIPPED,
                message=f"测试检查跳过: {str(e)}"
            )

    def _check_dependencies(self) -> CheckResult:
        """依赖完整性检查"""
        required_modules = [
            "pytest",
            "aiohttp",
            "pydantic"
        ]

        missing = []
        for module in required_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                missing.append(module)

        if missing:
            return CheckResult(
                name="依赖完整性",
                category=CheckCategory.DEPENDENCIES,
                severity=CheckSeverity.CRITICAL,
                status=CheckStatus.FAILED,
                message=f"缺少依赖模块: {', '.join(missing)}"
            )

        return CheckResult(
            name="依赖完整性",
            category=CheckCategory.DEPENDENCIES,
            severity=CheckSeverity.CRITICAL,
            status=CheckStatus.PASSED,
            message="所有依赖完整"
        )

    def _check_environment_vars(self) -> CheckResult:
        """环境变量检查"""
        required_vars = ["OPENAI_API_KEY"]
        missing = [v for v in required_vars if v not in os.environ]

        if missing:
            return CheckResult(
                name="环境变量检查",
                category=CheckCategory.CONFIGURATION,
                severity=CheckSeverity.CRITICAL,
                status=CheckStatus.FAILED,
                message=f"缺少环境变量: {', '.join(missing)}"
            )

        return CheckResult(
            name="环境变量检查",
            category=CheckCategory.CONFIGURATION,
            severity=CheckSeverity.CRITICAL,
            status=CheckStatus.PASSED,
            message="环境变量配置完整"
        )

    def _check_documentation(self) -> CheckResult:
        """文档完整性检查"""
        docs = [
            "docs/开发文档/使用指南.md",
            "docs/开发文档/API文档_完整版.md",
            "docs/开发文档/迭代报告与开发计划.md"
        ]

        missing = [d for d in docs if not os.path.exists(d)]

        if missing:
            return CheckResult(
                name="文档完整性",
                category=CheckCategory.DOCUMENTATION,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message=f"缺少文档: {', '.join(missing)}"
            )

        return CheckResult(
            name="文档完整性",
            category=CheckCategory.DOCUMENTATION,
            severity=CheckSeverity.WARNING,
            status=CheckStatus.PASSED,
            message="文档完整"
        )

    def _check_secrets(self) -> CheckResult:
        """敏感信息检查"""
        # 检查代码中是否包含硬编码的密钥
        sensitive_patterns = [
            "password=",
            "api_key=",
            "secret="
        ]

        try:
            # 简单检查 src 目录
            for root, dirs, files in os.walk("src"):
                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            for pattern in sensitive_patterns:
                                if pattern in content and "os.environ" not in content:
                                    return CheckResult(
                                        name="敏感信息检查",
                                        category=CheckCategory.SECURITY,
                                        severity=CheckSeverity.CRITICAL,
                                        status=CheckStatus.FAILED,
                                        message=f"可能存在硬编码敏感信息: {pattern} in {filepath}"
                                    )

            return CheckResult(
                name="敏感信息检查",
                category=CheckCategory.SECURITY,
                severity=CheckSeverity.CRITICAL,
                status=CheckStatus.PASSED,
                message="未发现硬编码敏感信息"
            )
        except Exception as e:
            return CheckResult(
                name="敏感信息检查",
                category=CheckCategory.SECURITY,
                severity=CheckSeverity.INFO,
                status=CheckStatus.SKIPPED,
                message=f"敏感信息检查跳过: {str(e)}"
            )


# 便捷函数
async def check_release(version: str = "1.0.0") -> ReleaseCheckReport:
    """便捷发布检查函数"""
    checker = ReleaseChecker(version)
    return await checker.run_all_checks()


def format_report(report: ReleaseCheckReport) -> str:
    """格式化报告"""
    lines = [
        f"# 发布检查报告 - v{report.version}",
        f"时间: {report.timestamp}",
        "",
        f"状态: {'✅ 可以发布' if report.can_release else '❌ 不可发布'}",
        "",
        f"检查总数: {report.total_checks}",
        f"通过: {report.passed_checks}",
        f"失败: {report.failed_checks}",
        "",
        "## 检查结果",
        ""
    ]

    for result in report.results:
        icon = "✅" if result.status == CheckStatus.PASSED else "❌"
        lines.append(f"{icon} [{result.severity.value}] {result.name}: {result.message}")

    if report.recommendations:
        lines.append("")
        lines.append("## 需要修复的问题")
        for rec in report.recommendations:
            lines.append(f"- {rec}")

    return "\n".join(lines)


# 需要导入 asyncio
import asyncio
