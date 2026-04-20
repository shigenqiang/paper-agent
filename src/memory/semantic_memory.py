"""长期记忆（语义记忆）模块"""
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """记忆类型"""
    FACT = "fact"  # 事实性知识
    CONCEPT = "concept"  # 概念定义
    PROCEDURE = "procedure"  # 过程/方法
    EXPERIENCE = "experience"  # 经验
    REFERENCE = "reference"  # 参考文献
    INSIGHT = "insight"  # 洞察/发现


class SemanticMemoryItem(BaseModel):
    """语义记忆项"""
    id: str
    content: str
    memory_type: MemoryType
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime
    last_accessed: datetime
    access_count: int = 0
    tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    source: Optional[str] = None  # 来源
    metadata: Optional[Dict[str, Any]] = None

    def calculate_relevance_score(
        self,
        query_time: datetime,
        time_decay: float = 0.99,
        importance_weight: float = 0.7,
        access_weight: float = 0.3
    ) -> float:
        """
        计算相关性分数
        考虑时效性、重要性、访问频率
        """
        # 时效性分数
        days_old = (query_time - self.last_accessed).days
        time_score = time_decay ** days_old

        # 访问频率分数
        access_score = min(1.0, self.access_count * 0.1)

        # 综合分数
        score = (
            self.importance * importance_weight +
            time_score * (1 - importance_weight) * 0.5 +
            access_score * access_weight
        ) * self.confidence

        return score


