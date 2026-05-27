"""
Fallback Router - 回退路由器

提供意图路由失败时的回退处理机制。
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..routing.intent_classifier import IntentType


class FallbackStrategy(str, Enum):
    """回退策略"""
    DEFAULT_INTENT = "default_intent"       # 使用默认意图
    SIMPLER_PATH = "simpler_path"           # 使用更简单的路径
    LAST_SUCCESS = "last_success"           # 使用上次成功的路径
    USER_CONFIRM = "user_confirm"           # 请求用户确认
    GRACEFUL_DEGRADE = "graceful_degrade"   # 优雅降级


@dataclass
class FallbackRule:
    """回退规则"""
    from_intent: IntentType
    to_intent: IntentType
    strategy: FallbackStrategy
    condition: Optional[str] = None
    max_attempts: int = 3


@dataclass
class FallbackResult:
    """回退结果"""
    original_intent: IntentType
    resolved_intent: IntentType
    strategy_used: FallbackStrategy
    success: bool
    attempts: int = 0
    reasoning: str = ""
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_intent": self.original_intent.value if isinstance(self.original_intent, Enum) else self.original_intent,
            "resolved_intent": self.resolved_intent.value if isinstance(self.resolved_intent, Enum) else self.resolved_intent,
            "strategy_used": self.strategy_used.value if isinstance(self.strategy_used, Enum) else self.strategy_used,
            "success": self.success,
            "attempts": self.attempts,
            "reasoning": self.reasoning,
            "message": self.message,
            "metadata": self.metadata
        }


class FallbackRouter:
    """
    回退路由器

    功能:
    - 定义回退规则
    - 执行回退策略
    - 跟踪回退历史

    使用示例:
        router = FallbackRouter()

        # 添加回退规则
        router.add_rule(
            from_intent=IntentType.FULL_PAPER,
            to_intent=IntentType.DRAFT_WRITE,
            strategy=FallbackStrategy.SIMPLER_PATH
        )

        # 执行回退
        result = router.route_with_fallback(
            intent=IntentType.FULL_PAPER,
            confidence=0.5,
            error_message="Agent timeout"
        )
    """

    # 默认回退映射
    DEFAULT_FALLBACKS = {
        IntentType.FULL_PAPER: IntentType.DRAFT_WRITE,
        IntentType.LITERATURE_REVIEW: IntentType.LITERATURE_SEARCH,
        IntentType.OUTLINE_GENERATE: IntentType.TOPIC_SELECT,
        IntentType.DRAFT_WRITE: IntentType.OUTLINE_GENERATE,
        IntentType.TOPIC_SELECT: IntentType.LITERATURE_SEARCH,
    }

    # 策略对应的意图
    STRATEGY_INTENTS = {
        FallbackStrategy.SIMPLER_PATH: IntentType.DIAGNOSTIC,
        FallbackStrategy.DEFAULT_INTENT: IntentType.LITERATURE_SEARCH,
        FallbackStrategy.LAST_SUCCESS: IntentType.LITERATURE_SEARCH,
        FallbackStrategy.GRACEFUL_DEGRADE: IntentType.QUESTION_ANSWER,
    }

    def __init__(self):
        self._rules: List[FallbackRule] = []
        self._last_successful: Dict[IntentType, IntentType] = {}
        self._failure_count: Dict[IntentType, int] = {}
        self._fallback_handlers: Dict[FallbackStrategy, Callable] = {}

    def add_rule(
        self,
        from_intent: IntentType,
        to_intent: IntentType,
        strategy: FallbackStrategy = FallbackStrategy.DEFAULT_INTENT,
        condition: Optional[str] = None,
        max_attempts: int = 3
    ):
        """添加回退规则"""
        rule = FallbackRule(
            from_intent=from_intent,
            to_intent=to_intent,
            strategy=strategy,
            condition=condition,
            max_attempts=max_attempts
        )
        self._rules.append(rule)

    def route_with_fallback(
        self,
        intent: IntentType,
        confidence: float = 0.0,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> FallbackResult:
        """
        带回退的路由

        Args:
            intent: 原始意图
            confidence: 置信度
            error_message: 错误信息
            context: 上下文

        Returns:
            FallbackResult: 回退结果
        """
        context = context or {}

        # 检查是否有自定义规则
        rule = self._find_rule(intent)

        # 如果有规则，使用规则
        if rule:
            return self._apply_rule(rule, intent, error_message, context)

        # 检查是否应该回退
        if confidence < 0.5 or error_message:
            return self._apply_default_fallback(intent, error_message, context)

        # 直接返回原始意图
        return FallbackResult(
            original_intent=intent,
            resolved_intent=intent,
            strategy_used=FallbackStrategy.DEFAULT_INTENT,
            success=True,
            reasoning="No fallback needed, confidence sufficient"
        )

    def _find_rule(self, intent: IntentType) -> Optional[FallbackRule]:
        """查找匹配的规则"""
        for rule in self._rules:
            if rule.from_intent == intent:
                # 检查失败次数
                current_failures = self._failure_count.get(intent, 0)
                if current_failures < rule.max_attempts:
                    return rule
        return None

    def _apply_rule(
        self,
        rule: FallbackRule,
        original_intent: IntentType,
        error_message: Optional[str],
        context: Dict[str, Any]
    ) -> FallbackResult:
        """应用回退规则"""
        self._failure_count[original_intent] = self._failure_count.get(original_intent, 0) + 1

        reasoning = f"Fallback triggered by rule: {rule.strategy.value}"
        if error_message:
            reasoning += f" - {error_message}"

        return FallbackResult(
            original_intent=original_intent,
            resolved_intent=rule.to_intent,
            strategy_used=rule.strategy,
            success=True,
            attempts=1,
            reasoning=reasoning,
            message=f"Rerouted from {original_intent.value} to {rule.to_intent.value}"
        )

    def _apply_default_fallback(
        self,
        intent: IntentType,
        error_message: Optional[str],
        context: Dict[str, Any]
    ) -> FallbackResult:
        """应用默认回退"""
        # 获取默认回退意图
        fallback_intent = self.DEFAULT_FALLBACKS.get(intent, IntentType.LITERATURE_SEARCH)

        return FallbackResult(
            original_intent=intent,
            resolved_intent=fallback_intent,
            strategy_used=FallbackStrategy.DEFAULT_INTENT,
            success=True,
            attempts=1,
            reasoning=f"Default fallback applied due to low confidence or error",
            message=f"Fell back from {intent.value} to {fallback_intent.value}"
        )

    def record_success(self, intent: IntentType, resolved_intent: IntentType):
        """记录成功"""
        self._last_successful[intent] = resolved_intent
        if intent in self._failure_count:
            del self._failure_count[intent]

    def record_failure(self, intent: IntentType):
        """记录失败"""
        self._failure_count[intent] = self._failure_count.get(intent, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """获取回退统计"""
        return {
            "total_rules": len(self._rules),
            "failure_counts": dict(self._failure_count),
            "last_successful": {
                k.value: v.value for k, v in self._last_successful.items()
            }
        }

    def clear_stats(self):
        """清除统计"""
        self._failure_count.clear()
        self._last_successful.clear()


def create_fallback_router() -> FallbackRouter:
    """创建回退路由器"""
    router = FallbackRouter()

    # 添加一些默认规则
    router.add_rule(
        from_intent=IntentType.FULL_PAPER,
        to_intent=IntentType.DRAFT_WRITE,
        strategy=FallbackStrategy.SIMPLER_PATH
    )
    router.add_rule(
        from_intent=IntentType.LITERATURE_REVIEW,
        to_intent=IntentType.LITERATURE_SEARCH,
        strategy=FallbackStrategy.DEFAULT_INTENT
    )

    return router