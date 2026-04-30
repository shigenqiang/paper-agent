"""
Ecosystem模块 - 生态适配器

包含:
- LangChainAdapter: LangChain适配器
- AutoGenAdapter: AutoGen适配器
- HuggingFaceAdapter: HuggingFace适配器
- OpenAIAdapter: OpenAI适配器
- EcosystemManager: 生态管理器
"""
from .adapters import (
    LangChainAdapter,
    AutoGenAdapter,
    HuggingFaceAdapter,
    OpenAIAdapter,
    EcosystemManager,
    create_langchain_adapter,
    create_autogen_adapter,
    create_huggingface_adapter,
    create_openai_adapter,
    create_ecosystem_manager
)

__all__ = [
    "LangChainAdapter",
    "AutoGenAdapter",
    "HuggingFaceAdapter",
    "OpenAIAdapter",
    "EcosystemManager",
    "create_langchain_adapter",
    "create_autogen_adapter",
    "create_huggingface_adapter",
    "create_openai_adapter",
    "create_ecosystem_manager"
]