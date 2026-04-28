"""
引用生成器 - Citation Generator

功能:
1. 引用生成
2. 参考文献格式化
3. 多格式支持
4. 引用一致性检查

设计原则:
- 多格式引用支持
- 自动引用提取
- 引用一致性验证
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


class CitationStyle(str, Enum):
    """引用格式"""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    GB_T = "gb_t"  # 中国国家标准


@dataclass
class Citation:
    """引用信息"""
    authors: List[str]
    year: str
    title: str
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None


@dataclass
class InTextCitation:
    """文中引用"""
    citation_key: str
    position: str  # e.g., "(Author, 2023)" or "[1]"
    start_index: int
    end_index: int


@dataclass
class CitationResult:
    """引用结果"""
    in_text_citations: List[InTextCitation]
    reference_list: List[str]
    formatted_references: Dict[CitationStyle, List[str]]


class CitationGenerator:
    """引用生成器"""

    def __init__(self, style: CitationStyle = CitationStyle.APA):
        self.style = style

    def format_citation(
        self,
        citation: Citation,
        style: Optional[CitationStyle] = None
    ) -> str:
        """格式化单条引用

        Args:
            citation: 引用信息
            style: 引用格式

        Returns:
            str: 格式化后的引用字符串
        """
        style = style or self.style

        if style == CitationStyle.APA:
            return self._format_apa(citation)
        elif style == CitationStyle.MLA:
            return self._format_mla(citation)
        elif style == CitationStyle.CHICAGO:
            return self._format_chicago(citation)
        elif style == CitationStyle.IEEE:
            return self._format_ieee(citation)
        elif style == CitationStyle.GB_T:
            return self._format_gb_t(citation)
        else:
            return self._format_apa(citation)

    def _format_apa(self, citation: Citation) -> str:
        """APA格式"""
        # Author, A. A., & Author, B. B. (Year). Title. Journal, Volume(Issue), Pages.
        authors = self._format_authors_apa(citation.authors)

        parts = [f"{authors} ({citation.year})."]

        # 标题
        if citation.title:
            parts.append(citation.title)

        # 期刊
        if citation.journal:
            journal_part = citation.journal
            if citation.volume:
                journal_part += f", {citation.volume}"
            if citation.issue:
                journal_part += f"({citation.issue})"
            if citation.pages:
                journal_part += f", {citation.pages}"
            parts.append(journal_part)

        # DOI
        if citation.doi:
            parts.append(f"https://doi.org/{citation.doi}")

        return "".join(f"{p}. " for p in parts).strip()

    def _format_mla(self, citation: Citation) -> str:
        """MLA格式"""
        authors = self._format_authors_mla(citation.authors)

        parts = [f"{authors}. \"{citation.title}.\""]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f", vol. {citation.volume}"
            if citation.issue:
                journal_part += f", no. {citation.issue}"
            if citation.year:
                journal_part += f", {citation.year}"
            if citation.pages:
                journal_part += f", pp. {citation.pages}"
            parts.append(journal_part)

        return " ".join(parts).strip()

    def _format_chicago(self, citation: Citation) -> str:
        """Chicago格式"""
        authors = self._format_authors_chicago(citation.authors)

        parts = [f"{authors}. \"{citation.title}.\""]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f" {citation.volume}"
            if citation.issue:
                journal_part += f", no. {citation.issue}"
            if citation.year:
                journal_part += f" ({citation.year})"
            if citation.pages:
                journal_part += f": {citation.pages}"
            parts.append(journal_part)

        if citation.doi:
            parts.append(f"https://doi.org/{citation.doi}")

        return " ".join(parts).strip()

    def _format_ieee(self, citation: Citation) -> str:
        """IEEE格式"""
        authors = self._format_authors_ieee(citation.authors)

        parts = [f"{authors}, \"{citation.title},\""]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f", vol. {citation.volume}"
            if citation.issue:
                journal_part += f", no. {citation.issue}"
            if citation.pages:
                journal_part += f", pp. {citation.pages}"
            if citation.year:
                journal_part += f", {citation.year}"
            parts.append(journal_part)

        return " ".join(parts).strip()

    def _format_gb_t(self, citation: Citation) -> str:
        """中国国家标准格式"""
        authors = ", ".join(citation.authors)

        parts = [f"{authors}. {citation.title}"]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f", {citation.volume}"
            if citation.issue:
                journal_part += f"({citation.issue})"
            if citation.pages:
                journal_part += f": {citation.pages}"
            if citation.year:
                journal_part += f", {citation.year}"
            parts.append(journal_part)

        if citation.doi:
            parts.append(f"DOI: {citation.doi}")

        return "".join(f"{p}." for p in parts).strip()

    def _format_authors_apa(self, authors: List[str]) -> str:
        """APA格式作者"""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]}, & {authors[1]}"
        if len(authors) > 2:
            return f"{', '.join(authors[:-1])}, & {authors[-1]}"
        return ", ".join(authors)

    def _format_authors_mla(self, authors: List[str]) -> str:
        """MLA格式作者"""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]}, and {authors[1]}"
        if len(authors) > 2:
            return f"{authors[0]}, et al."
        return ", ".join(authors)

    def _format_authors_chicago(self, authors: List[str]) -> str:
        """Chicago格式作者"""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]} and {authors[1]}"
        if len(authors) > 2:
            return f"{authors[0]} et al."
        return ", ".join(authors)

    def _format_authors_ieee(self, authors: List[str]) -> str:
        """IEEE格式作者"""
        if not authors:
            return ""
        # IEEE使用首字母缩写
        formatted = []
        for author in authors:
            parts = author.split()
            if len(parts) > 1:
                initials = " ".join(p[0] + "." for p in parts[1:])
                formatted.append(f"{parts[0]}, {initials}")
            else:
                formatted.append(author)
        return ", ".join(formatted)

    def extract_citations_from_text(
        self,
        text: str
    ) -> List[Tuple[str, int, int]]:
        """从文本中提取引用标记

        Args:
            text: 文本

        Returns:
            List[Tuple[str, int, int]]: [(citation_key, start, end)]
        """
        citations = []

        # 提取 [1], [1,2], [1-3] 格式
        pattern = r'\[(\d+(?:[,-]\d+)*)\]'
        for match in re.finditer(pattern, text):
            citations.append((match.group(0), match.start(), match.end()))

        # 提取 (Author, Year) 格式
        pattern = r'\(([A-Za-z]+(?:\s+et\s+al\.?)?,?\s*\d{4})\)'
        for match in re.finditer(pattern, text):
            citations.append((match.group(0), match.start(), match.end()))

        return citations

    def generate_reference_list(
        self,
        citations: List[Citation],
        style: Optional[CitationStyle] = None
    ) -> List[str]:
        """生成参考文献列表

        Args:
            citations: 引用列表
            style: 引用格式

        Returns:
            List[str]: 格式化后的参考文献列表
        """
        style = style or self.style
        references = []

        for citation in citations:
            ref = self.format_citation(citation, style)
            references.append(ref)

        return references


class CitationStyleAdapter:
    """引用格式适配器"""

    def __init__(self):
        self._adapters: Dict[CitationStyle, CitationGenerator] = {}

    def get_adapter(self, style: CitationStyle) -> CitationGenerator:
        """获取指定格式的适配器"""
        if style not in self._adapters:
            self._adapters[style] = CitationGenerator(style=style)
        return self._adapters[style]

    def convert_style(
        self,
        citation: Citation,
        from_style: CitationStyle,
        to_style: CitationStyle
    ) -> str:
        """转换引用格式"""
        from_adapter = self.get_adapter(from_style)
        to_adapter = self.get_adapter(to_style)

        # 先格式化为中间格式
        intermediate = from_adapter.format_citation(citation, from_style)
        # 然后解析并重新格式化
        # 简化处理：直接使用citation数据重新格式化
        return to_adapter.format_citation(citation, to_style)


# 便捷函数
def format_citation(
    citation: Citation,
    style: CitationStyle = CitationStyle.APA
) -> str:
    """便捷引用格式化函数"""
    generator = CitationGenerator(style=style)
    return generator.format_citation(citation, style)


def generate_references(
    citations: List[Citation],
    style: CitationStyle = CitationStyle.APA
) -> List[str]:
    """便捷参考文献生成函数"""
    generator = CitationGenerator(style=style)
    return generator.generate_reference_list(citations, style)
