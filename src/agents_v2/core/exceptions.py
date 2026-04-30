"""
自定义异常类

提供系统级异常的统一定义
"""


class AgentError(Exception):
    """Agent基础异常"""
    pass


class LLMError(AgentError):
    """LLM调用相关错误"""
    pass


class ValidationError(AgentError):
    """输入验证错误"""
    pass


class ConfigurationError(AgentError):
    """配置错误"""
    pass


class TimeoutError(AgentError):
    """超时错误"""
    pass


class ExternalAPIError(AgentError):
    """外部API调用错误"""
    pass


class CacheError(AgentError):
    """缓存相关错误"""
    pass


class CircuitBreakerOpenError(AgentError):
    """熔断器打开错误"""
    pass


class AgentNotFoundError(AgentError):
    """Agent未找到错误"""
    pass


class InvalidStateError(AgentError):
    """无效状态错误"""
    pass
