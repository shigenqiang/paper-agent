# Loguru 日志系统使用指南

## 概述

项目已迁移到 **Loguru** 日志系统，提供以下特性：

1. **自动包含调用位置信息**：文件名、行号、函数名
2. **支持多输出**：控制台、文件、旋转文件
3. **支持 JSON 结构化输出**
4. **支持日志级别动态配置**
5. **兼容 logging 模块接口**

---

## 快速开始

### 方法 1: 使用 `get_logging_logger()` (推荐)

```python
from src.agents_v2.logging_config import get_logging_logger

# 在每个模块中创建 logger
logger = get_logging_logger(__name__)

# 使用日志（兼容 logging 接口）
logger.info("Hello, %s", "world")  # 支持 % 格式化
logger.debug("Debug message")
logger.warning("Warning: %s", "something")
logger.error("Error occurred", code=500)
```

### 方法 2: 使用全局 `logger`

```python
from src.agents_v2.logging_config import logger

logger.info("Message with extra info", user_id="123", action="login")
```

### 方法 3: 在 main.py 中初始化

```python
from src.agents_v2.logging_config import setup_logging

# 初始化日志系统
setup_logging(
    level="DEBUG",           # 日志级别
    log_file="app.log",       # 日志文件名
    log_dir="logs",           # 日志目录
    rotation="500 MB",        # 轮转策略
    retention="7 days",       # 保留策略
)
```

---

## Loguru 完整特性

### 1. 开箱即用

```python
from loguru import logger

logger.info("这是 info 级别日志")
logger.debug("这是 debug 级别日志")
logger.warning("这是警告日志")
logger.error("这是错误日志")
logger.critical("这是严重错误日志")
```

### 2. 自动调用位置信息

Loguru 自动记录 **文件名、行号、函数名**，无需配置：

```
2026-05-01 16:54:32.123 | INFO    | module.py:45:handle_request | Request received
```

### 3. 多 Sink 输出

使用 `logger.add()` 添加多个输出目标：

```python
from loguru import logger

# 移除默认的 stderr 输出
logger.remove()

# 控制台输出（带颜色）
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True
)

# 文件输出（按大小轮转）
logger.add(
    "logs/app.log",
    rotation="500 MB",           # 文件达到 500MB 时自动轮转
    retention="10 days",          # 保留 10 天
    compression="zip",            # 压缩旧日志
    level="INFO"
)

# 文件输出（按时间轮转）
logger.add(
    "logs/app-{time:YYYY-MM-DD}.log",
    rotation="00:00",             # 每天午夜轮转
    retention="30 days",
    compression="gz"
)

# 错误专用日志文件
logger.add(
    "logs/error.log",
    level="ERROR",
    filter=lambda record: record["level"].no >= 40  # 只记录 ERROR 及以上
)

# 异步写入（多进程安全）
logger.add(
    "logs/async.log",
    enqueue=True,                 # 异步写入，支持多进程
    rotation="100 MB"
)
```

### 4. 轮转策略 (Rotation)

| 策略 | 示例 | 说明 |
|------|------|------|
| 文件大小 | `rotation="500 MB"` | 达到指定大小后创建新文件 |
| 时间间隔 | `rotation="1 week"` | 每周轮转一次 |
| 具体时间 | `rotation="12:00"` | 每天中午 12:00 轮转 |
| 具体时间 | `rotation="00:00"` | 每天午夜轮转 |

```python
# 按大小轮转
logger.add("logs/size.log", rotation="100 MB")

# 按时间轮转
logger.add("logs/daily.log", rotation="1 day", retention="30 days")

# 特定时间轮转
logger.add("logs/midnight.log", rotation="00:00", retention="7 days")
```

### 5. 保留策略 (Retention)

```python
# 保留 7 天
logger.add("logs/app.log", retention="7 days")

# 保留 30 天
logger.add("logs/archive.log", retention="30 days")

# 自定义时间
logger.add("logs/app.log", retention="15 days")
```

### 6. 压缩格式 (Compression)

