"""
统一记忆管理器 - Unified Memory Manager v4

基于"记忆系统与数据存储融合方案 v3.0"重构

架构:
┌──────────────────────────────────────────────────────────────┐
│                    UnifiedMemoryManager                       │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ShortTerm│ │ Session │ │LongTerm │ │Episodic │ │UserProf│ │
│  │(内存)  │ │(SQLite) │ │(SQLite) │ │(SQLite) │ │(SQLite)│ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
├──────────────────────────────────────────────────────────────┤
│  服务层: MemoryFlowController / RetrievalEngine             │
├──────────────────────────────────────────────────────────────┤
│  存储层: SQLite (主) + 内存 (缓存)                          │
└──────────────────────────────────────────────────────────────┘

流转规则:
| 阶段 | 触发条件 | 操作 |
|------|---------|------|
| STG→SESSION | 消息数≥30 OR 任务结束 | 批量存储到SQLite |
| STG→LONG_TERM | 重要性≥0.7 OR 用户标记 | 存入长期存储 |
| LONG_TERM→FORGOTTEN | retention<0.1 | 删除 |
"""

import asyncio
import time
import json
import sqlite3
import hashlib
import uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from collections import OrderedDict
import logging

from .types import MemoryType, MemoryEntry, ImportanceLevel

logger = logging.getLogger(__name__)

# ============================================================================
# 配置
# ============================================================================

@dataclass
class MemoryConfig:
    """记忆系统配置"""
    storage_path: str = ".memory"
    short_term_max_items: int = 100
    short_term_ttl_seconds: float = 3600
    session_max_entries: int = 500
    session_summary_trigger: int = 30
    long_term_persist_threshold: float = 0.7
    forgetting_threshold: float = 0.1
    importance_threshold: float = 0.3  # 召回时的最低重要性


# ============================================================================
# 短期记忆 - 内存 LRU + TTL
# ============================================================================

