"""LLM 错误类型"""

from __future__ import annotations


class LLMServiceError(Exception):
    """LLM 服务基础异常"""

    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        prompt_name: str = "",
        prompt_version: str = "",
        model: str = "",
    ):
        super().__init__(message)
        self.error_type = error_type
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        self.model = model


class LLMProviderError(LLMServiceError):
    """模型提供商错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_type="provider_error", **kwargs)


class LLMTimeoutError(LLMServiceError):
    """超时错误"""

    def __init__(self, message: str = "LLM request timed out", **kwargs):
        super().__init__(message, error_type="timeout", **kwargs)


class LLMRateLimitError(LLMServiceError):
    """限流错误"""

    def __init__(self, message: str = "Rate limited", retry_after: float = 0, **kwargs):
        super().__init__(message, error_type="rate_limited", **kwargs)
        self.retry_after = retry_after


class EmptyLLMResponseError(LLMServiceError):
    """空响应错误"""

    def __init__(self, message: str = "LLM returned empty response", **kwargs):
        super().__init__(message, error_type="empty_response", **kwargs)


class JsonExtractionError(LLMServiceError):
    """JSON 提取失败"""

    def __init__(self, message: str = "Failed to extract JSON from response", **kwargs):
        super().__init__(message, error_type="parse_failed", **kwargs)


class StructuredOutputError(LLMServiceError):
    """结构化输出 schema 校验失败"""

    def __init__(self, message: str, validation_errors: list[str] | None = None, **kwargs):
        super().__init__(message, error_type="schema_failed", **kwargs)
        self.validation_errors = validation_errors or []


class JsonRepairError(LLMServiceError):
    """JSON 修复失败"""

    def __init__(self, message: str = "JSON repair failed", **kwargs):
        super().__init__(message, error_type="repair_failed", **kwargs)
