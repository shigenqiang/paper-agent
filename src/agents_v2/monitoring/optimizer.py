"""
Performance Optimizer - 性能优化器

提供性能监控、分析和优化建议。
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import time
import asyncio

logger = get_logging_logger(__name__)


class MetricType(str, Enum):
    """指标类型"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CPU = "cpu"
    ERROR_RATE = "error_rate"


@dataclass
class PerformanceMetric:
    """性能指标"""
    metric_type: MetricType
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceBenchmark:
    """性能基准"""
    name: str
    target: float
    threshold: float
    unit: str


class PerformanceOptimizer:
    """
    性能优化器

    功能:
    - 性能指标收集
    - 瓶颈分析
    - 优化建议生成

    使用示例:
        optimizer = PerformanceOptimizer()

        # 记录指标
        optimizer.record_metric(MetricType.LATENCY, 150, "ms", tags={"operation": "search"})

        # 分析瓶颈
        bottlenecks = optimizer.find_bottlenecks()

        # 获取建议
        suggestions = optimizer.get_optimization_suggestions()
    """

    # 默认基准
    DEFAULT_BENCHMARKS = {
        "intent_routing": PerformanceBenchmark("intent_routing", 50, 100, "ms"),
        "llm_call_simple": PerformanceBenchmark("llm_call_simple", 500, 1000, "ms"),
        "llm_call_complex": PerformanceBenchmark("llm_call_complex", 2000, 5000, "ms"),
        "memory_retrieval": PerformanceBenchmark("memory_retrieval", 30, 100, "ms"),
        "tool_execution": PerformanceBenchmark("tool_execution", 200, 500, "ms"),
    }

    def __init__(self):
        self._metrics: List[PerformanceMetric] = []
        self._benchmarks = self.DEFAULT_BENCHMARKS.copy()
        self._bottleneck_cache: Optional[List[str]] = None
        self._last_analysis_time = 0

    def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        unit: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """记录性能指标"""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        self._metrics.append(metric)

        # 清理旧指标（保留最近10000条）
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-10000:]

    def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        since: Optional[float] = None,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """获取指标"""
        metrics = self._metrics

        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]

        if since:
            metrics = [m for m in metrics if m.timestamp >= since]

        if tags:
            metrics = [
                m for m in metrics
                if all(m.tags.get(k) == v for k, v in tags.items())
            ]

        return metrics[-limit:]

    def get_latency_stats(
        self,
        operation: Optional[str] = None
    ) -> Dict[str, float]:
        """获取延迟统计"""
        metrics = self.get_metrics(MetricType.LATENCY)

        if operation:
            metrics = [m for m in metrics if m.tags.get("operation") == operation]

        if not metrics:
            return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

        values = sorted([m.value for m in metrics])
        count = len(values)

        return {
            "count": count,
            "avg": sum(values) / count,
            "min": values[0],
            "max": values[-1],
            "p50": values[int(count * 0.5)],
            "p95": values[int(count * 0.95)] if count > 20 else values[-1],
            "p99": values[int(count * 0.99)] if count > 100 else values[-1],
        }

    def get_throughput_stats(self) -> Dict[str, float]:
        """获取吞吐量统计"""
        metrics = self.get_metrics(MetricType.THROUGHPUT)

        if not metrics:
            return {"count": 0, "rate": 0}

        # 按时间窗口计算
        if len(metrics) < 2:
            return {"count": len(metrics), "rate": 0}

        time_span = metrics[-1].timestamp - metrics[0].timestamp
        if time_span <= 0:
            return {"count": len(metrics), "rate": 0}

        rate = len(metrics) / time_span  # per second

        return {
            "count": len(metrics),
            "time_span_seconds": time_span,
            "rate_per_second": rate,
            "rate_per_minute": rate * 60
        }

    def check_benchmark(
        self,
        benchmark_name: str,
        value: float
    ) -> Tuple[bool, str]:
        """
        检查是否达到基准

        Returns:
            (是否达标, 状态描述)
        """
        benchmark = self._benchmarks.get(benchmark_name)
        if not benchmark:
            return True, "no_benchmark"

        if value <= benchmark.target:
            return True, "target_met"
        elif value <= benchmark.threshold:
            return True, "threshold_met"
        else:
            return False, "exceeded"

    def find_bottlenecks(self) -> List[str]:
        """查找性能瓶颈"""
        bottlenecks = []

        # 分析延迟
        latency_stats = self.get_latency_stats()
        if latency_stats["count"] > 0:
            if latency_stats["p95"] > 1000:
                bottlenecks.append(f"High P95 latency: {latency_stats['p95']:.0f}ms")
            if latency_stats["avg"] > 500:
                bottlenecks.append(f"High average latency: {latency_stats['avg']:.0f}ms")

        # 分析吞吐量
        throughput_stats = self.get_throughput_stats()
        if throughput_stats["count"] > 10:
            if throughput_stats["rate_per_second"] < 1:
                bottlenecks.append(f"Low throughput: {throughput_stats['rate_per_second']:.2f} req/s")

        # 分析错误率
        error_metrics = self.get_metrics(MetricType.ERROR_RATE)
        if error_metrics:
            error_count = sum(1 for m in error_metrics if m.value > 0)
            error_rate = error_count / len(error_metrics) if error_metrics else 0
            if error_rate > 0.05:  # 5%
                bottlenecks.append(f"High error rate: {error_rate * 100:.1f}%")

        return bottlenecks

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取优化建议"""
        suggestions = []
        bottlenecks = self.find_bottlenecks()

        for bottleneck in bottlenecks:
            if "latency" in bottleneck.lower():
                suggestions.append({
                    "issue": "High latency",
                    "suggestions": [
                        "Consider adding caching",
                        "Optimize database queries",
                        "Use connection pooling",
                        "Enable async operations"
                    ],
                    "priority": "high"
                })
            elif "throughput" in bottleneck.lower():
                suggestions.append({
                    "issue": "Low throughput",
                    "suggestions": [
                        "Enable request batching",
                        "Scale horizontally",
                        "Optimize hot paths",
                        "Reduce lock contention"
                    ],
                    "priority": "medium"
                })
            elif "error" in bottleneck.lower():
                suggestions.append({
                    "issue": "High error rate",
                    "suggestions": [
                        "Add retry logic",
                        "Implement circuit breaker",
                        "Improve input validation",
                        "Add better error handling"
                    ],
                    "priority": "high"
                })

        return suggestions

    def create_timer(
        self,
        operation: str,
        tags: Optional[Dict[str, str]] = None
    ) -> "OperationTimer":
        """创建操作计时器"""
        return OperationTimer(self, operation, tags)


class OperationTimer:
    """操作计时器"""

    def __init__(
        self,
        optimizer: PerformanceOptimizer,
        operation: str,
        tags: Optional[Dict[str, str]] = None
    ):
        self.optimizer = optimizer
        self.operation = operation
        self.tags = tags or {}
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            tags = {**self.tags, "operation": self.operation}
            self.optimizer.record_metric(
                MetricType.LATENCY,
                duration_ms,
                "ms",
                tags
            )

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            tags = {**self.tags, "operation": self.operation}
            self.optimizer.record_metric(
                MetricType.LATENCY,
                duration_ms,
                "ms",
                tags
            )


class CachedOperation:
    """缓存操作结果"""

    def __init__(
        self,
        cache: Dict[str, Any],
        key: str,
        ttl_seconds: float = 60
    ):
        self.cache = cache
        self.key = key
        self.ttl_seconds = ttl_seconds

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # 缓存写入在结果计算后手动调用


def create_optimizer() -> PerformanceOptimizer:
    """创建性能优化器"""
    return PerformanceOptimizer()
