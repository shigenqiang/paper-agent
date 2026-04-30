"""
Production模块测试

测试:
- RateLimiter: 限流器
- CostOptimizer: 成本优化器
- MonitoringDashboard: 监控仪表板
"""
import pytest
import time
import asyncio
from unittest.mock import MagicMock

from src.agents_v2._archive.production import (
    RateLimiter,
    LimiterStrategy,
    LimiterConfig,
    FixedWindowLimiter,
    SlidingWindowLimiter,
    TokenBucketLimiter,
    LeakyBucketLimiter,
    MultiLimiter,
    create_rate_limiter,
    CostOptimizer,
    CostConfig,
    CostMetrics,
    create_cost_optimizer,
    MonitoringDashboard,
    MetricsCollector,
    MetricPoint,
    create_dashboard
)


class TestFixedWindowLimiter:
    """FixedWindowLimiter测试"""

    def test_init(self):
        """测试初始化"""
        limiter = FixedWindowLimiter(max_requests=10, window_seconds=1.0)
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 1.0

    def test_is_allowed(self):
        """测试允许请求"""
        limiter = FixedWindowLimiter(max_requests=3, window_seconds=1.0)

        assert limiter.is_allowed() is True  # 1
        assert limiter.is_allowed() is True  # 2
        assert limiter.is_allowed() is True  # 3
        assert limiter.is_allowed() is False  # 4 (超过限制)

    def test_reset(self):
        """测试重置"""
        limiter = FixedWindowLimiter(max_requests=2, window_seconds=1.0)

        limiter.is_allowed()
        limiter.is_allowed()
        assert limiter.is_allowed() is False

        limiter.reset()
        assert limiter.is_allowed() is True


class TestSlidingWindowLimiter:
    """SlidingWindowLimiter测试"""

    def test_init(self):
        """测试初始化"""
        limiter = SlidingWindowLimiter(max_requests=5, window_seconds=1.0)
        assert limiter.max_requests == 5

    def test_is_allowed(self):
        """测试允许请求"""
        limiter = SlidingWindowLimiter(max_requests=3, window_seconds=1.0)

        for _ in range(3):
            assert limiter.is_allowed() is True

        assert limiter.is_allowed() is False

    def test_get_current_count(self):
        """测试获取当前计数"""
        limiter = SlidingWindowLimiter(max_requests=5, window_seconds=1.0)

        limiter.is_allowed()
        limiter.is_allowed()

        assert limiter.get_current_count() == 2


class TestTokenBucketLimiter:
    """TokenBucketLimiter测试"""

    def test_init(self):
        """测试初始化"""
        limiter = TokenBucketLimiter(rate=10.0, burst=20.0)
        assert limiter.rate == 10.0
        assert limiter.burst == 20.0

    def test_is_allowed(self):
        """测试允许请求"""
        limiter = TokenBucketLimiter(rate=1.0, burst=2.0)

        # 突发容量允许2个
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is False  # 桶空了

    def test_get_available_tokens(self):
        """测试获取可用令牌"""
        limiter = TokenBucketLimiter(rate=10.0, burst=10.0)

        # 消耗一些
        limiter.is_allowed()
        limiter.is_allowed()

        tokens = limiter.get_available_tokens()
        assert tokens < 10.0


class TestLeakyBucketLimiter:
    """LeakyBucketLimiter测试"""

    def test_init(self):
        """测试初始化"""
        limiter = LeakyBucketLimiter(rate=1.0, capacity=5.0)
        assert limiter.rate == 1.0
        assert limiter.capacity == 5.0

    def test_is_allowed(self):
        """测试允许请求"""
        limiter = LeakyBucketLimiter(rate=0.1, capacity=1.0)  # 慢漏水

        assert limiter.is_allowed() is True
        # 水量已满（超过容量），拒绝
        limiter.water = limiter.capacity + 1
        assert limiter.is_allowed() is False