class ShortTermMemory:
    """
    短期记忆 - 当前任务上下文

    特点:
    - 保存在内存中
    - 基于LRU淘汰策略 + TTL过期
    - 与AgentContext深度绑定
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._items: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def add(
        self,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        async with self._lock:
            if key in self._items:
                item = self._items[key]
                item.content = value
                item.created_at = time.time()
                item.access_count = 0  # 重置访问
                if tags:
                    item.tags = tags
                if metadata:
                    item.metadata.update(metadata)
                self._update_importance(item, importance)
                self._items.move_to_end(key)
                return

            if len(self._items) >= self.config.short_term_max_items:
                self._evict_lru()

            entry = MemoryEntry(
                id=key,
                memory_type=MemoryType.SHORT_TERM,
                content=value,
                importance=importance,
                importance_level=ImportanceLevel.from_score(importance),
                tags=tags or [],
                metadata=metadata or {}
            )
            self._items[key] = entry

    def _update_importance(self, entry: MemoryEntry, importance: float) -> None:
        """更新重要性并重新计算等级"""
        entry.importance = importance
        entry.importance_level = ImportanceLevel.from_score(importance)

    async def get(
        self,
        key: str,
        default: Any = None,
        update_access: bool = True
    ) -> Any:
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                return default

            if time.time() - item.created_at > self.config.short_term_ttl_seconds:
                del self._items[key]
                return default

            if update_access:
                item.access_count += 1
                item.last_accessed = time.time()
                # 频繁访问增加重要性
                if item.access_count > 5:
                    item.importance = min(1.0, item.importance + 0.01)
                    item.importance_level = ImportanceLevel.from_score(item.importance)
                self._items.move_to_end(key)

            return item.content

    async def remove(self, key: str) -> None:
        async with self._lock:
            self._items.pop(key, None)

    async def keys(self) -> List[str]:
        async with self._lock:
            return list(self._items.keys())

    async def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        async with self._lock:
            items = list(self._items.values())
            items.reverse()
            return items[:n]

    async def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        async with self._lock:
            results = []
            for item in self._items.values():
                if query in item.tags:
                    results.append(item)
                    continue
                content_str = str(item.content).lower()
                if query.lower() in content_str:
                    results.append(item)
                if len(results) >= limit:
                    break
            return results

    def _evict_lru(self) -> None:
        if self._items:
            self._items.popitem(last=False)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._items),
            "max_items": self.config.short_term_max_items,
            "memory_type": MemoryType.SHORT_TERM.value
        }


# ============================================================================
# 会话记忆 - SQLite 持久化
# ============================================================================

class SessionMemory:
    """
    会话记忆 - 任务内跨Agent共享

    特点:
    - SQLite 持久化
    - 自动摘要生成
    - 支持将重要信息同步到长期记忆
    """

    def __init__(self, config: MemoryConfig, session_id: str, task_id: str):
        self.config = config
        self.session_id = session_id
        self.task_id = task_id
        self._conn = self._init_db()
        self._lock = asyncio.Lock()

    def _init_db(self) -> sqlite3.Connection:
        db_path = Path(self.config.storage_path) / "sessions.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                messages JSON DEFAULT '[]',
                summary TEXT,
                created_at REAL,
                last_updated REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                agent_id TEXT,
                role TEXT,
                content TEXT,
                metadata JSON,
                timestamp REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.commit()
        return conn

    async def store_message(
        self,
        agent_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        async with self._lock:
            msg_id = hashlib.md5(
                f"{self.session_id}{agent_id}{content}{time.time()}".encode()
            ).hexdigest()[:16]

            timestamp = time.time()

            # 插入消息
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO session_messages (session_id, agent_id, role, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.session_id, agent_id, role, content, json.dumps(metadata or {}), timestamp))

            self._conn.commit()
            return msg_id

    async def get_messages(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM session_messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (self.session_id, limit, offset))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "message_id": row["id"],
                "agent_id": row["agent_id"],
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"] or "{}"),
                "timestamp": row["timestamp"]
            })

        messages.reverse()
        return messages

    async def generate_summary(self) -> str:
        """生成会话摘要"""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT content, agent_id FROM session_messages
            WHERE session_id = ?
            ORDER BY timestamp
        """, (self.session_id,))

        messages = []
        for row in cursor.fetchall():
            messages.append(f"[{row['agent_id']}]: {row['content'][:100]}")

        if not messages:
            return ""

        summary = f"## Session Summary\n\nTotal messages: {len(messages)}\n\n"
        summary += "\n".join(messages[-10:])

        # 更新 sessions 表
        cursor.execute("""
            UPDATE sessions SET summary = ?, last_updated = ? WHERE session_id = ?
        """, (summary, time.time(), self.session_id))
        self._conn.commit()

        return summary

    def get_stats(self) -> Dict[str, Any]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM session_messages WHERE session_id = ?", (self.session_id,))
        count = cursor.fetchone()["cnt"]
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "message_count": count,
            "memory_type": MemoryType.SESSION.value
        }


# ============================================================================
# 长期记忆 - SQLite + 简化向量搜索
# ============================================================================

