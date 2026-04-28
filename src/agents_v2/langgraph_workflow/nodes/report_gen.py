"""
报告生成节点 - Report Generation Node

功能：
1. 根据统计数据生成报告内容
2. 复用现有的报告生成器（DailyWatcher, WeeklyReport, MonthlyReport）
3. 生成结构化的报告文档

设计原则：
- 复用 qa/ 模块的报告生成器
- 支持多种报告格式
- ��成可读性强的报告
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ReportGenNode:
    """报告生成节点 - 生成最终报告文档"""

    def __init__(self, llm_provider=None):
        """初始化报告生成节点

        Args:
            llm_provider: LLM 提供者（可选），用于生成报告摘要
        """
        self.llm_provider = llm_provider

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告生成

        Args:
            state: 当前状态，需包含 report_stats 和 papers

        Returns:
            更新后的状态，添加 report_content 字段
        """
        report_type = state.get("report_type", "daily")
        stats = state.get("report_stats", {})
        papers = state.get("papers", [])

        if not papers:
            logger.warning("No papers for report generation")
            state["report_content"] = self._empty_report(report_type)
            return state

        try:
            # 生成报告内容
            report_content = self._generate_report(report_type, stats, papers)
            state["report_content"] = report_content

            logger.info(f"Report generation completed: {report_type} report")

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            state["report_content"] = self._empty_report(report_type)
            state.setdefault("errors", []).append(f"Report gen error: {str(e)}")

        return state

    def _generate_report(
        self,
        report_type: str,
        stats: Dict[str, Any],
        papers: list
    ) -> str:
        """生成报告内容"""
        sections = []

        # 标题
        title = self._get_report_title(report_type)
        sections.append(f"# {title}\n")

        # 概览
        sections.append("## 概览\n")
        sections.append(f"- 论文总数: {stats.get('total_papers', 0)}\n")
        sections.append(f"- 发表场所: {len(stats.get('venues', {}))}\n")
        sections.append(f"- 作者数量: {len(stats.get('authors', {}))}\n")

        citations = stats.get('citations', {})
        sections.append(f"- 总引用数: {citations.get('total', 0)}\n")
        sections.append(f"- 平均引用: {citations.get('avg', 0):.1f}\n\n")

        # Top 论文
        sections.append("## 高引用论文 Top 10\n")
        top_papers = stats.get('top_papers', [])[:10]
        for i, paper in enumerate(top_papers, 1):
            title = paper.get('title', 'Unknown')
            citations = paper.get('citations', 0)
            authors = paper.get('authors', [])
            author_str = ', '.join(authors[:3]) if authors else 'Unknown'
            sections.append(
                f"{i}. **{title}** ({citations} citations)\n"
                f"   - 作者: {author_str}\n"
            )
        sections.append("\n")

        # 热门场所
        sections.append("## 热门发表场所\n")
        venues = stats.get('venues', {})
        for venue, count in list(venues.items())[:10]:
            sections.append(f"- {venue}: {count} 篇\n")
        sections.append("\n")

        # 关键词
        sections.append("## 研究热点关键词\n")
        keywords = stats.get('keywords', [])[:20]
        sections.append(", ".join(keywords) + "\n\n")

        return "".join(sections)

    def _get_report_title(self, report_type: str) -> str:
        """获取报告标题"""
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

        titles = {
            "daily": f"学术资讯日报 - {date_str}",
            "weekly": f"学术资讯周报 - {date_str}",
            "monthly": f"学术资讯月报 - {date_str}"
        }
        return titles.get(report_type, f"学术资讯报告 - {date_str}")

    def _empty_report(self, report_type: str) -> str:
        """生成空报告"""
        title = self._get_report_title(report_type)
        return f"# {title}\n\n暂无数据\n"
