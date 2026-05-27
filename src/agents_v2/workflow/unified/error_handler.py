"""
错误处理与降级策略

提供:
1. FallbackHandler: 降级处理
2. RetryPolicy: 重试策略
3. ErrorContext: 错误上下文
4. ErrorClassifier: 错误分类
5. log_error_with_context: 智能日志记录
6. RecoveryStrategy: 恢复策略
"""
from src.agents_v2.logging_config import get_logging_logger

import logging
import time

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"      # 不影响流程，可忽略（LLM调用失败但有fallback）
    MEDIUM = "medium"  # 需要注意，但可继续
    HIGH = "high"    # 需要干预
    CRITICAL = "critical"  # 流程必须停止


class ErrorType(str, Enum):
    """错误类型 - 用于区分不同错误，减少误导性日志"""
    LLM_FAILURE = "llm_failure"           # LLM调用失败（有fallback）
    PARSING_FAILURE = "parsing_failure"   # JSON解析失败（有fallback）
    EXTERNAL_API_FAILURE = "external_api_failure"  # 外部API失败（有fallback）
    VALIDATION_FAILURE = "validation_failure"  # 验证失败（需要关注）
    SYSTEM_ERROR = "system_error"          # 系统错误（需要关注）
    USER_ERROR = "user_error"             # 用户输入错误


@dataclass
class ErrorContext:
    """错误上下文"""
    error: Exception
    phase: str
    agent_name: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    error_type: ErrorType = ErrorType.SYSTEM_ERROR
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    recovered: bool = True  # 是否有fallback恢复

    def should_log_as_warning(self) -> bool:
        """判断是否应该只记录为警告（而非error级别）"""
        if self.recovered and self.error_type in (
            ErrorType.LLM_FAILURE,
            ErrorType.PARSING_FAILURE,
            ErrorType.EXTERNAL_API_FAILURE
        ):
            return True
        return False


