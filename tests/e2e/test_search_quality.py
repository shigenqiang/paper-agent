"""搜索质量对比测试 — 短语匹配 vs LLM 过滤 vs 无筛选

只调用一次 API，然后用同一批结果模拟不同筛选策略的对比。

用法:
    python -m tests.e2e.test_search_quality
"""

from __future__ import annotations

import time
from datetime import datetime

from loguru import logger

TEST_QUERY = "sparse functional data for deep learning"
SOURCES = ["openalex", "arxiv", "semantic_scholar"]
LIMIT = 20


def judge_relevance(results: list, query: str) -> list[bool]:
    """判断论文是否与查询真正相关

    标准：标题或摘要必须同时包含 "sparse" 和 "functional"
    """
    judgments = []
    for r in results:
        title = (r.title or "").lower()
        abstract = (r.abstract or "").lower()
        text = title + " " + abstract

        has_sparse = "sparse" in text
        has_functional = "functional" in text

        is_relevant = has_sparse and has_functional
        judgments.append(is_relevant)
    return judgments


def search_once() -> tuple[list, float]:
    """执行一次搜索（短语匹配 + 排序），返回结果和耗时"""
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService

    sq = SearchQuery(query=TEST_QUERY, sources=SOURCES, limit=LIMIT)
    adapters = [OpenAlexClient(), ArxivClient(), SemanticScholarClient()]
    merger = SearchResultMerger()

    t0 = time.time()

    all_results = []
    for adapter in adapters:
        try:
            results = adapter.search(sq)
            all_results.extend(results)
            logger.info(f"{adapter.source_name}: {len(results)} results")
        except Exception as e:
            logger.error(f"{adapter.source_name} failed: {e}")

    merged = merger.merge(all_results)
    ranking = RankingService(query=TEST_QUERY)
    ranked = ranking.rank(merged, query=TEST_QUERY)

    elapsed = time.time() - t0
    return ranked, elapsed


def llm_filter(results: list, query: str) -> tuple[list, float]:
    """LLM 相关性过滤，返回过滤结果和耗时"""
    from src.agents_v3.research_workspace.search.relevance_filter import filter_relevant_papers
    t0 = time.time()
    filtered = filter_relevant_papers(results, query)
    elapsed = time.time() - t0
    return filtered, elapsed


def print_results(label: str, results: list, judgments: list, elapsed: float):
    """打印测试结果"""
    n_relevant = sum(judgments)
    n_total = len(results)
    precision = n_relevant / max(n_total, 1)

    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"  耗时: {elapsed:.2f}s | 总数: {n_total} | 相关: {n_relevant} | 精准率: {precision:.0%}")
    print(f"  前10篇:")
    for i, (r, rel) in enumerate(zip(results[:10], judgments[:10])):
        mark = "V" if rel else "X"
        score = r.final_score or 0
        print(f"    [{mark}] {score:.3f} | {r.title[:65]}")

    return {
        "label": label,
        "elapsed": elapsed,
        "total": n_total,
        "relevant": n_relevant,
        "irrelevant": n_total - n_relevant,
        "precision": precision,
        "results": results,
        "judgments": judgments,
    }


