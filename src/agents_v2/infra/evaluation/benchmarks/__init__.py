"""
Evaluation Benchmarks - 评估基准模块

包含:
- GAIA: General AI Assistants 基准
- AgentBench: 多领域Agent评估
- PaperWriting: 论文写作专项评估
- A/B Testing: 策略对比框架
"""
from .gaia import GAIABenchmark, GAIATask, GAIAResult, run_gaia_evaluation
from .agent_bench import (
    AgentBenchAdapter,
    Domain,
    DomainTask,
    DomainResult,
    BenchmarkReport,
    run_agent_bench_evaluation
)
from .paper_writing import (
    PaperWritingBenchmark,
    PaperWritingResult,
    DimensionScore,
    evaluate_paper
)
from .ab_testing import (
    ABTestFramework,
    ABTestResult,
    AgentConfig,
    TestTask,
    TaskResult,
    TestTypeEnum,
    run_ab_test
)

__all__ = [
    # GAIA
    "GAIABenchmark",
    "GAIATask",
    "GAIAResult",
    "run_gaia_evaluation",

    # AgentBench
    "AgentBenchAdapter",
    "Domain",
    "DomainTask",
    "DomainResult",
    "BenchmarkReport",
    "run_agent_bench_evaluation",

    # Paper Writing
    "PaperWritingBenchmark",
    "PaperWritingResult",
    "DimensionScore",
    "evaluate_paper",

    # A/B Testing
    "ABTestFramework",
    "ABTestResult",
    "AgentConfig",
    "TestTask",
    "TaskResult",
    "TestTypeEnum",
    "run_ab_test"
]
