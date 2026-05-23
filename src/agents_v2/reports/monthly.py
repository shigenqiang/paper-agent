"""
月报生成器 - Monthly Report Generator

功能：
1. 生成每月研究进展报告
2. 汇总整月的研究发现
3. 月度趋势和深度分析
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseReportGenerator, ReportConfig, ReportSection, ReportType, Report

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
            config = ReportConfig.from_env(overrides={"report_type": ReportType.MONTHLY})
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
        生成月报（文献综述风格）

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

        logger.info(f"Generating monthly report (literature review style) for {start_date}")

        # 过滤论文日期（论文必须早于月报结束日期）
        end_year = int(start_date[:4])
        valid_papers = []
        if papers:
            for paper in papers:
                paper_year = paper.get('year')
                if paper_year and isinstance(paper_year, int) and paper_year <= end_year:
                    valid_papers.append(paper)
                elif paper_year and isinstance(paper_year, str) and paper_year.isdigit():
                    if int(paper_year) <= end_year:
                        valid_papers.append(paper)

        logger.info(f"Filtered {len(valid_papers)} papers from {len(papers) if papers else 0} total (date constraint: year <= {end_year})")

        # 构建prompt
        prompt = self._build_prompt(topic, weekly_reports, valid_papers, start_date, end_date)

        # 调用LLM生成
        raw_content = await self._call_llm(prompt)

        # 生成报告名称（基于总结）
        report_title = self._generate_title(topic, papers, raw_content, start_date[:7])

        # 创建报告
        report = Report(
            title=report_title,
            config=self.config,
            raw_content=raw_content
        )

        # 添加文献综述风格的默认章节
        report.add_section(self._create_section("一、本月研究总览", level=1))
        report.add_section(self._create_section("二、核心论文综合分析", level=1))
        report.add_section(self._create_section("三、主要学术贡献", level=1))
        report.add_section(self._create_section("四、方法论评述", level=1))
        report.add_section(self._create_section("五、未来研究方向", level=1))

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
        """构建文献综述风格的prompt（遵循Agent提示词工程指南五部分结构）"""
        # 提取年月
        year_month = start_date[:7]

        # 构建论文信息
        paper_info = ""
        if papers:
            for i, paper in enumerate(papers):
                title = paper.get('title', 'N/A')
                authors = paper.get('authors', [])
                if isinstance(authors, list):
                    authors_str = ', '.join(authors[:3])
                else:
                    authors_str = str(authors)
                year = paper.get('year', 'n.d.')
                contribution = paper.get('key_contribution', '')
                paper_info += f"""
### 论文{i+1}: {title}
- 作者: {authors_str}
- 年份: {year}
- 核心贡献: {contribution}
"""

        # 构建论文详情（用于综合分析章节）
        paper_details = ""
        if papers:
            for i, paper in enumerate(papers):
                title = paper.get('title', 'N/A')
                authors = paper.get('authors', [])
                if isinstance(authors, list):
                    authors_str = ', '.join(authors[:3])
                else:
                    authors_str = str(authors)
                year = paper.get('year', 'n.d.')
                contribution = paper.get('key_contribution', '')
                paper_details += f"""
### 论文{i+1}：{title}
作者：{authors_str}，{year}
核心贡献：{contribution}

【研究问题与动机】请详细分析这篇论文的研究问题和动机。

【技术方法与模型架构】请详细分析这篇论文的技术方法和模型架构。

【关键实验结果】请详细分析这篇论文的关键实验结果。

【贡献与局限性】请详细分析这篇论文的主要贡献和局限性。
"""

        # 收集周报摘要（用于月度汇总）
        weekly_summary = ""
        if weekly_reports:
            for i, weekly in enumerate(weekly_reports):
                week_label = weekly.get("week", f"Week {i+1}")
                summary = weekly.get("summary", weekly.get("raw_content", "No summary"))
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                weekly_summary += f"""
## {week_label}
{summary}
"""
        else:
            weekly_summary = "（无周报数据）"

        prompt = f"""你是一位资深学术研究员。请撰写关于"{topic}"的文献综述月报，包含以下五章结构，每章必须有实质内容（至少200字），直接输出学术报告正文。

