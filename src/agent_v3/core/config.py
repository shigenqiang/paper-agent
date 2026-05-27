"""
Configuration for Agent v3.

Reads from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "minimax-m2.7"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 120


@dataclass
class EmbeddingConfig:
    model_name: str = "Qwen3-Embedding-0.6B"
    model_path: str = ""
    dimension: int = 1024


@dataclass
class StorageConfig:
    db_path: str = "data/agent_v3.db"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    log_level: str = "INFO"


def load_config() -> AppConfig:
    """Load config from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")
    model = os.getenv("LLM_MODEL", "minimax-m2.7")
    provider = os.getenv("LLM_PROVIDER", "openai")

    # MiniMax default base URL
    if not base_url and "minimax" in model.lower():
        base_url = "https://api.minimax.chat/v1"

    return AppConfig(
        llm=LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            timeout=int(os.getenv("LLM_TIMEOUT", "120")),
        ),
        embedding=EmbeddingConfig(
            model_path=os.getenv(
                "EMBEDDING_MODEL_PATH",
                "src/agents_v2/embedding/models/Qwen3-Embedding-0.6B",
            ),
        ),
        storage=StorageConfig(
            db_path=os.getenv("AGENT_V3_DB_PATH", "data/agent_v3.db"),
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
