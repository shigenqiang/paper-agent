"""HyDE 语义排序 — 假设性文档嵌入 + cosine similarity

流程：
1. LLM 生成假设性论文摘要（HyDE）
2. 嵌入假设性摘要 → query_embedding
3. 批量嵌入所有搜索结果（title + abstract）
4. 计算 cosine similarity → relevance_score
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


class HyDERanker:
    """基于 HyDE 的语义排序"""

    def __init__(self):
        from src.agents_v3.research_workspace.embedding_service import get_embedding_service
        self.embedding_service = get_embedding_service()

    def rank(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        """用 HyDE 语义相似度排序

        Args:
            results: 搜索结果列表
            query: 原始查询

        Returns:
            按 relevance_score 降序排列的结果列表
        """
        if not results:
            return results

        if not query or not query.strip():
            return results

        # 1. 生成假设性摘要
        try:
            from src.agents_v3.research_workspace.search.query_optimizer import hyde_query
            hypothetical = hyde_query(query)
        except Exception as e:
            logger.warning(f"HyDE query generation failed: {e}")
            hypothetical = ""

        if not hypothetical:
            logger.warning("HyDE: no hypothetical abstract generated, falling back to original query")
            hypothetical = query

        logger.info(f"HyDE: generated {len(hypothetical)} chars hypothetical abstract")

        # 2. 嵌入假设性摘要
        try:
            query_emb = self.embedding_service.embed_query(hypothetical)
        except Exception as e:
            logger.error(f"HyDE: failed to embed query: {e}")
            return results

        # 3. 批量嵌入所有论文
        texts = []
        for r in results:
            title = r.title or ""
            abstract = (r.abstract or "")[:500]
            texts.append(f"{title}. {abstract}")

        try:
            paper_embs = self.embedding_service.embed_texts(texts)
        except Exception as e:
            logger.error(f"HyDE: failed to embed papers: {e}")
            return results

        # 4. 计算 cosine similarity
        for i, r in enumerate(results):
            sim = _cosine_similarity(query_emb, paper_embs[i])
            r.relevance_score = round(max(0.0, sim), 3)

        # 5. 计算 final_score（relevance + quality）
        for r in results:
            quality = r.quality_score or 0.0
            r.final_score = round(0.75 * r.relevance_score + 0.25 * quality, 3)

        # 6. 按 final_score 降序排列
        results.sort(key=lambda r: r.final_score, reverse=True)

        for i, r in enumerate(results):
            r.source_rank = i + 1

        logger.info(f"HyDE ranker: scored {len(results)} results, top score={results[0].final_score:.3f}")
        return results
