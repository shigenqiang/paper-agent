"""
关系数据库存储 - Relational Storage

用于存储结构化数据:
- 用户画像 (UserProfile)
- 程序记忆 (ProceduralMemory)
- 实体关系 (EntityRelations)
- 记忆元数据索引
"""
import asyncio
import sqlite3
import json
import time
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager

from .types import MemoryType


@dataclass
class RelationalSchema:
    """关系数据库Schema定义"""
    user_profiles: str = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            preference_key TEXT NOT NULL,
            preference_value TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            updated_at REAL NOT NULL,
            source_interactions INTEGER DEFAULT 1
        )
    """

    procedures: str = """
        CREATE TABLE IF NOT EXISTS procedures (
            procedure_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            steps TEXT NOT NULL,
            success_rate REAL DEFAULT 1.0,
            total_executions INTEGER DEFAULT 0,
            successful_executions INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            last_used REAL NOT NULL,
            metadata TEXT
        )
    """

    entity_relations: str = """
        CREATE TABLE IF NOT EXISTS entity_relations (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            properties TEXT,
            created_at REAL NOT NULL
        )
    """

    relation_edges: str = """
        CREATE TABLE IF NOT EXISTS relation_edges (
            edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            properties TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (source_id) REFERENCES entity_relations(entity_id),
            FOREIGN KEY (target_id) REFERENCES entity_relations(entity_id)
        )
    """

    memory_index: str = """
        CREATE TABLE IF NOT EXISTS memory_index (
            memory_id TEXT PRIMARY KEY,
            memory_type TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            importance_level TEXT DEFAULT 'MEDIUM',
            tags TEXT,
            created_at REAL NOT NULL,
            last_accessed REAL NOT NULL,
            access_count INTEGER DEFAULT 0,
            retention_score REAL DEFAULT 1.0
        )
    """

    search_history: str = """
        CREATE TABLE IF NOT EXISTS search_history (
            search_id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            memory_type TEXT,
            results_count INTEGER,
            timestamp REAL NOT NULL
        )
    """


class RelationalStorage:
    """
    关系数据库存储

    支持:
    - SQLite本地存储
    - 用户画像管理
    - 程序记忆管理
    - 实体关系管理
    - 记忆索引和搜索历史
    """

    def __init__(self, storage_path: str = ".memory/relational.db"):
        self.storage_path = storage_path
        self._ensure_dir()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _ensure_dir(self) -> None:
        """确保目录存在"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.storage_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        """初始化数据库"""
        schema = RelationalSchema()
        conn = self._get_connection()

        # 创建所有表
        for table_sql in [
            schema.user_profiles,
            schema.procedures,
            schema.entity_relations,
            schema.relation_edges,
            schema.memory_index,
            schema.search_history
        ]:
            conn.execute(table_sql)

        conn.commit()

        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_index(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory_index(importance DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relation_source ON relation_edges(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relation_target ON relation_edges(target_id)")
        conn.commit()

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ========== 用户画像 ==========

    def upsert_user_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: Any,
        confidence: float = 0.5
    ) -> None:
        """更新用户偏好"""
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO user_profiles (user_id, preference_key, preference_value, confidence, updated_at, source_interactions)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    preference_key = excluded.preference_key,
                    preference_value = excluded.preference_value,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at,
                    source_interactions = source_interactions + 1
            """, (user_id, preference_key, json.dumps(preference_value), confidence, time.time()))

    def get_user_preferences(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有偏好"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                "user_id": row["user_id"],
                "preference_key": row["preference_key"],
                "preference_value": json.loads(row["preference_value"]),
                "confidence": row["confidence"],
                "updated_at": row["updated_at"],
                "source_interactions": row["source_interactions"]
            }
            for row in rows
        ]

    def get_user_preference(self, user_id: str, preference_key: str) -> Optional[Any]:
        """获取特定偏好"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT preference_value FROM user_profiles WHERE user_id = ? AND preference_key = ?",
            (user_id, preference_key)
        )
        row = cursor.fetchone()
        return json.loads(row["preference_value"]) if row else None

    # ========== 程序记忆 ==========

    def upsert_procedure(
        self,
        procedure_id: str,
        name: str,
        steps: List[Dict[str, Any]],
        description: str = "",
        metadata: Optional[Dict] = None
    ) -> None:
        """存储程序记忆"""
        now = time.time()
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO procedures (procedure_id, name, description, steps, created_at, last_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(procedure_id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    steps = excluded.steps,
                    last_used = excluded.last_used,
                    metadata = excluded.metadata
            """, (procedure_id, name, description, json.dumps(steps), now, now, json.dumps(metadata or {})))

    def get_procedure(self, procedure_id: str) -> Optional[Dict[str, Any]]:
        """获取程序记忆"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM procedures WHERE procedure_id = ?",
            (procedure_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "procedure_id": row["procedure_id"],
            "name": row["name"],
            "description": row["description"],
            "steps": json.loads(row["steps"]),
            "success_rate": row["success_rate"],
            "total_executions": row["total_executions"],
            "successful_executions": row["successful_executions"],
            "created_at": row["created_at"],
            "last_used": row["last_used"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
        }

    def record_procedure_execution(
        self,
        procedure_id: str,
        success: bool
    ) -> None:
        """记录程序执行结果"""
        with self.transaction() as conn:
            conn.execute("""
                UPDATE procedures SET
                    total_executions = total_executions + 1,
                    successful_executions = successful_executions + ?,
                    success_rate = CAST(successful_executions + ? AS REAL) / CAST(total_executions + 1 AS REAL),
                    last_used = ?
                WHERE procedure_id = ?
            """, (1 if success else 0, 1 if success else 0, time.time(), procedure_id))

    def list_procedures(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有程序记忆"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM procedures ORDER BY last_used DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [
            {
                "procedure_id": row["procedure_id"],
                "name": row["name"],
                "description": row["description"],
                "success_rate": row["success_rate"],
                "total_executions": row["total_executions"],
                "last_used": row["last_used"]
            }
            for row in rows
        ]

    # ========== 实体关系 ==========

    def upsert_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: Optional[Dict] = None
    ) -> None:
        """存储实体"""
        now = time.time()
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO entity_relations (entity_id, entity_type, properties, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    entity_type = excluded.entity_type,
                    properties = excluded.properties
            """, (entity_id, entity_type, json.dumps(properties or {}), now))

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """获取实体"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM entity_relations WHERE entity_id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
            "properties": json.loads(row["properties"]) if row["properties"] else {},
            "created_at": row["created_at"]
        }

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict] = None
    ) -> None:
        """添加关系边"""
        now = time.time()
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO relation_edges (source_id, target_id, relation_type, properties, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (source_id, target_id, relation_type, json.dumps(properties or {}), now))

    def get_relations(
        self,
        entity_id: str,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取实体的关系"""
        conn = self._get_connection()
        if relation_type:
            cursor = conn.execute("""
                SELECT * FROM relation_edges
                WHERE (source_id = ? OR target_id = ?) AND relation_type = ?
                ORDER BY created_at DESC
            """, (entity_id, entity_id, relation_type))
        else:
            cursor = conn.execute("""
                SELECT * FROM relation_edges
                WHERE source_id = ? OR target_id = ?
                ORDER BY created_at DESC
            """, (entity_id, entity_id))

        rows = cursor.fetchall()
        return [
            {
                "edge_id": row["edge_id"],
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "relation_type": row["relation_type"],
                "properties": json.loads(row["properties"]) if row["properties"] else {},
                "created_at": row["created_at"]
            }
            for row in rows
        ]

    def search_entities(
        self,
        entity_type: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索实体"""
        conn = self._get_connection()

        if entity_type and query:
            cursor = conn.execute("""
                SELECT * FROM entity_relations
                WHERE entity_type = ? AND properties LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (entity_type, f"%{query}%", limit))
        elif entity_type:
            cursor = conn.execute("""
                SELECT * FROM entity_relations
                WHERE entity_type = ?
                ORDER BY created_at DESC LIMIT ?
            """, (entity_type, limit))
        elif query:
            cursor = conn.execute("""
                SELECT * FROM entity_relations
                WHERE properties LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (f"%{query}%", limit))
        else:
            cursor = conn.execute("""
                SELECT * FROM entity_relations
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        return [
            {
                "entity_id": row["entity_id"],
                "entity_type": row["entity_type"],
                "properties": json.loads(row["properties"]) if row["properties"] else {},
                "created_at": row["created_at"]
            }
            for row in rows
        ]

    # ========== 记忆索引 ==========

    def index_memory(
        self,
        memory_id: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        importance_level: str = "MEDIUM",
        tags: Optional[List[str]] = None
    ) -> None:
        """索引记忆"""
        now = time.time()
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO memory_index (memory_id, memory_type, importance, importance_level, tags, created_at, last_accessed, access_count, retention_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1.0)
                ON CONFLICT(memory_id) DO UPDATE SET
                    importance = excluded.importance,
                    importance_level = excluded.importance_level,
                    tags = excluded.tags
            """, (memory_id, memory_type.value, importance, importance_level, json.dumps(tags or []), now, now))

    def update_memory_access(self, memory_id: str) -> None:
        """更新记忆访问"""
        now = time.time()
        with self.transaction() as conn:
            conn.execute("""
                UPDATE memory_index SET
                    last_accessed = ?,
                    access_count = access_count + 1
                WHERE memory_id = ?
            """, (now, memory_id))

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        conn = self._get_connection()

        # 总记忆数
        cursor = conn.execute("SELECT COUNT(*) as count FROM memory_index")
        total = cursor.fetchone()["count"]

        # 按类型统计
        cursor = conn.execute("""
            SELECT memory_type, COUNT(*) as count, AVG(importance) as avg_importance
            FROM memory_index
            GROUP BY memory_type
        """)
        by_type = {row["memory_type"]: {"count": row["count"], "avg_importance": row["avg_importance"]} for row in cursor.fetchall()}

        # 高重要性记忆
        cursor = conn.execute("SELECT COUNT(*) as count FROM memory_index WHERE importance >= 0.7")
        high_importance = cursor.fetchone()["count"]

        return {
            "total_memories": total,
            "by_type": by_type,
            "high_importance_count": high_importance
        }

    def cleanup_low_importance(self, threshold: float = 0.1) -> int:
        """清理低重要性记忆索引"""
        with self.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM memory_index WHERE importance < ?",
                (threshold,)
            )
            return cursor.rowcount

    # ========== 搜索历史 ==========

    def log_search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        results_count: int = 0
    ) -> None:
        """记录搜索历史"""
        with self.transaction() as conn:
            conn.execute("""
                INSERT INTO search_history (query, memory_type, results_count, timestamp)
                VALUES (?, ?, ?, ?)
            """, (query, memory_type, results_count, time.time()))

    def get_recent_searches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近搜索"""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM search_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [
            {
                "query": row["query"],
                "memory_type": row["memory_type"],
                "results_count": row["results_count"],
                "timestamp": row["timestamp"]
            }
            for row in rows
        ]

    def close(self) -> None:
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
