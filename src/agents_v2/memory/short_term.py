"""
短期记忆 - Short Term Memory

职责: 存储当前任务的即时上下文
- 位置: 内存
- 容量: 100-200条消息
- 淘汰: LRU + TTL
- 与 AgentContext 深度绑定
"""
import time
import asyncio
from typing import Any, Dict, List, Optional, Callable
from collections import OrderedDict
from dataclasses import dataclass, field

from .types import MemoryEntry, MemoryType, ImportanceLevel


@dataclass
class ShortTermMemoryConfig:
    """短期记忆配置"""
    max_items: int = 100          # 最大条目数
    ttl_seconds: float = 3600     # 默认1小时过期
    enable_auto_summary: bool = True  # 自动摘要
    summary_trigger_count: int = 20   # 触发摘要的消息数


class ShortTermMemory:
    """
    短期记忆 - 当前任务上下文

    特点:
    - 保存在内存中，任务结束后可选择持久化
    - 基于LRU淘汰策略 + TTL过期
    - 与AgentContext深度绑定
    - 支持自动摘要生成（待集成LLM）
    """

    def __init__(self, config: Optional[ShortTermMemoryConfig] = None):
        self.config = config or ShortTermMemoryConfig()
        self._items: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def add(
        self,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加记忆

        Args:
            key: 记忆键
            value: 记忆值
            tags: 标签列表
            importance: 重要性 (0.0-1.0)
            metadata: 额外元数据
        """
        async with self._lock:
            # 如果已存在，更新值
            if key in self._items:
                item = self._items[key]
                item.content = value
                item.created_at = time.time()
                if tags:
                    item.tags = tags
                if metadata:
                    item.metadata.update(metadata)
                self._items.move_to_end(key)
                return

            # 如果达到容量限制，淘汰最旧的项
            if len(self._items) >= self.config.max_items:
                self._evict_lru()

            # 添加新项
            importance_level = self._compute_importance_level(importance)
            entry = MemoryEntry(
                id=key,
                memory_type=MemoryType.SHORT_TERM,
                content=value,
                importance=importance,
                importance_level=importance_level,
                tags=tags or [],
                metadata=metadata or {}
            )
            self._items[key] = entry

    async def get(
        self,
        key: str,
        default: Any = None,
        update_access: bool = True
    ) -> Any:
        """
        获取记忆

        Args:
            key: 记忆键
            default: 默认值
            update_access: 是否更新访问时间

        Returns:
            记忆值或默认值
        """
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                return default

            # 检查是否过期
            if time.time() - item.created_at > self.config.ttl_seconds:
                del self._items[key]
                return default

            # 更新访问
            if update_access:
                item.access()
                self._items.move_to_end(key)

            return item.content

    async def has(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        async with self._lock:
            if key not in self._items:
                return False

            item = self._items[key]
            if time.time() - item.created_at > self.config.ttl_seconds:
                del self._items[key]
                return False

            return True

    async def remove(self, key: str) -> None:
        """移除记忆"""
        async with self._lock:
            if key in self._items:
                del self._items[key]

    async def clear(self) -> None:
        """清空所有短期记忆"""
        async with self._lock:
            self._items.clear()

    async def keys(self) -> List[str]:
        """获取所有键"""
        async with self._lock:
            return list(self._items.keys())

    async def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        """获取最近的n条记忆"""
        async with self._lock:
            items = list(self._items.values())
            items.reverse()  # 最新的在前
            return items[:n]

    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        在当前上下文搜索

        Args:
            query: 搜索查询（标签或关键词）
            limit: 返回结果数量限制

        Returns:
            匹配的MemoryEntry列表
        """
        async with self._lock:
            results = []

            for item in self._items.values():
                # 标签匹配
                if query in item.tags:
                    results.append(item)
                    continue

                # 关键词匹配
                content_str = str(item.content).lower()
                if query.lower() in content_str:
                    results.append(item)

                if len(results) >= limit:
                    break

            return results

    async def get_context_summary(self) -> str:
        """
        获取上下文字符串（用于给Agent）

        Returns:
            格式化的上下文字符串
        """
        async with self._lock:
            if not self._items:
                return ""

            parts = ["## 当前上下文\n"]
            for key, item in self._items.items():
                parts.append(f"- [{item.memory_type.value}] {key}: {item.content}")

            return "\n".join(parts)

    def should_trigger_summary(self) -> bool:
        """检查是否应该触发摘要生成"""
        return (
            self.config.enable_auto_summary and
            len(self._items) >= self.config.summary_trigger_count
        )

    def _evict_lru(self) -> None:
        """淘汰最近最少使用的项"""
        if not self._items:
            return

        # 找到最旧的项（OrderedDict头部）
        oldest_key = next(iter(self._items))
        del self._items[oldest_key]

    def _compute_importance_level(self, importance: float) -> ImportanceLevel:
        """根据重要性值计算等级"""
        if importance >= 0.9:
            return ImportanceLevel.CRITICAL
        elif importance >= 0.7:
            return ImportanceLevel.HIGH
        elif importance >= 0.4:
            return ImportanceLevel.MEDIUM
        else:
            return ImportanceLevel.LOW

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "size": len(self._items),
            "max_items": self.config.max_items,
            "ttl_seconds": self.config.ttl_seconds,
            "memory_type": MemoryType.SHORT_TERM.value
        }

    def to_dict(self) -> Dict[str, Any]:
        """序列化所有记忆"""
        return {
            key: item.to_dict()
            for key, item in self._items.items()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShortTermMemory":
        """从字典恢复记忆"""
        memory = cls()
        for key, item_data in data.items():
            entry = MemoryEntry(
                id=item_data["id"],
                memory_type=MemoryType.SHORT_TERM,
                content=item_data["content"],
                created_at=item_data.get("created_at", time.time()),
                last_accessed=item_data.get("last_accessed", time.time()),
                access_count=item_data.get("access_count", 0),
                importance=item_data.get("importance", 0.5),
                tags=item_data.get("tags", []),
                metadata=item_data.get("metadata", {})
            )
            memory._items[key] = entry
        return memory
