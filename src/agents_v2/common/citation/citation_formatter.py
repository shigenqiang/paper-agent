"""
引用格式化器 - Citation Formatter

将引用格式化为不同风格（APA/GB7714/Chicago/IEEE等）。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .citation_parser import CitationStyle, ParsedCitation
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


@dataclass
class FormattedCitation:
    """格式化后的引用"""
    ref_num: str
    text: str  # 格式化后的引用文本
    style: CitationStyle
    authors: Optional[str] = None
    year: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None


class CitationFormatter:
    """
    引用格式化器

    支持多种引用格式：
    - APA: 作者, 标题. 期刊, 年份.
    - GB7714: [1] 作者. 标题. 期刊, 年份.
    - Chicago: 作者. "标题." 期刊, 年份.
    - IEEE: [1] 作者, "标题," 期刊, 年份.
    - MLA: 作者. "标题." 期刊, 年份.
    """

    def __init__(self, style: CitationStyle = CitationStyle.APA):
        self.style = style

    def format(
        self,
        citation: ParsedCitation,
        ref_num: Optional[str] = None
    ) -> FormattedCitation:
        """
        格式化单个引用

        Args:
            citation: 解析后的引用
            ref_num: 引用编号

        Returns:
            FormattedCitation: 格式化后的引用
        """
        ref_num = ref_num or citation.ref_num

        if self.style == CitationStyle.APA:
            text = self._format_apa(citation)
        elif self.style == CitationStyle.GB7714:
            text = self._format_gb7714(citation)
        elif self.style == CitationStyle.CHICAGO:
            text = self._format_chicago(citation)
        elif self.style == CitationStyle.IEEE:
            text = self._format_ieee(citation)
        elif self.style == CitationStyle.MLA:
            text = self._format_mla(citation)
        else:
            text = self._format_plain(citation)

        return FormattedCitation(
            ref_num=ref_num,
            text=text,
            style=self.style,
            authors=citation.authors[0] if citation.authors else None,
            year=citation.year,
            title=citation.title,
            journal=citation.journal,
            volume=citation.volume,
            pages=citation.pages,
        )

    def format_batch(
        self,
        citations: List[ParsedCitation],
        start_num: int = 1
    ) -> List[FormattedCitation]:
        """批量格式化引用"""
        formatted = []
        for i, citation in enumerate(citations, start_num):
            formatted.append(self.format(citation, ref_num=str(i)))
        return formatted

    def _format_apa(self, citation: ParsedCitation) -> str:
        """APA格式: 作者. (年份). 标题. 期刊, 卷(期), 页码."""
        parts = []

        if citation.authors:
            authors = ', '.join(citation.authors) if isinstance(citation.authors, list) else citation.authors
            parts.append(f"{authors}.")
        else:
            parts.append("Unknown.")

        if citation.year:
            parts.append(f"({citation.year}).")
        else:
            parts.append("(n.d.).")

        if citation.title:
            parts.append(f"{citation.title}.")

        if citation.journal:
            journal_part = citation.journal
            if citation.volume:
                journal_part += f", {citation.volume}"
                if citation.pages:
                    journal_part += f", {citation.pages}"
            parts.append(journal_part + ".")

        return ' '.join(parts)

    def _format_gb7714(self, citation: ParsedCitation) -> str:
        """GB7714格式: [编号] 作者. 标题. 期刊, 年份, 卷(期): 页码."""
        parts = []

        if citation.authors:
            authors = ', '.join(citation.authors) if isinstance(citation.authors, list) else citation.authors
            parts.append(f"{authors}.")
        else:
            parts.append("Unknown.")

        if citation.title:
            parts.append(f"{citation.title}.")

        if citation.journal:
            journal_part = citation.journal
            if citation.year:
                journal_part += f", {citation.year}"
            if citation.volume:
                journal_part += f", {citation.volume}"
            if citation.pages:
                journal_part += f": {citation.pages}"
            parts.append(journal_part + ".")

        return ''.join(parts)

    def _format_chicago(self, citation: ParsedCitation) -> str:
        """Chicago格式: 作者. "标题." 期刊, 年份."""
        parts = []

        if citation.authors:
            authors = ', '.join(citation.authors) if isinstance(citation.authors, list) else citation.authors
            parts.append(f"{authors}.")
        else:
            parts.append("Unknown.")

        if citation.title:
            parts.append(f'"{citation.title}."')
        else:
            parts.append('"Unknown."')

        if citation.journal:
            journal_part = citation.journal
            if citation.year:
                journal_part += f", {citation.year}"
            parts.append(journal_part + ".")

        return ' '.join(parts)

    def _format_ieee(self, citation: ParsedCitation) -> str:
        """IEEE格式: 作者, "标题," 期刊, vol. 卷, no. 期, pp. 页码, 年份."""
        parts = []

        if citation.authors:
            authors = ', '.join(citation.authors) if isinstance(citation.authors, list) else citation.authors
            parts.append(f"{authors},")
        else:
            parts.append("Unknown,")

        if citation.title:
            parts.append(f'"{citation.title},"')
        else:
            parts.append('"Unknown,"')

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f", vol. {citation.volume}"
            if citation.pages:
                journal_part += f", pp. {citation.pages}"
            if citation.year:
                journal_part += f", {citation.year}"
            parts.append(journal_part + ".")

        return ' '.join(parts)

    def _format_mla(self, citation: ParsedCitation) -> str:
        """MLA格式: 作者. "标题." 期刊, 卷. 期 (年份): 页码."""
        parts = []

        if citation.authors:
            authors = ', '.join(citation.authors) if isinstance(citation.authors, list) else citation.authors
            parts.append(f"{authors}.")
        else:
            parts.append("Unknown.")

        if citation.title:
            parts.append(f'"{citation.title}."')
        else:
            parts.append('"Unknown."')

        if citation.journal:
            parts.append(f"{citation.journal},")

        if citation.volume:
            parts.append(f"vol. {citation.volume},")

        if citation.year:
            parts.append(f"{citation.year},")

        if citation.pages:
            parts.append(f"pp. {citation.pages}.")

        return ' '.join(parts)

    def _format_plain(self, citation: ParsedCitation) -> str:
        """纯文本格式"""
        parts = []

        if citation.authors:
            authors = ', '.join(citation.authors) if isinstance(citation.authors, list) else citation.authors
            parts.append(authors)

        if citation.year:
            parts.append(f"({citation.year})")

        if citation.title:
            parts.append(f"- {citation.title}")

        if citation.journal:
            parts.append(f"- {citation.journal}")

        return ': '.join(parts) if parts else "Unknown citation"


def format_citation(
    citation: ParsedCitation,
    style: CitationStyle = CitationStyle.APA,
    ref_num: Optional[str] = None
) -> str:
    """
    便捷函数：格式化单个引用

    Args:
        citation: 解析后的引用
        style: 引用格式风格
        ref_num: 引用编号

    Returns:
        str: 格式化后的引用文本
    """
    formatter = CitationFormatter(style=style)
    return formatter.format(citation, ref_num).text
