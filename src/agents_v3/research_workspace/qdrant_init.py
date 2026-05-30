"""Qdrant 集合初始化"""

from __future__ import annotations

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    VectorParams,
)

# ── 集合定义 ──────────────────────────────────────────────

COLLECTIONS = {
    "paper_chunks": {
        "description": "论文文本分块的语义向量，用于 RAG 检索",
        "vector_size": 512,
        "distance": Distance.COSINE,
        "payload_indexes": [
            ("paper_id", PayloadSchemaType.KEYWORD),
            ("project_id", PayloadSchemaType.KEYWORD),
            ("section_type", PayloadSchemaType.KEYWORD),
            ("chunk_type", PayloadSchemaType.KEYWORD),
        ],
    },
    "paper_profiles": {
        "description": "论文整体画像的语义向量，用于论文相似性搜索",
        "vector_size": 512,
        "distance": Distance.COSINE,
        "payload_indexes": [
            ("paper_id", PayloadSchemaType.KEYWORD),
            ("project_id", PayloadSchemaType.KEYWORD),
        ],
    },
}


def init_qdrant(
    host: str = "localhost",
    port: int = 6333,
    collections: dict | None = None,
) -> QdrantClient:
    """初始化 Qdrant，创建所有需要的集合和索引

    Args:
        host: Qdrant 主机
        port: Qdrant 端口
        collections: 自定义集合定义，None 则使用默认 COLLECTIONS

    Returns:
        QdrantClient 实例
    """
    client = QdrantClient(host=host, port=port)
    existing = {c.name for c in client.get_collections().collections}
    defs = collections or COLLECTIONS

    for name, cfg in defs.items():
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=cfg["vector_size"],
                    distance=cfg["distance"],
                ),
            )
            logger.info(f"[Qdrant] Created collection: {name} (dim={cfg['vector_size']})")
        else:
            logger.debug(f"[Qdrant] Collection exists: {name}")

        # 创建 payload 索引（加速过滤查询）
        for field_name, field_type in cfg.get("payload_indexes", []):
            try:
                client.create_payload_index(
                    collection_name=name,
                    field_name=field_name,
                    field_schema=field_type,
                )
            except Exception:
                pass  # 索引已存在则跳过

    return client


def get_collection_info(
    host: str = "localhost",
    port: int = 6333,
) -> dict[str, dict]:
    """获取所有集合的状态信息"""
    client = QdrantClient(host=host, port=port)
    info = {}
    for col in client.get_collections().collections:
        detail = client.get_collection(col.name)
        info[col.name] = {
            "points_count": detail.points_count,
            "status": str(detail.status),
        }
    return info
