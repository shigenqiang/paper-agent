"""Core 模块 - 核心基础类

包含:
- base_agent: BaseAgent 抽象基类和核心类型
- exceptions: 自定义异常层次
"""

from .base_agent import (
    BaseAgent,
    AgentInput,
    AgentOutput,
    AgentCapability,
    LLMConfig,
    Tool,
    VirtualTool,
)
from .exceptions import (
    AgentError,
    LLMError,
    ValidationError,
    ConfigurationError,
    TimeoutError,
    ExternalAPIError,
    CacheError,
    CircuitBreakerOpenError,
    AgentNotFoundError,
    InvalidStateError,
)

__all__ = [
    "BaseAgent", "AgentInput", "AgentOutput", "AgentCapability",
    "LLMConfig", "Tool", "VirtualTool",
    "AgentError", "LLMError", "ValidationError", "ConfigurationError",
    "TimeoutError", "ExternalAPIError", "CacheError", "CircuitBreakerOpenError",
    "AgentNotFoundError", "InvalidStateError",
]
