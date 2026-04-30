"""
配置管理 - YAML配置和配置验证

提供:
1. YAML配置加载
2. 环境变量覆盖
3. 配置验证
4. 配置合并
"""
import os
import yaml
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


from typing import Optional

# 导入统一的 LLMConfig (避免重复定义)
# 实际定义在 base_agent.py
# 此处重新导出以保持向后兼容
try:
    from ..base_agent import LLMConfig as BaseLLMConfig

    @dataclass
    class LLMConfig(BaseLLMConfig):
        """LLM配置 - 统一使用 base_agent.py 中的定义"""
        pass

except ImportError:
    # 如果 base_agent 导入失败，使用备用定义
    @dataclass
    class LLMConfig:
        """LLM配置"""
        provider: str = "openai"
        model_name: str = "minimax"
        temperature: float = 0.7
        max_tokens: int = 4096
        api_key: Optional[str] = None
        base_url: Optional[str] = None


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    ttl: int = 3600
    max_entries: int = 1000


@dataclass
class RateLimitConfig:
    """限流配置"""
    enabled: bool = True
    max_requests: int = 100
    window_seconds: int = 60


@dataclass
class SecurityConfig:
    """安全配置"""
    sanitize_input: bool = True
    allow_html: bool = False
    max_input_length: int = 10000


@dataclass
class AgentConfig:
    """Agent配置"""
    max_concurrent: int = 10
    timeout: int = 300
    retry_attempts: int = 3


@dataclass
class AppConfig:
    """应用配置"""
    log_level: str = "INFO"
    llm: LLMConfig = field(default_factory=LLMConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)


class ConfigLoader:
    """
    配置加载器

    使用方式:
        loader = ConfigLoader()
        config = loader.load("config.yaml")
    """

    DEFAULT_CONFIG = {
        "log_level": "INFO",
        "llm": {
            "provider": "openai",
            "model_name": "minimax",
            "temperature": 0.7,
            "max_tokens": 4096
        },
        "cache": {
            "enabled": True,
            "ttl": 3600,
            "max_entries": 1000
        },
        "rate_limit": {
            "enabled": True,
            "max_requests": 100,
            "window_seconds": 60
        },
        "security": {
            "sanitize_input": True,
            "allow_html": False,
            "max_input_length": 10000
        },
        "agent": {
            "max_concurrent": 10,
            "timeout": 300,
            "retry_attempts": 3
        }
    }

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.cwd()

    def load(self, config_file: str = "config.yaml") -> AppConfig:
        """
        加载配置

        优先级：环境变量 > config.yaml > 默认值
        """
        config_path = self.config_dir / config_file

        # 1. 加载默认配置
        config_data = self.DEFAULT_CONFIG.copy()

        # 2. 加载YAML文件（如果存在）
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        config_data = self._merge_config(config_data, yaml_config)
                        logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

        # 3. 环境变量覆盖
        config_data = self._apply_env_overrides(config_data)

        # 4. 构建配置对象
        return self._build_config(config_data)

    def _merge_config(self, base: Dict, override: Dict) -> Dict:
        """深度合并配置"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self, config: Dict) -> Dict:
        """应用环境变量覆盖"""
        # LLMs相关
        if os.environ.get("LLM_PROVIDER"):
            config["llm"]["provider"] = os.environ["LLM_PROVIDER"]
        if os.environ.get("LLM_MODEL"):
            config["llm"]["model_name"] = os.environ["LLM_MODEL"]
        if os.environ.get("LLM_TEMPERATURE"):
            config["llm"]["temperature"] = float(os.environ["LLM_TEMPERATURE"])
        if os.environ.get("LLM_MAX_TOKENS"):
            config["llm"]["max_tokens"] = int(os.environ["LLM_MAX_TOKENS"])

        # 缓存相关
        if os.environ.get("ENABLE_CACHE"):
            config["cache"]["enabled"] = os.environ["ENABLE_CACHE"].lower() == "true"
        if os.environ.get("CACHE_TTL"):
            config["cache"]["ttl"] = int(os.environ["CACHE_TTL"])

        # 日志相关
        if os.environ.get("LOG_LEVEL"):
            config["log_level"] = os.environ["LOG_LEVEL"]

        # Agent相关
        if os.environ.get("MAX_CONCURRENT"):
            config["agent"]["max_concurrent"] = int(os.environ["MAX_CONCURRENT"])

        return config

    def _build_config(self, data: Dict) -> AppConfig:
        """构建配置对象"""
        return AppConfig(
            log_level=data.get("log_level", "INFO"),
            llm=LLMConfig(**data.get("llm", {})),
            cache=CacheConfig(**data.get("cache", {})),
            rate_limit=RateLimitConfig(**data.get("rate_limit", {})),
            security=SecurityConfig(**data.get("security", {})),
            agent=AgentConfig(**data.get("agent", {}))
        )

    def save(self, config: AppConfig, config_file: str = "config.yaml"):
        """保存配置到YAML文件"""
        config_path = self.config_dir / config_file

        config_data = {
            "log_level": config.log_level,
            "llm": {
                "provider": config.llm.provider,
                "model_name": config.llm.model_name,
                "temperature": config.llm.temperature,
                "max_tokens": config.llm.max_tokens,
                "api_key": config.llm.api_key,
                "base_url": config.llm.base_url
            },
            "cache": {
                "enabled": config.cache.enabled,
                "ttl": config.cache.ttl,
                "max_entries": config.cache.max_entries
            },
            "rate_limit": {
                "enabled": config.rate_limit.enabled,
                "max_requests": config.rate_limit.max_requests,
                "window_seconds": config.rate_limit.window_seconds
            },
            "security": {
                "sanitize_input": config.security.sanitize_input,
                "allow_html": config.security.allow_html,
                "max_input_length": config.security.max_input_length
            },
            "agent": {
                "max_concurrent": config.agent.max_concurrent,
                "timeout": config.agent.timeout,
                "retry_attempts": config.agent.retry_attempts
            }
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"Saved config to {config_path}")


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate(config: AppConfig) -> list:
        """
        验证配置

        Returns:
            错误列表，空表示验证通过
        """
        errors = []

        # LLM验证
        if config.llm.temperature < 0 or config.llm.temperature > 2:
            errors.append("LLM temperature must be between 0 and 2")
        if config.llm.max_tokens < 100:
            errors.append("LLM max_tokens must be at least 100")

        # 缓存验证
        if config.cache.ttl < 0:
            errors.append("Cache TTL must be positive")
        if config.cache.max_entries < 1:
            errors.append("Cache max_entries must be at least 1")

        # Agent验证
        if config.agent.max_concurrent < 1:
            errors.append("Agent max_concurrent must be at least 1")
        if config.agent.timeout < 1:
            errors.append("Agent timeout must be at least 1 second")
        if config.agent.retry_attempts < 0:
            errors.append("Agent retry_attempts must be non-negative")

        return errors
