"""
报告分析节点 - Report Analyze Node

功能：
1. 统计论文数据（方法分布、趋势分析）
2. 提取关键信息（热门主题、重要作者）
3. 生成报告元数据

设计原则：
- 基于规则的统计分析
- 支持多维度数据提取
- 为报告生成提供结构化数据
"""
from typing import Dict, Any, List
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class ReportAnalyzeNode:
    """报告分析节点 - 分析论文数据生成报告统计"""

    def __init__(self):
        """初始化报告分析节点"""
        pass

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告数据分析

        Args:
            state: 当前状态，需包含 papers

        Returns:
            更新后的状态，添加 report_stats 字段
        """
        papers = state.get("papers", [])

        if not papers:
            logger.warning("No papers to analyze for report")
            state["report_stats"] = self._empty_stats()
            return state

        try:
            # 统计分析
            stats = {
                "total_papers": len(papers),
                "venues": self._analyze_venues(papers),
                "authors": self._analyze_authors(papers),
                "years": self._analyze_years(papers),
                "citations": self._analyze_citations(papers),
                "keywords": self._extract_keywords(papers),
                "top_papers": self._get_top_papers(papers, top_k=10)
            }

            state["report_stats"] = stats

            logger.info(
                f"Report analysis completed: {stats['total_papers']} papers, "
                f"{len(stats['venues'])} venues, {len(stats['authors'])} authors"
            )

        except Exception as e:
            logger.error(f"Report analysis failed: {e}")
            state["report_stats"] = self._empty_stats()
            state.setdefault("errors", []).append(f"Report analysis error: {str(e)}")

        return state

    def _analyze_venues(self, papers: List[Dict]) -> Dict[str, int]:
        """分析发表场所分布"""
        venues = [p.get("venue", "Unknown") for p in papers if p.get("venue")]
        return dict(Counter(venues).most_common(10))

    def _analyze_authors(self, papers: List[Dict]) -> Dict[str, int]:
        """分析作者分布"""
        all_authors = []
        for paper in papers:
            authors = paper.get("authors", [])
            if isinstance(authors, list):
                all_authors.extend(authors)
        return dict(Counter(all_authors).most_common(20))

    def _analyze_years(self, papers: List[Dict]) -> Dict[int, int]:
        """分析年份分布"""
        years = [p.get("year", 0) for p in papers if p.get("year")]
        return dict(Counter(years).most_common())

    def _analyze_citations(self, papers: List[Dict]) -> Dict[str, Any]:
        """分析引用统计"""
        citations = [p.get("citations", 0) for p in papers]
        if not citations:
            return {"total": 0, "avg": 0, "max": 0, "min": 0}

        return {
            "total": sum(citations),
            "avg": sum(citations) / len(citations),
            "max": max(citations),
            "min": min(citations)
        }

    def _extract_keywords(self, papers: List[Dict]) -> List[str]:
        """提取关键词（从标题和摘要）"""
        # 简单实现：提取高频词
        text = " ".join([
            p.get("title", "") + " " + p.get("abstract", "")
            for p in papers
        ]).lower()

        # 移除常见停用词
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        words = [w for w in text.split() if len(w) > 3 and w not in stopwords]

        return [word for word, _ in Counter(words).most_common(20)]

    def _get_top_papers(self, papers: List[Dict], top_k: int = 10) -> List[Dict]:
        """获取 Top K 论文（按引用数排序）"""
        sorted_papers = sorted(
            papers,
            key=lambda p: p.get("citations", 0),
            reverse=True
        )
        return sorted_papers[:top_k]

    def _empty_stats(self) -> Dict[str, Any]:
        """返回空统计数据"""
        return {
            "total_papers": 0,
            "venues": {},
            "authors": {},
            "years": {},
            "citations": {"total": 0, "avg": 0, "max": 0, "min": 0},
            "keywords": [],
            "top_papers": []
        }
