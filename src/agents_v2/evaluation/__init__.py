"""
评估模块 - Agent评估和报告生成

提供:
1. 报告生成器 (ReportGenerator)
2. 评估基准 (Benchmarks)
   - GAIA基准
   - AgentBench适配器
   - 论文写作专项基准
   - A/B测试框架
"""
from .report_generator import (
    ReportGenerator,
    EvaluationDimension,
    get_report_generator
)

# 导入benchmarks模块
from . import benchmarks

__all__ = [
    # 报告生成
    "ReportGenerator",
    "EvaluationDimension",
    "get_report_generator",
    # Benchmarks
    "benchmarks"
]
