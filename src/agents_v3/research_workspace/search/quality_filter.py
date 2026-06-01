"""两阶段过滤 — 先相关性，再质量

Stage 1: filter_by_relevance() — 按 relevance_score 阈值过滤
Stage 2: filter_by_quality()   — 按 quality_score 阈值过滤
"""

from __future__ import annotations

import math
from datetime import datetime

from loguru import logger

from src.agents_v3.research_workspace.search.base import SearchResult


# ── 质量分计算 ──────────────────────────────────────────

def compute_quality(result: SearchResult, max_citations: int = 1) -> float:
    """计算单篇论文的质量分

    质量分 = 0.75 × 引用数 + 0.10 × 引用速度 + 0.15 × 新近性

    Args:
        result: 搜索结果
        max_citations: 当前批次的最大引用数（用于归一化）

    Returns:
        质量分，范围 [0, 1]
    """
    citation = _citation_norm(result.citations, max_citations)
    velocity = _citation_velocity(result, max_citations)
    recency = _recency_score(result.year)
    return 0.75 * citation + 0.10 * velocity + 0.15 * recency


def compute_quality_batch(results: list[SearchResult]) -> list[float]:
    """批量计算质量分

    Args:
        results: 搜索结果列表

    Returns:
        质量分列表，与 results 一一对应
    """
    if not results:
        return []

    max_citations = max((r.citations or 0) for r in results) or 1
    return [compute_quality(r, max_citations) for r in results]


def _citation_norm(citations: int | None, max_citations: int = 1) -> float:
    """引用数归一化（平方根归一化）"""
    if not citations or citations <= 0:
        return 0.0
    return math.sqrt(citations) / math.sqrt(max(max_citations, 1))


def _citation_velocity(result: SearchResult, max_citations: int = 1) -> float:
    """引用速度 = citations / age，log 压缩归一化"""
    if not result.citations or result.citations <= 0:
        return 0.0
    if not result.year:
        return _citation_norm(result.citations, max_citations)
    age = max(1, datetime.now().year - result.year)
    velocity = result.citations / age
    return min(1.0, math.log(1 + velocity) / math.log(1 + max(max_citations, 1)))


def _recency_score(year: int | None) -> float:
    """新近性 = e^(-0.08 × age)，指数衰减"""
    if not year:
        return 0.3
    age = max(0, datetime.now().year - year)
    return math.exp(-0.08 * age)


# ── 过滤函数 ──────────────────────────────────────────

def filter_by_relevance(
    results: list[SearchResult],
    threshold: float = 0.5,
    min_results: int = 3,
) -> list[SearchResult]:
    """阶段1：按 relevance_score 过滤

    Args:
        results: 搜索结果列表（需已按 relevance_score 排序）
        threshold: relevance_score 阈值，低于此值的论文被过滤
        min_results: 最少保留的结果数（避免过滤过严）

    Returns:
        过滤后的结果列表
    """
    if not results:
        return []

    filtered = [r for r in results if (r.relevance_score or 0) >= threshold]

    # 保底：如果过滤后太少，保留 top-N
    if len(filtered) < min_results and len(results) > min_results:
        logger.info(
            f"Relevance filter: {len(filtered)} < {min_results}, "
            f"keeping top {min_results} by relevance"
        )
        filtered = results[:min_results]

    logger.info(
        f"Relevance filter (threshold={threshold}): "
        f"{len(results)} → {len(filtered)} papers"
    )
    return filtered


def filter_by_quality(
    results: list[SearchResult],
    threshold: float = 0.3,
    min_results: int = 3,
) -> list[SearchResult]:
    """阶段2：按 quality_score 过滤

    Args:
        results: 搜索结果列表
        threshold: quality_score 阈值，低于此值的论文被过滤
        min_results: 最少保留的结果数

    Returns:
        过滤后的结果列表
    """
    if not results:
        return []

    # 确保 quality_score 已计算
    for r in results:
        if not r.quality_score:
            r.quality_score = compute_quality(r)

    filtered = [r for r in results if (r.quality_score or 0) >= threshold]

    # 保底
    if len(filtered) < min_results and len(results) > min_results:
        logger.info(
            f"Quality filter: {len(filtered)} < {min_results}, "
            f"keeping top {min_results} by quality"
        )
        results.sort(key=lambda r: r.quality_score or 0, reverse=True)
        filtered = results[:min_results]

    logger.info(
        f"Quality filter (threshold={threshold}): "
        f"{len(results)} → {len(filtered)} papers"
    )
    return filtered


def two_stage_filter(
    results: list[SearchResult],
    relevance_threshold: float = 0.5,
    quality_threshold: float = 0.3,
    min_results: int = 3,
) -> list[SearchResult]:
    """两阶段过滤：先相关性，再质量

    Args:
        results: 搜索结果列表（需已排序）
        relevance_threshold: 相关性阈值
        quality_threshold: 质量阈值
        min_results: 每阶段最少保留数

    Returns:
        两阶段过滤后的结果列表
    """
    # 计算质量分
    for r in results:
        if not r.quality_score:
            r.quality_score = compute_quality(r)

    # 阶段1: 相关性过滤
    relevant = filter_by_relevance(results, relevance_threshold, min_results)

    # 阶段2: 质量过滤
    quality = filter_by_quality(relevant, quality_threshold, min_results)

    return quality
