"""
单元测试 - 监控和性能
"""
import pytest
import asyncio
import time


class TestMetricsCollector:
    """测试指标收集器"""

    def test_record_metric(self):
        """测试记录指标"""
        from src.agents_v2.unified.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.record("test_metric", 1.0)
        assert len(collector._metrics) == 1

    def test_increment_counter(self):
        """测试增加计数器"""
        from src.agents_v2.unified.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.increment("requests", 1)
        collector.increment("requests", 1)
        assert collector._counters["requests"] == 2

    def test_gauge(self):
        """测试仪表值"""
        from src.agents_v2.unified.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.gauge("memory_usage", 0.75)
        assert collector._gauges["memory_usage"] == 0.75

    def test_get_stats(self):
        """测试获取统计"""
        from src.agents_v2.unified.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.record("latency", 0.5)
        collector.record("latency", 1.0)
        collector.record("latency", 1.5)

        stats = collector.get_stats()
        assert "latency" in stats["histograms"]
        assert stats["histograms"]["latency"]["count"] == 3
        assert stats["histograms"]["latency"]["mean"] == 1.0

    def test_clear(self):
        """测试清空指标"""
        from src.agents_v2.unified.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.record("test", 1.0)
        collector.clear()

        assert len(collector._metrics) == 0
        assert len(collector._counters) == 0


class TestPerformanceMonitor:
    """测试性能监控器"""

    def test_monitor_init(self):
        """测试监控器初始化"""
        from src.agents_v2.unified.monitoring import PerformanceMonitor

        monitor = PerformanceMonitor()
        assert monitor.metrics is not None

    def test_track_sync(self):
        """测试跟踪同步函数"""
        from src.agents_v2.unified.monitoring import PerformanceMonitor

        monitor = PerformanceMonitor()

        @monitor.track_sync("test_op")
        def sync_function():
            time.sleep(0.01)
            return "result"

        result = sync_function()
        assert result == "result"

        stats = monitor.metrics.get_stats()
        assert "test_op_latency" in stats["histograms"]

    @pytest.mark.asyncio
    async def test_track_async(self):
        """测试跟踪异步函数"""
        from src.agents_v2.unified.monitoring import PerformanceMonitor

        monitor = PerformanceMonitor()

        @monitor.track("async_op")
        async def async_function():
            await asyncio.sleep(0.01)
            return "async_result"

        result = await async_function()
        assert result == "async_result"

    def test_get_summary(self):
        """测试获取摘要"""
        from src.agents_v2.unified.monitoring import PerformanceMonitor

        monitor = PerformanceMonitor()
        summary = monitor.get_summary()

        assert "stats" in summary
        assert "timestamp" in summary


class TestConcurrentExecutor:
    """测试并发执行器"""

    def test_executor_init(self):
        """测试执行器初始化"""
        from src.agents_v2.unified.monitoring import ConcurrentExecutor

        executor = ConcurrentExecutor(max_concurrent=5)
        assert executor.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_execute_tasks(self):
        """测试执行多个任务"""
        from src.agents_v2.unified.monitoring import ConcurrentExecutor

        executor = ConcurrentExecutor(max_concurrent=3)

        async def task(i):
            await asyncio.sleep(0.01)
            return i * 2

        tasks = [lambda i=i: task(i) for i in range(5)]
        results = await executor.execute(tasks)

        # 过滤异常
        valid_results = [r for r in results if not isinstance(r, Exception)]
        assert len(valid_results) == 5

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """测试带超时执行"""
        from src.agents_v2.unified.monitoring import ConcurrentExecutor

        executor = ConcurrentExecutor(max_concurrent=2)

        async def slow_task():
            await asyncio.sleep(0.05)
            return "done"

        tasks = [slow_task for _ in range(2)]
        results = await executor.execute(tasks, timeout=0.1)

        # 任务应该完成
        assert len(results) == 2


class TestBatchProcessor:
    """测试批处理器"""

    def test_batch_processor_init(self):
        """测试批处理器初始化"""
        from src.agents_v2.unified.monitoring import BatchProcessor

        processor = BatchProcessor(batch_size=5, max_wait_ms=100)
        assert processor.batch_size == 5

    @pytest.mark.asyncio
    async def test_add_to_batch(self):
        """测试添加项目到批次"""
        from src.agents_v2.unified.monitoring import BatchProcessor

        processor = BatchProcessor(batch_size=3)

        async def process(item):
            return item * 2

        # 添加3个项目，触发批次处理
        results = []
        for i in range(3):
            result = await processor.add(i, process)
            if result:
                results.extend(result)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_flush(self):
        """测试清空批次"""
        from src.agents_v2.unified.monitoring import BatchProcessor

        processor = BatchProcessor(batch_size=10)

        async def process(item):
            return item * 2

        for i in range(3):
            await processor.add(i, process)

        results = await processor.flush()
        assert len(results) == 3


class TestGlobalMetrics:
    """测试全局指标"""

    def test_get_global_metrics(self):
        """测试获取全局指标"""
        from src.agents_v2.unified.monitoring import get_global_metrics

        metrics = get_global_metrics()
        assert metrics is not None
        assert hasattr(metrics, 'record')

    def test_record_global_metric(self):
        """测试记录全局指标"""
        from src.agents_v2.unified.monitoring import record_metric

        record_metric("global_test", 1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
