"""
Cache Tests

Tests for:
- ResultCache: Simple key-value cache with TTL
- LLMLCallOptimizer: LLM call optimizer with caching and batching
- SemanticCache: Semantic similarity-based cache
"""
import pytest
import asyncio
import time
from src.agents_v2.unified.cache import (
    ResultCache,
    LLMLCallOptimizer,
    SemanticCache,
    CacheEntry,
    CacheStrategy
)


class TestCacheEntry:
    """CacheEntry Tests"""

    def test_create_entry(self):
        """Test creating cache entry"""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            ttl=3600
        )
        assert entry.key == "test_key"
        assert entry.value["data"] == "test"
        assert entry.ttl == 3600
        assert entry.hit_count == 0

    def test_is_expired(self):
        """Test expiration check"""
        entry = CacheEntry(
            key="test",
            value="test",
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600  # 1 hour TTL
        )
        assert entry.is_expired() is True

    def test_is_not_expired(self):
        """Test non-expired entry"""
        entry = CacheEntry(
            key="test",
            value="test",
            timestamp=time.time(),
            ttl=3600
        )
        assert entry.is_expired() is False

    def test_increment_hit(self):
        """Test hit count increment"""
        entry = CacheEntry(key="test", value="test")
        assert entry.hit_count == 0
        entry.increment_hit()
        assert entry.hit_count == 1
        entry.increment_hit()
        assert entry.hit_count == 2


class TestResultCache:
    """ResultCache Tests"""

    def test_set_and_get(self):
        """Test setting and getting values"""
        cache = ResultCache(default_ttl=3600)
        cache.set("key1", {"data": "test"})
        result = cache.get("key1")
        assert result["data"] == "test"

    def test_get_miss(self):
        """Test cache miss"""
        cache = ResultCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_expiration(self):
        """Test that expired entries are removed"""
        cache = ResultCache(default_ttl=1)  # 1 second TTL

        cache.set("key1", "value1")
        time.sleep(1.1)  # Wait for expiration

        result = cache.get("key1")
        assert result is None

    def test_delete(self):
        """Test deleting cache entry"""
        cache = ResultCache()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        """Test clearing all cache"""
        cache = ResultCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_stats(self):
        """Test getting cache stats"""
        cache = ResultCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["total_hits"] == 2

    def test_string_key_hashing(self):
        """Test that string keys are properly hashed"""
        cache = ResultCache()
        cache.set("key1", "value1")
        result = cache.get("key1")
        assert result == "value1"


class TestLLMLCallOptimizer:
    """LLMLCallOptimizer Tests"""

    def test_init_with_cache(self):
        """Test initialization with cache"""
        optimizer = LLMLCallOptimizer(cache_ttl=3600, enable_cache=True)
        assert optimizer.cache is not None

    def test_init_without_cache(self):
        """Test initialization without cache"""
        optimizer = LLMLCallOptimizer(enable_cache=False)
        assert optimizer.cache is None

    @pytest.mark.asyncio
    async def test_call_without_cache(self):
        """Test LLM call without cache"""
        optimizer = LLMLCallOptimizer(enable_cache=False)

        call_count = []
        async def mock_llm(prompt, **kwargs):
            call_count.append(1)
            return f"Response to: {prompt}"

        result = await optimizer.call(mock_llm, "Hello")
        assert result == "Response to: Hello"
        assert len(call_count) == 1

    @pytest.mark.asyncio
    async def test_call_with_cache_hit(self):
        """Test LLM call with cache hit"""
        optimizer = LLMLCallOptimizer(enable_cache=True)

        call_count = []
        async def mock_llm(prompt, **kwargs):
            call_count.append(1)
            return f"Response to: {prompt}"

        # First call
        result1 = await optimizer.call(mock_llm, "Hello")
        # Second call with same prompt should hit cache
        result2 = await optimizer.call(mock_llm, "Hello")

        assert result1 == result2
        assert len(call_count) == 1  # Only called once

    @pytest.mark.asyncio
    async def test_batch_call_with_cache(self):
        """Test batch call with cache"""
        optimizer = LLMLCallOptimizer(enable_cache=True, enable_batch=True)

        call_count = []
        async def mock_llm(prompt, **kwargs):
            call_count.append(1)
            return f"Response to: {prompt}"

        prompts = ["Hello", "World", "Test"]
        results = await optimizer.batch_call(mock_llm, prompts)

        assert len(results) == 3
        # Each prompt is unique, so should call LLM 3 times
        assert len(call_count) == 3

    @pytest.mark.asyncio
    async def test_batch_call_with_sequential_duplicates(self):
        """Test batch call cache hits when same prompt called separately"""
        optimizer = LLMLCallOptimizer(enable_cache=True, enable_batch=True)

        call_count = []
        async def mock_llm(prompt, **kwargs):
            call_count.append(1)
            return f"Response to: {prompt}"

        # First batch - all unique
        prompts1 = ["Hello", "World"]
        results1 = await optimizer.batch_call(mock_llm, prompts1)
        assert len(call_count) == 2

        # Second batch - "Hello" should now be cached
        prompts2 = ["Hello", "Test"]
        results2 = await optimizer.batch_call(mock_llm, prompts2)
        # Should only call LLM once for "Test", "Hello" should hit cache
        assert len(call_count) == 3

    @pytest.mark.asyncio
    async def test_batch_call_without_cache(self):
        """Test batch call without cache"""
        optimizer = LLMLCallOptimizer(enable_cache=False, enable_batch=True)

        call_count = []
        async def mock_llm(prompt, **kwargs):
            call_count.append(1)
            return f"Response to: {prompt}"

        prompts = ["Hello", "World"]
        results = await optimizer.batch_call(mock_llm, prompts)

        assert len(results) == 2
        assert len(call_count) == 2

    def test_cache_stats(self):
        """Test getting cache stats"""
        optimizer = LLMLCallOptimizer(enable_cache=True)
        stats = optimizer.get_cache_stats()
        assert "size" in stats
        assert "total_hits" in stats


