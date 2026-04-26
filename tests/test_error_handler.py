"""
单元测试 - error_handler模块
"""
import pytest
import json
from src.agents_v2.unified.error_handler import (
    ErrorSeverity,
    ErrorType,
    ErrorClassifier,
    log_error_with_context,
    FallbackHandler,
    RetryPolicy,
    RecoveryStrategy
)


class TestErrorClassifier:
    """测试错误分类器"""

    def test_classify_llm_error(self):
        """测试LLM错误分类"""
        error = Exception("OpenAI API timeout")
        error_type = ErrorClassifier.classify(error)
        assert error_type == ErrorType.LLM_FAILURE

    def test_classify_json_error(self):
        """测试JSON解析错误分类"""
        error = Exception("JSON decode error")
        error_type = ErrorClassifier.classify(error)
        assert error_type == ErrorType.PARSING_FAILURE

    def test_classify_external_api_error(self):
        """测试外部API错误分类"""
        error = Exception("arXiv HTTP 500")
        error_type = ErrorClassifier.classify(error)
        assert error_type == ErrorType.EXTERNAL_API_FAILURE

    def test_classify_validation_error(self):
        """测试验证错误分类"""
        error = Exception("validation failed")
        error_type = ErrorClassifier.classify(error)
        assert error_type == ErrorType.VALIDATION_FAILURE

    def test_classify_unknown_error(self):
        """测试未知错误分类"""
        error = Exception("some random error")
        error_type = ErrorClassifier.classify(error)
        assert error_type == ErrorType.SYSTEM_ERROR


class TestFallbackHandler:
    """测试降级处理器"""

    def test_get_fallback_for_topic(self):
        """测试topic阶段降级"""
        handler = FallbackHandler()
        fallback = handler.get_fallback("topic", {})
        assert "selected_topic" in fallback
        assert fallback["selected_topic"]["title"] == "待定研究主题"

    def test_get_fallback_for_literature(self):
        """测试literature阶段降级"""
        handler = FallbackHandler()
        fallback = handler.get_fallback("literature", {})
        assert "papers" in fallback
        assert fallback["papers"] == []

    def test_cache_and_get(self):
        """测试缓存功能"""
        handler = FallbackHandler()
        handler.cache_result("topic", {"cached": True})
        cached = handler.get_cached("topic")
        assert cached["cached"] is True

    def test_clear_cache(self):
        """测试清空缓存"""
        handler = FallbackHandler()
        handler.cache_result("topic", {"data": True})
        handler.clear_cache()
        assert handler.get_cached("topic") is None


class TestRetryPolicy:
    """测试重试策略"""

    def test_should_not_retry_after_max(self):
        """测试超过最大重试次数不应再重试"""
        policy = RetryPolicy(max_retries=3)
        error = Exception("test")
        should_retry = RecoveryStrategy.should_retry(error, policy, 3)
        assert should_retry is False

    def test_should_retry_before_max(self):
        """测试未超过最大重试次数应重试"""
        policy = RetryPolicy(max_retries=3)
        error = Exception("test")
        should_retry = RecoveryStrategy.should_retry(error, policy, 2)
        assert should_retry is True

    def test_exponential_delay(self):
        """测试指数退避延迟"""
        policy = RetryPolicy(initial_delay=1.0, exponential_base=2.0, max_delay=60.0)
        delay = RecoveryStrategy.get_delay(policy, 0)
        assert delay == 1.0
        delay = RecoveryStrategy.get_delay(policy, 1)
        assert delay == 2.0
        delay = RecoveryStrategy.get_delay(policy, 2)
        assert delay == 4.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
