"""
引用追踪器 - Citation Tracker

追踪和管理文档中的引用关系。
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from .citation_parser import Citation, ParsedCitation
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


@dataclass
class CitationNode:
    """引用节点"""
    ref_num: str
    citation: ParsedCitation
    cited_by: List[str] = field(default_factory=list)  # 引用此文献的编号列表
    cites: List[str] = field(default_factory=list)  # 此文献引用的编号列表
    position: int = 0  # 在文档中首次出现的位置


@dataclass
class CitationStatistics:
    """引用统计"""
    total_citations: int = 0
    unique_references: int = 0
    self_citations: int = 0
    most_cited: Optional[str] = None
    citation_frequency: Dict[str, int] = field(default_factory=dict)


class CitationTracker:
    """
    引用追踪器

    追踪文档中的引用关系，支持：
    - 引用图构建
    - 引用统计
    - 引用溯源
    - 检测自引
    """

    def __init__(self):
        self.nodes: Dict[str, CitationNode] = {}
        self.citation_order: List[str] = []  # 引用出现顺序

    def add_citation(self, citation: Citation, parsed: ParsedCitation):
        """
        添加引用

        Args:
            citation: 原始引用
            parsed: 解析后的引用
        """
        ref_num = citation.ref_num

        if ref_num not in self.nodes:
            self.nodes[ref_num] = CitationNode(
                ref_num=ref_num,
                citation=parsed,
                position=citation.position
            )
            self.citation_order.append(ref_num)

    def add_reference(
        self,
        ref_num: str,
        parsed: ParsedCitation,
        cited_refs: Optional[List[str]] = None
    ):
        """
        添加参考文献

        Args:
            ref_num: 引用编号
            parsed: 解析后的引用
            cited_refs: 此参考文献引用的其他编号列表
        """
        if ref_num not in self.nodes:
            self.nodes[ref_num] = CitationNode(
                ref_num=ref_num,
                citation=parsed
            )

        if cited_refs:
            self.nodes[ref_num].cites = cited_refs
            # 更新被引用者的cited_by
            for cited in cited_refs:
                if cited in self.nodes:
                    if ref_num not in self.nodes[cited].cited_by:
                        self.nodes[cited].cited_by.append(ref_num)

    def get_citation(self, ref_num: str) -> Optional[CitationNode]:
        """获取引用节点"""
        return self.nodes.get(ref_num)

    def get_references(self) -> List[CitationNode]:
        """获取所有引用节点"""
        return list(self.nodes.values())

    def get_citation_order(self) -> List[str]:
        """获取引用出现顺序"""
        return self.citation_order.copy()

    def is_self_citation(self, ref_num: str, author: str) -> bool:
        """
        检测自引

        Args:
            ref_num: 引用编号
            author: 作者名

        Returns:
            bool: 是否为自引
        """
        node = self.nodes.get(ref_num)
        if not node or not node.citation.authors:
            return False

        authors = node.citation.authors
        if isinstance(authors, str):
            return author in authors
        return any(author in a for a in authors)

    def get_statistics(self) -> CitationStatistics:
        """获取引用统计"""
        stats = CitationStatistics()

        all_ref_nums = []
        for node in self.nodes.values():
            all_ref_nums.append(node.ref_num)
            stats.citation_frequency[node.ref_num] = len(node.cited_by)

        stats.total_citations = len(all_ref_nums)
        stats.unique_references = len(set(all_ref_nums))

        if stats.citation_frequency:
            most_cited = max(stats.citation_frequency.items(), key=lambda x: x[1])
            stats.most_cited = most_cited[0]

        return stats

    def get_citation_chain(self, ref_num: str) -> List[str]:
        """
        获取引用链

        Args:
            ref_num: 起始引用编号

        Returns:
            List[str]: 引用链（此文献引用 -> 被引用 -> ...）
        """
        chain = [ref_num]
        visited: Set[str] = {ref_num}

        current = ref_num
        while current in self.nodes:
            cites = self.nodes[current].cites
            if not cites:
                break

            # 找到第一个未访问的引用
            next_ref = None
            for cited in cites:
                if cited not in visited:
                    next_ref = cited
                    break

            if not next_ref:
                break

            chain.append(next_ref)
            visited.add(next_ref)
            current = next_ref

        return chain

    def build_citation_graph(self) -> Dict[str, List[str]]:
        """
        构建引用图

        Returns:
            Dict[str, List[str]]: {ref_num: [被引用编号列表]}
        """
        graph: Dict[str, List[str]] = {}

        for ref_num, node in self.nodes.items():
            graph[ref_num] = node.cites.copy()

        return graph

    def detect_citation_loops(self) -> List[List[str]]:
        """
        检测引用循环

        Returns:
            List[List[str]]: 所有引用循环
        """
        loops = []
        visited: Set[str] = set()

        def dfs(node: str, path: List[str]):
            if node in visited:
                # 发现循环
                if node in path:
                    loop_start = path.index(node)
                    loop = path[loop_start:] + [node]
                    if loop not in loops:
                        loops.append(loop)
                return

            visited.add(node)
            path.append(node)

            if node in self.nodes:
                for cited in self.nodes[node].cites:
                    dfs(cited, path.copy())

        for ref_num in self.nodes:
            dfs(ref_num, [])

        return loops

    def clear(self):
        """清空所有引用"""
        self.nodes.clear()
        self.citation_order.clear()
        logger.info("Citation tracker cleared")
