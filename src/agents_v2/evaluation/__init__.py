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
4. RAG评估器 (RAGEvaluator)
   - 检索质量评估
   - 生成质量评估
   - 综合评分
5. 链路集成器 (ChainIntegrator)
   - 全链路测试
   - 集成测试编排
6. 性能基准 (PerformanceBenchmark)
   - 延迟基准测试
   - 吞吐量基准测试
   - 资源使用监控
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
    # Benchmarks
    "benchmarks"
]
