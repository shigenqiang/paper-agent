"""
引用提取器 - Citation Extractor

功能：
1. 从文本中提取引用标记（如 [1], [2,3], (Smith, 2020)）
2. 识别文中引用
3. 提取完整引用上下文
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)


@dataclass
class CitationMatch:
    """引用匹配结果"""
    raw: str                    # 原始匹配文本
    citation_id: str           # 引用ID（如 "1" 或 "ref_1"）
    start_pos: int             # 在原文中的起始位置
    end_pos: int               # 在原文中的结束位置
    context_before: str = ""   # 引用前的文本（用于判断作者）
    context_after: str = ""    # 引用后的文本
    is_numeric: bool = True    # 是否是数字引用 [1] vs (Smith, 2020)
    author: str = ""            # 识别的作者名（如果是非数字引用）
    year: str = ""              # 识别的年份（如果是非数字引用）


class CitationExtractor:
    """
    引用提取器

    支持的引用格式：
    - 数字标记：[1], [2,3], [1-5]
    - 作者年份：(Smith, 2020), (Smith & Jones, 2020)
    - 上标标记：¹²³
    - 混合格式
    """

    # 数字引用模式：[1], [2,3], [1-5]
    NUMERIC_PATTERN = re.compile(r'\[(\d+(?:\s*,\s*\d+)*(?:\s*-\s*\d+)?)\]')

    # 作者年份模式：(Smith, 2020), (Smith & Jones, 2020), (Smith et al., 2020)
    AUTHOR_YEAR_PATTERN = re.compile(
        r'\(([A-Z][a-zA-Z\-\s]+)(?:,?\s*(?:&|,|and)\s*([A-Z][a-zA-Z\-\s]+)?(?:\s*,)?(?:\s*(?:et\s+al\.|and|&))?\s*,?\s*(\d{4}))\s*\)'
    )

    # 上标引用模式：¹²³
    SUPERSCRIPT_PATTERN = re.compile(r'[¹²³⁰⁴⁵⁶⁷⁸⁹]+')

    def __init__(self, min_context_chars: int = 50):
        """
        初始化引用提取器

        Args:
            min_context_chars: 提取上下文的最小字符数
        """
        self.min_context_chars = min_context_chars

    def extract_from_text(self, text: str) -> List[CitationMatch]:
        """
        从文本中提取所有引用

        Args:
            text: 输入文本

        Returns:
            CitationMatch 列表
        """
        if not text:
            return []

        matches = []

        # 提取数字引用 [1], [2,3], [1-5]
        numeric_matches = self._extract_numeric(text)
        matches.extend(numeric_matches)

        # 提取作者年份引用 (Smith, 2020)
        author_year_matches = self._extract_author_year(text)
        matches.extend(author_year_matches)

        # 按起始位置排序
        matches.sort(key=lambda m: m.start_pos)

        return matches

    def _extract_numeric(self, text: str) -> List[CitationMatch]:
        """提取数字引用 [1], [2,3], [1-5]"""
        matches = []

        for match in self.NUMERIC_PATTERN.finditer(text):
            raw = match.group(0)
            citation_ids = match.group(1)

            # 解析可能的范围 [1-5] -> [1,2,3,4,5]
            ids = self._parse_citation_ids(citation_ids)

            # 获取上下文
            start_pos = match.start()
            end_pos = match.end()
            context_before = text[max(0, start_pos - self.min_context_chars):start_pos]
            context_after = text[end_pos:min(len(text), end_pos + self.min_context_chars)]

            for cid in ids:
                matches.append(CitationMatch(
                    raw=raw,
                    citation_id=cid,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    context_before=context_before,
                    context_after=context_after,
                    is_numeric=True
                ))

        return matches

    def _extract_author_year(self, text: str) -> List[CitationMatch]:
        """提取作者年份引用 (Smith, 2020)"""
        matches = []

        for match in self.AUTHOR_YEAR_PATTERN.finditer(text):
            raw = match.group(0)

            # 解析作者和年份
            author_part = match.group(1).strip()
            second_author = match.group(2) if match.group(2) else ""
            year = match.group(3) if match.group(3) else ""

            # 构建完整作者字符串
            if second_author:
                author = f"{author_part} & {second_author.strip()}"
            else:
                author = author_part

            # 处理 "et al."
            if "et al." in text[match.start():match.end()].lower():
                author += " et al."

            start_pos = match.start()
            end_pos = match.end()
            context_before = text[max(0, start_pos - self.min_context_chars):start_pos]
            context_after = text[end_pos:min(len(text), end_pos + self.min_context_chars)]

            matches.append(CitationMatch(
                raw=raw,
                citation_id=f"{author_part}_{year}",
                start_pos=start_pos,
                end_pos=end_pos,
                context_before=context_before,
                context_after=context_after,
                is_numeric=False,
                author=author,
                year=year
            ))

        return matches

    def _parse_citation_ids(self, citation_str: str) -> List[str]:
        """
        解析引用ID字符串，支持范围和列表

        Args:
            citation_str: "1" or "2,3" or "1-5"

        Returns:
            ['1', '2', '3', '4', '5']
        """
        ids = []

        # 处理范围 [1-5]
        if '-' in citation_str:
            parts = citation_str.split('-')
            if len(parts) == 2:
                try:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    ids = [str(i) for i in range(start, end + 1)]
                except ValueError:
                    ids = [citation_str]
        else:
            # 处理列表 [2,3,4]
            for part in citation_str.split(','):
                part = part.strip()
                if part.isdigit():
                    ids.append(part)

        return ids if ids else [citation_str]

    def extract_citations_with_context(
        self,
        text: str,
        window_chars: int = 100
    ) -> List[Dict[str, Any]]:
        """
        提取引用及其上下文（用于答案生成）

        Args:
            text: 输入文本
            window_chars: 上下文窗口大小

        Returns:
            包含引用和上下文的字典列表
        """
        matches = self.extract_from_text(text)

        results = []
        for match in matches:
            results.append({
                "raw": match.raw,
                "citation_id": match.citation_id,
                "position": (match.start_pos, match.end_pos),
                "context": f"{match.context_before}...{match.context_after}",
                "is_numeric": match.is_numeric,
                "author": match.author if not match.is_numeric else "",
                "year": match.year if not match.is_numeric else "",
            })

        return results

    def count_citations(self, text: str) -> int:
        """
        统计文本中的引用数量

        Args:
            text: 输入文本

        Returns:
            引用数量
        """
        matches = self.extract_from_text(text)
        return len(matches)

    def get_unique_citation_ids(self, text: str) -> List[str]:
        """
        获取文本中所有唯一的引用ID

        Args:
            text: 输入文本

        Returns:
            唯一引用ID列表
        """
        matches = self.extract_from_text(text)
        seen = set()
        unique_ids = []

        for match in matches:
            if match.citation_id not in seen:
                seen.add(match.citation_id)
                unique_ids.append(match.citation_id)

        return unique_ids


# 便捷函数
def extract_citations(text: str) -> List[Dict[str, Any]]:
    """
    便捷函数：从文本提取引用

    Args:
        text: 输入文本

    Returns:
        引用列表
    """
    extractor = CitationExtractor()
    return extractor.extract_citations_with_context(text)