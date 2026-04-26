"""
单元测试 - 缓存机制
"""
import pytest
import time


class TestResultCache:
    """测试ResultCache"""

    def test_cache_set_and_get(self):
        """测试基本set和get"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache()
        cache.set("key1", {"result": "value1"})
        result = cache.get("key1")
        assert result == {"result": "value1"}

    def test_cache_miss(self):
        """测试缓存未命中"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_expiration(self):
        """测试缓存过期"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache()
        cache.set("key1", "value1", ttl=0.1)  # 0.1秒过期
        time.sleep(0.15)
        result = cache.get("key1")
        assert result is None

    def test_cache_delete(self):
        """测试删除缓存"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """测试清空缓存"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_stats(self):
        """测试缓存统计"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache()
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["total_hits"] == 2


class TestLLMCallOptimizer:
    """测试LLM调用优化器"""

    def test_optimizer_init(self):
        """测试优化器初始化"""
        from src.agents_v2.unified.cache import LLMLCallOptimizer

        optimizer = LLMLCallOptimizer(enable_cache=True)
        assert optimizer.cache is not None

    def test_optimizer_no_cache(self):
        """测试禁用缓存的优化器"""
        from src.agents_v2.unified.cache import LLMLCallOptimizer

        optimizer = LLMLCallOptimizer(enable_cache=False)
        assert optimizer.cache is None

    def test_make_request_key(self):
        """测试请求键生成"""
        from src.agents_v2.unified.cache import LLMLCallOptimizer

        optimizer = LLMLCallOptimizer()
        key1 = optimizer._make_request_key("test prompt", temperature=0.7)
        key2 = optimizer._make_request_key("test prompt", temperature=0.7)
        key3 = optimizer._make_request_key("different prompt", temperature=0.7)

        assert key1 == key2  # 相同请求应生成相同键
        assert key1 != key3  # 不同请求应生成不同键

    def test_get_cache_stats(self):
        """测试获取缓存统计"""
        from src.agents_v2.unified.cache import LLMLCallOptimizer

        optimizer = LLMLCallOptimizer()
        stats = optimizer.get_cache_stats()
        assert "size" in stats
        assert "total_hits" in stats


class TestCacheEntry:
    """测试缓存条目"""

    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        from src.agents_v2.unified.cache import CacheEntry

        entry = CacheEntry(key="test", value="result")
        assert entry.key == "test"
        assert entry.value == "result"
        assert entry.hit_count == 0
        assert not entry.is_expired()

    def test_cache_entry_increment_hit(self):
        """测试命中次数增加"""
        from src.agents_v2.unified.cache import CacheEntry

        entry = CacheEntry(key="test", value="result")
        entry.increment_hit()
        entry.increment_hit()
        assert entry.hit_count == 2

    def test_cache_entry_expiration(self):
        """测试过期检查"""
        from src.agents_v2.unified.cache import CacheEntry

        entry = CacheEntry(key="test", value="result", ttl=0.1)
        time.sleep(0.15)
        assert entry.is_expired()


class TestCacheStrategy:
    """测试缓存策略枚举"""

    def test_cache_strategy_values(self):
        """测试策略枚举值"""
        from src.agents_v2.unified.cache import CacheStrategy

        assert CacheStrategy.EXACT.value == "exact"
        assert CacheStrategy.SEMANTIC.value == "semantic"
        assert CacheStrategy.HYBRID.value == "hybrid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
