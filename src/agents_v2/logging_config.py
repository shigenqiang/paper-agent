"""
Loguru 日志配置 - 统一日志系统

特性:
1. 自动包含调用位置信息（文件、行号、函数名）
2. 支持多输出（控制台、文件、旋转文件）
3. 支持 JSON 结构化输出
4. 支持日志级别动态配置
5. 支持上下文追踪（trace_id）
6. 支持日志绑定 (bind) 和上下文管理
7. 支持异常完整追踪 (backtrace, diagnose)
8. 支持多 sink 和过滤器
9. 支持异步安全写入 (enqueue)
10. 支持彩色输出和自定义格式

Loguru 完整特性列表:
- logger.add(sink, rotation, retention, compression, filter, level, format, colorize, serialize, enqueue, catch, backtrace, diagnose)
- logger.remove(handler_id)
- logger.bind(**kwargs) - 绑定上下文
- logger.patch(modifier) - 修改记录
- logger.catch() - 装饰器捕获异常
- logger.level() - 自定义级别
- logger.enable()/disable() - 动态启用/禁用
- logger.contextize() - 上下文管理器
- logger.log(level, message) - 通用日志方法
- logger.configure() - 运行时配置

使用方法:
    from src.agents_v2.logging_config import setup_logging, logger

    # 初始化日志系统
    setup_logging()

    # 使用 logger 记录日志
    logger.info("Hello, this log includes file:line:function info")

    # 绑定上下文
    user_logger = logger.bind(user_id="123")
    user_logger.info("User action")

    # 异常追踪
    try:
        risky_operation()
    except Exception:
        logger.exception("Operation failed")

    # 装饰器捕获
    @logger.catch
    def my_function():
        ...
"""
import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 尝试导入 loguru，如果不存在则使用备选方案
try:
    from loguru import logger as _loguru_logger
    _HAS_LOGURU = True
except ImportError:
    _HAS_LOGURU = False
    _loguru_logger = None

# 日志级别映射
LOG_LEVEL_MAP = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}

# 默认日志格式（包含文件位置）
_DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 普通格式（不含颜色）
_PLAIN_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# JSON 格式
_JSON_FORMAT = (
    '{"time":"{time:YYYY-MM-DD HH:mm:ss.SSS}",'
    '"level":"{level}",'
    '"file":"{file}",'
    '"line":{line},'
    '"function":"{function}",'
    '"name":"{name}",'
    '"message":"{message}"}'
)


def _get_caller_info() -> Dict[str, Any]:
    """获取调用者信息（文件名、行号、函数名）"""
    import traceback

    # 获取完整的调用栈
    stack = traceback.extract_stack()

    if not stack:
        return {"file": "unknown", "line": 0, "function": "unknown", "name": "unknown"}

    # 需要跳过的文件名模式（这些是我们内部的文件）
    skip_patterns = [
        "logging_config.py",
        "loguru",
        "<string>",  # 交互式环境
        "test_",
        "_get_caller_info",  # 自身
    ]

    # 找到最后一个不是内部文件的帧（从后往前找，找到实际调用者）
    # 调用栈的最后是实际的调用者
    for frame in stack:
        filename = os.path.basename(frame.filename)
        should_skip = any(pattern in filename for pattern in skip_patterns)

        # 额外检查：如果 filename 中包含 "logging_config" 也跳过
        if "logging_config" in frame.filename:
            should_skip = True

        if not should_skip:
            return {
                "file": filename,
                "line": frame.lineno,
                "function": frame.name,
                "name": frame.name
            }

    # 兜底返回（使用第一个调用栈条目）
    return {
        "file": os.path.basename(stack[0].filename),
        "line": stack[0].lineno,
        "function": stack[0].name,
        "name": stack[0].name
    }


