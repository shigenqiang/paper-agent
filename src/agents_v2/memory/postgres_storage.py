"""
PostgreSQL向量存储集成

使用PostgreSQL + pgvector实现向量存储和相似度搜索
"""
import os
import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# PostgreSQL相关导入
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from pgvector.psycopg2 import register_vector
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


@dataclass
class EmbeddingRecord:
    """嵌入记录"""
    id: int
    memory_id: str
    content: str
    embedding: List[float]
    memory_type: str
    importance: float
    created_at: datetime


class ConnectionPool:
    """
    PostgreSQL连接池

    管理数据库连接的复用
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "memory_db",
        user: str = None,
        password: str = None,
        pool_size: int = 10
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "postgres")
        self.pool_size = pool_size
        self._pool: List[PostgresConnection] = []
        self._available: asyncio.Queue = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """初始化连接池"""
        self._available = asyncio.Queue(maxsize=self.pool_size)

        for _ in range(self.pool_size):
            conn = PostgresConnection(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            conn.connect()
            await self._available.put(conn)

    async def acquire(self) -> PostgresConnection:
        """获取连接"""
        conn = await self._available.get()
        return conn

    async def release(self, conn: PostgresConnection) -> None:
        """释放连接"""
        await self._available.put(conn)

    async def close_all(self) -> None:
        """关闭所有连接"""
        while not self._available.empty():
            try:
                conn = self._available.get_nowait()
                conn.close()
            except asyncio.QueueEmpty:
                break


class PostgresConnection:
    """
    PostgreSQL连接管理器

    支持:
    - 普通查询
    - 向量操作
    - 事务管理
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "memory_db",
        user: str = None,
        password: str = None
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "postgres")
        self._connection = None
        self._cursor = None

    def _get_connection_string(self) -> str:
        """获取连接字符串"""
        return f"host={self.host} port={self.port} dbname={self.database} user={self.user} password={self.password}"

    def connect(self) -> None:
        """建立连接"""
        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 or pgvector not installed. Run: pip install psycopg2-binary pgvector")

        self._connection = psycopg2.connect(self._get_connection_string())
        register_vector(self._connection)
        self._cursor = self._connection.cursor(cursor_factory=RealDictCursor)

    def close(self) -> None:
        """关闭连接"""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()

    async def execute(self, query: str, params: tuple = None) -> None:
        """执行查询"""
        if not self._connection:
            self.connect()

        try:
            if params:
                self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            raise e

    async def fetch(self, query: str, params: tuple = None) -> List[Dict]:
        """获取查询结果"""
        if not self._connection:
            self.connect()

        try:
            if params:
                self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)
            results = self._cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            raise e

    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """获取单条结果"""
        results = await self.fetch(query, params)
        return results[0] if results else None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class VectorStorage:
    """
    PostgreSQL向量存储

    功能:
    - 存储向量嵌入
    - 相似度搜索
    - HNSW索引支持
    """

    def __init__(self, connection: PostgresConnection, dimension: int = 1536):
        self.connection = connection
        self.dimension = dimension

    async def initialize(self) -> None:
        """初始化表结构"""
        # 启用pgvector扩展
        await self.connection.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # 创建嵌入表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            memory_id VARCHAR(255) UNIQUE NOT NULL,
            content TEXT,
            embedding vector(%s),
            memory_type VARCHAR(50) DEFAULT 'unknown',
            importance FLOAT DEFAULT 0.5,
            tags TEXT[],
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        await self.connection.execute(create_table_sql, (self.dimension,))

        # 创建HNSW索引
        create_index_sql = """
        CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx
        ON embeddings USING HNSW (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
        await self.connection.execute(create_index_sql)

        # 创建普通索引
        await self.connection.execute("""
        CREATE INDEX IF NOT EXISTS embeddings_memory_id_idx ON embeddings(memory_id);
        """)
        await self.connection.execute("""
        CREATE INDEX IF NOT EXISTS embeddings_memory_type_idx ON embeddings(memory_type);
        """)

    async def add(
        self,
        memory_id: str,
        content: str,
        embedding: List[float],
        memory_type: str = "unknown",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        添加向量

        Args:
            memory_id: 记忆ID
            content: 内容文本
            embedding: 向量
            memory_type: 记忆类型
            importance: 重要性
            tags: 标签
            metadata: 元数据

        Returns:
            是否成功
        """
        insert_sql = """
        INSERT INTO embeddings (memory_id, content, embedding, memory_type, importance, tags, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (memory_id) DO UPDATE SET
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            memory_type = EXCLUDED.memory_type,
            importance = EXCLUDED.importance,
            tags = EXCLUDED.tags,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """
        params = (
            memory_id,
            content,
            embedding,
            memory_type,
            importance,
            tags or [],
            json.dumps(metadata) if metadata else "{}"
        )

        try:
            await self.connection.execute(insert_sql, params)
            return True
        except Exception as e:
            print(f"Error adding vector: {e}")
            return False

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        ef_search: int = 64
    ) -> List[Dict]:
        """
        相似度搜索

        Args:
            query_vector: 查询向量
            limit: 返回数量
            memory_type: 记忆类型过滤
            min_importance: 最小重要性
            ef_search: 搜索参数(越大越精确但越慢)

        Returns:
            匹配的记录列表
        """
        # 构建查询
        search_sql = """
        SELECT memory_id, content, 1 - (embedding <=> %s) as similarity,
               memory_type, importance, tags, metadata, created_at
        FROM embeddings
        WHERE importance >= %s
        """

        params = [query_vector, min_importance]

        if memory_type:
            search_sql += " AND memory_type = %s"
            params.append(memory_type)

        search_sql += f"""
        ORDER BY embedding <=> %s
        LIMIT %s
        """
        params.extend([query_vector, limit])

        # 设置HNSW搜索参数
        await self.connection.execute(f"SET hnsw.ef_search = {ef_search};")

        results = await self.connection.fetch(search_sql, tuple(params))
        return results

    async def delete(self, memory_id: str) -> bool:
        """删除向量"""
        delete_sql = "DELETE FROM embeddings WHERE memory_id = %s"
        try:
            await self.connection.execute(delete_sql, (memory_id,))
            return True
        except Exception as e:
            print(f"Error deleting vector: {e}")
            return False

    async def get(self, memory_id: str) -> Optional[Dict]:
        """获取单个向量"""
        select_sql = "SELECT * FROM embeddings WHERE memory_id = %s"
        return await self.connection.fetch_one(select_sql, (memory_id,))

    async def count(self, memory_type: Optional[str] = None) -> int:
        """统计向量数量"""
        if memory_type:
            sql = "SELECT COUNT(*) as count FROM embeddings WHERE memory_type = %s"
            result = await self.connection.fetch_one(sql, (memory_type,))
        else:
            sql = "SELECT COUNT(*) as count FROM embeddings"
            result = await self.connection.fetch_one(sql)

        return result["count"] if result else 0

    async def batch_add(
        self,
        entries: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        批量添加向量

        Args:
            entries: 向量条目列表
            batch_size: 批大小

        Returns:
            {success_count, failed_count}
        """
        success_count = 0
        failed_count = 0

        for i in range(0, len(entries), batch_size):
            batch = entries[i:i + batch_size]

            for entry in batch:
                result = await self.add(
                    memory_id=entry["memory_id"],
                    content=entry.get("content", ""),
                    embedding=entry["embedding"],
                    memory_type=entry.get("memory_type", "unknown"),
                    importance=entry.get("importance", 0.5),
                    tags=entry.get("tags"),
                    metadata=entry.get("metadata")
                )
                if result:
                    success_count += 1
                else:
                    failed_count += 1

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(entries)
        }

    async def batch_search(
        self,
        queries: List[List[float]],
        limit: int = 10,
        memory_type: Optional[str] = None,
        ef_search: int = 64
    ) -> List[List[Dict]]:
        """
        批量搜索

        Args:
            queries: 查询向量列表
            limit: 每个查询返回数量
            memory_type: 记忆类型过滤
            ef_search: HNSW搜索参数

        Returns:
            每个查询的结果列表
        """
        results = []

        # 设置搜索参数
        await self.connection.execute(f"SET hnsw.ef_search = {ef_search};")

        for query_vector in queries:
            search_results = await self.search(
                query_vector=query_vector,
                limit=limit,
                memory_type=memory_type,
                ef_search=ef_search
            )
            results.append(search_results)

        return results


class RelationalStorage:
    """
    PostgreSQL关系存储

    用于存储结构化记忆数据
    """

    def __init__(self, connection: PostgresConnection):
        self.connection = connection

    async def initialize(self) -> None:
        """初始化表结构"""
        # 用户画像表
        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            preference_key VARCHAR(255) NOT NULL,
            preference_value TEXT,
            confidence FLOAT DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, preference_key)
        );
        """)

        # 程序记忆表
        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS procedures (
            id SERIAL PRIMARY KEY,
            procedure_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            description TEXT,
            steps JSONB DEFAULT '[]',
            success_rate FLOAT DEFAULT 0.0,
            total_executions INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # 实体关系表
        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id SERIAL PRIMARY KEY,
            entity_id VARCHAR(255) UNIQUE NOT NULL,
            entity_type VARCHAR(100),
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # 关系边表
        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS relation_edges (
            id SERIAL PRIMARY KEY,
            source_id VARCHAR(255) NOT NULL,
            target_id VARCHAR(255) NOT NULL,
            relation_type VARCHAR(100),
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # 记忆索引表
        await self.connection.execute("""
        CREATE TABLE IF NOT EXISTS memory_index (
            id SERIAL PRIMARY KEY,
            memory_id VARCHAR(255) UNIQUE NOT NULL,
            memory_type VARCHAR(50),
            importance FLOAT DEFAULT 0.5,
            tags TEXT[],
            retention_score FLOAT DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

    async def store_user_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: Any,
        confidence: float = 1.0
    ) -> bool:
        """存储用户偏好"""
        sql = """
        INSERT INTO user_profiles (user_id, preference_key, preference_value, confidence)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, preference_key) DO UPDATE SET
            preference_value = EXCLUDED.preference_value,
            confidence = EXCLUDED.confidence,
            updated_at = NOW()
        """
        try:
            await self.connection.execute(sql, (user_id, preference_key, str(preference_value), confidence))
            return True
        except Exception as e:
            print(f"Error storing preference: {e}")
            return False

    async def get_user_preferences(self, user_id: str) -> List[Dict]:
        """获取用户偏好"""
        sql = "SELECT * FROM user_profiles WHERE user_id = %s"
        return await self.connection.fetch(sql, (user_id,))

    async def store_procedure(
        self,
        procedure_id: str,
        name: str,
        steps: List[str],
        description: str = "",
        success_rate: float = 0.0
    ) -> bool:
        """存储程序记忆"""
        sql = """
        INSERT INTO procedures (procedure_id, name, description, steps, success_rate)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (procedure_id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            steps = EXCLUDED.steps,
            success_rate = EXCLUDED.success_rate,
            updated_at = NOW()
        """
        try:
            await self.connection.execute(sql, (procedure_id, name, description, json.dumps(steps), success_rate))
            return True
        except Exception as e:
            print(f"Error storing procedure: {e}")
            return False

    async def get_procedure(self, procedure_id: str) -> Optional[Dict]:
        """获取程序记忆"""
        sql = "SELECT * FROM procedures WHERE procedure_id = %s"
        return await self.connection.fetch_one(sql, (procedure_id,))


# 连接管理器单例
_connection_manager: Optional[PostgresConnection] = None


def get_postgres_connection() -> PostgresConnection:
    """获取PostgreSQL连接单例"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = PostgresConnection()
    return _connection_manager


async def initialize_postgres_memory() -> Tuple[VectorStorage, RelationalStorage]:
    """
    初始化PostgreSQL记忆存储

    Returns:
        (VectorStorage, RelationalStorage)
    """
    connection = get_postgres_connection()
    connection.connect()

    # 初始化向量存储
    dimension = int(os.getenv("VECTOR_DIMENSION", "1536"))
    vector_storage = VectorStorage(connection, dimension=dimension)
    await vector_storage.initialize()

    # 初始化关系存储
    relational_storage = RelationalStorage(connection)
    await relational_storage.initialize()

    return vector_storage, relational_storage
