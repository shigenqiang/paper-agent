"""
Agent Selector - Agent选择器

根据意图和上下文选择最合适的Agent。
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..intent import IntentType


@dataclass
class AgentCapability:
    """Agent能力描述"""
    name: str
    supported_intents: List[IntentType] = field(default_factory=list)
    supported_languages: List[str] = field(default_factory=list)
    max_context_length: int = 4000
    average_latency: float = 0.0
    success_rate: float = 0.95
    cost_per_request: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelectionCriteria:
    """选择标准"""
    prioritize_speed: bool = False
    prioritize_accuracy: bool = False
    prioritize_cost: bool = False
    max_latency: Optional[float] = None
    max_cost: Optional[float] = None
    require_language: Optional[str] = None


@dataclass
class SelectionResult:
    """选择结果"""
    selected_agent: str
    agent_capability: Optional[AgentCapability] = None
    confidence: float = 0.0
    reasoning: str = ""
    alternatives: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_agent": self.selected_agent,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "metadata": self.metadata
        }


class AgentSelector:
    """
    Agent选择器

    功能:
    - 根据意图选择最合适的Agent
    - 考虑速度、准确性、成本
    - 提供备选Agent列表

    使用示例:
        selector = AgentSelector()

        result = selector.select(
            intent=IntentType.LITERATURE_SEARCH,
            criteria=SelectionCriteria(prioritize_speed=True)
        )
        print(f"选择Agent: {result.selected_agent}")
    """

    # 预定义的Agent能力
    AGENT_CAPABILITIES = {
        "PaperSearchAgent": AgentCapability(
            name="PaperSearchAgent",
            supported_intents=[IntentType.LITERATURE_SEARCH, IntentType.QUESTION_ANSWER],
            supported_languages=["en", "zh"],
            average_latency=0.5,
            success_rate=0.95
        ),
        "LiteratureReviewAgent": AgentCapability(
            name="LiteratureReviewAgent",
            supported_intents=[IntentType.LITERATURE_REVIEW, IntentType.SUMMARY],
            supported_languages=["en", "zh"],
            average_latency=1.0,
            success_rate=0.90
        ),
        "TopicSelectAgent": AgentCapability(
            name="TopicSelectAgent",
            supported_intents=[IntentType.TOPIC_SELECT, IntentType.THESIS_FORMULATE],
            supported_languages=["en", "zh"],
            average_latency=0.8,
            success_rate=0.88
        ),
        "OutlineGeneratorAgent": AgentCapability(
            name="OutlineGeneratorAgent",
            supported_intents=[IntentType.OUTLINE_GENERATE],
            supported_languages=["en", "zh"],
            average_latency=0.6,
            success_rate=0.92
        ),
        "DraftWriterAgent": AgentCapability(
            name="DraftWriterAgent",
            supported_intents=[IntentType.DRAFT_WRITE, IntentType.FULL_PAPER],
            supported_languages=["en", "zh"],
            average_latency=2.0,
            success_rate=0.85
        ),
        "TranslatorAgent": AgentCapability(
            name="TranslatorAgent",
            supported_intents=[IntentType.TRANSLATION],
            supported_languages=["en", "zh"],
            average_latency=0.4,
            success_rate=0.98
        ),
        "DiagnosticAgent": AgentCapability(
            name="DiagnosticAgent",
            supported_intents=[IntentType.DIAGNOSTIC],
            supported_languages=["en", "zh"],
            average_latency=0.3,
            success_rate=0.97
        ),
    }

    def __init__(self):
        self._custom_agents: Dict[str, AgentCapability] = {}

    def select(
        self,
        intent: IntentType,
        criteria: Optional[SelectionCriteria] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SelectionResult:
        """
        选择最合适的Agent

        Args:
            intent: 意图类型
            criteria: 选择标准
            context: 上下文信息

        Returns:
            SelectionResult: 选择结果
        """
        criteria = criteria or SelectionCriteria()
        context = context or {}

        # 获取支持该意图的Agent
        candidates = self._get_candidates(intent)

        if not candidates:
            return SelectionResult(
                selected_agent="UnknownAgent",
                confidence=0.0,
                reasoning=f"No agent found for intent {intent.value}"
            )

        # 过滤和排序
        filtered = self._filter_candidates(candidates, criteria, context)
        sorted_candidates = self._rank_candidates(filtered, criteria)

        # 选择最佳Agent
        best = sorted_candidates[0]
        alternatives = [a.name for a in sorted_candidates[1:4]]

        return SelectionResult(
            selected_agent=best.name,
            agent_capability=best,
            confidence=best.success_rate,
            reasoning=f"Selected {best.name} for {intent.value}",
            alternatives=alternatives,
            metadata={
                "intent": intent.value,
                "criteria": {
                    "prioritize_speed": criteria.prioritize_speed,
                    "prioritize_accuracy": criteria.prioritize_accuracy,
                    "prioritize_cost": criteria.prioritize_cost
                }
            }
        )

    def _get_candidates(self, intent: IntentType) -> List[AgentCapability]:
        """获取支持特定意图的Agent"""
        all_agents = {**self.AGENT_CAPABILITIES, **self._custom_agents}
        return [
            agent for agent in all_agents.values()
            if intent in agent.supported_intents
        ]

    def _filter_candidates(
        self,
        candidates: List[AgentCapability],
        criteria: SelectionCriteria,
        context: Dict[str, Any]
    ) -> List[AgentCapability]:
        """过滤候选Agent"""
        filtered = candidates

        # 语言过滤
        if criteria.require_language:
            filtered = [
                a for a in filtered
                if criteria.require_language in a.supported_languages
            ]

        # 延迟过滤
        if criteria.max_latency:
            filtered = [
                a for a in filtered
                if a.average_latency <= criteria.max_latency
            ]

        # 成本过滤
        if criteria.max_cost:
            filtered = [
                a for a in filtered
                if a.cost_per_request <= criteria.max_cost
            ]

        return filtered if filtered else candidates

    def _rank_candidates(
        self,
        candidates: List[AgentCapability],
        criteria: SelectionCriteria
    ) -> List[AgentCapability]:
        """对候选Agent排序"""
        def score(agent: AgentCapability) -> float:
            s = 0.0

            if criteria.prioritize_speed:
                s += (1.0 - agent.average_latency) * 0.4
            else:
                s += agent.success_rate * 0.3

            if criteria.prioritize_accuracy:
                s += agent.success_rate * 0.5

            if criteria.prioritize_cost:
                s += (1.0 - agent.cost_per_request) * 0.3
            else:
                s += agent.success_rate * 0.2

            # 基础成功率
            s += agent.success_rate * 0.3

            return s

        return sorted(candidates, key=score, reverse=True)

    def register_agent(self, capability: AgentCapability):
        """注册自定义Agent"""
        self._custom_agents[capability.name] = capability

    def list_agents(self) -> List[str]:
        """列出所有Agent"""
        all_agents = {**self.AGENT_CAPABILITIES, **self._custom_agents}
        return list(all_agents.keys())

    def get_agent_capability(self, name: str) -> Optional[AgentCapability]:
        """获取Agent能力"""
        all_agents = {**self.AGENT_CAPABILITIES, **self._custom_agents}
        return all_agents.get(name)


def select_agent(intent: IntentType, **kwargs) -> SelectionResult:
    """便捷函数：选择Agent"""
    selector = AgentSelector()
    return selector.select(intent, **kwargs)