"""文本向量化服务"""

from __future__ import annotations

from loguru import logger


class EmbeddingService:
    """基于 sentence-transformers 的文本向量化服务"""

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

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本"""
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """向量化查询文本（单条）"""
        return self.model.encode([query], show_progress_bar=False)[0].tolist()

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self.model.get_sentence_embedding_dimension()


_embedding_service: EmbeddingService | None = None


def get_embedding_service(model_name: str = "BAAI/bge-small-zh-v1.5") -> EmbeddingService:
    """获取全局 EmbeddingService 实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service