class SemanticMemory(BaseModel):
    """语义记忆（长期记忆）"""

    memories: Dict[str, SemanticMemoryItem] = {}
    tags_index: Dict[str, List[str]] = {}  # 标签到记忆ID的映射
    max_memories: int = 10000
    cleanup_threshold: int = 12000  # 超过这个数量时触发清理

    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        confidence: float = 0.8,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """添加语义记忆"""
        memory_id = f"sem_{datetime.now().timestamp()}"

        memory = SemanticMemoryItem(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            confidence=confidence,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=0,
            tags=tags or [],
            embedding=embedding,
            source=source,
            metadata=metadata or {}
        )

        self.memories[memory_id] = memory

        # 更新标签索引
        for tag in memory.tags:
            if tag not in self.tags_index:
                self.tags_index[tag] = []
            self.tags_index[tag].append(memory_id)

        # 检查是否需要清理
        if len(self.memories) >= self.cleanup_threshold:
            self._cleanup_low_importance()

        logger.info(f"Added semantic memory: {memory_id} (type: {memory_type})")
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[SemanticMemoryItem]:
        """获取记忆项"""
        memory = self.memories.get(memory_id)
        if memory:
            memory.last_accessed = datetime.now()
            memory.access_count += 1
        return memory

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        confidence: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """更新记忆项"""
        memory = self.memories.get(memory_id)
        if not memory:
            return False

        if content is not None:
            memory.content = content
        if importance is not None:
            memory.importance = max(0.0, min(1.0, importance))
        if confidence is not None:
            memory.confidence = max(0.0, min(1.0, confidence))
        if tags is not None:
            # 更新标签索引
            for old_tag in memory.tags:
                if old_tag in self.tags_index and memory_id in self.tags_index[old_tag]:
                    self.tags_index[old_tag].remove(memory_id)
            memory.tags = tags
            for new_tag in tags:
                if new_tag not in self.tags_index:
                    self.tags_index[new_tag] = []
                self.tags_index[new_tag].append(memory_id)

        memory.updated_at = datetime.now()
        logger.debug(f"Updated semantic memory: {memory_id}")
        return True

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆项"""
        memory = self.memories.get(memory_id)
        if not memory:
            return False

        # 从标签索引中移除
        for tag in memory.tags:
            if tag in self.tags_index and memory_id in self.tags_index[tag]:
                self.tags_index[tag].remove(memory_id)

        del self.memories[memory_id]
        logger.info(f"Deleted semantic memory: {memory_id}")
        return True

    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        top_k: Optional[int] = None
    ) -> List[SemanticMemoryItem]:
        """根据标签搜索记忆"""
        if match_all:
            # 所有标签都匹配
            matched_ids = set(self.tags_index.get(tags[0], []))
            for tag in tags[1:]:
                matched_ids &= set(self.tags_index.get(tag, []))
            results = [self.memories[mid] for mid in matched_ids if mid in self.memories]
        else:
            # 任意标签匹配
            matched_ids = set()
            for tag in tags:
                matched_ids.update(self.tags_index.get(tag, []))
            results = [self.memories[mid] for mid in matched_ids if mid in self.memories]

        # 按重要性排序
        results.sort(key=lambda m: m.importance, reverse=True)

        return results[:top_k] if top_k else results

    def search_by_content(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[SemanticMemoryItem, float]]:
        """根据内容搜索记忆（简化版，实际应该使用向量检索）"""
        query_lower = query.lower()
        results = []

        for memory in self.memories.values():
            # 简单的关键词匹配
            score = 0.0
            content_lower = memory.content.lower()

            # 精确匹配
            if query_lower in content_lower:
                score = 1.0
            # 部分匹配（单词级别）
            else:
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                if query_words & content_words:
                    intersection = query_words & content_words
                    score = len(intersection) / len(query_words)

            if score > 0:
                # 考虑时效性和重要性
                relevance_score = score * memory.calculate_relevance_score(datetime.now())
                results.append((memory, relevance_score))

        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[SemanticMemoryItem, float]]:
        """根据向量嵌入搜索记忆"""
        results = []

        for memory in self.memories.values():
            if memory.embedding:
                similarity = self._cosine_similarity(query_embedding, memory.embedding)
                if similarity >= threshold:
                    relevance_score = similarity * memory.calculate_relevance_score(datetime.now())
                    results.append((memory, relevance_score))

        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def get_by_type(
        self,
        memory_type: MemoryType,
        top_k: Optional[int] = None
    ) -> List[SemanticMemoryItem]:
        """根据类型获取记忆"""
        results = [
            memory for memory in self.memories.values()
            if memory.memory_type == memory_type
        ]

        # 按重要性排序
        results.sort(key=lambda m: m.importance, reverse=True)

        return results[:top_k] if top_k else results

    def get_by_source(self, source: str) -> List[SemanticMemoryItem]:
        """根据来源获取记忆"""
        return [
            memory for memory in self.memories.values()
            if memory.source == source
        ]

    def get_high_importance_memories(
        self,
        threshold: float = 0.8,
        top_k: Optional[int] = None
    ) -> List[SemanticMemoryItem]:
        """获取高重要性记忆"""
        results = [
            memory for memory in self.memories.values()
            if memory.importance >= threshold
        ]

        results.sort(key=lambda m: m.importance, reverse=True)
        return results[:top_k] if top_k else results

    def _cleanup_low_importance(self, threshold: float = 0.3, max_age_days: int = 90) -> int:
        """清理低重要性且旧的记忆"""
        now = datetime.now()
        threshold_date = now - timedelta(days=max_age_days)

        to_delete = []
        for memory_id, memory in self.memories.items():
            if (memory.importance < threshold and
                memory.last_accessed < threshold_date and
                memory.access_count < 2):
                to_delete.append(memory_id)

        for memory_id in to_delete:
            self.delete_memory(memory_id)

        logger.info(f"Cleaned up {len(to_delete)} low importance semantic memories")
        return len(to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.memories:
            return {"total": 0}

        type_counts = {}
        for memory in self.memories.values():
            memory_type = memory.memory_type.value
            type_counts[memory_type] = type_counts.get(memory_type, 0) + 1

        avg_importance = sum(m.importance for m in self.memories.values()) / len(self.memories)
        avg_confidence = sum(m.confidence for m in self.memories.values()) / len(self.memories)

        return {
            "total": len(self.memories),
            "by_type": type_counts,
            "average_importance": avg_importance,
            "average_confidence": avg_confidence,
            "total_access_count": sum(m.access_count for m in self.memories.values()),
            "tags_count": len(self.tags_index)
        }

    def export_memories(self, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
        """导出记忆"""
        memories = self.memories.values()

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        return [
            {
                "id": m.id,
                "content": m.content,
                "type": m.memory_type.value,
                "importance": m.importance,
                "confidence": m.confidence,
                "tags": m.tags,
                "source": m.source,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat()
            }
            for m in memories
        ]
