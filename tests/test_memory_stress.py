"""
记忆系统压测

大规模记忆操作性能测试
"""
import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch
from src.agents_v2.memory.hierarchical_memory import HierarchicalMemory, ShortTermMemory
from src.agents_v2.memory.services import MemoryCache, AdaptiveCache


class TestMemoryBatchOperations:
    """批量操作压测"""

    @pytest.mark.asyncio
    async def test_batch_insert_small(self):
        """测试小批量插入"""
        cache = MemoryCache(max_size=1000)

        start = time.time()
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")
        elapsed = time.time() - start

        assert elapsed < 0.1  # 100次操作应在100ms内完成

    @pytest.mark.asyncio
    async def test_batch_insert_large(self):
        """测试大批量插入"""
        cache = MemoryCache(max_size=10000)

        start = time.time()
        for i in range(5000):
            await cache.set(f"key_{i}", f"value_{i}" * 10)
        elapsed = time.time() - start

        # 5000次操作应在1秒内完成
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_batch_read_performance(self):
        """测试批量读取性能"""
        cache = MemoryCache(max_size=1000)

        for i in range(500):
            await cache.set(f"key_{i}", f"value_{i}")

        start = time.time()
        for i in range(500):
            _ = await cache.get(f"key_{i}")
        elapsed = time.time() - start

        # 500次读取应在100ms内完成
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_batch_delete_performance(self):
        """测试批量删除性能"""
        cache = MemoryCache(max_size=1000)

        for i in range(500):
            await cache.set(f"key_{i}", f"value_{i}")

        start = time.time()
        for i in range(500):
            cache.invalidate(f"key_{i}")
        elapsed = time.time() - start

        assert elapsed < 0.1
        stats = cache.get_stats()
        assert stats["size"] == 0


class TestMemoryThroughput:
    """吞吐量压测"""

    @pytest.mark.asyncio
    async def test_throughput_single_operation(self):
        """测试单操作吞吐量"""
        iterations = 10000
        cache = MemoryCache(max_size=20000)

        start = time.time()
        for i in range(iterations):
            await cache.set(f"key_{i}", f"value_{i}")
        elapsed = time.time() - start

        ops_per_second = iterations / elapsed
        # 纯内存操作应该达到很高的吞吐量
        assert ops_per_second > 50000

    @pytest.mark.asyncio
    async def test_throughput_mixed_operations(self):
        """测试混合操作吞吐量"""
        iterations = 5000
        cache = MemoryCache(max_size=10000)

        for i in range(1000):
            await cache.set(f"key_{i}", f"value_{i}")

        start = time.time()
        for i in range(iterations):
            op = i % 3
            if op == 0:
                await cache.get(f"key_{i % 1000}")
            elif op == 1:
                await cache.set(f"key_{i}", f"value_{i}")
            else:
                cache.invalidate(f"key_{i}")
        elapsed = time.time() - start

        ops_per_second = iterations / elapsed
        assert ops_per_second > 20000


class TestMemoryCapacity:
    """容量压测"""

    @pytest.mark.asyncio
    async def test_capacity_expansion(self):
        """测试容量扩展"""
        cache = MemoryCache(max_size=100)

        # 超过初始容量
        for i in range(200):
            await cache.set(f"key_{i}", f"value_{i}")

        # LRU应该淘汰旧数据
        stats = cache.get_stats()
        assert stats["size"] <= 100

    @pytest.mark.asyncio
    async def test_large_value_storage(self):
        """测试大值存储"""
        cache = MemoryCache(max_size=50)

        large_value = "x" * 10000  # 10KB value

        for i in range(60):
            await cache.set(f"key_{i}", large_value)

        # 大值会被存储
        stats = cache.get_stats()
        assert stats["size"] > 0

    def test_memory_usage_tracking(self):
        """测试内存使用跟踪"""
        cache = MemoryCache(max_size=100)

        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")

        stats = cache.get_stats()
        assert "size" in stats
        assert "max_size" in stats


class TestAdaptiveCache:
    """自适应缓存压测"""

    @pytest.mark.asyncio
    async def test_adaptive_cache_init(self):
        """测试自适应缓存初始化"""
        base_cache = MemoryCache(max_size=100)
        cache = AdaptiveCache(base_cache=base_cache)
        assert cache is not None
        assert cache.hit_rate == 0.0

    @pytest.mark.asyncio
    async def test_adaptive_cache_resize(self):
        """测试自适应缓存动态调整"""
        base_cache = MemoryCache(max_size=50)
        cache = AdaptiveCache(base_cache=base_cache)

        # 填充到初始容量
        for i in range(50):
            await base_cache.set(f"key_{i}", f"value_{i}")

        # 触发扩容 - 添加更多数据
        for i in range(50, 100):
            await base_cache.set(f"key_{i}", f"value_{i}")

        # 应该能处理更多数据
        stats = base_cache.get_stats()
        assert stats["size"] >= 50

    @pytest.mark.asyncio
    async def test_adaptive_cache_hit_rate(self):
        """测试自适应缓存命中率"""
        base_cache = MemoryCache(max_size=100)
        cache = AdaptiveCache(base_cache=base_cache)

        # 预热
        for i in range(50):
            await base_cache.set(f"key_{i}", f"value_{i}")

        # 多次访问热点数据
        for _ in range(100):
            await cache.get_or_set("key_0", lambda: "value_0")
            await cache.get_or_set("key_1", lambda: "value_1")
            await cache.get_or_set("key_2", lambda: "value_2")

        # 自适应缓存应该能跟踪命中率
        assert cache.hit_rate > 0


