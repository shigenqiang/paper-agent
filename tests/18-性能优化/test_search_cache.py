"""模块18 搜索缓存测试

验证 SearchCache 的命中、过期、LRU 淘汰。
"""

import time

import pytest

from src.agents_v3.research_workspace.search.base import SearchQuery, SearchResponse
from src.agents_v3.research_workspace.search.orchestrator import SearchCache


class TestSearchCache:
    """SearchCache 单元测试"""

    def test_cache_hit(self):
        """相同查询应命中缓存"""
        cache = SearchCache(max_entries=10, ttl=3600)
        q = SearchQuery(query="transformer attention")
        resp = SearchResponse(query=q, results=[], cache_hit=False)

        cache.put(q, resp)
        cached = cache.get(q)

        assert cached is not None
        assert cached.cache_hit is True

    def test_cache_miss_different_query(self):
        """不同查询不应命中"""
        cache = SearchCache(max_entries=10, ttl=3600)
        q1 = SearchQuery(query="transformer")
        q2 = SearchQuery(query="attention")
        cache.put(q1, SearchResponse(query=q1, results=[]))

        assert cache.get(q2) is None

    def test_cache_expired(self):
        """超过 TTL 应失效"""
        cache = SearchCache(max_entries=10, ttl=1)
        q = SearchQuery(query="test query")
        cache.put(q, SearchResponse(query=q, results=[]))

        time.sleep(1.1)
        assert cache.get(q) is None

    def test_cache_lru_eviction(self):
        """超过 max_entries 应淘汰最旧条目"""
        cache = SearchCache(max_entries=3, ttl=3600)

        queries = [SearchQuery(query=f"q{i}") for i in range(4)]
        for q in queries:
            cache.put(q, SearchResponse(query=q, results=[]))

        # 最早的 q0 应被淘汰
        assert cache.get(queries[0]) is None
        # q1, q2, q3 应仍在
        assert cache.get(queries[1]) is not None
        assert cache.get(queries[2]) is not None
        assert cache.get(queries[3]) is not None

    def test_cache_update_existing(self):
        """更新已有 key 不应增加条目数"""
        cache = SearchCache(max_entries=10, ttl=3600)
        q = SearchQuery(query="same query")
        cache.put(q, SearchResponse(query=q, results=[]))
        cache.put(q, SearchResponse(query=q, results=[]))

        assert len(cache._store) == 1

    def test_make_key_deterministic(self):
        """相同参数应生成相同 key"""
        q1 = SearchQuery(query="test", limit=10, offset=0)
        q2 = SearchQuery(query="test", limit=10, offset=0)
        assert SearchCache._make_key(q1) == SearchCache._make_key(q2)

    def test_make_key_different_params(self):
        """不同参数应生成不同 key"""
        q1 = SearchQuery(query="test", limit=10)
        q2 = SearchQuery(query="test", limit=20)
        assert SearchCache._make_key(q1) != SearchCache._make_key(q2)
