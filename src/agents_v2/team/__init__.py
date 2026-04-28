"""团队管理模块 - 多用户协作支持"""
from .team_manager import (
    UserRole,
    TeamRole,
    User,
    Team,
    SharedSubscription,
    TeamDiscussion,
    TeamManager,
    get_team_manager
)

__all__ = [
    "UserRole",
    "TeamRole",
    "User",
    "Team",
    "SharedSubscription",
    "TeamDiscussion",
    "TeamManager",
    "get_team_manager",
]
