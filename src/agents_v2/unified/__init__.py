"""
统一Agent框架 - 入口与使用示例

Usage:
    from src.agents_v2.unified import MasterSupervisor, LLMConfig

    supervisor = MasterSupervisor(llm_config)
    supervisor.register_problem_agents()
    supervisor.register_pipeline_agents()

    result = await supervisor.run("full_paper", {"topic": "深度学习..."})
"""

# Re-export key components
from .state_model import (
    PaperState,
    PhaseStatus,
    QualityLevel,
    ProblemType,
    QualityScore,
    AgentResult,
    DiagnosticResult,
    PhaseResult,
)
from .master_supervisor import MasterSupervisor, RoutingPolicy
from .phase_supervisor import PhaseSupervisor
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen, MultiCircuitBreaker
from .error_handler import FallbackHandler, RetryPolicy, ErrorAccumulator

__all__ = [
    # State models
    "PaperState",
    "PhaseStatus",
    "QualityLevel",
    "ProblemType",
    "QualityScore",
    "AgentResult",
    "DiagnosticResult",
    "PhaseResult",
    # Core supervisors
    "MasterSupervisor",
    "PhaseSupervisor",
    "RoutingPolicy",
    # Error handling
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "MultiCircuitBreaker",
    "FallbackHandler",
    "RetryPolicy",
    "ErrorAccumulator",
]