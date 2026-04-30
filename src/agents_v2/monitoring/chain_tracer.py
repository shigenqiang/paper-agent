"""
全链路追踪 - Chain Tracer

提供:
1. ChainTraceContext: 全链路追踪上下文
2. ChainSpan: 链路跨度
3. AgentChainTracer: Agent链路追踪器
4. 链路监听器 (ChainListener)
5. 全链路装饰器 (@chain_trace)
6. 链路状态管理 (ChainState)
"""
import time
import uuid
import logging
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
from functools import wraps
import threading
import json

logger = logging.getLogger(__name__)


class ChainPhase(str, Enum):
    """链路阶段"""
    INPUT = "input"                    # 输入处理
    ROUTING = "routing"               # 意图路由
    PLANNING = "planning"              # 规划
    EXECUTION = "execution"           # 执行
    RETRIEVAL = "retrieval"           # 检索
    GENERATION = "generation"          # 生成
    VALIDATION = "validation"          # 验证
    OUTPUT = "output"                  # 输出


class ChainStatus(str, Enum):
    """链路状态"""
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ChainSpan:
    """
    链路跨度

    代表链路中的一个执行单元
    """
    span_id: str
    trace_id: str
    phase: ChainPhase
    operation: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None

    # 层级关系
    parent_span_id: Optional[str] = None
    depth: int = 0

    # 状态和数据
    status: ChainStatus = ChainStatus.STARTED
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # 标签和属性
    tags: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, status: ChainStatus = ChainStatus.COMPLETED):
        """结束span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def add_tag(self, key: str, value: str):
        """添加标签"""
        self.tags[key] = value

    def add_attribute(self, key: str, value: Any):
        """添加属性"""
        self.attributes[key] = value

    def add_event(self, name: str, **kwargs):
        """添加事件"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            **kwargs
        })

    def set_input(self, data: Dict[str, Any]):
        """设置输入"""
        # 脱敏处理
        self.input_data = self._sanitize(data)

    def set_output(self, data: Dict[str, Any]):
        """设置输出"""
        self.output_data = self._sanitize(data)

    def set_error(self, error: Exception):
        """设置错误"""
        self.error = f"{type(error).__name__}: {str(error)}"
        self.status = ChainStatus.FAILED

    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏敏感数据"""
        sensitive_keys = {"password", "token", "api_key", "secret", "credential"}
        result = {}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_keys):
                result[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 1000:
                result[key] = value[:1000] + "...[truncated]"
            else:
                result[key] = value
        return result

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "phase": self.phase.value if isinstance(self.phase, ChainPhase) else self.phase,
            "operation": self.operation,
            "depth": self.depth,
            "start_time": self.start_time,
            "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value if isinstance(self.status, ChainStatus) else self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "tags": self.tags,
            "attributes": self.attributes,
            "events": self.events
        }


class ChainTraceContext:
    """
    全链路追踪上下文

    管理整个请求的生命周期
    """

    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or self._generate_trace_id()
        self.root_span_id: Optional[str] = None
        self.spans: Dict[str, ChainSpan] = {}
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.status = ChainStatus.RUNNING
        self._lock = threading.RLock()

    @staticmethod
    def _generate_trace_id() -> str:
        """生成Trace ID"""
        return f"tr_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def _generate_span_id() -> str:
        """生成Span ID"""
        return f"sp_{uuid.uuid4().hex[:8]}"

    def create_span(
        self,
        phase: ChainPhase,
        operation: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        input_data: Optional[Dict[str, Any]] = None
    ) -> ChainSpan:
        """创建新的span"""
        with self._lock:
            span_id = self._generate_span_id()

            # 计算深度
            depth = 0
            if parent_span_id and parent_span_id in self.spans:
                depth = self.spans[parent_span_id].depth + 1

            span = ChainSpan(
                span_id=span_id,
                trace_id=self.trace_id,
                phase=phase,
                operation=operation,
                parent_span_id=parent_span_id,
                depth=depth,
                tags=tags or {}
            )

            if input_data:
                span.set_input(input_data)

            # 记录根span
            if not self.root_span_id:
                self.root_span_id = span_id

            self.spans[span_id] = span
            return span

    def finish_span(
        self,
        span_id: str,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        """结束span"""
        with self._lock:
            if span_id not in self.spans:
                logger.warning(f"Span {span_id} not found")
                return

            span = self.spans[span_id]

            if output_data:
                span.set_output(output_data)

            if error:
                span.set_error(error)
                span.finish(ChainStatus.FAILED)
            else:
                span.finish(ChainStatus.COMPLETED)

    def finish(self, status: ChainStatus = ChainStatus.COMPLETED):
        """结束整个链路"""
        self.end_time = time.time()
        self.status = status

        # 结束所有未结束的span
        with self._lock:
            for span in self.spans.values():
                if span.end_time is None:
                    span.finish(ChainStatus.CANCELLED)

    def get_span_tree(self) -> Dict[str, Any]:
        """获取span树结构"""
        with self._lock:
            if not self.root_span_id:
                return {}

            root = self.spans[self.root_span_id]
            return self._build_tree(root)

    def _build_tree(self, span: ChainSpan) -> Dict[str, Any]:
        """递归构建树"""
        children = [
            self._build_tree(s)
            for s in self.spans.values()
            if s.parent_span_id == span.span_id
        ]

        result = span.to_dict()
        if children:
            result["children"] = children
        return result

    def get_summary(self) -> Dict[str, Any]:
        """获取链路摘要"""
        with self._lock:
            total_duration = (self.end_time or time.time()) - self.start_time

            # 按phase统计
            phase_stats: Dict[str, Dict[str, Any]] = {}
            for span in self.spans.values():
                phase_name = span.phase.value if isinstance(span.phase, ChainPhase) else span.phase
                if phase_name not in phase_stats:
                    phase_stats[phase_name] = {
                        "count": 0,
                        "total_duration_ms": 0,
                        "avg_duration_ms": 0,
                        "errors": 0
                    }

                phase_stats[phase_name]["count"] += 1
                if span.duration_ms:
                    phase_stats[phase_name]["total_duration_ms"] += span.duration_ms
                if span.error:
                    phase_stats[phase_name]["errors"] += 1

            # 计算平均值
            for stats in phase_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["count"]

            return {
                "trace_id": self.trace_id,
                "root_span_id": self.root_span_id,
                "start_time": self.start_time,
                "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": self.end_time,
                "total_duration_ms": total_duration * 1000,
                "status": self.status.value if isinstance(self.status, ChainStatus) else self.status,
                "total_spans": len(self.spans),
                "phase_stats": phase_stats
            }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "start_time": self.start_time,
            "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": self.end_time,
            "total_duration_ms": (self.end_time or time.time() - self.start_time) * 1000,
            "status": self.status.value if isinstance(self.status, ChainStatus) else self.status,
            "spans": [s.to_dict() for s in self.spans.values()]
        }


class ChainListener:
    """
    链路监听器

    用于接收链路事件，可以实现:
    - 日志记录
    - 指标收集
    - 性能监控
    - 错误告警
    """

    def on_span_start(self, span: ChainSpan):
        """Span开始"""
        pass

    def on_span_end(self, span: ChainSpan):
        """Span结束"""
        pass

    def on_trace_start(self, context: ChainTraceContext):
        """追踪开始"""
        pass

    def on_trace_end(self, context: ChainTraceContext):
        """追踪结束"""
        pass

    def on_error(self, span: ChainSpan, error: Exception):
        """发生错误"""
        pass


class ChainTracer:
    """
    全链路追踪器

    使用方式:
        tracer = ChainTracer()

        with tracer.trace("input", "process_query") as span:
            span.add_tag("query_type", "factual")
            # 处理逻辑
            pass

        # 或使用装饰器
        @tracer.trace_phase(ChainPhase.RETRIEVAL)
        def retrieve(query):
            ...
    """

    def __init__(self, listeners: Optional[List[ChainListener]] = None):
        self._listeners: List[ChainListener] = listeners or []
        self._current_context: Optional[ChainTraceContext] = None
        self._contexts: Dict[str, ChainTraceContext] = {}
        self._lock = threading.RLock()

    def add_listener(self, listener: ChainListener):
        """添加监听器"""
        self._listeners.append(listener)

    def start_trace(self, trace_id: Optional[str] = None) -> ChainTraceContext:
        """开始新的追踪"""
        context = ChainTraceContext(trace_id)
        self._current_context = context

        with self._lock:
            self._contexts[context.trace_id] = context

        for listener in self._listeners:
            listener.on_trace_start(context)

        return context

    def end_trace(self, status: ChainStatus = ChainStatus.COMPLETED):
        """结束当前追踪"""
        if self._current_context:
            self._current_context.finish(status)
            for listener in self._listeners:
                listener.on_trace_end(self._current_context)

    def get_current_context(self) -> Optional[ChainTraceContext]:
        """获取当前追踪上下文"""
        return self._current_context

    @contextmanager
    def trace(
        self,
        phase: ChainPhase,
        operation: str,
        tags: Optional[Dict[str, str]] = None,
        input_data: Optional[Dict[str, Any]] = None
    ):
        """追踪上下文管理器"""
        if not self._current_context:
            # 自动创建追踪上下文
            self.start_trace()

        parent_span_id = self._get_current_span_id()
        span = self._current_context.create_span(
            phase=phase,
            operation=operation,
            parent_span_id=parent_span_id,
            tags=tags,
            input_data=input_data
        )

        for listener in self._listeners:
            listener.on_span_start(span)

        try:
            yield span
            span.finish(ChainStatus.COMPLETED)
        except Exception as e:
            span.set_error(e)
            for listener in self._listeners:
                listener.on_error(span, e)
            raise
        finally:
            for listener in self._listeners:
                listener.on_span_end(span)

    def trace_phase(self, phase: ChainPhase):
        """阶段追踪装饰器工厂"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                operation_name = func.__name__
                with self.trace(phase, operation_name, input_data={"args": str(args)[:200]}) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_output({"result_type": type(result).__name__})
                        return result
                    except Exception as e:
                        span.set_error(e)
                        raise

            return wrapper
        return decorator

    def _get_current_span_id(self) -> Optional[str]:
        """获取当前span ID"""
        if not self._current_context:
            return None

        # 找到最近未结束的span
        for span in reversed(list(self._current_context.spans.values())):
            if span.end_time is None:
                return span.span_id

        return None

    def get_trace(self, trace_id: str) -> Optional[ChainTraceContext]:
        """获取指定追踪"""
        with self._lock:
            return self._contexts.get(trace_id)

    def get_all_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有追踪摘要"""
        with self._lock:
            contexts = list(self._contexts.values())[-limit:]
            return [ctx.get_summary() for ctx in contexts]


class LoggingChainListener(ChainListener):
    """
    日志监听器

    将链路事件记录到日志
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or logging.getLogger("chain_tracer")

    def on_span_start(self, span: ChainSpan):
        indent = "  " * span.depth
        self._logger.info(
            f"{indent}[{span.phase.value}] {span.operation} started "
            f"(span={span.span_id})"
        )

    def on_span_end(self, span: ChainSpan):
        indent = "  " * span.depth
        duration = f"{span.duration_ms:.2f}ms" if span.duration_ms else "N/A"
        status_icon = "✓" if span.status == ChainStatus.COMPLETED else "✗"
        self._logger.info(
            f"{indent}{status_icon}[{span.phase.value}] {span.operation} "
            f"completed in {duration} (span={span.span_id})"
        )

    def on_trace_start(self, context: ChainTraceContext):
        self._logger.info(f"=== Trace {context.trace_id} started ===")

    def on_trace_end(self, context: ChainTraceContext):
        duration = (context.end_time - context.start_time) * 1000 if context.end_time else 0
        summary = context.get_summary()
        self._logger.info(
            f"=== Trace {context.trace_id} ended: "
            f"{summary['total_spans']} spans, {duration:.2f}ms, "
            f"status={context.status.value} ==="
        )

    def on_error(self, span: ChainSpan, error: Exception):
        self._logger.error(
            f"[{span.phase.value}] {span.operation} failed: {error}",
            exc_info=True
        )


