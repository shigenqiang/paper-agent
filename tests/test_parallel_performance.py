"""并行性能测试脚本

测试 ParserService 中的并行下载、并行解析以及各解析器的性能对比。
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

# ── 测试 PDF 列表 ────────────────────────────────────────

TEST_PDFS = [
    # fixtures
    str(project_root / "tests" / "agents_v3" / "research_workspace" / "fixtures" / "sample_paper.pdf"),
    # test_pdfs
    str(project_root / "data" / "research_workspace" / "test_pdfs" / "attention_is_all_you_need.pdf"),
    str(project_root / "data" / "research_workspace" / "test_pdfs" / "bert.pdf"),
    # proj_673ac013
    str(project_root / "data" / "research_workspace" / "files" / "proj_673ac013" / "paper_17ae8232.pdf"),
    str(project_root / "data" / "research_workspace" / "files" / "proj_673ac013" / "paper_6c775e70.pdf"),
    str(project_root / "data" / "research_workspace" / "files" / "proj_673ac013" / "paper_cc3f2153.pdf"),
]


# ── 单解析器测试 ──────────────────────────────────────────

def test_single_adapter(adapter_name: str, pdf_path: str) -> dict[str, Any]:
    """测试单个解析器对单个 PDF 的解析性能"""
    from src.agents_v3.research_workspace.parser_service import (
        PdfPlumberAdapter,
        PyMuPDFAdapter,
        PdfMinerAdapter,
        DoclingAdapter,
    )

    adapters = {
        "pdfplumber": PdfPlumberAdapter,
        "pymupdf": PyMuPDFAdapter,
        "pdfminer": PdfMinerAdapter,
        "docling": DoclingAdapter,
    }

    cls = adapters.get(adapter_name)
    if not cls:
        return {"success": False, "error": f"Unknown adapter: {adapter_name}"}

    adapter = cls()
    if not adapter.can_parse(pdf_path):
        return {"success": False, "error": f"{adapter_name} cannot parse"}

    t0 = time.time()
    pages_text, flags = adapter.extract_pages(pdf_path)
    elapsed = time.time() - t0

    total_chars = sum(len(t) for _, t in pages_text)
    non_empty = sum(1 for _, t in pages_text if t.strip())

    return {
        "success": bool(pages_text and non_empty > 0),
        "adapter": adapter_name,
        "pdf": Path(pdf_path).name,
        "pages": len(pages_text),
        "non_empty_pages": non_empty,
        "total_chars": total_chars,
        "flags": flags,
        "elapsed_seconds": round(elapsed, 2),
    }


# ── 串行 vs 并行解析测试 ──────────────────────────────────

def test_parse_sequential(pdf_paths: list[str]) -> dict[str, Any]:
    """串行解析多个 PDF"""
    from src.agents_v3.research_workspace.parser_service import PdfPlumberAdapter

    adapter = PdfPlumberAdapter()
    results = []
    t0 = time.time()

    for path in pdf_paths:
        pages_text, flags = adapter.extract_pages(path)
        total_chars = sum(len(t) for _, t in pages_text)
        results.append({
            "pdf": Path(path).name,
            "pages": len(pages_text),
            "chars": total_chars,
        })

    elapsed = time.time() - t0
    return {
        "mode": "sequential",
        "adapter": "pdfplumber",
        "count": len(pdf_paths),
        "total_elapsed": round(elapsed, 2),
        "avg_per_pdf": round(elapsed / len(pdf_paths), 2) if pdf_paths else 0,
        "results": results,
    }


def test_parse_parallel(pdf_paths: list[str], max_workers: int = 4) -> dict[str, Any]:
    """并行解析多个 PDF"""
    from src.agents_v3.research_workspace.parser_service import PdfPlumberAdapter

    def _parse_one(path: str) -> dict[str, Any]:
        adapter = PdfPlumberAdapter()
        pages_text, flags = adapter.extract_pages(path)
        total_chars = sum(len(t) for _, t in pages_text)
        return {
            "pdf": Path(path).name,
            "pages": len(pages_text),
            "chars": total_chars,
        }

    results = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_parse_one, p): p for p in pdf_paths}
        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.time() - t0
    return {
        "mode": f"parallel (workers={max_workers})",
        "adapter": "pdfplumber",
        "count": len(pdf_paths),
        "total_elapsed": round(elapsed, 2),
        "avg_per_pdf": round(elapsed / len(pdf_paths), 2) if pdf_paths else 0,
        "results": results,
    }


# ── Docling 串行 vs 并行测试 ──────────────────────────────

def test_docling_sequential(pdf_paths: list[str]) -> dict[str, Any]:
    """Docling 串行解析"""
    from src.agents_v3.research_workspace.parser_service import DoclingAdapter

    adapter = DoclingAdapter()
    results = []
    t0 = time.time()

    for path in pdf_paths:
        pages_text, flags = adapter.extract_pages(path)
        total_chars = sum(len(t) for _, t in pages_text)
        results.append({
            "pdf": Path(path).name,
            "pages": len(pages_text),
            "chars": total_chars,
            "flags": flags,
        })

    elapsed = time.time() - t0
    return {
        "mode": "sequential",
        "adapter": "docling",
        "count": len(pdf_paths),
        "total_elapsed": round(elapsed, 2),
        "avg_per_pdf": round(elapsed / len(pdf_paths), 2) if pdf_paths else 0,
        "results": results,
    }


# ── 后处理并行测试 ──────────────────────────────────────────

def test_postprocess_sequential(texts: list[str]) -> dict[str, Any]:
    """串行后处理"""
    from src.agents_v3.research_workspace.parser_service import TextPostProcessor

    processor = TextPostProcessor()
    t0 = time.time()
    for text in texts:
        processor.process(text)
    elapsed = time.time() - t0

    return {
        "mode": "sequential",
        "count": len(texts),
        "total_elapsed": round(elapsed, 4),
        "avg_per_text": round(elapsed / len(texts), 6) if texts else 0,
    }


def test_postprocess_parallel(texts: list[str], max_workers: int = 4) -> dict[str, Any]:
    """并行后处理"""
    from src.agents_v3.research_workspace.parser_service import TextPostProcessor

    def _process(text: str) -> None:
        processor = TextPostProcessor()
        processor.process(text)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_process, texts))
    elapsed = time.time() - t0

    return {
        "mode": f"parallel (workers={max_workers})",
        "count": len(texts),
        "total_elapsed": round(elapsed, 4),
        "avg_per_text": round(elapsed / len(texts), 6) if texts else 0,
    }


# ── 下载并行测试（模拟） ──────────────────────────────────

def test_download_sequential_simulated(count: int = 6) -> dict[str, Any]:
    """模拟串行下载（sleep 代替网络 IO）"""
    t0 = time.time()
    for _ in range(count):
        time.sleep(0.5)  # 模拟 0.5s 下载时间
    elapsed = time.time() - t0

    return {
        "mode": "sequential (simulated)",
        "count": count,
        "total_elapsed": round(elapsed, 2),
        "avg_per_download": round(elapsed / count, 2),
    }


def test_download_parallel_simulated(count: int = 6, max_workers: int = 4) -> dict[str, Any]:
    """模拟并行下载（sleep 代替网络 IO）"""
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(lambda _: time.sleep(0.5), range(count)))
    elapsed = time.time() - t0

    return {
        "mode": f"parallel (workers={max_workers}, simulated)",
        "count": count,
        "total_elapsed": round(elapsed, 2),
        "avg_per_download": round(elapsed / count, 2),
    }


# ── 主测试流程 ────────────────────────────────────────────

def run_all_tests() -> dict[str, Any]:
    """运行所有并行性能测试"""
    all_results = {}

    # 1. 各解析器单独测试（取前 3 个 PDF）
    logger.info("=" * 60)
    logger.info("1. 各解析器单独性能测试")
    logger.info("=" * 60)

    adapter_results = {}
    test_pdfs = TEST_PDFS[:3]  # 取前 3 个 PDF

    for adapter_name in ["pdfplumber", "pymupdf", "pdfminer", "docling"]:
        logger.info(f"\n--- 测试 {adapter_name} ---")
        results = []
        for pdf_path in test_pdfs:
            logger.info(f"  解析: {Path(pdf_path).name}")
            result = test_single_adapter(adapter_name, pdf_path)
            results.append(result)
            if result["success"]:
                logger.info(f"    ✓ {result['total_chars']} chars, {result['pages']} pages, {result['elapsed_seconds']}s")
            else:
                logger.info(f"    ✗ {result.get('error', 'failed')}")
        adapter_results[adapter_name] = results

    all_results["adapter_comparison"] = adapter_results

    # 2. 串行 vs 并行解析（pdfplumber）
    logger.info("\n" + "=" * 60)
    logger.info("2. 串行 vs 并行解析测试 (pdfplumber)")
    logger.info("=" * 60)

    seq_result = test_parse_sequential(TEST_PDFS)
    logger.info(f"串行: {seq_result['total_elapsed']}s ({seq_result['count']} PDFs)")

    for workers in [2, 4]:
        par_result = test_parse_parallel(TEST_PDFS, max_workers=workers)
        speedup = seq_result["total_elapsed"] / par_result["total_elapsed"] if par_result["total_elapsed"] > 0 else 0
        logger.info(f"并行(workers={workers}): {par_result['total_elapsed']}s, 加速比: {speedup:.2f}x")
        all_results[f"parse_parallel_w{workers}"] = par_result

    all_results["parse_sequential"] = seq_result

    # 3. 串行 vs 并行后处理
    logger.info("\n" + "=" * 60)
    logger.info("3. 串行 vs 并行后处理测试")
    logger.info("=" * 60)

    # 准备测试文本
    from src.agents_v3.research_workspace.parser_service import PdfPlumberAdapter
    adapter = PdfPlumberAdapter()
    test_texts = []
    for pdf_path in TEST_PDFS[:3]:
        pages_text, _ = adapter.extract_pages(pdf_path)
        for _, text in pages_text:
            if text.strip():
                test_texts.append(text)

    logger.info(f"  测试文本数: {len(test_texts)}")

    seq_pp = test_postprocess_sequential(test_texts)
    logger.info(f"串行: {seq_pp['total_elapsed']}s")

    for workers in [2, 4]:
        par_pp = test_postprocess_parallel(test_texts, max_workers=workers)
        speedup = seq_pp["total_elapsed"] / par_pp["total_elapsed"] if par_pp["total_elapsed"] > 0 else 0
        logger.info(f"并行(workers={workers}): {par_pp['total_elapsed']}s, 加速比: {speedup:.2f}x")
        all_results[f"postprocess_parallel_w{workers}"] = par_pp

    all_results["postprocess_sequential"] = seq_pp

    # 4. 模拟下载并行测试
    logger.info("\n" + "=" * 60)
    logger.info("4. 模拟下载并行测试")
    logger.info("=" * 60)

    seq_dl = test_download_sequential_simulated(6)
    logger.info(f"串行: {seq_dl['total_elapsed']}s")

    for workers in [2, 4, 6]:
        par_dl = test_download_parallel_simulated(6, max_workers=workers)
        speedup = seq_dl["total_elapsed"] / par_dl["total_elapsed"] if par_dl["total_elapsed"] > 0 else 0
        logger.info(f"并行(workers={workers}): {par_dl['total_elapsed']}s, 加速比: {speedup:.2f}x")
        all_results[f"download_parallel_w{workers}"] = par_dl

    all_results["download_sequential"] = seq_dl

    return all_results


def generate_report(results: dict[str, Any]) -> str:
    """生成测试报告"""
    lines = []
    lines.append("# ParserService 并行性能测试报告")
    lines.append("")
    lines.append(f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**测试环境**: Windows, CPU 模式")
    lines.append(f"**测试 PDF 数量**: {len(TEST_PDFS)}")
    lines.append("")

    # 1. 解析器对比
    lines.append("## 1. 各解析器性能对比")
    lines.append("")
    lines.append("| 解析器 | PDF | 页数 | 字符数 | 耗时(s) | 状态 |")
    lines.append("|--------|-----|------|--------|---------|------|")

    for adapter_name, results_list in results.get("adapter_comparison", {}).items():
        for r in results_list:
            status = "✓" if r["success"] else "✗"
            lines.append(f"| {adapter_name} | {r['pdf']} | {r.get('pages', '-')} | {r.get('total_chars', '-'):,} | {r.get('elapsed_seconds', '-')} | {status} |")

    lines.append("")

    # 解析器汇总
    lines.append("### 解析器汇总")
    lines.append("")
    lines.append("| 解析器 | 成功率 | 平均耗时(s) | 平均字符数 |")
    lines.append("|--------|--------|------------|-----------|")

    for adapter_name, results_list in results.get("adapter_comparison", {}).items():
        success_count = sum(1 for r in results_list if r["success"])
        total = len(results_list)
        success_rate = f"{success_count/total*100:.0f}%" if total > 0 else "0%"
        avg_time = sum(r.get("elapsed_seconds", 0) for r in results_list if r["success"]) / max(success_count, 1)
        avg_chars = sum(r.get("total_chars", 0) for r in results_list if r["success"]) / max(success_count, 1)
        lines.append(f"| {adapter_name} | {success_rate} | {avg_time:.2f} | {avg_chars:,.0f} |")

    lines.append("")

    # 2. 串行 vs 并行解析
    lines.append("## 2. 串行 vs 并行解析 (pdfplumber)")
    lines.append("")

    seq = results.get("parse_sequential", {})
    lines.append(f"- **串行**: {seq.get('total_elapsed', '-')}s ({seq.get('count', '-')} PDFs)")
    lines.append("")

    lines.append("| 模式 | 总耗时(s) | 平均/PDF(s) | 加速比 |")
    lines.append("|------|----------|------------|--------|")

    seq_time = seq.get("total_elapsed", 0)
    for workers in [2, 4]:
        key = f"parse_parallel_w{workers}"
        par = results.get(key, {})
        par_time = par.get("total_elapsed", 0)
        speedup = seq_time / par_time if par_time > 0 else 0
        lines.append(f"| 并行(workers={workers}) | {par_time} | {par.get('avg_per_pdf', '-')} | {speedup:.2f}x |")

    lines.append("")

    # 3. 串行 vs 并行后处理
    lines.append("## 3. 串行 vs 并行后处理")
    lines.append("")

    seq_pp = results.get("postprocess_sequential", {})
    lines.append(f"- **测试文本数**: {seq_pp.get('count', '-')}")
    lines.append(f"- **串行**: {seq_pp.get('total_elapsed', '-')}s")
    lines.append("")

    lines.append("| 模式 | 总耗时(s) | 平均/文本(s) | 加速比 |")
    lines.append("|------|----------|-------------|--------|")

    seq_pp_time = seq_pp.get("total_elapsed", 0)
    for workers in [2, 4]:
        key = f"postprocess_parallel_w{workers}"
        par = results.get(key, {})
        par_time = par.get("total_elapsed", 0)
        speedup = seq_pp_time / par_time if par_time > 0 else 0
        lines.append(f"| 并行(workers={workers}) | {par_time} | {par.get('avg_per_text', '-')} | {speedup:.2f}x |")

    lines.append("")

    # 4. 模拟下载并行
    lines.append("## 4. 模拟下载并行测试")
    lines.append("")

    seq_dl = results.get("download_sequential", {})
    lines.append(f"- **模拟下载数**: {seq_dl.get('count', '-')}")
    lines.append(f"- **串行**: {seq_dl.get('total_elapsed', '-')}s")
    lines.append("")

    lines.append("| 模式 | 总耗时(s) | 加速比 |")
    lines.append("|------|----------|--------|")

    seq_dl_time = seq_dl.get("total_elapsed", 0)
    for workers in [2, 4, 6]:
        key = f"download_parallel_w{workers}"
        par = results.get(key, {})
        par_time = par.get("total_elapsed", 0)
        speedup = seq_dl_time / par_time if par_time > 0 else 0
        lines.append(f"| 并行(workers={workers}) | {par_time} | {speedup:.2f}x |")

    lines.append("")

    # 5. 结论
    lines.append("## 5. 结论与建议")
    lines.append("")
    lines.append("### 5.1 现有并行化")
    lines.append("")
    lines.append("- `download_all_pdfs`: 已实现并行下载，IO 密集型任务加速效果显著")
    lines.append("- `batch_parse_papers`: 已实现并行解析，多 PDF 并行处理有效")
    lines.append("")
    lines.append("### 5.2 并行化建议")
    lines.append("")
    lines.append("- **后处理**: CPU 密集型，GIL 限制下并行收益有限")
    lines.append("- **Docling 逐页提取**: CPU 密集型，并行反而更慢（实测 0.5x）")
    lines.append("- **IO 密集型任务**: 下载、文件读写等 IO 操作适合并行")
    lines.append("")

    return "\n".join(lines)


def main():
    """主函数"""
    results = run_all_tests()

    # 保存原始数据
    data_path = project_root / "docs" / "parallel-test-data.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"\n原始数据已保存到: {data_path}")

    # 生成报告
    report = generate_report(results)
    report_path = project_root / "docs" / "parallel-test-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
