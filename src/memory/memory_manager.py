"""统一记忆管理器 - 整合长短期记忆"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from src.memory.short_term_memory import ShortTermMemory
from src.memory.semantic_memory import SemanticMemory, SemanticMemoryItem, MemoryType
from src.memory.episodic_memory import EpisodicMemory
from src.memory.conversation_summarizer import ConversationSummarizer
from src.memory.memory_storage import MemoryStorage
from src.memory.memory_retriever import MemoryRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class UnifiedMemoryManager:
    """统一记忆管理器 - 整合短期、长期和情景记忆"""

    def __init__(
        self,
        storage_dir: str = "data/memory",
        embedding_service: Optional[Any] = None
    ):
        # 初始化各种记忆
        self.short_term_memories: Dict[str, ShortTermMemory] = {}
        self.semantic_memory = SemanticMemory()
        self.episodic_memory = EpisodicMemory()

        # 初始化辅助组件
        self.storage = MemoryStorage(storage_dir)
        self.summarizer = ConversationSummarizer(
            self.semantic_memory,
            self.episodic_memory
        )
        self.retriever = MemoryRetriever(
            self.semantic_memory,
            self.episodic_memory,
            embedding_service
        )

        # 加载持久化的记忆
        self._load_persistent_memories()

        logger.info("Unified memory manager initialized")

    def _load_persistent_memories(self):
        """加载持久化的记忆"""
        # 加载语义记忆
        semantic_data = self.storage.load_semantic_memory()
        if semantic_data:
            try:
                for memory_id, memory_data in semantic_data["memories"].items():
                    memory = SemanticMemoryItem(
                        id=memory_data["id"],
                        content=memory_data["content"],
                        memory_type=MemoryType(memory_data["memory_type"]),
                        importance=memory_data["importance"],
                        confidence=memory_data["confidence"],
                        created_at=datetime.fromisoformat(memory_data["created_at"]),
                        updated_at=datetime.fromisoformat(memory_data["updated_at"]),
                        last_accessed=datetime.fromisoformat(memory_data["last_accessed"]),
                        access_count=memory_data["access_count"],
                        tags=memory_data["tags"],
                        embedding=memory_data["embedding"],
                        source=memory_data["source"],
                        metadata=memory_data["metadata"]
                    )
                    self.semantic_memory.memories[memory_id] = memory

                self.semantic_memory.tags_index = semantic_data.get("tags_index", {})
                logger.info("Loaded semantic memory from storage")
            except Exception as e:
                logger.error(f"Failed to load semantic memory: {e}")

        # 加载情景记忆
        episodic_data = self.storage.load_episodic_memory()
        if episodic_data:
            try:
                from src.memory.episodic_memory import Event, Episode

                # 加载事件
                for event_id, event_data in episodic_data["events"].items():
                    event = Event(**event_data)
                    self.episodic_memory.events[event_id] = event

                # 加载情景
                for episode_id, episode_data in episodic_data["episodes"].items():
                    episode = Episode(**episode_data)
                    self.episodic_memory.episodes[episode_id] = episode

                self.episodic_memory.session_episodes = episodic_data.get("session_episodes", {})
                self.episodic_memory.current_episode_id = episodic_data.get("current_episode_id")

                logger.info("Loaded episodic memory from storage")
            except Exception as e:
                logger.error(f"Failed to load episodic memory: {e}")

    # ============ 会话管理 ============

    def create_session(self, session_id: str) -> ShortTermMemory:
        """创建新会话"""
        if session_id in self.short_term_memories:
            return self.short_term_memories[session_id]

        # 尝试从存储加载
        loaded_memory = self.storage.load_short_term_memory(session_id)
        if loaded_memory:
            self.short_term_memories[session_id] = loaded_memory
            logger.info(f"Loaded existing session: {session_id}")
        else:
            self.short_term_memories[session_id] = ShortTermMemory(
                session_id=session_id
            )
            logger.info(f"Created new session: {session_id}")

        # 开始新的情景
        self.episodic_memory.start_episode(
            title=f"Session {session_id}",
            description=f"Conversation session {session_id}",
            session_id=session_id
        )

        return self.short_term_memories[session_id]

    def get_session(self, session_id: str) -> Optional[ShortTermMemory]:
        """获取会话"""
        return self.short_term_memories.get(session_id)

    def close_session(self, session_id: str, save: bool = True) -> bool:
        """关闭会话"""
        if session_id not in self.short_term_memories:
            return False

        # 结束情景
        self.episodic_memory.end_episode(session_id=session_id)

        # 保存对话到长期记忆
        if save:
            try:
                import asyncio
                asyncio.run(self.summarizer.save_conversation_to_memory(
                    self.short_term_memories[session_id],
                    session_id
                ))
                logger.info(f"Saved session {session_id} to long-term memory")
            except Exception as e:
                logger.error(f"Failed to save session: {e}")

        # 保存短期记忆
        self.storage.save_short_term_memory(
            self.short_term_memories[session_id],
            session_id
        )

        # 保存长期记忆
        self.storage.save_semantic_memory(self.semantic_memory)
        self.storage.save_episodic_memory(self.episodic_memory)

        # 从内存中移除短期记忆
        del self.short_term_memories[session_id]

        logger.info(f"Closed session: {session_id}")
        return True

    # ============ 对话管理 ============

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """添加消息到会话"""
        session = self.get_or_create_session(session_id)
        if not session:
            return False

        session.add_turn(role, content, metadata)

        # 添加事件到情景记忆
        self.episodic_memory.add_event(
            event_type=self._get_event_type_from_role(role),
            description=f"{role}: {content}",
            session_id=session_id
        )

        return True

    def _get_event_type_from_role(self, role: str):
        """根据角色获取事件类型"""
        from src.memory.episodic_memory import EventType
        if role == "user":
            return EventType.QUERY
        elif role == "assistant":
            return EventType.INTERACTION
        return EventType.INTERACTION

    def get_recent_messages(
        self,
        session_id: str,
        n: int = 5
    ) -> List[Dict[str, str]]:
        """获取最近的消息"""
        session = self.get_session(session_id)
        if not session:
            return []

        recent_turns = session.get_recent_turns(n)
        return [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat()
            }
            for turn in recent_turns
        ]

    # ============ 记忆检索 ============

    async def retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 10,
        include_short_term: bool = True
    ) -> List[RetrievalResult]:
        """检索相关记忆"""
        results = []

        # 从短期记忆检索
        if include_short_term and session_id:
            session = self.get_session(session_id)
            if session:
                recent_turns = session.get_recent_turns(5)
                for turn in recent_turns:
                    if query.lower() in turn.content.lower():
                        results.append(RetrievalResult(
                            content=f"{turn.role}: {turn.content}",
                            score=0.8,
                            source="short_term",
                            timestamp=turn.timestamp.isoformat()
                        ))

        # 从长期记忆检索
        long_term_results = await self.retriever.retrieve(query, top_k)
        results.extend(long_term_results)

        # 按分数排序
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:top_k]

    async def retrieve_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5
    ) -> str:
        """检索并格式化上下文"""
        results = await self.retrieve(query, session_id, top_k)
        return self.retriever.format_retrieval_results(results)

    # ============ 长期记忆管理 ============

    def add_semantic_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None
    ) -> str:
        """添加语义记忆"""
        return self.semantic_memory.add_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            source=source
        )

    def add_fact(
        self,
        fact: str,
        importance: float = 0.7,
        source: Optional[str] = None
    ) -> str:
        """添加事实"""
        return self.add_semantic_memory(
            content=fact,
            memory_type=MemoryType.FACT,
            importance=importance,
            source=source
        )

    def add_preference(
        self,
        preference: str,
        source: Optional[str] = None
    ) -> str:
        """添加用户偏好"""
        return self.add_semantic_memory(
            content=preference,
            memory_type=MemoryType.FACT,
            importance=0.9,
            tags=["user_preference"],
            source=source
        )

    def add_insight(
        self,
        insight: str,
        importance: float = 0.8,
        source: Optional[str] = None
    ) -> str:
        """添加洞察"""
        return self.add_semantic_memory(
            content=insight,
            memory_type=MemoryType.INSIGHT,
            importance=importance,
            source=source
        )

    # ============ 持久化 ============

    def save_all(self) -> bool:
        """保存所有记忆"""
        try:
            # 保存短期记忆
            for session_id, memory in self.short_term_memories.items():
                self.storage.save_short_term_memory(memory, session_id)

            # 保存长期记忆
            self.storage.save_semantic_memory(self.semantic_memory)
            self.storage.save_episodic_memory(self.episodic_memory)

            logger.info("Saved all memories")
            return True
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")
            return False

    def backup(self, backup_name: Optional[str] = None) -> bool:
        """备份记忆"""
        return self.storage.backup_memory(backup_name)

    def restore(self, backup_name: str) -> bool:
        """恢复记忆"""
        return self.storage.restore_memory(backup_name)

    # ============ 统计信息 ============

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "sessions": {
                "active": len(self.short_term_memories),
                "total": len(self.storage.list_sessions())
            },
            "semantic_memory": self.semantic_memory.get_stats(),
            "episodic_memory": self.episodic_memory.get_stats(),
            "storage": self.storage.get_storage_stats()
        }

    def get_or_create_session(self, session_id: str) -> ShortTermMemory:
        """获取或创建会话"""
        if session_id not in self.short_term_memories:
            return self.create_session(session_id)
        return self.short_term_memories[session_id]
