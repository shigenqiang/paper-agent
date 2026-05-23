"""
Common模块 - 公共模块统一导出

提供三大系统（论文写作/QA问答/报告生成）的公共模块。
"""

from .llm import (
    LLMFactory,
    LLMConfig,
    LLMFactoryConfig,
    create_llm,
    get_default_factory,
    get_model_config,
    list_all_models,
    list_models_by_category,
    SUPPORTED_MODELS,
    MODEL_CATEGORIES,
)

from .citation import (
    CitationParser,
    CitationFormatter,
    Citation,
    CitationStyle,
    format_citation,
    parse_citations,
)

__all__ = [
    # LLM模块
    "LLMFactory",
    "LLMConfig",
    "LLMFactoryConfig",
    "create_llm",
    "get_default_factory",
    "get_model_config",
    "list_all_models",
    "list_models_by_category",
    "SUPPORTED_MODELS",
    "MODEL_CATEGORIES",
    # Citation模块
    "CitationParser",
    "CitationFormatter",
    "Citation",
    "CitationStyle",
    "format_citation",
    "parse_citations",
]
