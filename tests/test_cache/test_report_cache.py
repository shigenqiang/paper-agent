"""
缓存模块 单元测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from src.agents_v2._archive.cache import (
    CacheEntry,
    MemoryCache,
    SearchResultCache,
    ReportCache,
    get_search_cache,
    get_report_cache
)


class TestCacheEntry:
    """CacheEntry 测试"""

    def test_create_entry(self):
        """测试创建缓存条目"""
        now = time.time()
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            created_at=now,
            expires_at=now + 3600
        )
        assert entry.key == "test_key"
        assert entry.value["data"] == "test"
        assert entry.hit_count == 0

    def test_is_expired_false(self):
        """测试未过期"""
        now = time.time()
        entry = CacheEntry(
            key="test",
            value=None,
            created_at=now,
            expires_at=now + 3600
        )
        assert entry.is_expired() is False

    def test_is_expired_true(self):
        """测试已过期"""
        now = time.time()
        entry = CacheEntry(
            key="test",
            value=None,
            created_at=now - 7200,
            expires_at=now - 3600
        )
        assert entry.is_expired() is True

    def test_touch(self):
        """测试命中计数"""
        entry = CacheEntry(
            key="test",
            value=None,
            created_at=time.time(),
            expires_at=time.time() + 3600
        )
        assert entry.hit_count == 0
        entry.touch()
        assert entry.hit_count == 1
        entry.touch()
        assert entry.hit_count == 2


class TestMemoryCache:
    """MemoryCache 测试"""

    def setup_method(self):
        self.cache = MemoryCache(default_ttl=3600)

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """测试设置和获取"""
        await self.cache.set("key1", {"value": 1})
        result = await self.cache.get("key1")
        assert result == {"value": 1}

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        """测试获取不存在的键"""
        result = await self.cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """测试删除"""
        await self.cache.set("key1", "value1")
        deleted = await self.cache.delete("key1")
        assert deleted is True

        result = await self.cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """测试删除不存在的键"""
        deleted = await self.cache.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空"""
        await self.cache.set("key1", "value1")
        await self.cache.set("key2", "value2")
        await self.cache.clear()

        assert await self.cache.get("key1") is None
        assert await self.cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_expired_cleanup(self):
        """测试过期清理"""
        now = time.time()
        # 创建一个过期的条目
        entry = CacheEntry(
            key="expired",
            value="old",
            created_at=now - 7200,
            expires_at=now - 3600
        )
        self.cache._cache["expired"] = entry

        # 创建一个正常的条目
        await self.cache.set("valid", "new")

        cleaned = await self.cache.cleanup_expired()
        assert cleaned == 1
        assert await self.cache.get("expired") is None
        assert await self.cache.get("valid") == "new"

    def test_get_stats(self):
        """测试获取统计"""
        stats = self.cache.get_stats()
        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "total_hits" in stats


class TestSearchResultCache:
    """SearchResultCache 测试"""

    def setup_method(self):
        self.cache = SearchResultCache()

    @pytest.mark.asyncio
    async def test_set_and_get_search_result(self):
        """测试设置和获取搜索结果"""
        query = "machine learning"
        sources = ["arxiv", "pubmed"]
        time_range = 30

        result_data = {
            "papers": [{"title": "Paper 1"}],
            "total": 1
        }

        await self.cache.set_search_result(query, sources, time_range, result_data)

        cached = await self.cache.get_search_result(query, sources, time_range)
        assert cached == result_data

    @pytest.mark.asyncio
    async def test_different_queries(self):
        """测试不同查询"""
        await self.cache.set_search_result(
            "query1", ["arxiv"], 30, {"result": "1"}
        )
        await self.cache.set_search_result(
            "query2", ["arxiv"], 30, {"result": "2"}
        )

        assert await self.cache.get_search_result("query1", ["arxiv"], 30) == {"result": "1"}
        assert await self.cache.get_search_result("query2", ["arxiv"], 30) == {"result": "2"}

    def test_make_search_key(self):
        """测试生成搜索键"""
        key1 = self.cache._make_search_key("test", ["a", "b"], 30)
        key2 = self.cache._make_search_key("test", ["b", "a"], 30)
        key3 = self.cache._make_search_key("test", ["a", "b"], 7)

        # 相同参数应生成相同键
        assert key1 == key2
        # 不同参数应生成不同键
        assert key1 != key3


