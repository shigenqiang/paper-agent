"""
Intent Routing - 意图路由模块

提供意图路由优化、智能路由选择和回退处理功能。
"""
from .routing_optimizer import (
    RoutingOptimizer,
    RouteResult,
    RouteStrategy,
)
from .agent_selector import (
    AgentSelector,
    SelectionResult,
    SelectionCriteria,
    AgentCapability,
)
from .fallback_router import (
    FallbackRouter,
    FallbackResult,
    FallbackStrategy,
)

__all__ = [
    "RoutingOptimizer",
    "RouteResult",
    "RouteStrategy",
    "AgentSelector",
    "SelectionResult",
    "SelectionCriteria",
    "AgentCapability",
    "FallbackRouter",
    "FallbackResult",
    "FallbackStrategy",
]