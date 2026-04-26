"""每月论文报告Agent - 汇总一月内特定主题的论文"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

from .base_qa_agent import BaseQAAgent
from .paper_search import PaperSearchAgent

logger = logging.getLogger(__name__)


@dataclass
class MonthlyPaperReport:
    """每月论文报告"""
    month: str  # YYYY-MM
    topic: str
    keywords: List[str]
    papers_found: int
    summary: str
    method_distribution: Dict[str, int] = field(default_factory=dict)
    weekly_breakdown: Dict[str, int] = field(default_factory=dict)
    top_papers: List[Dict[str, Any]] = field(default_factory=list)
    influential_authors: List[str] = field(default_factory=list)
    key_themes: List[str] = field(default_factory=list)
    research_gaps: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


class MonthlyReportGenerator(BaseQAAgent):
    """
    月报生成Agent

    功能：
    1. 收集一月内的论文数据
    2. 按周分类统计
    3. 识别关键主题和研究空白
    4. 识別高影响力作者
    5. 生成月度分析报告

    使用方式：
    monthly = MonthlyReportGenerator()
    report = await monthly.execute(keywords=["statistical learning", "causal inference"])
    """

    def __init__(self):
        super().__init__(
            name="MonthlyReportGenerator",
            description="每月论文报告生成"
        )
        self.search_agent = PaperSearchAgent()
        self.system_prompt = """你是一个专业的学术月报分析助手，擅长：
1. 汇总多周的论文数据进行综合分析
2. 按研究方法分布统计
3. 识别关键主题和研究空白
4. 发现高影响力作者和研究团队
5. 生成深度月度分析报告

