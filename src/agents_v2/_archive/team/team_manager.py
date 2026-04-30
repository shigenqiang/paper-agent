"""团队管理 - 多用户协作支持"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class TeamRole(str, Enum):
    """团队角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    email: str
    role: UserRole = UserRole.MEMBER
    team_ids: Set[str] = field(default_factory=set)
    created_at: str = ""
    last_login: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Team:
    """团队"""
    team_id: str
    name: str
    description: str = ""
    owner_id: str = ""
    member_ids: Set[str] = field(default_factory=set)
    created_at: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        # 确保owner也被添加到member_ids
        if self.owner_id and self.owner_id not in self.member_ids:
            self.member_ids.add(self.owner_id)


@dataclass
class SharedSubscription:
    """共享订阅"""
    subscription_id: str
    team_id: str
    created_by: str
    keywords: List[str]
    channels: List[str]
    frequency: str  # daily, weekly, monthly
    enabled: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class TeamDiscussion:
    """团队讨论"""
    discussion_id: str
    team_id: str
    author_id: str
    paper_id: Optional[str] = None
    title: str = ""
    content: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
            self.updated_at = self.created_at


class TeamManager:
    """
    团队管理器

    功能：
    - 用户管理
    - 团队CRUD
    - 团队成员管理
    - 共享订阅
    - 团队讨论
    """

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._teams: Dict[str, Team] = {}
        self._shared_subscriptions: Dict[str, SharedSubscription] = {}
        self._discussions: Dict[str, TeamDiscussion] = {}

    # ========== 用户管理 ==========

    def create_user(
        self,
        username: str,
        email: str,
        role: UserRole = UserRole.MEMBER
    ) -> User:
        """创建用户"""
        user_id = str(uuid.uuid4())[:8]
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role
        )
        self._users[user_id] = user
        logger.info(f"创建用户: {username} ({user_id})")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def update_user(
        self,
        user_id: str,
        **kwargs
    ) -> Optional[User]:
        """更新用户"""
        user = self._users.get(user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)

        logger.info(f"更新用户: {user_id}")
        return user

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        user = self._users.pop(user_id, None)
        if user:
            # 从所有团队中移除
            for team in self._teams.values():
                team.member_ids.discard(user_id)
            logger.info(f"删除用户: {user_id}")
            return True
        return False

    def list_users(self) -> List[User]:
        """列出所有用户"""
        return list(self._users.values())

    # ========== 团队管理 ==========

    def create_team(
        self,
        name: str,
        owner_id: str,
        description: str = ""
    ) -> Team:
        """创建团队"""
        team_id = str(uuid.uuid4())[:8]
        team = Team(
            team_id=team_id,
            name=name,
            description=description,
            owner_id=owner_id
        )
        team.member_ids.add(owner_id)
        self._teams[team_id] = team

        # 更新用户
        user = self._users.get(owner_id)
        if user:
            user.team_ids.add(team_id)

        logger.info(f"创建团队: {name} ({team_id})")
        return team

    def get_team(self, team_id: str) -> Optional[Team]:
        """获取团队"""
        return self._teams.get(team_id)

    def update_team(
        self,
        team_id: str,
        **kwargs
    ) -> Optional[Team]:
        """更新团队"""
        team = self._teams.get(team_id)
        if not team:
            return None

        for key, value in kwargs.items():
            if hasattr(team, key) and value is not None:
                setattr(team, key, value)

        logger.info(f"更新团队: {team_id}")
        return team

    def delete_team(self, team_id: str) -> bool:
        """删除团队"""
        team = self._teams.pop(team_id, None)
        if team:
            # 从所有成员中移除
            for member_id in team.member_ids:
                user = self._users.get(member_id)
                if user:
                    user.team_ids.discard(team_id)
            logger.info(f"删除团队: {team_id}")
            return True
        return False

    def list_teams(self) -> List[Team]:
        """列出所有团队"""
        return list(self._teams.values())

    # ========== 团队成员管理 ==========

    def add_team_member(
        self,
        team_id: str,
        user_id: str,
        role: TeamRole = TeamRole.MEMBER
    ) -> bool:
        """添加团队成员"""
        team = self._teams.get(team_id)
        user = self._users.get(user_id)
        if not team or not user:
            return False

        team.member_ids.add(user_id)
        user.team_ids.add(team_id)
        logger.info(f"添加成员 {user_id} 到团队 {team_id}")
        return True

    def remove_team_member(self, team_id: str, user_id: str) -> bool:
        """移除团队成员"""
        team = self._teams.get(team_id)
        user = self._users.get(user_id)
        if not team or not user:
            return False

        # 不能移除所有者
        if user_id == team.owner_id:
            return False

        team.member_ids.discard(user_id)
        user.team_ids.discard(team_id)
        logger.info(f"从团队 {team_id} 移除成员 {user_id}")
        return True

    def get_team_members(self, team_id: str) -> List[User]:
        """获取团队成员"""
        team = self._teams.get(team_id)
        if not team:
            return []

        return [self._users[uid] for uid in team.member_ids if uid in self._users]

    def get_user_teams(self, user_id: str) -> List[Team]:
        """获取用户所在团队"""
        user = self._users.get(user_id)
        if not user:
            return []

        return [self._teams[tid] for tid in user.team_ids if tid in self._teams]

    # ========== 共享订阅 ==========

    def create_shared_subscription(
        self,
        team_id: str,
        created_by: str,
        keywords: List[str],
        channels: List[str],
        frequency: str
    ) -> SharedSubscription:
        """创建共享订阅"""
        subscription_id = str(uuid.uuid4())[:8]
        sub = SharedSubscription(
            subscription_id=subscription_id,
            team_id=team_id,
            created_by=created_by,
            keywords=keywords,
            channels=channels,
            frequency=frequency
        )
        self._shared_subscriptions[subscription_id] = sub
        logger.info(f"创建共享订阅: {subscription_id}")
        return sub

    def get_team_subscriptions(self, team_id: str) -> List[SharedSubscription]:
        """获取团队订阅"""
        return [
            sub for sub in self._shared_subscriptions.values()
            if sub.team_id == team_id
        ]

    def delete_shared_subscription(self, subscription_id: str) -> bool:
        """删除共享订阅"""
        sub = self._shared_subscriptions.pop(subscription_id, None)
        return sub is not None

    # ========== 团队讨论 ==========

    def create_discussion(
        self,
        team_id: str,
        author_id: str,
        content: str,
        title: str = "",
        paper_id: Optional[str] = None
    ) -> TeamDiscussion:
        """创建讨论"""
        discussion_id = str(uuid.uuid4())[:8]
        discussion = TeamDiscussion(
            discussion_id=discussion_id,
            team_id=team_id,
            author_id=author_id,
            paper_id=paper_id,
            title=title,
            content=content
        )
        self._discussions[discussion_id] = discussion
        logger.info(f"创建讨论: {discussion_id}")
        return discussion

    def get_discussion(self, discussion_id: str) -> Optional[TeamDiscussion]:
        """获取讨论"""
        return self._discussions.get(discussion_id)

    def get_team_discussions(self, team_id: str) -> List[TeamDiscussion]:
        """获取团队讨论"""
        return [
            d for d in self._discussions.values()
            if d.team_id == team_id
        ]

    # ========== 权限检查 ==========

    def is_team_member(self, team_id: str, user_id: str) -> bool:
        """检查是否是团队成员"""
        team = self._teams.get(team_id)
        if not team:
            return False
        return user_id in team.member_ids

    def is_team_owner(self, team_id: str, user_id: str) -> bool:
        """检查是否是团队所有者"""
        team = self._teams.get(team_id)
        if not team:
            return False
        return user_id == team.owner_id

    def can_manage_team(self, team_id: str, user_id: str) -> bool:
        """检查是否可以管理团队"""
        team = self._teams.get(team_id)
        if not team:
            return False
        # 所有者或管理员可以管理
        return user_id == team.owner_id


# 全局实例
_global_team_manager: Optional[TeamManager] = None


def get_team_manager() -> TeamManager:
    """获取全局团队管理器"""
    global _global_team_manager
    if _global_team_manager is None:
        _global_team_manager = TeamManager()
    return _global_team_manager
