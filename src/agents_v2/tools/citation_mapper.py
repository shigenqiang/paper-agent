"""
引用关系映射器

功能:
1. 图表引用关系建立
2. 正文引用上下文提取
3. 引用意图分类（supports/challenges/compares）
4. 参考文献关联

设计原则:
- 自动识别引用模式
- 分类引用意图
- 建立完整的引用图
"""
from src.agents_v2.logging_config import get_logging_logger

import re

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class CitationIntent(str, Enum):
    """引用意图"""
    SUPPORTS = "supports"       # 支持本文工作
    CHALLENGES = "challenges"   # 挑战或质疑
    COMPARES = "compares"        # 与之比较
    EXTENDS = "extends"         # 扩展已有工作
    BELONGS_TO = "belongs_to"   # 属于同一研究线
    METIONS = "mentions"         # 仅提及


@dataclass
class CitationContext:
    """引用上下文"""
    marker: str                  # 引用标记，如 "[1]"
    preceding_text: str         # 前导文本
    following_text: str         # 后续文本
    intent: CitationIntent     # 引用意图
    position: int               # 在全文中的位置
    is_citation_to_figure: bool = False
    is_citation_to_table: bool = False
    figure_id: Optional[str] = None
    table_id: Optional[str] = None


@dataclass
class CitationRelation:
    """引用关系"""
    citation_marker: str
    reference_index: int         # 参考文献编号
    context: CitationContext
    referring_paragraph: str      # 引用所在的段落


@dataclass
class CitationGraph:
    """引用图

    存储论文中所有引用关系
    """
    citations: Dict[str, CitationRelation] = field(default_factory=dict)
    figure_citations: Dict[str, List[str]] = field(default_factory=dict)
    table_citations: Dict[str, List[str]] = field(default_factory=dict)
    reference_usage: Dict[int, int] = field(default_factory=dict)  # 参考文献index -> 使用次数


