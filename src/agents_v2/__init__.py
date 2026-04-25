"""新架构Agent模块"""
from .base_agent import (
    BaseAgent,
    AgentInput,
    AgentOutput,
    AgentCapability,
    LLMConfig,
    Tool,
    VirtualTool
)

# 统一框架
from .unified import (
    MasterSupervisor,
    PhaseSupervisor,
    PaperState,
    CircuitBreaker,
    CircuitBreakerOpen,
    FallbackHandler,
    RetryPolicy,
    ProblemType,
    PhaseStatus,
    QualityLevel
)

__all__ = [
    "BaseAgent",
    "AgentInput",
    "AgentOutput",
    "AgentCapability",
    "LLMConfig",
    "Tool",
    "VirtualTool",
    # 统一框架
    "MasterSupervisor",
    "PhaseSupervisor",
    "PaperState",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "FallbackHandler",
    "RetryPolicy",
    "ProblemType",
    "PhaseStatus",
    "QualityLevel"
]
