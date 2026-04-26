"""
遗忘曲线记忆 - Forgetting Curve Memory

基于艾宾浩斯遗忘曲线理论的记忆管理:
- R = e^(-t/S)  (保留度公式)
- 当 R < 0.3 时需要强化记忆
- 复习间隔: [1, 2, 4, 7, 15, 30] 天
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryStrength(Enum):
    """记忆强度等级"""
    TRANSIENT = 1      # 瞬时记忆，很快遗忘
    SHORT = 2          # 短期记忆
    MEDIUM = 3         # 中期记忆
    LONG = 4           # 长期记忆
    PERMANENT = 5      # 永久记忆


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    importance: float  # 1.0-10.0, 重要性
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    strength: float = 1.0  # 初始强度
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def retention(self) -> float:
        """计算当前保留度 R = e^(-elapsed_days / strength)"""
        elapsed = time.time() - self.last_accessed
        elapsed_days = elapsed / (24 * 3600)
        # 强度与重要性相关，范围 [1, 10]
        effective_strength = self.strength * (self.importance / 5.0)
        retention = 2.71828 ** (-elapsed_days / max(effective_strength, 0.1))
        return max(0.0, min(1.0, retention))

    @property
    def needs_reinforcement(self) -> bool:
        """是否需要强化"""
        return self.retention < 0.3

    def get_review_interval_days(self) -> float:
        """获取复习间隔（基于间隔重复算法）"""
        intervals = [1, 2, 4, 7, 15, 30, 60]
        idx = min(self.access_count, len(intervals) - 1)
        return intervals[idx]


@dataclass
class ReviewResult:
    """复习结果"""
    memory_id: str
    was_recalled: bool
    recall_quality: float  # 0-1, 回忆质量
    time_taken: float
    next_review: float


class ForgettingCurveMemory:
    """遗忘曲线记忆管理器

    核心思想：
    1. 记忆条目根据保留度自动衰减
    2. 当保留度低于阈值时触发复习
    3. 复习后更新强度和间隔
    """

    def __init__(self,
                 retention_threshold: float = 0.3,
                 base_strength: float = 5.0):
        """初始化

        Args:
            retention_threshold: 保留度阈值，低于此值需要复习
            base_strength: 基础记忆强度
        """
        self.retention_threshold = retention_threshold
        self.base_strength = base_strength
        self._memory_store: Dict[str, MemoryItem] = {}
        self._review_log: List[ReviewResult] = []

    def add(self,
            content: str,
            importance: float = 5.0,
            metadata: Dict = None) -> MemoryItem:
        """添加记忆条目

        Args:
            content: 记忆内容
            importance: 重要性 (1.0-10.0)
            metadata: 元数据

        Returns:
            MemoryItem: 创建的记忆条目
        """
        import uuid

        item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            importance=importance,
            strength=self.base_strength,
            metadata=metadata or {}
        )

        self._memory_store[item.id] = item
        logger.info(f"添加记忆: {item.id[:8]}, 重要性={importance}")

        return item

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆条目（触发访问时间更新）

        Args:
            memory_id: 记忆ID

        Returns:
            Optional[MemoryItem]: 记忆条目
        """
        item = self._memory_store.get(memory_id)
        if item:
            item.last_accessed = time.time()
            item.access_count += 1
        return item

    def search(self, query: str, top_k: int = 10) -> List[MemoryItem]:
        """搜索记忆

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            List[MemoryItem]: 匹配的记忆条目，按相关性排序
        """
        # 简单的关键词匹配
        query_lower = query.lower()
        matched = []

        for item in self._memory_store.values():
            if query_lower in item.content.lower():
                matched.append((item, item.retention))

        # 按保留度排序（优先召回低保留度的）
        matched.sort(key=lambda x: x[1])
        return [m[0] for m in matched[:top_k]]

    def get_needing_review(self, limit: int = 20) -> List[MemoryItem]:
        """获取需要复习的记忆

        Args:
            limit: 返回数量限制

        Returns:
            List[MemoryItem]: 需要复习的记忆列表
        """
        needing_review = [
            item for item in self._memory_store.values()
            if item.needs_reinforcement
        ]

        # 按保留度升序（最需要复习的在前）
        needing_review.sort(key=lambda x: x.retention)
        return needing_review[:limit]

    def get_upcoming_review(self, hours: int = 24) -> List[MemoryItem]:
        """获取即将到期的复习

        Args:
            hours: 未来多少小时内的复习

        Returns:
            List[MemoryItem]: 即将到期的记忆
        """
        now = time.time()
        future = now + hours * 3600

        upcoming = []
        for item in self._memory_store.values():
            # 估计下次复习时间
            next_review = item.last_accessed + item.get_review_interval_days() * 24 * 3600
            if now <= next_review <= future:
                upcoming.append(item)

        return upcoming

    async def review(self, memory_id: str, recall_quality: float) -> ReviewResult:
        """执行复习

        Args:
            memory_id: 记忆ID
            recall_quality: 回忆质量 (0-1)

        Returns:
            ReviewResult: 复习结果
        """
        start_time = time.time()
        item = self.get(memory_id)

        if not item:
            raise ValueError(f"记忆不存在: {memory_id}")

        was_recalled = recall_quality > 0.3

        # 更新强度
        if was_recalled:
            # 成功回忆：增强强度
            item.strength = min(item.strength * 1.2, 20.0)
        else:
            # 失败回忆：减弱强度
            item.strength = max(item.strength * 0.8, 0.5)

        time_taken = time.time() - start_time

        result = ReviewResult(
            memory_id=memory_id,
            was_recalled=was_recalled,
            recall_quality=recall_quality,
            time_taken=time_taken,
            next_review=time.time() + item.get_review_interval_days() * 24 * 3600
        )

        self._review_log.append(result)
        logger.info(f"复习 {item.id[:8]}: recall={recall_quality:.2f}, new_strength={item.strength:.2f}")

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计

        Returns:
            Dict: 统计信息
        """
        total = len(self._memory_store)
        needing_review = sum(1 for i in self._memory_store.values() if i.needs_reinforcement)

        if total == 0:
            avg_retention = 0.0
            avg_strength = 0.0
        else:
            avg_retention = sum(i.retention for i in self._memory_store.values()) / total
            avg_strength = sum(i.strength for i in self._memory_store.values()) / total

        return {
            "total_memories": total,
            "needing_review": needing_review,
            "avg_retention": avg_retention,
            "avg_strength": avg_strength,
            "review_count": len(self._review_log)
        }

    def clear_old(self, days: int = 90) -> int:
        """清理旧记忆

        Args:
            days: 超过多少天的记忆将被清除

        Returns:
            int: 清除的记忆数量
        """
        cutoff = time.time() - days * 24 * 3600
        to_remove = [
            item_id for item_id, item in self._memory_store.items()
            if item.last_accessed < cutoff and item.strength < 3.0
        ]

        for item_id in to_remove:
            del self._memory_store[item_id]

        logger.info(f"清理了 {len(to_remove)} 条旧记忆")
        return len(to_remove)


# 便捷函数
def calculate_retention(elapsed_days: float, strength: float) -> float:
    """计算保留度

    Args:
        elapsed_days: 经过的天数
        strength: 记忆强度

    Returns:
        float: 保留度 (0-1)
    """
    import math
    return max(0.0, min(1.0, math.exp(-elapsed_days / max(strength, 0.1))))


def get_review_intervals(access_count: int) -> List[int]:
    """获取复习间隔

    Args:
        access_count: 已复习次数

    Returns:
        List[int]: 间隔天数列表
    """
    intervals = [1, 2, 4, 7, 15, 30, 60, 120]
    return intervals[:min(access_count + 1, len(intervals))]