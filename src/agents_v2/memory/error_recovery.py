"""
记忆系统错误恢复 - Memory Error Recovery

提供:
- MemoryErrorRecovery: 错误恢复机制
- MemoryCircuitBreaker: 熔断器（基于 core CircuitBreaker）
- MemoryFallback: 降级策略

底层使用 core/error_recovery.py 的共享原语。
"""
from src.agents_v2.logging_config import get_logging_logger

import asyncio
import time
from typing import Any, Callable, Optional, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum

from ..core.error_recovery import (
    CircuitBreaker,
    ErrorCategory as CoreErrorCategory,
    retry_with_backoff as core_retry_with_backoff,
    with_fallback as core_with_fallback,
    classify_error,
)

T = TypeVar('T')

logger = get_logging_logger(__name__)


class FailureType(Enum):
    """失败类型"""
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    QUOTA = "quota"
    UNKNOWN = "unknown"


# FailureType → core ErrorCategory 映射
_FAILURE_TO_CATEGORY = {
    FailureType.TIMEOUT: CoreErrorCategory.TIMEOUT,
    FailureType.CONNECTION: CoreErrorCategory.CONNECTION,
    FailureType.QUOTA: CoreErrorCategory.QUOTA,
    FailureType.UNKNOWN: CoreErrorCategory.UNKNOWN,
}


@dataclass
class RecoveryStats:
    """恢复统计"""
    total_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    last_failure_time: float = 0.0
    last_failure_type: Optional[FailureType] = None


class MemoryCircuitBreaker:
    """
    记忆系统熔断器

    基于 core.CircuitBreaker 的薄包装，保持原有接口不变。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_attempts: int = 3
    ):
        self._core = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_attempts=half_open_attempts,
            name="memory",
        )

    @property
    def state(self) -> str:
        return self._core.state

    def record_success(self) -> None:
        self._core.record_success()

    def record_failure(self, failure_type: FailureType = FailureType.UNKNOWN) -> None:
        category = _FAILURE_TO_CATEGORY.get(failure_type, CoreErrorCategory.UNKNOWN)
        self._core.record_failure(category)

    def is_open(self) -> bool:
        return self._core.is_open()

    def get_stats(self) -> dict:
        return self._core.get_stats()


class MemoryFallback:
    """
    记忆系统降级策略

    当主存储失败时,降级到备用存储
    """

    def __init__(self):
        self._fallback_order = [
            "long_term",
            "session",
            "short_term"
        ]

    async def execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_funcs: dict
    ) -> Any:
        """
        带降级的执行

        Args:
            primary_func: 主函数
            fallback_funcs: 降级函数字典 {storage_type: func}

        Returns:
            执行结果
        """
        try:
            return await primary_func()
        except Exception as e:
            logger.warning(f"Primary execution failed: {e}")

            # 按顺序尝试降级
            for storage_type in self._fallback_order:
                if storage_type in fallback_funcs:
                    try:
                        fallback_func = fallback_funcs[storage_type]
                        result = await fallback_func() if asyncio.iscoroutinefunction(fallback_func) else fallback_func()
                        logger.info(f"Fallback to {storage_type} succeeded")
                        return result
                    except Exception:
                        continue

            # 所有降级都失败
            raise


class MemoryErrorRecovery:
    """
    记忆系统错误恢复

    职责:
    - 重试机制
    - 降级策略
    - 熔断器
    """

    def __init__(self):
        self._circuit_breakers: dict = {}
        self._fallback = MemoryFallback()
        self._stats = RecoveryStats()

    def get_circuit_breaker(self, operation: str) -> MemoryCircuitBreaker:
        """获取操作的熔断器"""
        if operation not in self._circuit_breakers:
            self._circuit_breakers[operation] = MemoryCircuitBreaker()
        return self._circuit_breakers[operation]

    async def retry_with_backoff(
        self,
        operation: Callable[[], Any],
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 2.0,
        operation_name: str = "operation"
    ) -> Any:
        """
        带退避的重试（委托给 core.retry_with_backoff）

        Args:
            operation: 操作函数
            max_retries: 最大重试次数
            base_delay: 基础延迟(秒)
            max_delay: 最大延迟(秒)
            operation_name: 操作名称

        Returns:
            操作结果
        """
        cb = self.get_circuit_breaker(operation_name)
        self._stats.total_attempts += 1

        try:
            result = await core_retry_with_backoff(
                operation=operation,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                circuit_breaker=cb._core,
            )
            self._stats.successful_recoveries += 1
            return result
        except Exception:
            self._stats.failed_recoveries += 1
            self._stats.last_failure_time = time.time()
            raise

    async def execute_with_recovery(
        self,
        operation: Callable,
        fallback: Optional[Callable] = None,
        operation_name: str = "operation"
    ) -> Any:
        """
        带恢复的操作执行（委托给 core.with_fallback）

        Args:
            operation: 操作函数
            fallback: 降级函数
            operation_name: 操作名称

        Returns:
            操作结果
        """
        cb = self.get_circuit_breaker(operation_name)

        if fallback:
            return await core_with_fallback(
                primary=operation,
                fallback=fallback,
                circuit_breaker=cb._core,
            )

        # 无 fallback 时，熔断直接抛异常
        if cb.is_open():
            raise Exception(f"Circuit breaker is open for {operation_name}")

        try:
            result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
            cb.record_success()
            return result
        except Exception as e:
            cb.record_failure()
            raise

    def get_stats(self) -> RecoveryStats:
        """获取恢复统计"""
        return self._stats

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = RecoveryStats()

    def reset_circuit_breaker(self, operation: str) -> None:
        """重置熔断器"""
        if operation in self._circuit_breakers:
            self._circuit_breakers[operation]._state = "closed"
            self._circuit_breakers[operation]._failure_count = 0


class ResilientMemoryWrapper:
    """
    弹性记忆包装器

    为记忆操作添加错误恢复能力
    """

    def __init__(self, memory_manager: Any):
        self._memory = memory_manager
        self._recovery = MemoryErrorRecovery()

    async def remember(self, *args, **kwargs) -> Any:
        """带恢复的remember"""
        async def op():
            return await self._memory.remember(*args, **kwargs)

        return await self._recovery.execute_with_recovery(
            op,
            fallback=lambda: None,
            operation_name="remember"
        )

    async def recall(self, *args, **kwargs) -> Any:
        """带恢复的recall"""
        async def op():
            return await self._memory.recall(*args, **kwargs)

        async def fallback():
            return []

        return await self._recovery.execute_with_recovery(
            op,
            fallback=fallback,
            operation_name="recall"
        )

    async def search(self, *args, **kwargs) -> Any:
        """带恢复的search"""
        async def op():
            return await self._memory.search(*args, **kwargs)

        async def fallback():
            return []

        return await self._recovery.execute_with_recovery(
            op,
            fallback=fallback,
            operation_name="search"
        )
