"""
论文写作工具 - Paper Writing Tools

提供:
- 论文完整性检查
- 多格式引用格式化
- 参考文献管理
- 论文评分
"""
import re
from typing import Any, Dict, List, Optional
from .tool_spec import ToolSpec, ParameterSpec, ParameterType
from .registry import ToolRegistry


# ============== 论文完整性检查 ==============

async def check_paper_completeness_handler(content: str) -> Dict[str, Any]:
    """
    检查论文完整性

    Args:
        content: 论文内容

    Returns:
        {is_complete, score, missing_sections, suggestions}
    """
    issues = []
    suggestions = []
    missing_sections = []

    # 检查基本结构
    sections = {
        "title": r'^#\s+.+',
        "abstract": r'(?i)abstract',
        "introduction": r'(?i)introduction',
        "method": r'(?i)method|methodology',
        "results": r'(?i)results?',
        "discussion": r'(?i)discussion',
        "conclusion": r'(?i)conclusion',
        "references": r'(?i)references?|bibliography'
    }

    found_sections = {}
    for section, pattern in sections.items():
        if re.search(pattern, content, re.MULTILINE):
            found_sections[section] = True
        else:
            missing_sections.append(section)
            found_sections[section] = False

    # 计算分数
    score = len([s for s in found_sections.values() if s]) / len(sections) * 100

    # 生成建议
    if not found_sections.get("title"):
        suggestions.append("添加论文标题")
    if not found_sections.get("abstract"):
        suggestions.append("添加摘要部分(Abstract)")
    if not found_sections.get("introduction"):
        suggestions.append("添加引言部分(Introduction)")
    if not found_sections.get("method"):
        suggestions.append("添加方法部分(Methodology)")
    if not found_sections.get("results"):
        suggestions.append("添加结果部分(Results)")
    if not found_sections.get("conclusion"):
        suggestions.append("添加结论部分(Conclusion)")
    if not found_sections.get("references"):
        suggestions.append("添加参考文献(References)")

    # 检查内容长度
    if len(content) < 1000:
        issues.append("论文内容过短,可能不够完整")
    elif len(content) < 5000:
        suggestions.append("考虑增加论文内容深度")

    # 检查是否有图表
    if "figure" not in content.lower() and "table" not in content.lower():
        suggestions.append("考虑添加图表以增强表达")

    return {
        "is_complete": len(missing_sections) == 0 and len(content) > 1000,
        "score": round(score, 1),
        "missing_sections": missing_sections,
        "found_sections": found_sections,
        "issues": issues,
        "suggestions": suggestions,
        "content_length": len(content)
    }


# ============== 多格式引用格式化 ==============

async def format_reference_handler(
    paper: Dict[str, Any],
    style: str = "auto"
) -> Dict[str, Any]:
    """
    多格式引用格式化

    Args:
        paper: 论文信息 {title, authors, year, journal, volume, pages, doi}
        style: 引用格式 (apa/ieee/mla/chicago/bibtex/auto)

    Returns:
        {citations: {style: formatted_string}}
    """
    title = paper.get("title", "")
    authors = paper.get("authors", [])
    year = paper.get("year", 2024)
    journal = paper.get("journal", "")
    volume = paper.get("volume", "")
    pages = paper.get("pages", "")
    doi = paper.get("doi", "")
    publisher = paper.get("publisher", "")

    # 格式化作者列表
    def format_authors(authors, style):
        if not authors:
            return ""
        if isinstance(authors, str):
            authors = [authors]

        if style == "apa":
            # APA: Last, F. M., & Last, F. M.
            formatted = []
            for author in authors:
                parts = author.split()
                if len(parts) >= 2:
                    last = parts[-1]
                    initials = " ".join(parts[:-1])
                    formatted.append(f"{last}, {'.'.join([n[0]+'.' for n in initials.split()])}")
                else:
                    formatted.append(author)
            return ", & ".join(formatted)
        elif style == "ieee":
            # IEEE: F. M. Last, and F. M. Last,
            formatted = []
            for author in authors:
                parts = author.split()
                if len(parts) >= 2:
                    last = parts[-1]
                    initials = " ".join(parts[:-1])
                    formatted.append(f"{'.'.join([n[0]+'.' for n in initials.split()])} {last}")
                else:
                    formatted.append(author)
            return ", ".join(formatted[:-1]) + ", and " + formatted[-1] if len(formatted) > 1 else formatted[0]
        else:
            return ", ".join(authors)

    # 各种格式
    citations = {}

    # APA
    authors_apa = format_authors(authors, "apa")
    if journal:
        citations["apa"] = f"{authors_apa} ({year}). {title}. {journal}"
        if volume:
            citations["apa"] += f", {volume}"
        if pages:
            citations["apa"] += f", {pages}"
        citations["apa"] += "."
    else:
        citations["apa"] = f"{authors_apa} ({year}). {title}."

    # IEEE
    authors_ieee = format_authors(authors, "ieee")
    if journal:
        citations["ieee"] = f"{authors_ieee}, \"{title},\" {journal}, vol. {volume}, pp. {pages}, {year}."
    else:
        citations["ieee"] = f"{authors_ieee}, \"{title},\" {year}."

    # MLA
    citations["mla"] = f"{', '.join(authors)}. \"{title}.\" {journal}, {year}."

    # Chicago
    citations["chicago"] = f"{', '.join(authors)}. \"{title}.\" {journal} {year}."

    # BibTeX
    # 生成bibtex key
    first_author_last = authors[0].split()[-1] if authors else "unknown"
    bibtex_key = f"{first_author_last}{year}"
    citations["bibtex"] = f"""@article{{{bibtex_key},
  title={{{title}}},
  author={{{', '.join(authors)}}},
  journal={{{journal}}},
  year={{{year}}},
  volume={{{volume}}},
  pages={{{pages}}},
  doi={{{doi}}}
}}"""

    # 自动选择(根据内容)
    if style == "auto":
        style = "apa"

    return {
        "citations": citations,
        "selected_style": style,
        "selected_citation": citations.get(style, citations["apa"])
    }


