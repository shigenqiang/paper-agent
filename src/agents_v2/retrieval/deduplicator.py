"""
去重器 - Deduplicator V2

功能:
1. 语义去重
2. 相似度计算
3. 聚类去重
4. 多种去重策略

设计原则:
- 多维度相似度计算
- 可配置的阈值
- 高效的去重算法
"""
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class DeduplicationStrategy(str, Enum):
    """去重策略"""
    EXACT = "exact"  # 精确去重
    SIMILARITY = "similarity"  # 相似度去重
    SEMANTIC = "semantic"  # 语义去重
    CLUSTERING = "clustering"  # 聚类去重


@dataclass
class DedupConfig:
    """去重配置"""
    strategy: DeduplicationStrategy = DeduplicationStrategy.SIMILARITY
    similarity_threshold: float = 0.85  # 相似度阈值
    use_semantic: bool = False  # 是否使用语义相似度
    embedder: Optional[Callable] = None  # 嵌入函数


@dataclass
class DedupResult:
    """去重结果"""
    original_count: int
    deduped_count: int
    removed_items: List[str]  # 被移除的item id
    clusters: List[List[str]] = field(default_factory=list)  # 聚类分组


class Deduplicator:
    """去重器"""

    def __init__(self, config: Optional[DedupConfig] = None):
        self.config = config or DedupConfig()

    def deduplicate(
        self,
        items: List[Any],
        id_func: Callable[[Any], str] = lambda x: str(x),
        content_func: Callable[[Any], str] = lambda x: str(x)
    ) -> List[Any]:
        """去重

        Args:
            items: 待去重的项目列表
            id_func: 获取项目ID的函数
            content_func: 获取项目内容的函数

        Returns:
            List[Any]: 去重后的项目列表
        """
        if self.config.strategy == DeduplicationStrategy.EXACT:
            return self._exact_deduplicate(items, id_func)
        elif self.config.strategy == DeduplicationStrategy.SIMILARITY:
            return self._similarity_deduplicate(items, content_func)
        elif self.config.strategy == DeduplicationStrategy.SEMANTIC:
            return self._semantic_deduplicate(items, content_func)
        elif self.config.strategy == DeduplicationStrategy.CLUSTERING:
            return self._clustering_deduplicate(items, content_func)
        else:
            return items

    def _exact_deduplicate(
        self,
        items: List[Any],
        id_func: Callable[[Any], str]
    ) -> List[Any]:
        """精确去重"""
        seen_ids: Set[str] = set()
        result = []

        for item in items:
            item_id = id_func(item)
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                result.append(item)

        return result

    def _similarity_deduplicate(
        self,
        items: List[Any],
        content_func: Callable[[Any], str]
    ) -> List[Any]:
        """基于相似度的去重"""
        if not items:
            return []

        # 计算内容的哈希
        item_hashes: List[Tuple[Any, str, str]] = []  # (item, hash, content)

        for item in items:
            content = content_func(item)
            content_hash = self._compute_similarity_hash(content)
            item_hashes.append((item, content_hash, content))

        # 贪婪选择
        selected = []
        selected_hashes = []

        for item, content_hash, content in item_hashes:
            is_duplicate = False

            for selected_hash in selected_hashes:
                similarity = self._calculate_similarity(content_hash, selected_hash)
                if similarity >= self.config.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                selected.append(item)
                selected_hashes.append(content_hash)

        return selected

    def _semantic_deduplicate(
        self,
        items: List[Any],
        content_func: Callable[[Any], str]
    ) -> List[Any]:
        """基于语义的去重"""
        if not items:
            return []

        if not self.config.embedder:
            # 如果没有embedder，回退到相似度去重
            return self._similarity_deduplicate(items, content_func)

        # 计算嵌入向量
        contents = [content_func(item) for item in items]
        embeddings = [self.config.embedder(content) for content in contents]

        # 贪婪选择
        selected = []
        selected_embeddings = []

        for i, (item, embedding) in enumerate(zip(items, embeddings)):
            is_duplicate = False

            for selected_emb in selected_embeddings:
                similarity = self._cosine_similarity(embedding, selected_emb)
                if similarity >= self.config.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                selected.append(item)
                selected_embeddings.append(embedding)

        return selected

    def _clustering_deduplicate(
        self,
        items: List[Any],
        content_func: Callable[[Any], str]
    ) -> Tuple[List[Any], List[List[Any]]]:
        """聚类去重，返回去重结果和聚类分组"""
        if not items:
            return [], []

        # 计算相似度矩阵
        contents = [content_func(item) for item in items]
        n = len(contents)

        # 简单哈希方法
        hashes = [self._compute_similarity_hash(c) for c in contents]

        # 构建聚类
        clusters: List[List[int]] = []
        assigned: Set[int] = set()

        for i in range(n):
            if i in assigned:
                continue

            cluster = [i]
            assigned.add(i)

            for j in range(i + 1, n):
                if j in assigned:
                    continue

                similarity = self._calculate_similarity(hashes[i], hashes[j])
                if similarity >= self.config.similarity_threshold:
                    cluster.append(j)
                    assigned.add(j)

            clusters.append(cluster)

        # 从每个聚类中选择一个代表
        selected = []
        cluster_results = []

        for cluster in clusters:
            # 选择第一个（可以改进为选择最中心的）
            representative = items[cluster[0]]
            selected.append(representative)
            cluster_results.append([items[i] for i in cluster])

        return selected, cluster_results

    def _compute_similarity_hash(self, text: str) -> str:
        """计算用于相似度比较的哈希"""
        # 使用n-gram哈希
        text = text.lower().strip()

        # 字符级n-gram
        n = 3
        ngrams = [text[i:i+n] for i in range(len(text) - n + 1)]

        if not ngrams:
            return hashlib.md5(text.encode()).hexdigest()

        # 排序并哈希
        ngrams.sort()
        combined = "".join(ngrams)

        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """计算两个哈希的相似度"""
        if hash1 == hash2:
            return 1.0

        # 计算字符级相似度 (Jaccard)
        set1 = set(hash1)
        set2 = set(hash2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def get_dedup_stats(
        self,
        items: List[Any],
        id_func: Callable[[Any], str] = lambda x: str(x)
    ) -> Dict[str, Any]:
        """获取去重统计信息"""
        original_count = len(items)

        # 使用精确去重计算
        seen_ids: Set[str] = set()
        unique_ids: Set[str] = set()

        for item in items:
            item_id = id_func(item)
            if item_id in seen_ids:
                if item_id not in unique_ids:
                    unique_ids.add(item_id)
            else:
                seen_ids.add(item_id)

        deduped_count = len(seen_ids)
        duplicate_count = original_count - deduped_count

        return {
            "original_count": original_count,
            "deduped_count": deduped_count,
            "duplicate_count": duplicate_count,
            "duplicate_rate": duplicate_count / original_count if original_count > 0 else 0
        }


# 便捷函数
def deduplicate(
    items: List[Any],
    strategy: DeduplicationStrategy = DeduplicationStrategy.SIMILARITY,
    threshold: float = 0.85
) -> List[Any]:
    """便捷去重函数"""
    config = DedupConfig(strategy=strategy, similarity_threshold=threshold)
    deduplicator = Deduplicator(config)
    return deduplicator.deduplicate(items)
