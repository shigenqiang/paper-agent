"""快速搜索质量评估 — 不依赖 LLM，用关键词匹配 + 人工检查 top-10

用法:
    python -m tests.search_quality.quick_eval
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from loguru import logger

TEST_QUERY = "sparse functional data for deep learning"
SOURCES = ["openalex", "arxiv", "semantic_scholar"]
LIMIT = 50

# 相关性关键词（标题/摘要中出现 ≥2 个视为相关）
CORE_KEYWORDS = [
    "sparse", "functional data", "functional regression",
    "deep learning", "neural network",
    "functional", "fda", "basis function",
]
CONTEXT_KEYWORDS = [
    "representation", "learning", "model", "prediction",
    "regression", "classification", "approximation",
]


def keyword_relevance(title: str, abstract: str) -> tuple[bool, list[str]]:
    """基于关键词判断相关性"""
    text = f"{title} {abstract}".lower()
    matched_core = [kw for kw in CORE_KEYWORDS if kw in text]
    matched_ctx = [kw for kw in CONTEXT_KEYWORDS if kw in text]

    # 核心关键词 ≥2 个，或 "sparse" + "functional" 同时出现
    is_relevant = (
        len(matched_core) >= 2
        or ("sparse" in text and "functional" in text)
        or ("functional data" in text and "deep learning" in text)
        or ("sparse" in text and "deep learning" in text and len(matched_ctx) >= 1)
    )
    return is_relevant, matched_core + matched_ctx


def search_raw():
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
    from src.agents_v3.research_workspace.search.query_optimizer import refine_query

    optimized = refine_query(TEST_QUERY)
    sq = SearchQuery(query=optimized, sources=SOURCES, limit=LIMIT)
    adapters = [OpenAlexClient(), ArxivClient(), SemanticScholarClient()]
    merger = SearchResultMerger()

    all_results = []
    for adapter in adapters:
        try:
            results = adapter.search(sq)
            all_results.extend(results)
        except Exception as e:
            logger.error(f"{adapter.source_name} failed: {e}")

    merged = merger.merge(all_results)
    ranking = RankingService(query=optimized)
    ranked = ranking.rank(merged, query=optimized)
    return ranked, optimized


def search_hyde(optimized: str):
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
    from src.agents_v3.research_workspace.search.hyde_ranker import HyDERanker

    sq = SearchQuery(query=optimized, sources=SOURCES, limit=LIMIT)
    adapters = [OpenAlexClient(), ArxivClient(), SemanticScholarClient()]
    merger = SearchResultMerger()

    all_results = []
    for adapter in adapters:
        try:
            results = adapter.search(sq)
            all_results.extend(results)
        except Exception as e:
            logger.error(f"{adapter.source_name} failed: {e}")

    merged = merger.merge(all_results)
    ranking = RankingService(query=optimized)
    ranked = ranking.rank(merged, query=optimized)

    hyde_ranker = HyDERanker()
    ranked = hyde_ranker.rank(ranked, TEST_QUERY)
    return ranked


def search_hybrid(optimized: str):
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
    from src.agents_v3.research_workspace.search.hybrid_ranker import HybridRanker

    sq = SearchQuery(query=optimized, sources=SOURCES, limit=LIMIT)
    adapters = [OpenAlexClient(), ArxivClient(), SemanticScholarClient()]
    merger = SearchResultMerger()

    all_results = []
    for adapter in adapters:
        try:
            results = adapter.search(sq)
            all_results.extend(results)
        except Exception as e:
            logger.error(f"{adapter.source_name} failed: {e}")

    merged = merger.merge(all_results)
    ranking = RankingService(query=optimized)
    ranked = ranking.rank(merged, query=optimized)

    hybrid_ranker = HybridRanker()
    ranked = hybrid_ranker.rank(ranked, TEST_QUERY)
    return ranked


def eval_strategy(name: str, results: list) -> dict:
    """评估一个策略的结果"""
    judgments = []
    matched_keywords = []
    for r in results:
        is_rel, kws = keyword_relevance(r.title or "", r.abstract or "")
        judgments.append(is_rel)
        matched_keywords.append(kws)

    n_total = len(results)
    n_relevant = sum(judgments)
    precision = n_relevant / max(n_total, 1)

    # Top-10 精准率
    top10_judgments = judgments[:10]
    top10_precision = sum(top10_judgments) / max(len(top10_judgments), 1)

    return {
        "name": name,
        "n_total": n_total,
        "n_relevant": n_relevant,
        "precision": precision,
        "top10_precision": top10_precision,
        "judgments": judgments,
        "matched_keywords": matched_keywords,
    }


def main():
    print("=" * 70)
    print("搜索质量快速评估（关键词匹配，无需 LLM）")
    print("=" * 70)
    print(f"查询: {TEST_QUERY}")
    print(f"相关性标准: 标题/摘要包含 ≥2 个核心关键词")
    print(f"核心关键词: {CORE_KEYWORDS}")
    print()

    # 1. BM25 基线
    print("[1/3] BM25 基线搜索...")
    t0 = time.time()
    raw_results, optimized = search_raw()
    bm25_time = time.time() - t0
    print(f"  结果: {len(raw_results)} 篇, 耗时 {bm25_time:.1f}s")

    # 2. HyDE
    print("[2/3] HyDE 语义搜索...")
    t0 = time.time()
    hyde_results = search_hyde(optimized)
    hyde_time = time.time() - t0
    print(f"  结果: {len(hyde_results)} 篇, 耗时 {hyde_time:.1f}s")

    # 3. Hybrid
    print("[3/3] Hybrid 混合搜索...")
    t0 = time.time()
    hybrid_results = search_hybrid(optimized)
    hybrid_time = time.time() - t0
    print(f"  结果: {len(hybrid_results)} 篇, 耗时 {hybrid_time:.1f}s")

    # 评估
    bm25_eval = eval_strategy("BM25", raw_results)
    hyde_eval = eval_strategy("HyDE", hyde_results)
    hybrid_eval = eval_strategy("Hybrid", hybrid_results)

    # 汇总
    print(f"\n{'='*70}")
    print("汇总结果")
    print(f"{'='*70}")
    print(f"{'方案':<12} {'耗时':>6} {'总数':>4} {'相关':>4} {'精准率':>7} {'Top10精准率':>11}")
    print("-" * 55)
    for ev, t in [(bm25_eval, bm25_time), (hyde_eval, hyde_time), (hybrid_eval, hybrid_time)]:
        print(f"{ev['name']:<12} {t:>5.1f}s {ev['n_total']:>4} {ev['n_relevant']:>4} {ev['precision']:>6.0%} {ev['top10_precision']:>10.0%}")

    # Top-10 详细结果
    for ev, results in [(bm25_eval, raw_results), (hyde_eval, hyde_results), (hybrid_eval, hybrid_results)]:
        print(f"\n{'='*70}")
        print(f"{ev['name']} — Top 10 结果")
        print(f"{'='*70}")
        for i, (r, is_rel, kws) in enumerate(zip(results[:10], ev["judgments"][:10], ev["matched_keywords"][:10])):
            mark = "Y" if is_rel else "N"
            title = (r.title or "(无标题)")[:65]
            rel_s = r.relevance_score or 0
            print(f"  {i+1:2}. [{mark}] {rel_s:.3f}  {title}")
            if kws:
                print(f"      keywords: {', '.join(kws[:5])}")

    # 写报告
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_lines = [
        "# 搜索质量快速评估报告",
        "",
        f"**测试时间**: {now}",
        f"**查询**: `{TEST_QUERY}`",
        f"**优化查询**: `{optimized}`",
        f"**评估方法**: 关键词匹配（无需 LLM）",
        f"**相关性标准**: 标题/摘要包含 ≥2 个核心关键词",
        f"**核心关键词**: {', '.join(CORE_KEYWORDS)}",
        "",
        "## 汇总",
        "",
        "| 方案 | 耗时 | 总数 | 相关 | 精准率 | Top10精准率 |",
        "|------|------|------|------|--------|-------------|",
    ]
    for ev, t in [(bm25_eval, bm25_time), (hyde_eval, hyde_time), (hybrid_eval, hybrid_time)]:
        report_lines.append(f"| {ev['name']} | {t:.1f}s | {ev['n_total']} | {ev['n_relevant']} | {ev['precision']:.0%} | {ev['top10_precision']:.0%} |")

    report_lines.extend([
        "",
        "## Top-10 对比",
        "",
    ])
    for ev, results in [(bm25_eval, raw_results), (hyde_eval, hyde_results), (hybrid_eval, hybrid_results)]:
        report_lines.extend([
            f"### {ev['name']}",
            "",
            "| # | 相关 | score | 标题 | 匹配关键词 |",
            "|---|------|-------|------|-----------|",
        ])
        for i, (r, is_rel, kws) in enumerate(zip(results[:10], ev["judgments"][:10], ev["matched_keywords"][:10])):
            mark = "Y" if is_rel else "N"
            title = (r.title or "(无标题)")[:55]
            rel_s = r.relevance_score or 0
            kw_str = ", ".join(kws[:4]) if kws else "-"
            report_lines.append(f"| {i+1} | {mark} | {rel_s:.3f} | {title} | {kw_str} |")
        report_lines.append("")

    report_path = "docs/quick-eval-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n报告已写入: {report_path}")


if __name__ == "__main__":
    main()
