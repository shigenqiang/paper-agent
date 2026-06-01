"""搜索质量测试 — LLM-as-Judge 评估搜索结果相关性

流程：搜索 → LLM 判断全部结果 → 对比不同过滤策略的效果

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

    # 带重试的 LLM 调用
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
    """用 LLM 判断每篇论文是否与查询真正相关（分批处理）

    Returns:
        (judgments, reasons): judgments[i] = True/False, reasons[i] = 原因
    """
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
            # 批次间延迟，避免 429
            if start + batch_size < len(results):
                time.sleep(5)

        n_rel = sum(all_judgments)
        logger.info(f"LLM judge: {n_rel}/{len(results)} relevant for: {query[:50]}")
        return all_judgments, all_reasons

    except Exception as e:
        logger.warning(f"LLM judge failed: {e}")
        return [False] * len(results), [f"LLM调用失败: {e}"] * len(results)


# ── 搜索 ──────────────────────────────────────────────

def search_raw() -> tuple[list, float, str]:
    """执行搜索，返回去重排序后的全部结果（不做任何过滤）"""
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
    from src.agents_v3.research_workspace.search.query_optimizer import refine_query

    t0 = time.time()

    optimized_query = refine_query(TEST_QUERY)
    logger.info(f"Query: \"{TEST_QUERY}\" → \"{optimized_query}\"")

    sq = SearchQuery(query=optimized_query, sources=SOURCES, limit=LIMIT)
    adapters = [OpenAlexClient(), ArxivClient(), SemanticScholarClient()]
    merger = SearchResultMerger()

    all_results = []
    for adapter in adapters:
        try:
            results = adapter.search(sq)
            all_results.extend(results)
            logger.info(f"{adapter.source_name}: {len(results)} results")
        except Exception as e:
            logger.error(f"{adapter.source_name} failed: {e}")

    merged = merger.merge(all_results)
    ranking = RankingService(query=optimized_query)
    ranked = ranking.rank(merged, query=optimized_query)

    elapsed = time.time() - t0
    return ranked, elapsed, optimized_query


def search_multi_query() -> tuple[list, float, list[str]]:
    """Multi-Query: 生成变体，分别搜索，合并去重"""
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
    from src.agents_v3.research_workspace.search.query_optimizer import multi_query, refine_query

    t0 = time.time()

    variants = multi_query(TEST_QUERY, n=4)
    all_queries = [TEST_QUERY] + variants
    logger.info(f"Multi-Query: {len(all_queries)} queries")

    adapters = [OpenAlexClient(), ArxivClient(), SemanticScholarClient()]
    merger = SearchResultMerger()
    all_results = []

    for q in all_queries:
        sq = SearchQuery(query=q, sources=SOURCES, limit=30)
        for adapter in adapters:
            try:
                results = adapter.search(sq)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"{adapter.source_name} failed for '{q}': {e}")

    merged = merger.merge(all_results)
    optimized = refine_query(TEST_QUERY)
    ranking = RankingService(query=optimized)
    ranked = ranking.rank(merged, query=optimized)

    elapsed = time.time() - t0
    return ranked, elapsed, variants


def search_hyde() -> tuple[list, float, str]:
    """HyDE: 生成假设性摘要，用 embedding cosine similarity 语义排序"""
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
    from src.agents_v3.research_workspace.search.query_optimizer import refine_query, hyde_query
    from src.agents_v3.research_workspace.search.hyde_ranker import HyDERanker

    t0 = time.time()

    hypothetical = hyde_query(TEST_QUERY)
    logger.info(f"HyDE: generated {len(hypothetical)} chars hypothetical abstract")

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

    # 先用 BM25 计算 quality_score（HyDE 需要）
    ranking = RankingService(query=optimized)
    ranked = ranking.rank(merged, query=optimized)

    # HyDE 语义排序：embedding cosine similarity
    hyde_ranker = HyDERanker()
    ranked = hyde_ranker.rank(ranked, TEST_QUERY)

    elapsed = time.time() - t0
    return ranked, elapsed, hypothetical


def search_hybrid() -> tuple[list, float, str]:
    """Hybrid: dense (HyDE embedding) + sparse (TF-IDF) + RRF 融合排序"""
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
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

    # 先用 BM25 计算基础排序
    ranking = RankingService(query=optimized)
    ranked = ranking.rank(merged, query=optimized)

    # Hybrid 排序：dense + sparse + RRF
    hybrid_ranker = HybridRanker()
    ranked = hybrid_ranker.rank(ranked, TEST_QUERY)

    elapsed = time.time() - t0
    return ranked, elapsed, "hybrid (dense+sparse+RRF)"


# ── 报告 ──────────────────────────────────────────────

def build_report(
    raw_results, raw_judgments, raw_reasons, raw_time,
    mq_results, mq_judgments, mq_reasons, mq_time, mq_variants,
    hyde_results, hyde_judgments, hyde_reasons, hyde_time, hyde_abstract,
    hybrid_results, hybrid_judgments, hybrid_reasons, hybrid_time,
    optimized_query,
) -> str:
    """生成完整测试报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rel_threshold = 0.80
    qual_threshold = 0.12

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
        "使用 LLM-as-Judge 对搜索到的**全部论文**进行相关性判断，",
        "以此作为 ground truth，评估不同过滤策略的效果。",
        "",
        "**判断标准**: 论文的核心研究主题必须与查询 \"sparse functional data\" 一致或高度相关，",
        "仅在标题/摘要中出现 \"sparse\" 和 \"functional\" 但研究主题不同的判定为不相关。",
        "",
    ])

    # ── 场景1: 全量结果 ──
    n_raw = len(raw_results)
    n_raw_rel = sum(raw_judgments)
    prec_raw = n_raw_rel / max(n_raw, 1)

    # ── 场景2: relevance ≥ 0.80 ──
    rel_filtered = [(r, j, reason) for r, j, reason in zip(raw_results, raw_judgments, raw_reasons) if (r.relevance_score or 0) >= rel_threshold]
    n_rel = len(rel_filtered)
    n_rel_rel = sum(1 for _, j, _ in rel_filtered if j)
    prec_rel = n_rel_rel / max(n_rel, 1)

    # ── 场景3: relevance + quality ──
    qual_filtered = [(r, j, reason) for r, j, reason in rel_filtered if (r.quality_score or 0) >= qual_threshold]
    n_qual = len(qual_filtered)
    n_qual_rel = sum(1 for _, j, _ in qual_filtered if j)
    prec_qual = n_qual_rel / max(n_qual, 1)

    # ── 场景4: Multi-Query ──
    n_mq = len(mq_results)
    n_mq_rel = sum(mq_judgments)
    prec_mq = n_mq_rel / max(n_mq, 1)

    # Multi-Query + relevance
    mq_rel_filtered = [(r, j) for r, j in zip(mq_results, mq_judgments) if (r.relevance_score or 0) >= rel_threshold]
    n_mq_rel_f = len(mq_rel_filtered)
    n_mq_rel_f_rel = sum(1 for _, j in mq_rel_filtered if j)
    prec_mq_rel = n_mq_rel_f_rel / max(n_mq_rel_f, 1)

    # ── 场景5: HyDE ──
    n_hyde = len(hyde_results)
    n_hyde_rel = sum(hyde_judgments)
    prec_hyde = n_hyde_rel / max(n_hyde, 1)

    # HyDE + relevance
    hyde_rel_filtered = [(r, j) for r, j in zip(hyde_results, hyde_judgments) if (r.relevance_score or 0) >= rel_threshold]
    n_hyde_rel_f = len(hyde_rel_filtered)
    n_hyde_rel_f_rel = sum(1 for _, j in hyde_rel_filtered if j)
    prec_hyde_rel = n_hyde_rel_f_rel / max(n_hyde_rel_f, 1)

    # ── 场景6: Hybrid ──
    n_hybrid = len(hybrid_results)
    n_hybrid_rel = sum(hybrid_judgments)
    prec_hybrid = n_hybrid_rel / max(n_hybrid, 1)

    # Hybrid + relevance
    hybrid_rel_filtered = [(r, j) for r, j in zip(hybrid_results, hybrid_judgments) if (r.relevance_score or 0) >= rel_threshold]
    n_hybrid_rel_f = len(hybrid_rel_filtered)
    n_hybrid_rel_f_rel = sum(1 for _, j in hybrid_rel_filtered if j)
    prec_hybrid_rel = n_hybrid_rel_f_rel / max(n_hybrid_rel_f, 1)

    lines.extend([
        "## 结果汇总",
        "",
        "| 方案 | 耗时 | 总数 | LLM判定相关 | 精准率 | 召回率 |",
        "|------|------|------|------------|--------|--------|",
        f"| 全量结果 | {raw_time:.1f}s | {n_raw} | {n_raw_rel} | {prec_raw:.0%} | 100% |",
        f"| relevance≥{rel_threshold} | {raw_time:.1f}s | {n_rel} | {n_rel_rel} | {prec_rel:.0%} | {n_rel_rel/max(n_raw_rel,1):.0%} |",
        f"| relevance+quality | {raw_time:.1f}s | {n_qual} | {n_qual_rel} | {prec_qual:.0%} | {n_qual_rel/max(n_raw_rel,1):.0%} |",
        f"| Multi-Query 全量 | {mq_time:.1f}s | {n_mq} | {n_mq_rel} | {prec_mq:.0%} | {n_mq_rel/max(n_raw_rel,1):.0%} |",
        f"| Multi-Query + relevance | {mq_time:.1f}s | {n_mq_rel_f} | {n_mq_rel_f_rel} | {prec_mq_rel:.0%} | {n_mq_rel_f_rel/max(n_raw_rel,1):.0%} |",
        f"| HyDE 全量 | {hyde_time:.1f}s | {n_hyde} | {n_hyde_rel} | {prec_hyde:.0%} | {n_hyde_rel/max(n_raw_rel,1):.0%} |",
        f"| HyDE + relevance | {hyde_time:.1f}s | {n_hyde_rel_f} | {n_hyde_rel_f_rel} | {prec_hyde_rel:.0%} | {n_hyde_rel_f_rel/max(n_raw_rel,1):.0%} |",
        f"| Hybrid 全量 | {hybrid_time:.1f}s | {n_hybrid} | {n_hybrid_rel} | {prec_hybrid:.0%} | {n_hybrid_rel/max(n_raw_rel,1):.0%} |",
        f"| Hybrid + relevance | {hybrid_time:.1f}s | {n_hybrid_rel_f} | {n_hybrid_rel_f_rel} | {prec_hybrid_rel:.0%} | {n_hybrid_rel_f_rel/max(n_raw_rel,1):.0%} |",
        "",
        "**召回率** = 该方案找到的 LLM 判定相关论文数 / 全量结果中 LLM 判定相关论文数",
        "",
    ])

    # Multi-Query 变体
    if mq_variants:
        lines.extend([
            "## Multi-Query 变体",
            "",
            f"原始查询: `{TEST_QUERY}`",
            "",
        ])
        for i, v in enumerate(mq_variants, 1):
            lines.append(f"{i}. `{v}`")

    # HyDE 摘要
    if hyde_abstract:
        lines.extend([
            "",
            "## HyDE 假设性摘要",
            "",
            "HyDE (Hypothetical Document Embeddings) 流程：LLM 生成假设性论文摘要 → 嵌入假设摘要 → 与论文嵌入计算 cosine similarity → 语义排序。",
            "",
            f"> {hyde_abstract[:500]}",
        ])

    # ── 详细结果：全量 ──
    lines.extend(["", "## 全量搜索结果（LLM 判定）", ""])
    lines.append("| # | 相关 | relevance | quality | LLM原因 | 标题 |")
    lines.append("|---|------|-----------|---------|---------|------|")
    for i, (r, rel, reason) in enumerate(zip(raw_results, raw_judgments, raw_reasons), 1):
        mark = "Y" if rel else "N"
        rel_s = r.relevance_score or 0
        qual_s = r.quality_score or 0
        title = (r.title or "(无标题)")[:50]
        reason_short = reason[:30] if reason else ""
        lines.append(f"| {i} | {mark} | {rel_s:.3f} | {qual_s:.3f} | {reason_short} | {title} |")

    # ── 详细结果：Multi-Query ──
    if mq_results:
        lines.extend(["", "## Multi-Query 结果（LLM 判定）", ""])
        lines.append("| # | 相关 | relevance | quality | LLM原因 | 标题 |")
        lines.append("|---|------|-----------|---------|---------|------|")
        for i, (r, rel, reason) in enumerate(zip(mq_results, mq_judgments, mq_reasons), 1):
            mark = "Y" if rel else "N"
            rel_s = r.relevance_score or 0
            qual_s = r.quality_score or 0
            title = (r.title or "(无标题)")[:50]
            reason_short = reason[:30] if reason else ""
            lines.append(f"| {i} | {mark} | {rel_s:.3f} | {qual_s:.3f} | {reason_short} | {title} |")

    # ── 详细结果：HyDE ──
    if hyde_results:
        lines.extend(["", "## HyDE 结果（LLM 判定）", ""])
        lines.append("| # | 相关 | relevance | quality | LLM原因 | 标题 |")
        lines.append("|---|------|-----------|---------|---------|------|")
        for i, (r, rel, reason) in enumerate(zip(hyde_results, hyde_judgments, hyde_reasons), 1):
            mark = "Y" if rel else "N"
            rel_s = r.relevance_score or 0
            qual_s = r.quality_score or 0
            title = (r.title or "(无标题)")[:50]
            reason_short = reason[:30] if reason else ""
            lines.append(f"| {i} | {mark} | {rel_s:.3f} | {qual_s:.3f} | {reason_short} | {title} |")

    # ── 详细结果：Hybrid ──
    if hybrid_results:
        lines.extend(["", "## Hybrid 结果（LLM 判定）", ""])
        lines.append("| # | 相关 | relevance | quality | LLM原因 | 标题 |")
        lines.append("|---|------|-----------|---------|---------|------|")
        for i, (r, rel, reason) in enumerate(zip(hybrid_results, hybrid_judgments, hybrid_reasons), 1):
            mark = "Y" if rel else "N"
            rel_s = r.relevance_score or 0
            qual_s = r.quality_score or 0
            title = (r.title or "(无标题)")[:50]
            reason_short = reason[:30] if reason else ""
            lines.append(f"| {i} | {mark} | {rel_s:.3f} | {qual_s:.3f} | {reason_short} | {title} |")

    # ── 分析 ──
    lines.extend([
        "",
        "## 分析",
        "",
        "### BM25 排序效果",
        "",
        f"全量 {n_raw} 篇论文中，LLM 判定 {n_raw_rel} 篇真正相关（精准率 {prec_raw:.0%}）。",
        f"relevance≥{rel_threshold} 过滤后剩 {n_rel} 篇，其中 {n_rel_rel} 篇相关（精准率 {prec_rel:.0%}，召回率 {n_rel_rel/max(n_raw_rel,1):.0%}）。",
        "",
        "### 各策略对比",
        "",
        f"| 策略 | 精准率 | 召回率 | 说明 |",
        f"|------|--------|--------|------|",
        f"| 全量 | {prec_raw:.0%} | 100% | 基线 |",
        f"| relevance≥{rel_threshold} | {prec_rel:.0%} | {n_rel_rel/max(n_raw_rel,1):.0%} | BM25阈值过滤 |",
        f"| Multi-Query | {prec_mq:.0%} | {n_mq_rel/max(n_raw_rel,1):.0%} | 多查询变体 |",
        f"| HyDE | {prec_hyde:.0%} | {n_hyde_rel/max(n_raw_rel,1):.0%} | 假设文档嵌入语义排序 |",
        f"| Hybrid | {prec_hybrid:.0%} | {n_hybrid_rel/max(n_raw_rel,1):.0%} | dense+sparse+RRF混合排序 |",
        "",
    ])

    report = "\n".join(lines)
    return report


