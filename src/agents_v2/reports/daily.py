"""
日报生成器 - Daily Report Generator

功能：
1. 生成每日研究进展报告
2. 收集当日重要论文和发现
3. 结构化输出（摘要、亮点、详情）
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseReportGenerator, ReportConfig, ReportSection, ReportType

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class DailyReportGenerator(BaseReportGenerator):
    """
    日报生成器

    生成结构：
    1. 今日摘要
    2. 重要发现
    3. 详细分析
    4. 明日展望
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        if config is None:
            config = ReportConfig(report_type=ReportType.DAILY)
        super().__init__(config)

        self.system_prompt = """你是一个专业的日报生成助手。根据今日的研究信息，生成结构化的日报。
格式要求：
1. 今日摘要（100字内）
2. 重要发现（3-5条）
3. 详细分析
4. 明日展望

语言：中文
风格：专业、简洁
"""

    async def generate(
        self,
        topic: str = "",
        papers: Optional[List[Dict[str, Any]]] = None,
        search_results: Optional[List[Dict[str, Any]]] = None,
        date: Optional[str] = None,
        **kwargs
    ) -> Report:
        """
        生成日报

        Args:
            topic: 研究主题
            papers: 今日收集的论文列表
            search_results: 搜索结果
            date: 日期（默认今天）

        Returns:
            Report 对象
        """
        date = date or datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Generating daily report for {date}, topic: {topic}")

        # 构建prompt
        prompt = self._build_prompt(topic, papers, search_results, date)

        # 调用LLM生成
        raw_content = await self._call_llm(prompt)

        # 创建报告
        report = Report(
            title=f"日报 - {topic} - {date}",
            config=self.config,
            raw_content=raw_content
        )

        # 添加默认章节
        report.add_section(self._create_section("今日摘要", level=1))
        report.add_section(self._create_section("重要发现", level=1))
        report.add_section(self._create_section("详细分析", level=1))
        report.add_section(self._create_section("明日展望", level=1))

        # 解析内容填充章节
        sections = self.parse_raw_to_sections(raw_content)
        if sections:
            report.sections = sections[:self.config.max_sections]

        # 设置元数据
        report.metadata = {
            "date": date,
            "topic": topic,
            "papers_count": len(papers) if papers else 0,
            "search_count": len(search_results) if search_results else 0,
        }

        # 添加参考文献
        if self.config.include_references and papers:
            report.references = self._format_references(papers)

        return report

    def _build_prompt(
        self,
        topic: str,
        papers: Optional[List[Dict]],
        search_results: Optional[List[Dict]],
        date: str
    ) -> str:
        """构建生成prompt"""
        prompt = f"""生成今日（{date}）的研究日报。

主题：{topic}

"""

        if papers:
            prompt += f"\n今日论文（{len(papers)}篇）：\n"
            for i, paper in enumerate(papers[:10]):  # 最多10篇
                prompt += f"{i+1}. {paper.get('title', 'N/A')}"
                if paper.get('authors'):
                    prompt += f" - {', '.join(paper['authors'][:3])}"
                if paper.get('year'):
                    prompt += f" ({paper['year']})"
                prompt += "\n"

        if search_results:
            prompt += f"\n搜索结果（{len(search_results)}条）：\n"
            for result in search_results[:5]:
                prompt += f"- {result.get('title', 'N/A')}\n"

        prompt += f"""
请按以下格式生成日报：

## 今日摘要
（100字内概括今日进展）

## 重要发现
1. ...
2. ...
3. ...

## 详细分析
（对每篇重要论文进行分析）

## 明日展望
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


async def generate_daily_report(
    topic: str,
    papers: Optional[List[Dict[str, Any]]] = None,
    search_results: Optional[List[Dict[str, Any]]] = None,
    date: Optional[str] = None,
    **kwargs
) -> Report:
    """
    便捷函数：生成日报

    Args:
        topic: 研究主题
        papers: 论文列表
        search_results: 搜索结果
        date: 日期

    Returns:
        Report 对象
    """
    generator = DailyReportGenerator()
    return await generator.generate(topic, papers, search_results, date, **kwargs)