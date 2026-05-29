"""ChromaDB 向量存储后端"""

from __future__ import annotations

from typing import Any

from loguru import logger

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.warning("chromadb not installed, vector storage unavailable")


class VectorStorage:
    """ChromaDB 向量存储"""

    def __init__(self, path: str = "data/chromadb"):
        if not HAS_CHROMADB:
            raise RuntimeError("chromadb is not installed. Run: pip install chromadb")

        self.client = chromadb.PersistentClient(path=path)
        logger.info(f"ChromaDB initialized at {path}")

    def get_or_create_collection(self, name: str):
        """获取或创建集合"""
        return self.client.get_or_create_collection(name)

    def add_documents(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """添加文档到集合"""
        col = self.get_or_create_collection(collection)
        col.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.debug(f"Added {len(ids)} documents to {collection}")

    def update_documents(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """更新文档"""
        col = self.get_or_create_collection(collection)
        col.update(ids=ids, documents=documents, metadatas=metadatas)

    def delete_documents(self, collection: str, ids: list[str]) -> None:
        """删除文档"""
        col = self.get_or_create_collection(collection)
        col.delete(ids=ids)

    def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """查询相似文档"""
        col = self.get_or_create_collection(collection)
        kwargs = {"query_texts": [query_text], "n_results": n_results}
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    def query_by_embedding(
        self,
        collection: str,
        embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """通过嵌入向量查询"""
        col = self.get_or_create_collection(collection)
        kwargs = {"query_embeddings": [embedding], "n_results": n_results}
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    def get_collection_count(self, collection: str) -> int:
        """获取集合中的文档数量"""
        col = self.get_or_create_collection(collection)
        return col.count()

    def list_collections(self) -> list[str]:
        """列出所有集合"""
        return [c.name for c in self.client.list_collections()]

    def delete_collection(self, name: str) -> None:
        """删除集合"""
        self.client.delete_collection(name)
        logger.info(f"Deleted collection: {name}")


def get_vector_storage(path: str = "data/chromadb") -> VectorStorage:
    """获取向量存储实例"""
    return VectorStorage(path=path)
