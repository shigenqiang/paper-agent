"""
周报生成器 - Weekly Report Generator

功能：
1. 生成每周研究进展报告
2. 汇总多日的研究发现
3. 周度趋势分析
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseReportGenerator, ReportConfig, ReportSection, ReportType, Report

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
            config = ReportConfig.from_env(overrides={"report_type": ReportType.WEEKLY})
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
        生成周报（文献综述风格）

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

        logger.info(f"Generating weekly report (literature review style) for {start_date} to {end_date}")

        # 过滤论文日期（论文必须早于周报结束日期）
        valid_papers = []
        end_year = int(end_date[:4])
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
        prompt = self._build_prompt(topic, daily_reports, valid_papers, start_date, end_date)

        # 调用LLM生成
        raw_content = await self._call_llm(prompt)

        # 生成报告名称（基于总结）
        report_title = self._generate_title(topic, papers, raw_content, start_date, end_date)

        # 创建报告
        report = Report(
            title=report_title,
            config=self.config,
            raw_content=raw_content
        )

        # 添加文献综述风格的默认章节
        report.add_section(self._create_section("一、本周研究概述", level=1))
        report.add_section(self._create_section("二、核心论文深度分析", level=1))
        report.add_section(self._create_section("三、跨论文研究发现", level=1))
        report.add_section(self._create_section("四、方法对比与评估", level=1))
        report.add_section(self._create_section("五、下周研究计划", level=1))

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
        """构建文献综述风格的prompt（遵循Agent提示词工程指南五部分结构）"""

        # 收集论文信息用于Few-Shot示例
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

        # 构建论文详情（用于深度分析章节）
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

        # 收集日报摘要（用于周度汇总）
        daily_summary = ""
        if daily_reports:
            for i, daily in enumerate(daily_reports):
                date = daily.get("date", f"Day {i+1}")
                summary = daily.get("summary", daily.get("raw_content", "No summary"))
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                daily_summary += f"""
## {date}
{summary}
"""
        else:
            daily_summary = "（无日报数据）"

        prompt = f"""你是一位专业学术研究员。请撰写关于"{topic}"的文献综述周报，包含以下五章结构，每章必须有实质内容（至少200字），直接输出学术报告正文。

重要规则：
1. 直接输出学术报告正文，不要包含任何思考过程、规划说明、结构框架
2. 不要使用[think]、[judge]、[analyze]等标签
3. 章节标题格式必须为"## 一、本周研究概述"、"## 二、核心论文深度分析"等，使用##而非###
4. 章节编号必须连续：一、二、三、四、五，不要跳过任何编号
5. 不要写"让我按照结构来撰写"、"首先"、"其次"、"最后"等引导语
6. 论文的年份必须早于{end_date}，严禁引用未来日期的论文

## 一、本周研究概述

请阐述{topic}本周的研究背景、重要进展、核心发现和主要挑战。综合本周的文献调研和实验结果，给出本周研究的整体概览。

## 二、核心论文深度分析

{paper_details if paper_details else "请根据提供的数据（如果有）分析相关论文。如果没有论文数据，请基于本周研究主题进行综合性分析。"}

对于每篇论文，必须包含：
- 研究问题与动机
- 技术方法与模型架构
- 关键实验结果
- 贡献与局限性

## 三、跨论文研究发现

请总结本周核心论文的共同发现、研究趋势和跨论文关联。必须包含从"第一"到"第八"的完整八条发现，不要跳过任何编号，每条至少50字。

重点分析：
- 这些论文在方法上有何共同点和差异？
- 共同揭示了什么研究趋势？
- 不同论文之间有何关联或继承关系？

## 四、方法对比与评估

请对比本周论文的方法论、优劣势和适用场景。评估这些方法对{topic}领域的贡献和局限。

## 五、下周研究计划

基于本周研究发现，建议下周的研究工作从以下方向展开：需要深入的问题、计划开展的实验、待阅读的相关文献等。

**本周时间范围**：{start_date} 至 {end_date}

**本周汇总的日报**：
{daily_summary}

请直接输出学术报告正文，每章至少200字。"""

        return prompt

    def _generate_title(
        self,
        topic: str,
        papers: Optional[List[Dict]],
        raw_content: str,
        start_date: str,
        end_date: str
    ) -> str:
        """
        根据内容生成报告名称

        Args:
            topic: 研究主题
            papers: 论文列表
            raw_content: 生成的报告内容
            start_date: 开始日期
            end_date: 结束日期

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
            return f"周报 - {keywords} - {start_date}~{end_date}"
        else:
            return f"周报 - {topic} - {start_date}~{end_date}"

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