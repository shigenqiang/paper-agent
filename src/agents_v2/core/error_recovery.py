"""
Core Error Recovery - 共享错误恢复原语

提供通用的错误恢复构建块，供各子系统使用：
- CircuitBreaker: 熔断器（closed → open → half_open）
- retry_with_backoff: 指数退避重试
- with_fallback: 降级执行
- classify_error: 错误分类

设计原则：
- 零外部依赖，仅使用标准库
- 同时支持 sync 和 async callable
- 各子系统（unified/memory/agents）可组合使用这些原语
"""
import asyncio
import time
import logging
from typing import Any, Callable, Optional, TypeVar
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')
logger = logging.getLogger(__name__)


# ============ 错误分类 ============

class ErrorCategory(str, Enum):
    """错误类别"""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CONNECTION = "connection"
    INVALID_INPUT = "invalid_input"
    CONTEXT_OVERFLOW = "context_overflow"
    EXTERNAL_API = "external_api"
    QUOTA = "quota"
    UNKNOWN = "unknown"


def classify_error(error: Exception) -> ErrorCategory:
    """
    根据异常消息自动分类错误

    Args:
        error: 异常实例

    Returns:
        ErrorCategory 枚举值
    """
    msg = str(error).lower()

    if "rate limit" in msg or "429" in msg or "too many requests" in msg:
        return ErrorCategory.RATE_LIMIT
    if "quota" in msg:
        return ErrorCategory.QUOTA
    if "timeout" in msg or "timed out" in msg:
        return ErrorCategory.TIMEOUT
    if "connection" in msg or "connect" in msg:
        return ErrorCategory.CONNECTION
    if "context" in msg and ("overflow" in msg or "exceed" in msg or "length" in msg):
        return ErrorCategory.CONTEXT_OVERFLOW
    if "validation" in msg or "invalid" in msg:
        return ErrorCategory.INVALID_INPUT
    if any(kw in msg for kw in ("arxiv", "pubmed", "http", "api")):
        return ErrorCategory.EXTERNAL_API

    return ErrorCategory.UNKNOWN


# ============ 熔断器 ============

@dataclass
class CircuitBreakerStats:
    """熔断器统计"""
    total_calls: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    通用熔断器

    三态：closed（正常）→ open（熔断）→ half_open（试探）

    使用示例:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

        if cb.is_open():
            raise Exception("Circuit is open")

        try:
            result = await some_operation()
            cb.record_success()
        except Exception as e:
            cb.record_failure()
            raise
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_attempts: int = 3,
        name: str = "default"
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_attempts = half_open_attempts
        self._name = name

        self._state = "closed"  # closed | open | half_open
        self._failure_count = 0
        self._half_open_successes = 0
        self._last_failure_time: Optional[float] = None
        self._stats = CircuitBreakerStats()

    @property
    def state(self) -> str:
        """获取当前状态，open 超时后自动转 half_open"""
        if self._state == "open" and self._last_failure_time:
            if (time.time() - self._last_failure_time) > self._recovery_timeout:
                self._state = "half_open"
                self._half_open_successes = 0
                self._stats.state_changes += 1
                logger.info(f"CircuitBreaker[{self._name}] open → half_open")
        return self._state

    def is_open(self) -> bool:
        """是否处于熔断状态"""
        return self.state == "open"

    def record_success(self) -> None:
        """记录一次成功调用"""
        self._stats.total_calls += 1

        if self._state == "half_open":
            self._half_open_successes += 1
            if self._half_open_successes >= self._half_open_attempts:
                self._state = "closed"
                self._failure_count = 0
                self._stats.state_changes += 1
                logger.info(f"CircuitBreaker[{self._name}] half_open → closed")

    def record_failure(self, category: ErrorCategory = ErrorCategory.UNKNOWN) -> None:
        """记录一次失败调用"""
        self._stats.total_calls += 1
        self._stats.total_failures += 1
        self._stats.consecutive_failures += 1
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._stats.last_failure_time = self._last_failure_time

        # 配额错误立即熔断
        if category == ErrorCategory.QUOTA:
            self._state = "open"
            self._stats.state_changes += 1
            logger.warning(f"CircuitBreaker[{self._name}] quota error → open")
        elif self._failure_count >= self._failure_threshold:
            self._state = "open"
            self._stats.state_changes += 1
            logger.warning(
                f"CircuitBreaker[{self._name}] threshold({self._failure_threshold}) reached → open"
            )

    def reset(self) -> None:
        """手动重置熔断器"""
        self._state = "closed"
        self._failure_count = 0
        self._half_open_successes = 0
        self._stats.consecutive_failures = 0

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "name": self._name,
            "state": self.state,
            "failure_count": self._failure_count,
            "total_calls": self._stats.total_calls,
            "total_failures": self._stats.total_failures,
            "consecutive_failures": self._stats.consecutive_failures,
            "state_changes": self._stats.state_changes,
        }


