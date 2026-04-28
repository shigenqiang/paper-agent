"""报告缓存 - 搜索结果和报告缓存"""
import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
import time

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hit_count: int = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self):
        self.hit_count += 1


class MemoryCache:
    """内存缓存"""

    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._cache[key]
                return None
            entry.touch()
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存"""
        async with self._lock:
            ttl = ttl or self._default_ttl
            now = time.time()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl
            )
            self._cache[key] = entry

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self):
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self):
        """清理过期缓存"""
        async with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = len(self._cache)
        expired = sum(1 for v in self._cache.values() if v.is_expired())
        total_hits = sum(v.hit_count for v in self._cache.values())

        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "total_hits": total_hits
        }


class CacheDecorator:
    """缓存装饰器"""

    def __init__(self, cache: MemoryCache, key_prefix: str = "", ttl: int = 3600):
        self.cache = cache
        self.key_prefix = key_prefix
        self.ttl = ttl

    def cached(self, key_func: Optional[Callable] = None):
        """
        缓存装饰器

        Usage:
            @cache.cached()
            async def my_function(arg1, arg2):
                ...

            @cache.cached(key_func=lambda args, kwargs: args[0])
            async def my_function(arg1, arg2):
                ...
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key_data = key_func(args, kwargs)
                else:
                    cache_key_data = {"args": args, "kwargs": kwargs}

                cache_key = f"{self.key_prefix}:{hashlib.md5(json.dumps(cache_key_data, sort_keys=True, default=str).encode()).hexdigest()}"

                # 尝试获取缓存
                cached_value = await self.cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value

                # 执行函数
                result = await func(*args, **kwargs)

                # 设置缓存
                await self.cache.set(cache_key, result, self.ttl)
                logger.debug(f"Cache set: {cache_key}")

                return result
            return wrapper
        return decorator


def wraps(func):
    """简单的wraps替代"""
    def decorator(f):
        f.__name__ = func.__name__
        f.__doc__ = func.__doc__
        return f
    return decorator


class SearchResultCache:
    """
    搜索结果缓存

    专门用于缓存论文搜索结果
    """

    # 缓存TTL配置（秒）
    TTL_SHORT = 300      # 5分钟 - 最新搜索
    TTL_MEDIUM = 1800    # 30分钟 - 标准搜索
    TTL_LONG = 3600      # 1小时 - 热门搜索

    def __init__(self, cache: Optional[MemoryCache] = None):
        self._cache = cache or MemoryCache(default_ttl=self.TTL_MEDIUM)

    async def get_search_result(
        self,
        query: str,
        sources: List[str],
        time_range: int
    ) -> Optional[Dict[str, Any]]:
        """获取搜索结果缓存"""
        key = self._make_search_key(query, sources, time_range)
        return await self._cache.get(key)

    async def set_search_result(
        self,
        query: str,
        sources: List[str],
        time_range: int,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """设置搜索结果缓存"""
        key = self._make_search_key(query, sources, time_range)
        if ttl is None:
            # 根据时间范围确定TTL
            if time_range <= 7:
                ttl = self.TTL_SHORT
            elif time_range <= 30:
                ttl = self.TTL_MEDIUM
            else:
                ttl = self.TTL_LONG

        await self._cache.set(key, result, ttl)

    def _make_search_key(
        self,
        query: str,
        sources: List[str],
        time_range: int
    ) -> str:
        """生成搜索缓存键"""
        sources_str = ",".join(sorted(sources))
        key_data = f"{query}:{sources_str}:{time_range}"
        return f"search:{hashlib.md5(key_data.encode()).hexdigest()}"


class ReportCache:
    """
    报告缓存

    专门用于缓存生成的报告
    """

    # 报告缓存TTL（秒）
    TTL_DAILY = 3600       # 1小时
    TTL_WEEKLY = 7200      # 2小时
    TTL_MONTHLY = 14400   # 4小时

    def __init__(self, cache: Optional[MemoryCache] = None):
        self._cache = cache or MemoryCache(default_ttl=self.TTL_DAILY)

    async def get_daily_report(
        self,
        keywords: List[str],
        date: str
    ) -> Optional[Dict[str, Any]]:
        """获取每日报告缓存"""
        key = self._make_report_key("daily", keywords, date)
        return await self._cache.get(key)

    async def set_daily_report(
        self,
        keywords: List[str],
        date: str,
        report: Dict[str, Any]
    ):
        """设置每日报告缓存"""
        key = self._make_report_key("daily", keywords, date)
        await self._cache.set(key, report, self.TTL_DAILY)

    async def get_weekly_report(
        self,
        keywords: List[str],
        week_start: str,
        week_end: str
    ) -> Optional[Dict[str, Any]]:
        """获取周报告缓存"""
        key = self._make_report_key("weekly", keywords, f"{week_start}:{week_end}")
        return await self._cache.get(key)

    async def set_weekly_report(
        self,
        keywords: List[str],
        week_start: str,
        week_end: str,
        report: Dict[str, Any]
    ):
        """设置周报告缓存"""
        key = self._make_report_key("weekly", keywords, f"{week_start}:{week_end}")
        await self._cache.set(key, report, self.TTL_WEEKLY)

    async def get_monthly_report(
        self,
        keywords: List[str],
        year_month: str
    ) -> Optional[Dict[str, Any]]:
        """获取月报告缓存"""
        key = self._make_report_key("monthly", keywords, year_month)
        return await self._cache.get(key)

    async def set_monthly_report(
        self,
        keywords: List[str],
        year_month: str,
        report: Dict[str, Any]
    ):
        """设置月报告缓存"""
        key = self._make_report_key("monthly", keywords, year_month)
        await self._cache.set(key, report, self.TTL_MONTHLY)

    def _make_report_key(
        self,
        report_type: str,
        keywords: List[str],
        date_key: str
    ) -> str:
        """生成报告缓存键"""
        keywords_str = ",".join(sorted(keywords))
        key_data = f"{report_type}:{keywords_str}:{date_key}"
        return f"report:{hashlib.md5(key_data.encode()).hexdigest()}"


# 全局缓存实例
_search_cache: Optional[SearchResultCache] = None
_report_cache: Optional[ReportCache] = None


def get_search_cache() -> SearchResultCache:
    """获取搜索缓存"""
    global _search_cache
    if _search_cache is None:
        _search_cache = SearchResultCache()
    return _search_cache


def get_report_cache() -> ReportCache:
    """获取报告缓存"""
    global _report_cache
    if _report_cache is None:
        _report_cache = ReportCache()
    return _report_cache
