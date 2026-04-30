"""
用户行为分析器

功能:
1. 收集用户行为模式
2. 检测用户偏好
3. 推断专业水平
4. 生成用户画像

设计原则:
- 隐私优先，只收集必要的匿名信息
- 本地存储用户偏好
- 提供个性化建议
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class ExpertiseLevel(str, Enum):
    """专业水平"""
    BEGINNER = "beginner"     # 初学者
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"     # 高级
    EXPERT = "expert"         # 专家


class OutputFormat(str, Enum):
    """输出格式偏好"""
    MARKDOWN = "markdown"
    LATEX = "latex"
    WORD = "word"
    PDF = "pdf"


@dataclass
class UserAction:
    """用户操作记录"""
    timestamp: datetime
    action_type: str          # "search", "write", "revise", "export"
    duration_ms: float        # 操作耗时
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPreferences:
    """用户偏好"""
    preferred_output_format: OutputFormat = OutputFormat.MARKDOWN
    revision_tolerance: str = "medium"  # "low", "medium", "high"
    active_hours: List[int] = field(default_factory=list)  # 0-23
    depth_preference: str = "medium"  # "shallow", "medium", "deep"
    citation_style: str = "academic"  # "academic", "simple"
    language_preference: str = "zh"  # "zh", "en", "mixed"


@dataclass
class BehaviorProfile:
    """用户行为画像"""
    user_id: str
    preferences: UserPreferences
    expertise_level: ExpertiseLevel
    activity_level: str  # "low", "medium", "high"
    common_actions: List[str] = field(default_factory=list)
    avg_session_duration_minutes: float = 0
    total_actions: int = 0
    last_active: datetime = None


class PatternDetector:
    """模式检测器"""

    def __init__(self):
        self._patterns = defaultdict(list)

    def detect(self, actions: List[UserAction]) -> Dict[str, Any]:
        """检测行为模式

        Args:
            actions: 用户操作列表

        Returns:
            Dict: 检测到的模式
        """
        patterns = {}

        # 检测时间模式
        time_patterns = self._detect_time_patterns(actions)
        if time_patterns:
            patterns["time"] = time_patterns

        # 检测操作频率模式
        frequency_patterns = self._detect_frequency_patterns(actions)
        if frequency_patterns:
            patterns["frequency"] = frequency_patterns

        # 检测偏好模式
        preference_patterns = self._detect_preference_patterns(actions)
        if preference_patterns:
            patterns["preferences"] = preference_patterns

        return patterns

    def _detect_time_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """检测时间模式"""
        if not actions:
            return {}

        hour_counts = defaultdict(int)
        for action in actions:
            hour = action.timestamp.hour
            hour_counts[hour] += 1

        # 找出最活跃的时段
        most_active_hours = sorted(
            hour_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return {
            "most_active_hours": [h for h, _ in most_active_hours],
            "active_hours_distribution": dict(hour_counts)
        }

    def _detect_frequency_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """检测操作频率模式"""
        if not actions:
            return {}

        action_counts = defaultdict(int)
        for action in actions:
            action_counts[action.action_type] += 1

        return {
            "action_counts": dict(action_counts),
            "most_common_action": max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None
        }

    def _detect_preference_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """检测偏好模式"""
        preferences = {}

        # 检测输出格式偏好
        export_actions = [a for a in actions if a.action_type == "export"]
        if export_actions:
            formats = [a.metadata.get("format", "unknown") for a in export_actions]
            if formats:
                most_common = max(set(formats), key=formats.count)
                preferences["preferred_format"] = most_common

        # 检测修订偏好
        revise_actions = [a for a in actions if a.action_type == "revise"]
        if revise_actions:
            avg_revisions = sum(1 for _ in revise_actions) / len(revise_actions)
            preferences["revision_frequency"] = avg_revisions

        return preferences


class UserBehaviorAnalyzer:
    """用户行为分析器"""

    def __init__(self):
        self._action_history: List[UserAction] = []
        self._pattern_detector = PatternDetector()

    def record_action(self, action: UserAction):
        """记录用户操作"""
        self._action_history.append(action)

        # 保持最近1000条记录
        if len(self._action_history) > 1000:
            self._action_history = self._action_history[-1000:]

    async def analyze(self, user_id: str) -> BehaviorProfile:
        """分析用户行为

        Args:
            user_id: 用户ID

        Returns:
            BehaviorProfile: 用户画像
        """
        # 检测模式
        patterns = self._pattern_detector.detect(self._action_history)

        # 推断偏好
        preferences = self._infer_preferences(patterns)

        # 估计专业水平
        expertise = self._estimate_expertise_level()

        # 计算活跃度
        activity_level = self._calculate_activity_level()

        # 常见操作
        common_actions = self._get_common_actions()

        # 平均会话时长
        avg_duration = self._calculate_avg_session_duration()

        return BehaviorProfile(
            user_id=user_id,
            preferences=preferences,
            expertise_level=expertise,
            activity_level=activity_level,
            common_actions=common_actions,
            avg_session_duration_minutes=avg_duration,
            total_actions=len(self._action_history),
            last_active=self._action_history[-1].timestamp if self._action_history else None
        )

    def _infer_preferences(self, patterns: Dict[str, Any]) -> UserPreferences:
        """从模式推断用户偏好"""
        prefs = UserPreferences()

        if "preferences" in patterns:
            p = patterns["preferences"]

            if "preferred_format" in p:
                try:
                    prefs.preferred_output_format = OutputFormat(p["preferred_format"])
                except ValueError:
                    pass

            if "revision_frequency" in p:
                if p["revision_frequency"] > 3:
                    prefs.revision_tolerance = "high"
                elif p["revision_frequency"] > 1:
                    prefs.revision_tolerance = "medium"
                else:
                    prefs.revision_tolerance = "low"

        if "time" in patterns:
            prefs.active_hours = patterns["time"].get("most_active_hours", [])

        return prefs

    def _estimate_expertise_level(self) -> ExpertiseLevel:
        """估计专业水平"""
        if not self._action_history:
            return ExpertiseLevel.BEGINNER

        # 简单启发式估计
        action_types = set(a.action_type for a in self._action_history)

        # 根据操作类型判断
        advanced_actions = {"write", "revise", "export", "search"}
        beginner_actions = {"help", "tutorial"}

        advanced_count = sum(1 for a in self._action_history if a.action_type in advanced_actions)
        beginner_count = sum(1 for a in self._action_history if a.action_type in beginner_actions)

        total = len(self._action_history)

        if total < 10:
            return ExpertiseLevel.BEGINNER
        elif advanced_count / total > 0.7:
            return ExpertiseLevel.ADVANCED
        elif advanced_count / total > 0.4:
            return ExpertiseLevel.INTERMEDIATE
        else:
            return ExpertiseLevel.BEGINNER

    def _calculate_activity_level(self) -> str:
        """计算活跃度"""
        if not self._action_history:
            return "low"

        # 计算最近7天的活动
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        recent_actions = [
            a for a in self._action_history
            if a.timestamp > week_ago
        ]

        if len(recent_actions) > 50:
            return "high"
        elif len(recent_actions) > 20:
            return "medium"
        else:
            return "low"

    def _get_common_actions(self) -> List[str]:
        """获取常见操作"""
        action_counts = defaultdict(int)
        for action in self._action_history:
            action_counts[action.action_type] += 1

        sorted_actions = sorted(
            action_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [action for action, _ in sorted_actions[:5]]

    def _calculate_avg_session_duration(self) -> float:
        """计算平均会话时长"""
        if len(self._action_history) < 2:
            return 0

        # 简单按时间戳分组估算会话
        sessions = []
        current_session = []

        for action in self._action_history:
            if not current_session:
                current_session.append(action)
            else:
                # 如果间隔超过30分钟，认为是新会话
                last_time = current_session[-1].timestamp
                if (action.timestamp - last_time).total_seconds() > 1800:
                    sessions.append(current_session)
                    current_session = [action]
                else:
                    current_session.append(action)

        if current_session:
            sessions.append(current_session)

        if not sessions:
            return 0

        # 计算平均时长
        durations = []
        for session in sessions:
            if len(session) > 1:
                start = session[0].timestamp
                end = session[-1].timestamp
                duration = (end - start).total_seconds() / 60
                durations.append(duration)

        return sum(durations) / len(durations) if durations else 0

    def get_recent_actions(self, count: int = 10) -> List[UserAction]:
        """获取最近的操作"""
        return self._action_history[-count:]

    def get_action_stats(self) -> Dict[str, Any]:
        """获取操作统计"""
        if not self._action_history:
            return {}

        action_counts = defaultdict(int)
        success_counts = defaultdict(int)
        total_duration = defaultdict(float)

        for action in self._action_history:
            action_counts[action.action_type] += 1
            if action.success:
                success_counts[action.action_type] += 1
            total_duration[action.action_type] += action.duration_ms

        stats = {}
        for action_type in action_counts:
            stats[action_type] = {
                "count": action_counts[action_type],
                "success_rate": success_counts[action_type] / action_counts[action_type],
                "avg_duration_ms": total_duration[action_type] / action_counts[action_type]
            }

        return stats


class SmartPromptGenerator:
    """智能提示生成器"""

    def __init__(self, behavior_analyzer: UserBehaviorAnalyzer):
        self.behavior_analyzer = behavior_analyzer
        self._templates = self._load_templates()

    def _load_templates(self) -> Dict[str, List[str]]:
        """加载提示模板"""
        return {
            "encouragement": [
                "已经修订多次，建议先调整研究方向或完善文献综述",
                "您已经完成了大量工作，可以考虑先生成大纲"
            ],
            "help": [
                "当前质量分数偏低，建议先完善文献综述部分",
                "建议补充更多参考文献以增强论据"
            ],
            "efficiency": [
                "您最近的检索效率很高，继续保持",
                "基于您的偏好，建议使用批量操作"
            ],
            "expertise": {
                ExpertiseLevel.BEGINNER: [
                    "建议先使用我们的模板和示例论文开始",
                    "您可以使用'帮助'命令获取更多指导"
                ],
                ExpertiseLevel.INTERMEDIATE: [
                    "您已经熟悉基本流程，可以尝试高级功能",
                    "建议使用我们的批量处理功能提高效率"
                ],
                ExpertiseLevel.ADVANCED: [
                    "您是高级用户，可以尝试我们的专家模式",
                    "建议使用API进行自动化操作"
                ],
                ExpertiseLevel.EXPERT: [
                    "您是专家级用户，建议参与我们的Beta测试",
                    "您的反馈对我们非常重要"
                ]
            }
        }

    async def generate_suggestions(
        self,
        current_state: Dict[str, Any],
        user_id: str
    ) -> List[Dict[str, str]]:
        """生成提示建议

        Args:
            current_state: 当前状态
            user_id: 用户ID

        Returns:
            List[Dict[str, str]]: 提示建议列表
        """
        suggestions = []

        # 1. 基于当前状态生成建议
        state_based = self._generate_state_based(current_state)
        suggestions.extend(state_based)

        # 2. 基于用户历史生成建议
        profile = await self.behavior_analyzer.analyze(user_id)
        history_based = self._generate_history_based(profile)
        suggestions.extend(history_based)

        # 3. 基于最佳实践生成建议
        best_practice = self._generate_best_practice(current_state)
        suggestions.extend(best_practice)

        # 排序和过滤
        suggestions = self._rank_and_filter(suggestions)

        return suggestions[:5]  # 返回Top 5

    def _generate_state_based(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """基于当前状态生成建议"""
        suggestions = []

        phase = state.get("phase", "")
        revision_count = state.get("revision_count", 0)
        quality_score = state.get("quality_score", 1.0)

        if phase == "writing" and revision_count > 2:
            suggestions.append({
                "type": "encouragement",
                "message": self._templates["encouragement"][0],
                "priority": "low"
            })

        if quality_score < 0.6:
            suggestions.append({
                "type": "help",
                "message": self._templates["help"][0],
                "priority": "high"
            })

        if state.get("empty_outline", False):
            suggestions.append({
                "type": "help",
                "message": "建议先生成论文大纲，再进行撰写",
                "priority": "high"
            })

        return suggestions

    def _generate_history_based(self, profile: BehaviorProfile) -> List[Dict[str, str]]:
        """基于用户历史生成建议"""
        suggestions = []
        templates = self._templates["expertise"].get(profile.expertise_level, [])

        if templates and profile.total_actions > 5:
            suggestions.append({
                "type": "personalization",
                "message": templates[0],
                "priority": "medium"
            })

        return suggestions

    def _generate_best_practice(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """基于最佳实践生成建议"""
        suggestions = []

        if state.get("missing_citations", False):
            suggestions.append({
                "type": "efficiency",
                "message": "建议在写作前先检索相关文献，可以提高引用质量",
                "priority": "high"
            })

        if state.get("no_structured_outline", False):
            suggestions.append({
                "type": "efficiency",
                "message": "建议使用大纲功能来组织您的论文结构",
                "priority": "medium"
            })

        return suggestions

    def _rank_and_filter(
        self,
        suggestions: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """排序和过滤建议"""
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}

        return sorted(
            suggestions,
            key=lambda x: priority_order.get(x.get("priority", "low"), 2)
        )


# 便捷函数
async def analyze_user_behavior(
    user_id: str,
    actions: List[UserAction]
) -> BehaviorProfile:
    """分析用户行为的便捷函数"""
    analyzer = UserBehaviorAnalyzer()

    for action in actions:
        analyzer.record_action(action)

    return await analyzer.analyze(user_id)


def record_user_action(
    user_id: str,
    action_type: str,
    duration_ms: float,
    success: bool,
    metadata: Optional[Dict[str, Any]] = None
) -> UserAction:
    """记录用户操作的便捷函数"""
    return UserAction(
        timestamp=datetime.now(),
        action_type=action_type,
        duration_ms=duration_ms,
        success=success,
        metadata=metadata or {}
    )