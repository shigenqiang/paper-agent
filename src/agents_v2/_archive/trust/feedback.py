"""
Trust Feedback - 信任反馈系统

基于执行结果的信任评估和反馈机制。
"""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeedbackRecord:
    """反馈记录"""
    feedback_id: str
    source: str  # 反馈来源
    target: str  # 反馈目标
    feedback_type: str  # positive/negative/neutral
    quality_score: float  # 质量分数 0-1
    content: str
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustScore:
    """信任分数"""
    entity_id: str
    score: float  # 0-1
    total_feedback: int
    positive_count: int
    negative_count: int
    last_updated: float = field(default_factory=time.time)
    history: List[float] = field(default_factory=list)


class TrustFeedbackSystem:
    """
    信任反馈系统

    功能:
    - 收集反馈
    - 计算信任分数
    - 基于信任调整行为

    使用示例:
        system = TrustFeedbackSystem()

        # 记录反馈
        system.record_feedback(
            source="user",
            target="agent_1",
            feedback_type="positive",
            quality_score=0.9,
            content="Good result"
        )

        # 获取信任分数
        trust = system.get_trust_score("agent_1")
        print(f"Trust: {trust.score:.2f}")
    """

    def __init__(
        self,
        initial_trust: float = 0.5,
        trust_decay_rate: float = 0.01,
        min_trust: float = 0.1,
        max_trust: float = 0.95
    ):
        self.initial_trust = initial_trust
        self.trust_decay_rate = trust_decay_rate
        self.min_trust = min_trust
        self.max_trust = max_trust

        self._trust_scores: Dict[str, TrustScore] = {}
        self._feedback_history: List[FeedbackRecord] = []
        self._feedback_counter = 0

    def record_feedback(
        self,
        source: str,
        target: str,
        feedback_type: str,
        quality_score: float,
        content: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录反馈

        Args:
            source: 反馈来源
            target: 反馈目标
            feedback_type: 反馈类型 (positive/negative/neutral)
            quality_score: 质量分数 (0-1)
            content: 反馈内容
            context: 上下文信息

        Returns:
            str: 反馈ID
        """
        self._feedback_counter += 1
        feedback_id = f"fb_{self._feedback_counter}"

        record = FeedbackRecord(
            feedback_id=feedback_id,
            source=source,
            target=target,
            feedback_type=feedback_type,
            quality_score=quality_score,
            content=content,
            context=context or {}
        )

        self._feedback_history.append(record)

        # 更新信任分数
        self._update_trust_score(target, quality_score, feedback_type)

        logger.debug(f"Recorded feedback for {target}: {feedback_type} ({quality_score:.2f})")
        return feedback_id

    def _update_trust_score(
        self,
        entity_id: str,
        quality_score: float,
        feedback_type: str
    ) -> None:
        """更新信任分数"""
        if entity_id not in self._trust_scores:
            self._trust_scores[entity_id] = TrustScore(
                entity_id=entity_id,
                score=self.initial_trust,
                total_feedback=0,
                positive_count=0,
                negative_count=0
            )

        trust = self._trust_scores[entity_id]
        trust.total_feedback += 1

        # 更新正负计数
        if feedback_type == "positive":
            trust.positive_count += 1
        elif feedback_type == "negative":
            trust.negative_count += 1

        # 计算新分数（指数移动平均）
        alpha = 0.3  # 平滑因子
        if feedback_type == "positive":
            trust.score = trust.score * (1 - alpha) + quality_score * alpha
        elif feedback_type == "negative":
            trust.score = trust.score * (1 - alpha) + max(0, quality_score - 0.5) * alpha

        # 限制范围
        trust.score = max(self.min_trust, min(self.max_trust, trust.score))

        # 更新历史
        trust.history.append(trust.score)
        if len(trust.history) > 100:
            trust.history = trust.history[-100:]

        trust.last_updated = time.time()

    def get_trust_score(self, entity_id: str) -> Optional[TrustScore]:
        """获取信任分数"""
        return self._trust_scores.get(entity_id)

    def get_all_trust_scores(self) -> Dict[str, TrustScore]:
        """获取所有信任分数"""
        return self._trust_scores.copy()

    def apply_decay(self) -> None:
        """应用信任衰减"""
        current_time = time.time()

        for entity_id, trust in self._trust_scores.items():
            # 如果很长时间没有反馈，应用衰减
            time_since_update = current_time - trust.last_updated
            if time_since_update > 86400:  # 超过1天
                decay = self.trust_decay_rate * (time_since_update / 86400)
                trust.score = max(self.min_trust, trust.score - decay)

    def get_feedback_history(
        self,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[FeedbackRecord]:
        """获取反馈历史"""
        history = self._feedback_history

        if entity_id:
            history = [fb for fb in history if fb.target == entity_id]

        return history[-limit:]

    def get_trust_report(self, entity_id: str) -> Dict[str, Any]:
        """获取信任报告"""
        trust = self._trust_scores.get(entity_id)
        if not trust:
            return {"entity_id": entity_id, "found": False}

        recent_feedback = [
            fb for fb in self._feedback_history[-20:]
            if fb.target == entity_id
        ]

        avg_quality = sum(fb.quality_score for fb in recent_feedback) / len(recent_feedback) if recent_feedback else 0

        return {
            "entity_id": entity_id,
            "trust_score": trust.score,
            "total_feedback": trust.total_feedback,
            "positive_ratio": trust.positive_count / trust.total_feedback if trust.total_feedback > 0 else 0,
            "negative_ratio": trust.negative_count / trust.total_feedback if trust.total_feedback > 0 else 0,
            "recent_avg_quality": avg_quality,
            "last_updated": trust.last_updated,
            "trend": self._calculate_trend(trust.history)
        }

    def _calculate_trend(self, history: List[float]) -> str:
        """计算趋势"""
        if len(history) < 2:
            return "stable"

        recent = history[-5:] if len(history) >= 5 else history
        first_half = recent[:len(recent) // 2]
        second_half = recent[len(recent) // 2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        diff = avg_second - avg_first

        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"

    def reset_trust(self, entity_id: str) -> bool:
        """重置信任分数"""
        if entity_id in self._trust_scores:
            del self._trust_scores[entity_id]
            return True
        return False


class TrustAwareRouter:
    """信任感知路由器"""

    def __init__(self, trust_system: TrustFeedbackSystem):
        self.trust_system = trust_system
        self._routing_rules: Dict[str, float] = {}  # entity_id -> min_trust_required

    def set_min_trust(self, entity_id: str, min_trust: float) -> None:
        """设置最小信任要求"""
        self._routing_rules[entity_id] = min_trust

    def can_route_to(self, entity_id: str) -> bool:
        """检查是否可以路由到该实体"""
        trust = self.trust_system.get_trust_score(entity_id)

        if not trust:
            # 没有信任记录，使用初始信任
            return True

        min_required = self._routing_rules.get(entity_id, 0.3)
        return trust.score >= min_required

    def get_trust_weighted_score(
        self,
        base_score: float,
        entity_id: str
    ) -> float:
        """获取信任加权分数"""
        trust = self.trust_system.get_trust_score(entity_id)

        if not trust:
            return base_score

        # 信任加权
        weight = trust.score
        return base_score * (0.5 + 0.5 * weight)


def create_trust_system(
    initial_trust: float = 0.5
) -> TrustFeedbackSystem:
    """创建信任反馈系统"""
    return TrustFeedbackSystem(initial_trust=initial_trust)