class LongTermMemory:
    """
    长期记忆 - 跨任务持久化

    特点:
    - SQLite 持久化
    - 基于关键词的相似度搜索
    - 重要性 + 时间衰减
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._conn = self._init_db()
        self._lock = asyncio.Lock()

    def _init_db(self) -> sqlite3.Connection:
        db_path = Path(self.config.storage_path) / "long_term.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                content TEXT,
                importance REAL DEFAULT 0.5,
                importance_level TEXT DEFAULT 'MEDIUM',
                tags JSON DEFAULT '[]',
                metadata JSON DEFAULT '{}',
                retention_score REAL DEFAULT 1.0,
                access_count INTEGER DEFAULT 0,
                created_at REAL,
                last_accessed REAL,
                sm2_interval_days REAL DEFAULT 1.0,
                sm2_ease_factor REAL DEFAULT 2.5,
                sm2_repetitions INTEGER DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)")
        conn.commit()
        return conn

    async def remember(
        self,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        persist: bool = True,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if not persist:
            return

        async with self._lock:
            memory_id = hashlib.md5(key.encode()).hexdigest()[:16]
            now = time.time()
            level = ImportanceLevel.from_score(importance)

            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO memories (
                    memory_id, key, content, importance, importance_level,
                    tags, metadata, retention_score, access_count,
                    created_at, last_accessed, sm2_interval_days,
                    sm2_ease_factor, sm2_repetitions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id, key, str(value), importance, level.value,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(metadata or {}, ensure_ascii=False),
                1.0, 0, now, now, 1.0, 2.5, 0
            ))
            self._conn.commit()

    async def recall(self, key: str) -> Optional[Any]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE key = ? LIMIT 1", (key,))
        row = cursor.fetchone()

        if row:
            # 更新访问
            cursor.execute("""
                UPDATE memories SET access_count = access_count + 1, last_accessed = ?
                WHERE memory_id = ?
            """, (time.time(), row["memory_id"]))
            self._conn.commit()
            return row["content"]

        return None

    async def search(
        self,
        query: str,
        limit: int = 10,
        tags: Optional[List[str]] = None,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        cursor = self._conn.cursor()
        sql = "SELECT * FROM memories WHERE (key LIKE ? OR content LIKE ?) AND importance >= ?"
        params = [f"%{query}%", f"%{query}%", min_importance]

        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")

        sql += " ORDER BY importance DESC, last_accessed DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)

        entries = []
        for row in cursor.fetchall():
            # 安全转换 importance_level（可能是字符串或浮点数）
            il_value = float(row["importance_level"])
            entry = MemoryEntry(
                id=row["memory_id"],
                memory_type=MemoryType.LONG_TERM,
                content=row["content"],
                importance=float(row["importance"]),
                importance_level=ImportanceLevel(il_value),
                tags=json.loads(row["tags"] or "[]"),
                metadata=json.loads(row["metadata"] or "{}"),
                access_count=int(row["access_count"]),
                created_at=float(row["created_at"]),
                last_accessed=float(row["last_accessed"])
            )
            entry.sm2_interval_days = row["sm2_interval_days"]
            entry.sm2_ease_factor = row["sm2_ease_factor"]
            entry.sm2_repetitions = row["sm2_repetitions"]
            entries.append(entry)

        return entries

    async def delete(self, key: str) -> bool:
        async with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM memories WHERE key = ?", (key,))
            self._conn.commit()
            return cursor.rowcount > 0

    async def list_all(self) -> List[str]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT key FROM memories")
        return [row["key"] for row in cursor.fetchall()]

    async def get_stats(self) -> Dict[str, Any]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM memories")
        count = cursor.fetchone()["cnt"]
        return {
            "total_memories": count,
            "memory_type": MemoryType.LONG_TERM.value
        }


# ============================================================================
# 情景记忆 - SQLite
# ============================================================================

class EpisodicMemory:
    """情景记忆 - 记录Agent执行轨迹"""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        db_path = Path(self.config.storage_path) / "episodes.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                agent_id TEXT,
                action TEXT,
                result TEXT,
                context_snapshot TEXT,
                timestamp REAL,
                duration_ms REAL,
                success INTEGER
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_task ON episodes(task_id)")
        conn.commit()
        return conn

    async def record_episode(
        self,
        task_id: str,
        agent_id: str,
        action: str,
        result: Any,
        context_snapshot: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        episode_id = hashlib.md5(f"{task_id}{action}{time.time()}".encode()).hexdigest()[:16]

        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO episodes (
                episode_id, task_id, agent_id, action, result,
                context_snapshot, timestamp, duration_ms, success
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode_id, task_id, agent_id, action, str(result),
            json.dumps(context_snapshot or {}, ensure_ascii=False),
            time.time(), duration_ms, 1 if success else 0
        ))
        self._conn.commit()

        return episode_id

    def get_stats(self) -> Dict[str, Any]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM episodes")
        return {
            "total_episodes": cursor.fetchone()["cnt"],
            "memory_type": MemoryType.EPISODIC.value
        }


# ============================================================================
# 用户画像 - SQLite
# ============================================================================

class UserProfileMemory:
    """用户画像 - 存储用户偏好"""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        db_path = Path(self.config.storage_path) / "user_profiles.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT,
                confidence REAL DEFAULT 0.5,
                updated_at REAL,
                UNIQUE(user_id, preference_key)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prefs_user ON preferences(user_id)")
        conn.commit()
        return conn

    def upsert_preference(self, user_id: str, key: str, value: Any, confidence: float = 0.5) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO preferences (user_id, preference_key, preference_value, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, key, json.dumps(value, ensure_ascii=False), confidence, time.time()))
        self._conn.commit()

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT preference_key, preference_value FROM preferences WHERE user_id = ?", (user_id,))
        prefs = {}
        for row in cursor.fetchall():
            try:
                prefs[row["preference_key"]] = json.loads(row["preference_value"])
            except:
                prefs[row["preference_key"]] = row["preference_value"]
        return prefs


# ============================================================================
# 遗忘控制器
# ============================================================================

class ForgettingController:
    """遗忘控制器 - 清理低重要性记忆"""

    def __init__(self, long_term_memory: LongTermMemory, config: MemoryConfig):
        self.long_term = long_term_memory
        self.config = config

    async def cleanup(self, threshold: float = None) -> Dict[str, Any]:
        """
        清理已遗忘的记忆

        基于 Ebbinghaus 遗忘曲线: retention = importance * e^(-t/S)

        其中 S 根据 importance_level 确定：
        - CRITICAL: ∞ (永不遗忘)
        - HIGH: 7天
        - MEDIUM: 1天
        - LOW: 1小时
        """
        import math

        threshold = threshold or self.config.forgetting_threshold
        cursor = self.long_term._conn.cursor()

        # 获取所有记忆
        cursor.execute("""
            SELECT memory_id, importance, importance_level, last_accessed
            FROM memories
        """)

        deleted = 0
        current_time = time.time()

        for row in cursor.fetchall():
            importance = row["importance"]
            last_accessed = row["last_accessed"]
            t = current_time - last_accessed

            # 获取 S 参数
            try:
                level = ImportanceLevel(float(row["importance_level"]))
            except (ValueError, TypeError):
                level = ImportanceLevel.MEDIUM

            S = level.get_strength_seconds()

            # CRITICAL 永不删除
            if S == float('inf'):
                continue

            # 计算保留分数
            retention = importance * math.exp(-t / S)

            if retention < threshold:
                cursor.execute("DELETE FROM memories WHERE memory_id = ?", (row["memory_id"],))
                deleted += 1

        self.long_term._conn.commit()
        return {"deleted": deleted}


# ============================================================================
# 统一记忆管理器
# ============================================================================

class UnifiedMemoryManager:
    """
    统一记忆管理器

    整合所有记忆层，提供统一接口
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.config.storage_path = str(Path(self.config.storage_path).expanduser().absolute())

        # 初始化各层记忆
        self.short_term = ShortTermMemory(self.config)
        self.long_term = LongTermMemory(self.config)
        self.episodic = EpisodicMemory(self.config)
        self.user_profile = UserProfileMemory(self.config)

        # 会话记忆（需要 task_id 初始化）
        self._session_memory: Optional[SessionMemory] = None
        self._current_task_id: Optional[str] = None

        # 遗忘控制器
        self.forgetting = ForgettingController(self.long_term, self.config)

        # 状态
        self._lock = asyncio.Lock()
        self._last_retrieval_time: float = 0
        self._messages_since_retrieval: int = 0

    def init_session(self, task_id: str, session_id: Optional[str] = None) -> SessionMemory:
        """初始化会话记忆"""
        if session_id is None:
            session_id = f"session_{task_id}_{int(time.time())}"

        self._session_memory = SessionMemory(self.config, session_id, task_id)
        self._current_task_id = task_id
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
        """存储记忆"""
        async with self._lock:
            if memory_type == MemoryType.SHORT_TERM:
                await self.short_term.add(key, value, tags, importance, metadata)
                if persist:
                    await self.long_term.remember(key, value, tags, persist=True, importance=importance, metadata=metadata)

            elif memory_type == MemoryType.SESSION:
                if self._session_memory:
                    await self._session_memory.store_message(
                        agent_id=metadata.get("agent_id", "system") if metadata else "system",
                        role=metadata.get("role", "system") if metadata else "system",
                        content=str(value),
                        metadata=metadata
                    )

            elif memory_type == MemoryType.LONG_TERM:
                await self.long_term.remember(key, value, tags, persist=True, importance=importance, metadata=metadata)

            elif memory_type == MemoryType.USER_PROFILE:
                user_id = metadata.get("user_id", "default") if metadata else "default"
                self.user_profile.upsert_preference(user_id, key, value, importance)

    async def recall_direct(self, key: str) -> Optional[Any]:
        """直接通过键检索"""
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

    async def recall(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """检索记忆"""
        memory_types = memory_types or [MemoryType.LONG_TERM]
        results = []

        for mem_type in memory_types:
            if mem_type == MemoryType.SHORT_TERM:
                short_results = await self.short_term.search(query, limit)
                results.extend(short_results)
            elif mem_type == MemoryType.LONG_TERM:
                long_results = await self.long_term.search(
                    query, limit, min_importance=self.config.importance_threshold
                )
                results.extend(long_results)

        return results[:limit]

    async def recall_with_decay(
        self,
        query: str,
        top_k: int = 3,
        enable_decay: bool = True
    ) -> List[MemoryEntry]:
        """
        带遗忘曲线的时间衰减召回

        基于 Ebbinghaus 公式: retention = importance * e^(-t/S)

        改进(v4.0):
        1. 从长期记忆检索双倍数量
        2. 计算每个记忆的保留分数
        3. 低于阈值(0.1)过滤
        4. 按 final_score = importance * retention 排序
        5. 返回 top_k

        Args:
            query: 查询字符串
            top_k: 返回数量
            enable_decay: 是否启用时间衰减

        Returns:
            排序后的记忆列表
        """
        import math

        # 1. 从长期记忆检索双倍数量（给筛选留余地）
        memories = await self.long_term.search(query, limit=top_k * 2)

        if not memories:
            return []

        current_time = time.time()
        scored = []

        for mem in memories:
            importance = mem.importance

            # 重要性阈值过滤
            if importance < self.config.importance_threshold:
                continue

            if not enable_decay:
                scored.append((importance, mem))
                continue

            # 计算时间衰减保留分数
            t = current_time - mem.last_accessed
            S = mem.importance_level.get_strength_seconds()

            if S == float('inf'):
                retention = importance
            else:
                retention = importance * math.exp(-t / S)

            # 阈值过滤
            if retention < self.config.forgetting_threshold:
                continue

            # 最终分数 = 基础分数 * 保留分数
            final_score = importance * retention
            scored.append((final_score, mem))

        # 按分数排序
        scored.sort(key=lambda x: x[0], reverse=True)

        return [mem for _, mem in scored[:top_k]]

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
        """记录执行情节"""
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
        """为Agent生成上下文字符串"""
        parts = []

        # 添加会话上下文
        if self._session_memory:
            messages = await self._session_memory.get_messages(limit=20)
            if messages:
                parts.append(f"## Session: {self._session_memory.session_id}\n")
                for msg in messages[-10:]:
                    parts.append(f"[{msg['agent_id']}] {msg['content'][:100]}")

        # 添加短期记忆
        recent = await self.short_term.get_recent(n=5)
        if recent:
            parts.append("\n## Recent Memories")
            for entry in recent:
                parts.append(f"- {entry.content[:80]}")

        return "\n\n".join(parts)

    async def run_maintenance(self) -> Dict[str, Any]:
        """运行维护任务"""
        cleanup_result = await self.forgetting.cleanup()
        return {
            "forgetting_cleaned": cleanup_result.get("deleted", 0),
            "timestamp": time.time()
        }

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像"""
        return self.user_profile.get_preferences(user_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计"""
        return {
            "short_term": self.short_term.get_stats(),
            "long_term": {},  # long_term.get_stats 是协程，如需调用应使用 await
            "episodic": self.episodic.get_stats() if hasattr(self.episodic, 'get_stats') else {},
            "session": self._session_memory.get_stats() if self._session_memory else {},
            "current_task": self._current_task_id
        }


# ============================================================================
# 全局单例
# ============================================================================

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