# ── 主流程 ────────────────────────────────────────────

def main():
    print("=" * 60)
    print("搜索质量测试（LLM-as-Judge）")
    print("=" * 60)
    print(f"查询: {TEST_QUERY}")

    # 1. 全量搜索
    print("\n[1/5] 正在搜索...")
    raw_results, raw_time, optimized_query = search_raw()
    print(f"  优化查询: \"{TEST_QUERY}\" → \"{optimized_query}\"")
    print(f"  搜索完成: {len(raw_results)} 篇, 耗时 {raw_time:.1f}s")
    if not raw_results:
        print("  搜索无结果，退出")
        return

    # 2. LLM 判断全量结果
    print(f"\n[2/5] LLM 正在判断 {len(raw_results)} 篇论文相关性...")
    raw_judgments, raw_reasons = llm_judge(raw_results, TEST_QUERY)
    n_rel = sum(raw_judgments)
    print(f"  LLM判定: {n_rel}/{len(raw_results)} 相关")

    # 3. Multi-Query 搜索
    print("\n[3/5] 正在执行 Multi-Query 搜索...")
    mq_results, mq_time, mq_variants = search_multi_query()
    print(f"  Multi-Query: {len(mq_results)} 篇, 耗时 {mq_time:.1f}s")
    mq_judgments, mq_reasons = llm_judge(mq_results, TEST_QUERY)
    n_mq_rel = sum(mq_judgments)
    print(f"  LLM判定: {n_mq_rel}/{len(mq_results)} 相关")

    # 4. HyDE 搜索
    print("\n[4/5] 正在执行 HyDE 搜索...")
    hyde_results, hyde_time, hyde_abstract = search_hyde()
    print(f"  HyDE: {len(hyde_results)} 篇, 耗时 {hyde_time:.1f}s")
    hyde_judgments, hyde_reasons = llm_judge(hyde_results, TEST_QUERY)
    n_hyde_rel = sum(hyde_judgments)
    print(f"  LLM判定: {n_hyde_rel}/{len(hyde_results)} 相关")

    # 5. Hybrid 搜索
    print("\n[5/5] 正在执行 Hybrid 搜索（dense+sparse+RRF）...")
    hybrid_results, hybrid_time, hybrid_desc = search_hybrid()
    print(f"  Hybrid: {len(hybrid_results)} 篇, 耗时 {hybrid_time:.1f}s")
    hybrid_judgments, hybrid_reasons = llm_judge(hybrid_results, TEST_QUERY)
    n_hybrid_rel = sum(hybrid_judgments)
    print(f"  LLM判定: {n_hybrid_rel}/{len(hybrid_results)} 相关")

    # 汇总
    print(f"\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    print(f"{'方案':<30} {'总数':>4} {'相关':>4} {'精准率':>6}")
    print("-" * 50)
    print(f"{'全量结果':<30} {len(raw_results):>4} {n_rel:>4} {n_rel/max(len(raw_results),1):>5.0%}")
    print(f"{'Multi-Query':<30} {len(mq_results):>4} {n_mq_rel:>4} {n_mq_rel/max(len(mq_results),1):>5.0%}")
    print(f"{'HyDE':<30} {len(hyde_results):>4} {n_hyde_rel:>4} {n_hyde_rel/max(len(hyde_results),1):>5.0%}")
    print(f"{'Hybrid':<30} {len(hybrid_results):>4} {n_hybrid_rel:>4} {n_hybrid_rel/max(len(hybrid_results),1):>5.0%}")

    # 写报告
    report = build_report(
        raw_results, raw_judgments, raw_reasons, raw_time,
        mq_results, mq_judgments, mq_reasons, mq_time, mq_variants,
        hyde_results, hyde_judgments, hyde_reasons, hyde_time, hyde_abstract,
        hybrid_results, hybrid_judgments, hybrid_reasons, hybrid_time,
        optimized_query,
    )
    report_path = "docs/search-quality-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已写入: {report_path}")


if __name__ == "__main__":
    main()
