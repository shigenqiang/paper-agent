"""
知识图谱向量存储模块

支持:
1. Qdrant客户端集成
2. 内存向量存储（演示用）
3. 嵌入模型封装
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from src.agents_v2.logging_config import get_logging_logger

import math

logger = get_logging_logger(__name__)


@dataclass
class VectorSearchResult:
    """向量搜索结果"""
    id: str
    score: float
    payload: Dict[str, Any] = field(default_factory=dict)


class BaseVectorStore(ABC):
    """向量存储基类"""

    @abstractmethod
    def upsert(
        self,
        id: str,
        vector: List[float],
        payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """插入或更新向量"""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_payload: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """搜索最近邻"""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """删除向量"""
        pass

    @abstractmethod
    def count(self) -> int:
        """获取向量数量"""
        pass


class InMemoryVectorStore(BaseVectorStore):
    """
    内存向量存储

    适用于小规模数据或测试
    生产环境应使用Qdrant
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self._vectors: Dict[str, List[float]] = {}
        self._payloads: Dict[str, Dict[str, Any]] = {}

    def upsert(
        self,
        id: str,
        vector: List[float],
        payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """插入或更新向量"""
        if len(vector) != self.dimension:
            raise ValueError(
                f"Vector dimension {len(vector)} != expected {self.dimension}"
            )

        self._vectors[id] = vector
        if payload:
            self._payloads[id] = payload
        return True

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_payload: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """搜索最近邻"""
        if not self._vectors:
            return []

        # 计算余弦相似度
        scores = []
        for id, vector in self._vectors.items():
            # 过滤
            if filter_payload:
                payload = self._payloads.get(id, {})
                if not self._matches_filter(payload, filter_payload):
                    continue

            score = self._cosine_similarity(query_vector, vector)
            scores.append((id, score))

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)

        # 返回top_k
        results = []
        for id, score in scores[:top_k]:
            results.append(VectorSearchResult(
                id=id,
                score=score,
                payload=self._payloads.get(id, {})
            ))

        return results

    def delete(self, id: str) -> bool:
        """删除向量"""
        if id in self._vectors:
            del self._vectors[id]
            if id in self._payloads:
                del self._payloads[id]
            return True
        return False

    def count(self) -> int:
        """获取向量数量"""
        return len(self._vectors)

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _matches_filter(
        self,
        payload: Dict[str, Any],
        filter_spec: Dict[str, Any]
    ) -> bool:
        """检查payload是否匹配过滤器"""
        for key, value in filter_spec.items():
            if key not in payload:
                return False
            if isinstance(value, list):
                if payload[key] not in value:
                    return False
            elif payload[key] != value:
                return False
        return True


class QdrantVectorStore(BaseVectorStore):
    """
    Qdrant向量存储

    需要qdrant-client库:
        pip install qdrant-client

    使用方式:
        store = QdrantVectorStore(
            url="localhost:6333",
            collection_name="papers",
            dimension=768
        )
    """

    def __init__(
        self,
        url: str = "localhost:6333",
        collection_name: str = "default",
        dimension: int = 768,
        api_key: Optional[str] = None
    ):
        """
        Args:
            url: Qdrant服务器地址
            collection_name: 集合名称
            dimension: 向量维度
            api_key: API密钥（可选）
        """
        self.url = url
        self.collection_name = collection_name
        self.dimension = dimension
        self.api_key = api_key
        self._client = None
        self._initialized = False

    def _get_client(self):
        """获取Qdrant客户端"""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key
                )
            except ImportError:
                raise ImportError(
                    "qdrant-client not installed. Run: pip install qdrant-client"
                )
        return self._client

    def initialize(self) -> bool:
        """初始化集合"""
        try:
            client = self._get_client()

            # 检查集合是否存在
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                # 创建集合
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "size": self.dimension,
                        "distance": "Cosine"
                    }
                )

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Qdrant initialization error: {e}")
            return False

    def upsert(
        self,
        id: str,
        vector: List[float],
        payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """插入或更新向量"""
        if not self._initialized:
            self.initialize()

        try:
            client = self._get_client()

            points = [{
                "id": id,
                "vector": vector,
                "payload": payload or {}
            }]

            client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return True

        except Exception as e:
            logger.error(f"Qdrant upsert error: {e}")
            return False

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_payload: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """搜索最近邻"""
        if not self._initialized:
            self.initialize()

        try:
            client = self._get_client()

            search_params = {}
            if filter_payload:
                search_params["filter"] = self._build_filter(filter_payload)

            results = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                **search_params
            )

            return [
                VectorSearchResult(
                    id=r.id,
                    score=r.score,
                    payload=r.payload or {}
                )
                for r in results
            ]

        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []

    def delete(self, id: str) -> bool:
        """删除向量"""
        if not self._initialized:
            self.initialize()

        try:
            client = self._get_client()
            client.delete(
                collection_name=self.collection_name,
                points_selector=[id]
            )
            return True

        except Exception as e:
            logger.error(f"Qdrant delete error: {e}")
            return False

    def count(self) -> int:
        """获取向量数量"""
        if not self._initialized:
            self.initialize()

        try:
            client = self._get_client()
            info = client.get_collection(self.collection_name)
            return info.vectors_count
        except Exception as e:
            logger.error(f"Qdrant count error: {e}")
            return 0

    def _build_filter(self, filter_spec: Dict[str, Any]) -> Dict:
        """构建Qdrant过滤器"""
        must_conditions = []
        for key, value in filter_spec.items():
            if isinstance(value, list):
                must_conditions.append({
                    "key": key,
                    "match": {"any": value}
                })
            else:
                must_conditions.append({
                    "key": key,
                    "match": {"value": value}
                })

        return {
            "must": must_conditions
        }


class EmbeddingModel:
    """
    嵌入模型封装

    支持:
    - sentence-transformers (本地)
    - OpenAI (API)
    - Cohere (API)
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        """
        Args:
            model_name: 模型名称
            device: 设备 ("cpu" 或 "cuda")
        """
        self.model_name = model_name
        self.device = device
        self._model = None

    def load(self) -> bool:
        """加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            return True
        except Exception as e:
            logger.error(f"Model loading error: {e}")
            return False

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """编码文本为向量"""
        if self._model is None:
            self.load()

        if isinstance(texts, str):
            texts = [texts]

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        return embeddings.tolist()

    def encode_query(self, query: str) -> List[float]:
        """编码查询文本"""
        return self.encode([query])[0]


def create_vector_store(
    store_type: str = "memory",
    **kwargs
) -> BaseVectorStore:
    """
    工厂函数：创建向量存储

    Args:
        store_type: "memory" 或 "qdrant"
        **kwargs: 传递给向量存储的参数
    """
    if store_type == "memory":
        return InMemoryVectorStore(**kwargs)
    elif store_type == "qdrant":
        return QdrantVectorStore(**kwargs)
    else:
        raise ValueError(f"Unknown store type: {store_type}")