重要规则：
1. 直接输出学术报告正文，不要包含任何思考过程、规划说明、结构框架
2. 不要使用[think]、[judge]、[analyze]等标签
3. 章节标题格式必须为"## 一、本月研究总览"、"## 二、核心论文综合分析"等，使用##而非###
4. 章节编号必须连续：一、二、三、四、五，不要跳过任何编号
5. 不要写"让我按照结构来撰写"、"首先"、"其次"、"最后"等引导语
6. 论文的年份必须早于{year_month}，严禁引用未来日期的论文

## 一、本月研究总览

请阐述{topic}本月的研究背景、整体进展、核心成果和主要挑战。从全局视角总结本月的研究脉络和关键突破。

## 二、核心论文综合分析

{paper_details if paper_details else "请根据提供的数据（如果有）分析相关论文。如果没有论文数据，请基于本月研究主题进行综合性分析。"}

对于每篇论文，必须包含：
- 研究问题与动机
- 技术方法与模型架构
- 关键实验结果
- 贡献与局限性

## 三、主要学术贡献

请总结本月核心论文的主要学术贡献。必须包含从"第一"到"第八"的完整八条贡献，不要跳过任何编号，每条至少50字。

重点分析：
- 这些论文在学术上有哪些创新点和突破？
- 对{topic}领域的发展有何推动作用？
- 解决了哪些重要研究问题或填补了哪些研究空白？

## 四、方法论评述

请对本月论文的方法论进行深度评述，分析各方法的优势、局限和适用场景。

重点分析：
- 这些论文在研究方法上有何创新？
- 方法论对后续研究有何指导和借鉴意义？
- 存在哪些方法论层面的不足或挑战？

## 五、未来研究方向

基于本月研究成果，建议未来的研究方向从以下方面展开：

**本月时间范围**：{year_month}（{start_date} 至 {end_date}）

**本月汇总的周报**：
{weekly_summary}

请直接输出学术报告正文，每章至少200字。"""

        return prompt

    def _generate_title(
        self,
        topic: str,
        papers: Optional[List[Dict]],
        raw_content: str,
        year_month: str
    ) -> str:
        """
        根据内容生成报告名称

        Args:
            topic: 研究主题
            papers: 论文列表
            raw_content: 生成的报告内容
            year_month: 年月（YYYY-MM格式）

        Returns:
            str: 生成的报告名称
        """
        title_parts = []

        if topic:
            title_parts.append(topic)

        if papers:
            top_paper = papers[0]
            paper_title = top_paper.get('title', '')[:20]
            if paper_title:
                title_parts.append(paper_title)

        if raw_content:
            lines = raw_content.split('\n')
            for line in lines[:5]:
                if line.startswith('#') or line.startswith('##'):
                    continue
                if len(line) > 5 and len(line) < 30:
                    title_parts.append(line.strip())
                    break

        if title_parts:
            keywords = ' / '.join(title_parts[:2])
            return f"月报 - {keywords} - {year_month}"
        else:
            return f"月报 - {topic} - {year_month}"

    def _format_references(self, papers: List[Dict]) -> List[Dict[str, Any]]:
        """格式化参考文献"""
        from ..common.citation import CitationFormatter, ParsedCitation

        formatter = CitationFormatter()
        references = []

        for i, paper in enumerate(papers[:self.config.max_references]):
            authors = paper.get('authors')
            # 标准化authors为字符串列表
            if isinstance(authors, list):
                # 展平嵌套列表
                flat_authors = []
                for a in authors:
                    if isinstance(a, list):
                        flat_authors.extend(a)
                    else:
                        flat_authors.append(a)
                authors = flat_authors
            elif authors is None:
                authors = []

            parsed = ParsedCitation(
                ref_num=str(i+1),
                title=paper.get('title'),
                authors=authors,
                year=paper.get('year')
            )
            formatted = formatter.format(parsed, f"ref_{i+1}")
            references.append({"formatted": formatted.text})

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