def main():
    print("=" * 60)
    print("搜索质量对比测试")
    print("=" * 60)
    print(f"查询: {TEST_QUERY}")
    print(f"数据源: {', '.join(SOURCES)}")

    # 第一步：执行一次搜索
    print("\n正在搜索...")
    ranked, search_time = search_once()
    print(f"搜索完成: {len(ranked)} 篇, 耗时 {search_time:.2f}s")

    if not ranked:
        print("搜索无结果，退出")
        return

    all_reports = []

    # 场景1: 仅排序，无额外过滤（基线）
    judgments_1 = judge_relevance(ranked, TEST_QUERY)
    r1 = print_results(
        f"场景1: 短语匹配 + 排序（{search_time:.2f}s）",
        ranked, judgments_1, search_time,
    )
    all_reports.append(r1)

    # 场景2: 排序 + min_score 过滤（0.3）
    min_score = 0.3
    filtered_score = [r for r in ranked if (r.final_score or 0) >= min_score]
    judgments_2 = judge_relevance(filtered_score, TEST_QUERY)
    r2 = print_results(
        f"场景2: 短语匹配 + 排序 + min_score≥{min_score}（{search_time:.2f}s）",
        filtered_score, judgments_2, search_time,
    )
    all_reports.append(r2)

    # 场景3: 排序 + LLM 过滤
    print("\n正在执行 LLM 相关性过滤...")
    llm_filtered, llm_time = llm_filter(ranked, TEST_QUERY)
    judgments_3 = judge_relevance(llm_filtered, TEST_QUERY)
    total_time_3 = search_time + llm_time
    r3 = print_results(
        f"场景3: 短语匹配 + 排序 + LLM过滤（{total_time_3:.2f}s = 搜索{search_time:.2f}s + LLM{llm_time:.2f}s）",
        llm_filtered, judgments_3, total_time_3,
    )
    all_reports.append(r3)

    # 场景4: 排序 + min_score + LLM 过滤
    llm_filtered_2, llm_time_2 = llm_filter(filtered_score, TEST_QUERY)
    judgments_4 = judge_relevance(llm_filtered_2, TEST_QUERY)
    total_time_4 = search_time + llm_time_2
    r4 = print_results(
        f"场景4: 短语匹配 + 排序 + min_score≥{min_score} + LLM过滤（{total_time_4:.2f}s）",
        llm_filtered_2, judgments_4, total_time_4,
    )
    all_reports.append(r4)

    # 汇总
    print(f"\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    print(f"{'场景':<50} {'耗时':>6} {'总数':>4} {'相关':>4} {'精准率':>6}")
    print("-" * 70)
    for r in all_reports:
        print(f"{r['label']:<50} {r['elapsed']:>5.1f}s {r['total']:>4} {r['relevant']:>4} {r['precision']:>5.0%}")

    # 写入 MD 报告
    write_report(all_reports, search_time, llm_time)


def write_report(all_reports: list[dict], search_time: float, llm_time: float):
    """写入 MD 报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# 搜索质量对比测试报告",
        "",
        f"**测试时间**: {now}",
        f"**测试查询**: `{TEST_QUERY}`",
        f"**数据源**: OpenAlex, arXiv, Semantic Scholar",
        f"**返回数量上限**: {LIMIT}",
        "",
        "## 搜索耗时",
        "",
        f"| 阶段 | 耗时 |",
        f"|------|------|",
        f"| 搜索（短语匹配+去重+排序） | {search_time:.2f}s |",
        f"| LLM相关性过滤 | {llm_time:.2f}s |",
        f"| **总计** | **{search_time + llm_time:.2f}s** |",
        "",
        "## 测试方案说明",
        "",
        "| 方案 | 短语匹配 | min_score | LLM过滤 | 说明 |",
        "|------|---------|-----------|---------|------|",
        "| 场景1 | 开 | 关 | 关 | 仅短语匹配+排序 |",
        "| 场景2 | 开 | 0.3 | 关 | 短语匹配+排序+低分过滤 |",
        "| 场景3 | 开 | 关 | 开 | 短语匹配+排序+LLM相关性判断 |",
        "| 场景4 | 开 | 0.3 | 开 | 全部开启（推荐） |",
        "",
        "## 结果汇总",
        "",
        "| 方案 | 耗时 | 总数 | 相关 | 不相关 | 精准率 |",
        "|------|------|------|------|--------|--------|",
    ]

    for r in all_reports:
        lines.append(
            f"| {r['label'][:30]} | {r['elapsed']:.2f}s | {r['total']} | {r['relevant']} "
            f"| {r['irrelevant']} | {r['precision']:.0%} |"
        )

    lines.extend(["", "## 详细结果", ""])

    for r in all_reports:
        lines.extend([
            f"### {r['label'][:50]}",
            "",
            f"- 耗时: {r['elapsed']:.2f}s",
            f"- 精准率: {r['precision']:.0%} ({r['relevant']}/{r['total']})",
            "",
            "| # | 相关 | 分数 | 标题 |",
            "|---|------|------|------|",
        ])
        for i, (res, rel) in enumerate(zip(r["results"], r["judgments"]), 1):
            mark = "Y" if rel else "N"
            score = res.final_score or 0
            title = (res.title or "(无标题)")[:60]
            lines.append(f"| {i} | {mark} | {score:.3f} | {title} |")
        lines.append("")

    lines.extend([
        "## 分析",
        "",
        "### 相关性判断标准",
        "- 论文标题或摘要必须同时包含 `sparse` 和 `functional`",
        "- 仅包含 `deep learning`、`data` 等泛词的论文判定为不相关",
        "",
        "### Token 消耗",
        "",
        f"- LLM过滤消耗约 **1次 API 调用**，输入约 {LIMIT * 50} tokens（{LIMIT}篇论文标题+摘要），输出约 100 tokens",
        f"- LLM过滤耗时 **{llm_time:.1f}s**",
        "",
        "### 建议",
        "",
    ])

    if len(all_reports) >= 4:
        best = max(all_reports, key=lambda r: r["precision"])
        fastest = min(all_reports, key=lambda r: r["elapsed"])
        lines.append(f"- 最佳精准率: **{best['label'][:40]}** ({best['precision']:.0%})")
        lines.append(f"- 最快方案: **{fastest['label'][:40]}** ({fastest['elapsed']:.1f}s)")
        lines.append("")

        r1, r4 = all_reports[0], all_reports[-1]
        if r4["precision"] > r1["precision"]:
            gain = r4["precision"] - r1["precision"]
            lines.append(
                f"全方案（场景4）相比基线（场景1）精准率提升 **{gain:.0%}**，"
                f"额外耗时 {r4['elapsed'] - r1['elapsed']:.1f}s。"
            )

    report_path = "docs/search-quality-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n报告已写入: {report_path}")


if __name__ == "__main__":
    main()
