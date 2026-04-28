"""
问答综合节点 - QA Synthesize Node

功能：
1. 综合分析搜索到的论文
2. 支持比较分析、趋势分析
3. 提取关键信息用于回答生成

设计原则：
- 基于规则和统计的分析
- 支持多种问答模式
- 为回答生成提供结构化数据
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class QASynthesizeNode:
    """问答综合节点 - 综合分析论文数据"""

    def __init__(self):
        """初始化问答综合节点"""
        pass

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行问答数据综合

        Args:
            state: 当前状态，需包含 papers 和 question_type

        Returns:
            更新后的状态，添加 qa_synthesis 字段
        """
        papers = state.get("papers", [])
        question_type = state.get("question_type", "BASIC_QUERY")
        user_query = state.get("user_query", "")

        if not papers:
            logger.warning("No papers for QA synthesis")
            state["qa_synthesis"] = {"summary": "未找到相关论文"}
            return state

        try:
            # 根据问题类型进行不同的综合分析
            if "比较" in user_query or "对比" in user_query:
                synthesis = self._compare_analysis(papers, user_query)
            elif "趋势" in user_query or "发展" in user_query:
                synthesis = self._trend_analysis(papers)
            else:
                synthesis = self._basic_synthesis(papers)

            state["qa_synthesis"] = synthesis

            logger.info(f"QA synthesis completed for question type '{question_type}'")

        except Exception as e:
            logger.error(f"QA synthesis failed: {e}")
            state["qa_synthesis"] = {"summary": "分析失败"}
            state.setdefault("errors", []).append(f"QA synthesis error: {str(e)}")

        return state

    def _basic_synthesis(self, papers: List[Dict]) -> Dict[str, Any]:
        """基础综合分析"""
        return {
            "total_papers": len(papers),
            "top_papers": papers[:5],
            "key_authors": self._extract_top_authors(papers, top_k=5),
            "key_venues": self._extract_top_venues(papers, top_k=5),
            "summary": f"找到 {len(papers)} 篇相关论文"
        }

    def _compare_analysis(self, papers: List[Dict], query: str) -> Dict[str, Any]:
        """比较分析"""
        # 简单实现：按关键词分组
        keywords = self._extract_compare_keywords(query)

        groups = {}
        for keyword in keywords:
            groups[keyword] = [
                p for p in papers
                if keyword.lower() in p.get("title", "").lower() or
                   keyword.lower() in p.get("abstract", "").lower()
            ]

        return {
            "comparison_groups": groups,
            "keywords": keywords,
            "summary": f"比较分析: {', '.join(keywords)}"
        }

    def _trend_analysis(self, papers: List[Dict]) -> Dict[str, Any]:
        """趋势分析"""
        # 按年份分组
        year_groups = {}
        for paper in papers:
            year = paper.get("year", 0)
            if year:
                year_groups.setdefault(year, []).append(paper)

        return {
            "year_distribution": {
                year: len(papers_list)
                for year, papers_list in sorted(year_groups.items())
            },
            "recent_papers": papers[:10],
            "summary": f"趋势分析: {len(year_groups)} 个年份"
        }

    def _extract_top_authors(self, papers: List[Dict], top_k: int = 5) -> List[str]:
        """提取高频作者"""
        from collections import Counter
        all_authors = []
        for paper in papers:
            authors = paper.get("authors", [])
            if isinstance(authors, list):
                all_authors.extend(authors)
        return [author for author, _ in Counter(all_authors).most_common(top_k)]

    def _extract_top_venues(self, papers: List[Dict], top_k: int = 5) -> List[str]:
        """提取高频发表场所"""
        from collections import Counter
        venues = [p.get("venue", "") for p in papers if p.get("venue")]
        return [venue for venue, _ in Counter(venues).most_common(top_k)]

    def _extract_compare_keywords(self, query: str) -> List[str]:
        """从查询中提取比较关键词"""
        # 简单实现：提取"和"、"与"、"vs"分隔的词
        import re
        keywords = re.split(r'[和与vs]|对比|比较', query)
        return [k.strip() for k in keywords if k.strip() and len(k.strip()) > 1]