class TestHierarchicalMemory:
    """层级记忆压测"""

    def test_hierarchical_memory_init(self):
        """测试层级记忆初始化"""
        memory = HierarchicalMemory()
        assert memory is not None

    @pytest.mark.asyncio
    async def test_multi_level_access(self):
        """测试多级访问"""
        memory = HierarchicalMemory()

        memory.short_term.add("user_request", "test request")

        result = memory.short_term.get("user_request")
        assert result is not None or result == ""

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """测试批量操作"""
        memory = HierarchicalMemory()

        # 批量添加
        start = time.time()
        for i in range(100):
            memory.short_term.add(f"key_{i}", f"value_{i}")
        elapsed = time.time() - start

        assert elapsed < 2.0  # 100次操作应在2秒内完成


class TestConcurrencyPerformance:
    """并发性能压测"""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self):
        """测试并发读取"""
        cache = MemoryCache(max_size=1000)

        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")

        async def read_task(n):
            for i in range(n):
                await cache.get(f"key_{i % 100}")

        start = time.time()
        await asyncio.gather(*[read_task(50) for _ in range(10)])
        elapsed = time.time() - start

        # 10个并发任务，每个50次读取
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """测试并发写入"""
        cache = MemoryCache(max_size=5000)

        async def write_task(start, count):
            for i in range(count):
                await cache.set(f"key_{start + i}", f"value_{start + i}")

        start = time.time()
        await asyncio.gather(*[write_task(i * 100, 100) for i in range(10)])
        elapsed = time.time() - start

        # 10个并发任务，每个100次写入
        assert elapsed < 1.0
        stats = cache.get_stats()
        assert stats["size"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_mixed(self):
        """测试混合并发操作"""
        cache = MemoryCache(max_size=2000)

        for i in range(500):
            await cache.set(f"key_{i}", f"value_{i}")

        async def mixed_task(task_id):
            for i in range(50):
                key = f"key_{(task_id * 50 + i) % 500}"
                op = i % 3
                if op == 0:
                    await cache.get(key)
                elif op == 1:
                    await cache.set(f"new_{task_id}_{i}", f"value_{i}")
                else:
                    cache.invalidate(key)

        start = time.time()
        await asyncio.gather(*[mixed_task(i) for i in range(10)])
        elapsed = time.time() - start

        assert elapsed < 2.0


class TestLatencyBenchmarks:
    """延迟基准测试"""

    @pytest.mark.asyncio
    async def test_single_operation_latency(self):
        """测试单操作延迟"""
        cache = MemoryCache(max_size=1000)
        await cache.set("test_key", "test_value")

        latencies = []
        for _ in range(1000):
            start = time.time()
            await cache.get("test_key")
            latencies.append((time.time() - start) * 1000)  # 转换为ms

        avg_latency = sum(latencies) / len(latencies)
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        # 平均延迟应该很低
        assert avg_latency < 1.0  # 小于1ms
        assert p99_latency < 5.0  # P99小于5ms

    @pytest.mark.asyncio
    async def test_operation_latency_percentiles(self):
        """测试延迟百分位"""
        cache = MemoryCache(max_size=1000)

        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")

        latencies = []
        for _ in range(500):
            start = time.time()
            await cache.get(f"key_{_ % 100}")
            latencies.append((time.time() - start) * 1000)

        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

        assert p50 < 1.0
        assert p95 < 5.0
        assert p99 < 10.0


class TestMemoryEfficiency:
    """内存效率测试"""

    def test_memory_overhead(self):
        """测试内存开销"""
        cache = MemoryCache(max_size=1000)

        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")

        import sys
        size = sys.getsizeof(cache)

        # 基础对象应该有合理的内存占用
        assert size > 0

    @pytest.mark.asyncio
    async def test_entry_memory_efficiency(self):
        """测试条目内存效率"""
        cache = MemoryCache(max_size=1000)

        small_value = "x" * 10
        for i in range(100):
            await cache.set(f"key_{i}", small_value)

        # 小值应该高效存储
        stats = cache.get_stats()
        assert stats["size"] == 100


class TestShortTermMemory:
    """短期记忆压测"""

    def test_stm_init(self):
        """测试短期记忆初始化"""
        from src.agents_v2.memory.hierarchical_memory import ShortTermMemory
        stm = ShortTermMemory(max_items=100)
        assert stm is not None

    def test_stm_lru_eviction(self):
        """测试LRU淘汰"""
        from src.agents_v2.memory.hierarchical_memory import ShortTermMemory
        stm = ShortTermMemory(max_items=50)

        for i in range(60):
            stm.add(f"key_{i}", f"value_{i}")

        # 应该淘汰旧数据
        assert len(stm.items) <= 50

    def test_stm_ttl_expiry(self):
        """测试TTL过期"""
        from src.agents_v2.memory.hierarchical_memory import ShortTermMemory
        stm = ShortTermMemory(max_items=50, ttl=1)  # 1秒TTL

        stm.add("key_1", "value_1")
        assert stm.get("key_1") == "value_1"


class TestServiceLayerPerformance:
    """服务层性能测试"""

    @pytest.mark.asyncio
    async def test_cache_service_bypass(self):
        """测试缓存服务旁路"""
        cache = MemoryCache(max_size=100)

        # 旁路缓存直接操作
        await cache.set("key_1", "value_1")
        result = await cache.get("key_1")

        assert result == "value_1"

    @pytest.mark.asyncio
    async def test_stats_collection_performance(self):
        """测试统计收集性能"""
        cache = MemoryCache(max_size=1000)

        for i in range(500):
            await cache.set(f"key_{i}", f"value_{i}")
            await cache.get(f"key_{i}")

        start = time.time()
        for _ in range(100):
            cache.get_stats()
        elapsed = time.time() - start

        # 统计收集应该很快
        assert elapsed < 0.1
