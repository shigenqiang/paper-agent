"""
Search Cache Manager - 搜索结果缓存管理器

减少重复请求，提高响应速度，间接缓解限流压力。
"""

from src.agents_v2.logging_config import get_logging_logger

import asyncio
import hashlib
import json

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import OrderedDict
import pickle

logger = get_logging_logger(__name__)


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    ttl_seconds: int = 3600          # 默认1小时
    max_entries: int = 1000            # 最大条目数
    cache_dir: Optional[str] = None   # 持久化目录


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    timestamp: float
    ttl: int
    hit_count: int = 0

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class SearchCache:
    """LRU缓存实现"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def _make_key(self, source: str, query: str, max_results: int) -> str:
        """生成缓存键"""
        raw = f"{source}:{query.lower().strip()}:{max_results}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _hash_response(self, response) -> str:
        """对响应进行哈希"""
        try:
            data = {
                "total": response.total if hasattr(response, 'total') else 0,
                "count": len(response.results) if hasattr(response, 'results') else 0,
                "source": response.source if hasattr(response, 'source') else "",
            }
            return hashlib.md5(json.dumps(data).encode()).hexdigest()
        except Exception:
            return hashlib.md5(str(response).encode()).hexdigest()

    async def get(self, source: str, query: str, max_results: int) -> Optional[Any]:
        """获取缓存"""
        key = self._make_key(source, query, max_results)

        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    entry.hit_count += 1
                    self._cache.move_to_end(key)  # LRU
                    self._stats["hits"] += 1
                    logger.debug(f"Cache hit: {key[:8]}...")
                    return entry.value
                else:
                    del self._cache[key]

            self._stats["misses"] += 1
            return None

    async def set(self, source: str, query: str, max_results: int, value: Any, ttl: int = None):
        """设置缓存"""
        key = self._make_key(source, query, max_results)
        ttl = ttl or self.config.ttl_seconds

        async with self._lock:
            # LRU淘汰
            if len(self._cache) >= self.config.max_entries and key not in self._cache:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1

            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )
            self._cache.move_to_end(key)

    async def invalidate(self, source: str = None, pattern: str = None):
        """使缓存失效"""
        async with self._lock:
            if source:
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(source)]
                for key in keys_to_remove:
                    del self._cache[key]
            elif pattern:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]

    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self.config.max_entries,
            "hit_rate": round(hit_rate * 100, 2),
        }

    async def persist(self):
        """持久化到磁盘"""
        if not self.config.cache_dir:
            return

        import os
        try:
            os.makedirs(self.config.cache_dir, exist_ok=True)
            cache_file = os.path.join(self.config.cache_dir, "search_cache.pkl")

            async with self._lock:
                data = {k: v for k, v in self._cache.items() if not v.is_expired()}

            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)

            logger.info(f"Cache persisted: {len(data)} entries")

        except Exception as e:
            logger.error(f"Cache persist failed: {e}")

    async def restore(self):
        """从磁盘恢复"""
        if not self.config.cache_dir:
            return

        import os
        try:
            cache_file = os.path.join(self.config.cache_dir, "search_cache.pkl")
            if not os.path.exists(cache_file):
                return

            with open(cache_file, 'rb') as f:
                data = pickle.load(f)

            async with self._lock:
                for key, entry in data.items():
                    if not entry.is_expired():
                        self._cache[key] = entry

            logger.info(f"Cache restored: {len(self._cache)} entries")

        except Exception as e:
            logger.error(f"Cache restore failed: {e}")


class SearchCacheManager:
    """搜索缓存管理器"""

    _instance = None

    def __new__(cls, config: CacheConfig = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: CacheConfig = None):
        if self._initialized:
            return
        self._initialized = True
        self.config = config or CacheConfig()
        self.cache = SearchCache(self.config)

    async def get_or_fetch(
        self,
        source: str,
        query: str,
        max_results: int,
        fetch_func
    ) -> Any:
        """获取缓存或执行查询

        Args:
            source: 搜索源名称
            query: 查询内容
            max_results: 最大结果数
            fetch_func: 获取数据的异步函数

        Returns:
            搜索结果
        """
        # 尝试从缓存获取
        cached = await self.cache.get(source, query, max_results)
        if cached is not None:
            return cached

        # 执行查询
        result = await fetch_func()

        # 缓存结果
        if result:
            await self.cache.set(source, query, max_results, result)

        return result

    async def invalidate_source(self, source: str):
        """使某源的所有缓存失效"""
        await self.cache.invalidate(source=source)

    async def clear_all(self):
        """清空所有缓存"""
        await self.cache.clear()

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        return self.cache.get_stats()


# 全局实例
_cache_manager: Optional[SearchCacheManager] = None


def get_cache_manager(config: CacheConfig = None) -> SearchCacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = SearchCacheManager(config)
    return _cache_manager


# 装饰器方式使用缓存
def cached_search(source: str, ttl_seconds: int = 3600):
    """缓存装饰器"""
    def decorator(func):
        async def wrapper(self, query, max_results, *args, **kwargs):
            cache = get_cache_manager()

            async def fetch():
                return await func(self, query, max_results, *args, **kwargs)

            return await cache.get_or_fetch(source, query, max_results, fetch)

        return wrapper
    return decorator