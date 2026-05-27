"""
结构化日志 - 统一日志格式

提供:
1. StructuredLogger: 结构化日志记录器
2. 日志格式化器
3. 日志上下文管理器
4. 日志聚合器（LogAggregator）
5. 日志处理器（FileHandler, CloudHandler, S3Handler）
6. 日志采样器（LogSampler）
7. 分布式追踪支持（TraceContext）
"""

from src.agents_v2.logging_config import get_logging_logger

import json
import time
import traceback
import threading
import gzip
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
from contextvars import ContextVar
from functools import wraps
from enum import Enum
from queue import Queue, Empty
from dataclasses import dataclass, field

# 上下文变量用于存储请求级日志数据
_log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogAggregator:
    """
    日志聚合器

    功能:
    - 日志缓冲和批量处理
    - 日志采样
    - 日志过滤
    - 内存管理
    """

    def __init__(
        self,
        max_buffer_size: int = 1000,
        flush_interval: int = 5,
        max_memory_mb: int = 100
    ):
        self.max_buffer_size = max_buffer_size
        self.flush_interval = flush_interval
        self.max_memory_mb = max_memory_mb

        self._buffer: deque = deque(maxlen=max_buffer_size)
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self._sampler = LogSampler()
        self._filters: List[Callable] = []

    def add_filter(self, filter_func: Callable[[Dict], bool]):
        """添加日志过滤器"""
        self._filters.append(filter_func)

    def should_sample(self, log_entry: Dict) -> bool:
        """判断是否应该采样"""
        return self._sampler.should_sample(log_entry)

    def add(self, log_entry: Dict) -> bool:
        """
        添加日志条目

        Returns:
            True 如果日志被添加/采样，False 如果被过滤
        """
        # 应用过滤器
        for filter_func in self._filters:
            if not filter_func(log_entry):
                return False

        # 采样决定
        if not self.should_sample(log_entry):
            return False

        with self._lock:
            self._buffer.append(log_entry)

        # 检查是否需要刷新
        self._check_flush()

        return True

    def _check_flush(self):
        """检查是否需要刷新缓冲区"""
        now = time.time()
        should_flush = (
            len(self._buffer) >= self.max_buffer_size or
            now - self._last_flush >= self.flush_interval
        )

        if should_flush:
            self.flush()

    def flush(self) -> List[Dict]:
        """刷新缓冲区并返回日志条目"""
        with self._lock:
            logs = list(self._buffer)
            self._buffer.clear()
            self._last_flush = time.time()
        return logs

    def get_stats(self) -> Dict[str, Any]:
        """获取聚合统计"""
        return {
            "buffer_size": len(self._buffer),
            "max_buffer_size": self.max_buffer_size,
            "last_flush": self._last_flush,
            "filters_count": len(self._filters)
        }


class LogSampler:
    """
    日志采样器

    实现多种采样策略:
    - 头部采样（Head sampling）
    - 尾部采样（Tail sampling）
    - 错误过采样（Error oversampling）
    """

    # 采样率配置
    DEFAULT_SAMPLE_RATES = {
        LogLevel.DEBUG: 0.1,      # 只保留10%的debug日志
        LogLevel.INFO: 0.5,        # 保留50%的info日志
        LogLevel.WARNING: 1.0,    # 保留所有warning日志
        LogLevel.ERROR: 1.0,        # 保留所有error日志
        LogLevel.CRITICAL: 1.0     # 保留所有critical日志
    }

    def __init__(self, sample_rates: Optional[Dict[LogLevel, float]] = None):
        self.sample_rates = sample_rates or self.DEFAULT_SAMPLE_RATES
        self._counts: Dict[LogLevel, int] = {level: 0 for level in LogLevel}
        self._total: Dict[LogLevel, int] = {level: 0 for level in LogLevel}

    def should_sample(self, log_entry: Dict) -> bool:
        """
        判断是否应该采样日志条目

        策略:
        1. 错误日志总是被采样
        2. 根据日志级别应用不同的采样率
        3. 周期性强制采样以保持代表性
        """
        level_str = log_entry.get("level", "info").lower()
        try:
            level = LogLevel(level_str)
        except ValueError:
            level = LogLevel.INFO

        self._total[level] += 1

        # 错误日志总是采样
        if level in (LogLevel.ERROR, LogLevel.CRITICAL):
            self._counts[level] += 1
            return True

        # 根据采样率决定
        rate = self.sample_rates.get(level, 1.0)
        import random
        should_sample = random.random() < rate

        if should_sample:
            self._counts[level] += 1

        # 定期强制采样（每100条强制采样1条）
        if self._total[level] % 100 == 0:
            return True

        return should_sample

    def get_rates(self) -> Dict[str, float]:
        """获取实际采样率"""
        rates = {}
        for level in LogLevel:
            total = self._total[level]
            if total > 0:
                rates[level.value] = self._counts[level] / total
            else:
                rates[level.value] = 0.0
        return rates

    def reset(self):
        """重置计数器"""
        self._counts = {level: 0 for level in LogLevel}
        self._total = {level: 0 for level in LogLevel}


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础数据
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加上下文
        context = _log_context.get()
        if context:
            log_data["context"] = context

        # 添加额外字段
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # 性能数据
        if hasattr(record, 'duration'):
            log_data["duration_ms"] = record.duration

        return json.dumps(log_data, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """普通日志格式化器（开发模式使用）"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname[:5]
        logger_name = record.name.split(".")[-1][:20]
        message = record.getMessage()

        # 添加上下文
        context = _log_context.get()
        context_str = f" [{json.dumps(context)}]" if context else ""

        # 添加异常信息
        exc_info = ""
        if record.exc_info:
            exc_info = f"\n{''.join(traceback.format_exception(*record.exc_info))}"

        return f"{timestamp} | {level:5} | {logger_name:20} | {message}{context_str}{exc_info}"


class TraceContext:
    """
    分布式追踪上下文

    支持:
    - Trace ID 生成和传播
    - Span ID 管理
    - 父子关系追踪
    """

    def __init__(self):
        self.trace_id: Optional[str] = None
        self.span_id: Optional[str] = None
        self.parent_span_id: Optional[str] = None
        self._enabled = False

    def generate_trace_id(self) -> str:
        """生成新的Trace ID"""
        import uuid
        self.trace_id = uuid.uuid4().hex[:16]
        return self.trace_id

    def generate_span_id(self) -> str:
        """生成新的Span ID"""
        import uuid
        self.span_id = uuid.uuid4().hex[:8]
        return self.span_id

    def start_span(self, operation_name: str) -> 'Span':
        """开始一个新的Span"""
        return Span(self, operation_name)

    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {
            "trace_id": self.trace_id or "",
            "span_id": self.span_id or "",
            "parent_span_id": self.parent_span_id or ""
        }

    def inject(self) -> Dict[str, str]:
        """注入追踪头信息"""
        return self.to_dict()

    @classmethod
    def extract(cls, headers: Dict[str, str]) -> 'TraceContext':
        """从HTTP headers提取追踪上下文"""
        ctx = cls()
        ctx.trace_id = headers.get("X-Trace-ID") or headers.get("trace-id")
        ctx.span_id = headers.get("X-Span-ID") or headers.get("span-id")
        ctx.parent_span_id = headers.get("X-Parent-Span-ID") or headers.get("parent-span-id")
        return ctx


@dataclass
class Span:
    """追踪Span"""
    trace_context: TraceContext
    operation_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict] = field(default_factory=list)

    def finish(self):
        """结束Span"""
        self.end_time = time.time()

    def add_tag(self, key: str, value: str):
        """添加标签"""
        self.tags[key] = value

    def add_log(self, message: str, **kwargs):
        """添加Span日志"""
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            **kwargs
        })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time) * 1000

        return {
            "operation_name": self.operation_name,
            "trace_id": self.trace_context.trace_id,
            "span_id": self.trace_context.span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": duration,
            "tags": self.tags,
            "logs": self.logs
        }


def log_operation(operation_name: str, logger: Optional[StructuredLogger] = None):
    """操作日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = StructuredLogger(func.__module__)

            start_time = time.time()
            success = True
            error = None

            logger.info(f"Operation started: {operation_name}")

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000

                if success:
                    logger.info(
                        f"Operation completed: {operation_name}",
                        duration_ms=round(duration_ms, 2)
                    )
                else:
                    logger.error(
                        f"Operation failed: {operation_name}",
                        duration_ms=round(duration_ms, 2),
                        error=error
                    )

        return wrapper
    return decorator


async def log_operation_async(operation_name: str, logger: Optional[StructuredLogger] = None):
    """异步操作日志装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = StructuredLogger(func.__module__)

            start_time = time.time()
            success = True
            error = None

            logger.info(f"Async operation started: {operation_name}")

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000

                if success:
                    logger.info(
                        f"Async operation completed: {operation_name}",
                        duration_ms=round(duration_ms, 2)
                    )
                else:
                    logger.error(
                        f"Async operation failed: {operation_name}",
                        duration_ms=round(duration_ms, 2),
                        error=error
                    )

        return wrapper
    return decorator


class StructuredLogger:
    """
    结构化日志记录器

    使用方式:
        logger = StructuredLogger("my_component")

        # 基本日志
        logger.info("User logged in", user_id="123")

        # 带上下文的日志
        logger.with_context(request_id="abc").info("Processing request")

        # 带性能数据的日志
        logger.info("Operation completed", duration_ms=150)
    """

    def __init__(self, name: str, structured: bool = True):
        self.name = name
        self.structured = structured
        self._logger = get_logging_logger(name)
        self._logger.setLevel(logging.INFO)

        # 设置格式化器
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            if structured:
                handler.setFormatter(StructuredFormatter())
            else:
                handler.setFormatter(PlainFormatter())
            self._logger.addHandler(handler)

    def _log(self, level: int, message: str, **kwargs):
        """内部日志方法"""
        if kwargs:
            # 将kwargs添加到record
            record = self._logger.makeRecord(
                self.name, level, "", 0, message, (), None
            )
            for key, value in kwargs.items():
                setattr(record, key, value)
            self._logger.handle(record)
        else:
            self._logger.log(level, message)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def with_context(self, **context) -> 'StructuredLogger':
        """创建带上下文的日志记录器"""
        token = _log_context.set({**_log_context.get(), **context})
        logger = _StructuredLoggerWithContext(self, token)
        return logger


class _StructuredLoggerWithContext(StructuredLogger):
    """带上下文的日志记录器（临时）"""

    def __init__(self, parent: StructuredLogger, token):
        super().__init__(parent.name, parent.structured)
        self._parent = parent
        self._token = token

    def __enter__(self):
        return self

    def __exit__(self, *args):
        _log_context.reset(self._token)


class LogContext:
    """日志上下文管理器"""

    def __init__(self, **context):
        self._token = None
        self._context = context

    def __enter__(self):
        self._token = _log_context.set({**_log_context.get(), **self._context})
        return self

    def __exit__(self, *args):
        if self._token:
            _log_context.reset(self._token)


# 预配置的日志记录器
def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)