class FallbackLogger:
    """
    备用日志记录器（当 loguru 不可用时使用）

    提供与 loguru 相同的 API，自动包含调用位置信息
    """

    def __init__(self):
        self._level = "INFO"
        self._handlers = []

    def _should_log(self, level: str) -> bool:
        """检查是否应该记录此级别"""
        return LOG_LEVEL_MAP.get(level, 20) >= LOG_LEVEL_MAP.get(self._level, 20)

    def _format_log(self, level: str, message: str, **kwargs) -> str:
        """格式化日志行"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        caller_info = _get_caller_info()
        file_name = caller_info["file"]
        line_no = caller_info["line"]
        func_name = caller_info["function"]

        level_padded = level.ljust(8)

        # 构建日志消息
        extra_str = ""
        if kwargs:
            extra_pairs = []
            for k, v in kwargs.items():
                # 格式化值
                if isinstance(v, str):
                    extra_pairs.append(f'{k}="{v}"')
                else:
                    extra_pairs.append(f'{k}={v}')
            extra_str = " | " + " ".join(extra_pairs)

        return f"{timestamp} | {level_padded} | {file_name}:{line_no}:{func_name} | {message}{extra_str}"

    def _print_log(self, level: str, message: str, **kwargs):
        """输出日志到控制台"""
        if not self._should_log(level):
            return

        log_line = self._format_log(level, message, **kwargs)

        # 颜色代码
        color_map = {
            "TRACE": "\033[94m",    # 蓝色
            "DEBUG": "\033[96m",    # 青色
            "INFO": "\033[92m",     # 绿色
            "SUCCESS": "\033[92m",  # 绿色
            "WARNING": "\033[93m", # 黄色
            "ERROR": "\033[91m",    # 红色
            "CRITICAL": "\033[91m", # 红色
            "WARN": "\033[93m",      # 黄色（别名）
        }
        reset = "\033[0m"
        color = color_map.get(level, "")

        # 检查是否支持颜色输出
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            print(f"{color}{log_line}{reset}")
        else:
            # 无颜色输出
            print(log_line)

    def trace(self, message: str, **kwargs):
        self._print_log("TRACE", message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._print_log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        self._print_log("INFO", message, **kwargs)

    def success(self, message: str, **kwargs):
        self._print_log("SUCCESS", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._print_log("WARNING", message, **kwargs)

    def warn(self, message: str, **kwargs):
        self._print_log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self._print_log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._print_log("CRITICAL", message, **kwargs)

    def exception(self, message: str, **kwargs):
        kwargs["exc_info"] = True
        self._print_log("ERROR", message, **kwargs)

    def bind(self, **kwargs):
        """绑定上下文（用于兼容 loguru API）"""
        return self

    def __call__(self, message: str, **kwargs):
        """兼容 loguru 的调用方式"""
        self.info(message, **kwargs)


class StructuredFallbackLogger(FallbackLogger):
    """
    结构化日志记录器（输出 JSON 格式）
    """

    def _print_log(self, level: str, message: str, **kwargs):
        """输出 JSON 格式日志"""
        if not self._should_log(level):
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        caller_info = _get_caller_info()

        log_data = {
            "time": timestamp,
            "level": level,
            "file": caller_info["file"],
            "line": caller_info["line"],
            "function": caller_info["function"],
            "name": caller_info["name"],
            "message": message,
        }
        log_data.update(kwargs)

        print(json.dumps(log_data, ensure_ascii=False, indent=None))


# 全局 logger 实例
_logger_instance: Optional[Any] = None
_is_configured: bool = False


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    rotation: str = "500 MB",
    retention: str = "7 days",
    structured: bool = False,
    format_string: Optional[str] = None,
    use_color: bool = True,
    backtrace: bool = True,
    diagnose: bool = True,
    enqueue: bool = True,
    compression: str = "zip",
    serialize: bool = False,
    error_file: Optional[str] = None,
) -> Any:
    """
    配置日志系统

    Args:
        level: 日志级别 (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件名（不含路径），如果为 None 则只输出到控制台
        log_dir: 日志目录，默认为 "logs"
        rotation: 轮转策略，如 "500 MB" 或 "00:00"（每天）
        retention: 保留策略，如 "7 days"
        structured: 是否输出 JSON 格式
        format_string: 自定义格式字符串
        use_color: 是否使用颜色输出
        backtrace: 是否启用完整异常堆栈追踪
        diagnose: 是否添加变量诊断信息
        enqueue: 是否使用异步队列写入（多进程安全）
        compression: 压缩格式 ("zip", "gz", "bz2", "xz")
        serialize: 是否序列化为 JSON 格式
        error_file: 单独的错误日志文件路径

    Returns:
        配置好的 logger 实例

    Example:
        setup_logging(level="DEBUG", log_file="app.log")
        logger.info("Hello, this log includes file:line:function info")
    """
    global _logger_instance, _is_configured, _loguru_logger

    # 创建日志目录
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

    if _HAS_LOGURU:
        # 使用真正的 loguru

        # 移除所有现有的 handler
        _loguru_logger.remove()

        # 确定输出格式
        if format_string is None:
            if structured or serialize:
                format_string = _JSON_FORMAT
            elif use_color:
                format_string = _DEFAULT_FORMAT
            else:
                format_string = _PLAIN_FORMAT

        # 1. 添加控制台输出
        _loguru_logger.add(
            sys.stderr,
            format=format_string,
            level=level,
            colorize=use_color and sys.stdout.isatty(),
            backtrace=backtrace,
            diagnose=diagnose,
        )

        # 2. 添加文件输出（如果指定了 log_file）
        if log_file and log_dir:
            file_path = Path(log_dir) / log_file

            # 添加文件日志
            _loguru_logger.add(
                str(file_path),
                format=format_string,
                level=level,
                rotation=rotation,
                retention=retention,
                compression=compression,
                enqueue=enqueue,
                serialize=serialize,
                backtrace=backtrace,
                diagnose=diagnose,
            )

        # 3. 添加错误专用日志文件
        if error_file:
            error_path = Path(log_dir) / error_file
            _loguru_logger.add(
                str(error_path),
                format=format_string,
                level="ERROR",
                rotation=rotation,
                retention=retention,
                compression=compression,
                enqueue=enqueue,
                serialize=serialize,
                backtrace=backtrace,
                diagnose=diagnose,
                filter=lambda record: record["level"].no >= 40  # 只记录 ERROR 及以上
            )

        # 4. 添加 SUCCESS 级别支持（Loguru 内置）
        # SUCCESS 级别 no=25，在 DEBUG(10) 和 INFO(20) 之间

        _logger_instance = _loguru_logger

    else:
        # 使用备选的 FallbackLogger
        if structured:
            _logger_instance = StructuredFallbackLogger()
        else:
            _logger_instance = FallbackLogger()

        _logger_instance._level = level

    _is_configured = True
    return _logger_instance


def add_sink(
    sink: Any,
    level: str = "INFO",
    format_string: Optional[str] = None,
    rotation: Optional[str] = None,
    retention: Optional[str] = None,
    compression: Optional[str] = None,
    filter_func: Optional[callable] = None,
    enqueue: bool = False,
    serialize: bool = False,
    backtrace: bool = True,
    diagnose: bool = True,
) -> int:
    """
    添加额外的日志 sink

    Args:
        sink: 日志输出目标（文件路径、流对象、或可调用对象）
        level: 日志级别
        format_string: 自定义格式字符串
        rotation: 轮转策略
        retention: 保留策略
        compression: 压缩格式
        filter_func: 过滤器函数
        enqueue: 是否异步写入
        serialize: 是否序列化为 JSON
        backtrace: 是否启用完整堆栈追踪
        diagnose: 是否添加变量诊断

    Returns:
        sink 的 ID，用于 remove()

    Example:
        # 添加按模块过滤的文件输出
        add_sink(
            "logs/my_module.log",
            level="DEBUG",
            filter_func=lambda r: r["name"].startswith("my_module")
        )
    """
    global _logger_instance

    if _logger_instance is None:
        get_logger()

    if _HAS_LOGURU:
        kwargs = {
            "level": level,
            "backtrace": backtrace,
            "diagnose": diagnose,
            "enqueue": enqueue,
        }

        if format_string:
            kwargs["format"] = format_string
        if rotation:
            kwargs["rotation"] = rotation
        if retention:
            kwargs["retention"] = retention
        if compression:
            kwargs["compression"] = compression
        if filter_func:
            kwargs["filter"] = filter_func
        if serialize:
            kwargs["serialize"] = serialize

        sink_id = _loguru_logger.add(sink, **kwargs)
        return sink_id

    return -1


def remove_sink(sink_id: int) -> bool:
    """
    移除指定的 sink

    Args:
        sink_id: add_sink() 返回的 ID

    Returns:
        是否成功移除
    """
    global _logger_instance

    if _HAS_LOGURU and _logger_instance is not None:
        _loguru_logger.remove(sink_id)
        return True

    return False


def bind_context(**kwargs) -> 'ContextLogger':
    """
    创建绑定上下文的日志记录器

    Args:
        **kwargs: 要绑定的上下文键值对

    Returns:
        ContextLogger 对象，可作为上下文管理器使用

    Example:
        with bind_context(request_id="123", user_id="456"):
            logger.info("Request processed")
    """
    return ContextLogger(**kwargs)


class ContextLogger:
    """
    上下文日志记录器

    用法:
        ctx = ContextLogger(request_id="123")
        ctx.logger.info("Processing")  # 自动包含 request_id

        # 或作为上下文管理器
        with bind_context(user_id="456"):
            logger.info("User action")
    """

    def __init__(self, **context):
        self._context = context
        self._token = None
        if _HAS_LOGURU and _logger_instance is not None:
            # 使用 loguru 的 bind 功能
            self._bound_logger = _logger_instance.bind(**context)
        else:
            self._bound_logger = _logger_instance

    @property
    def logger(self):
        """获取绑定了上下文的 logger"""
        return self._bound_logger

    def __enter__(self):
        if _HAS_LOGURU and hasattr(_logger_instance, 'contextize'):
            self._ctx_manager = _logger_instance.contextize(**self._context)
            return self._ctx_manager.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_ctx_manager'):
            self._ctx_manager.__exit__(exc_type, exc_val, exc_tb)
        return False


def get_logger() -> Any:
    """
    获取全局 logger 实例

    如果尚未初始化，则使用默认配置初始化
    """
    global _logger_instance, _is_configured

    if _logger_instance is None or not _is_configured:
        # 使用环境变量或默认值初始化
        level = os.environ.get("LOG_LEVEL", "INFO")
        log_file = os.environ.get("LOG_FILE", None)
        log_dir = os.environ.get("LOG_DIR", "logs")

        setup_logging(
            level=level,
            log_file=log_file if log_file else None,
            log_dir=log_dir
        )

    return _logger_instance


# 为了兼容现有代码，提供一个 logger 实例
logger = get_logger()


def bind_trace(trace_id: str) -> Dict[str, str]:
    """
    绑定追踪 ID 到日志上下文

    Args:
        trace_id: 追踪 ID

    Returns:
        追踪上下文字典
    """
    return {"trace_id": trace_id}


def log_with_trace(message: str, level: str = "INFO", **kwargs):
    """
    带追踪上下文的日志记录

    Args:
        message: 日志消息
        level: 日志级别
        **kwargs: 其他上下文信息
    """
    global _logger_instance

    if _logger_instance is None:
        get_logger()

    log_func = getattr(_logger_instance, level.lower(), _logger_instance.info)
    log_func(message, **kwargs)


# 向后兼容：提供与 logging 模块兼容的接口
class LoggingAdapter:
    """
    适配 logging 模块的接口

    当 loguru 可用时，直接返回 loguru logger 以保持正确的调用位置信息
    """

    def __init__(self, name: str):
        self.name = name
        # 直接使用全局 logger（当 HAS_LOGURU 时就是 loguru）
        self._logger = get_logger()

    def _format_message(self, message: str, *args) -> str:
        """格式化消息，支持 % 格式化"""
        if args:
            try:
                return message % args
            except (TypeError, ValueError):
                pass
        return message

    def debug(self, message: str, *args, **kwargs):
        msg = self._format_message(message, *args) if args else message
        self._logger.debug(msg, **kwargs)

    def info(self, message: str, *args, **kwargs):
        msg = self._format_message(message, *args) if args else message
        self._logger.info(msg, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        msg = self._format_message(message, *args) if args else message
        self._logger.warning(msg, **kwargs)

    def warn(self, message: str, *args, **kwargs):
        msg = self._format_message(message, *args) if args else message
        self._logger.warning(msg, **kwargs)

    def error(self, message: str, *args, **kwargs):
        msg = self._format_message(message, *args) if args else message
        self._logger.error(msg, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        msg = self._format_message(message, *args) if args else message
        self._logger.critical(msg, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """记录异常（Loguru 的 exception 方法）"""
        msg = self._format_message(message, *args) if args else message
        self._logger.exception(msg, **kwargs)

    def success(self, message: str, *args, **kwargs):
        """记录成功信息（Loguru 特有）"""
        msg = self._format_message(message, *args) if args else message
        if hasattr(self._logger, 'success'):
            self._logger.success(msg, **kwargs)
        else:
            self._logger.info(msg, **kwargs)

    def trace(self, message: str, *args, **kwargs):
        """记录 TRACE 级别日志"""
        msg = self._format_message(message, *args) if args else message
        self._logger.trace(msg, **kwargs)

    def log(self, level: int, message: str, *args, **kwargs):
        """通用 log 方法"""
        level_name = self._level_to_name(level)
        msg = self._format_message(message, *args) if args else message
        log_func = getattr(self._logger, level_name, self._logger.info)
        log_func(msg, **kwargs)

    def bind(self, **kwargs):
        """绑定上下文到日志记录器"""
        bound_logger = self._logger.bind(**kwargs)
        adapter = LoggingAdapter(self.name)
        adapter._logger = bound_logger
        return adapter

    def patch(self, modifier):
        """使用修饰器修改日志记录"""
        return self._logger.patch(modifier)

    def catch(self, func):
        """装饰器：自动捕获并记录异常"""
        return self._logger.catch(func)

    def contextize(self, **kwargs):
        """创建上下文管理器，在块内绑定上下文"""
        return self._logger.contextize(**kwargs)

    def with_context(self, **kwargs):
        """类似于 bind()，但作为上下文管理器使用"""
        return self._logger.bind(**kwargs)

    @staticmethod
    def _level_to_name(level: int) -> str:
        """将数字级别转换为名称"""
        level_map = {
            0: "trace",
            10: "debug",
            20: "info",
            30: "warning",
            40: "error",
            50: "critical",
        }
        for l in sorted(level_map.keys(), reverse=True):
            if level >= l:
                return level_map[l]
        return "info"


def add_logging_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    rotation: str = "500 MB",
    retention: str = "7 days",
    compression: str = "zip",
    filter_func: Optional[callable] = None,
) -> int:
    """
    为特定模块添加专用的日志输出

    Args:
        name: 模块名称（用于标识）
        level: 日志级别
        log_file: 日志文件名
        log_dir: 日志目录
        rotation: 轮转策略
        retention: 保留策略
        compression: 压缩格式
        filter_func: 过滤器函数

    Returns:
        sink_id，用于 remove_sink()

    Example:
        # 为某模块添加专用日志文件
        add_logging_logger(
            "my_module",
            level="DEBUG",
            log_file="my_module.log",
            filter_func=lambda r: r["name"].startswith("my_module")
        )
    """
    if log_file is None:
        log_file = f"{name}.log"

    if log_dir:
        file_path = Path(log_dir) / log_file
    else:
        file_path = log_file

    kwargs = {
        "level": level,
        "rotation": rotation,
        "retention": retention,
        "compression": compression,
        "enqueue": True,
        "backtrace": True,
        "diagnose": True,
    }

    if filter_func:
        kwargs["filter"] = filter_func
    else:
        # 默认按模块名过滤
        kwargs["filter"] = lambda record: record["name"].startswith(name)

    if _HAS_LOGURU:
        sink_id = _loguru_logger.add(str(file_path), **kwargs)
        return sink_id

    return -1


def get_logging_logger(name: str):
    """
    获取日志记录器

    当 loguru 可用时，返回 loguru logger 以保持正确的调用位置信息
    支持 % 格式化（如 logger.info("Hello, %s", "world")）

    Example:
        logger = get_logging_logger(__name__)
        logger.info("Hello, %s", "world")
    """
    if _HAS_LOGURU:
        return _loguru_logger
    return LoggingAdapter(name)


# 便捷函数：创建带模块名的 logger
def get_module_logger(module_name: str) -> LoggingAdapter:
    """获取指定模块的 logger"""
    return LoggingAdapter(module_name)


if __name__ == "__main__":
    # 测试日志配置
    print("=" * 60)
    print("Loguru Logging System - Complete Feature Test")
    print("=" * 60)

    # 初始化日志系统
    setup_logging(
        level="DEBUG",
        log_file="test.log",
        log_dir="logs",
        structured=False,
        backtrace=True,
        diagnose=True,
        enqueue=True,
        compression="zip",
        error_file="error.log",
    )

    logger = get_logger()

    # ==================== 1. 测试日志级别 ====================
    print("\n" + "-" * 40)
    print("1. Testing Log Levels")
    print("-" * 40)
    logger.trace("This is a TRACE message")
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.success("This is a SUCCESS message (Loguru specific)")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")

    # ==================== 2. 测试带额外信息 ====================
    print("\n" + "-" * 40)
    print("2. Testing Extra Information")
    print("-" * 40)
    logger.info("User action", user_id="123", action="login", duration_ms=150.5)

    # ==================== 3. 测试上下文绑定 ====================
    print("\n" + "-" * 40)
    print("3. Testing Context Binding (bind)")
    print("-" * 40)
    request_logger = logger.bind(request_id="req-456", user_id="user-789")
    request_logger.info("Processing request")  # 包含 request_id 和 user_id
    request_logger.info("Request completed")     # 继续包含上下文

    # ==================== 4. 测试上下文管理器 ====================
    print("\n" + "-" * 40)
    print("4. Testing Context Manager (contextize)")
    print("-" * 40)
    if _HAS_LOGURU:
        with logger.contextize(transaction_id="txn-001"):
            logger.info("Transaction started")
            logger.info("Transaction processing")
            logger.info("Transaction committed")
    else:
        with bind_context(transaction_id="txn-001"):
            logger.info("Transaction started")
            logger.info("Transaction processing")
            logger.info("Transaction committed")

    # ==================== 5. 测试异常追踪 ====================
    print("\n" + "-" * 40)
    print("5. Testing Exception with Backtrace")
    print("-" * 40)
    try:
        def inner_function():
            x = 1 / 0  # 触发除零异常

        def outer_function():
            inner_function()

        outer_function()
    except Exception:
        logger.exception("Division operation failed")  # 自动包含完整堆栈

    # ==================== 6. 测试 LoggingAdapter ====================
    print("\n" + "-" * 40)
    print("6. Testing LoggingAdapter (logging compatible)")
    print("-" * 40)
    adapter = get_logging_logger(__name__)
    adapter.info("Using LoggingAdapter with %s", "format string")
    adapter.warning("Warning with code=%d", 404)
    adapter.error("Error with details", error_code=500)

    # ==================== 7. 测试 LoggingAdapter.bind() ====================
    print("\n" + "-" * 40)
    print("7. Testing LoggingAdapter.bind()")
    print("-" * 40)
    user_adapter = adapter.bind(user_id="user-123", role="admin")
    user_adapter.info("Admin action logged")

    # ==================== 8. 测试 @catch 装饰器 ====================
    print("\n" + "-" * 40)
    print("8. Testing @catch Decorator")
    print("-" * 40)
    if _HAS_LOGURU:
        @logger.catch
        def failing_function():
            return 1 / 0

        result = failing_function()  # 异常会被捕获并记录，不会崩溃

    # ==================== 9. 测试 SUCCESS 级别 ====================
    print("\n" + "-" * 40)
    print("9. Testing SUCCESS Level (no=25)")
    print("-" * 40)
    logger.success("Operation completed successfully!")
    logger.success("Data saved", rows=100, table="users")

    # ==================== 10. 测试多 sink ====================
    print("\n" + "-" * 40)
    print("10. Testing Multiple Sinks")
    print("-" * 40)
    # 添加一个额外的 sink
    sink_id = add_sink(
        "logs/extra.log",
        level="INFO",
        rotation="10 MB",
        filter_func=lambda r: "extra" in r["message"].lower()
    )
    logger.info("This goes to extra sink", extra="test")
    print(f"Added extra sink with id: {sink_id}")

    print("\n" + "=" * 60)
    print("Loguru Feature Test Complete!")
    print("Check the following files:")
    print("  - logs/test.log (main log)")
    print("  - logs/error.log (errors only)")
    print("  - logs/extra.log (extra sink)")
    print("=" * 60)