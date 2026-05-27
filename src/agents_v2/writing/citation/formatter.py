"""
引用格式化器 - Citation Formatter

支持多种引用格式：
- APA 7th
- MLA 9th
- Chicago
- IEEE
- GB/T 7714 (中国国家标准)
- Nature
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class CitationStyle(Enum):
    """引用样式枚举"""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    GB7714 = "gb7714"
    NATURE = "nature"


SUPPORTED_STYLES = ["apa", "mla", "chicago", "ieee", "gb7714", "nature"]


@dataclass
class FormattedCitation:
    """格式化后的引用"""
    citation_id: str
    raw_text: str = ""
    formatted: str = ""
    paper_id: str = ""
    paper_title: str = ""
    authors: List[str] = field(default_factory=list)
    year: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "raw_text": self.raw_text,
            "formatted": self.formatted,
            "paper_id": self.paper_id,
            "paper_title": self.paper_title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "volume": self.volume,
            "pages": self.pages,
            "doi": self.doi,
            "url": self.url,
            "source": self.source,
        }


@dataclass
class AuthorName:
    """作者姓名结构化"""
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    suffix: str = ""
    initials: str = ""

    @classmethod
    def parse(cls, name: str) -> "AuthorName":
        """解析作者姓名"""
        if not name:
            return cls()

        name = name.strip()

        # 处理 "Last, First" 格式
        if "," in name:
            parts = name.split(",", 1)
            last = parts[0].strip()
            first_parts = parts[1].strip().split()
            first = first_parts[0] if first_parts else ""
            middle = " ".join(first_parts[1:]) if len(first_parts) > 1 else ""
        else:
            parts = name.split()
            if len(parts) == 1:
                last = parts[0]
                first = ""
            else:
                last = parts[-1]
                first = parts[0]
                middle = " ".join(parts[1:-1])

        # 生成首字母
        initials = ""
        if first:
            initials += first[0].upper()
        if middle:
            for m in middle.split():
                initials += m[0].upper()

        return cls(
            last_name=last,
            first_name=first,
            middle_name=middle,
            initials=initials
        )

    def format(self, style: CitationStyle) -> str:
        """格式化作者名"""
        if style == CitationStyle.APA or style == CitationStyle.GB7714:
            if self.initials:
                return f"{self.last_name}, {self.initials}"
            return self.last_name
        elif style == CitationStyle.MLA:
            if self.initials:
                return f"{self.last_name}, {self.initials}"
            return self.last_name
        elif style == CitationStyle.IEEE:
            if self.initials:
                return f"{self.initials} {self.last_name}"
            return self.last_name
        else:
            if self.initials:
                return f"{self.last_name}, {self.initials}"
            return self.last_name


class CitationFormatter:
    """
    统一引用格式化器

    功能：
    1. 格式化单条或多条引用
    2. 转换引用格式
    3. 验证引用完整性
    """

    def __init__(self, default_style: str = "apa"):
        self.default_style = default_style.lower()
        if self.default_style not in SUPPORTED_STYLES:
            self.default_style = "apa"

    def format(
        self,
        paper: Dict[str, Any],
        style: Optional[str] = None,
        citation_id: Optional[str] = None
    ) -> FormattedCitation:
        """
        格式化单条引用

        Args:
            paper: 论文信息字典
            style: 引用格式 (apa/mla/chicago/ieee/gb7714/nature)
            citation_id: 引用ID

        Returns:
            FormattedCitation 对象
        """
        style = (style or self.default_style).lower()
        if style not in SUPPORTED_STYLES:
            style = self.default_style

        authors = paper.get("authors", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(";")]
        if not authors:
            authors = ["Unknown"]

        title = paper.get("title", "Unknown Title")
        year = str(paper.get("year", "n.d."))
        source = paper.get("source", "").lower()
        url = paper.get("url", "")
        doi = paper.get("doi", "")
        journal = paper.get("journal", paper.get("venue", ""))
        volume = paper.get("volume", "")
        pages = paper.get("pages", "")

        # 格式化作引用
        formatted = self._format_citation_text(
            authors=authors,
            title=title,
            year=year,
            source=source,
            url=url,
            doi=doi,
            journal=journal,
            volume=volume,
            pages=pages,
            style=style
        )

        return FormattedCitation(
            citation_id=citation_id or f"ref_{paper.get('paper_id', 'unknown')}",
            raw_text=paper.get("raw_text", ""),
            formatted=formatted,
            paper_id=paper.get("paper_id", ""),
            paper_title=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=volume,
            pages=pages,
            doi=doi,
            url=url,
            source=source,
        )

    def format_batch(
        self,
        papers: List[Dict[str, Any]],
        style: Optional[str] = None,
        start_id: int = 1
    ) -> List[FormattedCitation]:
        """
        批量格式化引用

        Args:
            papers: 论文列表
            style: 引用格式
            start_id: 起始ID

        Returns:
            FormattedCitation 列表
        """
        citations = []
        for i, paper in enumerate(papers):
            citation = self.format(paper, style, citation_id=f"ref_{start_id + i}")
            citations.append(citation)
        return citations

    def _format_citation_text(
        self,
        authors: List[str],
        title: str,
        year: str,
        source: str,
        url: str,
        doi: str,
        journal: str,
        volume: str,
        pages: str,
        style: str
    ) -> str:
        """根据格式类型格式化引用文本"""

        # 处理作者字符串
        author_str = self._format_authors(authors, style)

        # 根据style调用不同的格式化方法
        style_enum = CitationStyle(style)

        if style_enum == CitationStyle.APA:
            return self._apa_format(author_str, year, title, journal, volume, pages, doi, url)
        elif style_enum == CitationStyle.MLA:
            return self._mla_format(author_str, title, journal, year, volume, pages, url)
        elif style_enum == CitationStyle.CHICAGO:
            return self._chicago_format(author_str, title, journal, year, volume, pages, url)
        elif style_enum == CitationStyle.IEEE:
            return self._ieee_format(author_str, title, journal, year, volume, pages, url)
        elif style_enum == CitationStyle.GB7714:
            return self._gb7714_format(author_str, year, title, journal, volume, pages, doi, url)
        else:  # NATURE
            return self._nature_format(author_str, title, journal, year, volume, pages, doi, url)

    def _format_authors(self, authors: List[str], style: str) -> str:
        """格式化作者列表"""
        if not authors:
            return "Unknown"

        parsed = [AuthorName.parse(a) for a in authors]
        style_enum = CitationStyle(style)

        if len(parsed) == 1:
            return parsed[0].format(style_enum)
        elif len(parsed) == 2:
            return f"{parsed[0].format(style_enum)} & {parsed[1].format(style_enum)}"
        elif len(parsed) == 3:
            return f"{parsed[0].format(style_enum)}, {parsed[1].format(style_enum)}, & {parsed[2].format(style_enum)}"
        else:
            # 超过3个作者，只显示第一个 + et al.
            return f"{parsed[0].format(style_enum)} et al."

    def _apa_format(
        self,
        author: str,
        year: str,
        title: str,
        journal: str,
        volume: str,
        pages: str,
        doi: str,
        url: str
    ) -> str:
        """APA格式 (第7版)"""
        citation = f"{author} ({year}). {title}."

        if journal:
            citation += f" {journal}"
            if volume:
                citation += f", {volume}"
            if pages:
                citation += f", {pages}"

        if doi:
            citation += f". https://doi.org/{doi}"
        elif url:
            citation += f". {url}"

        return citation

    def _mla_format(
        self,
        author: str,
        title: str,
        journal: str,
        year: str,
        volume: str,
        pages: str,
        url: str
    ) -> str:
        """MLA格式 (第9版)"""
        citation = f'{author}. "{title}."'

        if journal:
            citation += f" {journal}"
            if volume:
                citation += f", vol. {volume}"
            citation += f", {year}"
        else:
            citation += f" {year}"

        if pages:
            citation += f", pp. {pages}"

        if url:
            citation += f". {url}"

        citation += "."
        return citation

    def _chicago_format(
        self,
        author: str,
        title: str,
        journal: str,
        year: str,
        volume: str,
        pages: str,
        url: str
    ) -> str:
        """Chicago格式"""
        citation = f'{author}. "{title}."'

        if journal:
            citation += f" {journal}"
            if volume:
                citation += f" {volume}"
            citation += f" ({year})"
        else:
            citation += f" {year}"

        if pages:
            citation += f": {pages}"

        if url:
            citation += f". {url}"

        citation += "."
        return citation

    def _ieee_format(
        self,
        author: str,
        title: str,
        journal: str,
        year: str,
        volume: str,
        pages: str,
        url: str
    ) -> str:
        """IEEE格式"""
        citation = f'{author}, "{title},"'

        if journal:
            citation += f" {journal}"
            if volume:
                citation += f", vol. {volume}"
            if pages:
                citation += f", pp. {pages}"

        citation += f", {year}"

        if url:
            citation += f". [Online]. Available: {url}"

        return citation

    def _gb7714_format(
        self,
        author: str,
        year: str,
        title: str,
        journal: str,
        volume: str,
        pages: str,
        doi: str,
        url: str
    ) -> str:
        """GB/T 7714格式 (中国国家标准)"""
        citation = f"{author}. {title}."

        if journal:
            citation += f" {journal}"
            if volume:
                citation += f", {volume}"
            if pages:
                citation += f", {pages}"

        citation += f". {year}"

        if doi:
            citation += f". DOI: {doi}"
        elif url:
            citation += f". {url}"

        return citation

    def _nature_format(
        self,
        author: str,
        title: str,
        journal: str,
        year: str,
        volume: str,
        pages: str,
        doi: str,
        url: str
    ) -> str:
        """Nature格式"""
        citation = f"{author}, {title}"

        if journal:
            citation += f", {journal}"
            if volume:
                citation += f", {volume}"
            if pages:
                citation += f", {pages}"

        citation += f", {year}"

        if doi:
            citation += f". https://doi.org/{doi}"

        return citation

    def convert_style(
        self,
        citations: List[Dict[str, Any]],
        to_style: str
    ) -> List[Dict[str, Any]]:
        """
        批量转换引用格式

        Args:
            citations: 现有引用列表
            to_style: 目标格式

        Returns:
            转换后的引用列表
        """
        converted = []
        for i, citation in enumerate(citations):
            formatted = self.format(citation, to_style, citation_id=citation.get("citation_id", f"ref_{i+1}"))
            converted.append(formatted.to_dict())
        return converted

    def validate(self, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证引用完整性

        Args:
            citations: 引用列表

        Returns:
            验证结果 {
                valid: bool,
                total: int,
                issues: List[Dict]
            }
        """
        issues = []
        for i, citation in enumerate(citations):
            missing = []
            if not citation.get("paper_title") and not citation.get("title"):
                missing.append("title")
            if not citation.get("year"):
                missing.append("year")
            if not citation.get("authors"):
                missing.append("authors")

            if missing:
                issues.append({
                    "citation_id": citation.get("citation_id", f"ref_{i+1}"),
                    "missing_fields": missing
                })

        return {
            "valid": len(issues) == 0,
            "total": len(citations),
            "issues": issues
        }


# 便捷函数
def format_citation(paper: Dict[str, Any], style: str = "apa") -> str:
    """
    便捷函数：格式化单条引用

    Args:
        paper: 论文信息
        style: 引用格式

    Returns:
        格式化后的引用字符串
    """
    formatter = CitationFormatter()
    return formatter.format(paper, style).formatted