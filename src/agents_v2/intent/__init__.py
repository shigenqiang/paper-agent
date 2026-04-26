"""
Intent Classification - 意图识别模块

提供基于LLM的意图分类、多意图检测、置信度计算等功能。
"""
from .intent_classifier import (
    IntentClassifier,
    IntentResult,
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
    "IntentClassifier",
    "IntentResult",
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