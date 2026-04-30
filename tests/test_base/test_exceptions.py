"""
单元测试 - 异常类
"""
import pytest


class TestExceptions:
    """测试自定义异常"""

    def test_agent_error(self):
        """测试AgentError"""
        from src.agents_v2.core.exceptions import AgentError

        with pytest.raises(AgentError):
            raise AgentError("Test error")

    def test_llm_error(self):
        """测试LLMError"""
        from src.agents_v2.core.exceptions import LLMError

        with pytest.raises(LLMError):
            raise LLMError("LLM failed")

    def test_validation_error(self):
        """测试ValidationError"""
        from src.agents_v2.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            raise ValidationError("Invalid input")

    def test_configuration_error(self):
        """测试ConfigurationError"""
        from src.agents_v2.core.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Missing config")

    def test_timeout_error(self):
        """测试TimeoutError"""
        from src.agents_v2.core.exceptions import TimeoutError

        with pytest.raises(TimeoutError):
            raise TimeoutError("Operation timed out")

    def test_external_api_error(self):
        """测试ExternalAPIError"""
        from src.agents_v2.core.exceptions import ExternalAPIError

        with pytest.raises(ExternalAPIError):
            raise ExternalAPIError("API unavailable")

    def test_cache_error(self):
        """测试CacheError"""
        from src.agents_v2.core.exceptions import CacheError

        with pytest.raises(CacheError):
            raise CacheError("Cache failure")

    def test_circuit_breaker_open_error(self):
        """测试CircuitBreakerOpenError"""
        from src.agents_v2.core.exceptions import CircuitBreakerOpenError

        with pytest.raises(CircuitBreakerOpenError):
            raise CircuitBreakerOpenError("Circuit is open")

    def test_agent_not_found_error(self):
        """测试AgentNotFoundError"""
        from src.agents_v2.core.exceptions import AgentNotFoundError

        with pytest.raises(AgentNotFoundError):
            raise AgentNotFoundError("Agent not found")

    def test_invalid_state_error(self):
        """测试InvalidStateError"""
        from src.agents_v2.core.exceptions import InvalidStateError

        with pytest.raises(InvalidStateError):
            raise InvalidStateError("Invalid state")

    def test_error_inheritance(self):
        """测试异常继承关系"""
        from src.agents_v2.core.exceptions import (
            AgentError, LLMError, ValidationError,
            ConfigurationError, TimeoutError, ExternalAPIError,
            CacheError, CircuitBreakerOpenError, AgentNotFoundError,
            InvalidStateError
        )

        # 所有自定义异常应该继承自AgentError
        assert issubclass(LLMError, AgentError)
        assert issubclass(ValidationError, AgentError)
        assert issubclass(ConfigurationError, AgentError)
        assert issubclass(TimeoutError, AgentError)
        assert issubclass(ExternalAPIError, AgentError)
        assert issubclass(CacheError, AgentError)
        assert issubclass(CircuitBreakerOpenError, AgentError)
        assert issubclass(AgentNotFoundError, AgentError)
        assert issubclass(InvalidStateError, AgentError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
