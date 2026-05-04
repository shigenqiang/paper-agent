"""
周报生成器 - Weekly Report Generator

功能：
1. 生成每周研究进展报告
2. 汇总多日的研究发现
3. 周度趋势分析
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseReportGenerator, ReportConfig, ReportSection, ReportType

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class WeeklyReportGenerator(BaseReportGenerator):
    """
    周报生成器

    生成结构：
    1. 本周概览
    2. 主要进展
    3. 论文分析
    4. 趋势洞察
    5. 下周计划
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        if config is None:
            config = ReportConfig(report_type=ReportType.WEEKLY)
        super().__init__(config)

        self.system_prompt = """你是一个专业的周报生成助手。根据本周的研究信息，生成结构化的周报。
格式要求：
1. 本周概览（100字内）
2. 主要进展（按日期或主题组织）
3. 论文分析摘要
4. 趋势洞察
5. 下周计划

语言：中文
风格：专业、详细
"""

    async def generate(
        self,
        topic: str = "",
        daily_reports: Optional[List[Dict[str, Any]]] = None,
        papers: Optional[List[Dict[str, Any]]] = None,
        dates: Optional[tuple] = None,
        **kwargs
    ) -> Report:
        """
        生成周报

        Args:
            topic: 研究主题
            daily_reports: 每日的报告列表
            papers: 本周收集的论文列表
            dates: 日期范围 (start_date, end_date)

        Returns:
            Report 对象
        """
        # 计算日期范围
        if dates:
            start_date, end_date = dates
        else:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info(f"Generating weekly report for {start_date} to {end_date}")

        # 构建prompt
        prompt = self._build_prompt(topic, daily_reports, papers, start_date, end_date)

        # 调用LLM生成
        raw_content = await self._call_llm(prompt)

        # 创建报告
        report = Report(
            title=f"周报 - {topic} - {start_date} to {end_date}",
            config=self.config,
            raw_content=raw_content
        )

        # 添加默认章节
        report.add_section(self._create_section("本周概览", level=1))
        report.add_section(self._create_section("主要进展", level=1))
        report.add_section(self._create_section("论文分析", level=1))
        report.add_section(self._create_section("趋势洞察", level=1))
        report.add_section(self._create_section("下周计划", level=1))

        # 解析内容填充章节
        sections = self.parse_raw_to_sections(raw_content)
        if sections:
            report.sections = sections[:self.config.max_sections]

        # 设置元数据
        report.metadata = {
            "start_date": start_date,
            "end_date": end_date,
            "topic": topic,
            "daily_count": len(daily_reports) if daily_reports else 0,
            "papers_count": len(papers) if papers else 0,
        }

        # 添加参考文献
        if self.config.include_references and papers:
            report.references = self._format_references(papers)

        return report

    def _build_prompt(
        self,
        topic: str,
        daily_reports: Optional[List[Dict]],
        papers: Optional[List[Dict]],
        start_date: str,
        end_date: str
    ) -> str:
        """构建生成prompt"""
        prompt = f"""生成本周（{start_date} 到 {end_date}）的研究周报。

主题：{topic}

"""

        if daily_reports:
            prompt += f"\n每日报告摘要（{len(daily_reports)}天）：\n"
            for i, daily in enumerate(daily_reports):
                date = daily.get("date", f"Day {i+1}")
                summary = daily.get("summary", "No summary")
                prompt += f"- {date}: {summary[:200]}\n"

        if papers:
            prompt += f"\n本周论文（{len(papers)}篇）：\n"
            for i, paper in enumerate(papers[:15]):  # 最多15篇
                prompt += f"{i+1}. {paper.get('title', 'N/A')}"
                if paper.get('authors'):
                    authors = paper['authors'][:3] if isinstance(paper['authors'], list) else str(paper['authors'])
                    prompt += f" - {authors}"
                if paper.get('year'):
                    prompt += f" ({paper['year']})"
                prompt += "\n"

        prompt += f"""
请按以下格式生成周报：

## 本周概览
（100字内概括本周整体进展）

## 主要进展
（按日期或主题组织本周的重要发现）

## 论文分析
（对重要论文的分析和评价）

## 趋势洞察
（基于本周发现的趋势和洞察）

## 下周计划
（计划和研究方向）
"""

        return prompt

    def _format_references(self, papers: List[Dict]) -> List[Dict[str, Any]]:
        """格式化参考文献"""
        from ..citation import CitationFormatter

        formatter = CitationFormatter()
        references = []

        for i, paper in enumerate(papers[:self.config.max_references]):
            formatted = formatter.format(paper, self.config.citation_style, f"ref_{i+1}")
            references.append(formatted.to_dict())

        return references


async def generate_weekly_report(
    topic: str,
    daily_reports: Optional[List[Dict[str, Any]]] = None,
    papers: Optional[List[Dict[str, Any]]] = None,
    dates: Optional[tuple] = None,
    **kwargs
) -> Report:
    """
    便捷函数：生成周报

    Args:
        topic: 研究主题
        daily_reports: 每日报告列表
        papers: 论文列表
        dates: 日期范围

    Returns:
        Report 对象
    """
    generator = WeeklyReportGenerator()
    return await generator.generate(topic, daily_reports, papers, dates, **kwargs)