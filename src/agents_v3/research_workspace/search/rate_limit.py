"""每源限流管理"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class SourceConfig:
    min_interval: float = 1.0  # 秒
    max_retries: int = 3
    backoff_factor: float = 2.0


# 默认配置
_DEFAULT_CONFIGS: dict[str, SourceConfig] = {
    "arxiv": SourceConfig(min_interval=3.0, max_retries=3),
    "openalex": SourceConfig(min_interval=0.5, max_retries=3),
    "semantic_scholar": SourceConfig(min_interval=0.2, max_retries=3),
    "pubmed": SourceConfig(min_interval=0.34, max_retries=3),
}


@dataclass
class _SourceState:
    last_request_time: float = 0.0
    consecutive_errors: int = 0
    backoff_until: float = 0.0


class RateManager:
    """每源限流管理器"""

    def __init__(self, configs: dict[str, SourceConfig] | None = None):
        self.configs = configs or _DEFAULT_CONFIGS
        self._states: dict[str, _SourceState] = {}

    def _get_state(self, source: str) -> _SourceState:
        if source not in self._states:
            self._states[source] = _SourceState()
        return self._states[source]

    def _get_config(self, source: str) -> SourceConfig:
        return self.configs.get(source, SourceConfig())

    def acquire(self, source: str) -> None:
        """等待直到可以发送请求"""
        config = self._get_config(source)
        state = self._get_state(source)

        # Check backoff
        now = time.time()
        if state.backoff_until > now:
            wait = state.backoff_until - now
            logger.debug(f"Rate limit backoff for {source}: waiting {wait:.1f}s")
            time.sleep(wait)

        # Enforce min interval
        elapsed = time.time() - state.last_request_time
        if elapsed < config.min_interval:
            sleep_time = config.min_interval - elapsed
            time.sleep(sleep_time)

        state.last_request_time = time.time()

    def record_success(self, source: str) -> None:
        """记录成功请求，重置退避"""
        state = self._get_state(source)
        state.consecutive_errors = 0
        state.backoff_until = 0.0

    def record_error(self, source: str, retry_after: float | None = None) -> None:
        """记录失败请求，触发退避"""
        config = self._get_config(source)
        state = self._get_state(source)
        state.consecutive_errors += 1

        if retry_after:
            state.backoff_until = time.time() + retry_after
        elif state.consecutive_errors >= config.max_retries:
            # Exponential backoff
            backoff = config.min_interval * (config.backoff_factor ** state.consecutive_errors)
            state.backoff_until = time.time() + min(backoff, 300)  # Max 5 min
            logger.warning(f"Source {source} backoff: {backoff:.1f}s after {state.consecutive_errors} errors")

    def is_available(self, source: str) -> bool:
        """检查源是否可用（未被熔断）"""
        state = self._get_state(source)
        return time.time() >= state.backoff_until

    def get_stats(self) -> dict[str, dict]:
        """获取各源状态"""
        stats = {}
        for source, state in self._states.items():
            config = self._get_config(source)
            stats[source] = {
                "consecutive_errors": state.consecutive_errors,
                "backoff_remaining": max(0, state.backoff_until - time.time()),
                "available": self.is_available(source),
                "min_interval": config.min_interval,
            }
        return stats
