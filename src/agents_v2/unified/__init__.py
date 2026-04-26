"""
统一Agent框架 - 入口与使用示例

Usage:
    from src.agents_v2.unified import MasterSupervisor, IntentRouter, LLMConfig

    # 方式1：使用IntentRouter自动路由
    router = IntentRouter(llm_config)
    route_result = await router.route("我想写一篇关于深度学习优化的论文")
    print(f"识别意图: {route_result['intent']}")
    print(f"建议Agent: {route_result['suggested_agents']}")

    # 方式2：直接使用MasterSupervisor
    supervisor = MasterSupervisor(llm_config)
    supervisor.register_problem_agents()
    supervisor.register_pipeline_agents()
    supervisor.register_writing_agents()

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
from .intent_router import IntentRouter, IntentType

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
    # Intent routing
    "IntentRouter",
    "IntentType",
    # Error handling
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "MultiCircuitBreaker",
    "FallbackHandler",
    "RetryPolicy",
    "ErrorAccumulator",
]