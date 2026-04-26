"""
Routing Optimizer - 路由优化器

提供意图路由的优化功能，包括路径选择、成本优化等。
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..intent import IntentType


class RouteStrategy(str, Enum):
    """路由策略"""
    FAST = "fast"              # 快速路由
    ACCURATE = "accurate"     # 精确路由
    BALANCED = "balanced"      # 平衡策略
    COST_AWARE = "cost_aware"  # 成本感知


@dataclass
class RouteStep:
    """路由步骤"""
    agent: str
    action: str
    estimated_cost: float = 0.0
    estimated_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResult:
    """路由结果"""
    intent: IntentType
    strategy: RouteStrategy
    route: List[RouteStep] = field(default_factory=list)
    total_cost: float = 0.0
    total_time: float = 0.0
    confidence: float = 0.0
    alternatives: List[List[RouteStep]] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value if isinstance(self.intent, Enum) else self.intent,
            "strategy": self.strategy.value if isinstance(self.strategy, Enum) else self.strategy,
            "route": [
                {
                    "agent": s.agent,
                    "action": s.action,
                    "estimated_cost": s.estimated_cost,
                    "estimated_time": s.estimated_time
                }
                for s in self.route
            ],
            "total_cost": self.total_cost,
            "total_time": self.total_time,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }


class RoutingOptimizer:
    """
    路由优化器

    功能:
    - 根据意图选择最优路由
    - 成本感知路由
    - 备选路由生成

    使用示例:
        optimizer = RoutingOptimizer()

        result = optimizer.optimize(
            intent=IntentType.LITERATURE_SEARCH,
            strategy=RouteStrategy.BALANCED
        )
        print(f"路由: {[s.agent for s in result.route]}")
        print(f"成本: {result.total_cost}")
    """

    # 意图到路由的映射
    INTENT_ROUTES = {
        IntentType.LITERATURE_SEARCH: [
            RouteStep(agent="QueryParser", action="parse"),
            RouteStep(agent="Retriever", action="search"),
            RouteStep(agent="Reranker", action="rerank"),
        ],
        IntentType.LITERATURE_REVIEW: [
            RouteStep(agent="QueryParser", action="parse"),
            RouteStep(agent="Retriever", action="search"),
            RouteStep(agent="Summarizer", action="summarize"),
            RouteStep(agent="Synthesizer", action="synthesize"),
        ],
        IntentType.TOPIC_SELECT: [
            RouteStep(agent="ResearchAnalyzer", action="analyze"),
            RouteStep(agent="TopicGenerator", action="generate"),
            RouteStep(agent="FeasibilityChecker", action="check"),
        ],
        IntentType.OUTLINE_GENERATE: [
            RouteStep(agent="OutlineGenerator", action="generate"),
            RouteStep(agent="StructureValidator", action="validate"),
        ],
        IntentType.DRAFT_WRITE: [
            RouteStep(agent="OutlineGenerator", action="get_outline"),
            RouteStep(agent="DraftWriter", action="write"),
            RouteStep(agent="Reviewer", action="review"),
        ],
        IntentType.FULL_PAPER: [
            RouteStep(agent="QueryParser", action="parse"),
            RouteStep(agent="Retriever", action="search"),
            RouteStep(agent="TopicGenerator", action="generate"),
            RouteStep(agent="OutlineGenerator", action="generate"),
            RouteStep(agent="DraftWriter", action="write"),
            RouteStep(agent="Reviewer", action="review"),
            RouteStep(agent="Polisher", action="polish"),
        ],
        IntentType.DIAGNOSTIC: [
            RouteStep(agent="DiagnosticAgent", action="diagnose"),
            RouteStep(agent="IssueAnalyzer", action="analyze"),
        ],
        IntentType.QUESTION_ANSWER: [
            RouteStep(agent="QueryParser", action="parse"),
            RouteStep(agent="Retriever", action="search"),
            RouteStep(agent="AnswerGenerator", action="generate"),
        ],
        IntentType.SUMMARY: [
            RouteStep(agent="Summarizer", action="summarize"),
        ],
        IntentType.TRANSLATION: [
            RouteStep(agent="Translator", action="translate"),
            RouteStep(agent="Reviewer", action="review"),
        ],
    }

    # 策略成本系数
    STRATEGY_COSTS = {
        RouteStrategy.FAST: 0.5,
        RouteStrategy.ACCURATE: 1.5,
        RouteStrategy.BALANCED: 1.0,
        RouteStrategy.COST_AWARE: 0.8,
    }

    def __init__(self):
        pass

    def optimize(
        self,
        intent: IntentType,
        strategy: RouteStrategy = RouteStrategy.BALANCED,
        context: Optional[Dict[str, Any]] = None
    ) -> RouteResult:
        """
        优化路由

        Args:
            intent: 意图类型
            strategy: 路由策略
            context: 上下文信息

        Returns:
            RouteResult: 路由结果
        """
        # 获取基础路由
        base_route = self.INTENT_ROUTES.get(intent, [])

        if not base_route:
            return RouteResult(
                intent=intent,
                strategy=strategy,
                route=[],
                confidence=0.0,
                reasoning=f"No route defined for {intent.value}"
            )

        # 根据策略调整路由
        optimized_route = self._apply_strategy(base_route, strategy, context or {})

        # 计算成本和时间
        total_cost = sum(s.estimated_cost for s in optimized_route)
        total_time = sum(s.estimated_time for s in optimized_route)

        # 生成备选路由
        alternatives = self._generate_alternatives(intent, strategy)

        # 生成推理说明
        reasoning = self._generate_reasoning(intent, strategy, optimized_route)

        return RouteResult(
            intent=intent,
            strategy=strategy,
            route=optimized_route,
            total_cost=total_cost,
            total_time=total_time,
            confidence=0.85,  # 简化的置信度
            alternatives=alternatives,
            reasoning=reasoning
        )

    def _apply_strategy(
        self,
        route: List[RouteStep],
        strategy: RouteStrategy,
        context: Dict[str, Any]
    ) -> List[RouteStep]:
        """应用策略到路由"""
        if strategy == RouteStrategy.FAST:
            # 快速策略：跳过一些步骤
            return route[:max(1, len(route) // 2)]
        elif strategy == RouteStrategy.ACCURATE:
            # 精确策略：添加验证步骤
            enhanced = list(route)
            if enhanced:
                enhanced.append(RouteStep(
                    agent="Validator",
                    action="validate",
                    estimated_cost=0.1
                ))
            return enhanced
        elif strategy == RouteStrategy.COST_AWARE:
            # 成本感知：使用更便宜的选项
            return [
                step if i % 2 == 0 else RouteStep(
                    agent=f"Cheap{step.agent}",
                    action=step.action,
                    estimated_cost=step.estimated_cost * 0.5
                )
                for i, step in enumerate(route)
            ]
        else:
            # 平衡策略
            return route

    def _generate_alternatives(
        self,
        intent: IntentType,
        strategy: RouteStrategy
    ) -> List[List[RouteStep]]:
        """生成备选路由"""
        alternatives = []

        # 生成不同策略的备选
        for strat in RouteStrategy:
            if strat != strategy:
                alt = self._apply_strategy(
                    self.INTENT_ROUTES.get(intent, []),
                    strat,
                    {}
                )
                if alt:
                    alternatives.append(alt)

        return alternatives[:2]  # 最多两个备选

    def _generate_reasoning(
        self,
        intent: IntentType,
        strategy: RouteStrategy,
        route: List[RouteStep]
    ) -> str:
        """生成推理说明"""
        return (
            f"Route for {intent.value} using {strategy.value} strategy: "
            f"{' -> '.join(s.agent for s in route)}"
        )

    def get_available_routes(self) -> Dict[str, List[str]]:
        """获取所有可用路由"""
        routes = {}
        for intent, steps in self.INTENT_ROUTES.items():
            routes[intent.value] = [s.agent for s in steps]
        return routes


def optimize_route(intent: IntentType, **kwargs) -> RouteResult:
    """便捷函数：优化路由"""
    optimizer = RoutingOptimizer()
    return optimizer.optimize(intent, **kwargs)