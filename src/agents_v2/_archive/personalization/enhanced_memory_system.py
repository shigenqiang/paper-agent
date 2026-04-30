"""
增强记忆系统 - Enhanced Memory System

整合遗忘曲线、用户偏好学习和跨会话知识累积，
提供统一的个性化记忆管理接口。

阶段1-Week3: 记忆系统优化
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import asyncio

from .forgetting_curve_memory import ForgettingCurveMemory, MemoryItem
from .preference_learner import PreferenceLearner, PreferenceProfile
from .user_profile_manager import UserProfileManager, UserProfile
from .cross_session_knowledge import CrossSessionKnowledge

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    """记忆上下文"""
    user_id: str
    session_id: str
    query: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonalizedResponse:
    """个性化响应"""
    content: str
    style: str  # 写作风格
    depth: str  # 深度
    relevant_memories: List[MemoryItem]
    user_preferences: PreferenceProfile
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedMemorySystem:
    """增强记忆系统

    核心功能：
    1. 遗忘曲线记忆管理
    2. 用户偏好学习
    3. 跨会话知识累积
    4. 个性化推荐
    5. 智能复习提醒
    """

    def __init__(
        self,
        storage_path: str = ".memory",
        enable_forgetting_curve: bool = True,
        enable_preference_learning: bool = True
    ):
        """初始化增强记忆系统

        Args:
            storage_path: 存储路径
            enable_forgetting_curve: 是否启用遗忘曲线
            enable_preference_learning: 是否启用偏好学习
        """
        self.storage_path = storage_path
        self.enable_forgetting_curve = enable_forgetting_curve
        self.enable_preference_learning = enable_preference_learning

        # 初始化组件
        self.forgetting_memory = ForgettingCurveMemory() if enable_forgetting_curve else None
        self.profile_manager = UserProfileManager(storage_path=f"{storage_path}/profiles.json")
        self.cross_session = CrossSessionKnowledge()

        # 用户偏好学习器缓存
        self._preference_learners: Dict[str, PreferenceLearner] = {}

        logger.info("增强记忆系统初始化完成")

    def get_or_create_learner(self, user_id: str) -> PreferenceLearner:
        """获取或创建偏好学习器

        Args:
            user_id: 用户ID

        Returns:
            PreferenceLearner: 偏好学习器
        """
        if user_id not in self._preference_learners:
            self._preference_learners[user_id] = PreferenceLearner(user_id=user_id)
        return self._preference_learners[user_id]

    async def remember(
        self,
        user_id: str,
        content: str,
        importance: float = 5.0,
        context: Optional[MemoryContext] = None
    ) -> MemoryItem:
        """记住内容

        Args:
            user_id: 用户ID
            content: 内容
            importance: 重要性 (1-10)
            context: 上下文

        Returns:
            MemoryItem: 记忆条目
        """
        # 确保用户画像存在
        profile = self.profile_manager.get_profile(user_id)
        if not profile:
            profile = self.profile_manager.create_profile(user_id)

        # 添加到遗忘曲线记忆
        memory_item = None
        if self.forgetting_memory:
            metadata = {
                "user_id": user_id,
                "context": context.__dict__ if context else {}
            }
            memory_item = self.forgetting_memory.add(
                content=content,
                importance=importance,
                metadata=metadata
            )

        # 添加到跨会话知识
        if context:
            await self.cross_session.add_knowledge(
                user_id=user_id,
                session_id=context.session_id,
                content=content,
                metadata={"importance": importance}
            )

        logger.info(f"用户 {user_id} 记住内容: {content[:50]}...")
        return memory_item

    async def recall(
        self,
        user_id: str,
        query: str,
        top_k: int = 10,
        min_retention: float = 0.3
    ) -> List[MemoryItem]:
        """回忆相关内容

        Args:
            user_id: 用户ID
            query: 查询
            top_k: 返回数量
            min_retention: 最小保留度

        Returns:
            List[MemoryItem]: 相关记忆列表
        """
        if not self.forgetting_memory:
            return []

        # 搜索记忆
        memories = self.forgetting_memory.search(query, top_k=top_k * 2)

        # 过滤低保留度的记忆
        filtered = [
            m for m in memories
            if m.retention >= min_retention and
            m.metadata.get("user_id") == user_id
        ]

        # 按保留度和重要性排序
        filtered.sort(
            key=lambda m: m.retention * m.importance,
            reverse=True
        )

        return filtered[:top_k]

    async def get_personalized_response(
        self,
        user_id: str,
        query: str,
        base_response: str,
        context: Optional[MemoryContext] = None
    ) -> PersonalizedResponse:
        """获取个性化响应

        Args:
            user_id: 用户ID
            query: 查询
            base_response: 基础响应
            context: 上下文

        Returns:
            PersonalizedResponse: 个性化响应
        """
        # 获取用户偏好
        learner = self.get_or_create_learner(user_id)
        preferences = learner.build_profile()

        # 回忆相关记忆
        relevant_memories = await self.recall(user_id, query, top_k=5)

        # 根据偏好调整响应
        adjusted_response = await self._adjust_response_style(
            base_response,
            preferences,
            relevant_memories
        )

        # 计算置信度
        confidence = self._calculate_confidence(preferences, relevant_memories)

        return PersonalizedResponse(
            content=adjusted_response,
            style=preferences.writing_style,
            depth=preferences.depth_preference,
            relevant_memories=relevant_memories,
            user_preferences=preferences,
            confidence=confidence,
            metadata={
                "query": query,
                "memory_count": len(relevant_memories),
                "timestamp": time.time()
            }
        )

    async def _adjust_response_style(
        self,
        response: str,
        preferences: PreferenceProfile,
        memories: List[MemoryItem]
    ) -> str:
        """根据偏好调整响应风格

        Args:
            response: 原始响应
            preferences: 用户偏好
            memories: 相关记忆

        Returns:
            str: 调整后的响应
        """
        adjusted = response

        # 根据写作风格调整
        if preferences.writing_style == "concise":
            # 简化响应（移除冗余内容）
            lines = adjusted.split('\n')
            # 保留关键信息
            adjusted = '\n'.join([
                line for line in lines
                if line.strip() and not line.startswith('例如') and not line.startswith('比如')
            ])
        elif preferences.writing_style == "detailed":
            # 添加更多细节（如果有相关记忆）
            if memories:
                memory_context = "\n\n相关背景：\n"
                for i, mem in enumerate(memories[:2], 1):
                    memory_context += f"{i}. {mem.content[:100]}...\n"
                adjusted = adjusted + memory_context

        # 根据深度偏好调整
        if preferences.depth_preference == "shallow":
            # 提取摘要
            lines = adjusted.split('\n')
            adjusted = '\n'.join(lines[:5])  # 只保留前5行
        elif preferences.depth_preference == "deep":
            # 保持完整内容
            pass

        return adjusted

    def _calculate_confidence(
        self,
        preferences: PreferenceProfile,
        memories: List[MemoryItem]
    ) -> float:
        """计算个性化置信度

        Args:
            preferences: 用户偏好
            memories: 相关记忆

        Returns:
            float: 置信度 (0-1)
        """
        # 基于偏好置信度
        pref_confidence = sum(preferences.confidence.values()) / max(len(preferences.confidence), 1)

        # 基于记忆质量
        if memories:
            avg_retention = sum(m.retention for m in memories) / len(memories)
            memory_confidence = avg_retention
        else:
            memory_confidence = 0.5

        # 综合置信度
        return (pref_confidence * 0.6 + memory_confidence * 0.4)

    async def record_interaction(
        self,
        user_id: str,
        interaction_type: str,
        content: str,
        outcome: str,
        metadata: Optional[Dict] = None
    ):
        """记录用户交互

        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            content: 内容
            outcome: 结果
            metadata: 元数据
        """
        if not self.enable_preference_learning:
            return

        learner = self.get_or_create_learner(user_id)
        learner.record_interaction(
            interaction_type=interaction_type,
            content=content,
            outcome=outcome,
            metadata=metadata or {}
        )

        logger.debug(f"记录交互: {user_id} - {interaction_type} - {outcome}")

    async def get_review_reminders(
        self,
        user_id: str,
        hours: int = 24
    ) -> List[MemoryItem]:
        """获取复习提醒

        Args:
            user_id: 用户ID
            hours: 未来多少小时内

        Returns:
            List[MemoryItem]: 需要复习的记忆
        """
        if not self.forgetting_memory:
            return []

        # 获取需要复习的记忆
        needing_review = self.forgetting_memory.get_needing_review(limit=20)

        # 过滤用户的记忆
        user_memories = [
            m for m in needing_review
            if m.metadata.get("user_id") == user_id
        ]

        # 获取即将到期的复习
        upcoming = self.forgetting_memory.get_upcoming_review(hours=hours)
        user_upcoming = [
            m for m in upcoming
            if m.metadata.get("user_id") == user_id
        ]

        # 合并并去重
        all_reviews = {m.id: m for m in user_memories + user_upcoming}

        return list(all_reviews.values())

    async def optimize_memory(self, user_id: str) -> Dict[str, Any]:
        """优化用户记忆

        清理旧记忆、强化重要记忆

        Args:
            user_id: 用户ID

        Returns:
            Dict: 优化结果
        """
        if not self.forgetting_memory:
            return {"status": "disabled"}

        # 清理90天以上的低强度记忆
        cleared = self.forgetting_memory.clear_old(days=90)

        # 获取需要强化的记忆
        needing_review = await self.get_review_reminders(user_id, hours=24)

        return {
            "cleared_count": cleared,
            "needing_review_count": len(needing_review),
            "status": "optimized"
        }

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息

        Args:
            user_id: 用户ID

        Returns:
            Dict: 统计信息
        """
        stats = {}

        # 用户画像信息
        profile = self.profile_manager.get_profile(user_id)
        if profile:
            stats["profile"] = {
                "name": profile.name,
                "role": profile.role,
                "session_count": profile.session_count,
                "research_fields": profile.research_fields
            }

        # 记忆统计
        if self.forgetting_memory:
            memory_stats = self.forgetting_memory.get_stats()
            stats["memory"] = memory_stats

        # 偏好统计
        if user_id in self._preference_learners:
            learner = self._preference_learners[user_id]
            pref_stats = learner.get_stats()
            stats["preferences"] = pref_stats

        return stats

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """导出用户数据

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户数据
        """
        data = {
            "user_id": user_id,
            "exported_at": time.time(),
            "profile": None,
            "memories": [],
            "preferences": None,
            "knowledge": []
        }

        # 导出画像
        profile = self.profile_manager.get_profile(user_id)
        if profile:
            data["profile"] = {
                "name": profile.name,
                "email": profile.email,
                "role": profile.role,
                "research_fields": profile.research_fields,
                "preferences": profile.preferences
            }

        # 导出记忆
        if self.forgetting_memory:
            all_memories = [
                m for m in self.forgetting_memory._memory_store.values()
                if m.metadata.get("user_id") == user_id
            ]
            data["memories"] = [
                {
                    "content": m.content,
                    "importance": m.importance,
                    "retention": m.retention,
                    "created_at": m.created_at
                }
                for m in all_memories
            ]

        # 导出偏好
        if user_id in self._preference_learners:
            learner = self._preference_learners[user_id]
            profile = learner.build_profile()
            data["preferences"] = {
                "writing_style": profile.writing_style,
                "citation_format": profile.citation_format,
                "depth_preference": profile.depth_preference,
                "topics": profile.topics,
                "confidence": profile.confidence
            }

        return data


# 便捷函数
def create_enhanced_memory_system(
    storage_path: str = ".memory",
    enable_all: bool = True
) -> EnhancedMemorySystem:
    """创建增强记忆系统

    Args:
        storage_path: 存储路径
        enable_all: 是否启用所有功能

    Returns:
        EnhancedMemorySystem: 增强记忆系统
    """
    return EnhancedMemorySystem(
        storage_path=storage_path,
        enable_forgetting_curve=enable_all,
        enable_preference_learning=enable_all
    )
