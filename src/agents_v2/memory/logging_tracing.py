"""
记忆系统日志和追踪 - Memory Logging and Tracing

提供:
- MemoryLogger: 记忆系统日志
- MemoryTracer: 记忆系统追踪
- OperationLog: 操作日志
"""
from src.agents_v2.logging_config import get_logging_logger

import time

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class OperationLog:
    """操作日志"""
    timestamp: float
    operation: str
    key: Optional[str] = None
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalLog:
    """检索日志"""
    timestamp: float
    query: str
    results_count: int
    latency_ms: float
    memory_types: List[str] = field(default_factory=list)
    strategy: str = "unknown"


class MemoryLogger:
    """
    记忆系统日志

    职责:
    - 记录操作日志
    - 记录检索日志
    - 统计操作性能
    """

    def __init__(self, name: str = "memory"):
        self._logger = get_logging_logger(name)
        self._operation_logs: List[OperationLog] = []
        self._retrieval_logs: List[RetrievalLog] = []
        self._max_logs = 10000

    def log_operation(
        self,
        operation: str,
        key: Optional[str] = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录操作日志

        Args:
            operation: 操作类型 (remember, recall, search, delete)
            key: 记忆键
            duration_ms: 持续时间(毫秒)
            success: 是否成功
            error: 错误信息
            metadata: 额外元数据
        """
        log = OperationLog(
            timestamp=time.time(),
            operation=operation,
            key=key,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {}
        )

        self._operation_logs.append(log)

        # 限制日志数量
        if len(self._operation_logs) > self._max_logs:
            self._operation_logs = self._operation_logs[-self._max_logs:]

        # 记录到标准日志
        level = logging.INFO if success else logging.ERROR
        msg = f"Memory operation: {operation}"
        if key:
            msg += f" key={key}"
        msg += f" duration={duration_ms:.2f}ms"
        if error:
            msg += f" error={error}"

        self._logger.log(level, msg)

    def log_retrieval(
        self,
        query: str,
        results_count: int,
        latency_ms: float,
        memory_types: Optional[List[str]] = None,
        strategy: str = "unknown"
    ) -> None:
        """
        记录检索日志

        Args:
            query: 查询字符串
            results_count: 结果数量
            latency_ms: 延迟(毫秒)
            memory_types: 查询的记忆类型
            strategy: 使用的检索策略
        """
        log = RetrievalLog(
            timestamp=time.time(),
            query=query,
            results_count=results_count,
            latency_ms=latency_ms,
            memory_types=memory_types or [],
            strategy=strategy
        )

        self._retrieval_logs.append(log)

        if len(self._retrieval_logs) > self._max_logs:
            self._retrieval_logs = self._retrieval_logs[-self._max_logs:]

        self._logger.debug(
            f"Retrieval query={query[:50]} results={results_count} "
            f"latency={latency_ms:.2f}ms strategy={strategy}"
        )

    def get_operation_stats(
        self,
        operation: Optional[str] = None,
        since_timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        获取操作统计

        Args:
            operation: 可选的操作类型过滤
            since_timestamp: 可选的起始时间

        Returns:
            统计字典
        """
        logs = self._operation_logs

        if operation:
            logs = [l for l in logs if l.operation == operation]

        if since_timestamp:
            logs = [l for l in logs if l.timestamp >= since_timestamp]

        if not logs:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0
            }

        total = len(logs)
        successes = sum(1 for l in logs if l.success)
        total_duration = sum(l.duration_ms for l in logs)

        return {
            "total_operations": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_duration_ms": total_duration / total if total > 0 else 0.0,
            "by_operation": self._group_by_operation(logs)
        }

    def _group_by_operation(self, logs: List[OperationLog]) -> Dict[str, Any]:
        """按操作类型分组"""
        groups: Dict[str, List[OperationLog]] = {}
        for log in logs:
            if log.operation not in groups:
                groups[log.operation] = []
            groups[log.operation].append(log)

        result = {}
        for op, op_logs in groups.items():
            total = len(op_logs)
            successes = sum(1 for l in op_logs if l.success)
            result[op] = {
                "count": total,
                "success_rate": successes / total if total > 0 else 0.0,
                "avg_duration_ms": sum(l.duration_ms for l in op_logs) / total if total > 0 else 0.0
            }

        return result

    def get_retrieval_stats(
        self,
        since_timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        获取检索统计

        Args:
            since_timestamp: 可选的起始时间

        Returns:
            检索统计
        """
        logs = self._retrieval_logs

        if since_timestamp:
            logs = [l for l in logs if l.timestamp >= since_timestamp]

        if not logs:
            return {
                "total_searches": 0,
                "avg_results": 0.0,
                "avg_latency_ms": 0.0
            }

        total = len(logs)
        total_results = sum(l.results_count for l in logs)
        total_latency = sum(l.latency_ms for l in logs)

        # 按策略分组
        by_strategy: Dict[str, List[RetrievalLog]] = {}
        for log in logs:
            if log.strategy not in by_strategy:
                by_strategy[log.strategy] = []
            by_strategy[log.strategy].append(log)

        strategy_stats = {}
        for strategy, strategy_logs in by_strategy.items():
            strategy_stats[strategy] = {
                "count": len(strategy_logs),
                "avg_results": sum(l.results_count for l in strategy_logs) / len(strategy_logs),
                "avg_latency_ms": sum(l.latency_ms for l in strategy_logs) / len(strategy_logs)
            }

        return {
            "total_searches": total,
            "avg_results": total_results / total if total > 0 else 0.0,
            "avg_latency_ms": total_latency / total if total > 0 else 0.0,
            "by_strategy": strategy_stats
        }

    def get_recent_logs(
        self,
        limit: int = 100,
        operation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取最近的日志

        Args:
            limit: 返回数量
            operation: 可选的操作类型过滤

        Returns:
            日志列表
        """
        logs = self._operation_logs

        if operation:
            logs = [l for l in logs if l.operation == operation]

        logs = logs[-limit:]
        logs.reverse()

        return [
            {
                "timestamp": datetime.fromtimestamp(l.timestamp).isoformat(),
                "operation": l.operation,
                "key": l.key,
                "duration_ms": l.duration_ms,
                "success": l.success,
                "error": l.error
            }
            for l in logs
        ]

    def export_logs(self, filepath: str) -> None:
        """
        导出日志到文件

        Args:
            filepath: 文件路径
        """
        logs_data = {
            "operation_logs": [
                {
                    "timestamp": l.timestamp,
                    "operation": l.operation,
                    "key": l.key,
                    "duration_ms": l.duration_ms,
                    "success": l.success,
                    "error": l.error,
                    "metadata": l.metadata
                }
                for l in self._operation_logs
            ],
            "retrieval_logs": [
                {
                    "timestamp": l.timestamp,
                    "query": l.query,
                    "results_count": l.results_count,
                    "latency_ms": l.latency_ms,
                    "memory_types": l.memory_types,
                    "strategy": l.strategy
                }
                for l in self._retrieval_logs
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, ensure_ascii=False, indent=2)

    def clear_logs(self) -> None:
        """清空日志"""
        self._operation_logs.clear()
        self._retrieval_logs.clear()


class MemoryTracer:
    """
    记忆系统追踪

    简化版追踪(不依赖外部追踪库)
    """

    def __init__(self, logger: Optional[MemoryLogger] = None):
        self._logger = logger or MemoryLogger()
        self._spans: List[Dict[str, Any]] = []
        self._max_spans = 1000

    def start_span(
        self,
        operation: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        开始追踪span

        Args:
            operation: 操作类型
            attributes: 属性

        Returns:
            span_id
        """
        span_id = f"span_{len(self._spans)}_{int(time.time() * 1000)}"

        span = {
            "span_id": span_id,
            "operation": operation,
            "attributes": attributes or {},
            "start_time": time.time(),
            "end_time": None,
            "duration_ms": None
        }

        self._spans.append(span)

        if len(self._spans) > self._max_spans:
            self._spans = self._spans[-self._max_spans:]

        return span_id

    def end_span(self, span_id: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        结束追踪span

        Args:
            span_id: span ID
            attributes: 额外属性
        """
        for span in reversed(self._spans):
            if span["span_id"] == span_id:
                span["end_time"] = time.time()
                span["duration_ms"] = (span["end_time"] - span["start_time"]) * 1000

                if attributes:
                    span["attributes"].update(attributes)

                # 记录到日志
                self._logger.log_operation(
                    operation=span["operation"],
                    duration_ms=span["duration_ms"],
                    success=True,
                    metadata=span["attributes"]
                )

                break

    def get_span(self, span_id: str) -> Optional[Dict[str, Any]]:
        """获取span"""
        for span in self._spans:
            if span["span_id"] == span_id:
                return span
        return None

    def get_active_spans(self) -> List[Dict[str, Any]]:
        """获取活跃的spans"""
        return [s for s in self._spans if s["end_time"] is None]

    def get_completed_spans(
        self,
        limit: int = 100,
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """获取已完成的spans"""
        spans = [s for s in self._spans if s["end_time"] is not None]

        if since_timestamp:
            spans = [s for s in spans if s["start_time"] >= since_timestamp]

        spans.sort(key=lambda x: x["start_time"], reverse=True)

        return spans[:limit]

    def trace_function(self, operation: str):
        """
        函数追踪装饰器

        用法:
            @tracer.trace_function("remember")
            async def remember(...):
                ...
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                attributes = {
                    "function": func.__name__,
                    "args": str(args)[:100]
                }
                span_id = self.start_span(operation, attributes)

                try:
                    result = await func(*args, **kwargs)
                    self.end_span(span_id, {"success": True})
                    return result
                except Exception as e:
                    self.end_span(span_id, {"success": False, "error": str(e)})
                    raise

            return wrapper
        return decorator
