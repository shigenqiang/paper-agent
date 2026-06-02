"""文本向量化服务（dense + sparse）"""

from __future__ import annotations

from loguru import logger


class EmbeddingService:
    """基于 sentence-transformers 的文本向量化服务

    支持两种编码：
    - dense: 语义向量（sentence-transformers，512维）
    - sparse: 关键词向量（TF-IDF，稀疏）
    """

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info(f"Embedding model loaded: {model_name}")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed. Run: pip install sentence-transformers"
            )

        # sparse 编码器（延迟初始化）
        self._sparse_encoder = None
        self._sparse_fitted = False

    # ── Dense 编码 ──────────────────────────────────────

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本（dense）"""
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """向量化查询文本（dense，单条）"""
        return self.model.encode([query], show_progress_bar=False)[0].tolist()

    @property
    def dimension(self) -> int:
        """dense 向量维度"""
        return self.model.get_sentence_embedding_dimension()

    # ── Sparse 编码 ─────────────────────────────────────

    def _get_sparse_encoder(self):
        """获取 sparse 编码器（延迟初始化）"""
        if self._sparse_encoder is None:
            from src.agents_v3.research_workspace.search.sparse_encoder import SparseEncoder
            self._sparse_encoder = SparseEncoder()
        return self._sparse_encoder

    def fit_sparse(self, corpus: list[str]) -> None:
        """用语料库训练 sparse 编码器"""
        encoder = self._get_sparse_encoder()
        encoder.fit(corpus)
        self._sparse_fitted = True
        logger.info(f"Sparse encoder fitted with {len(corpus)} documents")

    def embed_texts_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        """批量编码为稀疏向量"""
        encoder = self._get_sparse_encoder()
        if not self._sparse_fitted:
            self.fit_sparse(texts)
        return encoder.encode_batch(texts)

    def embed_query_sparse(self, query: str) -> dict[int, float]:
        """编码查询文本为稀疏向量"""
        encoder = self._get_sparse_encoder()
        if not self._sparse_fitted:
            raise RuntimeError("Sparse encoder not fitted. Call fit_sparse() first.")
        return encoder.encode_query(query)

    def embed_texts_hybrid(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """同时返回 dense 和 sparse 向量

        Returns:
            (dense_embeddings, sparse_embeddings)
        """
        dense = self.embed_texts(texts)
        sparse = self.embed_texts_sparse(texts)
        return dense, sparse

    def embed_query_hybrid(
        self, query: str
    ) -> tuple[list[float], dict[int, float]]:
        """同时返回查询的 dense 和 sparse 向量

        Returns:
            (dense_embedding, sparse_embedding)
        """
        dense = self.embed_query(query)
        sparse = self.embed_query_sparse(query)
        return dense, sparse


_embedding_service: EmbeddingService | None = None


def get_embedding_service(model_name: str = "BAAI/bge-small-zh-v1.5") -> EmbeddingService:
    """获取全局 EmbeddingService 实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service
