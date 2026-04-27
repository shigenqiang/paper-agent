"""
性能基准测试器 - Performance Benchmark

功能:
1. 性能指标基准测试
2. 延迟分布分析
3. 吞吐量测试
4. 资源使用监控

设计原则:
- 可重复的性能测试
- 多维度性能评估
- 自动化报告生成
"""
import asyncio
import time
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)


class BenchmarkType(str, Enum):
    """基准测试类型"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CPU = "cpu"
    COMBINED = "combined"


@dataclass
class LatencyStats:
    """延迟统计"""
    mean: float = 0.0
    median: float = 0.0
    p50: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    min: float = 0.0
    max: float = 0.0
    std_dev: float = 0.0


@dataclass
class ThroughputStats:
    """吞吐量统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    requests_per_second: float = 0.0
    avg_latency: float = 0.0


@dataclass
class ResourceStats:
    """资源使用统计"""
    cpu_percent_avg: float = 0.0
    cpu_percent_max: float = 0.0
    memory_mb_avg: float = 0.0
    memory_mb_max: float = 0.0
    memory_percent_avg: float = 0.0


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_name: str
    benchmark_type: BenchmarkType
    duration_seconds: float
    iterations: int
    latency: Optional[LatencyStats] = None
    throughput: Optional[ThroughputStats] = None
    resources: Optional[ResourceStats] = None
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmark:
    """性能基准测试器"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    async def benchmark_latency(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        iterations: int = 100,
        warmup_iterations: int = 10,
        name: str = "latency_test"
    ) -> BenchmarkResult:
        """延迟基准测试

        Args:
            func: 待测试函数
            args: 位置参数
            kwargs: 关键字参数
            iterations: 测试迭代次数
            warmup_iterations: 预热迭代次数
            name: 测试名称

        Returns:
            BenchmarkResult: 测试结果
        """
        kwargs = kwargs or {}

        # 预热
        for _ in range(warmup_iterations):
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            except Exception:
                pass

        # 正式测试
        latencies = []
        start_time = time.time()

        for _ in range(iterations):
            iter_start = time.time()
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
                latencies.append((time.time() - iter_start) * 1000)  # 转换为毫秒
            except Exception as e:
                logger.warning(f"Benchmark iteration failed: {e}")

        duration = time.time() - start_time

        # 计算统计
        latency_stats = self._calculate_latency_stats(latencies)

        result = BenchmarkResult(
            benchmark_name=name,
            benchmark_type=BenchmarkType.LATENCY,
            duration_seconds=duration,
            iterations=iterations,
            latency=latency_stats,
            success_rate=len(latencies) / iterations
        )

        self.results.append(result)
        return result

    async def benchmark_throughput(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        duration_seconds: float = 10.0,
        concurrency: int = 10,
        name: str = "throughput_test"
    ) -> BenchmarkResult:
        """吞吐量基准测试

        Args:
            func: 待测试函数
            args: 位置参数
            kwargs: 关键字参数
            duration_seconds: 测试持续时间
            concurrency: 并发数
            name: 测试名称

        Returns:
            BenchmarkResult: 测试结果
        """
        kwargs = kwargs or {}

        start_time = time.time()
        end_time = start_time + duration_seconds

        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        total_latency = 0.0

        async def worker():
            nonlocal total_requests, successful_requests, failed_requests, total_latency

            while time.time() < end_time:
                iter_start = time.time()
                total_requests += 1

                try:
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        func(*args, **kwargs)
                    successful_requests += 1
                except Exception:
                    failed_requests += 1

                total_latency += (time.time() - iter_start)

        # 启动并发worker
        tasks = [worker() for _ in range(concurrency)]
        await asyncio.gather(*tasks)

        actual_duration = time.time() - start_time

        throughput_stats = ThroughputStats(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=total_requests / actual_duration if actual_duration > 0 else 0,
            avg_latency=(total_latency / total_requests * 1000) if total_requests > 0 else 0
        )

        result = BenchmarkResult(
            benchmark_name=name,
            benchmark_type=BenchmarkType.THROUGHPUT,
            duration_seconds=actual_duration,
            iterations=total_requests,
            throughput=throughput_stats,
            success_rate=successful_requests / total_requests if total_requests > 0 else 0
        )

        self.results.append(result)
        return result

    async def benchmark_resource_usage(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        iterations: int = 50,
        sample_interval: float = 0.1,
        name: str = "resource_test"
    ) -> BenchmarkResult:
        """资源使用基准测试

        Args:
            func: 待测试函数
            args: 位置参数
            kwargs: 关键字参数
            iterations: 测试迭代次数
            sample_interval: 采样间隔
            name: 测试名称

        Returns:
            BenchmarkResult: 测试结果
        """
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, resource monitoring disabled")
            # Return a result without resource stats
            result = BenchmarkResult(
                benchmark_name=name,
                benchmark_type=BenchmarkType.MEMORY,
                duration_seconds=0,
                iterations=iterations,
                resources=None,
                metadata={"psutil_available": False}
            )
            self.results.append(result)
            return result

        kwargs = kwargs or {}

        process = psutil.Process()
        cpu_samples = []
        memory_samples = []

        start_time = time.time()

        for _ in range(iterations):
            # 采样前
            cpu_before = process.cpu_percent()
            mem_before = process.memory_info().rss / 1024 / 1024  # MB

            # 执行
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)

            # 采样后
            await asyncio.sleep(sample_interval)
            cpu_after = process.cpu_percent()
            mem_after = process.memory_info().rss / 1024 / 1024

            cpu_samples.append((cpu_before + cpu_after) / 2)
            memory_samples.append(mem_after)

        duration = time.time() - start_time

        resource_stats = ResourceStats(
            cpu_percent_avg=statistics.mean(cpu_samples) if cpu_samples else 0,
            cpu_percent_max=max(cpu_samples) if cpu_samples else 0,
            memory_mb_avg=statistics.mean(memory_samples) if memory_samples else 0,
            memory_mb_max=max(memory_samples) if memory_samples else 0,
            memory_percent_avg=0  # 可根据系统总内存计算
        )

        result = BenchmarkResult(
            benchmark_name=name,
            benchmark_type=BenchmarkType.MEMORY,
            duration_seconds=duration,
            iterations=iterations,
            resources=resource_stats,
            metadata={"sample_count": len(cpu_samples)}
        )

        self.results.append(result)
        return result

    def _calculate_latency_stats(self, latencies: List[float]) -> LatencyStats:
        """计算延迟统计"""
        if not latencies:
            return LatencyStats()

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return LatencyStats(
            mean=statistics.mean(latencies),
            median=statistics.median(latencies),
            p50=sorted_latencies[int(n * 0.5)] if n > 0 else 0,
            p90=sorted_latencies[int(n * 0.9)] if n > 0 else 0,
            p95=sorted_latencies[int(n * 0.95)] if n > 0 else 0,
            p99=sorted_latencies[int(n * 0.99)] if n > 0 else 0,
            min=min(latencies) if latencies else 0,
            max=max(latencies) if latencies else 0,
            std_dev=statistics.stdev(latencies) if len(latencies) > 1 else 0
        )

    def get_results_summary(self) -> Dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"total_benchmarks": 0}

        summary = {
            "total_benchmarks": len(self.results),
            "by_type": defaultdict(lambda: {"count": 0, "avg_duration": 0})
        }

        for result in self.results:
            btype = result.benchmark_type.value
            summary["by_type"][btype]["count"] += 1
            summary["by_type"][btype]["avg_duration"] += result.duration_seconds

        # 计算平均值
        for btype in summary["by_type"]:
            count = summary["by_type"][btype]["count"]
            if count > 0:
                summary["by_type"][btype]["avg_duration"] /= count

        return dict(summary)


class LoadTester:
    """负载测试器"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    async def run_load_test(
        self,
        func: Callable,
        load_profile: Dict[str, Any],
        name: str = "load_test"
    ) -> Dict[str, Any]:
        """运行负载测试

        Args:
            func: 待测试函数
            load_profile: 负载配置
                - users: 虚拟用户数
                - spawn_rate: 用户生成速率
                - duration: 测试持续时间

        Returns:
            Dict: 测试结果
        """
        users = load_profile.get("users", 10)
        spawn_rate = load_profile.get("spawn_rate", 1)
        duration = load_profile.get("duration", 60)

        start_time = time.time()
        end_time = start_time + duration

        active_users = 0
        completed_requests = 0
        failed_requests = 0
        user_tasks = []

        async def user_loop(user_id: int):
            nonlocal completed_requests, failed_requests

            while time.time() < end_time:
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func()
                    else:
                        func()
                    completed_requests += 1
                except Exception:
                    failed_requests += 1

                await asyncio.sleep(1 / spawn_rate)

        # 渐进启动用户
        for i in range(users):
            asyncio.create_task(user_loop(i))
            await asyncio.sleep(1 / spawn_rate)

        # 运行直到结束
        await asyncio.sleep(duration)

        actual_duration = time.time() - start_time

        result = {
            "name": name,
            "duration": actual_duration,
            "total_users": users,
            "completed_requests": completed_requests,
            "failed_requests": failed_requests,
            "requests_per_second": completed_requests / actual_duration if actual_duration > 0 else 0,
            "failure_rate": failed_requests / (completed_requests + failed_requests) if (completed_requests + failed_requests) > 0 else 0
        }

        self.results.append(result)
        return result


# 便捷函数
async def benchmark_function(
    func: Callable,
    iterations: int = 100,
    name: str = "benchmark"
) -> BenchmarkResult:
    """便捷基准测试函数"""
    benchmark = PerformanceBenchmark()
    return await benchmark.benchmark_latency(func, iterations=iterations, name=name)


async def run_load_test(
    func: Callable,
    users: int = 10,
    duration: float = 60
) -> Dict[str, Any]:
    """便捷负载测试函数"""
    tester = LoadTester()
    return await tester.run_load_test(
        func,
        {"users": users, "duration": duration}
    )