"""
向量嵌入接口 - Vector Embedding Interface

支持多种嵌入后端:
1. OpenAI (text-embedding-ada-002, text-embedding-3-small)
2. 本地模型 (sentence-transformers, BGE)
3. 自定义接口
"""
import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import numpy as np


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    embedding: List[float]
    model: str
    tokens: int
    content_hash: str  # 用于去重


class EmbeddingConfig:
    """嵌入配置"""
    def __init__(
        self,
        provider: str = "openai",  # openai, local, custom
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,  # 用于代理或自定义端点
        batch_size: int = 100,
        max_retries: int = 3
    ):
        self.provider = provider
        self.model = model
        self.dimension = dimension
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url
        self.batch_size = batch_size
        self.max_retries = max_retries


class BaseEmbedder(ABC):
    """嵌入器基类"""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[EmbeddingResult]:
        """嵌入文本列表"""
        pass

    @abstractmethod
    async def embed_single(self, text: str) -> EmbeddingResult:
        """嵌入单个文本"""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度"""
        pass


class OpenAIEmbedder(BaseEmbedder):
    """
    OpenAI嵌入器

    支持模型:
    - text-embedding-ada-002 (1536维)
    - text-embedding-3-small (1536维)
    - text-embedding-3-large (3072维)
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._client = None

    async def _get_client(self):
        """获取OpenAI客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url
                )
            except ImportError:
                # 如果没有OpenAI SDK，使用requests
                import aiohttp
                self._client = aiohttp.ClientSession()

        return self._client

    async def embed(self, texts: List[str]) -> List[EmbeddingResult]:
        """嵌入文本列表"""
        if not texts:
            return []

        results = []

        # 批量处理
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            batch_results = await self._embed_batch(batch)
            results.extend(batch_results)

        return results

    async def _embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """批量嵌入"""
        import hashlib
        import json

        try:
            client = await self._get_client()
            from openai import AsyncOpenAI

            if isinstance(client, AsyncOpenAI):
                response = await client.embeddings.create(
                    model=self.config.model,
                    input=texts
                )

                return [
                    EmbeddingResult(
                        embedding=r.embedding,
                        model=self.config.model,
                        tokens=0,  # OpenAI不返回这个
                        content_hash=hashlib.md5(texts[i].encode()).hexdigest()
                    )
                    for i, r in enumerate(response.data)
                ]
            else:
                # 使用requests
                import requests
                headers = {
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.config.model,
                    "input": texts
                }

                url = f"{self.config.base_url}/v1/embeddings" if self.config.base_url else "https://api.openai.com/v1/embeddings"

                async with client.post(url, headers=headers, json=data) as resp:
                    result = await resp.json()

                return [
                    EmbeddingResult(
                        embedding=r["embedding"],
                        model=self.config.model,
                        tokens=0,
                        content_hash=hashlib.md5(texts[i].encode()).hexdigest()
                    )
                    for i, r in enumerate(result["data"])
                ]

        except Exception as e:
            # 如果失败，返回零向量
            return [
                EmbeddingResult(
                    embedding=[0.0] * self.dimension,
                    model=self.config.model,
                    tokens=0,
                    content_hash=hashlib.md5(t.encode()).hexdigest()
                )
                for t in texts
            ]

    async def embed_single(self, text: str) -> EmbeddingResult:
        """嵌入单个文本"""
        results = await self.embed([text])
        return results[0] if results else EmbeddingResult(
            embedding=[0.0] * self.dimension,
            model=self.config.model,
            tokens=0,
            content_hash=""
        )

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        if self.config.model == "text-embedding-3-large":
            return 3072
        return 1536


class LocalEmbedder(BaseEmbedder):
    """
    本地嵌入器

    支持:
    - sentence-transformers
    - BGE
    - 其他本地模型
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
        normalize: bool = True
    ):
        self.model_name = model_name
        self.device = device
        self.normalize = normalize
        self._model = None

    async def _get_model(self):
        """获取模型"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    async def embed(self, texts: List[str]) -> List[EmbeddingResult]:
        """嵌入文本列表"""
        if not texts:
            return []

        model = await self._get_model()
        import hashlib

        # 同步调用，但在线程池中执行避免阻塞
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(texts, normalize_embeddings=self.normalize)
        )

        return [
            EmbeddingResult(
                embedding=emb.tolist(),
                model=self.model_name,
                tokens=0,
                content_hash=hashlib.md5(text.encode()).hexdigest()
            )
            for emb, text in zip(embeddings, texts)
        ]

    async def embed_single(self, text: str) -> EmbeddingResult:
        """嵌入单个文本"""
        results = await self.embed([text])
        return results[0]

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        # 常见模型的维度
        dims = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "BAAI/bge-small-zh": 512,
            "BAAI/bge-base-zh": 768,
        }
        return dims.get(self.model_name, 768)


def create_embedder(config: Optional[EmbeddingConfig] = None) -> BaseEmbedder:
    """
    创建嵌入器工厂

    Args:
        config: 嵌入配置

    Returns:
        BaseEmbedder实例
    """
    config = config or EmbeddingConfig()

    if config.provider == "openai":
        return OpenAIEmbedder(config)
    elif config.provider == "local":
        return LocalEmbedder(model_name=config.model)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


class VectorStore:
    """
    简单向量存储 (增强版 - 支持真实嵌入)

    可替换为:
    - Pinecone
    - Milvus
    - Qdrant
    - PostgreSQL + pgvector
    """

    def __init__(
        self,
        storage_path: str = ".memory/vectors",
        embedder: Optional[BaseEmbedder] = None,
        dimension: int = 1536
    ):
        self.storage_path = storage_path
        self.embedder = embedder or OpenAIEmbedder(EmbeddingConfig())
        self.dimension = dimension
        self._embeddings: Dict[str, List[float]] = {}  # key -> embedding
        self._metadata: Dict[str, Dict[str, Any]] = {}  # key -> metadata
        self._load_index()

    def _load_index(self) -> None:
        """加载索引"""
        import os, json

        index_file = os.path.join(self.storage_path, "index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._metadata = data.get("metadata", {})
            except Exception:
                pass

    def _save_index(self) -> None:
        """保存索引"""
        import os, json

        os.makedirs(self.storage_path, exist_ok=True)
        index_file = os.path.join(self.storage_path, "index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump({"metadata": self._metadata}, f, ensure_ascii=False)

    async def add(
        self,
        key: str,
        content: Any,
        metadata: Optional[Dict] = None,
        regenerate: bool = False
    ) -> None:
        """添加向量"""
        import os, json

        # 如果已有且不重新生成，直接返回
        if key in self._embeddings and not regenerate:
            return

        # 生成嵌入
        text_content = str(content)
        result = await self.embedder.embed_single(text_content)

        self._embeddings[key] = result.embedding

        # 存储元数据
        self._metadata[key] = {
            "content": content,
            "metadata": metadata or {},
            "model": result.model,
            "hash": result.content_hash,
            "timestamp": os.path.getmtime(os.path.join(self.storage_path, f"{key}.json")) if os.path.exists(os.path.join(self.storage_path, f"{key}.json")) else 0
        }

        # 保存向量文件
        vec_file = os.path.join(self.storage_path, f"{key}.json")
        os.makedirs(self.storage_path, exist_ok=True)
        with open(vec_file, 'w', encoding='utf-8') as f:
            json.dump({
                "key": key,
                "embedding": result.embedding,
                "metadata": self._metadata[key]
            }, f, ensure_ascii=False)

        self._save_index()

    async def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        import os

        # 生成查询向量
        query_result = await self.embedder.embed_single(query)
        query_vec = np.array(query_result.embedding)

        results = []

        for key, embedding in self._embeddings.items():
            # 计算余弦相似度
            vec = np.array(embedding)

            # 归一化
            norm1 = np.linalg.norm(query_vec)
            norm2 = np.linalg.norm(vec)

            if norm1 == 0 or norm2 == 0:
                similarity = 0.0
            else:
                similarity = np.dot(query_vec, vec) / (norm1 * norm2)

            if similarity >= threshold:
                metadata = self._metadata.get(key, {})
                results.append({
                    "key": key,
                    "similarity": float(similarity),
                    "content": metadata.get("content"),
                    "metadata": metadata.get("metadata", {})
                })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(v1, v2) / (norm1 * norm2))

    async def delete(self, key: str) -> None:
        """删除向量"""
        import os

        if key in self._embeddings:
            del self._embeddings[key]

        if key in self._metadata:
            del self._metadata[key]

        vec_file = os.path.join(self.storage_path, f"{key}.json")
        if os.path.exists(vec_file):
            os.remove(vec_file)

        self._save_index()

    def keys(self) -> List[str]:
        """获取所有键"""
        return list(self._embeddings.keys())

    def count(self) -> int:
        """获取向量数量"""
        return len(self._embeddings)
