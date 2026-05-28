"""搜索缓存测试"""

import time
import pytest

from src.agents_v3.research_workspace.search.cache import SearchCache


class TestSearchCache:
    def test_make_key_deterministic(self):
        k1 = SearchCache.make_key("test", ["arxiv", "openalex"], 20)
        k2 = SearchCache.make_key("test", ["openalex", "arxiv"], 20)
        assert k1 == k2  # Order-independent

    def test_make_key_different_for_different_queries(self):
        k1 = SearchCache.make_key("test", ["arxiv"], 20)
        k2 = SearchCache.make_key("other", ["arxiv"], 20)
        assert k1 != k2

    def test_get_returns_none_for_miss(self):
        cache = SearchCache()
        assert cache.get("nonexistent") is None

    def test_set_and_get(self):
        cache = SearchCache()
        cache.set("key1", {"results": [1, 2, 3]})
        data = cache.get("key1")
        assert data == {"results": [1, 2, 3]}

    def test_expired_not_returned(self):
        cache = SearchCache(default_ttl=1)
        cache.set("key1", {"data": True}, ttl=-1)  # Already expired
        assert cache.get("key1") is None

    def test_invalidate(self):
        cache = SearchCache()
        cache.set("key1", {"data": True})
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_clear_expired(self):
        cache = SearchCache(default_ttl=1)
        cache.set("k1", {"a": 1}, ttl=-1)  # Already expired
        cache.set("k2", {"b": 2}, ttl=100)
        cleared = cache.clear_expired()
        assert cleared >= 1

    def test_ttl_for_doi_query(self):
        ttl = SearchCache.get_ttl_for_query("10.1234/test", ["crossref"])
        assert ttl == 604800  # 7 days

    def test_ttl_for_arxiv_only(self):
        ttl = SearchCache.get_ttl_for_query("test query", ["arxiv"])
        assert ttl == 21600  # 6 hours