# ============ 重试 ============

async def retry_with_backoff(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Any:
    """
    指数退避重试

    Args:
        operation: 要重试的 callable（支持 sync/async）
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        circuit_breaker: 可选的熔断器
        on_retry: 可选的重试回调 (attempt, error) -> None

    Returns:
        操作结果

    Raises:
        最后一次重试的异常
    """
    for attempt in range(max_retries + 1):
        # 熔断检查
        if circuit_breaker and circuit_breaker.is_open():
            raise Exception(f"Circuit breaker is open, aborting retry")

        try:
            if asyncio.iscoroutinefunction(operation):
                result = await operation()
            else:
                result = operation()

            if circuit_breaker:
                circuit_breaker.record_success()
            return result

        except Exception as e:
            if circuit_breaker:
                category = classify_error(e)
                circuit_breaker.record_failure(category)

            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                if on_retry:
                    on_retry(attempt, e)
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed: {e}")
                raise


# ============ 降级 ============

async def with_fallback(
    primary: Callable,
    fallback: Callable,
    circuit_breaker: Optional[CircuitBreaker] = None,
) -> Any:
    """
    带降级的执行

    主操作失败时自动执行降级操作。

    Args:
        primary: 主操作（支持 sync/async）
        fallback: 降级操作（支持 sync/async）
        circuit_breaker: 可选的熔断器

    Returns:
        主操作或降级操作的结果
    """
    # 熔断时直接走降级
    if circuit_breaker and circuit_breaker.is_open():
        logger.info("Circuit open, executing fallback directly")
        if asyncio.iscoroutinefunction(fallback):
            return await fallback()
        return fallback()

    try:
        if asyncio.iscoroutinefunction(primary):
            result = await primary()
        else:
            result = primary()

        if circuit_breaker:
            circuit_breaker.record_success()
        return result

    except Exception as e:
        logger.warning(f"Primary failed: {e}, executing fallback")
        if circuit_breaker:
            circuit_breaker.record_failure(classify_error(e))

        if asyncio.iscoroutinefunction(fallback):
            return await fallback()
        return fallback()


# ============ 管理器 ============

class RecoveryManager:
    """
    错误恢复管理器

    集中管理熔断器实例，提供统一的恢复接口。

    使用示例:
        manager = RecoveryManager()

        # 为 LLM 调用创建带熔断的重试
        result = await manager.retry(
            llm_call,
            operation_name="llm_generate",
            max_retries=3
        )

        # 带降级的执行
        result = await manager.execute_with_fallback(
            primary=search_api,
            fallback=cached_search,
            operation_name="paper_search"
        )
    """

    def __init__(self):
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def get_circuit_breaker(
        self,
        operation_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> CircuitBreaker:
        """获取或创建操作对应的熔断器"""
        if operation_name not in self._circuit_breakers:
            self._circuit_breakers[operation_name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                name=operation_name,
            )
        return self._circuit_breakers[operation_name]

    async def retry(
        self,
        operation: Callable,
        operation_name: str = "default",
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> Any:
        """带熔断器的重试"""
        cb = circuit_breaker or self.get_circuit_breaker(operation_name)
        return await retry_with_backoff(
            operation=operation,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            circuit_breaker=cb,
        )

    async def execute_with_fallback(
        self,
        primary: Callable,
        fallback: Callable,
        operation_name: str = "default",
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> Any:
        """带降级的执行"""
        cb = circuit_breaker or self.get_circuit_breaker(operation_name)
        return await with_fallback(
            primary=primary,
            fallback=fallback,
            circuit_breaker=cb,
        )

    def get_all_stats(self) -> dict:
        """获取所有熔断器统计"""
        return {
            name: cb.get_stats()
            for name, cb in self._circuit_breakers.items()
        }

    def reset_all(self) -> None:
        """重置所有熔断器"""
        for cb in self._circuit_breakers.values():
            cb.reset()


# 全局实例
_recovery_manager: Optional[RecoveryManager] = None


def get_recovery_manager() -> RecoveryManager:
    """获取全局错误恢复管理器"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = RecoveryManager()
    return _recovery_manager
