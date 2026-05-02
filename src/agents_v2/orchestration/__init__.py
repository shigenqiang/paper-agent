"""
Orchestration 模块 - 编排逻辑

提供工作流编排能力:
- MasterSupervisor: 全局协调
- PhaseSupervisor: 阶段协调
- IntentRouter: 意图路由
- StateModel: 状态模型

注意: 此模块直接从 unified/ 迁移而来。
对于向后兼容性，请继续使用 src.agents_v2.unified.MasterSupervisor。
"""
import warnings

warnings.warn(
    "src.agents_v2.orchestration 是新的模块路径，但 unified/ 仍保留用于向后兼容。",
    DeprecationWarning,
    stacklevel=2
)

# 导出主要组件
from src.agents_v2.unified import (
    MasterSupervisor,
    PhaseSupervisor,
    IntentRouter,
    IntentType,
    PaperState,
    PhaseStatus,
    QualityLevel,
    ProblemType,
    PhaseResult,
    DiagnosticResult,
    QualityScore,
    AgentResult,
    RoutingPolicy,
)

__all__ = [
    "MasterSupervisor",
    "PhaseSupervisor",
    "IntentRouter",
    "IntentType",
    "PaperState",
    "PhaseStatus",
    "QualityLevel",
    "ProblemType",
    "PhaseResult",
    "DiagnosticResult",
    "QualityScore",
    "AgentResult",
    "RoutingPolicy",
]