"""
性能监控 - 监控和指标收集

提供:
1. MetricsCollector: 指标收集器
2. PerformanceMonitor: 性能监控器
3. 并发优化工具
"""
import time
import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    指标收集器

    使用方式:
        collector = MetricsCollector()
        collector.record("llm_calls", 1, tags={"agent": "topic"})
        collector.record("latency", 0.5, tags={"operation": "execute"})

        stats = collector.get_stats()
        print(f"Total calls: {stats['llm_calls']['count']}")
    """

    def __init__(self):
        self._metrics: List[Metric] = []
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}

    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录指标"""
        metric = Metric(name=name, value=value, tags=tags or {})
        self._metrics.append(metric)

        # 更新计数器
        if name not in self._counters:
            self._counters[name] = 0
        self._counters[name] += 1

        # 更新直方图
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)

    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """增加计数器"""
        self.record(name, float(value), tags)

    def gauge(self, name: str, value: float):
        """设置仪表值"""
        self._gauges[name] = value

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "counters": self._counters.copy(),
            "gauges": self._gauges.copy(),
            "histograms": {}
        }

        for name, values in self._histograms.items():
            if values:
                sorted_values = sorted(values)
                stats["histograms"][name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": sorted_values[len(sorted_values) // 2],
                    "p95": sorted_values[int(len(sorted_values) * 0.95)] if len(sorted_values) > 1 else sorted_values[0],
                    "p99": sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) > 1 else sorted_values[0],
                }

        return stats

    def clear(self):
        """清空指标"""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


class PerformanceMonitor:
    """
    性能监控器 - 监控函数执行性能

    使用方式:
        monitor = PerformanceMonitor()

        @monitor.track("my_operation")
        async def my_function():
            await do_work()

        @monitor.track_sync("sync_operation")
        def sync_function():
            do_work()
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics = metrics_collector or MetricsCollector()
        self._active_operations: Dict[str, float] = {}

    def track(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """装饰器：跟踪异步操作"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                self._active_operations[operation_name] = start_time

                try:
                    result = await func(*args, **kwargs)
                    latency = time.time() - start_time
                    self.metrics.record(f"{operation_name}_latency", latency, tags)
                    self.metrics.increment(f"{operation_name}_success", tags=tags)
                    return result
                except Exception as e:
                    latency = time.time() - start_time
                    self.metrics.record(f"{operation_name}_latency", latency, tags)
                    self.metrics.increment(f"{operation_name}_error", tags=tags)
                    raise

            return wrapper
        return decorator

    def track_sync(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """装饰器：跟踪同步操作"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    latency = time.time() - start_time
                    self.metrics.record(f"{operation_name}_latency", latency, tags)
                    self.metrics.increment(f"{operation_name}_success", tags=tags)
                    return result
                except Exception as e:
                    latency = time.time() - start_time
                    self.metrics.record(f"{operation_name}_latency", latency, tags)
                    self.metrics.increment(f"{operation_name}_error", tags=tags)
                    raise

            return wrapper
        return decorator

    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        stats = self.metrics.get_stats()
        return {
            "operations": list(self._active_operations.keys()),
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }


class ConcurrentExecutor:
    """
    并发执行器 - 优化并发处理

    提供:
    1. 并发限制 (Semaphore)
    2. 超时控制
    3. 结果聚合
    """

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(
        self,
        tasks: List[Callable],
        timeout: Optional[float] = None
    ) -> List[Any]:
        """
        并发执行多个任务

        Args:
            tasks: 任务函数列表
            timeout: 超时时间（秒）

        Returns:
            结果列表
        """
        async def bounded_task(task):
            async with self._semaphore:
                if inspect.iscoroutinefunction(task):
                    return await task()
                return task()

        if timeout:
            results = await asyncio.wait_for(
                asyncio.gather(*[bounded_task(t) for t in tasks], return_exceptions=True),
                timeout=timeout
            )
        else:
            results = await asyncio.gather(
                *[bounded_task(t) for t in tasks],
                return_exceptions=True
            )

        return results

    async def execute_with_retry(
        self,
        task: Callable,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Any:
        """带重试的任务执行"""
        last_error = None

        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    if inspect.iscoroutinefunction(task):
                        return await task()
                    return task()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

        raise last_error


class BatchProcessor:
    """
    批处理器 - 批量处理优化

    将多个小任务合并为一个批量任务，减少LLM调用次数
    """

    def __init__(self, batch_size: int = 5, max_wait_ms: float = 100):
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms
        self._pending: List[tuple] = []
        self._results: Dict[int, Any] = {}

    async def add(self, item: Any, process_func: Callable) -> Any:
        """
        添加项目到批次

        Args:
            item: 要处理的项目
            process_func: 处理函数

        Returns:
            处理结果
        """
        task_id = len(self._pending)
        self._pending.append((item, process_func))

        if len(self._pending) >= self.batch_size:
            return await self._process_batch()

        return None

    async def _process_batch(self) -> List[Any]:
        """处理当前批次"""
        if not self._pending:
            return []

        batch = self._pending[:self.batch_size]
        self._pending = self._pending[self.batch_size:]

        async def process(item_func):
            item, func = item_func
            return await func(item) if inspect.iscoroutinefunction(func) else func(item)

        results = await asyncio.gather(
            *[process(item_func) for item_func in batch],
            return_exceptions=True
        )

        return results

    async def flush(self) -> List[Any]:
        """处理所有待处理项目"""
        results = []
        while self._pending:
            batch_results = await self._process_batch()
            results.extend(batch_results)
        return results


# 全局指标收集器
_global_metrics = MetricsCollector()


def get_global_metrics() -> MetricsCollector:
    """获取全局指标收集器"""
    return _global_metrics


def record_metric(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """记录全局指标"""
    _global_metrics.record(name, value, tags)


def increment_metric(name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
    """增加全局计数器"""
    _global_metrics.increment(name, value, tags)
