"""搜索质量测试 — LLM-as-Judge 评估搜索结果相关性

流程：Hybrid 搜索 → LLM 判断全部结果 → 生成报告

用法:
    python -m tests.search_quality.test_search_quality
"""

from __future__ import annotations

import time
from datetime import datetime

from loguru import logger

TEST_QUERY = "sparse functional data for deep learning"
SOURCES = ["openalex", "arxiv", "semantic_scholar"]
LIMIT = 50


# ── LLM-as-Judge ──────────────────────────────────────

_JUDGE_PROMPT = """## 角色
你是学术论文相关性判断专家。

## 任务
判断每篇论文是否与查询主题**真正相关**。

## 判断标准
- 论文的**核心研究主题**必须与查询主题一致或高度相关
- 仅在标题/摘要中出现查询关键词，但研究主题不同的，判定为不相关
- 综述论文如果覆盖了查询主题，判定为相关
- 应用论文如果主要应用了查询中的方法/技术，判定为相关

## 输出格式
返回 JSON 数组，每篇论文一个判定：
```json
[{"id": 1, "relevant": true, "reason": "简短原因"}, {"id": 2, "relevant": false, "reason": "简短原因"}]
```"""


def _judge_batch(batch: list, query: str, start_idx: int, llm) -> tuple[list[bool], list[str]]:
    """判断一批论文的相关性"""
    import time as _time
    from src.agents_v3.research_workspace.llm.json_utils import extract_json

    lines = []
    for i, r in enumerate(batch, start_idx + 1):
        title = r.title or "(无标题)"
        abstract = (r.abstract or "")[:400]
        if len(r.abstract or "") > 400:
            abstract += "..."
        lines.append(f"[{i}] {title}\n    摘要: {abstract}")

    papers_text = "\n".join(lines)
    user_prompt = f"查询主题：{query}\n\n论文列表：\n{papers_text}"

    for attempt in range(3):
        try:
            response = llm.invoke(_JUDGE_PROMPT, user_prompt)
            parsed = extract_json(response)
            break
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 10 * (attempt + 1)
                logger.warning(f"LLM 429, waiting {wait}s...")
                _time.sleep(wait)
            else:
                raise

    if not isinstance(parsed, list):
        return [False] * len(batch), ["LLM返回非列表"] * len(batch)

    judge_map = {}
    for item in parsed:
        if isinstance(item, dict):
            jid = item.get("id")
            judge_map[jid] = (item.get("relevant", False), item.get("reason", ""))

    judgments = []
    reasons = []
    for i in range(start_idx + 1, start_idx + len(batch) + 1):
        rel, reason = judge_map.get(i, (False, "LLM未返回判定"))
        judgments.append(rel)
        reasons.append(reason)

    return judgments, reasons


def llm_judge(results: list, query: str) -> tuple[list[bool], list[str]]:
    """用 LLM 判断每篇论文是否与查询真正相关（分批处理）"""
    if not results:
        return [], []

    try:
        from src.agents_v3.research_workspace.llm.service import get_llm_service
        llm = get_llm_service()

        batch_size = 20
        all_judgments = []
        all_reasons = []

        for start in range(0, len(results), batch_size):
            batch = results[start:start + batch_size]
            try:
                judgments, reasons = _judge_batch(batch, query, start, llm)
                all_judgments.extend(judgments)
                all_reasons.extend(reasons)
            except Exception as e:
                logger.warning(f"LLM judge batch {start}-{start+len(batch)} failed: {e}")
                all_judgments.extend([False] * len(batch))
                all_reasons.extend([f"LLM调用失败: {e}"] * len(batch))
            if start + batch_size < len(results):
                time.sleep(5)

        n_rel = sum(all_judgments)
        logger.info(f"LLM judge: {n_rel}/{len(results)} relevant for: {query[:50]}")
        return all_judgments, all_reasons

    except Exception as e:
        logger.warning(f"LLM judge failed: {e}")
        return [False] * len(results), [f"LLM调用失败: {e}"] * len(results)


# ── 搜索 ──────────────────────────────────────────────