```python
# ZIP 压缩
logger.add("logs/app.zip", compression="zip")

# GZ 压缩
logger.add("logs/app.gz", compression="gz")

# BZ2 压缩
logger.add("logs/app.bz2", compression="bz2")

# XZ 压缩
logger.add("logs/app.xz", compression="xz")
```

### 7. 序列化输出 (JSON)

```python
# 启用 JSON 序列化
logger.add(
    "logs/app.json",
    serialize=True,               # 自动序列化为 JSON
    rotation="500 MB",
    retention="7 days"
)
```

输出格式：
```json
{"record": {"time": "2026-05-01T16:54:32.123456", "level": {"name": "INFO", "no": 20}, "name": "__main__", "function": "<module>", "line": 5, "file": {"pathname": "main.py"}}, "extra": {}, "message": "Hello world"}
```

### 8. 上下文绑定 (bind)

使用 `bind()` 为日志添加持久化上下文：

```python
from loguru import logger

# 绑定上下文变量
user_logger = logger.bind(user_id="123", request_id="abc-456")

user_logger.info("User logged in")       # 自动包含 user_id 和 request_id
user_logger.info("Processing request")    # 自动包含 user_id 和 request_id

# 临时上下文（with 语句）
with logger.contextize(user_id="789"):
    logger.info("Admin action")           # 包含 user_id=789
logger.info("Back to normal")             # 不包含临时上下文
```

### 9. 记录额外字段 (Extra)

```python
from loguru import logger

# 使用 extra 添加自定义字段
logger.info("Operation completed", duration_ms=150, status="success")

# 使用 bind 添加持久化额外字段
enriched_logger = logger.bind(service="paper-agent", version="1.0")
enriched_logger.info("Starting service")
```

### 10. 异常完整追踪 (Exception)

```python
from loguru import logger

# 基本异常记录
try:
    1 / 0
except Exception:
    logger.exception("Division failed")

# 带 backtrace 的异常（完整堆栈）
logger.add(
    "logs/error.log",
    backtrace=True,               # 启用完整的异常堆栈追踪
    diagnose=True,                 # 添加变量诊断信息
    level="ERROR"
)

try:
    some_function()
except Exception:
    logger.exception("Function failed")
```

### 11. 自动异常捕获 (catch)

使用 `catch()` 装饰器自动捕获异常：

```python
from loguru import logger

@logger.catch
def risky_function(x, y):
    return x / y

# 异常会被自动捕获并记录，不会崩溃程序
result = risky_function(1, 0)  # ZeroDivisionError 会被捕获并记录
```

### 12. 自定义过滤器 (filter)

```python
# 按日志级别过滤
logger.add(
    "logs/app.log",
    filter=lambda record: record["level"].no >= 20  # 只记录 INFO 及以上
)

# 按模块过滤
logger.add(
    "logs/core.log",
    filter="src.agents_v2.core"    # 只记录 core 模块的日志
)

# 多条件过滤
logger.add(
    "logs/warnings.log",
    filter=lambda record: (
        record["level"].no >= 30 or  # WARNING 及以上
        "error" in record["message"].lower()  # 或包含 error 的消息
    )
)
```

### 13. 异步安全写入 (enqueue)

```python
# 多进程/多线程环境下使用异步队列写入
logger.add(
    "logs/app.log",
    enqueue=True,                 # 使用后台队列异步写入
    rotation="500 MB",
    retention="7 days"
)
```

### 14. 自定义日志级别

```python
from loguru import logger

# 添加自定义级别
logger.level("SQL", no=25, color="<cyan>", icon="◆")

# 使用自定义级别
logger.log("SQL", "SELECT * FROM users")
logger.sql("SELECT * FROM users")  # 便捷方法
```

### 15. 动态级别修改

```python
from loguru import logger

# 全局修改级别
logger.enable("my_module")     # 启用某模块
logger.disable("my_module")    # 禁用某模块

# 运行时修改
logger.configure(levels=[...])  # 修改级别配置
```

