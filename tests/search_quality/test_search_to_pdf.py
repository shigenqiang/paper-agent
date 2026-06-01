"""搜索 → PDF下载 → 解析 全链路测试

流程：
1. 搜索论文（原始 + HyDE）
2. LLM-as-Judge 判定相关性
3. 对相关论文下载 PDF
4. 解析 PDF 生成 chunks
5. 生成测试报告

用法:
    python -m tests.search_quality.test_search_to_pdf
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

TEST_QUERY = "sparse functional data for deep learning"
SOURCES = ["openalex", "arxiv", "semantic_scholar"]
LIMIT = 50
MAX_PDF_DOWNLOAD = 10  # 最多下载解析几篇相关论文
PROJECT_ID = "test_search_to_pdf"


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
    """用 LLM 判断每篇论文是否与查询真正相关"""
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

def search_raw() -> tuple[list, float, str]:
    """原始搜索"""
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


def search_hyde() -> tuple[list, float, str]:
    """HyDE 搜索（假设性摘要增强排序）"""
    from src.agents_v3.research_workspace.search.base import SearchQuery
    from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
    from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
    from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
    from src.agents_v3.research_workspace.search.merger import SearchResultMerger
    from src.agents_v3.research_workspace.search.ranking import RankingService
    from src.agents_v3.research_workspace.search.query_optimizer import refine_query, hyde_query

    t0 = time.time()
    hypothetical = hyde_query(TEST_QUERY)
    logger.info(f"HyDE: generated {len(hypothetical)} chars")

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
    ranking = RankingService(query=hypothetical)
    ranked = ranking.rank(merged, query=hypothetical)

    elapsed = time.time() - t0
    return ranked, elapsed, hypothetical


# ── PDF 下载与解析 ─────────────────────────────────────

def _search_result_to_paper_data(result, project_id: str) -> dict:
    """将 SearchResult 转为 Paper 存储格式"""
    paper_id = f"paper_{uuid.uuid4().hex[:8]}"
    return {
        "paper_id": paper_id,
        "project_id": project_id,
        "title": result.title or "",
        "abstract": result.abstract or "",
        "language": result.language or "",
        "publication_type": result.publication_type or "",
        "identifiers": {
            "doi": result.doi or "",
            "arxiv_id": result.arxiv_id or "",
            "pubmed_id": result.pubmed_id or "",
            "openalex_id": result.openalex_id or "",
            "semantic_scholar_id": result.semantic_scholar_id or "",
        },
        "authors": [{"name": a} for a in (result.authors or [])],
        "dates": {"year": result.year},
        "source": {"venue": result.venue or ""},
        "open_access": {
            "is_oa": bool(result.pdf_url),
            "pdf_url": result.pdf_url or "",
        },
        "classification": {
            "concepts": result.concepts or [],
            "keywords": result.keywords or [],
        },
        "citation": {"citation_count": result.citations},
        "url": result.url or "",
        "source_platform": result.source or "",
        "status": "imported",
        "pdf_path": "",
        "relevance_score": result.relevance_score or 0,
        "quality_score": result.quality_score or 0,
    }


def download_and_parse_papers(
    relevant_results: list,
    storage,
) -> list[dict]:
    """对相关论文执行 PDF 下载 + 解析

    Returns:
        每篇论文的解析结果列表
    """
    from src.agents_v3.research_workspace.parser_service import ParserService

    parser = ParserService(storage=storage)
    parse_results = []

    for i, result in enumerate(relevant_results):
        if i >= MAX_PDF_DOWNLOAD:
            break

        if not result.pdf_url:
            parse_results.append({
                "title": result.title,
                "pdf_url": "",
                "status": "no_pdf_url",
                "error": "No PDF URL available",
            })
            continue

        # 创建 Paper 数据
        paper_data = _search_result_to_paper_data(result, PROJECT_ID)
        paper_id = paper_data["paper_id"]

        # 写入 papers 集合
        storage.upsert_item("papers", paper_id, paper_data)

        # 写入 papers_pool（download_pdf 需要）
        pool_data = {
            "paper_id": paper_id,
            "title": result.title,
            "abstract": result.abstract or "",
            "pdf_url": result.pdf_url,
            "is_pdf_downloaded": False,
            "is_parsed": False,
            "source": result.source or "",
            "added_at": datetime.now().isoformat(),
        }
        storage.save_to_folder("papers_pool", paper_id, pool_data)

        logger.info(f"[{i+1}/{min(len(relevant_results), MAX_PDF_DOWNLOAD)}] Downloading: {result.title[:60]}")

        # 下载 PDF
        dl_result = parser.download_pdf(paper_id)
        if not dl_result.get("success"):
            parse_results.append({
                "title": result.title,
                "pdf_url": result.pdf_url,
                "status": "download_failed",
                "error": dl_result.get("error", "Unknown"),
            })
            continue

        logger.info(f"  PDF downloaded: {dl_result.get('pdf_path', '')}")

        # 解析 PDF
        try:
            parse_result = parser.parse_paper(paper_id, force=True)
            parse_results.append({
                "title": result.title,
                "pdf_url": result.pdf_url,
                "pdf_path": dl_result.get("pdf_path", ""),
                "paper_id": paper_id,
                "status": "parsed" if parse_result.get("success") else "parse_failed",
                "chunk_count": parse_result.get("chunk_count", 0),
                "body_chunk_count": parse_result.get("body_chunk_count", 0),
                "reference_count": parse_result.get("reference_count", 0),
                "page_count": parse_result.get("page_count", 0),
                "section_count": parse_result.get("section_count", 0),
                "quality_flags": parse_result.get("quality_flags", []),
                "error": parse_result.get("error", ""),
            })

            if parse_result.get("success"):
                # 读取 chunks 分析质量
                chunks = storage.query("paper_chunks", {"paper_id": paper_id})
                _analyze_chunks(chunks, parse_results[-1])
                logger.info(f"  Parsed: {parse_result.get('chunk_count')} chunks, "
                            f"{parse_result.get('page_count')} pages, "
                            f"{parse_result.get('section_count')} sections")
            else:
                logger.warning(f"  Parse failed: {parse_result.get('error')}")

        except Exception as e:
            logger.error(f"  Parse exception: {e}")
            parse_results.append({
                "title": result.title,
                "pdf_url": result.pdf_url,
                "status": "exception",
                "error": str(e),
            })

    return parse_results


def _analyze_chunks(chunks: list[dict], result: dict) -> None:
    """分析 chunk 质量并写入 result"""
    if not chunks:
        result["avg_chunk_tokens"] = 0
        result["section_types"] = {}
        result["quality_distribution"] = {}
        return

    # token 统计
    token_counts = [c.get("token_count", 0) for c in chunks]
    result["avg_chunk_tokens"] = sum(token_counts) / max(len(token_counts), 1)
    result["min_chunk_tokens"] = min(token_counts) if token_counts else 0
    result["max_chunk_tokens"] = max(token_counts) if token_counts else 0

    # section 类型分布
    section_types = {}
    for c in chunks:
        st = c.get("section_type", "unknown")
        section_types[st] = section_types.get(st, 0) + 1
    result["section_types"] = section_types

    # chunk_type 分布
    chunk_types = {}
    for c in chunks:
        ct = c.get("chunk_type", "unknown")
        chunk_types[ct] = chunk_types.get(ct, 0) + 1
    result["chunk_types"] = chunk_types

    # 引用数量
    ref_chunks = [c for c in chunks if c.get("chunk_type") == "reference"]
    result["ref_chunk_count"] = len(ref_chunks)


# ── 报告生成 ──────────────────────────────────────────

def build_report(
    raw_results, raw_judgments, raw_reasons, raw_time, optimized_query,
    hyde_results, hyde_judgments, hyde_reasons, hyde_time, hyde_abstract,
    parse_results: list[dict],
) -> str:
    """生成完整测试报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 统计
    n_raw = len(raw_results)
    n_raw_rel = sum(raw_judgments)
    n_hyde = len(hyde_results)
    n_hyde_rel = sum(hyde_judgments)

    # 合并去重的相关论文
    all_relevant_titles = set()
    for r, j in zip(raw_results, raw_judgments):
        if j:
            all_relevant_titles.add(r.title)
    for r, j in zip(hyde_results, hyde_judgments):
        if j:
            all_relevant_titles.add(r.title)

    # 解析统计
    n_downloaded = sum(1 for p in parse_results if p.get("pdf_path"))
    n_parsed = sum(1 for p in parse_results if p.get("status") == "parsed")
    n_failed = sum(1 for p in parse_results if p.get("status") in ("download_failed", "parse_failed", "exception"))
    total_chunks = sum(p.get("chunk_count", 0) for p in parse_results if p.get("status") == "parsed")
    total_body_chunks = sum(p.get("body_chunk_count", 0) for p in parse_results if p.get("status") == "parsed")

    lines = [
        "# 搜索 → PDF解析 全链路测试报告",
        "",
        f"**测试时间**: {now}",
        f"**原始查询**: `{TEST_QUERY}`",
    ]
    if optimized_query and optimized_query != TEST_QUERY:
        lines.append(f"**优化查询**: `{optimized_query}`")
    lines.extend([
        f"**数据源**: OpenAlex, arXiv, Semantic Scholar",
        f"**返回数量上限**: {LIMIT}",
        f"**PDF下载上限**: {MAX_PDF_DOWNLOAD}",
        "",
        "---",
        "",
        "## 1. 搜索结果概览",
        "",
        "| 搜索策略 | 总数 | LLM判定相关 | 精准率 |",
        "|----------|------|------------|--------|",
        f"| 原始搜索 | {n_raw} | {n_raw_rel} | {n_raw_rel/max(n_raw,1):.0%} |",
        f"| HyDE 排序 | {n_hyde} | {n_hyde_rel} | {n_hyde_rel/max(n_hyde,1):.0%} |",
        f"| 合并去重 | - | {len(all_relevant_titles)} | - |",
        "",
    ])

    # HyDE 摘要
    if hyde_abstract:
        lines.extend([
            "### HyDE 假设性摘要",
            "",
            f"> {hyde_abstract[:500]}",
            "",
        ])

    # 相关论文列表
    lines.extend([
        "## 2. LLM 判定相关论文",
        "",
        "| # | 来源 | relevance | quality | pdf_url | 标题 |",
        "|---|------|-----------|---------|---------|------|",
    ])
    idx = 0
    for r, j, reason in zip(raw_results, raw_judgments, raw_reasons):
        if j:
            idx += 1
            has_pdf = "Y" if r.pdf_url else "N"
            lines.append(f"| {idx} | raw | {r.relevance_score:.3f} | {r.quality_score:.3f} | {has_pdf} | {r.title[:60]} |")
    for r, j, reason in zip(hyde_results, hyde_judgments, hyde_reasons):
        if j and r.title not in {rr.title for rr, jj in zip(raw_results, raw_judgments) if jj}:
            idx += 1
            has_pdf = "Y" if r.pdf_url else "N"
            lines.append(f"| {idx} | hyde | {r.relevance_score:.3f} | {r.quality_score:.3f} | {has_pdf} | {r.title[:60]} |")

    # PDF 解析结果
    lines.extend([
        "",
        "## 3. PDF 下载与解析结果",
        "",
        f"- 尝试下载: {len(parse_results)} 篇",
        f"- 下载成功: {n_downloaded} 篇",
        f"- 解析成功: {n_parsed} 篇",
        f"- 失败: {n_failed} 篇",
        f"- 总 chunks: {total_chunks} (正文: {total_body_chunks})",
        "",
    ])

    # 每篇论文的解析详情
    if parse_results:
        lines.extend([
            "### 3.1 解析详情",
            "",
            "| # | 状态 | 页数 | sections | chunks | 正文chunks | 引用 | 标题 |",
            "|---|------|------|----------|--------|-----------|------|------|",
        ])
        for i, p in enumerate(parse_results, 1):
            status = p.get("status", "unknown")
            pages = p.get("page_count", "-")
            sections = p.get("section_count", "-")
            chunks = p.get("chunk_count", "-")
            body_chunks = p.get("body_chunk_count", "-")
            refs = p.get("reference_count", "-")
            title = p.get("title", "")[:50]
            error = p.get("error", "")
            status_display = status
            if error and status != "parsed":
                status_display = f"{status}: {error[:30]}"
            lines.append(f"| {i} | {status_display} | {pages} | {sections} | {chunks} | {body_chunks} | {refs} | {title} |")

    # chunk 质量分析
    parsed_papers = [p for p in parse_results if p.get("status") == "parsed" and p.get("section_types")]
    if parsed_papers:
        lines.extend([
            "",
            "### 3.2 Chunk 质量分析",
            "",
        ])
        for p in parsed_papers:
            lines.extend([
                f"**{p['title'][:60]}**",
                "",
                f"- 平均 chunk tokens: {p.get('avg_chunk_tokens', 0):.0f}",
                f"- 最小/最大 tokens: {p.get('min_chunk_tokens', 0)} / {p.get('max_chunk_tokens', 0)}",
                "",
                "Section 分布:",
                "",
                "| Section Type | 数量 |",
                "|-------------|------|",
            ])
            for st, count in sorted(p.get("section_types", {}).items(), key=lambda x: -x[1]):
                lines.append(f"| {st} | {count} |")

            if p.get("chunk_types"):
                lines.extend([
                    "",
                    "Chunk Type 分布:",
                    "",
                    "| Chunk Type | 数量 |",
                    "|-----------|------|",
                ])
                for ct, count in sorted(p.get("chunk_types", {}).items(), key=lambda x: -x[1]):
                    lines.append(f"| {ct} | {count} |")
            lines.append("")

    # 失败详情
    failed_papers = [p for p in parse_results if p.get("status") != "parsed" and p.get("status") != "no_pdf_url"]
    if failed_papers:
        lines.extend([
            "",
            "### 3.3 失败详情",
            "",
        ])
        for p in failed_papers:
            lines.extend([
                f"- **{p.get('title', '')[:60]}**",
                f"  - 状态: {p.get('status')}",
                f"  - PDF URL: `{p.get('pdf_url', '')}`",
                f"  - 错误: {p.get('error', 'N/A')}",
                "",
            ])

    # 分析总结
    lines.extend([
        "",
        "## 4. 分析总结",
        "",
        "### 搜索质量",
        "",
        f"- 原始搜索返回 {n_raw} 篇，LLM 判定 {n_raw_rel} 篇真正相关（精准率 {n_raw_rel/max(n_raw,1):.0%}）",
        f"- HyDE 排序找到 {n_hyde_rel} 篇相关论文",
        f"- 合并去重后共 {len(all_relevant_titles)} 篇独特相关论文",
        "",
        "### PDF 解析质量",
        "",
    ])

    if n_parsed > 0:
        avg_pages = sum(p.get("page_count", 0) for p in parse_results if p.get("status") == "parsed") / n_parsed
        avg_sections = sum(p.get("section_count", 0) for p in parse_results if p.get("status") == "parsed") / n_parsed
        avg_chunks = total_chunks / n_parsed
        lines.extend([
            f"- 成功解析 {n_parsed} 篇论文",
            f"- 平均页数: {avg_pages:.1f}",
            f"- 平均章节数: {avg_sections:.1f}",
            f"- 平均 chunk 数: {avg_chunks:.1f}",
            f"- 总正文 chunks: {total_body_chunks}",
        ])
    else:
        lines.append("- 未能成功解析任何论文")

    if n_failed > 0:
        lines.append(f"- {n_failed} 篇下载或解析失败")

    report = "\n".join(lines)
    return report


