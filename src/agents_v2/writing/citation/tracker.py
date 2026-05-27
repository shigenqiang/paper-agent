"""
引用追踪器 - Citation Tracker

功能：
1. 追踪答案中的引用来源
2. 构建引用图谱
3. 生成引用报告
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


@dataclass
class TrackedCitation:
    """追踪的引用"""
    citation_id: str
    source_paper_id: str
    source_title: str
    context: str                    # 引用出现的上下文
    position: int                  # 在答案中的位置
    relevance_score: float = 0.0   # 与问题的相关性
    verified: bool = False         # 是否已验证


@dataclass
class CitationSource:
    """引用来源"""
    paper_id: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: str = ""
    url: str = ""
    abstract: str = ""
    cited_in_answer: bool = False
    citation_count: int = 0


class CitationTracker:
    """
    引用追踪器

    功能：
    1. 追踪答案中的引用
    2. 验证引用的真实性
    3. 构建引用图谱
    4. 生成引用质量报告

    使用场景：
    - QA系统：追踪答案中引用的论文
    - 报告生成：追踪使用的参考资料
    """

    def __init__(self):
        self.tracked_citations: List[TrackedCitation] = []
        self.sources: Dict[str, CitationSource] = {}
        self.citation_graph: Dict[str, Set[str]] = defaultdict(set)  # paper_id -> related_paper_ids

    def track(
        self,
        answer: str,
        contexts: List[Dict[str, Any]],
        question: str = ""
    ) -> Dict[str, Any]:
        """
        追踪答案中的引用

        Args:
            answer: 生成的答案
            contexts: 检索到的上下文列表
            question: 原始问题（用于相关性评估）

        Returns:
            追踪报告 {
                total_citations: int,
                verified_citations: int,
                unverified_citations: int,
                sources: List[Dict],
                citation_map: Dict[str, List[str]],
            }
        """
        from .extractor import CitationExtractor

        extractor = CitationExtractor()

        # 提取引用
        citations = extractor.extract_from_text(answer)

        # 清空之前的追踪
        self.tracked_citations = []
        self.sources = {}

        # 构建来源映射
        for ctx in contexts:
            paper_id = ctx.get("paper_id", ctx.get("id", ""))
            if paper_id and paper_id not in self.sources:
                self.sources[paper_id] = CitationSource(
                    paper_id=paper_id,
                    title=ctx.get("title", ""),
                    authors=ctx.get("authors", []),
                    year=str(ctx.get("year", "")),
                    url=ctx.get("url", ""),
                    abstract=ctx.get("abstract", "")
                )

        # 追踪每条引用
        for citation in citations:
            citation_id = citation.citation_id

            # 查找对应的来源
            source = self._find_source(citation_id, contexts)

            if source:
                tracked = TrackedCitation(
                    citation_id=citation_id,
                    source_paper_id=source["paper_id"],
                    source_title=source.get("title", ""),
                    context=citation.context_before + citation.raw + citation.context_after,
                    position=citation.start_pos,
                    relevance_score=self._calculate_relevance(citation, question),
                    verified=True
                )
                self.tracked_citations.append(tracked)

                # 更新来源的引用计数
                if source["paper_id"] in self.sources:
                    self.sources[source["paper_id"]].cited_in_answer = True
                    self.sources[source["paper_id"]].citation_count += 1

                # 更新引用图谱
                self.citation_graph[source["paper_id"]].add(source["paper_id"])

        return self.get_report()

    def _find_source(
        self,
        citation_id: str,
        contexts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """查找引用ID对应的来源"""
        # 尝试多种匹配方式
        for ctx in contexts:
            paper_id = str(ctx.get("paper_id", ctx.get("id", "")))

            # 精确匹配
            if paper_id == citation_id:
                return ctx

            # 编号匹配（如果citation_id是数字）
            if citation_id.isdigit():
                idx = int(citation_id) - 1
                if 0 <= idx < len(contexts):
                    return contexts[idx]

            # 标题关键词匹配
            title = ctx.get("title", "").lower()
            if citation_id.lower() in title:
                return ctx

        return None if not contexts else contexts[0] if len(contexts) > 0 else None

    def _calculate_relevance(self, citation, question: str) -> float:
        """计算引用与问题的相关性（简化版）"""
        if not question:
            return 0.5

        # 检查上下文中是否包含问题关键词
        context_lower = (citation.context_before + citation.context_after).lower()
        question_keywords = set(question.lower().split())

        matches = sum(1 for kw in question_keywords if kw in context_lower)

        return min(1.0, matches / max(1, len(question_keywords)))

    def verify_citation(self, citation_id: str) -> bool:
        """验证特定引用是否可信"""
        for tracked in self.tracked_citations:
            if tracked.citation_id == citation_id:
                return tracked.verified
        return False

    def get_cited_sources(self) -> List[CitationSource]:
        """获取所有被引用的来源"""
        return [s for s in self.sources.values() if s.cited_in_answer]

    def get_uncited_sources(self) -> List[CitationSource]:
        """获取未被引用的来源"""
        return [s for s in self.sources.values() if not s.cited_in_answer]

    def get_citation_graph(self) -> Dict[str, List[str]]:
        """获取引用图谱"""
        return {k: list(v) for k, v in self.citation_graph.items()}

    def get_report(self) -> Dict[str, Any]:
        """获取追踪报告"""
        verified = sum(1 for t in self.tracked_citations if t.verified)
        unverified = len(self.tracked_citations) - verified

        return {
            "total_citations": len(self.tracked_citations),
            "verified_citations": verified,
            "unverified_citations": unverified,
            "sources": [
                {
                    "paper_id": s.paper_id,
                    "title": s.title,
                    "authors": s.authors,
                    "year": s.year,
                    "cited": s.cited_in_answer,
                    "citation_count": s.citation_count
                }
                for s in self.sources.values()
            ],
            "citation_map": self.get_citation_graph(),
            "tracking_details": [
                {
                    "citation_id": t.citation_id,
                    "source_paper_id": t.source_paper_id,
                    "source_title": t.source_title,
                    "relevance_score": t.relevance_score,
                    "verified": t.verified
                }
                for t in self.tracked_citations
            ]
        }

    def reset(self):
        """重置追踪器"""
        self.tracked_citations = []
        self.sources = {}
        self.citation_graph = defaultdict(set)


# 便捷函数
def track_citations(answer: str, contexts: List[Dict[str, Any]], question: str = "") -> Dict[str, Any]:
    """
    便捷函数：追踪答案中的引用

    Args:
        answer: 生成的答案
        contexts: 检索到的上下文
        question: 原始问题

    Returns:
        追踪报告
    """
    tracker = CitationTracker()
    return tracker.track(answer, contexts, question)