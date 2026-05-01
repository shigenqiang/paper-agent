"""
Intent Routing - 意图路由模块

提供意图路由优化、智能路由选择和回退处理功能。
包含原 intent/ 模块的全部功能。
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
from .llm_intent_classifier import (
    LLMIntentClassifier,
    Intent,
    IntentResult,
    classify_intent,
)
# 从原 intent/ 模块合并的导出
from .intent_classifier import (
    IntentClassifier,
    IntentResult as IntentClassifierResult,
    IntentType,
)
from .multi_intent import (
    MultiIntentDetector,
    MultiIntentResult,
)
from .intent_confidence import (
    IntentConfidence,
    ConfidenceResult,
)
from .semantic_expander import (
    SemanticKeywordExpander,
    ExpansionResult,
    expand_keywords,
    expand_query,
)

__all__ = [
    # 原 routing/ 模块
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
    "LLMIntentClassifier",
    "Intent",
    "IntentResult",
    "classify_intent",
    # 原 intent/ 模块
    "IntentClassifier",
    "IntentClassifierResult",
    "IntentType",
    "MultiIntentDetector",
    "MultiIntentResult",
    "IntentConfidence",
    "ConfidenceResult",
    "SemanticKeywordExpander",
    "ExpansionResult",
    "expand_keywords",
    "expand_query",
]
