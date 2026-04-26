"""
扩展存储测试 - Extended Storage Tests

测试PostgreSQL、Redis、Neo4j等存储组件
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


class TestPostgresConnection:
    """PostgreSQL连接测试"""

    def test_connection_init(self):
        """测试连接初始化"""
        with patch('src.agents_v2.memory.postgres_storage.POSTGRES_AVAILABLE', True):
            with patch('psycopg2.connect') as mock_connect:
                mock_conn = Mock()
                mock_connect.return_value = mock_conn

                from src.agents_v2.memory.postgres_storage import PostgresConnection
                conn = PostgresConnection(host="localhost", port=5432, database="test_db")

                assert conn.host == "localhost"
                assert conn.port == 5432
                assert conn.database == "test_db"

    def test_connection_string(self):
        """测试连接字符串生成"""
        with patch('src.agents_v2.memory.postgres_storage.POSTGRES_AVAILABLE', True):
            from src.agents_v2.memory.postgres_storage import PostgresConnection
            conn = PostgresConnection(host="localhost", port=5432, database="test_db", user="testuser", password="testpass")

            conn_str = conn._get_connection_string()
            assert "localhost" in conn_str
            assert "5432" in conn_str
            assert "test_db" in conn_str
            assert "testuser" in conn_str


class TestVectorStorage:
    """向量存储测试"""

    def test_vector_storage_init(self):
        """测试向量存储初始化"""
        with patch('src.agents_v2.memory.postgres_storage.POSTGRES_AVAILABLE', True):
            mock_conn = Mock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])

            from src.agents_v2.memory.postgres_storage import VectorStorage

            vector_storage = VectorStorage(mock_conn, dimension=1536)

            assert vector_storage.dimension == 1536
            assert vector_storage.connection == mock_conn

    @pytest.mark.asyncio
    async def test_add_vector(self):
        """测试添加向量"""
        with patch('src.agents_v2.memory.postgres_storage.POSTGRES_AVAILABLE', True):
            mock_conn = Mock()
            mock_conn.execute = AsyncMock()

            from src.agents_v2.memory.postgres_storage import VectorStorage

            vector_storage = VectorStorage(mock_conn, dimension=1536)
            result = await vector_storage.add(
                memory_id="test_key",
                content="test content",
                embedding=[0.1] * 1536,
                memory_type="test",
                importance=0.8
            )

            assert result is True
            mock_conn.execute.assert_called_once()


class TestRelationalStorage:
    """关系存储测试"""

    def test_relational_storage_init(self):
        """测试关系存储初始化"""
        with patch('src.agents_v2.memory.postgres_storage.POSTGRES_AVAILABLE', True):
            mock_conn = Mock()

            from src.agents_v2.memory.postgres_storage import RelationalStorage

            rel_storage = RelationalStorage(mock_conn)
            assert rel_storage.connection == mock_conn

    @pytest.mark.asyncio
    async def test_store_user_preference(self):
        """测试存储用户偏好"""
        with patch('src.agents_v2.memory.postgres_storage.POSTGRES_AVAILABLE', True):
            mock_conn = Mock()
            mock_conn.execute = AsyncMock()

            from src.agents_v2.memory.postgres_storage import RelationalStorage

            rel_storage = RelationalStorage(mock_conn)
            result = await rel_storage.store_user_preference(
                user_id="user123",
                preference_key="language",
                preference_value="Python",
                confidence=0.9
            )

            assert result is True
            mock_conn.execute.assert_called_once()


class TestRedisCache:
    """Redis缓存测试"""

    def test_cache_init(self):
        """测试缓存初始化"""
        with patch('src.agents_v2.memory.redis_cache.REDIS_AVAILABLE', True):
            with patch('redis.Redis') as mock_redis:
                mock_client = Mock()
                mock_redis.return_value = mock_client

                from src.agents_v2.memory.redis_cache import RedisCache

                cache = RedisCache(host="localhost", port=6379, key_prefix="test:")

                assert cache.host == "localhost"
                assert cache.port == 6379
                assert cache.key_prefix == "test:"

    def test_make_key(self):
        """测试键生成"""
        with patch('src.agents_v2.memory.redis_cache.REDIS_AVAILABLE', True):
            with patch('redis.Redis') as mock_redis:
                from src.agents_v2.memory.redis_cache import RedisCache

                cache = RedisCache(key_prefix="memory:")
                key = cache._make_key("test_key")

                assert key == "memory:test_key"

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """测试缓存设置和获取"""
        with patch('src.agents_v2.memory.redis_cache.REDIS_AVAILABLE', True):
            with patch('redis.Redis') as mock_redis:
                mock_client = Mock()
                mock_redis.return_value = mock_client

                import pickle
                test_value = {"data": "test"}
                mock_client.setex = Mock(return_value=True)
                mock_client.get = Mock(return_value=pickle.dumps(test_value))

                from src.agents_v2.memory.redis_cache import RedisCache

                cache = RedisCache()
                cache._client = mock_client

                # 设置
                result = await cache.set("key1", test_value, ttl=3600)
                assert result is True

                # 获取
                value = await cache.get("key1")
                assert value == test_value

    def test_cache_stats(self):
        """测试缓存统计"""
        with patch('src.agents_v2.memory.redis_cache.REDIS_AVAILABLE', True):
            with patch('redis.Redis') as mock_redis:
                from src.agents_v2.memory.redis_cache import RedisCache, CacheStats

                cache = RedisCache()
                cache._stats.hits = 80
                cache._stats.misses = 20

                assert cache._stats.hit_rate == 0.8


class TestNeo4jGraphStore:
    """Neo4j图存储测试"""

    def test_graph_store_init(self):
        """测试图存储初始化"""
        with patch('src.agents_v2.memory.neo4j_store.NEO4J_AVAILABLE', True):
            from src.agents_v2.memory.neo4j_store import Neo4jGraphStore

            store = Neo4jGraphStore(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="testpass"
            )

            assert store.uri == "bolt://localhost:7687"
            assert store.user == "neo4j"
            assert store.password == "testpass"

    @pytest.mark.asyncio
    async def test_add_entity(self):
        """测试添加实体"""
        with patch('src.agents_v2.memory.neo4j_store.NEO4J_AVAILABLE', True):
            with patch('neo4j.GraphDatabase.driver') as mock_driver:
                mock_session = Mock()
                mock_driver.return_value.session.return_value.__enter__ = Mock(return_value=mock_session)
                mock_driver.return_value.session.return_value.__exit__ = Mock(return_value=None)
                mock_session.run = Mock()

                from src.agents_v2.memory.neo4j_store import Neo4jGraphStore

                store = Neo4jGraphStore()
                store._driver = mock_driver.return_value

                result = await store.add_entity(
                    entity_id="agent_1",
                    entity_type="agent",
                    properties={"name": "Test Agent", "capabilities": ["search", "write"]}
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_find_related_entities(self):
        """测试查找相关实体"""
        with patch('src.agents_v2.memory.neo4j_store.NEO4J_AVAILABLE', True):
            with patch('neo4j.GraphDatabase.driver') as mock_driver:
                mock_result = Mock()
                mock_result.__iter__ = Mock(return_value=iter([
                    {"entity_id": "entity_1", "entity_type": "task", "properties": {}},
                    {"entity_id": "entity_2", "entity_type": "task", "properties": {}}
                ]))

                mock_session = Mock()
                mock_session.run = Mock(return_value=mock_result)
                mock_driver.return_value.session.return_value.__enter__ = Mock(return_value=mock_session)
                mock_driver.return_value.session.return_value.__exit__ = Mock(return_value=None)

                from src.agents_v2.memory.neo4j_store import Neo4jGraphStore

                store = Neo4jGraphStore()
                store._driver = mock_driver.return_value

                result = await store.find_related_entities("task_1", depth=2)

                assert len(result) == 2
                assert result[0]["entity_id"] == "entity_1"


class TestConfigValidation:
    """配置验证测试"""

    def test_database_config(self):
        """测试数据库配置"""
        from src.agents_v2.memory.config import DatabaseConfig

        config = DatabaseConfig()
        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5432
        assert config.redis_port == 6379

    def test_database_url(self):
        """测试数据库URL生成"""
        from src.agents_v2.memory.config import DatabaseConfig

        config = DatabaseConfig(
            postgres_host="db.example.com",
            postgres_port=5432,
            postgres_database="mydb",
            postgres_user="user",
            postgres_password="pass"
        )

        assert "db.example.com" in config.postgres_url
        assert "5432" in config.postgres_url
        assert "mydb" in config.postgres_url

    def test_vector_config(self):
        """测试向量配置"""
        from src.agents_v2.memory.config import VectorConfig

        config = VectorConfig(
            dimension=1536,
            model="text-embedding-3-small",
            provider="openai"
        )

        assert config.dimension == 1536
        assert config.model == "text-embedding-3-small"
        assert config.provider == "openai"

    def test_cache_config(self):
        """测试缓存配置"""
        from src.agents_v2.memory.config import CacheConfig

        config = CacheConfig(
            enabled=True,
            max_size=10000,
            ttl_seconds=3600
        )

        assert config.enabled is True
        assert config.max_size == 10000
        assert config.ttl_seconds == 3600

    def test_config_from_env(self):
        """测试从环境变量加载配置"""
        with patch.dict('os.environ', {
            'POSTGRES_HOST': 'env-postgres',
            'VECTOR_DIMENSION': '768',
            'CACHE_MAX_SIZE': '5000'
        }):
            from src.agents_v2.memory.config import MemorySystemConfig

            config = MemorySystemConfig.from_env()

            assert config.database.postgres_host == "env-postgres"
            assert config.vector.dimension == 768
            assert config.cache.max_size == 5000

    def test_validate_config(self):
        """测试配置验证"""
        from src.agents_v2.memory.config import MemorySystemConfig

        config = MemorySystemConfig()
        errors = []

        # 验证正常配置
        assert len(errors) == 0

    def test_config_to_dict(self):
        """测试配置转字典"""
        from src.agents_v2.memory.config import MemorySystemConfig

        config = MemorySystemConfig()
        config_dict = config.to_dict()

        assert "version" in config_dict
        assert "database" in config_dict
        assert "vector" in config_dict
        assert "cache" in config_dict


class TestDistributedCache:
    """分布式缓存测试"""

    def test_distributed_cache_init(self):
        """测试分布式缓存初始化"""
        with patch('src.agents_v2.memory.redis_cache.REDIS_AVAILABLE', True):
            with patch('redis.Redis') as mock_redis:
                nodes = [
                    {"host": "redis1", "port": 6379},
                    {"host": "redis2", "port": 6379},
                    {"host": "redis3", "port": 6379}
                ]

                from src.agents_v2.memory.redis_cache import DistributedCache

                cache = DistributedCache(nodes)

                assert cache._node_count == 3
                assert len(cache._ring) == 3


class TestCacheStats:
    """缓存统计测试"""

    def test_cache_stats_hit_rate(self):
        """测试缓存命中率计算"""
        from src.agents_v2.memory.redis_cache import CacheStats

        stats = CacheStats(hits=80, misses=20)

        assert stats.hit_rate == 0.8

    def test_cache_stats_zero_hits(self):
        """测试零命中时的命中率"""
        from src.agents_v2.memory.redis_cache import CacheStats

        stats = CacheStats(hits=0, misses=0)

        assert stats.hit_rate == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
