"""PDF 解析器对比测试 — 当前解析器 vs MinerU v1.3 vs Docling v2.x

测试维度：
1. 文本提取完整性（字符数、页数）
2. Section 识别能力
3. Markdown 输出质量
4. 解析速度
5. 双栏/复杂布局处理

用法:
    python -m tests.search_quality.test_pdf_parsers
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import tempfile
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

# 设置 HuggingFace 镜像（国内网络优化）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# ── 常量 ─────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = PROJECT_ROOT / "data" / "research_workspace" / "test_pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "research_workspace" / "parser_test_output"
REPORT_PATH = PROJECT_ROOT / "docs" / "pdf-parser-test-report.md"

PDF_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# arXiv 公开论文（覆盖不同布局类型）
ARXIV_PAPERS = [
    {
        "name": "attention_is_all_you_need",
        "url": "https://arxiv.org/pdf/1706.03762",
        "desc": "Attention Is All You Need (Transformer, 双栏 LaTeX)",
    },
    {
        "name": "bert",
        "url": "https://arxiv.org/pdf/1810.04805",
        "desc": "BERT (NLP, 双栏 LaTeX)",
    },
    {
        "name": "sparse_functional_data",
        "url": "https://arxiv.org/pdf/2301.05856",
        "desc": "Sparse Functional Data (统计学, 双栏 LaTeX)",
    },
]


# ── PDF 准备 ────────────────────────────────────────────


def collect_test_pdfs() -> list[dict]:
    """收集所有可用的测试 PDF"""
    pdfs = []

    # 已有的 arXiv 论文
    for paper in ARXIV_PAPERS:
        path = PDF_DIR / f"{paper['name']}.pdf"
        if path.exists():
            pdfs.append({"path": str(path), "desc": paper["desc"], "source": "arxiv"})
        else:
            # 尝试下载
            try:
                import urllib.request
                logger.info(f"Downloading: {paper['url']}")
                headers = {"User-Agent": "Mozilla/5.0 (research-tool)"}
                req = urllib.request.Request(paper["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    with open(path, "wb") as f:
                        f.write(resp.read())
                pdfs.append({"path": str(path), "desc": paper["desc"], "source": "arxiv"})
                logger.info(f"Downloaded: {path.name}")
            except Exception as e:
                logger.warning(f"Failed to download {paper['name']}: {e}")

    # 已下载的 IEEE 论文
    existing = [
        ("data/research_workspace/files/test_search_to_pdf/paper_85306019.pdf",
         "IEEE Multimodal ASD (IEEE 双栏)"),
        ("data/research_workspace/files/test_search_to_pdf/paper_8164fcee.pdf",
         "Deep-fUS IEEE (IEEE 双栏)"),
    ]
    for rel_path, desc in existing:
        path = PROJECT_ROOT / rel_path
        if path.exists():
            pdfs.append({"path": str(path), "desc": desc, "source": "ieee"})

    return pdfs


# ── 当前解析器（基线）────────────────────────────────────


def parse_with_current(pdf_path: str) -> dict:
    """用当前 pdfplumber/PyMuPDF/pdfminer 解析链"""
    try:
        from src.agents_v3.research_workspace.parser.service import ParserService
        from src.agents_v3.research_workspace.storage import JSONStorage

        storage = JSONStorage(project_dir_name="parser_test")
        parser = ParserService(storage=storage)

        t0 = time.time()
        pages_text, parser_name, quality_flags = parser._extract_with_fallback(pdf_path)

        if pages_text:
            pages_text = [(pn, parser._post_processor.process(t)) for pn, t in pages_text]
            pages_text = parser._post_processor.remove_headers_footers(pages_text)

        elapsed = time.time() - t0

        total_chars = sum(len(t) for _, t in pages_text) if pages_text else 0
        total_pages = len(pages_text) if pages_text else 0

        chunks = []
        if pages_text:
            chunks_data = parser._chunk_by_sections(pages_text, "test_paper")
            chunks_data = parser._chunk_cleaner.clean(chunks_data)
            chunks = chunks_data

        # 拼接全文用于质量对比
        full_text = "\n\n".join(t for _, t in pages_text) if pages_text else ""

        return {
            "parser": "current",
            "success": bool(pages_text),
            "pages": total_pages,
            "chars": total_chars,
            "chunks": len(chunks),
            "body_chunks": len([c for c in chunks if c.get("chunk_type") != "reference"]),
            "sections": len({c.get("section_type", "") for c in chunks if c.get("section_type")}),
            "quality_flags": quality_flags,
            "elapsed": round(elapsed, 2),
            "error": "",
            "full_text": full_text,
            "sample_text": full_text[:800],
        }
    except Exception as e:
        return {"parser": "current", "success": False, "error": str(e), "elapsed": 0,
                "full_text": "", "sample_text": ""}


# ── MinerU v1.3+ ────────────────────────────────────────


def parse_with_mineru(pdf_path: str) -> dict:
    """用 MinerU (magic-pdf >= 1.0) 解析

    使用 do_parse 接口，输出 Markdown 文件后读取。
    """
    try:
        from magic_pdf.tools.common import do_parse
    except ImportError as e:
        return {"parser": "mineru", "success": False, "error": f"Not installed: {e}",
                "elapsed": 0, "full_text": "", "sample_text": ""}

    t0 = time.time()
    pdf_name = Path(pdf_path).stem
    out_dir = OUTPUT_DIR / "mineru" / pdf_name

    # 清理旧输出
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        pdf_bytes = Path(pdf_path).read_bytes()

        do_parse(
            output_dir=str(out_dir),
            pdf_file_name=pdf_name,
            pdf_bytes_or_dataset=pdf_bytes,
            model_list=[],          # 空列表 = 不使用布局模型，纯文本提取
            parse_method="txt",     # txt 模式，不依赖 OCR 模型
            debug_able=False,
            f_dump_md=True,
            f_dump_middle_json=False,
            f_dump_model_json=False,
            f_dump_orig_pdf=False,
            f_dump_content_list=False,
        )

        elapsed = time.time() - t0

        # 读取输出的 Markdown
        md_path = out_dir / pdf_name / f"{pdf_name}.md"
        if not md_path.exists():
            # 尝试其他可能的路径
            candidates = list(out_dir.rglob("*.md"))
            if candidates:
                md_path = candidates[0]
            else:
                return {
                    "parser": "mineru", "success": False,
                    "error": "No markdown output found",
                    "elapsed": round(elapsed, 2), "full_text": "", "sample_text": "",
                }

        md_content = md_path.read_text(encoding="utf-8")
        lines = md_content.split("\n")
        total_chars = len(md_content)

        # 统计 sections（# 标记）
        section_names = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("# ").strip()
                if title:
                    section_names.append(title)

        return {
            "parser": "mineru",
            "success": True,
            "chars": total_chars,
            "lines": len(lines),
            "sections": len(section_names),
            "section_names": section_names[:20],
            "elapsed": round(elapsed, 2),
            "error": "",
            "full_text": md_content,
            "sample_text": md_content[:800],
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "parser": "mineru", "success": False, "error": str(e),
            "elapsed": round(elapsed, 2), "full_text": "", "sample_text": "",
        }


# ── Docling v2.x ────────────────────────────────────────


def parse_with_docling(pdf_path: str) -> dict:
    """用 Docling 解析"""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as e:
        return {"parser": "docling", "success": False, "error": f"Not installed: {e}",
                "elapsed": 0, "full_text": "", "sample_text": ""}

    t0 = time.time()
    try:
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        md_content = result.document.export_to_markdown()
        elapsed = time.time() - t0

        lines = md_content.split("\n")
        total_chars = len(md_content)

        section_names = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("# ").strip()
                if title:
                    section_names.append(title)

        return {
            "parser": "docling",
            "success": True,
            "chars": total_chars,
            "lines": len(lines),
            "sections": len(section_names),
            "section_names": section_names[:20],
            "elapsed": round(elapsed, 2),
            "error": "",
            "full_text": md_content,
            "sample_text": md_content[:800],
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "parser": "docling", "success": False, "error": str(e),
            "elapsed": round(elapsed, 2), "full_text": "", "sample_text": "",
        }


# ── 超时控制 ────────────────────────────────────────────


def run_with_timeout(fn, *args, timeout_sec: int = 300, **kwargs) -> dict:
    """在线程中运行函数，超时返回错误"""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            return {
                "parser": "unknown", "success": False,
                "error": f"Timeout after {timeout_sec}s",
                "elapsed": timeout_sec, "full_text": "", "sample_text": "",
            }


# ── 质量评估 ────────────────────────────────────────────


def evaluate_quality(result: dict) -> dict:
    """评估单个解析结果的质量"""
    if not result.get("success"):
        return {"score": 0, "issues": [result.get("error", "unknown error")]}

    text = result.get("full_text", "")
    issues = []
    score = 100

    # 1. 文本长度检查
    chars = len(text)
    if chars < 1000:
        issues.append(f"文本过短 ({chars} chars)")
        score -= 40
    elif chars < 3000:
        issues.append(f"文本偏短 ({chars} chars)")
        score -= 15

    # 2. Section 识别
    sections = result.get("sections", 0)
    if sections == 0:
        issues.append("未识别到任何 section")
        score -= 20
    elif sections < 3:
        issues.append(f"section 过少 ({sections})")
        score -= 10

    # 3. 乱码检测（连续非 ASCII 字符 > 20）
    import re
    garbled = re.findall(r'[^\x00-\x7f]{20,}', text)
    if garbled:
        issues.append(f"疑似乱码 {len(garbled)} 处")
        score -= 20

    # 4. 空行比例
    lines = text.split("\n")
    empty_lines = sum(1 for l in lines if not l.strip())
    if len(lines) > 0 and empty_lines / len(lines) > 0.5:
        issues.append(f"空行比例过高 ({empty_lines}/{len(lines)})")
        score -= 10

    # 5. 表格/公式残留检测
    table_artifacts = len(re.findall(r'\|.*\|.*\|', text))
    formula_noise = len(re.findall(r'^\s*[A-Z]\s*=\s*$', text, re.MULTILINE))

    return {
        "score": max(0, score),
        "issues": issues,
        "chars": chars,
        "sections": sections,
        "lines": len(lines),
        "empty_line_ratio": round(empty_lines / max(len(lines), 1), 2),
    }


# ── 报告生成 ────────────────────────────────────────────


def build_report(all_results: list[dict]) -> str:
    """生成对比报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# PDF 解析器对比测试报告",
        "",
        f"**测试时间**: {now}",
        f"**测试 PDF 数量**: {len(all_results)}",
        f"**解析器**: 当前解析器 (pdfplumber/PyMuPDF/pdfminer) / MinerU v1.3 / Docling v2.x",
        "",
        "---",
        "",
        "## 1. 结果汇总",
        "",
        "| # | PDF | 解析器 | 成功 | 字符数 | Sections | 耗时 | 质量分 |",
        "|---|-----|--------|------|--------|----------|------|--------|",
    ]

    idx = 0
    for item in all_results:
        for r in item["results"]:
            idx += 1
            pdf_desc = item["desc"][:35]
            parser = r.get("parser", "?")
            success = "OK" if r.get("success") else "FAIL"
            chars = r.get("chars", 0)
            sections = r.get("sections", "-")
            elapsed = r.get("elapsed", 0)
            quality = r.get("quality", {})
            score = quality.get("score", "-")
            lines.append(
                f"| {idx} | {pdf_desc} | {parser} | {success} | {chars:,} | {sections} | {elapsed}s | {score} |"
            )

    # 每篇论文的详细对比
    lines.extend(["", "---", "", "## 2. 详细对比", ""])

    for item in all_results:
        lines.extend([
            f"### {item['desc']}",
            "",
            f"- 文件: `{Path(item['path']).name}`",
            "",
        ])

        for r in item["results"]:
            parser = r.get("parser", "?")
            if r.get("success"):
                quality = r.get("quality", {})
                lines.extend([
                    f"#### {parser}",
                    "",
                    f"- 字符数: {r.get('chars', 0):,}",
                    f"- 耗时: {r.get('elapsed', 0)}s",
                    f"- 质量分: {quality.get('score', '-')}/100",
                ])
                if r.get("sections"):
                    lines.append(f"- Sections: {r['sections']}")
                if r.get("section_names"):
                    names = ", ".join(r["section_names"][:8])
                    lines.append(f"- Section 名称: {names}")
                if quality.get("issues"):
                    lines.append(f"- 问题: {'; '.join(quality['issues'])}")

                sample = r.get("sample_text", "")
                if sample:
                    lines.extend([
                        "",
                        "<details><summary>前 800 字符样本</summary>",
                        "",
                        "```",
                        sample,
                        "```",
                        "",
                        "</details>",
                    ])
            else:
                lines.extend([
                    f"#### {parser}",
                    "",
                    f"- 失败: `{r.get('error', 'Unknown')[:100]}`",
                ])
            lines.append("")

    # 横向对比矩阵
    lines.extend(["---", "", "## 3. 横向对比", ""])
    lines.append("| 维度 | 当前解析器 | MinerU | Docling |")
    lines.append("|------|-----------|--------|---------|")

    # 汇总统计
    for parser_name in ["current", "mineru", "docling"]:
        results = [
            r for item in all_results
            for r in item["results"]
            if r.get("parser") == parser_name
        ]
        successes = [r for r in results if r.get("success")]
        failures = [r for r in results if not r.get("success")]

        if parser_name == "current":
            _current_stats = {
                "success_rate": f"{len(successes)}/{len(results)}",
                "avg_chars": sum(r.get("chars", 0) for r in successes) / max(len(successes), 1),
                "avg_time": sum(r.get("elapsed", 0) for r in successes) / max(len(successes), 1),
                "avg_score": sum(r.get("quality", {}).get("score", 0) for r in successes) / max(len(successes), 1),
            }
        elif parser_name == "mineru":
            _mineru_stats = {
                "success_rate": f"{len(successes)}/{len(results)}",
                "avg_chars": sum(r.get("chars", 0) for r in successes) / max(len(successes), 1),
                "avg_time": sum(r.get("elapsed", 0) for r in successes) / max(len(successes), 1),
                "avg_score": sum(r.get("quality", {}).get("score", 0) for r in successes) / max(len(successes), 1),
            }
        else:
            _docling_stats = {
                "success_rate": f"{len(successes)}/{len(results)}",
                "avg_chars": sum(r.get("chars", 0) for r in successes) / max(len(successes), 1),
                "avg_time": sum(r.get("elapsed", 0) for r in successes) / max(len(successes), 1),
                "avg_score": sum(r.get("quality", {}).get("score", 0) for r in successes) / max(len(successes), 1),
            }

    stats_map = {
        "current": _current_stats,
        "mineru": _mineru_stats,
        "docling": _docling_stats,
    }

    lines.append(f"| 成功率 | {stats_map['current']['success_rate']} | "
                 f"{stats_map['mineru']['success_rate']} | {stats_map['docling']['success_rate']} |")
    lines.append(f"| 平均字符数 | {stats_map['current']['avg_chars']:,.0f} | "
                 f"{stats_map['mineru']['avg_chars']:,.0f} | {stats_map['docling']['avg_chars']:,.0f} |")
    lines.append(f"| 平均耗时 | {stats_map['current']['avg_time']:.1f}s | "
                 f"{stats_map['mineru']['avg_time']:.1f}s | {stats_map['docling']['avg_time']:.1f}s |")
    lines.append(f"| 平均质量分 | {stats_map['current']['avg_score']:.0f} | "
                 f"{stats_map['mineru']['avg_score']:.0f} | {stats_map['docling']['avg_score']:.0f} |")

    # 结论
    lines.extend([
        "",
        "---",
        "",
        "## 4. 结论",
        "",
        "### 各解析器特点",
        "",
        "**当前解析器 (pdfplumber/PyMuPDF/pdfminer)**:",
        "- 优势: 轻量、无需 GPU、与现有 ParserService 完全集成",
        "- 劣势: 复杂布局处理能力有限，依赖文本提取质量",
        "",
        "**MinerU**:",
        "- 优势: 学术 PDF 解析专用，支持布局分析、表格识别、公式检测",
        "- 劣势: 依赖较重（torch、transformers），txt 模式下功能受限",
        "",
        "**Docling**:",
        "- 优势: 多格式支持、结构化输出、API 简洁",
        "- 劣势: 学术 PDF 专项优化不如 MinerU",
        "",
        "### 建议",
        "",
        "基于测试结果，建议集成方案：",
        "1. 保留当前解析器作为轻量 fallback",
        "2. 添加 MinerU 作为高质量解析选项（学术 PDF 优先）",
        "3. 添加 Docling 作为 MinerU 的备选",
        "",
    ])

    return "\n".join(lines)


