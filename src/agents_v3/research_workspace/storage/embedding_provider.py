"""统一 Embedding Provider：本地/云端配置切换

提供 EmbeddingProvider 协议，支持两种实现：
- LocalEmbeddingProvider: 本地 sentence-transformers
- CloudEmbeddingProvider: Qdrant Cloud inference API

通过 get_embedding_provider() 工厂函数从 config.yaml 自动选择。
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable

from loguru import logger


# ── 协议定义 ─────────────────────────────────────────────

@runtime_checkable
class EmbeddingProvider(Protocol):
    """统一 embedding 接口，本地和云端通用"""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本（dense）"""
        ...

    def embed_query(self, query: str) -> list[float]:
        """向量化查询文本（dense，单条）"""
        ...

    def fit_sparse(self, corpus: list[str]) -> None:
        """用语料库训练 sparse 编码器"""
        ...

    def embed_texts_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        """批量编码为稀疏向量"""
        ...

    def embed_query_sparse(self, query: str) -> dict[int, float]:
        """编码查询文本为稀疏向量"""
        ...

    def embed_texts_hybrid(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """同时返回 dense 和 sparse 向量"""
        ...

    def embed_query_hybrid(
        self, query: str
    ) -> tuple[list[float], dict[int, float]]:
        """同时返回查询的 dense 和 sparse 向量"""
        ...

    @property
    def dimension(self) -> int:
        """dense 向量维度"""
        ...

    @property
    def mode(self) -> str:
        """当前模式: 'local' 或 'cloud'"""
        ...


# ── 本地实现 ─────────────────────────────────────────────

class LocalEmbeddingProvider:
    """本地 sentence-transformers 实现（包装 EmbeddingService）"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from src.agents_v3.research_workspace.storage.embedding import EmbeddingService
        self._service = EmbeddingService(model_name)
        logger.info(f"[EmbeddingProvider] Local mode: {model_name}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._service.embed_texts(texts)

    def embed_query(self, query: str) -> list[float]:
        return self._service.embed_query(query)

    def fit_sparse(self, corpus: list[str]) -> None:
        self._service.fit_sparse(corpus)

    def embed_texts_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        return self._service.embed_texts_sparse(texts)

    def embed_query_sparse(self, query: str) -> dict[int, float]:
        return self._service.embed_query_sparse(query)

    def embed_texts_hybrid(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        return self._service.embed_texts_hybrid(texts)

    def embed_query_hybrid(
        self, query: str
    ) -> tuple[list[float], dict[int, float]]:
        return self._service.embed_query_hybrid(query)

    @property
    def dimension(self) -> int:
        return self._service.dimension

    @property
    def mode(self) -> str:
        return "local"


# ── 云端实现 ─────────────────────────────────────────────

# 临时集合名前缀，用于纯 embedding 提取
_TMP_PREFIX = "__embed_tmp_"


class CloudEmbeddingProvider:
    """Qdrant Cloud inference API 实现

    原理：通过 Qdrant 的 Document 对象让云端模型生成向量。
    纯 embedding 提取使用临时集合：upsert Document → scroll 取向量 → 删除。
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        dense_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        sparse_model: str = "Qdrant/bm25",
        dimension: int = 384,
    ):
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            Distance,
            Document,
            PointStruct,
            SparseIndexParams,
            SparseVectorParams,
            VectorParams,
        )
        self._Document = Document
        self._PointStruct = PointStruct
        self._VectorParams = VectorParams
        self._SparseVectorParams = SparseVectorParams
        self._SparseIndexParams = SparseIndexParams
        self._Distance = Distance

        self.client = QdrantClient(url=url, api_key=api_key, cloud_inference=True)
        self.dense_model = dense_model
        self.sparse_model = sparse_model
        self._dimension = dimension
        logger.info(f"[EmbeddingProvider] Cloud mode: dense={dense_model}, sparse={sparse_model}")

    # ── Dense 编码 ──────────────────────────────────────

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本（dense，通过临时集合）"""
        if not texts:
            return []
        return self._extract_vectors(texts, vector_type="dense")

    def embed_query(self, query: str) -> list[float]:
        """向量化查询文本（dense，单条）"""
        vectors = self._extract_vectors([query], vector_type="dense")
        return vectors[0]

    # ── Sparse 编码 ─────────────────────────────────────

    def fit_sparse(self, corpus: list[str]) -> None:
        """云端模式无需本地训练 sparse 编码器（no-op）"""
        logger.debug("[EmbeddingProvider] Cloud mode: fit_sparse is no-op")

    def embed_texts_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        """批量编码为稀疏向量（通过临时集合）"""
        if not texts:
            return []
        return self._extract_vectors(texts, vector_type="sparse")

    def embed_query_sparse(self, query: str) -> dict[int, float]:
        """编码查询文本为稀疏向量"""
        vectors = self._extract_vectors([query], vector_type="sparse")
        return vectors[0]

    # ── Hybrid 编码 ─────────────────────────────────────

    def embed_texts_hybrid(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """同时返回 dense 和 sparse 向量"""
        if not texts:
            return [], []
        dense, sparse = self._extract_vectors_hybrid(texts)
        return dense, sparse

    def embed_query_hybrid(
        self, query: str
    ) -> tuple[list[float], dict[int, float]]:
        """同时返回查询的 dense 和 sparse 向量"""
        dense, sparse = self._extract_vectors_hybrid([query])
        return dense[0], sparse[0]

    # ── 属性 ───────────────────────────────────────────

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def mode(self) -> str:
        return "cloud"

    # ── 内部方法 ────────────────────────────────────────

    def _extract_vectors(
        self, texts: list[str], vector_type: str = "dense"
    ) -> list[Any]:
        """通过临时集合提取向量

        Args:
            texts: 待编码文本列表
            vector_type: "dense" 返回 list[float]，"sparse" 返回 dict[int, float]

        Returns:
            向量列表
        """
        tmp_col = f"{_TMP_PREFIX}{uuid.uuid4().hex[:12]}"

        try:
            # 创建临时集合
            vectors_config = {
                "dense": self._VectorParams(size=self._dimension, distance=self._Distance.COSINE),
            }
            sparse_vectors_config = {
                "sparse": self._SparseVectorParams(
                    index=self._SparseIndexParams(on_disk=False),
                ),
            }
            self.client.create_collection(
                collection_name=tmp_col,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )

            # upsert Document 对象，让 Qdrant Cloud 生成向量
            points = []
            for i, text in enumerate(texts):
                points.append(self._PointStruct(
                    id=i,
                    vector={
                        "dense": self._Document(text=text, model=self.dense_model),
                        "sparse": self._Document(text=text, model=self.sparse_model),
                    },
                ))
            self.client.upsert(collection_name=tmp_col, points=points)

            # scroll 取回生成的向量
            results, _ = self.client.scroll(
                collection_name=tmp_col,
                limit=len(texts),
                with_vectors=True,
            )

            # 按 id 排序确保顺序一致
            results.sort(key=lambda p: p.id)

            vectors = []
            for point in results:
                if vector_type == "dense":
                    vectors.append(point.vector.get("dense", []))
                else:
                    sparse_vec = point.vector.get("sparse", {})
                    # sparse 可能是 SparseVector 对象或 dict
                    if hasattr(sparse_vec, "indices"):
                        vectors.append(dict(zip(sparse_vec.indices, sparse_vec.values)))
                    else:
                        vectors.append(sparse_vec)

            return vectors

        finally:
            # 清理临时集合
            try:
                self.client.delete_collection(tmp_col)
            except Exception:
                pass

    def _extract_vectors_hybrid(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """通过临时集合同时提取 dense 和 sparse 向量"""
        tmp_col = f"{_TMP_PREFIX}{uuid.uuid4().hex[:12]}"

        try:
            vectors_config = {
                "dense": self._VectorParams(size=self._dimension, distance=self._Distance.COSINE),
            }
            sparse_vectors_config = {
                "sparse": self._SparseVectorParams(
                    index=self._SparseIndexParams(on_disk=False),
                ),
            }
            self.client.create_collection(
                collection_name=tmp_col,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )

            points = []
            for i, text in enumerate(texts):
                points.append(self._PointStruct(
                    id=i,
                    vector={
                        "dense": self._Document(text=text, model=self.dense_model),
                        "sparse": self._Document(text=text, model=self.sparse_model),
                    },
                ))
            self.client.upsert(collection_name=tmp_col, points=points)

            results, _ = self.client.scroll(
                collection_name=tmp_col,
                limit=len(texts),
                with_vectors=True,
            )

            results.sort(key=lambda p: p.id)

            dense_list = []
            sparse_list = []
            for point in results:
                dense_list.append(point.vector.get("dense", []))
                sparse_vec = point.vector.get("sparse", {})
                if hasattr(sparse_vec, "indices"):
                    sparse_list.append(dict(zip(sparse_vec.indices, sparse_vec.values)))
                else:
                    sparse_list.append(sparse_vec)

            return dense_list, sparse_list

        finally:
            try:
                self.client.delete_collection(tmp_col)
            except Exception:
                pass


# ── 工厂函数 ─────────────────────────────────────────────

_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """从 config.yaml 读取配置，返回对应的 EmbeddingProvider

    配置优先级:
        database.qdrant.embedding.mode → 显式指定 "local" 或 "cloud"
        database.qdrant.cloud.enabled  → mode 未设置时的 fallback

    其他配置项:
        database.qdrant.inference.dense_model → dense 模型名
        database.qdrant.inference.sparse_model → sparse 模型名
        database.qdrant.vector_size → 向量维度
    """
    global _provider
    if _provider is not None:
        return _provider

    try:
        from src.agents_v3.research_workspace.config import load_config
        cfg = load_config()
    except Exception:
        cfg = {}

    qdrant_cfg = cfg.get("database", {}).get("qdrant", {})
    cloud_cfg = qdrant_cfg.get("cloud", {})
    inference_cfg = qdrant_cfg.get("inference", {})
    embedding_cfg = qdrant_cfg.get("embedding", {})

    dense_model = inference_cfg.get("dense_model", "sentence-transformers/all-MiniLM-L6-v2")
    sparse_model = inference_cfg.get("sparse_model", "Qdrant/bm25")
    vector_size = qdrant_cfg.get("vector_size", 384)

    # mode: 显式配置 > cloud.enabled 推断
    mode = embedding_cfg.get("mode")
    if mode is None:
        mode = "cloud" if cloud_cfg.get("enabled") else "local"

    if mode == "cloud" and cloud_cfg.get("url") and cloud_cfg.get("api_key"):
        _provider = CloudEmbeddingProvider(
            url=cloud_cfg["url"],
            api_key=cloud_cfg["api_key"],
            dense_model=dense_model,
            sparse_model=sparse_model,
            dimension=vector_size,
        )
    else:
        _provider = LocalEmbeddingProvider(model_name=dense_model)

    return _provider


def reset_embedding_provider() -> None:
    """重置全局 provider（用于测试或配置切换后）"""
    global _provider
    _provider = None


# ── SPECTER2 学术文本 Provider ─────────────────────────

class SPECTER2Provider:
    """SPECTER2 学术文本 Embedding Provider（本地 sentence-transformers，768 维）

    SPECTER2 基于 SciBERT，在 citation graph 上训练，适合学术文本语义匹配。
    输入格式：title + abstract 拼接。对短 label 实体，拼接 description 作为补充。
    """

    def __init__(self, model_name: str = "allenai/specter2_base"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        self._dimension = 768
        logger.info(f"[SPECTER2Provider] Loaded: {model_name} (dim={self._dimension})")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return [v.tolist() for v in embeddings]

    def embed_query(self, query: str) -> list[float]:
        embedding = self._model.encode([query], show_progress_bar=False, convert_to_numpy=True)
        return embedding[0].tolist()

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def mode(self) -> str:
        return "local"


_specter2_provider: SPECTER2Provider | None = None


def get_specter2_provider() -> SPECTER2Provider:
    """获取 SPECTER2 单例 Provider

    配置路径: database.embedding.specter2.model_name
    默认模型: allenai/specter2_base
    """
    global _specter2_provider
    if _specter2_provider is not None:
        return _specter2_provider

    try:
        from src.agents_v3.research_workspace.config import load_config
        cfg = load_config()
    except Exception:
        cfg = {}

    model_name = (
        cfg.get("database", {})
        .get("embedding", {})
        .get("specter2", {})
        .get("model_name", "allenai/specter2_base")
    )

    _specter2_provider = SPECTER2Provider(model_name=model_name)
    return _specter2_provider


def reset_specter2_provider() -> None:
    """重置 SPECTER2 provider（用于测试）"""
    global _specter2_provider
    _specter2_provider = None
