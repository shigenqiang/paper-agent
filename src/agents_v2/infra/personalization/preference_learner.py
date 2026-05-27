"""
用户偏好学习器 - Preference Learner

学习用户的多维偏好:
- 写作风格 (简洁/详细)
- 引用格式 (APA/MLA/GB/T)
- 深度偏好 (浅/中/深)
- 主题兴趣 (AI/医学/金融等)
- 时间偏好 (工作日/周末)
"""
from src.agents_v2.logging_config import get_logging_logger

import time

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

logger = get_logging_logger(__name__)


@dataclass
class PreferenceProfile:
    """用户偏好画像"""
    writing_style: str = "balanced"  # concise/balanced/detailed
    citation_format: str = "GB/T"    # APA/MLA/GB/T
    depth_preference: str = "medium"  # shallow/medium/deep
    topics: List[str] = field(default_factory=list)
    time_preference: str = "anytime"  # weekday/weekend/anytime
    language: str = "zh"             # zh/en
    confidence: Dict[str, float] = field(default_factory=dict)  # 各维度置信度
    last_updated: float = field(default_factory=time.time)


@dataclass
class InteractionRecord:
    """交互记录"""
    timestamp: float
    interaction_type: str  # query/revision/selection/feedback
    content: str
    outcome: str  # accepted/rejected/modified
    metadata: Dict = field(default_factory=dict)


