"""
长期记忆 - Long Term Memory

职责: 跨任务持久化，支持语义检索
- 双重存储: 向量数据库 + 图数据库
- 语义检索 + 标签检索
- 重要性 + 时间衰减
"""
import asyncio
import time
import json
import os
import hashlib
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from .types import MemoryEntry, MemoryType, ImportanceLevel


class VectorStore:
    """
    简单向量存储 (可替换为Pinecone/Milvus/Chroma)

    当前实现: TF-IDF + 内存存储
    """

    def __init__(self, storage_path: str = ".memory/vectors"):
        self.storage_path = storage_path
        self._index_path = os.path.join(storage_path, "index.json")
        self._vectors: Dict[str, List[float]] = {}  # key -> vector
        self._content: Dict[str, Any] = {}  # key -> content
        self._load_index()

    def _load_index(self) -> None:
        """加载索引"""
        if os.path.exists(self._index_path):
            try:
                with open(self._index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._vectors = data.get("vectors", {})
                    self._content = data.get("content", {})
            except Exception:
                pass

    def _save_index(self) -> None:
        """保存索引"""
        os.makedirs(self.storage_path, exist_ok=True)
        with open(self._index_path, 'w', encoding='utf-8') as f:
            json.dump({
                "vectors": self._vectors,
                "content": self._content
            }, f, ensure_ascii=False)

    def _compute_tfidf_vector(self, text: str) -> List[float]:
        """
        计算TF-IDF向量 (简化实现)

        完整实现应使用sklearn的TfidfVectorizer
        """
        words = text.lower().split()
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1

        # 简化的TF-IDF: 使用词频作为向量
        # 完整实现应该计算IDF
        unique_words = list(set(words))
        vector = [0.0] * max(len(unique_words), 1)

        for i, word in enumerate(unique_words[:100]):  # 限制维度
            vector[i] = word_freq[word] / max(len(words), 1)

        return vector

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if not v1 or not v2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def add(self, key: str, content: Any, metadata: Optional[Dict] = None) -> None:
        """添加向量"""
        text_content = str(content)
        vector = self._compute_tfidf_vector(text_content)

        self._vectors[key] = vector
        self._content[key] = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self._save_index()

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """语义搜索"""
        query_vector = self._compute_tfidf_vector(query)

        results = []
        for key, vector in self._vectors.items():
            similarity = self._cosine_similarity(query_vector, vector)
            if similarity > 0.1:  # 阈值
                results.append({
                    "key": key,
                    "similarity": similarity,
                    "content": self._content[key]["content"],
                    "metadata": self._content[key].get("metadata", {})
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    async def delete(self, key: str) -> None:
        """删除向量"""
        if key in self._vectors:
            del self._vectors[key]
        if key in self._content:
            del self._content[key]
        self._save_index()

    def keys(self) -> List[str]:
        """获取所有键"""
        return list(self._content.keys())


class GraphStore:
    """
    简单图存储 (可替换为Neo4j)

    当前实现: 内存 + JSON持久化
    """

    def __init__(self, storage_path: str = ".memory/graphs"):
        self.storage_path = storage_path
        self._graph_path = os.path.join(storage_path, "graph.json")
        self._entities: Dict[str, Dict[str, Any]] = {}  # entity_id -> entity
        self._relations: List[Dict[str, Any]] = []  # [source, relation, target]
        self._load_graph()

    def _load_graph(self) -> None:
        """加载图"""
        if os.path.exists(self._graph_path):
            try:
                with open(self._graph_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._entities = data.get("entities", {})
                    self._relations = data.get("relations", [])
            except Exception:
                pass

    def _save_graph(self) -> None:
        """保存图"""
        os.makedirs(self.storage_path, exist_ok=True)
        with open(self._graph_path, 'w', encoding='utf-8') as f:
            json.dump({
                "entities": self._entities,
                "relations": self._relations
            }, f, ensure_ascii=False)

    async def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加实体"""
        self._entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "properties": properties or {},
            "created_at": time.time()
        }
        self._save_graph()

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加关系"""
        self._relations.append({
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "properties": properties or {},
            "created_at": time.time()
        })
        self._save_graph()

    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """获取实体"""
        return self._entities.get(entity_id)

    async def get_relations(
        self,
        entity_id: str,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取实体关系"""
        relations = []
        for rel in self._relations:
            if rel["source"] == entity_id or rel["target"] == entity_id:
                if relation_type is None or rel["type"] == relation_type:
                    relations.append(rel)
        return relations

    async def search_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """按类型搜索实体"""
        return [
            entity for entity in self._entities.values()
            if entity.get("type") == entity_type
        ]

    async def extract_and_link(
        self,
        content: Any,
        extractor: Optional[Callable] = None
    ) -> None:
        """
        从内容中提取实体并建立关系

        当前为简化实现，完整版需要NER/LLM
        """
        text = str(content)

        # 简单提取：假设内容格式为 "主题: 描述"
        if ": " in text:
            parts = text.split(": ", 1)
            if len(parts) == 2:
                subject, description = parts

                # 创建实体
                entity_id = hashlib.md5(subject.encode()).hexdigest()[:12]
                await self.add_entity(
                    entity_id=entity_id,
                    entity_type="concept",
                    properties={"name": subject, "description": description}
                )

                # 建立与任务的关联
                # (实际应该从context中获取task_id)


class LongTermMemory:
    """
    长期记忆 - 跨任务持久化

    双重存储:
    - VectorStore: 语义内容存储
    - GraphStore: 实体关系存储
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        graph_store: Optional[GraphStore] = None,
        storage_path: str = ".memory"
    ):
        self.vector_store = vector_store or VectorStore(storage_path=os.path.join(storage_path, "vectors"))
        self.graph_store = graph_store or GraphStore(storage_path=os.path.join(storage_path, "graphs"))
        self.storage_path = storage_path
        self._lock = asyncio.Lock()

    async def remember(
        self,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        persist: bool = True,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        存储到长期记忆

        Args:
            key: 记忆键
            value: 记忆值
            tags: 标签
            persist: 是否持久化
            importance: 重要性
            metadata: 元数据
        """
        async with self._lock:
            if not persist:
                return

            entry = MemoryEntry(
                id=key,
                memory_type=MemoryType.LONG_TERM,
                content=value,
                importance=importance,
                tags=tags or [],
                metadata=metadata or {}
            )

            # 存储到向量数据库
            await self.vector_store.add(
                key=key,
                content=value,
                metadata={
                    "importance": importance,
                    "tags": tags,
                    **entry.to_dict()
                }
            )

            # 从内容中提取实体并建立关系
            try:
                await self.graph_store.extract_and_link(value)
            except Exception:
                pass  # 图提取失败不影响主流程

    async def recall(self, key: str) -> Optional[Any]:
        """
        检索记忆

        Args:
            key: 记忆键

        Returns:
            记忆值或None
        """
        async with self._lock:
            # 从向量存储获取
            results = await self.vector_store.search(key, limit=1)
            if results:
                return results[0].get("content")

            return None

    async def search(
        self,
        query: str,
        limit: int = 10,
        tags: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """
        搜索记忆

        Args:
            query: 搜索查询
            limit: 返回数量限制
            tags: 可选的标签过滤

        Returns:
            匹配的MemoryEntry列表
        """
        async with self._lock:
            results = await self.vector_store.search(query, limit)

            entries = []
            for result in results:
                metadata = result.get("metadata", {})
                entry_tags = metadata.get("tags", [])

                # 标签过滤
                if tags and not any(tag in entry_tags for tag in tags):
                    continue

                entry = MemoryEntry(
                    id=result["key"],
                    memory_type=MemoryType.LONG_TERM,
                    content=result["content"],
                    importance=metadata.get("importance", 0.5),
                    tags=entry_tags,
                    metadata=metadata
                )
                entries.append(entry)

                if len(entries) >= limit:
                    break

            return entries

    async def search_by_entity(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按实体搜索相关记忆"""
        relations = await self.graph_store.get_relations(entity_id)

        results = []
        for rel in relations[:limit]:
            related_id = rel["target"] if rel["source"] == entity_id else rel["source"]
            entity = await self.graph_store.get_entity(related_id)
            if entity:
                results.append({
                    "entity": entity,
                    "relation": rel
                })

        return results

    async def search_by_relation(
        self,
        relation_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按关系类型搜索"""
        relations = []
        for rel in self.graph_store._relations:
            if rel["type"] == relation_type:
                relations.append(rel)

            if len(relations) >= limit:
                break

        return relations

    async def delete(self, key: str) -> bool:
        """删除记忆"""
        async with self._lock:
            await self.vector_store.delete(key)
            return True

    async def list_all(self) -> List[str]:
        """列出所有记忆键"""
        return self.vector_store.keys()

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_memories": len(self.vector_store.keys()),
            "total_entities": len(self.graph_store._entities),
            "total_relations": len(self.graph_store._relations),
            "memory_type": MemoryType.LONG_TERM.value
        }

    async def cleanup_low_importance(self, threshold: float = 0.2) -> int:
        """
        清理低重要性记忆

        Args:
            threshold: 重要性阈值

        Returns:
            删除数量
        """
        async with self._lock:
            deleted = 0
            keys = await self.list_all()

            for key in keys:
                results = await self.vector_store.search(key, limit=1)
                if results:
                    importance = results[0].get("metadata", {}).get("importance", 1.0)
                    if importance < threshold:
                        await self.vector_store.delete(key)
                        deleted += 1

            return deleted
