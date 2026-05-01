"""
报告爬取节点 - Report Crawl Node

功能：
1. 根据报告类型（日报/周报/月报）搜索论文
2. 复用现有的 PaperSearchAgent
3. 支持关键词过滤和时间范围

设计原则：
- 复用 qa/paper_search.py 的 PaperSearchAgent
- 根据报告类型调整搜索参数
- 保持状态一致性
"""
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ReportCrawlNode:
    """报告爬取节点 - 为报告生成搜索论文"""

    def __init__(self):
        """初始化报告爬取节点"""
        from ...paper_search.paper_search import PaperSearchAgent
        self.search_agent = PaperSearchAgent()

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告论文搜索

        Args:
            state: 当前状态，需包含 report_type 和 keywords

        Returns:
            更新后的状态，添加 papers 字段
        """
        report_type = state.get("report_type", "daily")
        keywords = state.get("keywords", [])
        user_query = state.get("user_query", "")

        if not keywords and not user_query:
            logger.warning("No keywords or query for report")
            state["papers"] = []
            return state

        try:
            # 根据报告类型确定时间范围
            date_range = self._get_date_range(report_type)

            # 构建搜索查询
            if keywords:
                query = " OR ".join(keywords)
            else:
                query = user_query

            # 执行搜索
            search_params = {
                "source": "all",
                "max_results": self._get_max_results(report_type),
                "date_range": date_range
            }

            result = await self.search_agent.execute(query, search_params)

            # 更新状态
            papers = result.get("papers", [])
            state["papers"] = papers
            state["report_search_count"] = len(papers)

            logger.info(
                f"Report crawl completed: {len(papers)} papers found "
                f"for {report_type} report"
            )

        except Exception as e:
            logger.error(f"Report crawl failed: {e}")
            state["papers"] = []
            state.setdefault("errors", []).append(f"Report crawl error: {str(e)}")

        return state

    def _get_date_range(self, report_type: str) -> Dict[str, str]:
        """根据报告类型获取日期范围"""
        now = datetime.now()

        if report_type == "daily":
            start = now - timedelta(days=1)
        elif report_type == "weekly":
            start = now - timedelta(days=7)
        elif report_type == "monthly":
            start = now - timedelta(days=30)
        else:
            start = now - timedelta(days=7)  # 默认周报

        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d")
        }

    def _get_max_results(self, report_type: str) -> int:
        """根据报告类型获取最大结果数"""
        return {
            "daily": 20,
            "weekly": 50,
            "monthly": 100
        }.get(report_type, 50)
