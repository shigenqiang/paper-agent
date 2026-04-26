"""
分层记忆系统 - Hierarchical Memory System

提供:
1. ShortTermMemory: 短期记忆，当前任务上下文
2. LongTermMemory: 长期记忆，跨任务持久化
3. HierarchicalMemory: 统一接口
"""
import time
import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryItem:
    """记忆条目"""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)

    def access(self):
        """记录访问"""
        self.access_count += 1
        self.last_access = time.time()

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "access_count": self.access_count,
            "last_access": self.last_access
        }


class ShortTermMemory:
    """
    短期记忆 - 当前任务上下文

    特点:
    - 保存在内存中，任务结束后清空
    - 基于LRU淘汰策略
    - 容量限制
    """

    def __init__(self, max_items: int = 100, ttl: float = 3600):
        self.max_items = max_items
        self.ttl = ttl  # 默认1小时过期
        self.items: Dict[str, MemoryItem] = {}

    def add(self, key: str, value: Any, tags: Optional[List[str]] = None) -> None:
        """
        添加记忆

        Args:
            key: 记忆键
            value: 记忆值
            tags: 标签列表
        """
        # 如果已存在，更新值
        if key in self.items:
            item = self.items[key]
            item.value = value
            item.timestamp = time.time()
            if tags:
                item.tags = tags
            return

        # 如果达到容量限制，淘汰最旧的项
        if len(self.items) >= self.max_items:
            self._evict_lru()

        # 添加新项
        self.items[key] = MemoryItem(
            key=key,
            value=value,
            tags=tags or []
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取记忆

        Args:
            key: 记忆键
            default: 默认值

        Returns:
            记忆值或默认值
        """
        item = self.items.get(key)
        if item is None:
            return default

        # 检查是否过期
        if time.time() - item.timestamp > self.ttl:
            del self.items[key]
            return default

        # 记录访问
        item.access()
        return item.value

    def has(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        if key not in self.items:
            return False

        item = self.items[key]
        if time.time() - item.timestamp > self.ttl:
            del self.items[key]
            return False

        return True

    def remove(self, key: str) -> None:
        """移除记忆"""
        if key in self.items:
            del self.items[key]

    def clear(self) -> None:
        """清空所有短期记忆"""
        self.items.clear()

    def keys(self) -> List[str]:
        """获取所有键"""
        return list(self.items.keys())

    def _evict_lru(self) -> None:
        """淘汰最近最少使用的项"""
        if not self.items:
            return

        # 找到访问时间最早的项
        oldest_key = min(
            self.items.keys(),
            key=lambda k: self.items[k].last_access
        )
        del self.items[oldest_key]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "size": len(self.items),
            "max_items": self.max_items,
            "ttl": self.ttl
        }


class LongTermMemory:
    """
    长期记忆 - 跨任务持久化

    特点:
    - 持久化到磁盘
    - 支持检索
    - 标签分类
    """

    def __init__(self, storage_path: str = ".memory"):
        self.storage_path = storage_path
        self._index_path = os.path.join(storage_path, "index.json")
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """确保存储目录存在"""
        os.makedirs(self.storage_path, exist_ok=True)

    def _get_item_path(self, key: str) -> str:
        """获取项的存储路径"""
        # 使用hash避免文件系统不支持的字符
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.storage_path, f"{key_hash}.json")

    def _load_index(self) -> Dict[str, Dict]:
        """加载索引"""
        if not os.path.exists(self._index_path):
            return {}

        try:
            with open(self._index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_index(self, index: Dict[str, Dict]) -> None:
        """保存索引"""
        try:
            with open(self._index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def store(
        self,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        存储到长期记忆

        Args:
            key: 记忆键
            value: 记忆值
            tags: 标签列表
            metadata: 额外元数据
        """
        item_path = self._get_item_path(key)

        item_data = {
            "key": key,
            "value": value,
            "timestamp": time.time(),
            "tags": tags or [],
            "metadata": metadata or {}
        }

        # 保存数据
        with open(item_path, 'w', encoding='utf-8') as f:
            json.dump(item_data, f, ensure_ascii=False, indent=2)

        # 更新索引
        index = self._load_index()
        index[key] = {
            "path": item_path,
            "timestamp": time.time(),
            "tags": tags or [],
            "size": os.path.getsize(item_path)
        }
        self._save_index(index)

    def recall(self, key: str) -> Optional[Any]:
        """
        检索记忆

        Args:
            key: 记忆键

        Returns:
            记忆值或None
        """
        item_path = self._get_item_path(key)

        if not os.path.exists(item_path):
            return None

        try:
            with open(item_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("value")
        except Exception:
            return None

    def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """
        搜索记忆

        Args:
            query: 搜索查询（标签或关键词）
            limit: 返回结果数量限制

        Returns:
            匹配的MemoryItem列表
        """
        index = self._load_index()
        results = []

        for key, info in index.items():
            # 标签匹配
            if query in info.get("tags", []):
                value = self.recall(key)
                if value:
                    results.append(MemoryItem(
                        key=key,
                        value=value,
                        tags=info.get("tags", [])
                    ))

            if len(results) >= limit:
                break

        return results

    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[MemoryItem]:
        """
        按标签搜索

        Args:
            tags: 标签列表
            limit: 返回结果数量限制

        Returns:
            匹配的MemoryItem列表
        """
        index = self._load_index()
        results = []

        for key, info in index.items():
            item_tags = info.get("tags", [])
            if any(tag in item_tags for tag in tags):
                value = self.recall(key)
                if value:
                    results.append(MemoryItem(
                        key=key,
                        value=value,
                        tags=item_tags
                    ))

            if len(results) >= limit:
                break

        return results

    def delete(self, key: str) -> bool:
        """
        删除记忆

        Args:
            key: 记忆键

        Returns:
            是否成功删除
        """
        item_path = self._get_item_path(key)

        if os.path.exists(item_path):
            os.remove(item_path)

            # 更新索引
            index = self._load_index()
            if key in index:
                del index[key]
                self._save_index(index)

            return True

        return False

    def list_all(self) -> List[str]:
        """列出所有记忆键"""
        index = self._load_index()
        return list(index.keys())

    def clear(self) -> None:
        """清空所有长期记忆"""
        import shutil
        if os.path.exists(self.storage_path):
            shutil.rmtree(self.storage_path)
        self._ensure_storage()


class HierarchicalMemory:
    """
    分层记忆系统 - 统一接口

    组合短期记忆和长期记忆:
    - 短期: 当前任务上下文，容量有限
    - 长期: 跨任务持久化，支持检索
    """

    def __init__(
        self,
        short_term_capacity: int = 100,
        long_term_path: str = ".memory"
    ):
        self.short_term = ShortTermMemory(max_items=short_term_capacity)
        self.long_term = LongTermMemory(storage_path=long_term_path)

    def remember(self, key: str, value: Any, tags: Optional[List[str]] = None, persist: bool = False):
        """
        存储记忆

        Args:
            key: 记忆键
            value: 记忆值
            tags: 标签
            persist: 是否持久化到长期记忆
        """
        self.short_term.add(key, value, tags)

        if persist:
            self.long_term.store(key, value, tags)

    def recall(self, key: str, default: Any = None) -> Any:
        """
        检索记忆

        先查短期记忆，再查长期记忆
        """
        # 先查短期记忆
        value = self.short_term.get(key)
        if value is not None:
            return value

        # 再查长期记忆
        value = self.long_term.recall(key)
        if value is not None:
            # 如果在长期记忆找到，升级到短期记忆
            self.short_term.add(key, value)
            return value

        return default

    def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """
        搜索记忆

        仅在长期记忆中搜索
        """
        return self.long_term.search(query, limit)

    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "short_term_stats": self.short_term.get_stats(),
            "long_term_count": len(self.long_term.list_all()),
            "recent_keys": self.short_term.keys()[-10:]
        }
