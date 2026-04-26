"""
记忆压缩 - Memory Compression

提供:
- MemoryCompressor: 记忆压缩器
- KeyPointExtractor: 关键点提取
- CompressedEntry: 压缩后的记忆
"""
import asyncio
import hashlib
import re
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from .types import MemoryEntry, ImportanceLevel


@dataclass
class CompressedEntry:
    """压缩后的记忆"""
    original_id: str
    summary: str
    key_points: List[str]
    importance: float
    original_size: int
    compressed_size: int
    compression_ratio: float


class KeyPointExtractor:
    """
    关键点提取器

    从文本中提取关键信息点
    """

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    async def extract(
        self,
        content: str,
        max_points: int = 5
    ) -> List[str]:
        """
        提取关键点

        Args:
            content: 原始内容
            max_points: 最大点数

        Returns:
            关键点列表
        """
        if self.llm_client:
            return await self._extract_with_llm(content, max_points)
        return self._extract_with_rules(content, max_points)

    async def _extract_with_llm(
        self,
        content: str,
        max_points: int
    ) -> List[str]:
        """使用LLM提取关键点"""
        prompt = f"""从以下文本中提取{max_points}个关键点:

{content[:1000]}

关键点应该:
1. 简洁明了
2. 包含核心信息
3. 用一句话描述

格式: 每行一个关键点"""
        try:
            response = await self.llm_client.ainvoke(prompt)
            text = response.content if hasattr(response, 'content') else str(response)
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            return lines[:max_points]
        except Exception:
            return self._extract_with_rules(content, max_points)

    def _extract_with_rules(self, content: str, max_points: int) -> List[str]:
        """使用规则提取关键点"""
        points = []

        # 提取数字信息
        numbers = re.findall(r'\d+(?:\.\d+)?', content)
        if numbers:
            points.append(f"包含数字信息: {', '.join(numbers[:3])}")

        # 提取关键词
        keywords = re.findall(r'\b[A-Z][a-z]+\b', content)
        unique_keywords = list(dict.fromkeys(keywords))[:5]
        if unique_keywords:
            points.append(f"关键词: {', '.join(unique_keywords)}")

        # 提取缩写/术语
        terms = re.findall(r'\b[A-Z]{2,}\b', content)
        if terms:
            points.append(f"术语: {', '.join(terms[:3])}")

        return points[:max_points]


class MemoryCompressor:
    """
    记忆压缩器

    职责:
    - 摘要压缩存储
    - 重要记忆提取
    - 增量压缩
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        compression_threshold: int = 500
    ):
        self.llm_client = llm_client
        self.compression_threshold = compression_threshold  # 超过此长度则压缩
        self.key_point_extractor = KeyPointExtractor(llm_client)

    async def compress_entry(
        self,
        entry: MemoryEntry
    ) -> CompressedEntry:
        """
        压缩单条记忆

        Args:
            entry: 原始记忆条目

        Returns:
            压缩后的记忆
        """
        content = str(entry.content)
        original_size = len(content)

        # 如果太短，不压缩
        if len(content) < self.compression_threshold:
            return CompressedEntry(
                original_id=entry.id,
                summary=content,
                key_points=[],
                importance=entry.importance,
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=1.0
            )

        # 根据重要性决定压缩策略
        if entry.importance >= 0.8:
            # 高重要性：保留完整，只提取关键点
            key_points = await self.key_point_extractor.extract(content)
            summary = content[:500]
            compressed_size = len(summary) + sum(len(k) for k in key_points)
        else:
            # 中低重要性：摘要压缩
            summary = await self._generate_summary(content)
            key_points = await self.key_point_extractor.extract(content, max_points=3)
            compressed_size = len(summary) + sum(len(k) for k in key_points)

        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0

        return CompressedEntry(
            original_id=entry.id,
            summary=summary,
            key_points=key_points,
            importance=entry.importance,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio
        )

    async def compress_batch(
        self,
        entries: List[MemoryEntry],
        batch_size: int = 50
    ) -> List[CompressedEntry]:
        """
        批量压缩

        Args:
            entries: 记忆条目列表
            batch_size: 批大小

        Returns:
            压缩后的条目列表
        """
        results = []

        for i in range(0, len(entries), batch_size):
            batch = entries[i:i + batch_size]

            compressed_batch = await asyncio.gather(
                *[self.compress_entry(entry) for entry in batch],
                return_exceptions=True
            )

            for result in compressed_batch:
                if not isinstance(result, Exception):
                    results.append(result)

        return results

    async def _generate_summary(self, content: str) -> str:
        """生成摘要"""
        if self.llm_client:
            prompt = f"""请为以下内容生成简洁摘要(不超过200字):

{content[:2000]}

摘要:"""
            try:
                response = await self.llm_client.ainvoke(prompt)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception:
                pass

        # 简单摘要：取前200字
        return content[:200] + "..." if len(content) > 200 else content

    async def should_compress(self, entry: MemoryEntry) -> bool:
        """
        判断是否应该压缩

        Args:
            entry: 记忆条目

        Returns:
            是否应该压缩
        """
        content = str(entry.content)

        # 太短不压缩
        if len(content) < self.compression_threshold:
            return False

        # 低重要性不压缩
        if entry.importance < 0.3:
            return False

        return True

    def estimate_compression_ratio(self, entry: MemoryEntry) -> float:
        """
        估算压缩率

        Args:
            entry: 记忆条目

        Returns:
            估算的压缩率
        """
        original_size = len(str(entry.content))

        if entry.importance >= 0.8:
            # 高重要性：保留摘要+关键点，约30%
            return 0.3
        elif entry.importance >= 0.5:
            # 中重要性：只保留摘要，约20%
            return 0.2
        else:
            # 低重要性：只保留关键点，约10%
            return 0.1


class IncrementalCompressor:
    """
    增量压缩器

    用于对积累的历史记忆进行定期压缩
    """

    def __init__(self, compressor: MemoryCompressor):
        self.compressor = compressor

    async def compress_old_memories(
        self,
        get_memories_func: Callable,
        max_age_days: int = 30,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        压缩旧记忆

        Args:
            get_memories_func: 获取记忆的函数
            max_age_days: 超过此天数的记忆将被压缩
            batch_size: 批大小

        Returns:
            压缩统计
        """
        stats = {
            "total_processed": 0,
            "compressed": 0,
            "skipped": 0,
            "errors": 0,
            "space_saved": 0
        }

        memories = await get_memories_func()

        for i in range(0, len(memories), batch_size):
            batch = memories[i:i + batch_size]

            for entry in batch:
                stats["total_processed"] += 1

                # 检查年龄
                if not self._is_old(entry, max_age_days):
                    stats["skipped"] += 1
                    continue

                # 检查是否需要压缩
                if not await self.compressor.should_compress(entry):
                    stats["skipped"] += 1
                    continue

                try:
                    compressed = await self.compressor.compress_entry(entry)
                    stats["compressed"] += 1
                    stats["space_saved"] += (
                        compressed.original_size - compressed.compressed_size
                    )
                except Exception:
                    stats["errors"] += 1

        return stats

    def _is_old(self, entry: MemoryEntry, max_age_days: int) -> bool:
        """检查记忆是否足够旧"""
        if not hasattr(entry, 'created_at'):
            return False

        import time
        age_seconds = time.time() - entry.created_at
        age_days = age_seconds / 86400

        return age_days > max_age_days