class TestSemanticCache:
    """SemanticCache Tests"""

    def test_set_and_get_exact_match(self):
        """Test setting and getting with exact match"""
        cache = SemanticCache(similarity_threshold=0.85)

        cache.set("Hello world", {"response": "Hi"})
        result = cache.get("Hello world")

        assert result["response"] == "Hi"

    def test_get_miss(self):
        """Test cache miss"""
        cache = SemanticCache(similarity_threshold=0.85)
        result = cache.get("nonexistent")
        assert result is None

    def test_semantic_match(self):
        """Test semantic similarity matching"""
        cache = SemanticCache(similarity_threshold=0.85)

        # Set with embedding
        embedding1 = [0.1, 0.2, 0.3, 0.4]
        cache.set("What is AI?", {"response": "AI is artificial intelligence"}, embedding=embedding1)

        # Query with similar embedding
        embedding2 = [0.1, 0.2, 0.3, 0.5]  # Very similar
        result = cache.get("What is artificial intelligence?", embedding=embedding2)

        assert result is not None
        assert result["response"] == "AI is artificial intelligence"

    def test_semantic_no_match(self):
        """Test no match when similarity is below threshold"""
        cache = SemanticCache(similarity_threshold=0.95)  # Very high threshold

        embedding1 = [0.1, 0.2, 0.3, 0.4]
        cache.set("What is AI?", {"response": "AI response"}, embedding=embedding1)

        # Query with very different embedding
        embedding2 = [0.9, 0.8, 0.7, 0.6]  # Very different
        result = cache.get("What is cooking?", embedding=embedding2)

        assert result is None

    def test_max_entries_eviction(self):
        """Test that max entries causes oldest eviction"""
        cache = SemanticCache(max_entries=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_clear(self):
        """Test clearing cache"""
        cache = SemanticCache()
        cache.set("key1", "value1", embedding=[0.1, 0.2])
        cache.clear()

        assert cache.get("key1") is None
        assert len(cache._cache) == 0
        assert len(cache._embeddings) == 0

    def test_stats(self):
        """Test getting stats"""
        cache = SemanticCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["total_hits"] == 2
        assert stats["similarity_threshold"] == 0.85


class TestCosineSimilarity:
    """Test cosine similarity calculation"""

    def test_identical_vectors(self):
        """Test identical vectors have similarity 1"""
        cache = SemanticCache()
        vec = [0.1, 0.2, 0.3]
        similarity = cache._compute_similarity(vec, vec)
        assert similarity == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Test orthogonal vectors have similarity 0"""
        cache = SemanticCache()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = cache._compute_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Test opposite vectors have similarity -1"""
        cache = SemanticCache()
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        similarity = cache._compute_similarity(vec1, vec2)
        assert similarity == pytest.approx(-1.0)

    def test_similar_vectors(self):
        """Test similar vectors have high similarity"""
        cache = SemanticCache()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.9, 0.1, 0.0]
        similarity = cache._compute_similarity(vec1, vec2)
        assert similarity > 0.9

    def test_zero_vector(self):
        """Test zero vector handling"""
        cache = SemanticCache()
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = cache._compute_similarity(vec1, vec2)
        assert similarity == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])