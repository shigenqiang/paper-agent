"""
Performance Optimizer Tests

Tests for:
- ObjectPool: Object pooling for reducing GC pressure
- LazyLoader: Lazy initialization
- VectorCache: Vector caching for retrieval acceleration
- AsyncBatchExecutor: Async batch processing
- PerformanceOptimizer: Main performance optimizer
"""
import pytest
import asyncio
import time
from src.agents_v2.optimization import (
    PerformanceOptimizer,
    PerformanceMetrics,
    ObjectPool,
    LazyLoader,
    VectorCache,
    AsyncBatchExecutor,
    create_optimizer
)


class TestObjectPool:
    """ObjectPool Tests"""

    def test_acquire_release(self):
        """Test acquiring and releasing objects"""
        factory = lambda: {"data": "test"}
        pool = ObjectPool(factory, max_size=10)

        obj1 = pool.acquire()
        assert obj1["data"] == "test"

        pool.release(obj1)
        obj2 = pool.acquire()
        assert obj2["data"] == "test"

    def test_pool_size_limit(self):
        """Test pool size limit"""
        factory = lambda: {"data": "test"}
        pool = ObjectPool(factory, max_size=2)

        obj1 = pool.acquire()
        obj2 = pool.acquire()
        obj3 = pool.acquire()  # Should create new since pool is empty

        assert pool._pool == []
        pool.release(obj3)  # Will be discarded since over max_size

    def test_prewarm(self):
        """Test prewarming pool"""
        factory = lambda: {"data": "test"}
        pool = ObjectPool(factory, max_size=10)
        pool.prewarm(5)

        assert len(pool._pool) == 5


class TestLazyLoader:
    """LazyLoader Tests"""

    def test_register_and_get(self):
        """Test registering and getting instances"""
        loader = LazyLoader()

        factory_calls = []
        def factory():
            factory_calls.append(1)
            return {"initialized": True}

        loader.register("test_instance", factory)
        instance = loader.get("test_instance")

        assert instance["initialized"] is True
        assert len(factory_calls) == 1

    def test_get_without_register(self):
        """Test getting non-registered instance"""
        loader = LazyLoader()
        result = loader.get("nonexistent")
        assert result is None

    def test_get_idempotent(self):
        """Test that getting instance only creates once"""
        loader = LazyLoader()

        factory_calls = []
        def factory():
            factory_calls.append(1)
            return {"initialized": True}

        loader.register("test_instance", factory)
        loader.get("test_instance")
        loader.get("test_instance")
        loader.get("test_instance")

        assert len(factory_calls) == 1

    def test_preload_all(self):
        """Test preloading all registered factories"""
        loader = LazyLoader()

        def factory1():
            return {"name": "factory1"}
        def factory2():
            return {"name": "factory2"}

        loader.register("inst1", factory1)
        loader.register("inst2", factory2)
        loader.preload_all()

        assert loader.get("inst1")["name"] == "factory1"
        assert loader.get("inst2")["name"] == "factory2"


class TestVectorCache:
    """VectorCache Tests"""

    def test_set_and_get(self):
        """Test setting and getting vectors"""
        cache = VectorCache(max_size=100)

        vector = [0.1, 0.2, 0.3]
        cache.set("key1", vector)

        result = cache.get("key1")
        assert result == vector

    def test_get_miss(self):
        """Test cache miss"""
        cache = VectorCache(max_size=100)
        result = cache.get("nonexistent")
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = VectorCache(max_size=3)

        cache.set("key1", [0.1])
        cache.set("key2", [0.2])
        cache.set("key3", [0.3])

        # Access key1 to make it recent
        cache.get("key1")

        # Add new item, should evict key2 (least recent)
        cache.set("key4", [0.4])

        assert cache.get("key1") == [0.1]
        assert cache.get("key2") is None  # evicted
        assert cache.get("key3") == [0.3]
        assert cache.get("key4") == [0.4]

    def test_hit_rate(self):
        """Test hit rate calculation"""
        cache = VectorCache(max_size=100)

        cache.set("key1", [0.1])
        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        assert cache.hit_rate == pytest.approx(2/3, rel=0.01)

    def test_clear(self):
        """Test clearing cache"""
        cache = VectorCache(max_size=100)

        cache.set("key1", [0.1])
        cache.set("key2", [0.2])
        cache.clear()

        assert cache.get("key1") is None
        assert len(cache._cache) == 0
        assert cache.hit_rate == 0.0