class TestRateLimiter:
    """RateLimiter测试"""

    def test_init_token_bucket(self):
        """测试TokenBucket初始化"""
        config = LimiterConfig(
            strategy=LimiterStrategy.TOKEN_BUCKET,
            rate=10.0,
            burst=20.0
        )
        limiter = RateLimiter(config)
        assert limiter.config.strategy == LimiterStrategy.TOKEN_BUCKET

    def test_init_fixed_window(self):
        """测试FixedWindow初始化"""
        config = LimiterConfig(strategy=LimiterStrategy.FIXED_WINDOW)
        limiter = RateLimiter(config)
        assert limiter.config.strategy == LimiterStrategy.FIXED_WINDOW

    def test_is_allowed(self):
        """测试允许请求"""
        config = LimiterConfig(
            strategy=LimiterStrategy.TOKEN_BUCKET,
            rate=1.0,
            burst=1.0
        )
        limiter = RateLimiter(config)

        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is False

    def test_get_stats(self):
        """测试获取统计"""
        config = LimiterConfig(strategy=LimiterStrategy.TOKEN_BUCKET, rate=10.0, burst=20.0)
        limiter = RateLimiter(config)

        stats = limiter.get_stats()
        assert "strategy" in stats
        assert stats["strategy"] == "token_bucket"


class TestMultiLimiter:
    """MultiLimiter测试"""

    def test_init(self):
        """测试初始化"""
        multi = MultiLimiter()
        assert multi is not None

    def test_add_limiter(self):
        """测试添加限流器"""
        multi = MultiLimiter()
        limiter = create_rate_limiter("token_bucket", 10.0, 20.0)
        multi.add_limiter("api", limiter)

        assert "api" in multi._limiters

    def test_is_allowed_single(self):
        """测试单维度限流"""
        multi = MultiLimiter()
        limiter = create_rate_limiter("token_bucket", 1.0, 1.0)
        multi.add_limiter("api", limiter)

        assert multi.is_allowed(api=1.0) is True
        assert multi.is_allowed(api=1.0) is False

    def test_get_all_stats(self):
        """测试获取所有统计"""
        multi = MultiLimiter()
        limiter = create_rate_limiter("token_bucket", 10.0, 20.0)
        multi.add_limiter("api", limiter)

        stats = multi.get_all_stats()
        assert "api" in stats


class TestCostConfig:
    """CostConfig测试"""

    def test_init(self):
        """测试初始化"""
        config = CostConfig(primary_model="gpt-4", fallback_model="gpt-3.5")
        assert config.primary_model == "gpt-4"
        assert config.fallback_model == "gpt-3.5"


class TestCostMetrics:
    """CostMetrics测试"""

    def test_init(self):
        """测试初始化"""
        metrics = CostMetrics()
        assert metrics.total_calls == 0

    def test_cache_hit_rate(self):
        """测试缓存命中率"""
        metrics = CostMetrics(total_calls=10, cached_calls=3)
        assert metrics.cache_hit_rate == 0.3


class TestCostOptimizer:
    """CostOptimizer测试"""

    def test_init(self):
        """测试初始化"""
        optimizer = CostOptimizer()
        assert optimizer is not None
        assert optimizer.metrics.total_calls == 0

    def test_get_cache_key(self):
        """测试缓存键生成"""
        optimizer = CostOptimizer()
        key1 = optimizer._get_cache_key("test prompt")
        key2 = optimizer._get_cache_key("test prompt")
        key3 = optimizer._get_cache_key("different prompt")

        assert key1 == key2
        assert key1 != key3

    def test_is_cache_valid(self):
        """测试缓存有效性"""
        optimizer = CostOptimizer()
        optimizer._cache["test_key"] = "value"
        optimizer._cache_times["test_key"] = time.time()

        assert optimizer._is_cache_valid("test_key") is True
        assert optimizer._is_cache_valid("nonexistent") is False

    def test_should_use_fallback(self):
        """测试降级判断"""
        optimizer = CostOptimizer()

        # 短prompt应该用降级
        assert optimizer._should_use_fallback("short", 100) is True

        # 长prompt不用降级
        assert optimizer._should_use_fallback("a" * 2000, 1000) is False

    def test_estimate_cost(self):
        """测试成本估算"""
        optimizer = CostOptimizer()

        cost = optimizer._estimate_cost(1000, "gpt-4")
        assert cost == pytest.approx(0.03)

    @pytest.mark.asyncio
    async def test_execute_with_fallback_caching(self):
        """测试带缓存的降级执行"""
        config = CostConfig(primary_model="gpt-4", fallback_model="gpt-3.5-turbo", cache_enabled=True)
        optimizer = CostOptimizer(config=config)

        async def primary_func(prompt):
            return f"primary: {prompt}"

        async def fallback_func(prompt):
            return f"fallback: {prompt}"

        # 使用超过500 tokens的prompt避免自动降级
        long_prompt = "这是一个很长的prompt " * 200  # ~2800 chars -> ~700 tokens

        result = await optimizer.execute_with_fallback(
            long_prompt,
            primary_func,
            fallback_func,
            use_cache=True
        )

        assert "primary" in result
        assert optimizer.metrics.total_calls == 1

        # 第二次应该命中缓存
        result2 = await optimizer.execute_with_fallback(
            long_prompt,
            primary_func,
            fallback_func,
            use_cache=True
        )

        assert optimizer.metrics.cached_calls == 1

    def test_compress_context(self):
        """测试上下文压缩"""
        optimizer = CostOptimizer()

        long_text = "这是" * 5000
        compressed = optimizer.compress_context(long_text, max_length=1000)

        assert len(compressed) <= 1000

        short_text = "短文本"
        assert optimizer.compress_context(short_text, max_length=1000) == short_text

    def test_get_stats(self):
        """测试获取统计"""
        optimizer = CostOptimizer()
        optimizer.metrics.total_calls = 10
        optimizer.metrics.cached_calls = 3

        stats = optimizer.get_stats()
        assert stats["total_calls"] == 10
        assert stats["cached_calls"] == 3

    def test_clear_cache(self):
        """测试清空缓存"""
        optimizer = CostOptimizer()
        optimizer._cache["test"] = "value"

        optimizer.clear_cache()
        assert len(optimizer._cache) == 0


