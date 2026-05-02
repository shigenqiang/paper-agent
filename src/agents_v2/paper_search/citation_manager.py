"""引用管理Agent - 管理论文参考文献和引用格式"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_qa_agent import BaseQAAgent
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


@dataclass
class Citation:
    """引用条目"""
    citation_id: str
    raw_text: str = ""
    formatted: str = ""  # 格式化后的引用
    paper_id: str = ""
    paper_title: str = ""
    authors: List[str] = field(default_factory=list)
    year: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    doi: str = ""

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
            "doi": self.doi
        }


class CitationManager(BaseQAAgent):
    """
    引用管理Agent

    职责：
    1. 格式化参考文献（APA、MLA、Chicago等）
    2. 检查引用完整性
    3. 生成参考文献列表
    4. 转换引用格式

    支持的格式：
    - APA 7th
    - MLA 9th
    - Chicago
    - IEEE
    """

    SUPPORTED_STYLES = ["apa", "mla", "chicago", "ieee", "nature"]

    def __init__(self):
        super().__init__(
            name="CitationManager",
            description="引用管理Agent - 管理论文参考文献和引用格式"
        )

    async def execute(
        self,
        papers: List[Dict],
        style: str = "apa",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        管理引用

        Args:
            papers: 论文列表
            style: 引用格式（apa, mla, chicago, ieee, nature）
            context: 上下文

        Returns:
            包含格式化引用的字典
        """
        self.logger.info(f"格式化 {len(papers)} 篇论文的引用，格式: {style}")

        if style.lower() not in self.SUPPORTED_STYLES:
            return {
                "success": False,
                "error": f"不支持的格式: {style}，支持的格式: {self.SUPPORTED_STYLES}",
                "citations": []
            }

        try:
            citations = []
            for i, paper in enumerate(papers):
                citation = self._format_citation(paper, style)
                citation.citation_id = f"ref_{i+1}"
                citations.append(citation)

            self.logger.info(f"成功格式化 {len(citations)} 条引用")

            return {
                "success": True,
                "citations": [c.to_dict() for c in citations],
                "style": style,
                "count": len(citations)
            }

        except Exception as e:
            self.logger.error(f"引用格式化失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "citations": []
            }

    def _format_citation(self, paper: Dict, style: str) -> Citation:
        """格式化单条引用"""
        authors = paper.get("authors", [])
        title = paper.get("title", "Unknown Title")
        year = str(paper.get("year", "n.d."))
        source = paper.get("source", "").lower()
        url = paper.get("url", "")
        doi = paper.get("doi", "")

        # 准备作者字符串
        if not authors:
            author_str = "Unknown"
        elif len(authors) == 1:
            author_str = self._format_author_name(authors[0], style)
        elif len(authors) == 2:
            author_str = f"{self._format_author_name(authors[0], style)} & {self._format_author_name(authors[1], style)}"
        else:
            author_str = f"{self._format_author_name(authors[0], style)} et al."

        if style.lower() == "apa":
            formatted = self._apa_format(author_str, year, title, source, url, doi)
        elif style.lower() == "mla":
            formatted = self._mla_format(author_str, title, source, year, url)
        elif style.lower() == "chicago":
            formatted = self._chicago_format(author_str, title, source, year, url)
        elif style.lower() == "ieee":
            formatted = self._ieee_format(author_str, title, source, year, url)
        else:  # nature
            formatted = self._nature_format(author_str, title, source, year, url)

        return Citation(
            paper_id=paper.get("paper_id", ""),
            paper_title=title,
            authors=authors,
            year=year,
            formatted=formatted,
            doi=doi
        )

    def _format_author_name(self, name: str, style: str) -> str:
        """格式化作者名"""
        if not name:
            return ""

        # 假设name格式为 "Last, First" 或 "First Last"
        if "," in name:
            parts = name.split(",")
            last = parts[0].strip()
            first = parts[1].strip() if len(parts) > 1 else ""
            if first:
                initials = "".join([n[0] + "." for n in first.split()])
                return f"{last}, {initials}"
            return last
        else:
            parts = name.split()
            if len(parts) > 1:
                last = parts[-1]
                initials = "".join([n[0] + "." for n in parts[:-1]])
                return f"{last}, {initials}"
            return name

    def _apa_format(
        self,
        author: str,
        year: str,
        title: str,
        source: str,
        url: str,
        doi: str
    ) -> str:
        """APA格式"""
        citation = f"{author} ({year}). {title}."

        if source == "arxiv":
            citation += " arXiv preprint."
        elif source == "pubmed":
            citation += " [Peer-reviewed journal article]."

        if doi:
            citation += f" https://doi.org/{doi}"
        elif url:
            citation += f" {url}"

        return citation

    def _mla_format(
        self,
        author: str,
        title: str,
        source: str,
        year: str,
        url: str
    ) -> str:
        """MLA格式"""
        citation = f'{author}. "{title}."'

        if source == "arxiv":
            citation += " arXiv,"
        elif source == "pubmed":
            citation += " Journal,"

        citation += f" {year}"

        if url:
            citation += f". {url}"

        citation += "."

        return citation

    def _chicago_format(
        self,
        author: str,
        title: str,
        source: str,
        year: str,
        url: str
    ) -> str:
        """Chicago格式"""
        citation = f"{author}. \"{title}.\""

        if source == "arxiv":
            citation += " arXiv"
        elif source == "pubmed":
            citation += " Journal"

        citation += f" ({year})"

        if url:
            citation += f". {url}"

        citation += "."

        return citation

    def _ieee_format(
        self,
        author: str,
        title: str,
        source: str,
        year: str,
        url: str
    ) -> str:
        """IEEE格式"""
        citation = f"{author}, \"{title},\""

        if source == "arxiv":
            citation += " arXiv"
        elif source == "pubmed":
            citation += " IEEE"
        else:
            citation += " preprint"

        citation += f", {year}"

        if url:
            citation += f". [Online]. Available: {url}"

        return citation

    def _nature_format(
        self,
        author: str,
        title: str,
        source: str,
        year: str,
        url: str
    ) -> str:
        """Nature格式"""
        citation = f"{author}, {title}"

        if source == "arxiv":
            citation += ", arXiv ("
        elif source == "pubmed":
            citation += ", Nature ("
        else:
            citation += ", "

        citation += f"{year})"

        if url:
            citation += f" {url}"

        return citation

    async def convert_style(
        self,
        citations: List[Dict],
        from_style: str,
        to_style: str
    ) -> Dict[str, Any]:
        """转换引用格式"""
        if to_style.lower() not in self.SUPPORTED_STYLES:
            return {
                "success": False,
                "error": f"不支持的目标格式: {to_style}",
                "citations": []
            }

        # 重新格式化
        return await self.execute(citations, to_style)

    def validate_citations(self, citations: List[Dict]) -> Dict[str, Any]:
        """验证引用完整性"""
        issues = []

        for i, citation in enumerate(citations):
            missing = []

            if not citation.get("paper_title"):
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