### 16. 格式化选项

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{time}` | 时间戳 | `2026-05-01 16:54:32` |
| `{time:YYYY-MM-DD}` | 自定义时间格式 | `2026-05-01` |
| `{level}` | 日志级别 | `INFO` |
| `{level: <8}` | 左对齐的级别 | `INFO    ` |
| `{name}` | 模块名 | `module` |
| `{function}` | 函数名 | `handle_request` |
| `{line}` | 行号 | `42` |
| `{file}` | 文件名 | `module.py` |
| `{message}` | 日志消息 | `Hello` |
| `{thread.id}` | 线程 ID | `1234` |
| `{process.id}` | 进程 ID | `5678` |
| `{extra}` | 额外字段 | `{'key': 'value'}` |

### 17. 彩色输出

```python
# 使用 HTML 标签设置颜色
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    colorize=True
)

# 颜色代码
# <red>, <green>, <yellow>, <blue>, <magenta>, <cyan>, <white>
# <bold>, <underline>, <strike>
# <bg_red>, <bg_green>, etc. (背景色)
```

### 18. 装饰器记录

```python
from loguru import logger
import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__}", args=args, kwargs=kwargs)
        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} returned", result=result)
            return result
        except Exception as e:
            logger.exception(f"{func.__name__} raised {type(e).__name__}")
            raise
    return wrapper

@log_calls
def my_function(x, y):
    return x + y
```

### 19. 日志到标准错误 vs 标准输出

```python
import sys
from loguru import logger

# 默认输出到 stderr
logger.add(sys.stderr)

# 输出到 stdout
logger.add(sys.stdout)

# 输出到文件
logger.add("app.log")

# 输出到流对象
from io import StringIO
string_stream = StringIO()
logger.add(string_stream, format="{message}")
```

### 20. 多 Handler 管理

```python
from loguru import logger

# 添加多个 handler
file_handler = logger.add("app.log", rotation="100 MB", level="INFO")
error_handler = logger.add("errors.log", level="ERROR", filter=lambda r: r["level"].no >= 40)

# 动态移除 handler
logger.remove(file_handler)

# 移除默认 handler，重新配置
logger.remove()
logger.add("new-app.log")
```

### 21. 进度条集成

```python
from loguru import logger

# 使用 extra 显示进度
for i in range(100):
    logger.info(f"Processing {i}/100", progress=i/100, total=100)
```

### 22. 标准库 logging 兼容

```python
import logging
from loguru import logger

# 将 loguru 作为 logging Handler
logging.getLogger().addHandler(
    lambda record: logger.info(record.getMessage())
)

# 或者使用拦截器
class LoguruInterceptHandler(logging.Handler):
    def emit(self, record):
        logger.log(
            record.levelname,
            record.getMessage()
        )

handler = LoguruInterceptHandler()
logging.getLogger().addHandler(handler)
```

---

## API 参考

### `setup_logging()`

初始化日志系统。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | str | "INFO" | 日志级别 (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `log_file` | str | None | 日志文件名（不含路径） |
| `log_dir` | str | "logs" | 日志目录 |
| `rotation` | str | "500 MB" | 轮转策略 ("500 MB", "00:00", "1 week") |
| `retention` | str | "7 days" | 保留策略 ("7 days", "30 days") |
| `structured` | bool | False | 是否输出 JSON 格式 |
| `format_string` | str | None | 自定义格式字符串 |
| `use_color` | bool | True | 是否使用颜色输出 |
| `backtrace` | bool | True | 是否启用完整异常堆栈追踪 |
| `diagnose` | bool | True | 是否添加变量诊断信息 |
| `enqueue` | bool | True | 是否使用异步队列写入（多进程安全） |
| `compression` | str | "zip" | 压缩格式 ("zip", "gz", "bz2", "xz") |
| `serialize` | bool | False | 是否序列化为 JSON 格式 |
| `error_file` | str | None | 独立的错误日志文件名 |

### `add_sink()`

添加额外的日志 sink。

```python
from src.agents_v2.logging_config import add_sink, logger

# 添加按模块过滤的文件输出
sink_id = add_sink(
    "logs/my_module.log",
    level="DEBUG",
    filter_func=lambda r: r["name"].startswith("my_module")
)