class MetricsChainListener(ChainListener):
    """
    指标监听器

    收集链路指标用于监控
    """

    def __init__(self):
        self._span_count = 0
        self._error_count = 0
        self._total_duration_ms = 0.0
        self._phase_counts: Dict[str, int] = {}

    def on_span_end(self, span: ChainSpan):
        self._span_count += 1
        if span.duration_ms:
            self._total_duration_ms += span.duration_ms

        phase_name = span.phase.value if isinstance(span.phase, ChainPhase) else span.phase
        self._phase_counts[phase_name] = self._phase_counts.get(phase_name, 0) + 1

    def on_error(self, span: ChainSpan, error: Exception):
        self._error_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        avg_duration = self._total_duration_ms / self._span_count if self._span_count > 0 else 0
        return {
            "total_spans": self._span_count,
            "total_errors": self._error_count,
            "total_duration_ms": self._total_duration_ms,
            "avg_span_duration_ms": avg_duration,
            "phase_counts": self._phase_counts
        }


# 全局追踪器实例
_global_tracer: Optional[ChainTracer] = None
_global_lock = threading.Lock()


def get_chain_tracer() -> ChainTracer:
    """获取全局链路追踪器"""
    global _global_tracer
    with _global_lock:
        if _global_tracer is None:
            # 创建带日志监听器的追踪器
            _global_tracer = ChainTracer([
                LoggingChainListener(),
                MetricsChainListener()
            ])
        return _global_tracer


def set_chain_tracer(tracer: ChainTracer):
    """设置全局链路追踪器"""
    global _global_tracer
    with _global_lock:
        _global_tracer = tracer


@contextmanager
def chain_trace(
    phase: ChainPhase,
    operation: str,
    tags: Optional[Dict[str, str]] = None,
    input_data: Optional[Dict[str, Any]] = None
):
    """全局追踪上下文管理器"""
    tracer = get_chain_tracer()
    with tracer.trace(phase, operation, tags, input_data) as span:
        yield span


def trace_phase(phase: ChainPhase):
    """全局阶段追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_chain_tracer()
            with tracer.trace(phase, func.__name__) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_error(e)
                    raise

        return wrapper
    return decorator
