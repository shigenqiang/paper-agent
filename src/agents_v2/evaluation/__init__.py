"""
评估模块 - Agent评估和报告生成

提供:
1. 报告生成器 (ReportGenerator)
2. 评估基准 (Benchmarks)
   - GAIA基准
   - AgentBench适配器
   - 论文写作专项基准
   - A/B测试框架
3. 输出验证器 (OutputValidator)
   - 结构完整性验证
   - 内容质量验证
   - 格式规范验证
4. 输出格式化器 (OutputFormatter)
   - Markdown/JSON/HTML/LaTeX格式化
   - 学术论文格式化
5. RAG评估器 (RAGEvaluator)
   - 检索质量评估
   - 生成质量评估
   - 综合评分
6. 链路集成器 (ChainIntegrator)
   - 全链路测试
   - 集成测试编排
7. 性能基准 (PerformanceBenchmark)
   - 延迟基准测试
   - 吞吐量基准测试
   - 资源使用监控
8. 反馈收集器 (FeedbackCollector)
   - 用户反馈收集
   - 反馈分类与优先级
   - 反馈分析
9. 混沌测试器 (ChaosTester)
   - 故障注入测试
   - 韧性测试
   - 恢复测试
10. E2E测试套件 (E2ETestSuite)
    - 完整流程测试
    - 场景测试
    - 回归测试
11. 发布检查器 (ReleaseChecker)
    - 发布前检查清单
    - 版本验证
    - 依赖检查
"""
from .report_generator import (
    ReportGenerator,
    EvaluationDimension,
    get_report_generator
)
from .output_validator import (
    OutputValidator,
    SchemaValidator,
    QualityVerifier,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_output,
    verify_quality
)
from .output_formatter import (
    OutputFormatter,
    OutputFormat,
    MarkdownStyle,
    FormattedOutput,
    format_output
)
from .rag_evaluator import (
    RAGEvaluator,
    RetrievalMetrics,
    RetrievalEvalResult,
    GenerationEvalResult,
    RAGEvalResult,
    EvaluationMetric,
    evaluate_rag,
    evaluate_retrieval
)
from .chain_integrator import (
    ChainIntegrator,
    IntegrationTester,
    IntegrationStage,
    IntegrationStep,
    IntegrationResult,
    ChainTestResult
)
from .performance_benchmark import (
    PerformanceBenchmark,
    LoadTester,
    LatencyStats,
    ThroughputStats,
    ResourceStats,
    BenchmarkType,
    benchmark_function
)
from .feedback_collector import (
    FeedbackCollector,
    FeedbackAnalyzer,
    FeedbackType,
    FeedbackPriority,
    FeedbackStatus,
    Feedback,
    FeedbackSummary,
    collect_feedback
)
from .chaos_tester import (
    ChaosTester,
    RecoveryTester,
    TimeoutHandler,
    ChaosAction,
    ChaosTarget,
    ChaosScenario,
    ChaosResult,
    ChaosTestReport,
    run_chaos_test,
    test_system_resilience
)
from .e2e_test_suite import (
    E2ETestSuite,
    RegressionTester,
    TestType,
    TestStatus,
    TestCase,
    TestResult,
    E2ETestReport,
    run_e2e_tests,
    run_smoke_tests,
    run_regression_tests
)
from .release_checker import (
    ReleaseChecker,
    CheckCategory,
    CheckSeverity,
    CheckStatus,
    CheckResult,
    ReleaseCheckReport,
    check_release,
    format_report
)
from .quality_evaluator import (
    QualityEvaluator,
    EvalDimension,
    DimensionScore,
    QualityReport,
    RuleEngine,
    LLMJudge,
    create_evaluator,
)

# 导入benchmarks模块
from . import benchmarks

__all__ = [
    # 报告生成
    "ReportGenerator",
    "EvaluationDimension",
    "get_report_generator",
    # 输出验证
    "OutputValidator",
    "SchemaValidator",
    "QualityVerifier",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "validate_output",
    "verify_quality",
    # 输出格式化
    "OutputFormatter",
    "OutputFormat",
    "MarkdownStyle",
    "FormattedOutput",
    "format_output",
    # RAG评估
    "RAGEvaluator",
    "RetrievalMetrics",
    "RetrievalEvalResult",
    "GenerationEvalResult",
    "RAGEvalResult",
    "EvaluationMetric",
    "evaluate_rag",
    "evaluate_retrieval",
    # 链路集成
    "ChainIntegrator",
    "IntegrationTester",
    "IntegrationStage",
    "IntegrationStep",
    "IntegrationResult",
    "ChainTestResult",
    # 性能基准
    "PerformanceBenchmark",
    "LoadTester",
    "LatencyStats",
    "ThroughputStats",
    "ResourceStats",
    "BenchmarkType",
    "benchmark_function",
    # 反馈收集
    "FeedbackCollector",
    "FeedbackAnalyzer",
    "FeedbackType",
    "FeedbackPriority",
    "FeedbackStatus",
    "Feedback",
    "FeedbackSummary",
    "collect_feedback",
    # 混沌测试
    "ChaosTester",
    "RecoveryTester",
    "TimeoutHandler",
    "ChaosAction",
    "ChaosTarget",
    "ChaosScenario",
    "ChaosResult",
    "ChaosTestReport",
    "run_chaos_test",
    "test_system_resilience",
    # E2E测试
    "E2ETestSuite",
    "RegressionTester",
    "TestType",
    "TestStatus",
    "TestCase",
    "TestResult",
    "E2ETestReport",
    "run_e2e_tests",
    "run_smoke_tests",
    "run_regression_tests",
    # 发布检查
    "ReleaseChecker",
    "CheckCategory",
    "CheckSeverity",
    "CheckStatus",
    "CheckResult",
    "ReleaseCheckReport",
    "check_release",
    "format_report",
    # Benchmarks
    "benchmarks",
    # 质量评估
    "QualityEvaluator",
    "EvalDimension",
    "DimensionScore",
    "QualityReport",
    "RuleEngine",
    "LLMJudge",
    "create_evaluator",
]
