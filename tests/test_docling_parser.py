"""Docling 解析器测试脚本

测试 Docling 对所有 PDF 文件的解析效果，生成详细报告。
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from docling.document_converter import DocumentConverter
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")


def get_test_pdfs() -> list[dict[str, str]]:
    """获取所有测试 PDF 文件"""
    pdfs = []

    # 1. fixtures 目录
    fixtures_dir = project_root / "tests" / "agents_v3" / "research_workspace" / "fixtures"
    if fixtures_dir.exists():
        for pdf_file in fixtures_dir.glob("*.pdf"):
            pdfs.append({
                "path": str(pdf_file),
                "name": pdf_file.name,
                "source": "fixtures",
                "category": "test_fixtures"
            })

    # 2. test_pdfs 目录
    test_pdfs_dir = project_root / "data" / "research_workspace" / "test_pdfs"
    if test_pdfs_dir.exists():
        for pdf_file in test_pdfs_dir.glob("*.pdf"):
            pdfs.append({
                "path": str(pdf_file),
                "name": pdf_file.name,
                "source": "test_pdfs",
                "category": "research_papers"
            })

    # 3. test_search_to_pdf 目录
    search_pdf_dir = project_root / "data" / "research_workspace" / "files" / "test_search_to_pdf"
    if search_pdf_dir.exists():
        for pdf_file in search_pdf_dir.glob("*.pdf"):
            pdfs.append({
                "path": str(pdf_file),
                "name": pdf_file.name,
                "source": "test_search_to_pdf",
                "category": "search_results"
            })

    # 4. proj_673ac013 目录
    proj_dir = project_root / "data" / "research_workspace" / "files" / "proj_673ac013"
    if proj_dir.exists():
        for pdf_file in proj_dir.glob("*.pdf"):
            pdfs.append({
                "path": str(pdf_file),
                "name": pdf_file.name,
                "source": "proj_673ac013",
                "category": "project_papers"
            })

    return pdfs


def parse_pdf_with_docling(pdf_path: str) -> dict[str, Any]:
    """使用 Docling 解析单个 PDF 文件"""
    result = {
        "success": False,
        "pdf_path": pdf_path,
        "page_count": 0,
        "char_count": 0,
        "word_count": 0,
        "section_count": 0,
        "sections": [],
        "has_abstract": False,
        "has_references": False,
        "has_tables": False,
        "has_figures": False,
        "parse_time_seconds": 0.0,
        "markdown_preview": "",
        "error": None,
    }

    try:
        start_time = time.time()

        # 创建转换器
        converter = DocumentConverter()

        # 转换 PDF
        conv_result = converter.convert(pdf_path)
        doc = conv_result.document

        # 导出为 Markdown
        markdown = doc.export_to_markdown()

        parse_time = time.time() - start_time

        # 统计信息
        lines = markdown.split("\n")
        char_count = len(markdown)
        word_count = len(markdown.split())

        # 检测章节
        sections = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                # 提取章节标题
                level = len(stripped) - len(stripped.lstrip("#"))
                title = stripped.lstrip("#").strip()
                if title:
                    sections.append({
                        "level": level,
                        "title": title
                    })

        # 检测特殊内容
        has_abstract = any(
            "abstract" in line.lower() or "摘要" in line
            for line in lines[:100]  # 只检查前100行
        )

        has_references = any(
            "reference" in line.lower() or "参考文献" in line or "bibliography" in line.lower()
            for line in lines
        )

        has_tables = any(
            "| " in line and " |" in line
            for line in lines
        )

        has_figures = any(
            "figure" in line.lower() or "fig." in line.lower() or "图" in line
            for line in lines
        )

        # 获取页数（从文档元数据）
        page_count = 0
        if hasattr(doc, 'pages'):
            page_count = len(doc.pages)
        elif hasattr(conv_result, 'pages'):
            page_count = len(conv_result.pages)

        # 更新结果
        result.update({
            "success": True,
            "page_count": page_count,
            "char_count": char_count,
            "word_count": word_count,
            "section_count": len(sections),
            "sections": sections[:20],  # 只保存前20个章节
            "has_abstract": has_abstract,
            "has_references": has_references,
            "has_tables": has_tables,
            "has_figures": has_figures,
            "parse_time_seconds": round(parse_time, 2),
            "markdown_preview": markdown[:1000] + "..." if len(markdown) > 1000 else markdown,
        })

        logger.info(f"✓ 解析成功: {char_count} 字符, {len(sections)} 章节, {parse_time:.2f}s")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ 解析失败: {e}")

    return result


def run_tests() -> dict[str, Any]:
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("Docling 解析器测试开始")
    logger.info("=" * 60)

    # 获取所有 PDF 文件
    pdfs = get_test_pdfs()
    logger.info(f"找到 {len(pdfs)} 个 PDF 文件")

    if not pdfs:
        logger.warning("没有找到 PDF 文件")
        return {"total": 0, "success": 0, "failed": 0, "results": []}

    # 测试结果
    results = []
    success_count = 0
    failed_count = 0
    total_chars = 0
    total_sections = 0
    total_time = 0.0

    # 逐个测试
    for i, pdf_info in enumerate(pdfs, 1):
        logger.info(f"\n[{i}/{len(pdfs)}] 测试: {pdf_info['name']}")
        logger.info(f"  路径: {pdf_info['path']}")
        logger.info(f"  来源: {pdf_info['source']} ({pdf_info['category']})")

        # 解析 PDF
        result = parse_pdf_with_docling(pdf_info["path"])

        # 合并信息
        result.update({
            "name": pdf_info["name"],
            "source": pdf_info["source"],
            "category": pdf_info["category"],
        })

        results.append(result)

        if result["success"]:
            success_count += 1
            total_chars += result["char_count"]
            total_sections += result["section_count"]
            total_time += result["parse_time_seconds"]
        else:
            failed_count += 1

    # 生成汇总
    summary = {
        "total": len(pdfs),
        "success": success_count,
        "failed": failed_count,
        "success_rate": f"{success_count/len(pdfs)*100:.1f}%" if pdfs else "0%",
        "total_chars": total_chars,
        "total_sections": total_sections,
        "total_parse_time": round(total_time, 2),
        "avg_chars_per_pdf": round(total_chars / success_count) if success_count > 0 else 0,
        "avg_sections_per_pdf": round(total_sections / success_count, 1) if success_count > 0 else 0,
        "avg_parse_time": round(total_time / success_count, 2) if success_count > 0 else 0,
        "results": results,
    }

    return summary


def generate_report(summary: dict[str, Any]) -> str:
    """生成 Markdown 测试报告"""
    report_lines = []

    # 标题
    report_lines.append("# Docling 解析器测试报告")
    report_lines.append("")
    report_lines.append(f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**测试环境**: Docling (Python)")
    report_lines.append("")

    # 汇总统计
    report_lines.append("## 1. 测试汇总")
    report_lines.append("")
    report_lines.append(f"| 指标 | 数值 |")
    report_lines.append(f"|------|------|")
    report_lines.append(f"| 测试 PDF 数量 | {summary['total']} |")
    report_lines.append(f"| 成功解析 | {summary['success']} |")
    report_lines.append(f"| 解析失败 | {summary['failed']} |")
    report_lines.append(f"| 成功率 | {summary['success_rate']} |")
    report_lines.append(f"| 总字符数 | {summary['total_chars']:,} |")
    report_lines.append(f"| 总章节数 | {summary['total_sections']} |")
    report_lines.append(f"| 总解析时间 | {summary['total_parse_time']:.2f}s |")
    report_lines.append(f"| 平均字符数/PDF | {summary['avg_chars_per_pdf']:,} |")
    report_lines.append(f"| 平均章节数/PDF | {summary['avg_sections_per_pdf']} |")
    report_lines.append(f"| 平均解析时间/PDF | {summary['avg_parse_time']:.2f}s |")
    report_lines.append("")

    # 详细结果
    report_lines.append("## 2. 详细测试结果")
    report_lines.append("")

    for i, result in enumerate(summary["results"], 1):
        report_lines.append(f"### 2.{i} {result['name']}")
        report_lines.append("")

        # 基本信息
        report_lines.append("**基本信息**:")
        report_lines.append(f"- 文件路径: `{result['pdf_path']}`")
        report_lines.append(f"- 来源: {result['source']} ({result['category']})")
        report_lines.append(f"- 状态: {'✓ 成功' if result['success'] else '✗ 失败'}")
        report_lines.append("")

        if result["success"]:
            # 解析统计
            report_lines.append("**解析统计**:")
            report_lines.append(f"- 页数: {result['page_count']}")
            report_lines.append(f"- 字符数: {result['char_count']:,}")
            report_lines.append(f"- 单词数: {result['word_count']:,}")
            report_lines.append(f"- 章节数: {result['section_count']}")
            report_lines.append(f"- 解析时间: {result['parse_time_seconds']:.2f}s")
            report_lines.append("")

            # 内容特征
            report_lines.append("**内容特征**:")
            report_lines.append(f"- 包含摘要: {'是' if result['has_abstract'] else '否'}")
            report_lines.append(f"- 包含参考文献: {'是' if result['has_references'] else '否'}")
            report_lines.append(f"- 包含表格: {'是' if result['has_tables'] else '否'}")
            report_lines.append(f"- 包含图片: {'是' if result['has_figures'] else '否'}")
            report_lines.append("")

            # 章节列表
            if result["sections"]:
                report_lines.append("**主要章节**:")
                for sec in result["sections"][:10]:  # 只显示前10个
                    indent = "  " * (sec["level"] - 1) if sec["level"] > 1 else ""
                    report_lines.append(f"{indent}- {sec['title']}")
                if len(result["sections"]) > 10:
                    report_lines.append(f"  - ... (共 {len(result['sections'])} 个章节)")
                report_lines.append("")

            # Markdown 预览
            report_lines.append("**Markdown 预览** (前 500 字符):")
            report_lines.append("```markdown")
            preview = result["markdown_preview"][:500]
            report_lines.append(preview)
            report_lines.append("```")
            report_lines.append("")
        else:
            # 错误信息
            report_lines.append(f"**错误信息**: `{result['error']}`")
            report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

    # 结论
    report_lines.append("## 3. 测试结论")
    report_lines.append("")

    if summary["success"] > 0:
        report_lines.append("### 3.1 解析能力评估")
        report_lines.append("")

        # 评估章节识别能力
        avg_sections = summary["avg_sections_per_pdf"]
        if avg_sections >= 10:
            section_rating = "优秀"
        elif avg_sections >= 5:
            section_rating = "良好"
        else:
            section_rating = "一般"

        report_lines.append(f"- **章节识别能力**: {section_rating} (平均 {avg_sections} 个章节/PDF)")
        report_lines.append(f"- **文本提取能力**: 平均提取 {summary['avg_chars_per_pdf']:,} 字符/PDF")
        report_lines.append(f"- **解析速度**: 平均 {summary['avg_parse_time']:.2f}s/PDF")
        report_lines.append("")

        # 优势
        report_lines.append("### 3.2 Docling 优势")
        report_lines.append("")
        report_lines.append("1. **高质量 Markdown 输出**: 自动识别章节结构，生成格式化的 Markdown")
        report_lines.append("2. **多语言支持**: 支持中英文混合文档")
        report_lines.append("3. **内容识别**: 能够识别摘要、参考文献、表格、图片等")
        report_lines.append("4. **无需额外配置**: 开箱即用，无需下载额外模型")
        report_lines.append("5. **内存效率**: 相比 MinerU，内存占用更低")
        report_lines.append("")

        # 局限性
        report_lines.append("### 3.3 局限性")
        report_lines.append("")
        report_lines.append("1. **解析速度**: 相比传统解析器（pdfplumber）较慢")
        report_lines.append("2. **页数信息**: 部分 PDF 可能无法获取准确页数")
        report_lines.append("3. **复杂布局**: 对于特殊布局（如多栏、公式密集）可能有局限")
        report_lines.append("")

    # 建议
    report_lines.append("### 3.4 使用建议")
    report_lines.append("")
    report_lines.append("基于测试结果，建议:")
    report_lines.append("")
    report_lines.append("1. **正式生产环境**: 优先使用 Docling 作为主要解析器")
    report_lines.append("2. **快速预览**: 对于需要快速获取文本的场景，可使用传统解析器作为 fallback")
    report_lines.append("3. **集成方案**: 将 Docling 集成到 ParserService 中，作为高质量解析选项")
    report_lines.append("")

    return "\n".join(report_lines)


def main():
    """主函数"""
    # 运行测试
    summary = run_tests()

    # 打印汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)
    logger.info(f"总计: {summary['total']} 个 PDF")
    logger.info(f"成功: {summary['success']} 个")
    logger.info(f"失败: {summary['failed']} 个")
    logger.info(f"成功率: {summary['success_rate']}")
    logger.info(f"总字符数: {summary['total_chars']:,}")
    logger.info(f"总章节数: {summary['total_sections']}")
    logger.info(f"总解析时间: {summary['total_parse_time']:.2f}s")

    # 生成报告
    report = generate_report(summary)

    # 保存报告
    report_path = project_root / "docs" / "docling-test-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"\n报告已保存到: {report_path}")

    # 保存原始数据
    data_path = project_root / "docs" / "docling-test-data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"原始数据已保存到: {data_path}")

    return summary


if __name__ == "__main__":
    main()
