"""
引用解析器 - Citation Parser

从文本中提取和管理引用标记。
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class CitationStyle(Enum):
    """引用格式风格"""
    APA = "apa"
    GB7714 = "gb7714"  # 中国国家标准
    CHICAGO = "chicago"
    IEEE = "ieee"
    MLA = "mla"
    PLAIN = "plain"  # 纯文本


@dataclass
class Citation:
    """单个引用"""
    ref_num: str  # 引用编号（如"1", "2-5"）
    text: str = ""  # 引用文本
    position: int = 0  # 在原文中的位置
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def expand(self) -> List[str]:
        """展开引用范围，返回单独编号列表"""
        result = []
        for part in self.ref_num.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                if start.isdigit() and end.isdigit():
                    result.extend(str(i) for i in range(int(start), int(end) + 1))
            elif part.isdigit():
                result.append(part)
        return result


@dataclass
class ParsedCitation:
    """解析后的引用"""
    ref_num: str
    authors: Optional[List[str]] = None
    year: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None


class CitationParser:
    """
    引用解析器

    从文本中提取引用标记，如[1], [1,2], [1-3]。
    支持多种格式的引用解析。
    """

    # 匹配[1], [1,2], [1-3], [1,2-5]等格式
    CITATION_PATTERN = re.compile(r'\[(\d+(?:[,-]\d+)*)\]')

    # 匹配DOI
    DOI_PATTERN = re.compile(r'doi[:\s]+(10\.\d{4,}/[^\s]+)', re.IGNORECASE)

    # 匹配年份
    YEAR_PATTERN = re.compile(r'\((\d{4})\)|\b(\d{4})\b')

    def __init__(self, style: CitationStyle = CitationStyle.PLAIN):
        self.style = style

    def parse(self, text: str) -> List[Citation]:
        """
        从文本中解析所有引用

        Args:
            text: 包含引用的文本

        Returns:
            List[Citation]: 引用列表
        """
        citations = []
        for match in self.CITATION_PATTERN.finditer(text):
            ref_num = match.group(1)
            position = match.start()

            citation = Citation(
                ref_num=ref_num,
                text=match.group(0),
                position=position,
                metadata={"original": match.group(0)}
            )
            citations.append(citation)

        return citations

    def extract_ref_numbers(self, text: str) -> List[str]:
        """
        提取引用编号（去重）

        Args:
            text: 包含引用的文本

        Returns:
            List[str]: 去重后的引用编号列表
        """
        parsed = self.parse(text)
        all_refs = []

        for citation in parsed:
            all_refs.extend(citation.expand())

        return list(set(all_refs))

    def extract_doi(self, text: str) -> List[str]:
        """从文本中提取DOI"""
        return self.DOI_PATTERN.findall(text)

    def extract_year(self, text: str) -> List[str]:
        """从文本中提取年份"""
        years = []
        for match in self.YEAR_PATTERN.finditer(text):
            year = match.group(1) or match.group(2)
            if year:
                years.append(year)
        return years

    def parse_reference(self, ref_text: str) -> ParsedCitation:
        """
        解析参考文献文本

        Args:
            ref_text: 参考文献文本，如"[1] Smith et al. (2020). Title..."

        Returns:
            ParsedCitation: 解析后的引用
        """
        # 简化实现，实际应用中需要更复杂的解析逻辑
        ref_num_match = re.match(r'\[(\d+)\]', ref_text)

        return ParsedCitation(
            ref_num=ref_num_match.group(1) if ref_num_match else "",
            metadata={"original": ref_text}
        )


def parse_citations(text: str, style: CitationStyle = CitationStyle.PLAIN) -> List[Citation]:
    """
    便捷函数：解析文本中的引用

    Args:
        text: 包含引用的文本
        style: 引用格式风格

    Returns:
        List[Citation]: 引用列表
    """
    parser = CitationParser(style=style)
    return parser.parse(text)
