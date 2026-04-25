"""
熔断器 - 防止级联失败的防护机制
"""
import time
from typing import Callable, Any, Optional
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常，允许请求通过
    OPEN = "open"          # 断开，拒绝请求
    HALF_OPEN = "half_open"  # 半开，允许尝试


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""
    pass


class CircuitBreaker:
    """
    熔断器实现

    状态转换:
    CLOSED -> OPEN: 失败次数超过阈值
    OPEN -> HALF_OPEN: 超过恢复超时
    HALF_OPEN -> CLOSED: 请求成功
    HALF_OPEN -> OPEN: 请求失败
    """

    def __init__(
        self,
        name: str = "circuit_breaker",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器执行函数

        Raises:
            CircuitBreakerOpen: 熔断器打开时拒绝调用
        """
        # 检查状态
        if self.state == CircuitState.OPEN:
            if self._should_try_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                logger.warning(f"Circuit {self.name} is OPEN, rejecting call")
                raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                logger.warning(f"Circuit {self.name} HALF_OPEN max calls reached")
                raise CircuitBreakerOpen(f"Circuit {self.name} HALF_OPEN max calls")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if self.state == CircuitState.OPEN:
                raise
            raise e

    def _should_try_reset(self) -> bool:
        """是否应该尝试恢复"""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) > self.recovery_timeout

    def _on_success(self):
        """成功处理"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1
            if self.success_count >= self.half_open_max_calls:
                logger.info(f"Circuit {self.name} reset to CLOSED")
                self._reset()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self):
        """失败处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.half_open_calls += 1

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit {self.name} HALF_OPEN -> OPEN")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit {self.name} CLOSED -> OPEN (failures={self.failure_count})")
            self.state = CircuitState.OPEN

    def _reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self.state

    def reset(self):
        """手动重置"""
        self._reset()
        logger.info(f"Circuit {self.name} manually reset")


class MultiCircuitBreaker:
    """多熔断器管理"""

    def __init__(self):
        self.circuits: dict[str, CircuitBreaker] = {}

    def get_circuit(self, name: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self.circuits:
            self.circuits[name] = CircuitBreaker(name=name)
        return self.circuits[name]

    async def call(
        self,
        circuit_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """使用指定熔断器执行"""
        circuit = self.get_circuit(circuit_name)
        return await circuit.call(func, *args, **kwargs)

    def get_all_states(self) -> dict[str, CircuitState]:
        """获取所有熔断器状态"""
        return {name: cb.get_state() for name, cb in self.circuits.items()}

    def reset_all(self):
        """重置所有熔断器"""
        for cb in self.circuits.values():
            cb.reset()