# ── 主流程 ────────────────────────────────────────────

def main():
    from src.agents_v3.research_workspace.storage import JSONStorage

    print("=" * 60)
    print("搜索 → PDF解析 全链路测试")
    print("=" * 60)
    print(f"查询: {TEST_QUERY}")

    # 初始化存储（使用独立项目目录避免污染正式数据）
    storage = JSONStorage(project_dir_name=PROJECT_ID)
    storage.ensure_dirs()
    print(f"存储目录: {storage.data_dir}")

    # 1. 原始搜索
    print("\n[1/5] 正在执行原始搜索...")
    raw_results, raw_time, optimized_query = search_raw()
    print(f"  优化查询: \"{TEST_QUERY}\" → \"{optimized_query}\"")
    print(f"  搜索完成: {len(raw_results)} 篇, 耗时 {raw_time:.1f}s")

    if not raw_results:
        print("  搜索无结果，退出")
        return

    # 2. LLM 判断原始搜索结果
    print(f"\n[2/5] LLM 正在判断 {len(raw_results)} 篇论文相关性...")
    raw_judgments, raw_reasons = llm_judge(raw_results, TEST_QUERY)
    n_raw_rel = sum(raw_judgments)
    print(f"  LLM判定: {n_raw_rel}/{len(raw_results)} 相关")

    # 3. HyDE 搜索
    print("\n[3/5] 正在执行 HyDE 搜索...")
    hyde_results, hyde_time, hyde_abstract = search_hyde()
    print(f"  HyDE: {len(hyde_results)} 篇, 耗时 {hyde_time:.1f}s")
    hyde_judgments, hyde_reasons = llm_judge(hyde_results, TEST_QUERY)
    n_hyde_rel = sum(hyde_judgments)
    print(f"  LLM判定: {n_hyde_rel}/{len(hyde_results)} 相关")

    # 4. 收集相关论文（合并去重），下载并解析 PDF
    print("\n[4/5] 正在下载并解析相关论文 PDF...")

    # 收集所有 LLM 判定相关的论文
    relevant_results = []
    seen_titles = set()
    for r, j in zip(raw_results, raw_judgments):
        if j and r.title not in seen_titles:
            relevant_results.append(r)
            seen_titles.add(r.title)
    for r, j in zip(hyde_results, hyde_judgments):
        if j and r.title not in seen_titles:
            relevant_results.append(r)
            seen_titles.add(r.title)

    # 按是否有 pdf_url 排序（有 pdf_url 的优先）
    relevant_results.sort(key=lambda r: (0 if r.pdf_url else 1, -(r.relevance_score or 0)))

    n_with_pdf = sum(1 for r in relevant_results if r.pdf_url)
    print(f"  相关论文: {len(relevant_results)} 篇, 其中有 PDF URL: {n_with_pdf} 篇")
    print(f"  将下载解析前 {min(n_with_pdf, MAX_PDF_DOWNLOAD)} 篇")

    parse_results = download_and_parse_papers(relevant_results, storage)
    n_parsed = sum(1 for p in parse_results if p.get("status") == "parsed")
    print(f"  解析完成: {n_parsed}/{len(parse_results)} 成功")

    # 5. 生成报告
    print("\n[5/5] 生成测试报告...")
    report = build_report(
        raw_results, raw_judgments, raw_reasons, raw_time, optimized_query,
        hyde_results, hyde_judgments, hyde_reasons, hyde_time, hyde_abstract,
        parse_results,
    )
    report_path = "docs/search-to-pdf-test-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"报告已写入: {report_path}")

    # 汇总
    print(f"\n{'='*60}")
    print("汇总")
    print(f"{'='*60}")
    print(f"搜索结果: {len(raw_results)} 篇 (原始), {len(hyde_results)} 篇 (HyDE)")
    print(f"LLM相关: {n_raw_rel} 篇 (原始), {n_hyde_rel} 篇 (HyDE)")
    print(f"PDF下载解析: {n_parsed}/{len(parse_results)} 成功")
    total_chunks = sum(p.get("chunk_count", 0) for p in parse_results if p.get("status") == "parsed")
    print(f"总 chunks: {total_chunks}")


if __name__ == "__main__":
    main()