class TestMetricsCollector:
    """MetricsCollector测试"""

    def test_init(self):
        """测试初始化"""
        collector = MetricsCollector()
        assert collector is not None

    def test_record_latency(self):
        """测试记录延迟"""
        collector = MetricsCollector()
        collector.record_latency("test_op", 0.5)

        stats = collector.get_latency_stats("test_op")
        assert stats["avg"] == 0.5

    def test_record_count(self):
        """测试记录计数"""
        collector = MetricsCollector()
        collector.record_count("test_counter", 5)

        assert collector.get_counter("test_counter") == 5

    def test_set_gauge(self):
        """测试设置仪表"""
        collector = MetricsCollector()
        collector.set_gauge("test_gauge", 100.0)

        assert collector.get_gauge("test_gauge") == 100.0


class TestMonitoringDashboard:
    """MonitoringDashboard测试"""

    def test_init(self):
        """测试初始化"""
        dashboard = MonitoringDashboard()
        assert dashboard is not None

    def test_record_request(self):
        """测试记录请求"""
        dashboard = MonitoringDashboard()
        dashboard.record_request("test_op", 0.5, True)

        summary = dashboard.get_dashboard_summary()
        assert summary["requests"]["total"] == 1

    def test_record_queue_size(self):
        """测试记录队列大小"""
        dashboard = MonitoringDashboard()
        dashboard.record_queue_size("default", 50)

        summary = dashboard.get_dashboard_summary()
        assert summary["queues"]["default"] == 50

    def test_get_dashboard_summary(self):
        """测试获取仪表板摘要"""
        dashboard = MonitoringDashboard()
        dashboard.record_request("op1", 0.3, True)
        dashboard.record_request("op1", 0.7, True)
        dashboard.record_request("op2", 0.1, False)

        summary = dashboard.get_dashboard_summary()

        assert summary["requests"]["total"] == 3
        assert summary["requests"]["success"] == 2
        assert summary["requests"]["failure"] == 1


class TestCreateRateLimiter:
    """create_rate_limiter测试"""

    def test_create_token_bucket(self):
        """测试创建令牌桶限流器"""
        limiter = create_rate_limiter("token_bucket", 100.0, 200.0)
        assert limiter.config.strategy == LimiterStrategy.TOKEN_BUCKET

    def test_create_leaky_bucket(self):
        """测试创建漏桶限流器"""
        limiter = create_rate_limiter("leaky_bucket", 50.0, 100.0)
        assert limiter.config.strategy == LimiterStrategy.LEAKY_BUCKET


class TestCreateCostOptimizer:
    """create_cost_optimizer测试"""

    def test_create(self):
        """测试创建成本优化器"""
        optimizer = create_cost_optimizer("gpt-4", "gpt-3.5-turbo", True)
        assert optimizer.config.primary_model == "gpt-4"


class TestCreateDashboard:
    """create_dashboard测试"""

    def test_create(self):
        """测试创建仪表板"""
        dashboard = create_dashboard()
        assert isinstance(dashboard, MonitoringDashboard)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])