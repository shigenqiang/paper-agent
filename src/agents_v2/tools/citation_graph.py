"""
Citation Graph - 引用图谱

构建和管理论文之间的引用关系图。
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CitationNode:
    """引用图节点（论文）"""
    paper_id: str
    title: str
    authors: List[str]
    year: Optional[int] = None
    citations_count: int = 0
    references_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CitationEdge:
    """引用边"""
    from_paper: str  # 引用方
    to_paper: str    # 被引用方
    edge_type: str = "cites"  # "cites" or "referenced_by"


class CitationGraph:
    """引用图谱

    管理论文之间的引用关系。
    """

    def __init__(self):
        """初始化引用图谱"""
        self.nodes: Dict[str, CitationNode] = {}
        self.edges: List[CitationEdge] = []
        self._citations: Dict[str, Set[str]] = defaultdict(set)  # paper -> set of papers it cites
        self._references: Dict[str, Set[str]] = defaultdict(set)  # paper -> set of papers that cite it

    def add_paper(
        self,
        paper_id: str,
        title: str,
        authors: List[str],
        year: Optional[int] = None,
        **metadata
    ) -> CitationNode:
        """添加论文到图谱

        Args:
            paper_id: 论文ID
            title: 论文标题
            authors: 作者列表
            year: 发表年份
            **metadata: 其他元数据

        Returns:
            CitationNode: 创建的节点
        """
        node = CitationNode(
            paper_id=paper_id,
            title=title,
            authors=authors,
            year=year,
            metadata=metadata
        )
        self.nodes[paper_id] = node
        return node

    def add_citation(self, from_paper: str, to_paper: str) -> None:
        """添加引用关系

        Args:
            from_paper: 引用方论文ID
            to_paper: 被引用方论文ID
        """
        # 确保节点存在
        if from_paper not in self.nodes:
            self.nodes[from_paper] = CitationNode(
                paper_id=from_paper,
                title="",
                authors=[]
            )
        if to_paper not in self.nodes:
            self.nodes[to_paper] = CitationNode(
                paper_id=to_paper,
                title="",
                authors=[]
            )

        # 添加边
        edge = CitationEdge(from_paper=from_paper, to_paper=to_paper)
        self.edges.append(edge)

        # 更新邻接表
        self._citations[from_paper].add(to_paper)
        self._references[to_paper].add(from_paper)

        # 更新计数
        self.nodes[from_paper].references_count += 1
        self.nodes[to_paper].citations_count += 1

    def get_citations(self, paper_id: str) -> List[str]:
        """获取论文引用的所有论文

        Args:
            paper_id: 论文ID

        Returns:
            List[str]: 被引用论文ID列表
        """
        return list(self._citations.get(paper_id, set()))

    def get_references(self, paper_id: str) -> List[str]:
        """获取论文的所有参考文献（引用该论文的）

        Args:
            paper_id: 论文ID

        Returns:
            List[str]: 参考文献论文ID列表
        """
        return list(self._references.get(paper_id, set()))

    def get_citation_chain(self, paper_id: str, depth: int = 2) -> List[List[str]]:
        """获取引用链

        Args:
            paper_id: 起始论文ID
            depth: 追溯深度

        Returns:
            List[List[str]]: 引用链列表
        """
        chains = []

        def dfs(current_id: str, path: List[str], current_depth: int):
            if current_depth >= depth:
                return

            citations = self.get_citations(current_id)
            for cited in citations:
                if cited not in path:  # 避免循环
                    new_path = path + [cited]
                    chains.append(new_path)
                    dfs(cited, new_path, current_depth + 1)

        dfs(paper_id, [paper_id], 0)
        return chains

    def get_reference_chain(self, paper_id: str, depth: int = 2) -> List[List[str]]:
        """获取参考链（被引用路径）

        Args:
            paper_id: 起始论文ID
            depth: 追溯深度

        Returns:
            List[List[str]]: 参考链列表
        """
        chains = []

        def dfs(current_id: str, path: List[str], current_depth: int):
            if current_depth >= depth:
                return

            references = self.get_references(current_id)
            for referencer in references:
                if referencer not in path:  # 避免循环
                    new_path = [referencer] + path
                    chains.append(new_path)
                    dfs(referencer, new_path, current_depth + 1)

        dfs(paper_id, [paper_id], 0)
        return chains

    def get_common_citations(self, paper_id1: str, paper_id2: str) -> List[str]:
        """获取两篇论文的共同引用

        Args:
            paper_id1: 论文1 ID
            paper_id2: 论文2 ID

        Returns:
            List[str]: 共同引用论文ID列表
        """
        citations1 = self._citations.get(paper_id1, set())
        citations2 = self._citations.get(paper_id2, set())
        return list(citations1 & citations2)

    def get_influential_papers(self, min_citations: int = 10) -> List[CitationNode]:
        """获取高影响力论文

        Args:
            min_citations: 最小引用数

        Returns:
            List[CitationNode]: 高影响力论文列表
        """
        return [
            node for node in self.nodes.values()
            if node.citations_count >= min_citations
        ]

    def get_papers_by_year(self, year: int) -> List[CitationNode]:
        """获取特定年份发表的论文

        Args:
            year: 年份

        Returns:
            List[CitationNode]: 该年份的论文列表
        """
        return [
            node for node in self.nodes.values()
            if node.year == year
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_papers": len(self.nodes),
            "total_citations": len(self.edges),
            "avg_citations_per_paper": (
                sum(n.citations_count for n in self.nodes.values()) / len(self.nodes)
                if self.nodes else 0
            ),
            "year_distribution": self._get_year_distribution(),
            "most_cited": (
                max(self.nodes.values(), key=lambda n: n.citations_count).paper_id
                if self.nodes else None
            )
        }

    def _get_year_distribution(self) -> Dict[int, int]:
        """获取年份分布"""
        distribution: Dict[int, int] = defaultdict(int)
        for node in self.nodes.values():
            if node.year:
                distribution[node.year] += 1
        return dict(distribution)


# 便捷函数
def create_citation_graph() -> CitationGraph:
    """创建引用图谱的便捷函数"""
    return CitationGraph()
