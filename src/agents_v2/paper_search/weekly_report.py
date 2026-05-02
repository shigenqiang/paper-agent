"""每周论文报告Agent - 汇总一周内特定主题的论文"""
from src.agents_v2.logging_config import get_logging_logger

import asyncio

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

from .base_qa_agent import BaseQAAgent
from .paper_search import PaperSearchAgent
from .daily_watcher import DailyWatcher

logger = get_logging_logger(__name__)


@dataclass
class WeeklyPaperReport:
    """每周论文报告"""
    week_start: str
    week_end: str
    topic: str
    keywords: List[str]
    papers_found: int
    summary: str
    method_breakdown: Dict[str, int] = field(default_factory=dict)
    top_papers: List[Dict[str, Any]] = field(default_factory=list)
    emerging_trends: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


class WeeklyReportGenerator(BaseQAAgent):
    """
    周报生成Agent

    功能：
    1. 收集一周内的论文数据
    2. 按方法分类统计
    3. 识别新兴趋势
    4. 生成周度总结报告

    使用方式：
    weekly = WeeklyReportGenerator()
    report = await weekly.execute(keywords=["statistical learning", "causal inference"])
    """

    def __init__(self):
        super().__init__(
            name="WeeklyReportGenerator",
            description="每周论文报告生成"
        )
        self.search_agent = PaperSearchAgent()
        self.daily_watcher = DailyWatcher()
        self.system_prompt = """你是一个专业的学术周报分析助手，擅长：
1. 汇总多日的论文数据
2. 按研究方法分类统计
3. 识别一周内的研究趋势变化
4. 生成结构化周报

请保持客观、专业的分析风格。"""

    async def execute(
        self,
        keywords: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行周报生成

        Args:
            keywords: 搜索关键词列表
            context: 配置（week_start, week_end, max_papers等）

        Returns:
            周报字典
        """
        keywords = keywords or ["statistical learning", "causal inference", "machine learning"]
        context = context or {}

        # 计算周日期范围
        week_end = context.get("week_end", datetime.now())
        if isinstance(week_end, str):
            week_end = datetime.fromisoformat(week_end)

        week_start = context.get("week_start", week_end - timedelta(days=7))
        if isinstance(week_start, str):
            week_start = datetime.fromisoformat(week_start)

        days = (week_end - week_start).days
        max_papers_per_day = context.get("max_papers", 20)

        self.logger.info(f"生成周报，日期范围: {week_start.date()} 到 {week_end.date()}")

        try:
            # 收集每天的论文数据
            daily_reports = []
            all_papers = []

            # 每日关键词搜索（覆盖一周）
            for i in range(days):
                date = week_start + timedelta(days=i)
                day_end = date + timedelta(days=1)

                # 按天搜索
                tasks = []
                for kw in keywords:
                    task = self._search_for_date(
                        kw,
                        days=1,
                        max_results=max_papers_per_day // len(keywords)
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                day_papers = []
                for result in results:
                    if isinstance(result, list):
                        day_papers.extend(result)

                if day_papers:
                    all_papers.extend(day_papers)
                    daily_reports.append({
                        "date": date.isoformat(),
                        "papers": day_papers
                    })

            # 去重
            all_papers = self._deduplicate_papers(all_papers)

            # 生成报告
            report = await self._generate_weekly_report(
                papers=all_papers,
                keywords=keywords,
                week_start=week_start,
                week_end=week_end,
                daily_reports=daily_reports
            )

            self.logger.info(f"周报生成完成，共 {len(all_papers)} 篇论文")

            return {
                "success": True,
                "report": report,
                "papers_found": len(all_papers),
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "keywords": keywords,
                "daily_breakdown": len(daily_reports)
            }

        except Exception as e:
            self.logger.error(f"周报生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "report": None
            }

    async def _search_for_date(
        self,
        keyword: str,
        days: int,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """为特定日期搜索论文"""
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

    async def _generate_weekly_report(
        self,
        papers: List[Dict],
        keywords: List[str],
        week_start: datetime,
        week_end: datetime,
        daily_reports: List[Dict]
    ) -> Dict[str, Any]:
        """生成周报内容"""
        if not papers:
            return {
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "topic": ", ".join(keywords),
                "papers_found": 0,
                "summary": "本周未找到相关论文",
                "content": "# 每周学术资讯\n\n本周未找到相关论文",
                "method_breakdown": {},
                "top_papers": [],
                "emerging_trends": [],
                "references": []
            }

        # 构建论文信息摘要
        papers_info = []
        for p in papers[:30]:  # 最多处理30篇
            papers_info.append({
                "title": p.get("title", ""),
                "year": p.get("year", ""),
                "source": p.get("source", ""),
                "methodology": p.get("methodology", ""),
                "abstract": p.get("abstract", "")[:200]
            })

        # 分析方法分布
        method_counts: Dict[str, int] = {}
        for p in papers:
            methods = p.get("methodology", "")
            if methods and methods != "未明确说明":
                for m in methods.split(", "):
                    m = m.strip()
                    if m:
                        method_counts[m] = method_counts.get(m, 0) + 1

        # 按频率排序
        method_breakdown = dict(sorted(
            method_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])  # Top 10方法

        prompt = f"""请分析以下本周论文列表，生成周度总结报告。

## 周报时间范围
{week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}

## 搜索关键词
{', '.join(keywords)}

## 论文列表（共{len(papers)}篇）

## 报告要求

请生成Markdown格式的周报，包含以下部分：

1. **# 每周学术资讯** - 标题，包含周日期范围
2. **## 本周概览** - 论文总数、关键词
3. **## 主要研究进展** - 概述本周最重要的研究发现
4. **## 方法分类统计** - 按研究方法分类统计
5. **## 重点论文推荐** - 3-5篇重要论文及其亮点
6. **## 研究趋势分析** - 本周研究趋势

注意：
- 使用中文撰写
- Markdown格式规范
- 内容专业简洁
- 不包含参考文献链接（单独列出）
"""
        response = await self._llm_call(prompt, self.system_prompt)

        # 构建参考文献
        references = []
        for i, p in enumerate(papers[:10], 1):
            title = p.get('title', 'Unknown')
            url = p.get('url', '')
            source = p.get('source', '')
            if url:
                references.append(f"[{i}]: {url}")
            else:
                references.append(f"[{i}]: {source}")

        return {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "topic": ", ".join(keywords),
            "papers_found": len(papers),
            "summary": response,
            "content": f"{response}\n\n---\n\n## 参考文献\n\n" + "\n".join(references) if references else response,
            "method_breakdown": method_breakdown,
            "top_papers": [
                {"title": p.get("title", ""), "key_contribution": ""}
                for p in papers[:5]
            ],
            "emerging_trends": [],
            "references": references
        }

    def run_sync(
        self,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """同步运行周报生成"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.execute(keywords))
