"""
Harness 模块 - 质量保障

提供运行时质量保障机制:
- CircuitBreaker: 熔断器，防止级联失败
- ErrorHandler: 错误处理和恢复
- HITLManager: 人机协作管理
- ExecutionReplay: 执行回放
- OutputManager: 输出管理

注意: 此模块直接从 unified/ 迁移而来。
对于向后兼容性，请继续使用 src.agents_v2.unified 中的相应组件。
"""
import warnings

warnings.warn(
    "src.agents_v2.harness 是新的模块路径，但 unified/ 仍保留用于向后兼容。",
    DeprecationWarning,
    stacklevel=2
)

# 导出主要组件
from src.agents_v2.unified import (
    CircuitBreaker,
    CircuitBreakerOpen,
    MultiCircuitBreaker,
    FallbackHandler,
    RetryPolicy,
    ErrorAccumulator,
    HITLManager,
    InterventionType,
    InterventionPriority,
    InterventionRequest,
    InterventionResponse,
    get_hitl_manager,
    ExecutionReplay,
    ExecutionReplayManager,
    ReplayEntry,
    SlowExecutionWarning,
    EarlyResult,
    create_replay,
    create_replay_manager,
    ResultCache,
    LLMLCallOptimizer,
    SemanticCache,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "MultiCircuitBreaker",
    "FallbackHandler",
    "RetryPolicy",
    "ErrorAccumulator",
    "HITLManager",
    "InterventionType",
    "InterventionPriority",
    "InterventionRequest",
    "InterventionResponse",
    "get_hitl_manager",
    "ExecutionReplay",
    "ExecutionReplayManager",
    "ReplayEntry",
    "SlowExecutionWarning",
    "EarlyResult",
    "create_replay",
    "create_replay_manager",
    "ResultCache",
    "LLMLCallOptimizer",
    "SemanticCache",
]