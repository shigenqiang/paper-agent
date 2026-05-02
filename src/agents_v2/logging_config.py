"""
Logging Config - 日志配置 (已迁移)

此文件已迁移到: src/agents_v2/server/logging_config.py

请更新您的导入语句:
- 旧: from src.agents_v2.logging_config import get_logging_logger
- 新: from src.agents_v2.server.logging_config import get_logging_logger

此文件仅用于向后兼容，不应在新代码中使用。
"""
import sys
import warnings

# 发出弃用警告
warnings.warn(
    "src.agents_v2.logging_config 已迁移到 src.agents_v2.server.logging_config。"
    "请更新您的导入语句。",
    DeprecationWarning,
    stacklevel=2
)

# 延迟导入函数，避免循环导入
def __getattr__(name):
    if name == 'get_logging_logger':
        from src.agents_v2.server.logging_config import get_logging_logger
        return get_logging_logger
    elif name == 'add_sink':
        from src.agents_v2.server.logging_config import add_sink
        return add_sink
    elif name == 'get_module_logger':
        from src.agents_v2.server.logging_config import get_module_logger
        return get_module_logger
    elif name == 'setup_logging':
        from src.agents_v2.server.logging_config import setup_logging
        return setup_logging
    elif name == 'logger':
        from src.agents_v2.server.logging_config import get_logger
        return get_logger()
    raise AttributeError(f"module 'src.agents_v2.logging_config' has no attribute '{name}'")

def __dir__():
    return ['get_logging_logger', 'add_sink', 'get_module_logger', 'setup_logging', 'logger']