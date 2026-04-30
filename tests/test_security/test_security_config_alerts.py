"""
单元测试 - 安全、配置、告警模块
"""
import pytest


class TestInputSanitizer:
    """测试输入清理器"""

    def test_basic_sanitization(self):
        """测试基础清理"""
        from src.agents_v2.core.security import InputSanitizer

        sanitizer = InputSanitizer()

        # HTML转义
        assert sanitizer.sanitize("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

    def test_dangerous_pattern_removal(self):
        """测试危险模式移除"""
        from src.agents_v2.core.security import InputSanitizer

        sanitizer = InputSanitizer()

        # javascript:协议
        assert sanitizer.sanitize("javascript:alert('xss')") == "alert(&#x27;xss&#x27;)"
        # vbscript:协议
        assert sanitizer.sanitize("vbscript:msgbox('xss')") == "msgbox(&#x27;xss&#x27;)"

    def test_null_byte_removal(self):
        """测试空字节移除"""
        from src.agents_v2.core.security import InputSanitizer

        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("test\x00value")
        assert "\x00" not in result
        assert "testvalue" in result

    def test_whitespace_normalization(self):
        """测试空白符规范化"""
        from src.agents_v2.core.security import InputSanitizer

        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("test    \n\nvalue")
        assert "test" in result
        assert "value" in result

    def test_sanitize_dict(self):
        """测试字典清理"""
        from src.agents_v2.core.security import InputSanitizer

        sanitizer = InputSanitizer()
        data = {"name": "<script>", "age": 25}
        result = sanitizer.sanitize_dict(data)

        assert result["name"] == "&lt;script&gt;"
        assert result["age"] == 25


class TestSecretManager:
    """测试密钥管理器"""

    def test_set_and_get(self):
        """测试设置和获取"""
        from src.agents_v2.core.security import SecretManager

        secrets = SecretManager()
        secrets.set("TEST_KEY", "test_value")

        # 默认从内存获取
        assert secrets.get("TEST_KEY") == "test_value"

    def test_get_or_raise(self):
        """测试获取或抛出"""
        from src.agents_v2.core.security import SecretManager
        from src.agents_v2.core.exceptions import ConfigurationError

        secrets = SecretManager()

        with pytest.raises(ConfigurationError):
            secrets.get_or_raise("NONEXISTENT_KEY")


class TestSecurityConfig:
    """测试安全配置"""

    def test_default_config(self):
        """测试默认配置"""
        from src.agents_v2.core.security import SecurityConfig

        config = SecurityConfig()
        assert config.sanitize_input is True
        assert config.allow_html is False
        assert config.max_input_length == 10000


class TestRateLimiter:
    """测试限流器"""

    def test_rate_limiter_init(self):
        """测试限流器初始化"""
        from src.agents_v2.monitoring.alerts import RateLimiter

        limiter = RateLimiter(max_requests=10, window=60)
        assert limiter.max_requests == 10
        assert limiter.window == 60

    def test_is_allowed(self):
        """测试请求允许"""
        from src.agents_v2.monitoring.alerts import RateLimiter

        limiter = RateLimiter(max_requests=3, window=60)

        # 前3个请求应该被允许
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True

        # 第4个请求应该被拒绝
        assert limiter.is_allowed("user1") is False

    def test_get_remaining(self):
        """测试剩余请求数"""
        from src.agents_v2.monitoring.alerts import RateLimiter

        limiter = RateLimiter(max_requests=5, window=60)

        limiter.is_allowed("user1")
        limiter.is_allowed("user1")

        assert limiter.get_remaining("user1") == 3

    def test_reset(self):
        """测试重置"""
        from src.agents_v2.monitoring.alerts import RateLimiter

        limiter = RateLimiter(max_requests=2, window=60)

        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False

        limiter.reset("user1")
        assert limiter.is_allowed("user1") is True


class TestAlertManager:
    """测试告警管理器"""

    def test_trigger(self):
        """测试触发告警"""
        from src.agents_v2.monitoring.alerts import AlertManager, AlertType, AlertSeverity

        manager = AlertManager()

        alert = manager.trigger(
            AlertType.ERROR_RATE,
            AlertSeverity.WARNING,
            "Error rate exceeded"
        )

        assert alert.alert_type == AlertType.ERROR_RATE
        assert alert.severity == AlertSeverity.WARNING

    def test_record_metric(self):
        """测试记录指标"""
        from src.agents_v2.monitoring.alerts import AlertManager

        manager = AlertManager()
        manager.record_metric("errors", 1.0)
        manager.record_metric("errors", 2.0)

        stats = manager.get_stats()
        assert "errors" in stats["metrics"]


class TestAlertSeverity:
    """测试告警级别"""

    def test_alert_severity_values(self):
        """测试告警级别枚举值"""
        from src.agents_v2.monitoring.alerts import AlertSeverity

        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertType:
    """测试告警类型"""

    def test_alert_type_values(self):
        """测试告警类型枚举值"""
        from src.agents_v2.monitoring.alerts import AlertType

        assert AlertType.ERROR_RATE.value == "error_rate"
        assert AlertType.LATENCY_HIGH.value == "latency_high"
        assert AlertType.RATE_LIMIT.value == "rate_limit"


class TestHealthChecker:
    """测试健康检查器"""

    def test_register_check(self):
        """测试注册检查"""
        from src.agents_v2.monitoring.alerts import HealthChecker

        checker = HealthChecker()
        checker.register_check("test", lambda: True)

        assert "test" in checker._checks

    def test_check(self):
        """测试执行检查"""
        from src.agents_v2.monitoring.alerts import HealthChecker

        checker = HealthChecker()
        checker.register_check("healthy", lambda: True)
        checker.register_check("unhealthy", lambda: False)

        result = checker.check()

        assert result["healthy"] is False  # 因为有unhealthy
        assert "unhealthy" in result["unhealthy"]


class TestConfigLoader:
    """测试配置加载器"""

    def test_default_config(self):
        """测试默认配置"""
        from src.agents_v2.core.config import ConfigLoader

        loader = ConfigLoader()
        config = loader.load("nonexistent.yaml")  # 使用默认配置

        assert config.log_level == "INFO"
        assert config.llm.provider == "openai"
        assert config.cache.enabled is True

    def test_build_config(self):
        """测试构建配置"""
        from src.agents_v2.core.config import AppConfig, LLMConfig, CacheConfig

        config = AppConfig(
            log_level="DEBUG",
            llm=LLMConfig(provider="anthropic"),
            cache=CacheConfig(ttl=7200)
        )

        assert config.log_level == "DEBUG"
        assert config.llm.provider == "anthropic"
        assert config.cache.ttl == 7200


class TestConfigValidator:
    """测试配置验证器"""

    def test_validate_valid_config(self):
        """测试验证有效配置"""
        from src.agents_v2.core.config import ConfigLoader, ConfigValidator

        loader = ConfigLoader()
        config = loader.load("nonexistent.yaml")

        validator = ConfigValidator()
        errors = validator.validate(config)

        assert len(errors) == 0

    def test_validate_invalid_temperature(self):
        """测试验证无效温度"""
        from src.agents_v2.core.config import AppConfig, LLMConfig, ConfigValidator

        config = AppConfig(llm=LLMConfig(temperature=5.0))

        validator = ConfigValidator()
        errors = validator.validate(config)

        assert len(errors) > 0
        assert any("temperature" in e for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