# 移除 sink
from src.agents_v2.logging_config import remove_sink
remove_sink(sink_id)
```

### `bind_context()`

创建绑定上下文的日志记录器。

```python
from src.agents_v2.logging_config import logger, bind_context

# 使用上下文管理器
with bind_context(request_id="123", user_id="456"):
    logger.info("Request processed")
```

### `get_logger()`

获取全局 logger 实例。

```python
from src.agents_v2.logging_config import get_logger
logger = get_logger()
```

### `get_logging_logger(name)`

获取兼容 logging 模块的 logger。

```python
from src.agents_v2.logging_config import get_logging_logger
logger = get_logging_logger(__name__)
```

---

## 日志级别

| 级别 | 值 | 方法 | 说明 |
|------|-----|------|------|
| TRACE | 5 | `logger.trace()` | 最详细跟踪信息 |
| DEBUG | 10 | `logger.debug()` | 调试信息 |
| INFO | 20 | `logger.info()` | 普通信息 |
| SUCCESS | 25 | `logger.success()` | 成功信息 |
| WARNING | 30 | `logger.warning()` | 警告信息 |
| ERROR | 40 | `logger.error()` | 错误信息 |
| CRITICAL | 50 | `logger.critical()` | 严重错误 |

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LOG_LEVEL` | 日志级别 | "INFO" |
| `LOG_FILE` | 日志文件名 | None |
| `LOG_DIR` | 日志目录 | "logs" |

---

## 最佳实践

### 1. 模块级 Logger

每个模块使用 `get_logging_logger(__name__)` 创建 logger：

```python
# my_module.py
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)

def process():
    logger.info("Processing started")
```

### 2. 结构化日志

使用 extra 字段记录结构化数据：

```python
logger.info(
    "Request processed",
    request_id="abc-123",
    user_id="user-456",
    duration_ms=150,
    status="success"
)
```

### 3. 错误日志

始终使用 `logger.exception()` 记录异常：

```python
try:
    result = risky_operation()
except Exception:
    logger.exception("Operation failed")
```

### 4. 性能日志

记录操作耗时：

```python
import time
start = time.time()
result = do_work()
logger.info("Work completed", duration_ms=(time.time() - start) * 1000)
```

### 5. 上下文日志

在请求处理中绑定上下文：

```python
def handle_request(request_id):
    request_logger = logger.bind(request_id=request_id)
    request_logger.info("Request received")
    # ... 处理逻辑
    request_logger.info("Request completed")

# 或使用 LoggingAdapter
adapter = get_logging_logger(__name__)
user_adapter = adapter.bind(user_id="123")
user_adapter.info("User action")

# 或使用上下文管理器
from src.agents_v2.logging_config import bind_context
with bind_context(request_id="abc"):
    logger.info("Inside context")
```

### 6. 装饰器捕获异常

```python
from src.agents_v2.logging_config import logger

# 使用 @logger.catch 自动捕获异常
@logger.catch
def risky_function():
    return 1 / 0
```

---

## 迁移指南

### 从 `logging` 迁移

**之前：**
```python
import logging

logger = logging.getLogger(__name__)
logger.info("Hello, %s", "world")
```

**之后：**
```python
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)
logger.info("Hello, %s", "world")  # 接口兼容
```

### 从 `print()` 迁移

**之前：**
```python
print("User logged in:", user_id)
```

**之后：**
```python
logger.info("User logged in", user_id=user_id)
```

---

## 文件结构

```
src/agents_v2/
├── logging_config.py      # 日志配置模块
├── migrate_logging.py      # 迁移脚本
└── ...
```

---

## 示例项目文件

### 在 `src/main.py` 中初始化

```python
from src.agents_v2.logging_config import setup_logging, logger

# 初始化日志系统
setup_logging(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    log_file="paper_agent.log",
    log_dir="logs"
)

logger.info("Paper Agent 学术论文写作辅助系统启动")
```

### 在模块中使用

```python
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)

def process_request(request_id: str):
    logger.info(f"Processing request: {request_id}")
    try:
        result = do_something()
        logger.debug("Operation completed", result=result)
        return result
    except Exception:
        logger.exception("Operation failed", request_id=request_id)
        raise
```