请保持客观、专业的分析风格。"""

    async def execute(
        self,
        keywords: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行月报生成

        Args:
            keywords: 搜索关键词列表
            context: 配置（month, year, max_papers等）

        Returns:
            月报字典
        """
        keywords = keywords or ["statistical learning", "causal inference", "machine learning"]
        context = context or {}

        # 确定月份
        now = datetime.now()
        year = context.get("year", now.year)
        month = context.get("month", now.month)

        # 计算月份日期范围
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(days=1)

        days = (month_end - month_start).days + 1
        max_papers_per_keyword = context.get("max_papers", 50)

        self.logger.info(f"生成月报，月份: {year}-{month:02d}")

        try:
            # 每周收集论文
            weekly_papers: Dict[str, List[Dict]] = {}
            all_papers = []

            # 分周收集
            for week in range(4):
                week_start = month_start + timedelta(days=week * 7)
                week_end = min(week_start + timedelta(days=6), month_end)

                if week_start > month_end:
                    break

                # 搜索本周论文
                week_key = week_start.strftime("%Y-%m-%d")
                tasks = []
                for kw in keywords:
                    task = self._search_for_range(
                        kw,
                        days=min(7, (month_end - week_start).days + 1),
                        max_results=max_papers_per_keyword // len(keywords)
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                week_papers = []
                for result in results:
                    if isinstance(result, list):
                        week_papers.extend(result)

                if week_papers:
                    weekly_papers[week_key] = week_papers
                    all_papers.extend(week_papers)

            # 去重
            all_papers = self._deduplicate_papers(all_papers)

            # 生成报告
            report = await self._generate_monthly_report(
                papers=all_papers,
                keywords=keywords,
                year=year,
                month=month,
                monthly_range=f"{month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')}",
                weekly_papers=weekly_papers
            )

            self.logger.info(f"月报生成完成，共 {len(all_papers)} 篇论文")

            return {
                "success": True,
                "report": report,
                "papers_found": len(all_papers),
                "month": f"{year}-{month:02d}",
                "keywords": keywords,
                "weeks_with_papers": len([v for v in weekly_papers.values() if v])
            }

        except Exception as e:
            self.logger.error(f"月报生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "report": None
            }

    async def _search_for_range(
        self,
        keyword: str,
        days: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """为特定日期范围搜索论文"""
        try:
            result = await self.search_agent.execute(
                keyword,
                {"source": "all", "time_range": days, "max_results": max_results}
            )
            return result.get("papers", [])
        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []

    def _deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """去重"""
        seen_titles = set()
        unique = []

        for paper in papers:
            title_lower = paper.get("title", "").lower()
            if title_lower and title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique.append(paper)

        return unique

    async def _generate_monthly_report(
        self,
        papers: List[Dict],
        keywords: List[str],
        year: int,
        month: int,
        monthly_range: str,
        weekly_papers: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """生成月报内容"""
        if not papers:
            return {
                "month": f"{year}-{month:02d}",
                "topic": ", ".join(keywords),
                "papers_found": 0,
                "summary": "本月未找到相关论文",
                "method_distribution": {},
                "weekly_breakdown": {},
                "top_papers": [],
                "influential_authors": [],
                "key_themes": [],
                "research_gaps": [],
                "references": []
            }

        # 统计每周分布
        weekly_breakdown: Dict[str, int] = {}
        for week, week_papers in weekly_papers.items():
            weekly_breakdown[week] = len(week_papers)

        # 分析方法分布
        method_counts: Dict[str, int] = {}
        for p in papers:
            methods = p.get("methodology", "")
            if methods and methods != "未明确说明":
                for m in methods.split(", "):
                    m = m.strip()
                    if m:
                        method_counts[m] = method_counts.get(m, 0) + 1

        method_distribution = dict(sorted(
            method_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:15])

        # 统计作者出现频率
        author_counts: Dict[str, int] = {}
        for p in papers:
            for author in p.get("authors", []):
                author_counts[author] = author_counts.get(author, 0) + 1

        influential_authors = [
            author for author, count in sorted(
                author_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]

        # 构建论文信息摘要
        papers_info = []
        for p in papers[:100]:  # 最多处理100篇
            papers_info.append({
                "title": p.get("title", ""),
                "authors": p.get("authors", [])[:3],
                "year": p.get("year", ""),
                "source": p.get("source", ""),
                "methodology": p.get("methodology", ""),
                "abstract": p.get("abstract", "")[:200]
            })

        prompt = f"""请分析以下本月论文列表，生成深度月度分析报告。

## 月份
{year}年{month}月

## 搜索关键词
{', '.join(keywords)}

## 论文统计
- 总数: {len(papers)}篇
- 每周分布: {json.dumps(weekly_breakdown, ensure_ascii=False)}

## 方法分布（Top 15）
{json.dumps(method_distribution, ensure_ascii=False, indent=2)}

## 高影响力作者（按论文数量排序）
{influential_authors}

## 论文列表（前{len(papers_info)}篇）
{json.dumps(papers_info, ensure_ascii=False, indent=2)}

## 报告要求
请生成JSON格式的月度深度报告：

{{
    "month": "月份 (YYYY-MM)",
    "topic": "主题概括",
    "papers_found": 论文总数,
    "summary": "本月总体摘要 (500字以内)",
    "method_distribution": {{"方法名": 数量}},
    "weekly_breakdown": {{"周起始日": 论文数}},
    "top_papers": [
        {{
            "title": "论文标题",
            "authors": ["作者列表"],
            "source": "来源",
            "key_contribution": "主要贡献",
            "citations": 引用数
        }}
    ],
    "influential_authors": ["作者1", "作者2", ...],
    "key_themes": ["主题1", "主题2", "主题3"],
    "research_gaps": ["研究空白1", "研究空白2", "研究空白3"],
    "references": ["引用格式1", "引用格式2"]
}}
"""
        response = await self._llm_call(prompt, self.system_prompt)

        try:
            report = json.loads(response)
            report["papers_found"] = len(papers)
            report["method_distribution"] = method_distribution
            report["weekly_breakdown"] = weekly_breakdown
            return report
        except json.JSONDecodeError:
            return {
                "month": f"{year}-{month:02d}",
                "topic": ", ".join(keywords),
                "papers_found": len(papers),
                "summary": response[:500] if response else "月报生成失败",
                "method_distribution": method_distribution,
                "weekly_breakdown": weekly_breakdown,
                "top_papers": [
                    {"title": p.get("title", ""), "key_contribution": ""}
                    for p in papers[:10]
                ],
                "influential_authors": influential_authors,
                "key_themes": [],
                "research_gaps": [],
                "references": []
            }

    def run_sync(
        self,
        keywords: Optional[List[str]] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """同步运行月报生成"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        context = {}
        if year:
            context["year"] = year
        if month:
            context["month"] = month

        return loop.run_until_complete(self.execute(keywords, context))