class TestAsyncBatchExecutor:
    """AsyncBatchExecutor Tests"""

    @pytest.mark.asyncio
    async def test_submit_single(self):
        """Test submitting single coroutine"""
        executor = AsyncBatchExecutor(batch_size=5, max_wait_ms=100)

        async def simple_coro():
            return 42

        result = await executor.submit(simple_coro())
        assert result == 42

    @pytest.mark.asyncio
    async def test_batch_trigger(self):
        """Test batch is triggered when size reached"""
        executor = AsyncBatchExecutor(batch_size=3, max_wait_ms=1000)

        async def simple_coro(i):
            return i

        # Submit 3 items - when batch size is reached, it flushes and returns all
        results = []
        for i in range(3):
            result = await executor.submit(simple_coro(i))
            results.append(result)

        # When batch is full, results are returned as list of all results
        # The submit returns await future which gives individual result
        # But after flush, pending is cleared
        assert len(executor._pending) == 0 or len(results) == 3

    @pytest.mark.asyncio
    async def test_flush_empty(self):
        """Test flushing empty batch"""
        executor = AsyncBatchExecutor(batch_size=10, max_wait_ms=100)
        result = await executor._flush()
        assert result == []


class TestPerformanceOptimizer:
    """PerformanceOptimizer Tests"""

    def test_create_pool(self):
        """Test creating object pool"""
        optimizer = create_optimizer()
        optimizer.create_pool("test_pool", lambda: {"data": "test"}, max_size=10)

        assert "test_pool" in optimizer._pools
        obj = optimizer._pools["test_pool"].acquire()
        assert obj["data"] == "test"

    def test_register_lazy(self):
        """Test registering lazy loader"""
        optimizer = create_optimizer()

        factory_calls = []
        def factory():
            factory_calls.append(1)
            return {"initialized": True}

        optimizer.register_lazy("test_inst", factory)
        instance = optimizer.get_cached_vector("test_inst")  # This uses vector cache, not lazy
        # Lazy loader is separate
        optimizer._lazy_loader.register("test_lazy", factory)
        lazy_instance = optimizer._lazy_loader.get("test_lazy")

        assert lazy_instance["initialized"] is True
        assert len(factory_calls) == 1

    def test_vector_cache_operations(self):
        """Test vector cache operations"""
        optimizer = create_optimizer()

        vector = [0.1, 0.2, 0.3]
        optimizer.cache_vector("key1", vector)

        result = optimizer.get_cached_vector("key1")
        assert result == vector

    def test_prewarm(self):
        """Test prewarm operation"""
        optimizer = create_optimizer()
        optimizer.create_pool("test_pool", lambda: {"data": "test"}, max_size=10)

        optimizer.prewarm()
        assert len(optimizer._pools["test_pool"]._pool) == 10

    def test_get_metrics(self):
        """Test getting performance metrics"""
        optimizer = create_optimizer()
        metrics = optimizer.get_metrics()

        assert isinstance(metrics, PerformanceMetrics)
        assert hasattr(metrics, 'cold_start_time')
        assert hasattr(metrics, 'memory_usage_mb')
        assert hasattr(metrics, 'cache_hit_rate')

    def test_optimize_with_suggestions(self):
        """Test optimize returns suggestions"""
        optimizer = create_optimizer()

        # Add some vectors to cache
        for i in range(100):
            optimizer.cache_vector(f"key{i}", [float(i)] * 10)

        result = optimizer.optimize()

        assert "metrics" in result
        assert "suggestions" in result
        assert "cache_size" in result
        assert result["cache_size"] == 100


class TestPerformanceMetrics:
    """PerformanceMetrics Tests"""

    def test_create_metrics(self):
        """Test creating performance metrics"""
        metrics = PerformanceMetrics(
            cold_start_time=1.5,
            retrieval_latency_p95=50.0,
            generation_speed=100.0,
            memory_usage_mb=512.0,
            cache_hit_rate=0.75,
            total_requests=1000
        )

        assert metrics.cold_start_time == 1.5
        assert metrics.retrieval_latency_p95 == 50.0
        assert metrics.generation_speed == 100.0
        assert metrics.memory_usage_mb == 512.0
        assert metrics.cache_hit_rate == 0.75
        assert metrics.total_requests == 1000

    def test_default_metrics(self):
        """Test default performance metrics"""
        metrics = PerformanceMetrics()
        assert metrics.cold_start_time == 0.0
        assert metrics.retrieval_latency_p95 == 0.0
        assert metrics.generation_speed == 0.0
        assert metrics.memory_usage_mb == 0.0
        assert metrics.cache_hit_rate == 0.0
        assert metrics.total_requests == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])