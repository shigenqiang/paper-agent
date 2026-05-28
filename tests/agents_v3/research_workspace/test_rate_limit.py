"""限流管理器测试"""

import time
import pytest

from src.agents_v3.research_workspace.search.rate_limit import RateManager, SourceConfig


class TestRateManager:
    def test_acquire_respects_min_interval(self):
        rm = RateManager({"test": SourceConfig(min_interval=0.1)})
        rm.acquire("test")
        start = time.time()
        rm.acquire("test")
        elapsed = time.time() - start
        assert elapsed >= 0.08  # Some tolerance

    def test_record_success_resets_backoff(self):
        rm = RateManager({"test": SourceConfig(min_interval=0.01)})
        rm.record_error("test")
        rm.record_success("test")
        state = rm._get_state("test")
        assert state.consecutive_errors == 0

    def test_record_error_triggers_backoff(self):
        rm = RateManager({"test": SourceConfig(min_interval=0.01, max_retries=1)})
        rm.record_error("test")
        rm.record_error("test")  # Exceeds max_retries
        assert rm.is_available("test") is False

    def test_is_available_default_true(self):
        rm = RateManager()
        assert rm.is_available("unknown_source") is True

    def test_get_stats(self):
        rm = RateManager({"test": SourceConfig(min_interval=0.5)})
        rm.acquire("test")
        stats = rm.get_stats()
        assert "test" in stats
        assert stats["test"]["min_interval"] == 0.5
