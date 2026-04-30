"""
用户画像管理器 - User Profile Manager

管理用户画像的CRUD操作:
- 基本信息
- 偏好设置
- 关联的记忆和知识
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .preference_learner import PreferenceProfile


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    name: str = ""
    email: str = ""
    role: str = "researcher"  # researcher/student/teacher
    institution: str = ""
    research_fields: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    session_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_activity(self):
        """更新活跃时间"""
        self.last_active = time.time()
        self.session_count += 1


@dataclass
class UserKnowledge:
    """用户知识记录"""
    user_id: str
    topic: str
    expertise_level: float = 0.0  # 0-1
    last_demonstrated: float = field(default_factory=time.time)
    evidence_count: int = 0
    sources: List[str] = field(default_factory=list)


class UserProfileManager:
    """用户画像管理器

    支持:
    - 用户CRUD
    - 偏好存储
    - 知识追踪
    """

    def __init__(self, storage_path: str = None):
        """初始化

        Args:
            storage_path: 可选的存储路径
        """
        self.storage_path = storage_path
        self._profiles: Dict[str, UserProfile] = {}
        self._user_knowledge: Dict[str, Dict[str, UserKnowledge]] = {}  # user_id -> topic -> knowledge
        self._load_profiles()

    def _load_profiles(self):
        """加载存储的用户画像"""
        if self.storage_path:
            try:
                import json
                import os
                if os.path.exists(self.storage_path):
                    with open(self.storage_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for profile_data in data.get("profiles", []):
                            profile = UserProfile(**profile_data)
                            self._profiles[profile.user_id] = profile
                    logger.info(f"加载了 {len(self._profiles)} 个用户画像")
            except Exception as e:
                logger.warning(f"加载用户画像失败: {e}")

    def _save_profiles(self):
        """保存用户画像到存储"""
        if not self.storage_path:
            return

        try:
            import json
            import os
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

            data = {
                "profiles": [
                    {
                        "user_id": p.user_id,
                        "name": p.name,
                        "email": p.email,
                        "role": p.role,
                        "institution": p.institution,
                        "research_fields": p.research_fields,
                        "preferences": p.preferences,
                        "created_at": p.created_at,
                        "last_active": p.last_active,
                        "session_count": p.session_count,
                        "metadata": p.metadata
                    }
                    for p in self._profiles.values()
                ]
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"保存了 {len(self._profiles)} 个用户画像")
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")

    def create_profile(self,
                       user_id: str,
                       name: str = "",
                       email: str = "",
                       role: str = "researcher",
                       **kwargs) -> UserProfile:
        """创建用户画像

        Args:
            user_id: 用户ID
            name: 姓名
            email: 邮箱
            role: 角色
            **kwargs: 其他字段

        Returns:
            UserProfile: 创建的画像
        """
        if user_id in self._profiles:
            logger.warning(f"用户 {user_id} 已存在，将更新")

        profile = UserProfile(
            user_id=user_id,
            name=name,
            email=email,
            role=role,
            **kwargs
        )

        self._profiles[user_id] = profile
        self._user_knowledge[user_id] = {}
        self._save_profiles()

        logger.info(f"创建用户画像: {user_id}")
        return profile

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像

        Args:
            user_id: 用户ID

        Returns:
            Optional[UserProfile]: 用户画像
        """
        profile = self._profiles.get(user_id)
        if profile:
            profile.update_activity()
        return profile

    def update_profile(self, user_id: str, **updates) -> Optional[UserProfile]:
        """更新用户画像

        Args:
            user_id: 用户ID
            **updates: 要更新的字段

        Returns:
            Optional[UserProfile]: 更新后的画像
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return None

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        self._save_profiles()
        logger.info(f"更新用户画像: {user_id}")
        return profile

    def delete_profile(self, user_id: str) -> bool:
        """删除用户画像

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否成功
        """
        if user_id in self._profiles:
            del self._profiles[user_id]
            if user_id in self._user_knowledge:
                del self._user_knowledge[user_id]
            self._save_profiles()
            logger.info(f"删除用户画像: {user_id}")
            return True
        return False

    def set_preference(self, user_id: str, key: str, value: Any):
        """设置用户偏好

        Args:
            user_id: 用户ID
            key: 偏好键
            value: 偏好值
        """
        profile = self.get_profile(user_id)
        if profile:
            profile.preferences[key] = value
            self._save_profiles()

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """获取用户偏好

        Args:
            user_id: 用户ID
            key: 偏好键
            default: 默认值

        Returns:
            Any: 偏好值
        """
        profile = self._profiles.get(user_id)
        if profile:
            return profile.preferences.get(key, default)
        return default

    def update_knowledge(self,
                        user_id: str,
                        topic: str,
                        expertise_level: float,
                        source: str = ""):
        """更新用户知识

        Args:
            user_id: 用户ID
            topic: 主题
            expertise_level: 专长级别
            source: 来源
        """
        if user_id not in self._user_knowledge:
            self._user_knowledge[user_id] = {}

        knowledge = self._user_knowledge[user_id].get(topic)

        if knowledge:
            # 更新已有知识
            knowledge.expertise_level = (
                knowledge.expertise_level * knowledge.evidence_count + expertise_level
            ) / (knowledge.evidence_count + 1)
            knowledge.last_demonstrated = time.time()
            knowledge.evidence_count += 1
            if source and source not in knowledge.sources:
                knowledge.sources.append(source)
        else:
            # 创建新知识
            self._user_knowledge[user_id][topic] = UserKnowledge(
                user_id=user_id,
                topic=topic,
                expertise_level=expertise_level,
                sources=[source] if source else []
            )

    def get_knowledge(self, user_id: str, topic: str) -> Optional[UserKnowledge]:
        """获取用户知识

        Args:
            user_id: 用户ID
            topic: 主题

        Returns:
            Optional[UserKnowledge]: 用户知识
        """
        return self._user_knowledge.get(user_id, {}).get(topic)

    def get_user_topics(self, user_id: str) -> List[UserKnowledge]:
        """获取用户的主题知识列表

        Args:
            user_id: 用户ID

        Returns:
            List[UserKnowledge]: 主题知识列表
        """
        knowledge_map = self._user_knowledge.get(user_id, {})
        topics = list(knowledge_map.values())
        topics.sort(key=lambda x: x.expertise_level, reverse=True)
        return topics

    def list_profiles(self) -> List[UserProfile]:
        """列出所有用户画像

        Returns:
            List[UserProfile]: 用户画像列表
        """
        return list(self._profiles.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        total_users = len(self._profiles)

        role_counts = {}
        for profile in self._profiles.values():
            role_counts[profile.role] = role_counts.get(profile.role, 0) + 1

        total_knowledge = sum(
            len(topics) for topics in self._user_knowledge.values()
        )

        return {
            "total_users": total_users,
            "role_distribution": role_counts,
            "total_knowledge_topics": total_knowledge
        }


# 便捷函数
def create_profile_manager(storage_path: str = None) -> UserProfileManager:
    """创建用户画像管理器"""
    return UserProfileManager(storage_path=storage_path)