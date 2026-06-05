"""混合排序 — dense (HyDE embedding) + sparse (TF-IDF) + RRF 融合 + 质量过滤

流程：
1. HyDE 生成假设性论文摘要
2. dense 编码（语义向量）+ sparse 编码（关键词向量）
3. RRF 融合两个排序
4. 按 RRF 排名取 top-K
5. 质量分过滤 → top-N
"""

from __future__ import annotations

import math

from loguru import logger

from src.agents_v3.research_workspace.search.base import SearchResult


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的 cosine similarity"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _sparse_dot_product(a: dict[int, float], b: dict[int, float]) -> float:
    """计算两个稀疏向量的 dot product"""
    if not a or not b:
        return 0.0
    # 只遍历较小的那个
    if len(a) > len(b):
        a, b = b, a
    return sum(a[k] * b[k] for k in a if k in b)


def _rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[float]:
    """RRF (Reciprocal Rank Fusion) 融合多个排序

    Args:
        rankings: 每个排序是 [index] 的列表（按分数降序）
        k: RRF 常数

    Returns:
        每个元素的 RRF 分数
    """
    n = max(len(r) for r in rankings) if rankings else 0
    scores = [0.0] * n
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] += 1.0 / (k + rank + 1)
    return scores


class HybridRanker:
    """混合排序：dense (HyDE) + sparse (TF-IDF) + RRF 融合

    用于外部 API 返回的搜索结果排序（数据不在 Qdrant 中）。
    在内存中计算 dense 和 sparse 分数，用 RRF 融合。
    """

    def __init__(
        self,
        rrf_k: int = 60,
        top_k: int = 60,
        top_n: int = 30,
        quality_threshold: float = 0.3,
    ):
        from src.agents_v3.research_workspace.storage.embedding_provider import get_embedding_provider
        self.embedding_service = get_embedding_provider()
        self.rrf_k = rrf_k
        self.top_k = top_k
        self.top_n = top_n
        self.quality_threshold = quality_threshold

    def rank(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        """用 dense + sparse + RRF 混合排序

        Args:
            results: 搜索结果列表
            query: 原始查询

        Returns:
            RRF 排序 → top-K → 质量过滤 → top-N
        """
        if not results or not query.strip():
            return results

        # 1. HyDE 生成假设性摘要
        hypothetical = self._generate_hyde(query)
        if not hypothetical:
            hypothetical = query
            logger.warning("HyDE generation failed, using original query for dense encoding")

        # 2. 训练 sparse 编码器（用论文文本作为语料）
        corpus = [f"{r.title or ''} {r.abstract or ''}" for r in results]
        self.embedding_service.fit_sparse(corpus)

        # 3. 编码查询（dense + sparse）
        query_dense = self.embedding_service.embed_query(hypothetical)
        query_sparse = self.embedding_service.embed_query_sparse(hypothetical)

        # 4. 编码所有论文（dense + sparse）
        paper_dense = self.embedding_service.embed_texts(corpus)
        paper_sparse = self.embedding_service.embed_texts_sparse(corpus)

        # 5. 计算 dense 分数（cosine similarity）
        dense_scores = [_cosine_similarity(query_dense, d) for d in paper_dense]
        dense_scores = [max(0.0, s) for s in dense_scores]

        # 6. 计算 sparse 分数（dot product）
        sparse_scores = [_sparse_dot_product(query_sparse, s) for s in paper_sparse]

        # 7. 分别排序，得到排名
        dense_ranking = sorted(range(len(results)), key=lambda i: dense_scores[i], reverse=True)
        sparse_ranking = sorted(range(len(results)), key=lambda i: sparse_scores[i], reverse=True)

        # 8. RRF 融合
        rrf_scores = _rrf_fuse([dense_ranking, sparse_ranking], k=self.rrf_k)

        # 9. 归一化 RRF 分数到 [0, 1]
        max_rrf = max(rrf_scores) if rrf_scores else 1.0
        if max_rrf > 0:
            rrf_scores = [s / max_rrf for s in rrf_scores]

        # 10. 设置 dense_score（cosine similarity，用于入库）
        for i, r in enumerate(results):
            r.dense_score = round(dense_scores[i], 3)

        # 11. 按 RRF 分数降序排列（排序用 RRF，入库用 dense_score）
        rrf_order = sorted(range(len(results)), key=lambda i: rrf_scores[i], reverse=True)
        results = [results[i] for i in rrf_order]
        for i, r in enumerate(results):
            r.source_rank = i + 1

        n_before = len(results)

        # 12. RRF 排名取 top-K
        results = results[:self.top_k]

        # 13. 质量分过滤 → top-N
        results = self._filter_by_quality(results)

        logger.info(
            f"Hybrid ranker: {n_before} → top_k={self.top_k} → {len(results)} results, "
            f"quality≥{self.quality_threshold}"
        )
        return results

    def _filter_by_quality(self, results: list[SearchResult]) -> list[SearchResult]:
        """质量分过滤（保持 RRF 排序顺序，只剔除低质量论文）"""
        if not results:
            return []
        from src.agents_v3.research_workspace.search.quality_filter import compute_quality_batch
        quality_scores = compute_quality_batch(results)
        for i, r in enumerate(results):
            r.quality_score = round(quality_scores[i], 3)
        # 保持 RRF 排序，只过滤低质量
        filtered = [r for r in results if (r.quality_score or 0) >= self.quality_threshold]
        # 保底：过滤太少则保留前 top_n
        if len(filtered) < 3:
            filtered = results[:self.top_n]
        return filtered[:self.top_n]

    def _generate_hyde(self, query: str) -> str:
        """生成 HyDE 假设性摘要"""
        try:
            from src.agents_v3.research_workspace.search.query_optimizer import hyde_query
            hypothetical = hyde_query(query)
            if hypothetical:
                logger.info(f"HyDE: generated {len(hypothetical)} chars hypothetical abstract")
            return hypothetical
        except Exception as e:
            logger.warning(f"HyDE query generation failed: {e}")
            return ""
