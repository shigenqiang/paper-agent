"""
缓存机制 - 减少重复LLM调用

提供:
1. SemanticCache: 语义缓存，相似查询复用结果
2. LLMLCallOptimizer: LLM调用优化器
3. ResultCache: 结果缓存
"""
from src.agents_v2.logging_config import get_logging_logger

import time
import hashlib
import json

import asyncio
from typing import Any, Callable, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class CacheStrategy(str, Enum):
    """缓存策略"""
    EXACT = "exact"      # 精确匹配
    SEMANTIC = "semantic"  # 语义相似
    HYBRID = "hybrid"    # 混合策略


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: float = 3600  # 默认1小时
    hit_count: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        return (time.time() - self.timestamp) > self.ttl

    def increment_hit(self):
        """增加命中次数"""
        self.hit_count += 1


class ResultCache:
    """
    结果缓存 - 简单的键值缓存

    使用方式:
        cache = ResultCache()
        cache.set("key", result, ttl=3600)
        result = cache.get("key")
    """

    def __init__(self, default_ttl: float = 3600):
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}

    def _make_key(self, key_input: Any) -> str:
        """生成缓存键"""
        if isinstance(key_input, str):
            return hashlib.md5(key_input.encode()).hexdigest()
        return hashlib.md5(json.dumps(key_input, sort_keys=True).encode()).hexdigest()

    def set(self, key: Any, value: Any, ttl: Optional[float] = None):
        """设置缓存"""
        cache_key = self._make_key(key)
        self._cache[cache_key] = CacheEntry(
            key=cache_key,
            value=value,
            ttl=ttl or self.default_ttl
        )
        logger.debug(f"Cache set: {cache_key[:8]}...")

    def get(self, key: Any) -> Optional[Any]:
        """获取缓存"""
        cache_key = self._make_key(key)
        entry = self._cache.get(cache_key)

        if entry is None:
            logger.debug(f"Cache miss: {cache_key[:8]}...")
            return None

        if entry.is_expired():
            del self._cache[cache_key]
            logger.debug(f"Cache expired: {cache_key[:8]}...")
            return None

        entry.increment_hit()
        logger.debug(f"Cache hit: {cache_key[:8]}... (hits={entry.hit_count})")
        return entry.value

    def delete(self, key: Any):
        """删除缓存"""
        cache_key = self._make_key(key)
        if cache_key in self._cache:
            del self._cache[cache_key]

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_hits = sum(e.hit_count for e in self._cache.values())
        expired = sum(1 for e in self._cache.values() if e.is_expired())
        return {
            "size": len(self._cache),
            "total_hits": total_hits,
            "expired": expired,
            "memory_entries": list(self._cache.keys())[:10]
        }


