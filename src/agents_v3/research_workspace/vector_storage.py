"""Qdrant 向量存储后端"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

# 固定命名空间，确保相同字符串 ID 总是生成相同 UUID
_NS_QDRANT = uuid.UUID("a3f5b8c2-7d1e-4f9a-b6c8-123456789abc")


def _to_point_id(chunk_id: str) -> uuid.UUID:
    """将字符串 ID 确定性地转换为 Qdrant 兼容的 UUID"""
    return uuid.uuid5(_NS_QDRANT, chunk_id)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointIdsList,
        PointStruct,
        VectorParams,
    )

    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    logger.warning("qdrant-client not installed, vector storage unavailable")


class VectorStorage:
    """Qdrant 向量存储"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        vector_size: int = 512,
        distance: str = "cosine",
    ):
        if not HAS_QDRANT:
            raise RuntimeError("qdrant-client is not installed. Run: pip install qdrant-client")

        self.client = QdrantClient(host=host, port=port)
        self.vector_size = vector_size
        self.distance = Distance.COSINE if distance == "cosine" else Distance.EUCLID
        logger.info(f"Qdrant connected at {host}:{port}")

    def _ensure_collection(self, name: str) -> None:
        """确保集合存在"""
        collections = [c.name for c in self.client.get_collections().collections]
        if name not in collections:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=self.vector_size, distance=self.distance),
            )
            logger.info(f"Created Qdrant collection: {name}")

    def add_documents(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """添加文档到集合（需要预计算的 embeddings）"""
        self._ensure_collection(collection)
        if embeddings is None:
            raise ValueError("Qdrant backend requires pre-computed embeddings")

        points = []
        for i, (doc_id, text, emb) in enumerate(zip(ids, documents, embeddings)):
            payload = {"text": text, "chunk_id": doc_id}
            if metadatas and i < len(metadatas):
                payload.update(metadatas[i])
            points.append(PointStruct(id=_to_point_id(doc_id), vector=emb, payload=payload))

        self.client.upsert(collection_name=collection, points=points)
        logger.debug(f"Added {len(ids)} documents to {collection}")

    def update_documents(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """更新文档"""
        self.add_documents(collection, ids, documents, metadatas, embeddings)

    def delete_documents(self, collection: str, ids: list[str]) -> None:
        """删除文档"""
        self._ensure_collection(collection)
        self.client.delete(
            collection_name=collection,
            points_selector=PointIdsList(points=[_to_point_id(i) for i in ids]),
        )

    def query_by_embedding(
        self,
        collection: str,
        embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """通过嵌入向量查询"""
        self._ensure_collection(collection)

        query_filter = None
        if where:
            conditions = []
            for key, value in where.items():
                if isinstance(value, list):
                    # 多值匹配：任一匹配即可
                    from qdrant_client.models import MatchAny

                    conditions.append(
                        FieldCondition(key=key, match=MatchAny(any=value))
                    )
                else:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
            query_filter = Filter(must=conditions)

        results = self.client.query_points(
            collection_name=collection,
            query=embedding,
            limit=n_results,
            query_filter=query_filter,
            with_payload=True,
        )

        ids_list = []
        documents_list = []
        metadatas_list = []
        distances_list = []

        for point in results.points:
            payload = point.payload or {}
            # 优先使用原始 chunk_id，没有则用 point UUID
            ids_list.append(payload.pop("chunk_id", str(point.id)))
            documents_list.append(payload.pop("text", ""))
            metadatas_list.append(payload)
            distances_list.append(1.0 - point.score)  # cosine distance

        return {
            "ids": [ids_list],
            "documents": [documents_list],
            "metadatas": [metadatas_list],
            "distances": [distances_list],
        }

    def get_collection_count(self, collection: str) -> int:
        """获取集合中的文档数量"""
        self._ensure_collection(collection)
        info = self.client.get_collection(collection)
        return info.points_count

    def list_collections(self) -> list[str]:
        """列出所有集合"""
        return [c.name for c in self.client.get_collections().collections]

    def delete_collection(self, name: str) -> None:
        """删除集合"""
        self.client.delete_collection(name)
        logger.info(f"Deleted collection: {name}")

    def add_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        collection: str = "paper_chunks",
    ) -> None:
        """存储分块到向量库（跳过 parent 块，parent 块仅存 PostgreSQL）"""
        # 过滤掉 parent 块，只嵌入子块
        child_indices = [i for i, c in enumerate(chunks) if c.get("chunk_type") != "parent"]
        child_chunks = [chunks[i] for i in child_indices]
        child_embeddings = [embeddings[i] for i in child_indices]

        ids = [c["chunk_id"] for c in child_chunks]
        documents = [c["text"] for c in child_chunks]
        metadatas = [
            {
                "paper_id": c.get("paper_id", ""),
                "section_type": c.get("section_type", ""),
                "chunk_type": c.get("chunk_type", ""),
                "parent_id": c.get("parent_id", ""),
                "page_start": c.get("page_start", 0),
                "page_end": c.get("page_end", 0),
                "token_count": c.get("token_count", 0),
            }
            for c in child_chunks
        ]
        self.add_documents(collection, ids, documents, metadatas, child_embeddings)
        logger.info(f"Added {len(ids)} child chunks to {collection} (skipped {len(chunks) - len(ids)} parent chunks)")

    def search_chunks(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        paper_ids: list[str] | None = None,
        collection: str = "paper_chunks",
    ) -> list[dict[str, Any]]:
        """向量检索最相关的 chunks"""
        where = None
        if paper_ids:
            where = {"paper_id": paper_ids if len(paper_ids) > 1 else paper_ids[0]}

        results = self.query_by_embedding(collection, query_embedding, top_k, where)

        items = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                items.append({
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                })
        return items

    def delete_by_paper(self, paper_id: str, collection: str = "paper_chunks") -> None:
        """删除某论文的所有 chunks"""
        self._ensure_collection(collection)
        self.client.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
        )
        logger.info(f"Deleted chunks for paper {paper_id} from {collection}")

    def delete_by_papers(self, paper_ids: list[str], collection: str = "paper_chunks") -> int:
        """批量删除多篇论文的所有 chunks，返回删除的论文数"""
        if not paper_ids:
            return 0
        self._ensure_collection(collection)
        from qdrant_client.models import MatchAny
        self.client.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[FieldCondition(key="paper_id", match=MatchAny(any=paper_ids))]
            ),
        )
        logger.info(f"Deleted chunks for {len(paper_ids)} papers from {collection}")
        return len(paper_ids)


def get_vector_storage(
    host: str = "localhost",
    port: int = 6333,
    vector_size: int = 512,
) -> VectorStorage:
    """获取向量存储实例"""
    return VectorStorage(host=host, port=port, vector_size=vector_size)