class PreferenceLearner:
    """用户偏好学习器

    通过分析用户行为学习偏好:
    1. 查询模式分析
    2. 选择/拒绝分析
    3. 反馈信号
    4. 时间模式
    """

    def __init__(self, user_id: str = "default"):
        """初始化

        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.profile = PreferenceProfile()
        self._interaction_history: List[InteractionRecord] = []
        self._topic_counts: Dict[str, int] = defaultdict(int)
        self._style_signals: Dict[str, int] = defaultdict(int)
        self._time_slots: Dict[int, int] = defaultdict(int)  # hour -> count

    def record_interaction(self,
                          interaction_type: str,
                          content: str,
                          outcome: str,
                          metadata: Dict = None):
        """记录交互

        Args:
            interaction_type: 交互类型
            content: 内容
            outcome: 结果
            metadata: 元数据
        """
        record = InteractionRecord(
            timestamp=time.time(),
            interaction_type=interaction_type,
            content=content,
            outcome=outcome,
            metadata=metadata or {}
        )
        self._interaction_history.append(record)

        # 实时学习
        self._update_preferences(record)

    def _update_preferences(self, record: InteractionRecord):
        """根据交互更新偏好"""
        content = record.content.lower()

        # 学习写作风格
        if record.interaction_type == "revision":
            # 分析修改模式
            if "简化" in content or "缩短" in content:
                self._style_signals["concise"] += 1
            elif "详细" in content or "扩展" in content:
                self._style_signals["detailed"] += 1

        # 学习引用格式
        if "apa" in content:
            self.profile.citation_format = "APA"
        elif "mla" in content:
            self.profile.citation_format = "MLA"
        elif "gb/t" in content or "国标" in content:
            self.profile.citation_format = "GB/T"

        # 学习主题兴趣
        topic_keywords = {
            "ai": ["人工智能", "AI", "机器学习", "深度学习"],
            "medical": ["医学", "医疗", "疾病", "治疗"],
            "finance": ["金融", "经济", "投资", "股票"],
            "education": ["教育", "学习", "教学", "学校"],
            "law": ["法律", "司法", "判决", "法规"]
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in content for kw in keywords):
                self._topic_counts[topic] += 1

        # 学习时间偏好
        hour = time.localtime(record.timestamp).tm_hour
        if 9 <= hour <= 17:
            self._time_slots["weekday"] += 1
        elif 18 <= hour <= 22:
            self._time_slots["evening"] += 1
        else:
            self._time_slots["other"] += 1

        self.profile.last_updated = time.time()

    def update_from_feedback(self, feedback_type: str, content: str):
        """从反馈中学习

        Args:
            feedback_type: 反馈类型 (positive/negative/neutral)
            content: 内容
        """
        outcome = "accepted" if feedback_type == "positive" else "rejected"
        self.record_interaction("feedback", content, outcome)

    def update_from_selection(self, selected_option: str, alternatives: List[str]):
        """从选择中学习

        Args:
            selected_option: 选择的选项
            alternatives: 所有选项
        """
        self.record_interaction(
            "selection",
            selected_option,
            "accepted",
            {"alternatives": alternatives}
        )

    def infer_writing_style(self) -> Tuple[str, float]:
        """推断写作风格偏好

        Returns:
            Tuple[str, float]: (风格, 置信度)
        """
        total = sum(self._style_signals.values())
        if total == 0:
            return "balanced", 0.5

        concise_ratio = self._style_signals["concise"] / total
        detailed_ratio = self._style_signals["detailed"] / total

        if concise_ratio > 0.6:
            return "concise", min(concise_ratio, 1.0)
        elif detailed_ratio > 0.6:
            return "detailed", min(detailed_ratio, 1.0)
        else:
            return "balanced", 0.5

    def infer_depth_preference(self) -> Tuple[str, float]:
        """推断深度偏好

        Returns:
            Tuple[str, float]: (深度, 置信度)
        """
        # 基于查询长度推断
        recent_queries = [
            r.content for r in self._interaction_history[-10:]
            if r.interaction_type == "query"
        ]

        if not recent_queries:
            return "medium", 0.5

        avg_length = sum(len(q) for q in recent_queries) / len(recent_queries)

        if avg_length > 200:
            return "deep", 0.7
        elif avg_length < 50:
            return "shallow", 0.7
        else:
            return "medium", 0.6

    def infer_topics(self, top_k: int = 5) -> List[Tuple[str, float]]:
        """推断主题兴趣

        Args:
            top_k: 返回数量

        Returns:
            List[Tuple[str, float]]: [(主题, 置信度)]
        """
        total = sum(self._topic_counts.values())
        if total == 0:
            return []

        topic_scores = []
        for topic, count in self._topic_counts.items():
            score = count / total
            topic_scores.append((topic, score))

        topic_scores.sort(key=lambda x: x[1], reverse=True)
        return topic_scores[:top_k]

    def infer_time_preference(self) -> Tuple[str, float]:
        """推断时间偏好

        Returns:
            Tuple[str, float]: (时间偏好, 置信度)
        """
        total = sum(self._time_slots.values())
        if total == 0:
            return "anytime", 0.5

        weekday_ratio = self._time_slots["weekday"] / total

        if weekday_ratio > 0.7:
            return "weekday", min(weekday_ratio, 1.0)
        elif self._time_slots.get("evening", 0) / total > 0.5:
            return "evening", 0.6
        else:
            return "anytime", 0.5

    def build_profile(self) -> PreferenceProfile:
        """构建完整偏好画像

        Returns:
            PreferenceProfile: 偏好画像
        """
        # 推断各维度
        style, style_conf = self.infer_writing_style()
        self.profile.writing_style = style

        depth, depth_conf = self.infer_depth_preference()
        self.profile.depth_preference = depth

        topics = self.infer_topics()
        self.profile.topics = [t[0] for t in topics]

        time_pref, time_conf = self.infer_time_preference()
        self.profile.time_preference = time_pref

        # 更新置信度
        self.profile.confidence = {
            "writing_style": style_conf,
            "depth_preference": depth_conf,
            "topics": sum(t[1] for t in topics) / len(topics) if topics else 0.5,
            "time_preference": time_conf
        }

        return self.profile

    def get_recommendation(self, context: str) -> Dict[str, Any]:
        """获取个性化推荐

        Args:
            context: 上下文

        Returns:
            Dict: 推荐结果
        """
        profile = self.build_profile()

        return {
            "writing_style": profile.writing_style,
            "depth": profile.depth_preference,
            "citation_format": profile.citation_format,
            "suggested_topics": profile.topics[:3],
            "confidence": profile.confidence,
            "reasoning": self._generate_reasoning()
        }

    def _generate_reasoning(self) -> str:
        """生成推荐理由"""
        reasons = []
        profile = self.build_profile()

        if profile.writing_style == "concise":
            reasons.append("您倾向于简洁的写作风格")
        elif profile.writing_style == "detailed":
            reasons.append("您偏好详细的论述")

        if profile.topics:
            reasons.append(f"您对 {', '.join(profile.topics[:2])} 领域感兴趣")

        if profile.time_preference == "weekday":
            reasons.append("您主要在工作日使用")
        elif profile.time_preference == "evening":
            reasons.append("您偏好在晚间使用")

        return "; ".join(reasons) if reasons else "基于历史行为推断"

    def get_stats(self) -> Dict[str, Any]:
        """获取学习统计

        Returns:
            Dict: 统计信息
        """
        return {
            "total_interactions": len(self._interaction_history),
            "topic_distribution": dict(self._topic_counts),
            "style_signals": dict(self._style_signals),
            "profile": {
                "writing_style": self.profile.writing_style,
                "citation_format": self.profile.citation_format,
                "depth_preference": self.profile.depth_preference,
                "topics": self.profile.topics
            }
        }


# 便捷函数
def create_learner(user_id: str = "default") -> PreferenceLearner:
    """创建偏好学习器"""
    return PreferenceLearner(user_id=user_id)