class LLMLCallOptimizer:
    """
    LLM调用优化器 - 减少重复调用

    策略:
    1. 请求折叠: 多个相似请求合并为一个
    2. 批量处理: 将多个请求批量处理
    3. 缓存: 缓存相同/相似请求的结果
    """

    def __init__(
        self,
        cache_ttl: float = 3600,
        enable_cache: bool = True,
        enable_batch: bool = True
    ):
        self.cache = ResultCache(default_ttl=cache_ttl) if enable_cache else None
        self.enable_batch = enable_batch
        self._pending_requests: Dict[str, list] = {}

    def _make_request_key(self, prompt: str, **kwargs) -> str:
        """生成请求键"""
        key_data = {
            "prompt": prompt[:500],  # 截断避免过长
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    async def call(
        self,
        llm_func: Callable,
        prompt: str,
        **kwargs
    ) -> str:
        """
        优化后的LLM调用

        Args:
            llm_func: LLM调用函数
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            LLM响应
        """
        # 1. 尝试从缓存获取
        if self.cache:
            cache_key = self._make_request_key(prompt, **kwargs)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"LLM call cache hit for key {cache_key[:8]}...")
                return cached_result

        # 2. 执行LLM调用
        try:
            result = await llm_func(prompt, **kwargs)

            # 3. 缓存结果
            if self.cache and result:
                self.cache.set(cache_key, result)

            return result
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def batch_call(
        self,
        llm_func: Callable,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """
        批量LLM调用

        Args:
            llm_func: LLM调用函数
            prompts: 提示词列表
            **kwargs: 其他参数

        Returns:
            响应列表
        """
        if not self.enable_batch:
            # 非批量模式，逐一调用
            return [await self.call(llm_func, p, **kwargs) for p in prompts]

        # 批量模式优化：先检查缓存，再批量调用
        results = []
        cache_hits = []
        cache_misses = []
        miss_indices = []

        # 1. 检查缓存
        if self.cache:
            for i, prompt in enumerate(prompts):
                cache_key = self._make_request_key(prompt, **kwargs)
                cached = self.cache.get(cache_key)
                if cached:
                    results.append(cached)
                    cache_hits.append(i)
                else:
                    results.append(None)
                    cache_misses.append(prompt)
                    miss_indices.append(i)

            # 2. 批量处理缓存未命中的（使用信号量控制并发）
            if miss_indices:
                semaphore = asyncio.Semaphore(5)  # 最多5个并发

                async def bounded_call(idx, prompt):
                    async with semaphore:
                        try:
                            result = await llm_func(prompt, **kwargs)
                            cache_key = self._make_request_key(prompt, **kwargs)
                            self.cache.set(cache_key, result)
                            return idx, result
                        except Exception as e:
                            logger.error(f"Batch LLM call failed for prompt {idx}: {e}")
                            return idx, f"Error: {str(e)}"

                tasks = [bounded_call(idx, p) for idx, p in zip(miss_indices, cache_misses)]
                completed = await asyncio.gather(*tasks)

                for idx, result in completed:
                    results[idx] = result

            return results
        else:
            # 无缓存模式
            return [await llm_func(p, **kwargs) for p in prompts]

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        if self.cache:
            return self.cache.stats()
        return {"size": 0, "total_hits": 0}


class SemanticCache:
    """
    语义缓存 - 基于相似度的缓存

    当没有精确匹配时，使用Embedding相似度判断是否可以使用缓存结果
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        default_ttl: float = 3600,
        max_entries: int = 1000
    ):
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._embeddings: Dict[str, list[float]] = {}

    def _make_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode()).hexdigest()

    def _compute_similarity(self, emb1: list[float], emb2: list[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5
        if norm1 * norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def set(self, text: str, value: Any, embedding: Optional[list[float]] = None):
        """设置缓存"""
        key = self._make_key(text)

        # 如果缓存已满，删除最旧的条目
        if len(self._cache) >= self.max_entries:
            oldest = min(self._cache.items(), key=lambda x: x[1].timestamp)
            del self._cache[oldest[0]]
            if oldest[0] in self._embeddings:
                del self._embeddings[oldest[0]]

        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            ttl=self.default_ttl
        )
        if embedding:
            self._embeddings[key] = embedding

    def get(self, text: str, embedding: Optional[list[float]] = None) -> Optional[Any]:
        """获取缓存"""
        key = self._make_key(text)

        # 1. 精确匹配
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            entry.increment_hit()
            return entry.value

        # 2. 语义相似度匹配（如果有embedding）
        if embedding and self._embeddings:
            best_match = None
            best_similarity = 0.0

            for cache_key, cache_emb in self._embeddings.items():
                if cache_key == key:
                    continue
                entry = self._cache.get(cache_key)
                if not entry or entry.is_expired():
                    continue

                similarity = self._compute_similarity(embedding, cache_emb)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = entry

            if best_similarity >= self.similarity_threshold and best_match:
                best_match.increment_hit()
                logger.info(f"Semantic cache hit: similarity={best_similarity:.3f}")
                return best_match.value

        return None

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._embeddings.clear()

    def stats(self) -> Dict[str, Any]:
        """获取统计"""
        total_hits = sum(e.hit_count for e in self._cache.values())
        return {
            "size": len(self._cache),
            "total_hits": total_hits,
            "similarity_threshold": self.similarity_threshold
        }
