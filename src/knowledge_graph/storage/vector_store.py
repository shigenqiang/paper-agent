"""
向量存储客户端
Vector Store Client
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

from ..schema.academic_kg_schema import Entity


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    score: float
    metadata: Dict = None


class VectorStoreClient:
    """向量存储客户端"""

    def __init__(
        self,
        store_type: str = "qdrant",
        url: str = "http://localhost:6333",
        collection_name: str = "academic_kg",
        embedding_dim: int = 256
    ):
        self.store_type = store_type
        self.url = url
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        self.client = None
        self._initialized = False

        # 检查可用的向量存储
        self._available = self._check_available()

    def _check_available(self) -> bool:
        """检查向量存储是否可用"""
        if self.store_type == "qdrant":
            try:
                from qdrant_client import QdrantClient
                return True
            except ImportError:
                print("Warning: qdrant-client not installed")
                return False
        elif self.store_type == "milvus":
            try:
                from pymilvus import connections
                return True
            except ImportError:
                print("Warning: pymilvus not installed")
                return False
        elif self.store_type == "chroma":
            try:
                import chromadb
                return True
            except ImportError:
                print("Warning: chromadb not installed")
                return False

        return False

    def connect(self):
        """建立连接"""
        if not self._available:
            print(f"Mock: connect to {self.store_type}")
            return

        if self.store_type == "qdrant":
            from qdrant_client import QdrantClient
            self.client = QdrantClient(url=self.url)
            self._ensure_collection()

        elif self.store_type == "chroma":
            import chromadb
            self.client = chromadb.Client()

        self._initialized = True

    def _ensure_collection(self):
        """确保collection存在"""
        if self.store_type == "qdrant":
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )

    def insert(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict] = None
    ):
        """插入向量"""
        if not self._available:
            print(f"Mock: insert vector {id}")
            return

        if self.store_type == "qdrant":
            from qdrant_client.models import PointStruct

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=id,
                        vector=vector,
                        payload=metadata or {}
                    )
                ]
            )

        elif self.store_type == "chroma":
            self.client.add(
                ids=[id],
                embeddings=[vector],
                metadatas=[metadata] if metadata else None
            )

    def insert_batch(
        self,
        items: List[Dict[str, Any]]
    ):
        """批量插入"""
        if not self._available:
            print(f"Mock: batch insert {len(items)} items")
            return

        if self.store_type == "qdrant":
            from qdrant_client.models import PointStruct

            points = [
                PointStruct(
                    id=item["id"],
                    vector=item["vector"],
                    payload=item.get("metadata", {})
                )
                for item in items
            ]

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_conditions: Optional[Dict] = None
    ) -> List[SearchResult]:
        """向量相似度搜索"""
        if not self._available:
            return []

        if self.store_type == "qdrant":
            from qdrant_client.models import Filter

            search_params = {}
            if filter_conditions:
                search_params["filter"] = Filter(**filter_conditions)

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                **search_params
            )

            return [
                SearchResult(
                    id=r.id,
                    score=r.score,
                    metadata=r.payload
                )
                for r in results
            ]

        elif self.store_type == "chroma":
            results = self.client.query(
                query_embeddings=[query_vector],
                n_results=top_k
            )

            return [
                SearchResult(
                    id=results["ids"][0][i],
                    score=0.0,  # Chroma不返回分数
                    metadata=results["metadatas"][0][i] if results.get("metadatas") else None
                )
                for i in range(len(results["ids"][0]))
            ]

        return []

    def search_by_id(
        self,
        query_id: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """基于ID搜索"""
        if not self._available:
            return []

        # 获取查询向量的元数据
        if self.store_type == "qdrant":
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[query_id]
            )

            if not result:
                return []

            query_vector = result[0].vector
            return self.search(query_vector, top_k)

        return []

    def retrieve(self, id: str) -> Optional[Dict]:
        """检索单个向量"""
        if not self._available:
            return None

        if self.store_type == "qdrant":
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[id]
            )

            if results:
                r = results[0]
                return {
                    "id": r.id,
                    "vector": r.vector,
                    "metadata": r.payload
                }

        return None

    def delete(self, id: str):
        """删除向量"""
        if not self._available:
            print(f"Mock: delete vector {id}")
            return

        if self.store_type == "qdrant":
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[id]
            )

    def count(self) -> int:
        """统计向量数量"""
        if not self._available:
            return 0

        if self.store_type == "qdrant":
            info = self.client.get_collection(self.collection_name)
            return info.points_count

        return 0

    def close(self):
        """关闭连接"""
        self._initialized = False
        self.client = None
