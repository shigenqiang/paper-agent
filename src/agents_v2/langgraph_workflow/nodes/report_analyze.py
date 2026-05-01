"""
报告分析节点 - Report Analyze Node

功能：
1. 统计论文数据（方法分布、趋势分析）
2. LLM驱动的深度分析（趋势洞察、研究空白、综合评述）
3. 生成报告元数据

设计原则：
- 规则引擎 + LLM 双层分析
- 支持多维度数据提取
- 为报告生成提供结构化数据
"""
from typing import Dict, Any, List, Optional, Callable
from collections import Counter
import json
import logging

logger = logging.getLogger(__name__)


class ReportAnalyzeNode:
    """
    报告分析节点

    两层分析:
    1. 规则引擎: 统计论文数据（快速、确定性）
    2. LLM分析: 趋势洞察、研究空白识别、综合评述（深度、智能）
    """

    def __init__(self, llm_caller: Optional[Callable] = None):
        """
        Args:
            llm_caller: LLM调用函数，签名 async (prompt: str) -> str
        """
        self._llm_caller = llm_caller

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告数据分析

        Args:
            state: 当前状态，需包含 papers

        Returns:
            更新后的状态，添加 report_stats 字段
        """
        papers = state.get("papers", [])
        query = state.get("query", state.get("topic", ""))

        if not papers:
            logger.warning("No papers to analyze for report")
            state["report_stats"] = self._empty_stats()
            return state

        try:
            # 第一层：规则引擎统计分析
            stats = {
                "total_papers": len(papers),
                "venues": self._analyze_venues(papers),
                "authors": self._analyze_authors(papers),
                "years": self._analyze_years(papers),
                "citations": self._analyze_citations(papers),
                "keywords": self._extract_keywords(papers),
                "top_papers": self._get_top_papers(papers, top_k=10)
            }

            # 第二层：LLM深度分析
            if self._llm_caller:
                llm_insights = await self._llm_deep_analysis(papers, query, stats)
                stats["insights"] = llm_insights
            else:
                stats["insights"] = self._rule_based_insights(stats)

            state["report_stats"] = stats

            logger.info(
                f"Report analysis completed: {stats['total_papers']} papers, "
                f"{len(stats['venues'])} venues, insights={'LLM' if self._llm_caller else 'rule'}"
            )

        except Exception as e:
            logger.error(f"Report analysis failed: {e}")
            state["report_stats"] = self._empty_stats()
            state.setdefault("errors", []).append(f"Report analysis error: {str(e)}")

        return state

    async def _llm_deep_analysis(
        self,
        papers: List[Dict],
        query: str,
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """LLM驱动的深度分析"""
        # 构建论文摘要
        paper_summaries = []
        for i, p in enumerate(papers[:20]):
            summary = f"{i+1}. {p.get('title', 'N/A')} ({p.get('year', '?')})"
            if p.get('authors'):
                authors = p['authors'] if isinstance(p['authors'], list) else [p['authors']]
                summary += f" - {', '.join(authors[:3])}"
            if p.get('abstract'):
                summary += f"\n   摘要: {p['abstract'][:200]}"
            paper_summaries.append(summary)

        papers_text = "\n".join(paper_summaries)
        years_str = json.dumps(stats.get("years", {}), ensure_ascii=False)

        prompt = f"""基于以下论文集合，进行深度研究分析。

研究主题: {query}

论文列表（共{len(papers)}篇，显示前20篇）:
{papers_text}

年份分布: {years_str}

请从以下维度进行分析，输出JSON格式：

1. research_trends: 研究趋势（3-5个关键趋势）
2. research_gaps: 研究空白（2-4个尚未充分研究的方向）
3. key_findings: 关键发现（该领域最重要的3-5个发现或共识）
4. methodology_overview: 方法论概述（主流研究方法及其优劣）
5. future_directions: 未来方向（2-3个值得深入的研究方向）
6. narrative: 综合叙述（200-300字的研究领域综述）

JSON格式：
{{
    "research_trends": ["趋势1", "趋势2"],
    "research_gaps": ["空白1", "空白2"],
    "key_findings": ["发现1", "发现2"],
    "methodology_overview": {{"主流方法": "描述", "新兴方法": "描述"}},
    "future_directions": ["方向1", "方向2"],
    "narrative": "综合叙述..."
}}"""

        try:
            response = await self._llm_caller(prompt)
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取JSON
            import re
            match = re.search(r'\{[\s\S]*\}', response if isinstance(response, str) else "")
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {"narrative": str(response)[:500], "parse_error": True}
        except Exception as e:
            logger.warning(f"LLM deep analysis failed: {e}")
            return self._rule_based_insights(stats)

    def _rule_based_insights(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """规则引擎生成基础洞察"""
        years = stats.get("years", {})
        citations = stats.get("citations", {})
        keywords = stats.get("keywords", [])

        # 趋势判断
        trends = []
        if years:
            sorted_years = sorted(years.items())
            if len(sorted_years) >= 2:
                recent = sum(v for k, v in sorted_years[-2:])
                older = sum(v for k, v in sorted_years[:-2])
                if recent > older:
                    trends.append("近年研究热度上升")
                else:
                    trends.append("研究热度趋于稳定")

        # 引用分析
        if citations.get("avg", 0) > 50:
            trends.append("该领域论文受到较高关注")

        return {
            "research_trends": trends,
            "research_gaps": [],
            "key_findings": [],
            "methodology_overview": {},
            "future_directions": [],
            "narrative": f"共收集{stats['total_papers']}篇相关论文，"
                        f"涉及{len(stats['venues'])}个发表场所，"
                        f"总引用数{citations.get('total', 0)}。"
                        f"高频关键词: {', '.join(keywords[:5])}。" if keywords else "",
        }

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
        text = " ".join([
            p.get("title", "") + " " + p.get("abstract", "")
            for p in papers
        ]).lower()

        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                     "of", "is", "are", "was", "were", "be", "been", "being", "have", "has",
                     "with", "that", "this", "from", "by", "not", "can", "will", "do"}
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
            "top_papers": [],
            "insights": {},
        }