@dataclass
class RetryPolicy:
    """重试策略配置"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retry_on: tuple = (Exception,)


class FallbackHandler:
    """降级处理handler"""

    PHASE_FALLBACKS = {
        "topic": {
            "default_output": {
                "selected_topic": {
                    "title": "待定研究主题",
                    "scope": "需要进一步明确",
                    "novelty_score": 0.3
                },
                "feasibility_report": {"score": 0.5, "concerns": ["需要用户确认"]}
            },
            "skip_allowed": False
        },
        "literature": {
            "default_output": {
                "papers": [],
                "literature_map": {},
                "gaps_identified": []
            },
            "skip_allowed": True
        },
        "methodology": {
            "default_output": {
                "recommended_methods": [],
                "rigor_assessment": {"score": 0.4}
            },
            "skip_allowed": True
        },
        "argument": {
            "default_output": {
                "argument_framework": {},
                "logical_gaps": ["论证框架未建立"]
            },
            "skip_allowed": False
        },
        "writing": {
            "default_output": {
                "outline": [],
                "draft_sections": [],
                "report": "内容生成失败"
            },
            "skip_allowed": False
        },
        "polish": {
            "default_output": {
                "polished_text": "",
                "issues_identified": []
            },
            "skip_allowed": True
        }
    }

    def __init__(self, enable_caching: bool = True):
        self.enable_caching = enable_caching
        self.cache: Dict[str, Any] = {}

    def get_fallback(
        self,
        phase: str,
        context: Dict[str, Any],
        error: Optional[Exception] = None
    ) -> Dict[str, Any]:
        logger.warning(f"Using fallback for phase: {phase}")

        fallback_config = self.PHASE_FALLBACKS.get(phase, {})
        default_output = fallback_config.get("default_output", {})

        if self.enable_caching and phase in self.cache:
            logger.info(f"Using cached result for phase: {phase}")
            return self.cache[phase]

        if error:
            default_output["_error"] = str(error)
            default_output["_fallback_used"] = True

        return default_output

    def cache_result(self, phase: str, result: Dict[str, Any]):
        if self.enable_caching:
            self.cache[phase] = result
            logger.debug(f"Cached result for phase: {phase}")

    def get_cached(self, phase: str) -> Optional[Dict[str, Any]]:
        return self.cache.get(phase)

    def clear_cache(self):
        self.cache.clear()


class ErrorAccumulator:
    """错误累积器"""

    def __init__(self, max_errors: int = 50):
        self.max_errors = max_errors
        self.errors: List[ErrorContext] = []

    def add(self, context: ErrorContext):
        self.errors.append(context)
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)

    def get_by_phase(self, phase: str) -> List[ErrorContext]:
        return [e for e in self.errors if e.phase == phase]

    def get_by_severity(self, severity: ErrorSeverity) -> List[ErrorContext]:
        return [e for e in self.errors if e.severity == severity]

    def has_critical(self) -> bool:
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_errors": len(self.errors),
            "by_phase": {
                phase: len(self.get_by_phase(phase))
                for phase in set(e.phase for e in self.errors)
            },
            "by_severity": {
                sev.value: len(self.get_by_severity(sev))
                for sev in ErrorSeverity
            },
            "has_critical": self.has_critical()
        }


class ErrorClassifier:
    """错误分类器"""

    @staticmethod
    def classify(error: Exception, context: str = "") -> ErrorType:
        error_msg = str(error).lower()

        if any(keyword in error_msg for keyword in ["llm", "openai", "anthropic", "api", "rate limit", "timeout"]):
            return ErrorType.LLM_FAILURE
        if any(keyword in error_msg for keyword in ["json", "parse", "decode"]):
            return ErrorType.PARSING_FAILURE
        if any(keyword in error_msg for keyword in ["arxiv", "pubmed", "http", "request", "connection"]):
            return ErrorType.EXTERNAL_API_FAILURE
        if any(keyword in error_msg for keyword in ["validation", "invalid", "empty", "missing"]):
            return ErrorType.VALIDATION_FAILURE

        return ErrorType.SYSTEM_ERROR

    @staticmethod
    def get_severity(error_type: ErrorType, has_fallback: bool = True) -> ErrorSeverity:
        if not has_fallback:
            if error_type == ErrorType.LLM_FAILURE:
                return ErrorSeverity.HIGH
            return ErrorSeverity.CRITICAL
        return ErrorSeverity.LOW


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: str,
    recovered: bool = True,
    extra_data: Optional[Dict[str, Any]] = None
):
    """
    带上下文的智能日志记录
    有fallback恢复 -> warning级别（避免error级别误导）
    无fallback -> error级别
    """
    error_type = ErrorClassifier.classify(error, context)
    severity = ErrorClassifier.get_severity(error_type, recovered)

    log_data = {
        "error_type": error_type.value,
        "recovered": recovered,
        "context": context
    }
    if extra_data:
        log_data.update(extra_data)

    if severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM):
        logger.warning(f"[{error_type.value}] {context}: {error}", extra=log_data)
    else:
        logger.error(f"[{error_type.value}] {context}: {error}", extra=log_data)


class RecoveryStrategy:
    """恢复策略"""

    @staticmethod
    def should_retry(error: Exception, retry_policy: RetryPolicy, current_retry: int) -> bool:
        if current_retry >= retry_policy.max_retries:
            return False
        return isinstance(error, retry_policy.retry_on)

    @staticmethod
    def get_delay(retry_policy: RetryPolicy, current_retry: int) -> float:
        delay = retry_policy.initial_delay * (retry_policy.exponential_base ** current_retry)
        return min(delay, retry_policy.max_delay)


async def execute_with_retry(
    func: Callable,
    retry_policy: Optional[RetryPolicy] = None,
    fallback_handler: Optional[FallbackHandler] = None,
    phase: str = "unknown",
    context: Optional[Dict[str, Any]] = None
) -> Any:
    retry_policy = retry_policy or RetryPolicy()
    current_retry = 0

    while True:
        try:
            result = await func()
            return result
        except Exception as e:
            if not RecoveryStrategy.should_retry(e, retry_policy, current_retry):
                logger.error(f"Max retries reached for phase {phase}: {e}")
                if fallback_handler:
                    return fallback_handler.get_fallback(phase, context or {}, e)
                raise

            current_retry += 1
            delay = RecoveryStrategy.get_delay(retry_policy, current_retry)
            logger.warning(f"Retry {current_retry}/{retry_policy.max_retries} for {phase}, delay={delay}s")
            time.sleep(delay)
