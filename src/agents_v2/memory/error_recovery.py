"""
记忆系统错误恢复 - Memory Error Recovery

提供:
- MemoryErrorRecovery: 错误恢复机制
- MemoryCircuitBreaker: 熔断器
- MemoryFallback: 降级策略
"""
import asyncio
import time
from typing import Any, Callable, Optional, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import logging

T = TypeVar('T')

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """失败类型"""
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    QUOTA = "quota"
    UNKNOWN = "unknown"


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

    当失败率超过阈值时,熔断器打开,快速返回失败
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_attempts: int = 3
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_attempts = half_open_attempts

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half_open
        self._half_open_successes = 0

    @property
    def state(self) -> str:
        """获取当前状态"""
        if self._state == "open":
            # 检查是否应该转换到half_open
            if self._last_failure_time and \
               (time.time() - self._last_failure_time) > self._recovery_timeout:
                self._state = "half_open"
                self._half_open_successes = 0
        return self._state

    def record_success(self) -> None:
        """记录成功"""
        if self._state == "half_open":
            self._half_open_successes += 1
            if self._half_open_successes >= self._half_open_attempts:
                self._state = "closed"
                self._failure_count = 0

    def record_failure(self, failure_type: FailureType = FailureType.UNKNOWN) -> None:
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if failure_type == FailureType.QUOTA:
            # 配额失败,立即熔断
            self._state = "open"
        elif self._failure_count >= self._failure_threshold:
            self._state = "open"

    def is_open(self) -> bool:
        """是否打开"""
        return self.state == "open"

    def get_stats(self) -> dict:
        """获取统计"""
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time
        }


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
        带退避的重试

        Args:
            operation: 操作函数
            max_retries: 最大重试次数
            base_delay: 基础延迟(秒)
            max_delay: 最大延迟(秒)
            operation_name: 操作名称

        Returns:
            操作结果
        """
        circuit_breaker = self.get_circuit_breaker(operation_name)

        for attempt in range(max_retries + 1):
            self._stats.total_attempts += 1

            try:
                # 检查熔断器
                if circuit_breaker.is_open():
                    raise Exception(f"Circuit breaker is open for {operation_name}")

                result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
                circuit_breaker.record_success()
                self._stats.successful_recoveries += 1
                return result

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < max_retries:
                    # 计算延迟
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    await asyncio.sleep(delay)

                    # 判断失败类型
                    if "quota" in str(e).lower() or "rate limit" in str(e).lower():
                        circuit_breaker.record_failure(FailureType.QUOTA)
                    elif "timeout" in str(e).lower():
                        circuit_breaker.record_failure(FailureType.TIMEOUT)
                    elif "connection" in str(e).lower():
                        circuit_breaker.record_failure(FailureType.CONNECTION)
                    else:
                        circuit_breaker.record_failure(FailureType.UNKNOWN)

        self._stats.failed_recoveries += 1
        self._stats.last_failure_time = time.time()
        raise Exception(f"All {max_retries + 1} attempts failed for {operation_name}")

    async def execute_with_recovery(
        self,
        operation: Callable,
        fallback: Optional[Callable] = None,
        operation_name: str = "operation"
    ) -> Any:
        """
        带恢复的操作执行

        Args:
            operation: 操作函数
            fallback: 降级函数
            operation_name: 操作名称

        Returns:
            操作结果
        """
        circuit_breaker = self.get_circuit_breaker(operation_name)

        if circuit_breaker.is_open():
            if fallback:
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
            raise Exception(f"Circuit breaker is open for {operation_name}")

        try:
            result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
            circuit_breaker.record_success()
            return result
        except Exception as e:
            circuit_breaker.record_failure()

            if fallback:
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
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
