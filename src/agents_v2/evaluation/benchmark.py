"""
基准测试套件 - Benchmark Suite

提供:
- LatencyBenchmark: 延迟基准测试
- ThroughputBenchmark: 吞吐量基准测试
- MemoryBenchmark: 记忆系统基准测试
- AgentBenchmark: Agent性能基准测试
"""
import asyncio
import time
import psutil
import os
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, median, stdev


@dataclass
class LatencyReport:
    """延迟报告"""
    operation: str
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float


@dataclass
class ThroughputReport:
    """吞吐量报告"""
    operation: str
    total_items: int
    duration_seconds: float
    items_per_second: float
    avg_latency_ms: float


@dataclass
class MemoryBenchmarkReport:
    """记忆系统基准报告"""
    operation: str
    memory_before_mb: float
    memory_after_mb: float
    memory_delta_mb: float
    avg_latency_ms: float
    throughput: float


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    timestamp: datetime
    duration_ms: float
    metrics: Dict[str, Any]
    passed: bool
    details: Optional[Dict[str, Any]] = None


class LatencyBenchmark:
    """
    延迟基准测试

    测试各种操作的延迟情况
    """

    def __init__(self, warmup_runs: int = 3, runs: int = 100):
        self.warmup_runs = warmup_runs
        self.runs = runs

    async def run(
        self,
        operation: Callable,
        operation_name: str = "operation"
    ) -> LatencyReport:
        """
        运行延迟基准测试

        Args:
            operation: 异步操作函数
            operation_name: 操作名称

        Returns:
            LatencyReport
        """
        latencies = []

        # 预热
        for _ in range(self.warmup_runs):
            await operation()

        # 正式测试
        for _ in range(self.runs):
            start = time.perf_counter()
            await operation()
            elapsed = (time.perf_counter() - start) * 1000  # 转换为毫秒
            latencies.append(elapsed)

        latencies.sort()

        return LatencyReport(
            operation=operation_name,
            count=len(latencies),
            min_ms=latencies[0],
            max_ms=latencies[-1],
            mean_ms=mean(latencies),
            median_ms=median(latencies),
            p95_ms=latencies[int(len(latencies) * 0.95)],
            p99_ms=latencies[int(len(latencies) * 0.99)],
            std_dev_ms=stdev(latencies) if len(latencies) > 1 else 0
        )


class ThroughputBenchmark:
    """
    吞吐量基准测试

    测试单位时间内的处理量
    """

    def __init__(self, duration_seconds: float = 5.0):
        self.duration_seconds = duration_seconds

    async def run(
        self,
        operation: Callable,
        operation_name: str = "operation"
    ) -> ThroughputReport:
        """
        运行吞吐量基准测试

        Args:
            operation: 异步操作函数
            operation_name: 操作名称

        Returns:
            ThroughputReport
        """
        count = 0
        latencies = []
        start_time = time.perf_counter()
        end_time = start_time + self.duration_seconds

        while time.perf_counter() < end_time:
            op_start = time.perf_counter()
            await operation()
            op_elapsed = (time.perf_counter() - op_start) * 1000
            latencies.append(op_elapsed)
            count += 1

        total_duration = time.perf_counter() - start_time

        return ThroughputReport(
            operation=operation_name,
            total_items=count,
            duration_seconds=total_duration,
            items_per_second=count / total_duration if total_duration > 0 else 0,
            avg_latency_ms=mean(latencies) if latencies else 0
        )


class MemoryBenchmark:
    """
    记忆系统基准测试

    测试记忆系统的内存使用和性能
    """

    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def get_memory_mb(self) -> float:
        """获取当前内存使用(MB)"""
        return self.process.memory_info().rss / 1024 / 1024

    async def run_memory_operation(
        self,
        operation: Callable,
        operation_name: str = "memory_operation"
    ) -> MemoryBenchmarkReport:
        """
        运行内存操作基准测试

        Args:
            operation: 异步操作函数
            operation_name: 操作名称

        Returns:
            MemoryBenchmarkReport
        """
        mem_before = self.get_memory_mb()

        start = time.perf_counter()
        await operation()
        duration_ms = (time.perf_counter() - start) * 1000

        mem_after = self.get_memory_mb()

        return MemoryBenchmarkReport(
            operation=operation_name,
            memory_before_mb=mem_before,
            memory_after_mb=mem_after,
            memory_delta_mb=mem_after - mem_before,
            avg_latency_ms=duration_ms,
            throughput=1000 / duration_ms if duration_ms > 0 else 0
        )


class BenchmarkRunner:
    """
    基准测试运行器

    运行多种基准测试并生成报告
    """

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.latency_benchmark = LatencyBenchmark()
        self.throughput_benchmark = ThroughputBenchmark()
        self.memory_benchmark = MemoryBenchmark()

    async def run_latency_test(
        self,
        name: str,
        operation: Callable,
        threshold_ms: float = 100.0
    ) -> BenchmarkResult:
        """
        运行延迟测试

        Args:
            name: 测试名称
            operation: 操作函数
            threshold_ms: 阈值(毫秒)

        Returns:
            BenchmarkResult
        """
        start = time.perf_counter()
        report = await self.latency_benchmark.run(operation, name)
        duration_ms = (time.perf_counter() - start) * 1000

        passed = report.mean_ms < threshold_ms

        result = BenchmarkResult(
            name=name,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            metrics={
                "min_ms": report.min_ms,
                "max_ms": report.max_ms,
                "mean_ms": report.mean_ms,
                "median_ms": report.median_ms,
                "p95_ms": report.p95_ms,
                "p99_ms": report.p99_ms
            },
            passed=passed,
            details={"threshold_ms": threshold_ms}
        )

        self.results.append(result)
        return result

    async def run_throughput_test(
        self,
        name: str,
        operation: Callable,
        min_throughput: float = 10.0
    ) -> BenchmarkResult:
        """
        运行吞吐量测试

        Args:
            name: 测试名称
            operation: 操作函数
            min_throughput: 最小吞吐量

        Returns:
            BenchmarkResult
        """
        start = time.perf_counter()
        report = await self.throughput_benchmark.run(operation, name)
        duration_ms = (time.perf_counter() - start) * 1000

        passed = report.items_per_second >= min_throughput

        result = BenchmarkResult(
            name=name,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            metrics={
                "total_items": report.total_items,
                "items_per_second": report.items_per_second,
                "avg_latency_ms": report.avg_latency_ms
            },
            passed=passed,
            details={"min_throughput": min_throughput}
        )

        self.results.append(result)
        return result

    async def run_memory_test(
        self,
        name: str,
        operation: Callable,
        max_memory_delta_mb: float = 100.0
    ) -> BenchmarkResult:
        """
        运行内存测试

        Args:
            name: 测试名称
            operation: 操作函数
            max_memory_delta_mb: 最大内存增量

        Returns:
            BenchmarkResult
        """
        start = time.perf_counter()
        report = await self.memory_benchmark.run_memory_operation(operation, name)
        duration_ms = (time.perf_counter() - start) * 1000

        passed = abs(report.memory_delta_mb) < max_memory_delta_mb

        result = BenchmarkResult(
            name=name,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            metrics={
                "memory_before_mb": report.memory_before_mb,
                "memory_after_mb": report.memory_after_mb,
                "memory_delta_mb": report.memory_delta_mb,
                "avg_latency_ms": report.avg_latency_ms
            },
            passed=passed,
            details={"max_memory_delta_mb": max_memory_delta_mb}
        )

        self.results.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """获取基准测试总结"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)

        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "metrics": r.metrics
                }
                for r in self.results
            ]
        }
