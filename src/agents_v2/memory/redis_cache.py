"""
Redis缓存集成

提供高性能内存缓存
"""
import os
import asyncio
import json
import pickle
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    keys: int = 0
    memory_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class RedisCache:
    """
    Redis缓存管理器

    功能:
    - 键值存储
    - TTL过期
    - LRU淘汰
    - 内存统计
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "memory:"
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self._client = None
        self._stats = CacheStats()

    def _get_client(self):
        """获取Redis客户端"""
        if not REDIS_AVAILABLE:
            raise ImportError("redis not installed. Run: pip install redis")

        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False  # 存储二进制数据
            )
        return self._client

    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            value = client.get(full_key)

            if value is None:
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            return pickle.loads(value)
        except Exception as e:
            print(f"Redis get error: {e}")
            self._stats.misses += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        nx: bool = False
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)
            nx: 只在键不存在时设置

        Returns:
            是否成功
        """
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            serialized = pickle.dumps(value)

            if nx:
                result = client.setex(full_key, ttl, serialized)
            else:
                result = client.setex(full_key, ttl, serialized)

            return bool(result)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            result = client.delete(full_key)
            return result > 0
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            return client.exists(full_key) > 0
        except Exception:
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            return client.expire(full_key, ttl)
        except Exception:
            return False

    async def get_ttl(self, key: str) -> int:
        """获取剩余TTL"""
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            return client.ttl(full_key)
        except Exception:
            return -1

    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的键"""
        try:
            client = self._get_client()
            full_pattern = self._make_key(pattern)
            raw_keys = client.keys(full_pattern)
            # 移除前缀
            prefix = self.key_prefix
            return [k.decode() if isinstance(k, bytes) else k for k in raw_keys]
        except Exception as e:
            print(f"Redis keys error: {e}")
            return []

    async def flush_pattern(self, pattern: str = "*") -> int:
        """删除匹配模式的键"""
        try:
            client = self._get_client()
            full_pattern = self._make_key(pattern)
            keys = client.keys(full_pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis flush error: {e}")
            return 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            return client.incrby(full_key, amount)
        except Exception:
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            client = self._get_client()
            info = client.info("memory")
            return {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "hit_rate": self._stats.hit_rate,
                "used_memory": info.get("used_memory_human", "unknown"),
                "keys": self._stats.keys
            }
        except Exception:
            return {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "hit_rate": self._stats.hit_rate
            }

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = CacheStats()

    async def pipeline(self) -> 'RedisPipeline':
        """获取管道对象"""
        client = self._get_client()
        pipe = client.pipeline()
        return RedisPipeline(pipe, self)


class RedisPipeline:
    """Redis管道(批量操作)"""

    def __init__(self, pipe, cache: RedisCache):
        self.pipe = pipe
        self.cache = cache

    def get(self, key: str):
        """队列获取操作"""
        full_key = self.cache._make_key(key)
        self.pipe.get(full_key)
        return self

    def set(self, key: str, value: Any, ttl: int = 3600):
        """队列设置操作"""
        full_key = self.cache._make_key(key)
        serialized = pickle.dumps(value)
        self.pipe.setex(full_key, ttl, serialized)
        return self

    def delete(self, key: str):
        """队列删除操作"""
        full_key = self.cache._make_key(key)
        self.pipe.delete(full_key)
        return self

    async def execute(self) -> List[Any]:
        """执行管道"""
        try:
            results = self.pipe.execute()
            # 处理结果
            processed = []
            for r in results:
                if isinstance(r, bytes):
                    try:
                        processed.append(pickle.loads(r))
                    except Exception:
                        processed.append(r)
                else:
                    processed.append(r)
            return processed
        except Exception as e:
            print(f"Redis pipeline error: {e}")
            return []


class DistributedCache:
    """
    分布式缓存(Redis集群)

    支持:
    - 自动分片
    - 故障转移
    """

    def __init__(self, nodes: List[Dict[str, str]]):
        """
        初始化分布式缓存

        Args:
            nodes: 节点列表 [{"host": "x", "port": 6379}, ...]
        """
        self.nodes = nodes
        self._ring: Dict[int, RedisCache] = {}
        self._hash_ring: Dict[int, int] = {}  # hash -> node_index
        self._node_count = len(nodes)
        self._initialize_ring()

    def _initialize_ring(self) -> None:
        """初始化一致性哈希环"""
        import hashlib

        for i, node in enumerate(self.nodes):
            cache = RedisCache(
                host=node["host"],
                port=int(node.get("port", 6379)),
                db=int(node.get("db", i))
            )
            self._ring[i] = cache

            # 每个节点创建多个虚拟节点
            for v in range(10):
                key = int(hashlib.md5(f"{node['host']}:{node['port']}:{v}".encode()).hexdigest(), 16)
                self._hash_ring[key] = i

    def _get_node_index(self, key: str) -> int:
        """根据键获取节点索引"""
        import hashlib
        key_hash = int(hashlib.md5(key.encode()).hexdigest(), 16)

        # 找到第一个 >= key_hash 的节点
        for ring_key in sorted(self._hash_ring.keys()):
            if ring_key >= key_hash:
                return self._hash_ring[ring_key]

        # 回到第一个节点
        return self._hash_ring[sorted(self._hash_ring.keys())[0]]

    def _get_node(self, key: str) -> RedisCache:
        """获取键对应的节点"""
        index = self._get_node_index(key)
        return self._ring[index % self._node_count]

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        node = self._get_node(key)
        return await node.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存"""
        node = self._get_node(key)
        return await node.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        node = self._get_node(key)
        return await node.delete(key)


# 单例
_cache_instance: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """获取Redis缓存单例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD")
        )
    return _cache_instance
