"""Qdrant 集合初始化"""

from __future__ import annotations

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

# ── 集合定义 ──────────────────────────────────────────────

COLLECTIONS = {
    "paper_chunks": {
        "description": "论文文本分块的语义向量，用于 RAG 检索",
        "vector_size": 384,
        "distance": Distance.COSINE,
        "sparse": True,  # 启用 sparse vector
        "payload_indexes": [
            ("paper_id", PayloadSchemaType.KEYWORD),
            ("section_id", PayloadSchemaType.KEYWORD),
            ("project_id", PayloadSchemaType.KEYWORD),
            ("section_type", PayloadSchemaType.KEYWORD),
            ("chunk_type", PayloadSchemaType.KEYWORD),
        ],
    },
    "paper_profiles": {
        "description": "论文整体画像的语义向量，用于论文相似性搜索",
        "vector_size": 384,
        "distance": Distance.COSINE,
        "sparse": True,  # 启用 sparse vector
        "payload_indexes": [
            ("paper_id", PayloadSchemaType.KEYWORD),
            ("project_id", PayloadSchemaType.KEYWORD),
        ],
    },
    "search_queries": {
        "description": "搜索查询的语义向量，用于历史查询相似度匹配",
        "vector_size": 384,
        "distance": Distance.COSINE,
        "sparse": True,
        "payload_indexes": [
            ("query_id", PayloadSchemaType.KEYWORD),
        ],
    },
    "citation_contexts": {
        "description": "引用上下文的语义向量，用于引用语义检索和立场分析",
        "vector_size": 384,
        "distance": Distance.COSINE,
        "sparse": True,
        "payload_indexes": [
            ("citing_paper_id", PayloadSchemaType.KEYWORD),
            ("cited_paper_id", PayloadSchemaType.KEYWORD),
            ("citation_type", PayloadSchemaType.KEYWORD),
            ("section", PayloadSchemaType.KEYWORD),
            ("project_id", PayloadSchemaType.KEYWORD),
        ],
    },
    "paper_sections": {
        "description": "论文章节级全文向量，用于章节语义检索",
        "vector_size": 384,
        "distance": Distance.COSINE,
        "sparse": True,
        "payload_indexes": [
            ("paper_id", PayloadSchemaType.KEYWORD),
            ("section_type", PayloadSchemaType.KEYWORD),
            ("project_id", PayloadSchemaType.KEYWORD),
        ],
    },
}


def init_qdrant(
    host: str = "localhost",
    port: int = 6333,
    collections: dict | None = None,
    cloud_url: str | None = None,
    cloud_api_key: str | None = None,
    cloud_inference: bool = False,
) -> QdrantClient:
    """初始化 Qdrant，创建所有需要的集合和索引

    Args:
        host: Qdrant 主机
        port: Qdrant 端口
        collections: 自定义集合定义，None 则使用默认 COLLECTIONS
        cloud_url: Qdrant Cloud URL
        cloud_api_key: Qdrant Cloud API key
        cloud_inference: 是否启用云端推理

    Returns:
        QdrantClient 实例
    """
    if cloud_url and cloud_api_key:
        client = QdrantClient(url=cloud_url, api_key=cloud_api_key, cloud_inference=cloud_inference)
        logger.info(f"[Qdrant] Cloud connected: {cloud_url[:50]}...")
    else:
        client = QdrantClient(host=host, port=port)
        logger.info(f"[Qdrant] Local connected: {host}:{port}")
    existing = {c.name for c in client.get_collections().collections}
    defs = collections or COLLECTIONS

    for name, cfg in defs.items():
        if name not in existing:
            # 构建 named vectors config（dense + 可选 sparse）
            vectors_config = {
                "dense": VectorParams(
                    size=cfg["vector_size"],
                    distance=cfg["distance"],
                ),
            }
            sparse_vectors_config = None
            if cfg.get("sparse"):
                sparse_vectors_config = {
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False),
                    ),
                }

            client.create_collection(
                collection_name=name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
            logger.info(f"[Qdrant] Created collection: {name} (dim={cfg['vector_size']}, sparse={cfg.get('sparse', False)})")
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
