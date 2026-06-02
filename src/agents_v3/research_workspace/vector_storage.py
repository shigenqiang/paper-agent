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
        Document,
        FieldCondition,
        Filter,
        Fusion,
        FusionQuery,
        MatchValue,
        PointIdsList,
        PointStruct,
        Prefetch,
        Query,
        SparseIndexParams,
        SparseVector,
        SparseVectorParams,
        VectorParams,
    )

    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    logger.warning("qdrant-client not installed, vector storage unavailable")


class VectorStorage:
    """Qdrant 向量存储（支持本地和云端推理）"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        vector_size: int = 512,
        distance: str = "cosine",
        cloud_url: str | None = None,
        cloud_api_key: str | None = None,
        cloud_inference: bool = False,
        dense_model: str = "BAAI/bge-small-zh-v1.5",
        sparse_model: str = "Qdrant/bm25",
    ):
        if not HAS_QDRANT:
            raise RuntimeError("qdrant-client is not installed. Run: pip install qdrant-client")

        # 优先使用云端
        if cloud_url and cloud_api_key:
            self.client = QdrantClient(
                url=cloud_url,
                api_key=cloud_api_key,
                cloud_inference=cloud_inference,
            )
            self.use_cloud = True
            self.use_inference = cloud_inference
            logger.info(f"Qdrant Cloud connected: {cloud_url[:50]}...")
        else:
            self.client = QdrantClient(host=host, port=port)
            self.use_cloud = False
            self.use_inference = False
            logger.info(f"Qdrant local connected at {host}:{port}")

        self.vector_size = vector_size
        self.distance = Distance.COSINE if distance == "cosine" else Distance.EUCLID
        self.dense_model = dense_model
        self.sparse_model = sparse_model

    def _ensure_collection(self, name: str, with_sparse: bool = True) -> None:
        """确保集合存在

        Args:
            with_sparse: 是否创建带 sparse vector 的 collection（默认 True）
        """
        collections = [c.name for c in self.client.get_collections().collections]
        if name not in collections:
            vectors_config = {
                "dense": VectorParams(size=self.vector_size, distance=self.distance),
            }
            sparse_vectors_config = None
            if with_sparse:
                sparse_vectors_config = {
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False),
                    ),
                }
            self.client.create_collection(
                collection_name=name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
            logger.info(f"Created Qdrant collection: {name} (with_sparse={with_sparse})")

    def add_documents(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        embeddings: list[list[float]] | None = None,
        sparse_embeddings: list[dict[int, float]] | None = None,
    ) -> None:
        """添加文档到集合

        如果 use_inference=True，使用 Qdrant 云端推理（传文本，自动生成向量）。
        否则需要预计算的 embeddings。
        """
        self._ensure_collection(collection)

        points = []
        for i, (doc_id, text) in enumerate(zip(ids, documents)):
            payload = {"text": text, "chunk_id": doc_id}
            if metadatas and i < len(metadatas):
                payload.update(metadatas[i])

            if self.use_inference:
                # 云端推理：传文本，Qdrant 自动生成 dense + sparse 向量
                vector = {
                    "dense": Document(text=text, model=self.dense_model),
                    "sparse": Document(text=text, model=self.sparse_model),
                }
            else:
                # 本地模式：使用预计算的 embeddings
                if embeddings is None:
                    raise ValueError("Local mode requires pre-computed embeddings")
                emb = embeddings[i]
                if sparse_embeddings and i < len(sparse_embeddings) and sparse_embeddings[i]:
                    vector = {
                        "dense": emb,
                        "sparse": SparseVector(
                            indices=list(sparse_embeddings[i].keys()),
                            values=list(sparse_embeddings[i].values()),
                        ),
                    }
                else:
                    vector = emb

            points.append(PointStruct(id=_to_point_id(doc_id), vector=vector, payload=payload))

        self.client.upsert(collection_name=collection, points=points)
        logger.debug(f"Added {len(ids)} documents to {collection} (inference={self.use_inference})")

    def update_documents(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        embeddings: list[list[float]] | None = None,
        sparse_embeddings: list[dict[int, float]] | None = None,
    ) -> None:
        """更新文档"""
        self.add_documents(collection, ids, documents, metadatas, embeddings, sparse_embeddings)

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
        query_text: str | None = None,
    ) -> dict[str, Any]:
        """通过嵌入向量查询

        Args:
            query_text: 如果 use_inference=True，传原始文本让 Qdrant 服务端生成查询向量。
        """
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

        # 选择查询向量：推理模式用 Document，本地模式用预计算向量
        if self.use_inference and query_text:
            query_vector = Document(text=query_text, model=self.dense_model)
        else:
            query_vector = embedding

        results = self.client.query_points(
            collection_name=collection,
            query=query_vector,
            using="dense",
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
        sparse_embeddings: list[dict[int, float]] | None = None,
    ) -> None:
        """存储分块到向量库（跳过 parent 块，parent 块仅存 Qdrant）

        Args:
            sparse_embeddings: 可选的稀疏向量列表，与 chunks 一一对应。
        """
        # 过滤掉 parent 块，只嵌入子块
        child_indices = [i for i, c in enumerate(chunks) if c.get("chunk_type") != "parent"]
        child_chunks = [chunks[i] for i in child_indices]
        child_embeddings = [embeddings[i] for i in child_indices]
        child_sparse = [sparse_embeddings[i] for i in child_indices] if sparse_embeddings else None

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
        self.add_documents(collection, ids, documents, metadatas, child_embeddings, child_sparse)
        logger.info(f"Added {len(ids)} child chunks to {collection} (skipped {len(chunks) - len(ids)} parent chunks)")

    def add_paper_profiles(
        self,
        paper_ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        collection: str = "paper_profiles",
        embeddings: list[list[float]] | None = None,
        sparse_embeddings: list[dict[int, float]] | None = None,
    ) -> None:
        """存储论文级向量（title + abstract）

        云端推理模式下自动嵌入，本地模式需传入 embeddings。
        """
        self._ensure_collection(collection)

        points = []
        for i, (paper_id, text) in enumerate(zip(paper_ids, texts)):
            payload = {"paper_id": paper_id}
            if metadatas and i < len(metadatas):
                payload.update(metadatas[i])

            if self.use_inference:
                vector = {
                    "dense": Document(text=text, model=self.dense_model),
                    "sparse": Document(text=text, model=self.sparse_model),
                }
            elif embeddings and i < len(embeddings):
                vector = {"dense": embeddings[i]}
                if sparse_embeddings and i < len(sparse_embeddings):
                    vector["sparse"] = sparse_embeddings[i]
            else:
                raise ValueError("Local mode requires pre-computed embeddings")

            points.append(PointStruct(id=_to_point_id(paper_id), vector=vector, payload=payload))

        self.client.upsert(collection_name=collection, points=points)
        logger.info(f"Added {len(paper_ids)} paper profiles to {collection}")

    def add_search_query(
        self,
        query_id: str,
        query_text: str,
        collection: str = "search_queries",
    ) -> None:
        """存储搜索查询向量（用于历史查询相似度匹配）

        云端推理模式下自动嵌入，本地模式需预计算 embeddings。
        """
        self._ensure_collection(collection)

        payload = {"query_id": query_id}

        if self.use_inference:
            vector = {
                "dense": Document(text=query_text, model=self.dense_model),
                "sparse": Document(text=query_text, model=self.sparse_model),
            }
        else:
            raise ValueError("add_search_query requires cloud_inference=True for auto-embedding")

        point = PointStruct(id=_to_point_id(query_id), vector=vector, payload=payload)
        self.client.upsert(collection_name=collection, points=[point])
        logger.debug(f"Added search query {query_id} to {collection}")

    def search_similar_queries(
        self,
        query_text: str,
        top_k: int = 5,
        collection: str = "search_queries",
    ) -> list[dict[str, Any]]:
        """搜索相似的历史查询（dense only 语义搜索）

        使用 dense 向量的余弦相似度。
        返回的 score 是余弦相似度分数。

        Args:
            query_text: 查询文本
            top_k: 返回结果数
            collection: 集合名

        Returns:
            相似查询列表 [{"query_id": ..., "score": cosine_similarity}, ...]
        """
        self._ensure_collection(collection)

        if not self.use_inference:
            raise ValueError("search_similar_queries requires cloud_inference=True")

        results = self.client.query_points(
            collection_name=collection,
            query=Document(text=query_text, model=self.dense_model),
            using="dense",
            limit=top_k,
            with_payload=True,
        )

        items = []
        for point in results.points:
            payload = point.payload or {}
            items.append({
                "query_id": payload.get("query_id", str(point.id)),
                "score": point.score,
            })
        return items

    def search_dense_by_text(
        self,
        query_text: str,
        top_k: int = 10,
        paper_ids: list[str] | None = None,
        collection: str = "paper_profiles",
    ) -> list[dict[str, Any]]:
        """Dense-only 语义搜索（云端推理自动向量化）

        Args:
            query_text: 查询文本
            top_k: 返回结果数
            paper_ids: 可选的论文 ID 过滤
            collection: 集合名

        Returns:
            检索结果列表 [{"id": ..., "text": ..., "metadata": ..., "score": ...}]
        """
        self._ensure_collection(collection)

        query_filter = None
        if paper_ids:
            from qdrant_client.models import MatchAny
            conditions = [
                FieldCondition(
                    key="paper_id",
                    match=MatchAny(any=paper_ids) if len(paper_ids) > 1 else MatchValue(value=paper_ids[0]),
                )
            ]
            query_filter = Filter(must=conditions)

        if self.use_inference:
            query_vector = Document(text=query_text, model=self.dense_model)
        else:
            raise ValueError("search_dense_by_text requires cloud_inference=True")

        results = self.client.query_points(
            collection_name=collection,
            query=query_vector,
            using="dense",
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        items = []
        for point in results.points:
            payload = point.payload or {}
            items.append({
                "id": payload.pop("chunk_id", payload.get("paper_id", str(point.id))),
                "text": payload.pop("text", ""),
                "metadata": payload,
                "score": point.score,
            })
        return items

    def search_sparse_by_text(
        self,
        query_text: str,
        top_k: int = 10,
        paper_ids: list[str] | None = None,
        collection: str = "paper_profiles",
    ) -> list[dict[str, Any]]:
        """Sparse-only BM25 搜索（云端推理自动向量化）

        Args:
            query_text: 查询文本
            top_k: 返回结果数
            paper_ids: 可选的论文 ID 过滤
            collection: 集合名

        Returns:
            检索结果列表 [{"id": ..., "text": ..., "metadata": ..., "score": ...}]
        """
        self._ensure_collection(collection)

        query_filter = None
        if paper_ids:
            from qdrant_client.models import MatchAny
            conditions = [
                FieldCondition(
                    key="paper_id",
                    match=MatchAny(any=paper_ids) if len(paper_ids) > 1 else MatchValue(value=paper_ids[0]),
                )
            ]
            query_filter = Filter(must=conditions)

        if self.use_inference:
            sparse_vector = Document(text=query_text, model=self.sparse_model)
        else:
            raise ValueError("search_sparse_by_text requires cloud_inference=True")

        results = self.client.query_points(
            collection_name=collection,
            query=sparse_vector,
            using="sparse",
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        items = []
        for point in results.points:
            payload = point.payload or {}
            items.append({
                "id": payload.pop("chunk_id", payload.get("paper_id", str(point.id))),
                "text": payload.pop("text", ""),
                "metadata": payload,
                "score": point.score,
            })
        return items

    def search_hybrid(
        self,
        dense_embedding: list[float],
        sparse_embedding: dict[int, float],
        top_k: int = 10,
        paper_ids: list[str] | None = None,
        collection: str = "paper_chunks",
        fusion: str = "rrf",
    ) -> list[dict[str, Any]]:
        """Qdrant 原生混合检索：dense + sparse + RRF/DBSF 融合

        Args:
            dense_embedding: 稠密查询向量
            sparse_embedding: 稀疏查询向量 {index: weight}
            top_k: 返回结果数
            paper_ids: 可选的论文 ID 过滤
            collection: 集合名
            fusion: 融合方式，"rrf" 或 "dbsf"

        Returns:
            检索结果列表
        """
        self._ensure_collection(collection)

        # 构建过滤条件
        query_filter = None
        if paper_ids:
            from qdrant_client.models import MatchAny
            conditions = [
                FieldCondition(
                    key="paper_id",
                    match=MatchAny(any=paper_ids) if len(paper_ids) > 1 else MatchValue(value=paper_ids[0]),
                )
            ]
            query_filter = Filter(must=conditions)

        # 选择融合方式
        fusion_method = Fusion.RRF if fusion == "rrf" else Fusion.DBSF

        # 构建 sparse vector
        sparse_vec = SparseVector(
            indices=list(sparse_embedding.keys()),
            values=list(sparse_embedding.values()),
        )

        # Qdrant hybrid 查询
        results = self.client.query_points(
            collection_name=collection,
            prefetch=[
                Prefetch(
                    query=dense_embedding,
                    using="dense",
                    limit=top_k * 2,
                ),
                Prefetch(
                    query=sparse_vec,
                    using="sparse",
                    limit=top_k * 2,
                ),
            ],
            query=FusionQuery(fusion=fusion_method),
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        items = []
        for point in results.points:
            payload = point.payload or {}
            items.append({
                "chunk_id": payload.pop("chunk_id", str(point.id)),
                "text": payload.pop("text", ""),
                "metadata": payload,
                "score": point.score,
            })
        return items

    def search_hybrid_by_text(
        self,
        query_text: str,
        top_k: int = 10,
        paper_ids: list[str] | None = None,
        collection: str = "paper_chunks",
        fusion: str = "rrf",
    ) -> list[dict[str, Any]]:
        """文本版 hybrid 检索（云端推理自动向量化查询）

        Args:
            query_text: 查询文本（Qdrant 云端自动生成 dense + sparse 向量）
            top_k: 返回结果数
            paper_ids: 可选的论文 ID 过滤
            collection: 集合名
            fusion: 融合方式，"rrf" 或 "dbsf"

        Returns:
            检索结果列表
        """
        self._ensure_collection(collection)

        # 构建过滤条件
        query_filter = None
        if paper_ids:
            from qdrant_client.models import MatchAny
            conditions = [
                FieldCondition(
                    key="paper_id",
                    match=MatchAny(any=paper_ids) if len(paper_ids) > 1 else MatchValue(value=paper_ids[0]),
                )
            ]
            query_filter = Filter(must=conditions)

        fusion_method = Fusion.RRF if fusion == "rrf" else Fusion.DBSF

        if self.use_inference:
            # 云端推理：传文本，Qdrant 自动生成向量
            query_vector = Document(text=query_text, model=self.dense_model)
            sparse_vector = Document(text=query_text, model=self.sparse_model)
        else:
            raise ValueError("search_hybrid_by_text requires cloud_inference=True")

        results = self.client.query_points(
            collection_name=collection,
            prefetch=[
                Prefetch(query=query_vector, using="dense", limit=top_k * 2),
                Prefetch(query=sparse_vector, using="sparse", limit=top_k * 2),
            ],
            query=FusionQuery(fusion=fusion_method),
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        items = []
        for point in results.points:
            payload = point.payload or {}
            items.append({
                "id": payload.pop("chunk_id", str(point.id)),
                "text": payload.pop("text", ""),
                "metadata": payload,
                "score": point.score,
            })
        return items

    def search_chunks(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        paper_ids: list[str] | None = None,
        collection: str = "paper_chunks",
        query_text: str | None = None,
    ) -> list[dict[str, Any]]:
        """向量检索最相关的 chunks

        Args:
            query_text: 推理模式下传原始文本，让 Qdrant 服务端生成查询向量。
        """
        where = None
        if paper_ids:
            where = {"paper_id": paper_ids if len(paper_ids) > 1 else paper_ids[0]}

        results = self.query_by_embedding(collection, query_embedding, top_k, where, query_text=query_text)

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
    cloud_url: str | None = None,
    cloud_api_key: str | None = None,
    cloud_inference: bool = False,
    dense_model: str = "BAAI/bge-small-zh-v1.5",
    sparse_model: str = "Qdrant/bm25",
) -> VectorStorage:
    """获取向量存储实例（优先使用云端配置）"""
    # 尝试从 config 读取云端配置
    if not cloud_url:
        try:
            from src.agents_v3.research_workspace.config import load_config
            cfg = load_config()
            qdrant_cfg = cfg.get("database", {}).get("qdrant", {})
            cloud_cfg = qdrant_cfg.get("cloud", {})
            if cloud_cfg.get("enabled"):
                cloud_url = cloud_cfg.get("url")
                cloud_api_key = cloud_cfg.get("api_key")
                cloud_inference = cloud_cfg.get("cloud_inference", False)
            inference_cfg = qdrant_cfg.get("inference", {})
            dense_model = inference_cfg.get("dense_model", dense_model)
            sparse_model = inference_cfg.get("sparse_model", sparse_model)
            vector_size = qdrant_cfg.get("vector_size", vector_size)
        except Exception:
            pass

    return VectorStorage(
        host=host,
        port=port,
        vector_size=vector_size,
        cloud_url=cloud_url,
        cloud_api_key=cloud_api_key,
        cloud_inference=cloud_inference,
        dense_model=dense_model,
        sparse_model=sparse_model,
    )
