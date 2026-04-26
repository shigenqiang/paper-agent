"""
统一记忆管理器 - Unified Memory Manager

整合所有记忆层，提供统一接口

架构:
┌────────────────────────────────────────────────────────────────┐
│                      UnifiedMemoryManager                       │
├────────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │ShortTerm  │ │ Session    │ │ LongTerm   │ │ Episodic   │  │
│  │Memory     │ │ Memory     │ │ Memory     │ │ Memory     │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │
│  ┌────────────┐ ┌────────────┐                                 │
│  │UserProfile│ │ Procedural │                                 │
│  │Memory     │ │ Memory     │                                 │
│  └────────────┘ └────────────┘                                 │
├────────────────────────────────────────────────────────────────┤
│                        核心服务层                               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │Extractor  │ │ Summarizer │ │ Retrieval  │ │ Forgetting │  │
│  │           │ │            │ │ Engine     │ │ Controller │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │
└────────────────────────────────────────────────────────────────┘
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from .types import MemoryType, MemoryEntry, ImportanceLevel
from .short_term import ShortTermMemory, ShortTermMemoryConfig
from .session import SessionMemory, SessionConfig
from .long_term import LongTermMemory, VectorStore, GraphStore
from .episodic import EpisodicMemory
from .relational import RelationalStorage
from .retrieval import (
    EnhancedRetrievalEngine,
    RetrievalQuery,
    RetrievalResult,
    QueryType
)
from .services import (
    MemoryExtractor,
    SummaryGenerator,
    RetrievalEngine,
    ForgettingController
)


@dataclass
class UnifiedMemoryConfig:
    """统一记忆配置"""
    # 存储路径
    storage_path: str = ".memory"

    # 短期记忆配置
    short_term_max_items: int = 100
    short_term_ttl_seconds: float = 3600

    # 会话配置
    session_max_entries: int = 500
    session_summary_trigger: int = 30

    # 长期记忆配置
    long_term_persist_threshold: float = 0.7

    # 遗忘配置
    forgetting_threshold: float = 0.1
    forgetting_interval_seconds: float = 3600

    # LLM客户端 (可选)
    llm_client: Optional[Any] = None

    # 检索配置
    enable_enhanced_retrieval: bool = True
    retrieval_interval_seconds: float = 60
    min_messages_before_retrieval: int = 5


class UnifiedMemoryManager:
    """
    统一记忆管理器

    功能:
    - 整合所有记忆层
    - 提供统一接口
    - 自动协调各层之间的数据流动
    """

    def __init__(self, config: Optional[UnifiedMemoryConfig] = None):
        self.config = config or UnifiedMemoryConfig()

        # 初始化各层记忆
        self.short_term = ShortTermMemory(
            config=ShortTermMemoryConfig(
                max_items=self.config.short_term_max_items,
                ttl_seconds=self.config.short_term_ttl_seconds
            )
        )

        # 会话记忆 (需要task_id初始化，这里延迟初始化)
        self._session_memory: Optional[SessionMemory] = None

        # 长期记忆
        self.long_term = LongTermMemory(
            vector_store=VectorStore(
                storage_path=f"{self.config.storage_path}/vectors"
            ),
            graph_store=GraphStore(
                storage_path=f"{self.config.storage_path}/graphs"
            )
        )

        # 情景记忆
        self.episodic = EpisodicMemory(
            storage_path=f"{self.config.storage_path}/episodes"
        )

        # 关系数据库存储 (用户画像、程序记忆、实体关系)
        self.relational = RelationalStorage(
            storage_path=f"{self.config.storage_path}/memory.db"
        )

        # 增强检索引擎
        if self.config.enable_enhanced_retrieval:
            self.enhanced_retriever = EnhancedRetrievalEngine(
                long_term_memory=self.long_term,
                relational_store=self.relational
            )
        else:
            self.enhanced_retriever = None

        # 初始化核心服务
        self.extractor = MemoryExtractor(llm_client=self.config.llm_client)
        self.summarizer = SummaryGenerator(llm_client=self.config.llm_client)
        self.retriever = RetrievalEngine(
            long_term_memory=self.long_term,
            graph_store=self.long_term.graph_store
        )
        self.forgetting = ForgettingController(
            long_term_memory=self.long_term,
            base_retention_time=86400
        )

        # 状态
        self._initialized = False
        self._current_task_id: Optional[str] = None
        self._lock = asyncio.Lock()
        self._last_retrieval_time: float = 0
        self._messages_since_retrieval: int = 0

    def init_session(self, task_id: str, session_id: Optional[str] = None) -> SessionMemory:
        """
        初始化会话记忆

        Args:
            task_id: 任务ID
            session_id: 会话ID (默认自动生成)

        Returns:
            SessionMemory实例
        """
        if session_id is None:
            session_id = f"session_{task_id}_{int(time.time())}"

        self._session_memory = SessionMemory(
            config=SessionConfig(
                session_id=session_id,
                task_id=task_id
            ),
            long_term_memory=self.long_term
        )
        self._current_task_id = task_id
        self._initialized = True

        return self._session_memory

    async def remember(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        persist: bool = False,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        存储记忆

        Args:
            key: 记忆键
            value: 记忆值
            memory_type: 记忆类型
            persist: 是否持久化到长期记忆
            importance: 重要性 (0.0-1.0)
            tags: 标签列表
            metadata: 额外元数据
        """
        async with self._lock:
            if memory_type == MemoryType.SHORT_TERM:
                await self.short_term.add(key, value, tags, importance, metadata)

                # 如果标记为持久化，同时存入长期记忆
                if persist:
                    await self.long_term.remember(
                        key=key, value=value, tags=tags,
                        persist=True, importance=importance, metadata=metadata
                    )

            elif memory_type == MemoryType.SESSION:
                if self._session_memory:
                    await self._session_memory.store_message(
                        agent_id=metadata.get("agent_id", "system") if metadata else "system",
                        role=metadata.get("role", "system") if metadata else "system",
                        content=str(value),
                        metadata=metadata
                    )

            elif memory_type == MemoryType.LONG_TERM:
                await self.long_term.remember(
                    key=key, value=value, tags=tags,
                    persist=True, importance=importance, metadata=metadata
                )

            elif memory_type == MemoryType.USER_PROFILE:
                user_id = metadata.get("user_id", "default") if metadata else "default"
                self.relational.upsert_user_preference(
                    user_id=user_id,
                    preference_key=key,
                    preference_value=value
                )

            elif memory_type == MemoryType.PROCEDURAL:
                steps = value if isinstance(value, list) else [value]
                self.relational.upsert_procedure(
                    procedure_id=key,
                    name=metadata.get("name", key) if metadata else key,
                    steps=steps,
                    description=metadata.get("description", "") if metadata else ""
                )

    async def recall(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        检索记忆

        Args:
            query: 查询字符串
            memory_types: 记忆类型过滤
            limit: 返回数量限制

        Returns:
            匹配的MemoryEntry列表
        """
        memory_types = memory_types or [MemoryType.LONG_TERM]

        results = []
        for mem_type in memory_types:
            if mem_type == MemoryType.SHORT_TERM:
                short_results = await self.short_term.search(query, limit)
                results.extend(short_results)

            elif mem_type == MemoryType.LONG_TERM:
                long_results = await self.long_term.search(query, limit)
                results.extend(long_results)

            elif mem_type == MemoryType.SESSION and self._session_memory:
                messages = await self._session_memory.get_messages(limit=limit)
                for msg in messages:
                    results.append(MemoryEntry(
                        id=msg.get("message_id", ""),
                        memory_type=MemoryType.SESSION,
                        content=msg.get("content", ""),
                        metadata=msg
                    ))

        return results[:limit]

    async def recall_direct(self, key: str) -> Optional[Any]:
        """
        直接通过键检索

        Args:
            key: 记忆键

        Returns:
            记忆值或None
        """
        # 先查短期记忆
        value = await self.short_term.get(key, update_access=False)
        if value is not None:
            return value

        # 再查长期记忆
        value = await self.long_term.recall(key)
        if value is not None:
            # 升级到短期记忆
            await self.short_term.add(key, value)
            return value

        return None

    async def search(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        高级搜索

        Args:
            query: 搜索查询
            memory_types: 记忆类型过滤
            filters: 过滤条件
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        return await self.retriever.retrieve(
            query=query,
            memory_types=memory_types,
            limit=limit,
            filters=filters
        )

    async def record_episode(
        self,
        agent_id: str,
        action: str,
        result: Any,
        context_snapshot: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """
        记录执行情节

        Args:
            agent_id: Agent ID
            action: 执行的动作
            result: 执行结果
            context_snapshot: 上下文快照
            duration_ms: 执行时长
            success: 是否成功
            error: 错误信息

        Returns:
            episode_id
        """
        task_id = self._current_task_id or "unknown"

        return await self.episodic.record_episode(
            task_id=task_id,
            agent_id=agent_id,
            action=action,
            result=result,
            context_snapshot=context_snapshot,
            duration_ms=duration_ms,
            success=success,
            error=error
        )

    async def get_context_for_agent(
        self,
        agent_id: str,
        max_tokens: int = 4096,
        force_retrieve: bool = False
    ) -> str:
        """
        为Agent生成上下文字符串

        Args:
            agent_id: Agent ID
            max_tokens: 最大token数
            force_retrieve: 强制检索

        Returns:
            格式化的上下文字符串
        """
        parts = []
        context = {
            "short_term": self.short_term,
            "session": self._session_memory,
            "episodic": self.episodic,
            "messages": await self.short_term.keys(),
            "last_retrieval_time": self._last_retrieval_time,
            "messages_since_retrieval": self._messages_since_retrieval,
            "force_retrieve": force_retrieve
        }

        # 检查是否应该触发增强检索
        should_retrieve = False
        if self.enhanced_retriever:
            should_retrieve, reason = self.enhanced_retriever.should_retrieve(context)
            if should_retrieve or force_retrieve:
                # 执行增强检索
                retrieval_query = RetrievalQuery(
                    text=f"task {self._current_task_id}" if self._current_task_id else agent_id,
                    limit=10
                )

                results = await self.enhanced_retriever.retrieve(
                    query=retrieval_query,
                    context=context
                )

                if results:
                    parts.append("## 相关记忆\n")
                    for result in results[:5]:
                        parts.append(f"- [{result.entry.memory_type.value}] {str(result.entry.content)[:100]}")

                self._last_retrieval_time = time.time()
                self._messages_since_retrieval = 0

        # 添加短期记忆上下文
        context_summary = await self.short_term.get_context_summary()
        if context_summary:
            parts.append(context_summary)

        # 添加会话上下文
        if self._session_memory:
            session_context = await self._session_memory.get_context_for_agent(
                agent_id, max_messages=20
            )
            if session_context:
                parts.append(session_context)

        # 添加相关记忆
        if self._current_task_id:
            task_context = await self.retriever.get_context_for_agent(
                agent_id=agent_id,
                task_id=self._current_task_id,
                max_tokens=max_tokens
            )
            if task_context:
                parts.append(task_context)

        self._messages_since_retrieval += 1

        return "\n\n".join(parts)

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像"""
        prefs = self.relational.get_user_preferences(user_id)
        return {p["preference_key"]: p["preference_value"] for p in prefs}

    def get_procedure(self, procedure_id: str) -> Optional[Dict[str, Any]]:
        """获取程序记忆"""
        return self.relational.get_procedure(procedure_id)

    def record_procedure_execution(self, procedure_id: str, success: bool) -> None:
        """记录程序执行结果"""
        self.relational.record_procedure_execution(procedure_id, success)

    async def run_maintenance(self) -> Dict[str, Any]:
        """
        运行维护任务

        - 清理低重要性记忆
        - 生成必要摘要

        Returns:
            维护统计
        """
        stats = {
            "forgetting_cleaned": 0,
            "summary_generated": False,
            "timestamp": time.time()
        }

        # 遗忘清理
        cleanup_result = await self.forgetting.cleanup(
            threshold=self.config.forgetting_threshold
        )
        stats["forgetting_cleaned"] = cleanup_result.get("deleted", 0)

        return stats

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计"""
        return {
            "short_term": self.short_term.get_stats(),
            "long_term": self.long_term.get_stats() if hasattr(self.long_term, 'get_stats') else {},
            "episodic": self.episodic.get_stats(),
            "session": self._session_memory.get_stats() if self._session_memory else {},
            "relational": self.relational.get_memory_stats(),
            "current_task": self._current_task_id,
            "retrieval_stats": {
                "last_retrieval_time": self._last_retrieval_time,
                "messages_since_retrieval": self._messages_since_retrieval
            }
        }


# 全局单例
_memory_manager: Optional[UnifiedMemoryManager] = None


def get_memory_manager() -> UnifiedMemoryManager:
    """获取全局记忆管理器"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = UnifiedMemoryManager()
    return _memory_manager


def init_memory_for_task(task_id: str) -> UnifiedMemoryManager:
    """为特定任务初始化记忆管理器"""
    manager = get_memory_manager()
    manager.init_session(task_id)
    return manager
