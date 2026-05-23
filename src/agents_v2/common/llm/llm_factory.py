"""
LLM工厂 - LLM Factory

统一管理LLM创建和配置，为三大系统（论文写作/QA问答/报告生成）提供统一的LLM接口。

功能：
1. 统一LLM配置管理
2. 支持多种Provider（OpenAI/Anthropic/MiniMax/DeepSeek/Qwen/GLM）
3. 模型注册表管理
4. 环境变量覆盖
5. 超时和重试配置
"""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)

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


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "openai"
    model_name: str = "minimax-m2.7"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 120
    max_retries: int = 3


@dataclass
class LLMFactoryConfig:
    """LLM工厂配置"""
    default_provider: str = "openai"
    default_model: str = "minimax-m2.7"
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    default_timeout: int = 120
    enable_cache: bool = True
    cache_ttl: int = 3600


class LLMFactory:
    """
    LLM工厂类

    统一创建和管理LLM实例，支持多种Provider。

    使用方式：
        factory = LLMFactory()
        llm = factory.create_llm(model_id="minimax-m2.7")
        # 或使用默认配置
        llm = factory.create_llm()
    """

    def __init__(self, config: Optional[LLMFactoryConfig] = None):
        self.config = config or LLMFactoryConfig()
        self._llm_cache: Dict[str, Any] = {}

    def get_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型配置"""
        for model in SUPPORTED_MODELS:
            if model["id"] == model_id:
                return model
        return None

    def get_default_config(self) -> LLMConfig:
        """获取默认LLM配置"""
        model_config = self.get_model_config(self.config.default_model)
        if model_config:
            return LLMConfig(
                provider=model_config["provider"],
                model_name=model_config["model_name"],
                temperature=self.config.default_temperature,
                max_tokens=model_config.get("max_tokens", self.config.default_max_tokens),
                base_url=model_config.get("base_url"),
                timeout=self.config.default_timeout,
            )
        return LLMConfig()

    def create_llm(
        self,
        model_id: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        use_cache: bool = True
    ) -> Any:
        """
        创建LLM实例

        Args:
            model_id: 模型ID（如"minimax-m2.7"）
            config: 直接传入LLMConfig配置（优先级高于model_id）
            use_cache: 是否使用缓存

        Returns:
            LLM实例（ChatOpenAI或兼容实例）
        """
        if config is None:
            if model_id:
                config = self._config_from_model_id(model_id)
            else:
                config = self.get_default_config()

        cache_key = self._get_cache_key(config)
        if use_cache and cache_key in self._llm_cache:
            return self._llm_cache[cache_key]

        llm = self._create_langchain_llm(config)

        if use_cache:
            self._llm_cache[cache_key] = llm

        return llm

    def _config_from_model_id(self, model_id: str) -> LLMConfig:
        """从模型ID生成LLMConfig"""
        model_config = self.get_model_config(model_id)
        if not model_config:
            logger.warning(f"Model {model_id} not found, using default")
            return self.get_default_config()

        return LLMConfig(
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            temperature=self.config.default_temperature,
            max_tokens=model_config.get("max_tokens", self.config.default_max_tokens),
            base_url=model_config.get("base_url"),
            timeout=self.config.default_timeout,
        )

    def _get_cache_key(self, config: LLMConfig) -> str:
        """生成缓存键"""
        return f"{config.provider}:{config.model_name}:{config.temperature}"

    def _create_langchain_llm(self, config: LLMConfig) -> Any:
        """创建LangChain LLM实例"""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            logger.error("langchain-openai not installed")
            raise ImportError("请安装 langchain-openai: pip install langchain-openai")

        # 构建初始化参数
        init_params = {
            "model": config.model_name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
        }

        # 处理API密钥
        if config.api_key:
            init_params["api_key"] = config.api_key
        elif config.provider == "anthropic":
            init_params["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        else:
            init_params["api_key"] = os.getenv("OPENAI_API_KEY")

        # 处理base_url
        if config.base_url:
            init_params["base_url"] = config.base_url

        # 根据provider选择合适的初始化方式
        if config.provider == "anthropic":
            # Anthropic需要特殊处理
            return ChatOpenAI(
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout=config.timeout,
                api_key=init_params.get("api_key"),
            )
        else:
            return ChatOpenAI(**init_params)

    def list_models(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出支持的模型

        Args:
            category: 可选，按分类筛选（如"minimax", "openai"）

        Returns:
            模型列表
        """
        if category:
            return [m for m in SUPPORTED_MODELS if m["category"] == category]
        return SUPPORTED_MODELS.copy()

    def get_model_categories(self) -> Dict[str, str]:
        """获取所有模型分类"""
        return MODEL_CATEGORIES.copy()

    def clear_cache(self):
        """清空LLM缓存"""
        self._llm_cache.clear()
        logger.info("LLM cache cleared")


# ============ 便捷函数 ============

_default_factory: Optional[LLMFactory] = None


def get_default_factory() -> LLMFactory:
    """获取默认工厂实例（单例）"""
    global _default_factory
    if _default_factory is None:
        _default_factory = LLMFactory()
    return _default_factory


def create_llm(
    model_id: Optional[str] = None,
    config: Optional[LLMConfig] = None
) -> Any:
    """便捷函数：创建LLM实例"""
    return get_default_factory().create_llm(model_id=model_id, config=config)


def get_model_config(model_id: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取模型配置"""
    return get_default_factory().get_model_config(model_id)


def list_all_models() -> List[Dict[str, Any]]:
    """便捷函数：列出所有模型"""
    return get_default_factory().list_models()


def list_models_by_category(category: str) -> List[Dict[str, Any]]:
    """便捷函数：按分类列出模型"""
    return get_default_factory().list_models(category=category)
