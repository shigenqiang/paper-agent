"""
Rate Manager - 智能频率限制管理器

管理多平台API的请求频率，避免触发限制。
"""

from src.agents_v2.logging_config import get_logging_logger

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from collections import deque

logger = get_logging_logger(__name__)


@dataclass
class PlatformConfig:
    """平台频率配置"""
    name: str
    min_interval: float = 1.0        # 最小请求间隔(秒)
    max_requests_per_second: float = 1.0  # 最大每秒请求数
    max_requests_per_hour: int = 3600    # 每小时最大请求数
    max_requests_per_day: int = 100000    # 每日最大请求数
    backoff_multiplier: float = 2.0      # 退避倍数
    max_backoff: float = 60.0            # 最大退避时间(秒)
    use_api_key: bool = False
    api_key_env_var: str = ""             # API Key环境变量名


class RateManager:
    """智能频率管理器 - 单例模式"""

    _instance: Optional['RateManager'] = None

    # 平台默认配置
    DEFAULT_CONFIGS: Dict[str, PlatformConfig] = {
        "openalex": PlatformConfig(
            name="openalex",
            min_interval=0.5,
            max_requests_per_second=2,
            max_requests_per_hour=7200,
        ),
        "arxiv": PlatformConfig(
            name="arxiv",
            min_interval=3.0,
            max_requests_per_hour=1000,  # 官方限制
            max_requests_per_day=10000,
        ),
        "semantic_scholar": PlatformConfig(
            name="semantic_scholar",
            min_interval=0.2,
            max_requests_per_second=5,
            use_api_key=True,
            api_key_env_var="SEMANTIC_SCHOLAR_API_KEY",
        ),
        "pubmed": PlatformConfig(
            name="pubmed",
            min_interval=0.33,
            max_requests_per_second=3,
            max_requests_per_hour=10000,
            use_api_key=True,
            api_key_env_var="NCBI_API_KEY",
        ),
        "crossref": PlatformConfig(
            name="crossref",
            min_interval=0.02,
            max_requests_per_second=50,
        ),
        "biorxiv": PlatformConfig(
            name="biorxiv",
            min_interval=1.0,
            max_requests_per_second=1,
        ),
        "base": PlatformConfig(
            name="base",
            min_interval=1.0,
            max_requests_per_second=2,
        ),
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._last_request_time: Dict[str, float] = {}
        self._request_counts_hour: Dict[str, deque] = {}
        self._request_counts_day: Dict[str, deque] = {}
        self._backoff_until: Dict[str, float] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._initialized = True

    def _get_lock(self, platform: str) -> asyncio.Lock:
        """获取平台锁"""
        if platform not in self._locks:
            self._locks[platform] = asyncio.Lock()
        return self._locks[platform]

    def get_config(self, platform: str, **overrides) -> PlatformConfig:
        """获取平台配置，支持覆盖"""
        config = self.DEFAULT_CONFIGS.get(platform)
        if not config:
            config = PlatformConfig(name=platform)
        if overrides:
            config = PlatformConfig(
                name=config.name,
                **{**config.__dict__, **overrides}
            )
        return config

    async def acquire(self, platform: str, config: Optional[PlatformConfig] = None):
        """获取请求许可，必要时等待"""
        config = config or self.get_config(platform)
        lock = self._get_lock(platform)

        async with lock:
            # 检查是否在退避期
            if platform in self._backoff_until:
                backoff_end = self._backoff_until[platform]
                if time.time() < backoff_end:
                    wait_time = backoff_end - time.time()
                    logger.debug(f"{platform} in backoff, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            # 检查最小间隔
            if platform in self._last_request_time:
                elapsed = time.time() - self._last_request_time[platform]
                if elapsed < config.min_interval:
                    wait_time = config.min_interval - elapsed
                    await asyncio.sleep(wait_time)

            # 检查小时配额
            self._clean_old_counts(platform, window=3600)
            if config.max_requests_per_hour:
                hour_counts = self._request_counts_hour.setdefault(platform, deque())
                if len(hour_counts) >= config.max_requests_per_hour:
                    oldest = hour_counts[0]
                    wait_time = 3600 - (time.time() - oldest)
                    if wait_time > 0:
                        logger.warning(f"{platform} hourly limit reached, waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)

            # 检查每日配额
            self._clean_old_counts(platform, window=86400, key="day")
            if config.max_requests_per_day:
                day_counts = self._request_counts_day.setdefault(platform, deque())
                if len(day_counts) >= config.max_requests_per_day:
                    oldest = day_counts[0]
                    wait_time = 86400 - (time.time() - oldest)
                    if wait_time > 0:
                        logger.warning(f"{platform} daily limit reached, waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)

            # 记录请求时间
            self._last_request_time[platform] = time.time()

            hour_counts = self._request_counts_hour.setdefault(platform, deque())
            hour_counts.append(time.time())

            day_counts = self._request_counts_day.setdefault(platform, deque())
            day_counts.append(time.time())

    def record_error(self, platform: str, config: Optional[PlatformConfig] = None):
        """记录错误，触发退避"""
        config = config or self.get_config(platform)

        current_backoff = self._backoff_until.get(platform, 0) - time.time()
        if current_backoff > 0:
            # 已经在退避中，增加退避时间
            backoff_time = min(
                config.max_backoff,
                current_backoff * config.backoff_multiplier
            )
        else:
            # 新错误，使用基础退避时间
            backoff_time = config.min_interval * config.backoff_multiplier

        self._backoff_until[platform] = time.time() + backoff_time
        logger.warning(f"{platform} error recorded, backoff for {backoff_time:.2f}s")

    def record_rate_limit(self, platform: str, config: Optional[PlatformConfig] = None):
        """记录限流错误，触发较长退避"""
        config = config or self.get_config(platform)
        # 限流错误使用更长的退避
        backoff_time = min(30, config.max_backoff / 2)
        self._backoff_until[platform] = time.time() + backoff_time
        logger.warning(f"{platform} rate limit hit, backoff for {backoff_time:.2f}s")

    def clear_backoff(self, platform: str):
        """清除退避状态"""
        if platform in self._backoff_until:
            del self._backoff_until[platform]

    def _clean_old_counts(self, platform: str, window: int, key: str = "hour"):
        """清理过期计数"""
        current = time.time()
        if key == "hour":
            counts = self._request_counts_hour.get(platform, deque())
        else:
            counts = self._request_counts_day.get(platform, deque())

        while counts and current - counts[0] > window:
            counts.popleft()

    def get_stats(self, platform: str) -> Dict:
        """获取平台统计信息"""
        self._clean_old_counts(platform, 3600)
        self._clean_old_counts(platform, 86400, key="day")

        hour_counts = self._request_counts_hour.get(platform, deque())
        day_counts = self._request_counts_day.get(platform, deque())

        return {
            "platform": platform,
            "requests_last_hour": len(hour_counts),
            "requests_last_day": len(day_counts),
            "in_backoff": platform in self._backoff_until and time.time() < self._backoff_until[platform],
            "backoff_remaining": max(0, self._backoff_until.get(platform, 0) - time.time()) if platform in self._backoff_until else 0,
            "last_request": self._last_request_time.get(platform),
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有平台统计"""
        return {name: self.get_stats(name) for name in self.DEFAULT_CONFIGS.keys()}

    def reset(self, platform: Optional[str] = None):
        """重置统计"""
        if platform:
            self._request_counts_hour.pop(platform, None)
            self._request_counts_day.pop(platform, None)
            self._backoff_until.pop(platform, None)
            self._last_request_time.pop(platform, None)
        else:
            self._request_counts_hour.clear()
            self._request_counts_day.clear()
            self._backoff_until.clear()
            self._last_request_time.clear()


# 全局单例
_rate_manager: Optional[RateManager] = None


def get_rate_manager() -> RateManager:
    """获取全局RateManager实例"""
    global _rate_manager
    if _rate_manager is None:
        _rate_manager = RateManager()
    return _rate_manager