# ============== 论文评分 ==============

async def score_paper_handler(content: str, criteria: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    论文评分

    Args:
        content: 论文内容
        criteria: 评分标准及权重 {criterion: weight}

    Returns:
        {overall_score, dimension_scores, feedback}
    """
    criteria = criteria or {
        "structure": 0.2,
        "content_quality": 0.25,
        "clarity": 0.2,
        "references": 0.15,
        "formatting": 0.2
    }

    dimension_scores = {}

    # 结构评分
    structure_keywords = ["abstract", "introduction", "method", "results", "discussion", "conclusion", "references"]
    found_struct = sum(1 for kw in structure_keywords if kw.lower() in content.lower())
    dimension_scores["structure"] = found_struct / len(structure_keywords) * 100

    # 内容质量评分
    if len(content) > 5000:
        content_quality = 80
    elif len(content) > 2000:
        content_quality = 60
    else:
        content_quality = 40
    dimension_scores["content_quality"] = content_quality

    # 清晰度评分
    if "however" in content.lower() or "therefore" in content.lower():
        clarity = 75
    else:
        clarity = 60
    dimension_scores["clarity"] = clarity

    # 参考文献评分
    ref_count = len(re.findall(r'\[\d+\]', content))
    if ref_count > 10:
        dimension_scores["references"] = 80
    elif ref_count > 5:
        dimension_scores["references"] = 60
    else:
        dimension_scores["references"] = 40

    # 格式评分
    if re.search(r'^#\s+', content, re.MULTILINE):
        formatting = 80
    else:
        formatting = 50
    dimension_scores["formatting"] = formatting

    # 计算综合分
    overall_score = sum(
        dimension_scores[d] * criteria.get(d, 1/len(criteria))
        for d in dimension_scores
    )

    # 反馈
    feedback = []
    if dimension_scores["structure"] < 60:
        feedback.append("建议完善论文结构")
    if dimension_scores["content_quality"] < 60:
        feedback.append("建议增加内容深度")
    if dimension_scores["references"] < 60:
        feedback.append("建议增加参考文献数量")
    if dimension_scores["formatting"] < 60:
        feedback.append("建议使用标准论文格式")

    return {
        "overall_score": round(overall_score, 1),
        "dimension_scores": {k: round(v, 1) for k, v in dimension_scores.items()},
        "feedback": feedback
    }


# ============== 工具注册 ==============

def register_paper_tools(registry: ToolRegistry) -> None:
    """注册论文写作工具"""

    registry.register(ToolSpec(
        name="check_paper_completeness",
        description="检查论文完整性,给出缺失部分和建议",
        parameters=[
            ParameterSpec("content", ParameterType.STRING, "论文内容", required=True)
        ],
        handler=check_paper_completeness_handler,
        category="paper"
    ))

    registry.register(ToolSpec(
        name="format_reference",
        description="多格式引用格式化(APA/IEEE/MLA/Chicago/BibTeX)",
        parameters=[
            ParameterSpec("paper", ParameterType.OBJECT, "论文信息", required=True),
            ParameterSpec("style", ParameterType.STRING, "引用格式", required=False, default="auto")
        ],
        handler=format_reference_handler,
        category="paper"
    ))

    registry.register(ToolSpec(
        name="score_paper",
        description="对论文进行多维度评分",
        parameters=[
            ParameterSpec("content", ParameterType.STRING, "论文内容", required=True),
            ParameterSpec("criteria", ParameterType.OBJECT, "评分标准权重", required=False)
        ],
        handler=score_paper_handler,
        category="paper"
    ))
