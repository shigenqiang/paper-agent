"""记忆语义检索"""
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
import logging
import numpy as np

from src.memory.semantic_memory import SemanticMemory, SemanticMemoryItem, MemoryType
from src.memory.episodic_memory import EpisodicMemory, Event, Episode
from src.memory.short_term_memory import ShortTermMemory, ConversationTurn

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    """检索结果"""
    content: str
    score: float
    source: str  # "semantic", "episodic", "short_term"
    memory_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class MemoryRetriever:
    """记忆检索器 - 集成语义检索"""

    def __init__(
        self,
        semantic_memory: SemanticMemory,
        episodic_memory: EpisodicMemory,
        embedding_service: Optional[Any] = None
    ):
        self.semantic_memory = semantic_memory
        self.episodic_memory = episodic_memory
        self.embedding_service = embedding_service

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        memory_types: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        use_embedding: bool = False
    ) -> List[RetrievalResult]:
        """
        综合检索记忆
        从语义记忆、情景记忆中检索相关信息
        """
        results = []

        # 从语义记忆检索
        if memory_types is None or "semantic" in memory_types:
            semantic_results = await self._retrieve_semantic(
                query, top_k // 2, use_embedding
            )
            results.extend(semantic_results)

        # 从情景记忆检索
        if memory_types is None or "episodic" in memory_types:
            episodic_results = await self._retrieve_episodic(
                query, top_k // 2, session_id, use_embedding
            )
            results.extend(episodic_results)

        # 按分数排序
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:top_k]

    async def _retrieve_semantic(
        self,
        query: str,
        top_k: int,
        use_embedding: bool
    ) -> List[RetrievalResult]:
        """从语义记忆检索"""
        results = []

        if use_embedding and self.embedding_service:
            # 使用向量嵌入检索
            try:
                query_embedding = await self.embedding_service.embed_query(query)
                search_results = self.semantic_memory.search_by_embedding(
                    query_embedding, top_k
                )

                for memory, score in search_results:
                    results.append(RetrievalResult(
                        content=memory.content,
                        score=score,
                        source="semantic",
                        memory_type=memory.memory_type.value,
                        metadata=memory.metadata,
                        timestamp=memory.updated_at.isoformat()
                    ))
            except Exception as e:
                logger.error(f"Embedding retrieval failed: {e}, falling back to content search")

        # 降级到内容检索
        if not results:
            search_results = self.semantic_memory.search_by_content(query, top_k)

            for memory, score in search_results:
                results.append(RetrievalResult(
                    content=memory.content,
                    score=score,
                    source="semantic",
                    memory_type=memory.memory_type.value,
                    metadata=memory.metadata,
                    timestamp=memory.updated_at.isoformat()
                ))

        return results

    async def _retrieve_episodic(
        self,
        query: str,
        top_k: int,
        session_id: Optional[str],
        use_embedding: bool
    ) -> List[RetrievalResult]:
        """从情景记忆检索"""
        results = []

        # 检索情景
        episode_results = self.episodic_memory.search_episodes(
            query, session_id, top_k
        )

        for episode, score in episode_results:
            # 获取情景的事件
            events = self.episodic_memory.get_episode_events(episode.id)

            # 提取关键事件内容
            event_contents = [e.description for e in events[:3]]  # 最多取前3个事件

            combined_content = f"{episode.title}\n{episode.description}\n"
            if episode.summary:
                combined_content += f"摘要: {episode.summary}\n"
            combined_content += "\n".join(event_contents)

            results.append(RetrievalResult(
                content=combined_content,
                score=score,
                source="episodic",
                metadata={
                    "episode_id": episode.id,
                    "event_count": len(events),
                    "tags": episode.tags
                },
                timestamp=episode.start_time.isoformat()
            ))

        return results

    async def retrieve_by_type(
        self,
        query: str,
        memory_type: MemoryType,
        top_k: int = 10,
        use_embedding: bool = False
    ) -> List[RetrievalResult]:
        """根据记忆类型检索"""
        results = []

        memories = self.semantic_memory.get_by_type(memory_type, top_k)

        if use_embedding and self.embedding_service:
            try:
                query_embedding = await self.embedding_service.embed_query(query)
                scored_memories = []
                for memory in memories:
                    if memory.embedding:
                        similarity = self._cosine_similarity(query_embedding, memory.embedding)
                        scored_memories.append((memory, similarity))
                scored_memories.sort(key=lambda x: x[1], reverse=True)
                memories = [m for m, _ in scored_memories[:top_k]]
            except Exception as e:
                logger.error(f"Embedding retrieval failed: {e}")

        for memory in memories:
            results.append(RetrievalResult(
                content=memory.content,
                score=memory.importance,
                source="semantic",
                memory_type=memory.memory_type.value,
                metadata=memory.metadata,
                timestamp=memory.updated_at.isoformat()
            ))

        return results

    async def retrieve_by_tags(
        self,
        tags: List[str],
        top_k: int = 10,
        match_all: bool = False
    ) -> List[RetrievalResult]:
        """根据标签检索"""
        results = []

        memories = self.semantic_memory.search_by_tags(tags, match_all, top_k)

        for memory in memories:
            results.append(RetrievalResult(
                content=memory.content,
                score=memory.importance,
                source="semantic",
                memory_type=memory.memory_type.value,
                metadata={"tags": memory.tags},
                timestamp=memory.updated_at.isoformat()
            ))

        return results

    async def retrieve_recent_context(
        self,
        session_id: str,
        short_term_memory: Optional[ShortTermMemory] = None,
        n_turns: int = 5
    ) -> List[RetrievalResult]:
        """检索最近的对话上下文"""
        results = []

        if short_term_memory:
            recent_turns = short_term_memory.get_recent_turns(n_turns)

            for turn in recent_turns:
                results.append(RetrievalResult(
                    content=f"{turn.role}: {turn.content}",
                    score=1.0,
                    source="short_term",
                    timestamp=turn.timestamp.isoformat()
                ))

        # 也可以从情景记忆中检索最近的情景
        recent_episodes = self.episodic_memory.get_recent_episodes(3)

        for episode in recent_episodes:
            if episode.session_id == session_id:
                events = self.episodic_memory.get_episode_events(episode.id)
                event_descriptions = [e.description for e in events]

                results.append(RetrievalResult(
                    content=f"情景: {episode.title}\n" + "\n".join(event_descriptions),
                    score=0.8,
                    source="episodic",
                    metadata={"episode_id": episode.id},
                    timestamp=episode.start_time.isoformat()
                ))

        return results

    async def retrieve_with_rerank(
        self,
        query: str,
        top_k: int = 10,
        reranker: Optional[Any] = None
    ) -> List[RetrievalResult]:
        """检索并重排序"""
        # 初始检索
        results = await self.retrieve(query, top_k * 2)

        # 如果有重排序器，使用它
        if reranker and results:
            try:
                documents = [r.content for r in results]
                rerank_scores = await reranker.rerank(query, documents)

                # 更新分数
                for i, score in enumerate(rerank_scores):
                    results[i].score = score

                # 重新排序
                results.sort(key=lambda r: r.score, reverse=True)
            except Exception as e:
                logger.error(f"Reranking failed: {e}")

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

    async def retrieve_by_time_range(
        self,
        query: str,
        start_time: str,
        end_time: str,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """根据时间范围检索"""
        from datetime import datetime

        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        results = []

        # 检索语义记忆
        for memory in self.semantic_memory.memories.values():
            if start_dt <= memory.updated_at <= end_dt:
                score = self._content_match_score(query, memory.content)
                if score > 0:
                    results.append(RetrievalResult(
                        content=memory.content,
                        score=score,
                        source="semantic",
                        memory_type=memory.memory_type.value,
                        timestamp=memory.updated_at.isoformat()
                    ))

        # 检索情景记忆
        for episode in self.episodic_memory.episodes.values():
            if start_dt <= episode.start_time <= end_dt:
                score = self._content_match_score(
                    query,
                    f"{episode.title} {episode.description}"
                )
                if score > 0:
                    results.append(RetrievalResult(
                        content=f"{episode.title}: {episode.description}",
                        score=score,
                        source="episodic",
                        timestamp=episode.start_time.isoformat()
                    ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _content_match_score(self, query: str, content: str) -> float:
        """简单的内容匹配分数"""
        query_lower = query.lower()
        content_lower = content.lower()

        if query_lower in content_lower:
            return 1.0

        query_words = set(query_lower.split())
        content_words = set(content_lower.split())

        if query_words & content_words:
            intersection = query_words & content_words
            return len(intersection) / len(query_words)

        return 0.0

    def format_retrieval_results(
        self,
        results: List[RetrievalResult],
        include_metadata: bool = False
    ) -> str:
        """格式化检索结果"""
        if not results:
            return "No relevant memories found."

        formatted_parts = []
        formatted_parts.append(f"Found {len(results)} relevant memories:\n")

        for i, result in enumerate(results, 1):
            formatted_parts.append(f"{i}. [{result.source.upper()}] (Score: {result.score:.2f})")
            formatted_parts.append(f"   {result.content}")

            if include_metadata and result.metadata:
                formatted_parts.append(f"   Metadata: {result.metadata}")

            if result.timestamp:
                formatted_parts.append(f"   Time: {result.timestamp}")

            formatted_parts.append("")

        return "\n".join(formatted_parts)
