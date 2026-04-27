"""
Personalization模块 - 个性化与长期记忆

包含:
- ForgettingCurveMemory: 遗忘曲线记忆管理
- PreferenceLearner: 用户偏好学习
- SpacedRepetitionSystem: 间隔重复复习
- UserProfileManager: 用户画像管理
- CrossSessionKnowledge: 跨会话知识累积
- UserBehaviorAnalyzer: 用户行为分析
- SmartPromptGenerator: 智能提示生成
"""
from .forgetting_curve_memory import (
    ForgettingCurveMemory,
    MemoryStrength,
    MemoryItem,
    ReviewResult,
    calculate_retention,
    get_review_intervals
)
from .preference_learner import (
    PreferenceLearner,
    PreferenceProfile,
    InteractionRecord,
    create_learner
)
from .spaced_repetition import (
    SpacedRepetitionSystem,
    ReviewQuality,
    ReviewSchedule,
    ReviewSession,
    create_spaced_repetition,
    calculate_next_interval
)
from .user_profile_manager import (
    UserProfileManager,
    UserProfile,
    UserKnowledge,
    create_profile_manager
)
from .cross_session_knowledge import (
    CrossSessionKnowledge,
    KnowledgeEntry,
    SessionContext,
    create_cross_session_knowledge
)
from .behavior_analyzer import (
    UserBehaviorAnalyzer,
    UserAction,
    UserPreferences,
    BehaviorProfile,
    ExpertiseLevel,
    OutputFormat,
    PatternDetector,
    SmartPromptGenerator,
    analyze_user_behavior,
    record_user_action
)

__all__ = [
    # 遗忘曲线记忆
    "ForgettingCurveMemory",
    "MemoryStrength",
    "MemoryItem",
    "ReviewResult",
    "calculate_retention",
    "get_review_intervals",

    # 偏好学习
    "PreferenceLearner",
    "PreferenceProfile",
    "InteractionRecord",
    "create_learner",

    # 间隔重复
    "SpacedRepetitionSystem",
    "ReviewQuality",
    "ReviewSchedule",
    "ReviewSession",
    "create_spaced_repetition",
    "calculate_next_interval",

    # 用户画像
    "UserProfileManager",
    "UserProfile",
    "UserKnowledge",
    "create_profile_manager",

    # 跨会话知识
    "CrossSessionKnowledge",
    "KnowledgeEntry",
    "SessionContext",
    "create_cross_session_knowledge",

    # 用户行为分析
    "UserBehaviorAnalyzer",
    "UserAction",
    "UserPreferences",
    "BehaviorProfile",
    "ExpertiseLevel",
    "OutputFormat",
    "PatternDetector",
    "SmartPromptGenerator",
    "analyze_user_behavior",
    "record_user_action"
]