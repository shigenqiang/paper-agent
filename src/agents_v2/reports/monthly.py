"""
月报生成器 - Monthly Report Generator

功能：
1. 生成每月研究进展报告
2. 汇总整月的研究发现
3. 月度趋势和深度分析
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseReportGenerator, ReportConfig, ReportSection, ReportType

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class MonthlyReportGenerator(BaseReportGenerator):
    """
    月报生成器

    生成结构：
    1. 月度概览
    2. 主要成就
    3. 深度分析
    4. 趋势与展望
    5. 下月计划
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        if config is None:
            config = ReportConfig(report_type=ReportType.MONTHLY)
        super().__init__(config)

        self.system_prompt = """你是一个专业的月报生成助手。根据本月的研究信息，生成结构化的月报。
格式要求：
1. 月度概览（150字内）
2. 主要成就（按主题或项目组织）
3. 深度分析（对重要进展的深入分析）
4. 趋势与展望（基于本月发现的长期趋势）
5. 下月计划

语言：中文
风格：专业、深度、战略性
"""

    async def generate(
        self,
        topic: str = "",
        weekly_reports: Optional[List[Dict[str, Any]]] = None,
        papers: Optional[List[Dict[str, Any]]] = None,
        month: Optional[str] = None,
        **kwargs
    ) -> Report:
        """
        生成月报

        Args:
            topic: 研究主题
            weekly_reports: 每周报告列表
            papers: 本月收集的论文列表
            month: 月份（默认当前月份，格式YYYY-MM）

        Returns:
            Report 对象
        """
        # 计算月份范围
        if month:
            year, month_num = month.split("-")
            start_date = f"{year}-{month_num}-01"
            # 计算月末
            next_month = int(month_num) + 1
            next_year = int(year)
            if next_month > 12:
                next_month = 1
                next_year += 1
            end_date = f"{next_year:04d}-{next_month:02d}-01"
        else:
            now = datetime.now()
            start_date = f"{now.year}-{now.month:02d}-01"
            next_month = now.month + 1
            next_year = now.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            end_date = f"{next_year:04d}-{next_month:02d}-01"

        logger.info(f"Generating monthly report for {start_date}")

        # 构建prompt
        prompt = self._build_prompt(topic, weekly_reports, papers, start_date, end_date)

        # 调用LLM生成
        raw_content = await self._call_llm(prompt)

        # 创建报告
        report = Report(
            title=f"月报 - {topic} - {start_date[:7]}",
            config=self.config,
            raw_content=raw_content
        )

        # 添加默认章节
        report.add_section(self._create_section("月度概览", level=1))
        report.add_section(self._create_section("主要成就", level=1))
        report.add_section(self._create_section("深度分析", level=1))
        report.add_section(self._create_section("趋势与展望", level=1))
        report.add_section(self._create_section("下月计划", level=1))

        # 解析内容填充章节
        sections = self.parse_raw_to_sections(raw_content)
        if sections:
            report.sections = sections[:self.config.max_sections]

        # 设置元数据
        report.metadata = {
            "month": start_date[:7],
            "start_date": start_date,
            "end_date": end_date,
            "topic": topic,
            "weekly_count": len(weekly_reports) if weekly_reports else 0,
            "papers_count": len(papers) if papers else 0,
        }

        # 添加参考文献
        if self.config.include_references and papers:
            report.references = self._format_references(papers)

        return report

    def _build_prompt(
        self,
        topic: str,
        weekly_reports: Optional[List[Dict]],
        papers: Optional[List[Dict]],
        start_date: str,
        end_date: str
    ) -> str:
        """构建生成prompt"""
        # 提取年月
        year_month = start_date[:7]

        prompt = f"""生成{year_month}月的研究月报。

主题：{topic}

"""

        if weekly_reports:
            prompt += f"\n周报摘要（{len(weekly_reports)}周）：\n"
            for i, weekly in enumerate(weekly_reports):
                week_label = weekly.get("week", f"Week {i+1}")
                summary = weekly.get("summary", "No summary")
                prompt += f"- {week_label}: {summary[:300]}\n"

        if papers:
            prompt += f"\n本月论文（{len(papers)}篇）：\n"
            for i, paper in enumerate(papers[:20]):  # 最多20篇
                prompt += f"{i+1}. {paper.get('title', 'N/A')}"
                if paper.get('authors'):
                    authors = paper['authors'][:3] if isinstance(paper['authors'], list) else str(paper['authors'])
                    prompt += f" - {authors}"
                if paper.get('year'):
                    prompt += f" ({paper['year']})"
                if paper.get('key_contribution'):
                    prompt += f"\n   贡献: {paper['key_contribution'][:100]}"
                prompt += "\n"

        prompt += f"""
请按以下格式生成月报：

## 月度概览
（150字内概括本月整体进展）

## 主要成就
（按主题或项目组织本月的重要成就）

## 深度分析
（对重要进展的深入分析，包含方法、结果、意义）

## 趋势与展望
（基于本月发现的长期趋势和对未来的展望）

## 下月计划
（详细的研究计划和发展方向）
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


async def generate_monthly_report(
    topic: str,
    weekly_reports: Optional[List[Dict[str, Any]]] = None,
    papers: Optional[List[Dict[str, Any]]] = None,
    month: Optional[str] = None,
    **kwargs
) -> Report:
    """
    便捷函数：生成月报

    Args:
        topic: 研究主题
        weekly_reports: 每周报告列表
        papers: 论文列表
        month: 月份（YYYY-MM格式）

    Returns:
        Report 对象
    """
    generator = MonthlyReportGenerator()
    return await generator.generate(topic, weekly_reports, papers, month, **kwargs)