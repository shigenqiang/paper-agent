"""
Latency Tracker - 延迟跟踪器

跟踪各组件的延迟情况。
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


@dataclass
class LatencyRecord:
    """延迟记录"""
    component: str
    operation: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0


@dataclass
class LatencyStats:
    """延迟统计"""
    component: str
    count: int = 0
    total_ms: float = 0.0
    avg_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    error_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "count": self.count,
            "total_ms": self.total_ms,
            "avg_ms": self.avg_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "error_rate": self.error_rate
        }


class LatencyTracker:
    """
    延迟跟踪器

    功能:
    - 记录操作延迟
    - 统计分析
    - 性能告警

    使用示例:
        tracker = LatencyTracker()

        with tracker.track("Retriever", "search"):
            # 执行操作
            pass

        stats = tracker.get_stats("Retriever")
    """

    def __init__(self, slow_threshold_ms: float = 5000):
        """
        初始化延迟跟踪器

        Args:
            slow_threshold_ms: 慢操作阈值（毫秒）
        """
        self.slow_threshold_ms = slow_threshold_ms
        self._records: List[LatencyRecord] = []
        self._component_records: Dict[str, List[LatencyRecord]] = defaultdict(list)

    def track(self, component: str, operation: str):
        """追踪操作的上下文管理器"""
        return LatencyContext(self, component, operation)

    def record(
        self,
        component: str,
        operation: str,
        start_time: datetime,
        end_time: datetime,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录延迟"""
        duration_ms = (end_time - start_time).total_seconds() * 1000

        record = LatencyRecord(
            component=component,
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {}
        )

        self._records.append(record)
        self._component_records[component].append(record)

    def get_stats(self, component: Optional[str] = None) -> Dict[str, LatencyStats]:
        """获取统计信息"""
        if component:
            records = self._component_records.get(component, [])
            return {component: self._calc_stats(component, records)}

        stats = {}
        for comp, records in self._component_records.items():
            stats[comp] = self._calc_stats(comp, records)
        return stats

    def _calc_stats(self, component: str, records: List[LatencyRecord]) -> LatencyStats:
        """计算统计信息"""
        if not records:
            return LatencyStats(component=component)

        durations = [r.duration_ms for r in records]
        errors = sum(1 for r in records if not r.success)

        sorted_durations = sorted(durations)
        n = len(sorted_durations)

        return LatencyStats(
            component=component,
            count=n,
            total_ms=sum(durations),
            avg_ms=statistics.mean(durations),
            min_ms=min(durations),
            max_ms=max(durations),
            p50_ms=sorted_durations[int(n * 0.5)] if n > 0 else 0,
            p95_ms=sorted_durations[int(n * 0.95)] if n > 0 else 0,
            p99_ms=sorted_durations[int(n * 0.99)] if n > 0 else 0,
            error_rate=errors / n if n > 0 else 0
        )

    def get_slow_operations(self, threshold_ms: Optional[float] = None) -> List[LatencyRecord]:
        """获取慢操作"""
        threshold = threshold_ms or self.slow_threshold_ms
        return [r for r in self._records if r.duration_ms > threshold]

    def get_recent(self, minutes: int = 5) -> List[LatencyRecord]:
        """获取最近的操作记录"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [r for r in self._records if r.start_time >= cutoff]

    def detect_slow_components(self) -> List[Dict[str, Any]]:
        """检测慢组件"""
        slow = []
        stats = self.get_stats()

        for comp, stat in stats.items():
            if stat.avg_ms > self.slow_threshold_ms:
                slow.append({
                    "component": comp,
                    "avg_ms": stat.avg_ms,
                    "max_ms": stat.max_ms,
                    "p95_ms": stat.p95_ms
                })

        return sorted(slow, key=lambda x: x["avg_ms"], reverse=True)

    def clear(self):
        """清除记录"""
        self._records.clear()
        self._component_records.clear()


class LatencyContext:
    """延迟追踪上下文"""

    def __init__(self, tracker: LatencyTracker, component: str, operation: str):
        self.tracker = tracker
        self.component = component
        self.operation = operation
        self.start_time: Optional[datetime] = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        success = exc_type is None

        self.tracker.record(
            component=self.component,
            operation=self.operation,
            start_time=self.start_time,
            end_time=end_time,
            success=success,
            metadata={"error": str(exc_val)} if exc_val else {}
        )


def create_tracker() -> LatencyTracker:
    """创建延迟跟踪器"""
    return LatencyTracker()