"""
Performance Benchmark Tests

Tests for:
- PerformanceBenchmark: Performance testing
- LoadTester: Load testing
"""
import pytest
import asyncio
from src.agents_v2.evaluation.performance_benchmark import (
    PerformanceBenchmark,
    LoadTester,
    LatencyStats,
    ThroughputStats,
    ResourceStats,
    BenchmarkType,
    benchmark_function,
    run_load_test
)


class TestLatencyStats:
    """LatencyStats Tests"""

    def test_create_latency_stats(self):
        """Test creating latency stats"""
        stats = LatencyStats(
            mean=100.0,
            median=95.0,
            p50=95.0,
            p90=150.0,
            p95=180.0,
            p99=200.0,
            min=50.0,
            max=250.0,
            std_dev=30.0
        )
        assert stats.mean == 100.0
        assert stats.p95 == 180.0


class TestThroughputStats:
    """ThroughputStats Tests"""

    def test_create_throughput_stats(self):
        """Test creating throughput stats"""
        stats = ThroughputStats(
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            requests_per_second=100.0,
            avg_latency=10.0
        )
        assert stats.total_requests == 1000
        assert stats.requests_per_second == 100.0


class TestResourceStats:
    """ResourceStats Tests"""

    def test_create_resource_stats(self):
        """Test creating resource stats"""
        stats = ResourceStats(
            cpu_percent_avg=50.0,
            cpu_percent_max=80.0,
            memory_mb_avg=512.0,
            memory_mb_max=1024.0,
            memory_percent_avg=25.0
        )
        assert stats.cpu_percent_avg == 50.0
        assert stats.memory_mb_avg == 512.0


class TestPerformanceBenchmark:
    """PerformanceBenchmark Tests"""

    def setup_method(self):
        self.benchmark = PerformanceBenchmark()

    @pytest.mark.asyncio
    async def test_benchmark_latency_sync_function(self):
        """Test benchmarking sync function"""
        def sync_func():
            return sum(range(100))

        result = await self.benchmark.benchmark_latency(
            sync_func,
            iterations=10,
            name="sync_test"
        )
        assert result.benchmark_name == "sync_test"
        assert result.benchmark_type == BenchmarkType.LATENCY
        assert result.iterations == 10
        assert result.latency is not None

    @pytest.mark.asyncio
    async def test_benchmark_latency_async_function(self):
        """Test benchmarking async function"""
        async def async_func():
            await asyncio.sleep(0.001)
            return sum(range(100))

        result = await self.benchmark.benchmark_latency(
            async_func,
            iterations=10,
            name="async_test"
        )
        assert result.benchmark_name == "async_test"
        assert result.benchmark_type == BenchmarkType.LATENCY

    @pytest.mark.asyncio
    async def test_benchmark_with_args(self):
        """Test benchmarking with arguments"""
        def func_with_args(a, b):
            return a + b

        result = await self.benchmark.benchmark_latency(
            func_with_args,
            args=(1, 2),
            iterations=5,
            name="args_test"
        )
        assert result.iterations == 5

    @pytest.mark.asyncio
    async def test_benchmark_throughput(self):
        """Test throughput benchmarking"""
        async def simple_func():
            await asyncio.sleep(0.01)

        result = await self.benchmark.benchmark_throughput(
            simple_func,
            duration_seconds=0.5,
            concurrency=2,
            name="throughput_test"
        )
        assert result.benchmark_name == "throughput_test"
        assert result.benchmark_type == BenchmarkType.THROUGHPUT
        assert result.throughput is not None

    def test_get_results_summary_empty(self):
        """Test getting summary with no results"""
        summary = self.benchmark.get_results_summary()
        assert summary["total_benchmarks"] == 0

    def test_get_results_summary_with_results(self):
        """Test getting summary with results"""
        # Run a benchmark first
        import time
        def quick_func():
            time.sleep(0.001)

        async def run():
            await self.benchmark.benchmark_latency(quick_func, iterations=3, name="test")

        asyncio.run(run())

        summary = self.benchmark.get_results_summary()
        assert summary["total_benchmarks"] >= 1


class TestLoadTester:
    """LoadTester Tests"""

    def setup_method(self):
        self.tester = LoadTester()

    @pytest.mark.asyncio
    async def test_run_load_test(self):
        """Test running load test"""
        async def simple_func():
            await asyncio.sleep(0.01)

        result = await self.tester.run_load_test(
            simple_func,
            {"users": 2, "duration": 0.5, "spawn_rate": 2}
        )

        assert "completed_requests" in result
        assert "requests_per_second" in result


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.mark.asyncio
    async def test_benchmark_function(self):
        """Test benchmark_function convenience"""
        def simple_func():
            return 1 + 1

        result = await benchmark_function(simple_func, iterations=5, name="convenience_test")
        assert result.benchmark_name == "convenience_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])