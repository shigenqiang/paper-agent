"""
记忆系统监控面板

提供:
- 统计收集 (MemoryStatsCollector)
- 性能监控 (MemoryPerformanceMonitor)
- 访问分析 (AccessAnalytics)
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from collections import defaultdict

from .types import MemoryType, MemoryEntry, ImportanceLevel

if TYPE_CHECKING:
    from .unified import UnifiedMemoryManager


@dataclass
class LayerStats:
    """单层记忆统计"""
    memory_type: MemoryType
    total_count: int
    size_bytes: int
    avg_importance: float
    importance_distribution: Dict[str, int]
    access_count: int
    last_accessed: float
    last_updated: float


@dataclass
class AccessStats:
    """访问统计"""
    total_accesses: int
    unique_keys: int
    hit_rate: float
    miss_rate: float
    avg_access_latency_ms: float


@dataclass
class RetrievalStats:
    """检索统计"""
    total_searches: int
    avg_results: float
    avg_latency_ms: float
    query_type_distribution: Dict[str, int]
    strategy_distribution: Dict[str, int]


@dataclass
class RetentionStats:
    """保留统计"""
    total_memories: int
    avg_retention_score: float
    below_threshold: int
    above_threshold: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


@dataclass
class MemorySystemStats:
    """完整记忆系统统计"""
    total_memories: int
    by_layer: Dict[str, int]
    size_bytes: int
    importance_distribution: Dict[str, int]
    access_stats: AccessStats
    retrieval_stats: RetrievalStats
    retention_stats: RetentionStats
    collected_at: float


class MemoryStatsCollector:
    """
    记忆系统统计收集器

    职责:
    - 收集各层记忆统计
    - 计算重要性分布
    - 分析访问模式
    - 生成报告
    """

    def __init__(self, memory_manager: Optional["UnifiedMemoryManager"] = None):
        self.memory_manager = memory_manager
        self._access_count = defaultdict(int)
        self._last_access_time: Dict[str, float] = {}
        self._retrieval_count = 0
        self._search_latencies: List[float] = []

    async def collect_all(self) -> MemorySystemStats:
        """
        收集所有统计

        Returns:
            MemorySystemStats
        """
        stats = MemorySystemStats(
            total_memories=0,
            by_layer={},
            size_bytes=0,
            importance_distribution={},
            access_stats=AccessStats(
                total_accesses=sum(self._access_count.values()),
                unique_keys=len(self._access_count),
                hit_rate=0.0,
                miss_rate=0.0,
                avg_access_latency_ms=0.0
            ),
            retrieval_stats=RetrievalStats(
                total_searches=self._retrieval_count,
                avg_results=0.0,
                avg_latency_ms=0.0,
                query_type_distribution={},
                strategy_distribution={}
            ),
            retention_stats=RetentionStats(
                total_memories=0,
                avg_retention_score=0.0,
                below_threshold=0,
                above_threshold=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0
            ),
            collected_at=time.time()
        )

        if not self.memory_manager:
            return stats

        # 收集各层统计
        layers = [
            (MemoryType.SHORT_TERM, "short_term"),
            (MemoryType.SESSION, "session"),
            (MemoryType.LONG_TERM, "long_term"),
            (MemoryType.EPISODIC, "episodic"),
            (MemoryType.USER_PROFILE, "user_profile"),
            (MemoryType.PROCEDURAL, "procedural")
        ]

        for mem_type, attr_name in layers:
            layer_stats = await self.get_layer_stats(mem_type)
            stats.by_layer[mem_type.value] = layer_stats.total_count
            stats.total_memories += layer_stats.total_count

            if layer_stats.importance_distribution:
                for level, count in layer_stats.importance_distribution.items():
                    stats.importance_distribution[level] = (
                        stats.importance_distribution.get(level, 0) + count
                    )

        return stats

    async def get_layer_stats(self, layer: MemoryType) -> LayerStats:
        """
        获取单层统计

        Args:
            layer: 记忆层类型

        Returns:
            LayerStats
        """
        stats = LayerStats(
            memory_type=layer,
            total_count=0,
            size_bytes=0,
            avg_importance=0.0,
            importance_distribution={},
            access_count=0,
            last_accessed=0.0,
            last_updated=0.0
        )

        if not self.memory_manager:
            return stats

        try:
            if layer == MemoryType.SHORT_TERM and hasattr(self.memory_manager, 'short_term'):
                # 短期记忆统计
                st = self.memory_manager.short_term
                if hasattr(st, '_storage'):
                    entries = list(st._storage.values())
                    stats.total_count = len(entries)
                    stats.size_bytes = sum(
                        len(str(e.content)) for e in entries
                    )
                    if entries:
                        stats.avg_importance = sum(e.importance for e in entries) / len(entries)

            elif layer == MemoryType.SESSION and hasattr(self.memory_manager, 'session'):
                # 会话记忆统计
                sess = self.memory_manager.session
                if hasattr(sess, 'messages'):
                    messages = await sess.get_messages(limit=10000)
                    stats.total_count = len(messages)

            elif layer == MemoryType.LONG_TERM and hasattr(self.memory_manager, 'long_term'):
                # 长期记忆统计
                lt = self.memory_manager.long_term
                if hasattr(lt, 'vector_store'):
                    all_keys = await lt.vector_store.list_all()
                    stats.total_count = len(all_keys)

            elif layer == MemoryType.EPISODIC and hasattr(self.memory_manager, 'episodic'):
                # 情景记忆统计
                ep = self.memory_manager.episodic
                ep_stats = ep.get_stats()
                stats.total_count = ep_stats.get("total_episodes", 0)

        except Exception:
            pass

        return stats

    async def get_retrieval_stats(self) -> RetrievalStats:
        """获取检索统计"""
        avg_latency = (
            sum(self._search_latencies) / len(self._search_latencies)
            if self._search_latencies else 0.0
        )

        return RetrievalStats(
            total_searches=self._retrieval_count,
            avg_results=0.0,
            avg_latency_ms=avg_latency,
            query_type_distribution={},
            strategy_distribution={}
        )

    def record_access(self, key: str) -> None:
        """记录记忆访问"""
        self._access_count[key] += 1
        self._last_access_time[key] = time.time()

    def record_search(self, latency_ms: float, results_count: int) -> None:
        """记录搜索操作"""
        self._retrieval_count += 1
        self._search_latencies.append(latency_ms)
        # 保留最近1000个延迟记录
        if len(self._search_latencies) > 1000:
            self._search_latencies = self._search_latencies[-1000:]

    def get_top_k_memories(self, k: int = 10) -> List[Dict[str, Any]]:
        """
        获取TOP-K最重要记忆

        Args:
            k: 返回数量

        Returns:
            TOP-K记忆列表
        """
        if not self.memory_manager:
            return []

        # 按访问次数排序
        sorted_keys = sorted(
            self._access_count.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_memories = []
        for key, count in sorted_keys[:k]:
            memory = asyncio.create_task(
                self.memory_manager.recall(key)
            )
            if memory:
                top_memories.append({
                    "key": key,
                    "access_count": count,
                    "last_accessed": self._last_access_time.get(key, 0)
                })

        return top_memories


class MemoryPerformanceMonitor:
    """
    记忆性能监控器

    职责:
    - 监控读写延迟
    - 检测性能瓶颈
    - 触发自动优化
    """

    def __init__(
        self,
        stats_collector: MemoryStatsCollector,
        alert_threshold_ms: float = 100.0
    ):
        self.stats_collector = stats_collector
        self.alert_threshold_ms = alert_threshold_ms
        self._slow_operations: List[Dict[str, Any]] = []
        self._operation_latencies: Dict[str, List[float]] = defaultdict(list)

    def record_operation(
        self,
        operation: str,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录操作延迟

        Args:
            operation: 操作类型 (remember, recall, search)
            latency_ms: 延迟(毫秒)
            metadata: 额外信息
        """
        self._operation_latencies[operation].append(latency_ms)

        # 记录慢操作
        if latency_ms > self.alert_threshold_ms:
            self._slow_operations.append({
                "operation": operation,
                "latency_ms": latency_ms,
                "timestamp": time.time(),
                "metadata": metadata or {}
            })

            # 保留最近100个慢操作
            if len(self._slow_operations) > 100:
                self._slow_operations = self._slow_operations[-100:]

    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """
        获取操作统计

        Args:
            operation: 操作类型

        Returns:
            {avg, min, max, p95, p99}
        """
        latencies = self._operation_latencies.get(operation, [])

        if not latencies:
            return {"avg": 0, "min": 0, "max": 0, "p95": 0, "p99": 0}

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return {
            "avg": sum(latencies) / n,
            "min": sorted_latencies[0],
            "max": sorted_latencies[-1],
            "p95": sorted_latencies[int(n * 0.95)] if n > 0 else 0,
            "p99": sorted_latencies[int(n * 0.99)] if n > 0 else 0
        }

    def get_slow_operations(
        self,
        limit: int = 10,
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        获取慢操作列表

        Args:
            limit: 返回数量
            since_timestamp: 可选的起始时间过滤

        Returns:
            慢操作列表
        """
        operations = self._slow_operations

        if since_timestamp:
            operations = [
                op for op in operations
                if op["timestamp"] >= since_timestamp
            ]

        return sorted(
            operations,
            key=lambda x: x["latency_ms"],
            reverse=True
        )[:limit]

    def should_trigger_optimization(self) -> tuple:
        """
        判断是否应该触发优化

        Returns:
            (should_optimize, reason)
        """
        # 检查平均延迟
        for operation, latencies in self._operation_latencies.items():
            if not latencies:
                continue

            avg_latency = sum(latencies) / len(latencies)
            if avg_latency > self.alert_threshold_ms * 2:
                return True, f"High latency in {operation}: {avg_latency:.2f}ms"

        # 检查慢操作比例
        total_ops = sum(len(l) for l in self._operation_latencies.values())
        slow_ops = len(self._slow_operations)
        if total_ops > 0 and slow_ops / total_ops > 0.1:
            return True, f"High slow operation ratio: {slow_ops}/{total_ops}"

        return False, ""


class AccessAnalytics:
    """
    访问分析器

    职责:
    - 分析访问模式
    - 预测未来访问
    - 优化缓存策略
    """

    def __init__(self, stats_collector: MemoryStatsCollector):
        self.stats_collector = stats_collector
        self._access_history: List[Dict[str, Any]] = []
        self._pattern_cache: Dict[str, float] = {}

    def analyze_access_pattern(self) -> Dict[str, Any]:
        """
        分析访问模式

        Returns:
            {pattern_type, peak_hours, frequent_keys}
        """
        if not self._access_history:
            return {
                "pattern_type": "unknown",
                "peak_hours": [],
                "frequent_keys": []
            }

        # 按小时统计
        hourly_counts = defaultdict(int)
        for access in self._access_history:
            timestamp = access.get("timestamp", 0)
            if timestamp:
                hour = int(timestamp / 3600) % 24
                hourly_counts[hour] += 1

        # 找出高峰时段
        peak_hours = sorted(
            hourly_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        peak_hours = [h for h, _ in peak_hours]

        # 频繁访问的键
        key_counts = defaultdict(int)
        for access in self._access_history:
            key = access.get("key", "")
            if key:
                key_counts[key] += 1

        frequent_keys = sorted(
            key_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        frequent_keys = [k for k, _ in frequent_keys]

        return {
            "pattern_type": "temporal" if peak_hours else "random",
            "peak_hours": peak_hours,
            "frequent_keys": frequent_keys
        }

    def predict_next_access(self, key: str) -> Optional[float]:
        """
        预测下次访问时间

        Args:
            key: 记忆键

        Returns:
            预测的时间戳或None
        """
        # 简单的指数移动平均预测
        access_times = [
            a["timestamp"] for a in self._access_history
            if a.get("key") == key
        ]

        if len(access_times) < 2:
            return None

        # 计算平均间隔
        intervals = []
        for i in range(1, len(access_times)):
            intervals.append(access_times[i] - access_times[i-1])

        avg_interval = sum(intervals) / len(intervals)
        last_access = access_times[-1]

        return last_access + avg_interval

    def get_cache_recommendation(self) -> List[str]:
        """
        获取缓存优化建议

        Returns:
            建议保留的键列表
        """
        pattern = self.analyze_access_pattern()
        return pattern.get("frequent_keys", [])

    def record_access_event(
        self,
        key: str,
        access_type: str = "read",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录访问事件

        Args:
            key: 记忆键
            access_type: 访问类型 (read/write)
            metadata: 额外信息
        """
        self._access_history.append({
            "key": key,
            "access_type": access_type,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })

        # 保留最近10000条记录
        if len(self._access_history) > 10000:
            self._access_history = self._access_history[-10000:]