def search_hybrid() -> tuple[list, float, str]:
    """Hybrid: dense (HyDE embedding) + sparse (TF-IDF) + RRF 融合排序"""
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.query_optimizer import refine_query
    from src.agents_v3.research_workspace.search.hybrid_ranker import HybridRanker

    t0 = time.time()

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
    hybrid_ranker = HybridRanker()
    ranked = hybrid_ranker.rank(merged, TEST_QUERY)

    elapsed = time.time() - t0
    return ranked, elapsed, optimized


# ── 报告 ──────────────────────────────────────────────

def build_report(
    hybrid_results, hybrid_judgments, hybrid_reasons, hybrid_time, optimized_query,
) -> str:
    """生成完整测试报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    n_hybrid = len(hybrid_results)
    n_hybrid_rel = sum(hybrid_judgments)
    prec_hybrid = n_hybrid_rel / max(n_hybrid, 1)

    lines = [
        "# 搜索质量测试报告（LLM-as-Judge）",
        "",
        f"**测试时间**: {now}",
        f"**原始查询**: `{TEST_QUERY}`",
    ]
    if optimized_query and optimized_query != TEST_QUERY:
        lines.append(f"**优化查询**: `{optimized_query}`")
    lines.extend([
        f"**数据源**: OpenAlex, arXiv, Semantic Scholar",
        f"**返回数量上限**: {LIMIT}",
        "",
        "## 评估方法",
        "",
        "使用 LLM-as-Judge 对搜索到的**全部论文**进行相关性判断。",
        "",
        "**判断标准**: 论文的核心研究主题必须与查询一致或高度相关。",
        "",
        "## 结果汇总",
        "",
        "| 方案 | 耗时 | 总数 | LLM判定相关 | 精准率 |",
        "|------|------|------|------------|--------|",
        f"| Hybrid | {hybrid_time:.1f}s | {n_hybrid} | {n_hybrid_rel} | {prec_hybrid:.0%} |",
        "",
    ])

    # 详细结果
    lines.extend(["", "## Hybrid 结果（LLM 判定）", ""])
    lines.append("| # | 相关 | dense_score | quality | LLM原因 | 标题 |")
    lines.append("|---|------|-------------|---------|---------|------|")
    for i, (r, rel, reason) in enumerate(zip(hybrid_results, hybrid_judgments, hybrid_reasons), 1):
        mark = "Y" if rel else "N"
        dense_s = r.dense_score or 0
        qual_s = r.quality_score or 0
        title = (r.title or "(无标题)")[:50]
        reason_short = reason[:30] if reason else ""
        lines.append(f"| {i} | {mark} | {dense_s:.3f} | {qual_s:.3f} | {reason_short} | {title} |")

    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────

def main():
    print("=" * 60)
    print("搜索质量测试（LLM-as-Judge）")
    print("=" * 60)
    print(f"查询: {TEST_QUERY}")

    # 1. Hybrid 搜索
    print("\n[1/2] 正在执行 Hybrid 搜索...")
    hybrid_results, hybrid_time, optimized_query = search_hybrid()
    print(f"  优化查询: \"{TEST_QUERY}\" → \"{optimized_query}\"")
    print(f"  搜索完成: {len(hybrid_results)} 篇, 耗时 {hybrid_time:.1f}s")
    if not hybrid_results:
        print("  搜索无结果，退出")
        return

    # 2. LLM 判断
    print(f"\n[2/2] LLM 正在判断 {len(hybrid_results)} 篇论文相关性...")
    hybrid_judgments, hybrid_reasons = llm_judge(hybrid_results, TEST_QUERY)
    n_rel = sum(hybrid_judgments)
    print(f"  LLM判定: {n_rel}/{len(hybrid_results)} 相关")

    # 汇总
    print(f"\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    print(f"{'方案':<30} {'总数':>4} {'相关':>4} {'精准率':>6}")
    print("-" * 50)
    print(f"{'Hybrid':<30} {len(hybrid_results):>4} {n_rel:>4} {n_rel/max(len(hybrid_results),1):>5.0%}")

    # 写报告
    report = build_report(
        hybrid_results, hybrid_judgments, hybrid_reasons, hybrid_time, optimized_query,
    )
    report_path = "docs/search-quality-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已写入: {report_path}")


if __name__ == "__main__":
    main()
