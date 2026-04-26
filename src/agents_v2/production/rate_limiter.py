"""
限流器 - Rate Limiter

实现多种限流算法:
- 固定窗口
- 滑动窗口
- 令牌桶
- 漏桶
"""
import time
import logging
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


class LimiterStrategy(Enum):
    """限流策略"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class LimiterConfig:
    """限流器配置"""
    strategy: LimiterStrategy = LimiterStrategy.TOKEN_BUCKET
    rate: float = 100.0           # 每秒请求数
    burst: float = 200.0          # 突发容量
    refill_rate: float = 50.0    # 每秒补充令牌数


class FixedWindowLimiter:
    """固定窗口限流器"""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.window_start = time.time()
        self.count = 0

    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        now = time.time()

        if now - self.window_start >= self.window_seconds:
            self.window_start = now
            self.count = 0

        if self.count < self.max_requests:
            self.count += 1
            return True
        return False

    def reset(self):
        """重置"""
        self.window_start = time.time()
        self.count = 0


class SlidingWindowLimiter:
    """滑动窗口限流器"""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        now = time.time()
        cutoff = now - self.window_seconds

        # 清理过期的请求
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

    def get_current_count(self) -> int:
        """获取当前窗口内的请求数"""
        now = time.time()
        cutoff = now - self.window_seconds

        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

        return len(self.requests)


class TokenBucketLimiter:
    """令牌桶限流器"""

    def __init__(self, rate: float, burst: float):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.time()

    def is_allowed(self, tokens_needed: float = 1.0) -> bool:
        """检查是否允许请求"""
        self._refill()

        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True
        return False

    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill

        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def get_available_tokens(self) -> float:
        """获取可用令牌数"""
        self._refill()
        return self.tokens


class LeakyBucketLimiter:
    """漏桶限流器"""

    def __init__(self, rate: float, capacity: float):
        self.rate = rate  # 每秒处理请求数
        self.capacity = capacity
        self.water = 0.0  # 当前水量
        self.last_leak = time.time()

    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        self._leak()

        if self.water < self.capacity:
            self.water += 1
            return True
        return False

    def _leak(self):
        """漏水"""
        now = time.time()
        elapsed = now - self.last_leak

        leaked = elapsed * self.rate
        self.water = max(0, self.water - leaked)
        self.last_leak = now

    def get_current_water(self) -> float:
        """获取当前水量"""
        self._leak()
        return self.water


class RateLimiter:
    """统一限流器

    支持多种限流策略。
    """

    def __init__(self, config: LimiterConfig):
        """初始化限流器

        Args:
            config: 限流配置
        """
        self.config = config

        strategy = config.strategy

        if strategy == LimiterStrategy.FIXED_WINDOW:
            self._limiter = FixedWindowLimiter(
                max_requests=int(config.rate * config.burst / config.refill_rate),
                window_seconds=1.0
            )
        elif strategy == LimiterStrategy.SLIDING_WINDOW:
            self._limiter = SlidingWindowLimiter(
                max_requests=int(config.rate),
                window_seconds=1.0
            )
        elif strategy == LimiterStrategy.TOKEN_BUCKET:
            self._limiter = TokenBucketLimiter(
                rate=config.refill_rate,
                burst=config.burst
            )
        elif strategy == LimiterStrategy.LEAKY_BUCKET:
            self._limiter = LeakyBucketLimiter(
                rate=config.rate,
                capacity=config.burst
            )
        else:
            self._limiter = TokenBucketLimiter(
                rate=config.refill_rate,
                burst=config.burst
            )

    def is_allowed(self, tokens_needed: float = 1.0) -> bool:
        """检查是否允许请求

        Args:
            tokens_needed: 需要的令牌数

        Returns:
            bool: 是否允许
        """
        if isinstance(self._limiter, TokenBucketLimiter):
            return self._limiter.is_allowed(tokens_needed)
        elif isinstance(self._limiter, LeakyBucketLimiter):
            return self._limiter.is_allowed()
        else:
            return self._limiter.is_allowed()

    def reset(self):
        """重置限流器"""
        self._limiter.reset() if hasattr(self._limiter, 'reset') else None

    def get_stats(self) -> Dict:
        """获取限流器统计"""
        stats = {"strategy": self.config.strategy.value}

        if isinstance(self._limiter, TokenBucketLimiter):
            stats["available_tokens"] = self._limiter.get_available_tokens()
        elif isinstance(self._limiter, LeakyBucketLimiter):
            stats["current_water"] = self._limiter.get_current_water()
        elif isinstance(self._limiter, SlidingWindowLimiter):
            stats["current_count"] = self._limiter.get_current_count()

        return stats


class MultiLimiter:
    """多维度限流器"""

    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}

    def add_limiter(self, name: str, limiter: RateLimiter):
        """添加限流器

        Args:
            name: 限流器名称
            limiter: 限流器实例
        """
        self._limiters[name] = limiter

    def is_allowed(self, **dimensions) -> bool:
        """检查多维度限流

        Args:
            **dimensions: 维度名称和令牌数

        Returns:
            bool: 是否所有维度都允许
        """
        for name, tokens in dimensions.items():
            if name in self._limiters:
                if not self._limiters[name].is_allowed(tokens):
                    return False
        return True

    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有限流器统计"""
        return {name: limiter.get_stats() for name, limiter in self._limiters.items()}


# 便捷函数
def create_rate_limiter(
    strategy: str = "token_bucket",
    rate: float = 100.0,
    burst: float = 200.0
) -> RateLimiter:
    """创建限流器"""
    strategy_map = {
        "fixed_window": LimiterStrategy.FIXED_WINDOW,
        "sliding_window": LimiterStrategy.SLIDING_WINDOW,
        "token_bucket": LimiterStrategy.TOKEN_BUCKET,
        "leaky_bucket": LimiterStrategy.LEAKY_BUCKET
    }

    config = LimiterConfig(
        strategy=strategy_map.get(strategy, LimiterStrategy.TOKEN_BUCKET),
        rate=rate,
        burst=burst,
        refill_rate=rate / 2
    )

    return RateLimiter(config)