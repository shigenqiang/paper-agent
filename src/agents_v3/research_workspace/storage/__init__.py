"""存储子包 — PostgreSQL + Qdrant + Embedding"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents_v3.research_workspace.storage.backend import StorageBackend
from src.agents_v3.research_workspace.storage.embedding import EmbeddingService, get_embedding_service
from src.agents_v3.research_workspace.storage.embedding_provider import (
    CloudEmbeddingProvider,
    EmbeddingProvider,
    LocalEmbeddingProvider,
    get_embedding_provider,
    reset_embedding_provider,
)
from src.agents_v3.research_workspace.storage.postgres import PostgresStorage, get_postgres_storage
from src.agents_v3.research_workspace.storage.qdrant import get_collection_info, init_qdrant
from src.agents_v3.research_workspace.storage.vector import VectorStorage, get_vector_storage

# 全局 PostgreSQL 单例
_pg_instance: PostgresStorage | None = None


def _load_pg_config() -> dict[str, Any]:
    """从 config.yaml 读取 PostgreSQL 配置，环境变量可覆盖"""
    import os
    import yaml
    config_path = Path("config.yaml")
    config: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        config = cfg.get("database", {}).get("postgres", {})

    # 环境变量覆盖
    dsn = os.environ.get("PAPER_AGENT_DB_DSN")
    if dsn:
        config["dsn"] = dsn
    password = os.environ.get("PAPER_AGENT_DB_PASSWORD")
    if password:
        config["password"] = password
    return config


def get_storage() -> PostgresStorage:
    """获取全局 PostgreSQL 存储实例（单例）"""
    global _pg_instance
    if _pg_instance is not None:
        return _pg_instance

    pg_config = _load_pg_config()
    dsn = pg_config.get("dsn")
    if dsn:
        _pg_instance = PostgresStorage(dsn=dsn)
    else:
        _pg_instance = PostgresStorage(
            host=pg_config.get("host", "localhost"),
            port=pg_config.get("port", 5432),
            database=pg_config.get("database", "paper_agent"),
            user=pg_config.get("user", "postgres"),
            password=pg_config.get("password", ""),
        )
    return _pg_instance


__all__ = [
    "CloudEmbeddingProvider", "EmbeddingProvider", "EmbeddingService",
    "LocalEmbeddingProvider", "PostgresStorage", "StorageBackend",
    "VectorStorage", "get_collection_info", "get_embedding_provider",
    "get_embedding_service", "get_postgres_storage", "get_storage",
    "get_vector_storage", "init_qdrant", "reset_embedding_provider",
]