class CitationRelationMapper:
    """引用关系映射器"""

    # 引用意图关键词
    INTENT_KEYWORDS = {
        CitationIntent.SUPPORTS: [
            "based on", "using", "adopt", "follow", "依据", "采用",
            "according to", "based upon"
        ],
        CitationIntent.CHALLENGES: [
            "however", "contrary", "different", "although", "despite",
            "然而", "但是", "不同于", "尽管"
        ],
        CitationIntent.COMPARES: [
            "compare", "similar", "unlike", "whereas", "while",
            "对比", "比较", "类似于", "不同于"
        ],
        CitationIntent.EXTENDS: [
            "extend", "build upon", "improve", "further", "基于",
            "扩展", "改进", "进一步", "在...基础上"
        ],
    }

    # 图表引用模式
    FIGURE_PATTERNS = [
        r'(?:图|Figure|Fig\.?)\s*(\d+[a-zA-Z]?)',
        r'shown in (?:Figure|Fig\.?)\s*(\d+[a-zA-Z]?)',
        r'illustrated in (?:Figure|Fig\.?)\s*(\d+[a-zA-Z]?)',
    ]

    TABLE_PATTERNS = [
        r'(?:表|Table)\s*(\d+[a-zA-Z]?)',
        r'presented in (?:Table)\s*(\d+[a-zA-Z]?)',
        r'listed in (?:Table)\s*(\d+[a-zA-Z]?)',
    ]

    def __init__(self):
        self._citation_patterns = self._init_citation_patterns()

    def _init_citation_patterns(self) -> List[re.Pattern]:
        """初始化引用检测模式"""
        return [
            # [1], [2,3], [1-5] 格式
            re.compile(r'\[(\d+(?:[,-]\d+)*)\]'),
            # [Smith et al., 2020] 格式
            re.compile(r'\[([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4})\]'),
        ]

    def build_citation_graph(
        self,
        full_text: str,
        references: List[str]
    ) -> CitationGraph:
        """构建完整引用图

        Args:
            full_text: 论文全文
            references: 参考文献列表

        Returns:
            CitationGraph: 引用图
        """
        graph = CitationGraph()

        # 1. 收集所有引用标记
        citation_markers = self._collect_citation_markers(full_text)

        # 2. 建立引用上下文
        for marker in citation_markers:
            context = self._extract_citation_context(full_text, marker)
            relation = self._build_citation_relation(
                marker, context, full_text, references
            )

            if relation:
                graph.citations[marker] = relation

                # 统计引用使用
                if relation.reference_index not in graph.reference_usage:
                    graph.reference_usage[relation.reference_index] = 0
                graph.reference_usage[relation.reference_index] += 1

        # 3. 建立图表引用关系
        graph.figure_citations = self._extract_figure_citations(full_text)
        graph.table_citations = self._extract_table_citations(full_text)

        return graph

    def _collect_citation_markers(self, text: str) -> List[str]:
        """收集所有引用标记"""
        markers = set()

        for pattern in self._citation_patterns:
            matches = pattern.findall(text)
            for match in matches:
                # 处理 [1,2,3] 或 [1-5] 格式
                if ',' in match or '-' in match:
                    # 分割并展开
                    nums = re.findall(r'\d+', match)
                    for num in nums:
                        markers.add(f"[{num}]")
                else:
                    markers.add(f"[{match}]")

        return sorted(list(markers), key=lambda x: int(re.search(r'\d+', x).group()))

    def _extract_citation_context(
        self,
        text: str,
        marker: str
    ) -> CitationContext:
        """提取引用上下文

        Args:
            text: 全文
            marker: 引用标记

        Returns:
            CitationContext: 引用上下文
        """
        # 找到引用在正文中的位置
        position = text.find(marker)
        if position == -1:
            return CitationContext(
                marker=marker,
                preceding_text="",
                following_text="",
                intent=CitationIntent.METIONS,
                position=0
            )

        # 提取前后各150个字符作为上下文
        start = max(0, position - 150)
        end = min(len(text), position + 150)

        preceding = text[start:position].strip()
        following = text[position + len(marker):end].strip()

        # 判断引用意图
        intent = self._classify_citation_intent(preceding, following)

        # 检查是否引用图表
        is_figure, figure_id = self._check_figure_reference(preceding, following)
        is_table, table_id = self._check_table_reference(preceding, following)

        return CitationContext(
            marker=marker,
            preceding_text=preceding[-100:] if len(preceding) > 100 else preceding,
            following_text=following[:100] if len(following) > 100 else following,
            intent=intent,
            position=position,
            is_citation_to_figure=is_figure,
            is_citation_to_table=is_table,
            figure_id=figure_id,
            table_id=table_id
        )

    def _classify_citation_intent(
        self,
        preceding: str,
        following: str
    ) -> CitationIntent:
        """分类引用意图

        Args:
            preceding: 前导文本
            following: 后续文本

        Returns:
            CitationIntent: 引用意图
        """
        combined = (preceding + following).lower()

        # 按优先级检测
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in combined for keyword in keywords):
                return intent

        return CitationIntent.METIONS

    def _check_figure_reference(
        self,
        preceding: str,
        following: str
    ) -> Tuple[bool, Optional[str]]:
        """检查是否引用图片

        Returns:
            Tuple[bool, Optional[str]]: (是否引用图片, 图片ID)
        """
        combined = preceding + " " + following

        for pattern in self.FIGURE_PATTERNS:
            match = re.search(pattern, combined, flags=re.IGNORECASE)
            if match:
                return True, match.group(1)

        return False, None

    def _check_table_reference(
        self,
        preceding: str,
        following: str
    ) -> Tuple[bool, Optional[str]]:
        """检查是否引用表格

        Returns:
            Tuple[bool, Optional[str]]: (是否引用表格, 表格ID)
        """
        combined = preceding + " " + following

        for pattern in self.TABLE_PATTERNS:
            match = re.search(pattern, combined, flags=re.IGNORECASE)
            if match:
                return True, match.group(1)

        return False, None

    def _build_citation_relation(
        self,
        marker: str,
        context: CitationContext,
        full_text: str,
        references: List[str]
    ) -> Optional[CitationRelation]:
        """构建引用关系"""
        # 提取引用编号
        num_match = re.search(r'\d+', marker)
        if not num_match:
            return None

        ref_index = int(num_match.group())

        # 检查是否超出范围
        if ref_index > len(references):
            logger.warning(f"Citation [{ref_index}] out of range (total {len(references)} refs)")
            ref_index = min(ref_index, len(references))

        # 获取引用所在段落
        paragraph = self._get_containing_paragraph(full_text, context.position)

        return CitationRelation(
            citation_marker=marker,
            reference_index=ref_index,
            context=context,
            referring_paragraph=paragraph
        )

    def _get_containing_paragraph(
        self,
        text: str,
        position: int
    ) -> str:
        """获取包含位置的段落"""
        # 向前找段落开始
        start = position
        while start > 0 and text[start - 1] not in '\n\n':
            start -= 1

        # 向后找段落结束
        end = position
        while end < len(text) and text[end] not in '\n\n':
            end += 1

        return text[start:end].strip()

    def _extract_figure_citations(self, text: str) -> Dict[str, List[str]]:
        """提取图片引用关系

        Returns:
            Dict[str, List[str]]: figure_id -> citation_markers
        """
        figure_citations = {}

        for pattern in self.FIGURE_PATTERNS:
            matches = re.finditer(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                figure_id = match.group(1)

                # 找到该位置附近的引用标记
                pos = match.start()
                nearby_markers = self._find_nearby_citations(text, pos)

                if figure_id not in figure_citations:
                    figure_citations[figure_id] = []
                figure_citations[figure_id].extend(nearby_markers)

        return figure_citations

    def _extract_table_citations(self, text: str) -> Dict[str, List[str]]:
        """提取表格引用关系

        Returns:
            Dict[str, List[str]]: table_id -> citation_markers
        """
        table_citations = {}

        for pattern in self.TABLE_PATTERNS:
            matches = re.finditer(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                table_id = match.group(1)

                # 找到该位置附近的引用标记
                pos = match.start()
                nearby_markers = self._find_nearby_citations(text, pos)

                if table_id not in table_citations:
                    table_citations[table_id] = []
                table_citations[table_id].extend(nearby_markers)

        return table_citations

    def _find_nearby_citations(
        self,
        text: str,
        position: int,
        window: int = 50
    ) -> List[str]:
        """找到位置附近的引用标记"""
        nearby = text[max(0, position - window):position + window]
        markers = []

        for pattern in self._citation_patterns:
            matches = pattern.findall(nearby)
            for match in matches:
                if ',' in match or '-' in match:
                    nums = re.findall(r'\d+', match)
                    for num in nums:
                        markers.append(f"[{num}]")
                else:
                    markers.append(f"[{match}]")

        return markers

    def get_citation_summary(self, graph: CitationGraph) -> Dict[str, Any]:
        """获取引用摘要

        Args:
            graph: 引用图

        Returns:
            Dict: 引用摘要统计
        """
        intent_counts = {}
        for citation in graph.citations.values():
            intent = citation.context.intent
            intent_counts[intent.value] = intent_counts.get(intent.value, 0) + 1

        return {
            "total_citations": len(graph.citations),
            "unique_references_used": len(graph.reference_usage),
            "most_cited_reference": max(
                graph.reference_usage.items(),
                key=lambda x: x[1],
                default=(0, 0)
            )[0] if graph.reference_usage else None,
            "citation_intents": intent_counts,
            "figure_citations_count": len(graph.figure_citations),
            "table_citations_count": len(graph.table_citations),
            "references_usage": graph.reference_usage
        }

    def find_unused_references(self, graph: CitationGraph, total_refs: int) -> List[int]:
        """找出未被引用的参考文献

        Args:
            graph: 引用图
            total_refs: 总参考文献数

        Returns:
            List[int]: 未被引用的参考文献编号
        """
        used = set(graph.reference_usage.keys())
        unused = [i for i in range(1, total_refs + 1) if i not in used]
        return unused

    def find_citation_chain(self, graph: CitationGraph, ref_index: int) -> List[str]:
        """找出引用某参考文献的所有引用位置

        Args:
            graph: 引用图
            ref_index: 参考文献编号

        Returns:
            List[str]: 引用标记列表
        """
        chain = []
        for marker, relation in graph.citations.items():
            if relation.reference_index == ref_index:
                chain.append(marker)
        return chain


# 便捷函数
def build_citation_graph(
    full_text: str,
    references: List[str]
) -> CitationGraph:
    """构建引用图"""
    mapper = CitationRelationMapper()
    return mapper.build_citation_graph(full_text, references)


def get_citation_summary(graph: CitationGraph) -> Dict[str, Any]:
    """获取引用摘要"""
    mapper = CitationRelationMapper()
    return mapper.get_citation_summary(graph)