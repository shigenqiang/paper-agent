"""
监控与自动改进系统 - Monitoring & Auto-Improvement System

这是一个持续运行的监控服务，提供：
- 性能监控与瓶颈检测
- 代码质量分析
- 自动问题诊断
- 自我修复建议

使用方法:
    python -m src.agents_v2.monitoring.auto_improver

    # 或在代码中
    from src.agents_v2.monitoring.auto_improver import AutoImprover
    improver = AutoImprover()
    await improver.start()
"""
import asyncio
import sys
import os
import time
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# 禁用日志
os.environ["LOG_LEVEL"] = "ERROR"

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class IssueSeverity(str, Enum):
    """问题严重性"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    """问题类别"""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    ERROR = "error"
    SECURITY = "security"
    RELIABILITY = "reliability"


@dataclass
class Issue:
    """问题"""
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    location: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    auto_fixable: bool = False
    fix_suggestion: Optional[str] = None


@dataclass
class ImprovementAction:
    """改进动作"""
    action_type: str
    description: str
    priority: int
    estimated_impact: str
    implemented: bool = False
    success: bool = False
    result: Optional[str] = None


class AutoImprover:
    """监控与自动改进系统

    功能特性：
    - 持续性能监控
    - 问题自动检测与分类
    - 自动修复建议
    - 自我改进学习
    - 定期报告生成
    """

    def __init__(
        self,
        check_interval: float = 60.0,
        auto_diagnose: bool = True,
        enable_auto_fix: bool = False,
        project_root: Optional[str] = None,
    ):
        """
        初始化自动改进器

        Args:
            check_interval: 检查间隔（秒）
            auto_diagnose: 自动诊断问题
            enable_auto_fix: 启用自动修复（谨慎！）
            project_root: 项目根目录
        """
        self.check_interval = check_interval
        self.auto_diagnose = auto_diagnose
        self.enable_auto_fix = enable_auto_fix
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent.parent

        self._running = False

        # 问题和改进
        self.issues: List[Issue] = []
        self.improvement_history: List[ImprovementAction] = []
        self.fixed_issues: List[str] = []

        # 性能指标
        self.performance_metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "response_times": [],
            "error_counts": [],
        }

        # 监控配置
        self.monitored_paths = [
            "src/agents_v2/paper_agents",
            "src/agents_v2/academic_qa",
            "src/agents_v2/memory",
            "src/agents_v2/knowledge_graph",
            "src/agents_v2/writing",
        ]

        # 基准
        self.benchmarks = {
            "response_time_p95": 5000,  # ms
            "error_rate": 0.05,  # 5%
            "cpu_usage": 0.8,  # 80%
            "memory_usage": 0.85,  # 85%
        }

        # 回调函数
        self.issue_callbacks: List[Callable[[Issue], None]] = []

    async def start(self):
        """启动监控循环"""
        await self.initialize()
        self._running = True

        print("\n" + "="*60)
        print("监控与自动改进系统启动")
        print("="*60)
        print(f"检查间隔: {self.check_interval}秒")
        print(f"自动诊断: {'启用' if self.auto_diagnose else '禁用'}")
        print(f"自动修复: {'启用' if self.enable_auto_fix else '禁用'}")
        print(f"监控路径: {', '.join(self.monitored_paths)}")
        print("="*60)

        while self._running:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\n\n正在停止监控...")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                continue

        await self.shutdown()

    async def initialize(self):
        """初始化监控系统"""
        # 创建输出目录
        output_dir = self.project_root / "output"
        output_dir.mkdir(exist_ok=True)

        logger.info("AutoImprover initialized")
        return self

    async def _monitoring_cycle(self):
        """监控周期"""
        cycle_start = time.time()

        # 1. 收集性能指标
        await self._collect_metrics()

        # 2. 检测问题
        if self.auto_diagnose:
            await self._detect_issues()

        # 3. 生成改进建议
        improvements = await self._generate_improvements()

        # 4. 执行自动修复（如果启用）
        if self.enable_auto_fix and improvements:
            await self._apply_fixes(improvements)

        # 5. 生成报告
        await self._generate_report()

        cycle_time = time.time() - cycle_start

        # 打印状态
        if len(self.issues) > 0:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                  f"发现 {len(self.issues)} 个问题, "
                  f"周期耗时 {cycle_time:.2f}s")

    async def _collect_metrics(self):
        """收集性能指标"""
        import psutil

        try:
            # CPU 使用率
            cpu = psutil.cpu_percent(interval=0.1)
            self.performance_metrics["cpu_usage"].append(cpu)

            # 内存使用率
            memory = psutil.virtual_memory().percent / 100
            self.performance_metrics["memory_usage"].append(memory)

            # 保持最近100条记录
            for key in self.performance_metrics:
                if len(self.performance_metrics[key]) > 100:
                    self.performance_metrics[key] = self.performance_metrics[key][-100:]

        except ImportError:
            pass

    async def _detect_issues(self):
        """检测问题"""
        new_issues = []

        # 1. 性能问题检测
        for key in ["cpu_usage", "memory_usage"]:
            if self.performance_metrics[key]:
                latest = self.performance_metrics[key][-1]
                threshold = self.benchmarks.get(key.replace("_usage", "_usage"))
                if threshold and latest > threshold:
                    new_issues.append(Issue(
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.HIGH if latest > threshold * 1.2 else IssueSeverity.MEDIUM,
                        title=f"高{key.replace('_usage', '')}使用",
                        description=f"{key.replace('_', ' ').title()}达到 {latest:.1%}",
                        auto_fixable=True,
                        fix_suggestion=f"考虑优化 {key.replace('_', ' ')} 占用",
                    ))

        # 2. 检查代码问题
        code_issues = await self._check_code_quality()
        new_issues.extend(code_issues)

        # 3. 检查测试覆盖
        test_issues = await self._check_test_coverage()
        new_issues.extend(test_issues)

        # 更新问题列表（去重）
        existing_titles = {i.title for i in self.issues}
        for issue in new_issues:
            if issue.title not in existing_titles:
                self.issues.append(issue)
                self._notify_issue(issue)

        # 移除已修复的问题
        self.issues = [i for i in self.issues if i.title not in self.fixed_issues]

    async def _check_code_quality(self) -> List[Issue]:
        """检查代码质量"""
        issues = []

        for monitored_path in self.monitored_paths:
            src_path = self.project_root / monitored_path
            if not src_path.exists():
                continue

            # 统计代码行数
            total_lines = 0
            file_count = 0
            for py_file in src_path.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        lines = len(f.readlines())
                        total_lines += lines
                        file_count += 1
                except:
                    pass

            # 检查文件大小
            for py_file in src_path.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        lines = len(f.readlines())
                        if lines > 2000:
                            issues.append(Issue(
                                category=IssueCategory.QUALITY,
                                severity=IssueSeverity.MEDIUM,
                                title=f"大文件: {py_file.name}",
                                description=f"文件超过2000行 ({lines}行)",
                                location=str(py_file.relative_to(self.project_root)),
                                auto_fixable=False,
                            ))
                except:
                    pass

        return issues

    async def _check_test_coverage(self) -> List[Issue]:
        """检查测试覆盖"""
        issues = []

        # 检查是否有测试文件
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            issues.append(Issue(
                category=IssueCategory.QUALITY,
                severity=IssueSeverity.LOW,
                title="缺少测试目录",
                description="tests 目录不存在",
                auto_fixable=False,
            ))

        return issues

    async def _generate_improvements(self) -> List[ImprovementAction]:
        """生成改进建议"""
        improvements = []

        # 基于问题生成改进
        for issue in self.issues:
            if issue.auto_fixable and issue.fix_suggestion:
                improvements.append(ImprovementAction(
                    action_type=issue.category.value,
                    description=issue.fix_suggestion,
                    priority=1 if issue.severity == IssueSeverity.CRITICAL else 2,
                    estimated_impact="中",
                ))

        return improvements

    async def _apply_fixes(self, improvements: List[ImprovementAction]):
        """应用修复（谨慎！）"""
        for improvement in improvements[:3]:  # 最多一次应用3个
            if improvement.implemented:
                continue

            # 这里需要实现实际的自动修复逻辑
            # 当前只是记录建议，不实际修复
            improvement.implemented = True
            self.improvement_history.append(improvement)

    async def _generate_report(self):
        """生成报告"""
        if not self.issues:
            return

        # 按类别分组
        by_category: Dict[IssueCategory, List[Issue]] = {}
        for issue in self.issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)

        # 打印摘要
        print(f"\n【问题摘要】")
        for category, issues in by_category.items():
            high_count = sum(1 for i in issues if i.severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL])
            print(f"  {category.value}: {len(issues)}个 ({high_count}个高危)")

    def _notify_issue(self, issue: Issue):
        """通知问题"""
        for callback in self.issue_callbacks:
            try:
                callback(issue)
            except Exception as e:
                logger.error(f"Issue callback error: {e}")

    def register_issue_callback(self, callback: Callable[[Issue], None]):
        """注册问题回调"""
        self.issue_callbacks.append(callback)

    async def shutdown(self):
        """关闭系统"""
        self._running = False

        print("\n" + "="*60)
        print("监控与自动改进系统已停止")
        print(f"历史问题数: {len(self.issues)}")
        print(f"改进记录数: {len(self.improvement_history)}")
        print(f"已修复问题数: {len(self.fixed_issues)}")
        print("="*60)

        # 保存报告
        await self._save_report()

    async def _save_report(self):
        """保存报告"""
        output_dir = self.project_root / "output" / "monitoring"
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / f"report_{int(time.time())}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_issues": len(self.issues),
            "fixed_issues": len(self.fixed_issues),
            "improvements": [
                {
                    "action_type": i.action_type,
                    "description": i.description,
                    "implemented": i.implemented,
                    "success": i.success,
                }
                for i in self.improvement_history
            ],
            "current_issues": [
                {
                    "category": i.category.value,
                    "severity": i.severity.value,
                    "title": i.title,
                    "description": i.description,
                    "location": i.location,
                }
                for i in self.issues
            ],
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"报告已保存: {report_path}")

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "running": self._running,
            "issues_count": len(self.issues),
            "high_severity_count": sum(
                1 for i in self.issues
                if i.severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]
            ),
            "improvements_count": len(self.improvement_history),
            "performance_metrics": {
                key: values[-1] if values else None
                for key, values in self.performance_metrics.items()
            },
        }


async def run_monitoring_demo():
    """运行监控演示"""
    improver = await AutoImprover(
        check_interval=10.0,
        auto_diagnose=True,
        enable_auto_fix=False,
    )
    await improver.start()


if __name__ == "__main__":
    asyncio.run(run_monitoring_demo())