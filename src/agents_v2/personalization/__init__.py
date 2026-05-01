"""
个性化模块 - Personalization

提供用户偏好学习和画像管理功能。
"""
from .preference_learner import (
    PreferenceLearner,
    PreferenceProfile,
    InteractionRecord,
)
from .user_profile_manager import (
    UserProfileManager,
    UserProfile,
    UserKnowledge,
)

__all__ = [
    "PreferenceLearner",
    "PreferenceProfile",
    "InteractionRecord",
    "UserProfileManager",
    "UserProfile",
    "UserKnowledge",
]
