"""
配置管理 - YAML配置和配置验证

提供:
1. YAML配置加载
2. 环境变量覆盖
3. 配置验证
4. 配置合并
"""
import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

from .exceptions import ConfigurationError

# 使用新的日志系统
from src.agents_v2.logging_config import get_logging_logger
logger = get_logging_logger(__name__)

# yaml is optional - graceful fallback if not installed
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False
    logger.warning("pyyaml not installed, YAML config file support disabled")


from typing import Optional

# LLMConfig for configuration purposes (standalone dataclass, separate from base_agent.LLMConfig)
@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "openai"
    model_name: str = "minimax"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 120


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


# ============ 支持的LLM模型注册表 ============

SUPPORTED_MODELS = [
    # --- MiniMax 系列 ---
    {
        "id": "minimax-m2",
        "name": "MiniMax-M2",
        "provider": "openai",
        "model_name": "MiniMax-M2",
        "base_url": "https://api.minimax.chat/v1",
        "description": "MiniMax最新大模型，支持中文，适合学术写作",
        "category": "minimax",
        "max_tokens": 8192,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "minimax-m2.7",
        "name": "MiniMax-M2.7",
        "provider": "openai",
        "model_name": "MiniMax-M2.7",
        "base_url": "https://api.minimax.chat/v1",
        "description": "MiniMax-M2增强版，推理能力更强",
        "category": "minimax",
        "max_tokens": 8192,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },

    # --- OpenAI 系列 ---
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "model_name": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "description": "OpenAI旗舰模型，综合能力最强",
        "category": "openai",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o mini",
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "description": "GPT-4o轻量版，速度快成本低",
        "category": "openai",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "model_name": "gpt-4-turbo",
        "base_url": "https://api.openai.com/v1",
        "description": "GPT-4增强版，更大上下文窗口",
        "category": "openai",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "base_url": "https://api.openai.com/v1",
        "description": "OpenAI快速模型，适合日常对话",
        "category": "openai",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "o3-mini",
        "name": "o3-mini",
        "provider": "openai",
        "model_name": "o3-mini",
        "base_url": "https://api.openai.com/v1",
        "description": "OpenAI推理模型，擅长逻辑分析",
        "category": "openai",
        "max_tokens": 4096,
        "default_temperature": 1.0,
        "supports_function_calling": False,
    },

    # --- Claude / Anthropic 系列 ---
    {
        "id": "claude-sonnet-4-6",
        "name": "Claude Sonnet 4",
        "provider": "anthropic",
        "model_name": "claude-sonnet-4-6",
        "base_url": "https://api.anthropic.com/v1",
        "description": "Anthropic Sonnet模型，平衡性能与成本",
        "category": "anthropic",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "claude-opus-4-7",
        "name": "Claude Opus 4",
        "provider": "anthropic",
        "model_name": "claude-opus-4-7",
        "base_url": "https://api.anthropic.com/v1",
        "description": "Anthropic最强模型，适合复杂推理",
        "category": "anthropic",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "claude-haiku-4-5",
        "name": "Claude Haiku 4",
        "provider": "anthropic",
        "model_name": "claude-haiku-4-5-20251001",
        "base_url": "https://api.anthropic.com/v1",
        "description": "Anthropic快速模型，响应速度快",
        "category": "anthropic",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },

    # --- 通义千问 (Qwen) 系列 ---
    {
        "id": "qwen-max",
        "name": "Qwen-Max",
        "provider": "openai",
        "model_name": "qwen-max",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "description": "通义千问最强模型，中文理解优秀",
        "category": "qwen",
        "max_tokens": 8192,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "qwen-plus",
        "name": "Qwen-Plus",
        "provider": "openai",
        "model_name": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "description": "通义千问平衡版，性价比高",
        "category": "qwen",
        "max_tokens": 8192,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "qwen-turbo",
        "name": "Qwen-Turbo",
        "provider": "openai",
        "model_name": "qwen-turbo",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "description": "通义千问快速版，适合高频调用",
        "category": "qwen",
        "max_tokens": 8192,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },

    # --- DeepSeek 系列 ---
    {
        "id": "deepseek-chat",
        "name": "DeepSeek-V3",
        "provider": "openai",
        "model_name": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "description": "DeepSeek最新模型，中英文表现优异",
        "category": "deepseek",
        "max_tokens": 8192,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek-R1",
        "provider": "openai",
        "model_name": "deepseek-reasoner",
        "base_url": "https://api.deepseek.com/v1",
        "description": "DeepSeek推理模型，深度思考能力强",
        "category": "deepseek",
        "max_tokens": 8192,
        "default_temperature": 0.6,
        "supports_function_calling": False,
    },

    # --- 智谱 (GLM) 系列 ---
    {
        "id": "glm-4",
        "name": "GLM-4",
        "provider": "openai",
        "model_name": "glm-4",
        "base_url": "https://open.bigmodel.cn/api/pas/v4",
        "description": "智谱最新大模型，中文能力强",
        "category": "glm",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
    {
        "id": "glm-4-plus",
        "name": "GLM-4-Plus",
        "provider": "openai",
        "model_name": "glm-4-plus",
        "base_url": "https://open.bigmodel.cn/api/pas/v4",
        "description": "GLM-4增强版，推理能力更佳",
        "category": "glm",
        "max_tokens": 4096,
        "default_temperature": 0.7,
        "supports_function_calling": True,
    },
]

# 模型分类标签
MODEL_CATEGORIES = {
    "minimax": "MiniMax",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "qwen": "通义千问",
    "deepseek": "DeepSeek",
    "glm": "智谱",
}


def get_model_by_id(model_id: str) -> Optional[Dict[str, Any]]:
    """根据ID获取模型配置"""
    for model in SUPPORTED_MODELS:
        if model["id"] == model_id:
            return model
    return None


def get_models_by_category(category: str) -> List[Dict[str, Any]]:
    """获取指定分类的所有模型"""
    return [m for m in SUPPORTED_MODELS if m["category"] == category]


def get_all_models() -> List[Dict[str, Any]]:
    """获取所有支持的模型列表"""
    return SUPPORTED_MODELS.copy()


def get_default_model() -> Dict[str, Any]:
    """获取默认模型（MiniMax-M2.7）"""
    return get_model_by_id("minimax-m2.7") or SUPPORTED_MODELS[0]


# ============ 配置加载器 ============

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
        if config_path.exists() and _HAS_YAML:
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        config_data = self._merge_config(config_data, yaml_config)
                        logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        elif config_path.exists() and not _HAS_YAML:
            logger.warning(f"config.yaml exists but pyyaml not installed, using defaults")

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
        if not _HAS_YAML:
            logger.warning("Cannot save config: pyyaml not installed")
            return

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
