"""搜索结果缓存"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from loguru import logger


# TTL 配置（秒）
_DEFAULT_TTL = 86400       # 24 小时
_DOI_TTL = 604800          # 7 天
_ARXIV_TTL = 21600         # 6 小时


class SearchCache:
    """搜索结果缓存（基于内存 + 可选 JSONStorage 持久化）"""

    def __init__(self, storage: Any | None = None, default_ttl: int = _DEFAULT_TTL):
        self.storage = storage
        self.default_ttl = default_ttl
        self._memory_cache: dict[str, tuple[float, Any]] = {}

    @staticmethod
    def make_key(
        query: str,
        sources: list[str],
        limit: int,
        year_from: int | None = None,
        year_to: int | None = None,
        field: str = "all",
        offset: int = 0,
    ) -> str:
        """生成缓存 key"""
        parts = [
            query.lower().strip(),
            ",".join(sorted(sources)),
            str(limit),
            str(offset),
            str(year_from or ""),
            str(year_to or ""),
            field,
        ]
        raw = "|".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        """获取缓存"""
        # Memory cache first
        if key in self._memory_cache:
            expires_at, data = self._memory_cache[key]
            if time.time() < expires_at:
                logger.debug(f"Cache hit (memory): {key[:8]}")
                return data
            else:
                del self._memory_cache[key]

        # Storage cache
        if self.storage:
            items = self.storage.query("search_cache", {"cache_key": key})
            if items:
                item = items[0]
                if time.time() < item.get("expires_at", 0):
                    logger.debug(f"Cache hit (storage): {key[:8]}")
                    data = item.get("data")
                    # Promote to memory
                    self._memory_cache[key] = (item["expires_at"], data)
                    return data
                else:
                    # Expired, clean up
                    self.storage.delete_item("search_cache", key)

        return None

    def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        """设置缓存"""
        effective_ttl = ttl or self.default_ttl
        expires_at = time.time() + effective_ttl

        # Memory
        self._memory_cache[key] = (expires_at, data)

        # Storage
        if self.storage:
            self.storage.upsert_item("search_cache", key, {
                "cache_key": key,
                "data": data,
                "expires_at": expires_at,
                "created_at": time.time(),
            })

        logger.debug(f"Cache set: {key[:8]} (TTL {effective_ttl}s)")

    def invalidate(self, key: str) -> None:
        """删除缓存"""
        self._memory_cache.pop(key, None)
        if self.storage:
            self.storage.delete_item("search_cache", key)

    def clear_expired(self) -> int:
        """清理过期缓存"""
        now = time.time()
        cleared = 0

        # Memory
        expired_keys = [k for k, (exp, _) in self._memory_cache.items() if now >= exp]
        for k in expired_keys:
            del self._memory_cache[k]
            cleared += 1

        return cleared

    @staticmethod
    def get_ttl_for_query(query: str, sources: list[str]) -> int:
        """根据查询类型选择 TTL"""
        q = query.lower().strip()
        # DOI query
        if q.startswith("10.") or "doi" in q:
            return _DOI_TTL
        # arXiv ID query
        if "arxiv" in sources and len(sources) == 1:
            return _ARXIV_TTL
        return _DEFAULT_TTL
