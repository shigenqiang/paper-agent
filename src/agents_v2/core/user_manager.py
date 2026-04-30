"""
UserManager - 用户会话管理

管理用户会话、用户信息和论文关联
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class UserSession:
    """用户会话"""
    session_id: str
    user_id: str
    created_at: datetime
    last_active: datetime
    metadata: Dict = field(default_factory=dict)

    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """检查会话是否过期"""
        elapsed = (self.last_active - self.created_at).total_seconds()
        return elapsed > timeout_seconds

    def update_activity(self):
        """更新最后活动时间"""
        self.last_active = datetime.now()


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str
    created_at: datetime
    role: str = "user"
    metadata: Dict = field(default_factory=dict)


class UserManager:
    """用户管理器"""

    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.users: Dict[str, User] = {}
        self.user_papers: Dict[str, List[str]] = {}  # user_id -> paper_ids

    def generate_session_id(self) -> str:
        """生成会话ID"""
        return f"sess_{uuid.uuid4().hex[:16]}"

    def generate_user_id(self) -> str:
        """生成用户ID"""
        return f"user_{uuid.uuid4().hex[:16]}"

    async def create_user(self, username: str, email: str, role: str = "user") -> User:
        """创建用户"""
        user_id = self.generate_user_id()
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            created_at=datetime.now(),
            role=role
        )
        self.users[user_id] = user
        self.user_papers[user_id] = []
        return user

    async def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self.users.get(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    async def create_session(self, user_id: str) -> UserSession:
        """创建用户会话"""
        session_id = self.generate_session_id()
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        self.sessions[session_id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session and not session.is_expired():
            session.update_activity()
            return session
        elif session:
            # 删除过期会话
            del self.sessions[session_id]
        return None

    async def delete_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    async def list_user_papers(self, user_id: str) -> List[str]:
        """列出用户的论文"""
        return self.user_papers.get(user_id, [])

    async def add_paper_to_user(self, user_id: str, paper_id: str):
        """将论文关联到用户"""
        if user_id not in self.user_papers:
            self.user_papers[user_id] = []
        if paper_id not in self.user_papers[user_id]:
            self.user_papers[user_id].append(paper_id)

    async def remove_paper_from_user(self, user_id: str, paper_id: str):
        """从用户移除论文关联"""
        if user_id in self.user_papers and paper_id in self.user_papers[user_id]:
            self.user_papers[user_id].remove(paper_id)

    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        expired = [
            sid for sid, sess in self.sessions.items()
            if sess.is_expired()
        ]
        for sid in expired:
            del self.sessions[sid]


# 全局用户管理器实例
_user_manager: Optional[UserManager] = None


def get_user_manager() -> UserManager:
    """获取全局用户管理器"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager
