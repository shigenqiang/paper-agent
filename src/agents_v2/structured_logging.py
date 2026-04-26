"""
结构化日志 - 统一日志格式

提供:
1. StructuredLogger: 结构化日志记录器
2. 日志格式化器
3. 日志上下文管理器
"""
import logging
import json
import time
import traceback
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar
from functools import wraps

# 上下文变量用于存储请求级日志数据
_log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})


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
        self._logger = logging.getLogger(name)
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
        extra = {"extra": kwargs} if kwargs else {}

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


# 预配置的日志记录器
def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)