# ── 主流程 ──────────────────────────────────────────────


def main():
    print("=" * 60)
    print("PDF 解析器对比测试")
    print("=" * 60)

    # 1. 收集 PDF
    print("\n[1/4] 收集测试 PDF...")
    pdfs = collect_test_pdfs()
    print(f"  共 {len(pdfs)} 个 PDF")
    for p in pdfs:
        print(f"  - {p['desc']}: {Path(p['path']).name}")

    if not pdfs:
        print("  无可用 PDF，退出")
        return

    # 2-4. 测试各解析器
    parsers = [
        ("current", parse_with_current),
        ("mineru", parse_with_mineru),
        ("docling", parse_with_docling),
    ]

    all_results = []
    for p in pdfs:
        item = {"desc": p["desc"], "path": p["path"], "results": []}
        for parser_name, parser_fn in parsers:
            timeout = 60 if parser_name == "current" else 300
            print(f"\n  [{parser_name}] {p['desc'][:40]}... (timeout: {timeout}s)")
            result = run_with_timeout(parser_fn, p["path"], timeout_sec=timeout)

            # 质量评估
            result["quality"] = evaluate_quality(result)

            status = "[OK]" if result.get("success") else f"[FAIL] {result.get('error', '')[:50]}"
            score = result.get("quality", {}).get("score", "-")
            print(f"    {status} | {result.get('chars', 0):,} chars | {result.get('elapsed', 0)}s | score={score}")
            item["results"].append(result)

        all_results.append(item)

    # 5. 生成报告
    print("\n生成报告...")
    report = build_report(all_results)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"报告已写入: {REPORT_PATH}")

    # 同时保存原始 JSON 数据
    json_path = OUTPUT_DIR / "test_results.json"
    json_data = []
    for item in all_results:
        json_item = {"desc": item["desc"], "path": item["path"], "results": []}
        for r in item["results"]:
            r_copy = {k: v for k, v in r.items() if k not in ("full_text",)}
            json_item["results"].append(r_copy)
        json_data.append(json_item)
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"原始数据: {json_path}")

    # 汇总
    print(f"\n{'=' * 60}")
    print("汇总")
    print(f"{'=' * 60}")
    for item in all_results:
        print(f"\n{item['desc']}:")
        for r in item["results"]:
            parser = r.get("parser", "?")
            if r.get("success"):
                q = r.get("quality", {})
                print(f"  {parser}: OK | {r.get('chars', 0):,} chars | "
                      f"{r.get('elapsed', 0)}s | score={q.get('score', '-')}")
            else:
                print(f"  {parser}: FAIL | {r.get('error', '')[:60]}")


if __name__ == "__main__":
    main()