class TestReportCache:
    """ReportCache 测试"""

    def setup_method(self):
        self.cache = ReportCache()

    @pytest.mark.asyncio
    async def test_daily_report(self):
        """测试每日报告缓存"""
        keywords = ["ML", "DL"]
        date = "2026-04-28"
        report = {"summary": "Daily report", "papers": []}

        await self.cache.set_daily_report(keywords, date, report)
        cached = await self.cache.get_daily_report(keywords, date)
        assert cached == report

    @pytest.mark.asyncio
    async def test_weekly_report(self):
        """测试周报告缓存"""
        keywords = ["NLP"]
        week_start = "2026-04-20"
        week_end = "2026-04-26"
        report = {"summary": "Weekly report"}

        await self.cache.set_weekly_report(keywords, week_start, week_end, report)
        cached = await self.cache.get_weekly_report(keywords, week_start, week_end)
        assert cached == report

    @pytest.mark.asyncio
    async def test_monthly_report(self):
        """测试月报告缓存"""
        keywords = ["CV"]
        year_month = "2026-04"
        report = {"summary": "Monthly report"}

        await self.cache.set_monthly_report(keywords, year_month, report)
        cached = await self.cache.get_monthly_report(keywords, year_month)
        assert cached == report

    @pytest.mark.asyncio
    async def test_different_keywords(self):
        """测试不同关键词"""
        await self.cache.set_daily_report(["ML"], "2026-04-28", {"k": "ML"})
        await self.cache.set_daily_report(["DL"], "2026-04-28", {"k": "DL"})

        assert await self.cache.get_daily_report(["ML"], "2026-04-28") == {"k": "ML"}
        assert await self.cache.get_daily_report(["DL"], "2026-04-28") == {"k": "DL"}


class TestGlobalInstances:
    """全局实例测试"""

    def test_get_search_cache_singleton(self):
        """测试搜索缓存单例"""
        cache1 = get_search_cache()
        cache2 = get_search_cache()
        assert cache1 is cache2

    def test_get_report_cache_singleton(self):
        """测试报告缓存单例"""
        cache1 = get_report_cache()
        cache2 = get_report_cache()
        assert cache1 is cache2


class TestCacheIntegration:
    """集成测试"""

    def setup_method(self):
        self.search_cache = SearchResultCache()
        self.report_cache = ReportCache()

    @pytest.mark.asyncio
    async def test_cached_search_flow(self):
        """测试缓存搜索流程"""
        query = "causal inference"
        sources = ["arxiv"]
        time_range = 30

        # 第一次搜索（未缓存）
        result1 = await self.search_cache.get_search_result(query, sources, time_range)
        assert result1 is None

        # 模拟搜索
        search_result = {"papers": [{"title": "Causal Paper"}], "total": 1}
        await self.search_cache.set_search_result(query, sources, time_range, search_result)

        # 第二次搜索（缓存命中）
        cached = await self.search_cache.get_search_result(query, sources, time_range)
        assert cached == search_result

    @pytest.mark.asyncio
    async def test_cached_report_flow(self):
        """测试缓存报告流程"""
        # 模拟日报生成流程
        keywords = ["machine learning"]
        date = "2026-04-28"

        # 检查缓存
        cached = await self.report_cache.get_daily_report(keywords, date)
        if cached is None:
            # 生成报告
            report = {"summary": "Generated report", "papers_found": 50}
            await self.report_cache.set_daily_report(keywords, date, report)

        # 获取缓存
        final = await self.report_cache.get_daily_report(keywords, date)
        assert final is not None
        assert final["papers_found"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
