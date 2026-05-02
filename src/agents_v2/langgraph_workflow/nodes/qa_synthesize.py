"""
问答综合节点 - QA Synthesize Node

功能：
1. 综合分析搜索到的论文
2. LLM驱动的多源信息融合、证据链构建、矛盾检测
3. 支持比较分析、趋势分析、综合回答

设计原则：
- 规则引擎 + LLM 双层综合
- 支持多种问答模式
- 为回答生成提供结构化数据
"""
from typing import Dict, Any, List, Optional, Callable
from src.agents_v2.logging_config import get_logging_logger

import json
import re

from collections import Counter

logger = get_logging_logger(__name__)


class QASynthesizeNode:
    """
    问答综合节点

    两层综合:
    1. 规则引擎: 统计分组、关键词提取（快速）
    2. LLM综合: 答案生成、证据链构建、矛盾检测（深度）
    """

    def __init__(self, llm_caller: Optional[Callable] = None):
        """
        Args:
            llm_caller: LLM调用函数，签名 async (prompt: str) -> str
        """
        self._llm_caller = llm_caller

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行问答数据综合

        Args:
            state: 当前状态，需包含 papers 和 user_query

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
            # 第一层：规则引擎
            rule_synthesis = self._rule_based_synthesis(papers, user_query)

            # 第二层：LLM深度综合
            if self._llm_caller:
                llm_synthesis = await self._llm_synthesize(papers, user_query, rule_synthesis)
                rule_synthesis.update(llm_synthesis)
                rule_synthesis["synthesis_mode"] = "LLM"
            else:
                rule_synthesis["synthesis_mode"] = "rule"

            state["qa_synthesis"] = rule_synthesis

            logger.info(f"QA synthesis completed, mode={rule_synthesis['synthesis_mode']}")

        except Exception as e:
            logger.error(f"QA synthesis failed: {e}")
            state["qa_synthesis"] = {"summary": "分析失败", "error": str(e)}
            state.setdefault("errors", []).append(f"QA synthesis error: {str(e)}")

        return state

    def _rule_based_synthesis(self, papers: List[Dict], query: str) -> Dict[str, Any]:
        """规则引擎综合"""
        if "比较" in query or "对比" in query:
            return self._compare_analysis(papers, query)
        elif "趋势" in query or "发展" in query:
            return self._trend_analysis(papers)
        else:
            return self._basic_synthesis(papers)

    async def _llm_synthesize(
        self,
        papers: List[Dict],
        query: str,
        rule_synthesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """LLM驱动的深度综合"""
        # 构建论文摘要
        paper_summaries = []
        for i, p in enumerate(papers[:15]):
            abstract = p.get("abstract", "")[:150]
            authors = p.get("authors", [])
            if isinstance(authors, list):
                authors_str = ", ".join(authors[:3])
            else:
                authors_str = str(authors)
            paper_summaries.append(
                f"{i+1}. [{p.get('year', '?')}] {p.get('title', 'N/A')}\n"
                f"   作者: {authors_str}\n"
                f"   摘要: {abstract}"
            )

        papers_text = "\n".join(paper_summaries)

        prompt = f"""基于以下论文集合，回答用户问题。

用户问题: {query}

论文（共{len(papers)}篇，显示前15篇）:
{papers_text}

请进行深度分析，输出JSON格式：

1. answer: 直接回答用户问题（200-400字）
2. evidence_chain: 支撑答案的证据链（每条证据引用具体论文编号）
3. key_insights: 关键洞察（3-5个）
4. contradictions: 论文间的矛盾或分歧（如有）
5. confidence: 答案置信度（0-1）
6. limitations: 答案的局限性

JSON格式：
{{
    "answer": "综合回答...",
    "evidence_chain": [
        {{"claim": "论点", "evidence": "来自论文X的证据", "source_index": 1}},
    ],
    "key_insights": ["洞察1", "洞察2"],
    "contradictions": ["矛盾1"],
    "confidence": 0.85,
    "limitations": ["局限1"]
}}"""

        try:
            response = await self._llm_caller(prompt)
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed in _llm_synthesize: {e}, raw_input={response[:500] if isinstance(response, str) else str(response)[:500]}")
            match = re.search(r'\{[\s\S]*\}', response if isinstance(response, str) else "")
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError as e2:
                    logger.warning(f"Regex extraction also failed in _llm_synthesize: {e2}, raw_input={match.group()[:500]}")
                    pass
            return {"answer": str(response)[:500], "parse_error": True}
        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}")
            return {}

    def _basic_synthesis(self, papers: List[Dict]) -> Dict[str, Any]:
        """基础综合分析"""
        return {
            "total_papers": len(papers),
            "top_papers": papers[:5],
            "key_authors": self._extract_top_authors(papers, top_k=5),
            "key_venues": self._extract_top_venues(papers, top_k=5),
            "summary": f"找到 {len(papers)} 篇相关论文",
        }

    def _compare_analysis(self, papers: List[Dict], query: str) -> Dict[str, Any]:
        """比较分析"""
        keywords = self._extract_compare_keywords(query)

        groups = {}
        for keyword in keywords:
            groups[keyword] = [
                p for p in papers
                if keyword.lower() in p.get("title", "").lower() or
                   keyword.lower() in p.get("abstract", "").lower()
            ]

        return {
            "comparison_groups": {k: len(v) for k, v in groups.items()},
            "comparison_details": groups,
            "keywords": keywords,
            "summary": f"比较分析: {', '.join(keywords)}",
        }

    def _trend_analysis(self, papers: List[Dict]) -> Dict[str, Any]:
        """趋势分析"""
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
            "summary": f"趋势分析: {len(year_groups)} 个年份",
        }

    def _extract_top_authors(self, papers: List[Dict], top_k: int = 5) -> List[str]:
        """提取高频作者"""
        all_authors = []
        for paper in papers:
            authors = paper.get("authors", [])
            if isinstance(authors, list):
                all_authors.extend(authors)
        return [author for author, _ in Counter(all_authors).most_common(top_k)]

    def _extract_top_venues(self, papers: List[Dict], top_k: int = 5) -> List[str]:
        """提取高频发表场所"""
        venues = [p.get("venue", "") for p in papers if p.get("venue")]
        return [venue for venue, _ in Counter(venues).most_common(top_k)]

    def _extract_compare_keywords(self, query: str) -> List[str]:
        """从查询中提取比较关键词"""
        keywords = re.split(r'[和与vs]|对比|比较', query)
        return [k.strip() for k in keywords if k.strip() and len(k.strip()) > 1]
