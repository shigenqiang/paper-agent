"""每日论文监控Agent - 自动订阅和总结最新统计学论文"""
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
class DailyPaperReport:
    """每日论文报告"""
    date: str
    topic: str
    keywords: List[str]
    papers_found: int
    summary: str
    new_methods: List[str] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    top_papers: List[Dict[str, Any]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


class DailyWatcher(BaseQAAgent):
    """
    每日论文监控Agent

    功能：
    1. 定期搜索最新统计学论文
    2. 筛选高相关性论文
    3. 生成摘要报告
    4. 追踪研究趋势

    使用场景：
    - 每日自动推送
    - 特定主题追踪
    - 新论文提醒
    """

    # 默认搜索关键词
    DEFAULT_KEYWORDS = [
        "statistical learning",
        "causal inference",
        "bayesian methods",
        "machine learning",
        "time series analysis"
    ]

    def __init__(self):
        super().__init__(
            name="DailyWatcher",
            description="每日论文监控Agent"
        )
        self.search_agent = PaperSearchAgent()
        self.system_prompt = """你是一个专业的学术信息分析助手，擅长：
1. 从论文列表中提取关键信息
2. 识别新方法和研究趋势
3. 生成简洁准确的摘要

请保持客观和专业的分析风格。"""

    async def execute(
        self,
        keywords: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行每日监控

        Args:
            keywords: 搜索关键词列表
            context: 配置（days, max_papers等）

        Returns:
            每日报告字典
        """
        keywords = keywords or self.DEFAULT_KEYWORDS
        context = context or {}

        days = context.get("days", 30)
        max_papers_per_keyword = context.get("max_papers", 10)

        self.logger.info(f"开始每日监控，关键词: {keywords}")

        try:
            # 并行搜索每个关键词
            tasks = []
            for kw in keywords:
                task = self._search_keyword(kw, days, max_papers_per_keyword)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 聚合论文
            all_papers = []
            for result in results:
                if isinstance(result, list):
                    all_papers.extend(result)

            # 去重和排序
            all_papers = self._deduplicate_and_rank(all_papers, keywords)

            # 生成报告
            report = await self._generate_daily_report(
                papers=all_papers,
                keywords=keywords,
                days=days
            )

            self.logger.info(f"每日监控完成，找到 {len(all_papers)} 篇论文")

            return {
                "success": True,
                "report": report,
                "papers_found": len(all_papers),
                "keywords_searched": keywords
            }

        except Exception as e:
            self.logger.error(f"每日监控失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "report": None
            }

    async def _search_keyword(
        self,
        keyword: str,
        days: int,
        max_papers: int
    ) -> List[Dict]:
        """搜索单个关键词"""
        try:
            result = await self.search_agent.execute(
                keyword,
                {"source": "all", "time_range": days, "max_results": max_papers}
            )
            return result.get("papers", [])
        except Exception as e:
            self.logger.error(f"关键词 '{keyword}' 搜索失败: {e}")
            return []

    def _deduplicate_and_rank(
        self,
        papers: List[Dict],
        keywords: List[str]
    ) -> List[Dict]:
        """去重并排序"""
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            title_lower = paper.get("title", "").lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_papers.append(paper)

        # 按相关性和时间排序
        def score(paper: Dict) -> float:
            s = 0.0
            # 关键词匹配
            abstract = paper.get("abstract", "").lower()
            for kw in keywords:
                if kw.lower() in abstract:
                    s += 2.0
                if kw.lower() in paper.get("title", "").lower():
                    s += 3.0
            # 最新论文
            year = paper.get("year", 2020)
            if year >= 2025:
                s += 2.0
            elif year >= 2024:
                s += 1.0
            return s

        return sorted(unique_papers, key=score, reverse=True)

    async def _generate_daily_report(
        self,
        papers: List[Dict],
        keywords: List[str],
        days: int
    ) -> Dict[str, Any]:
        """生成每日报告"""
        if not papers:
            return {
                "date": datetime.now().isoformat(),
                "topic": ", ".join(keywords),
                "keywords": keywords,
                "papers_found": 0,
                "summary": "未找到相关论文",
                "content": "# 每日学术资讯\n\n未找到相关论文",
                "new_methods": [],
                "trends": [],
                "top_papers": [],
                "references": []
            }

        # 构建prompt - 输出Markdown格式
        top_papers = papers[:20]  # 最多分析20篇
        papers_info = "\n".join([
            f"- **{p.get('title', 'Unknown')}** ({p.get('year', '')}, {p.get('source', '')})"
            for p in top_papers
        ])

        prompt = f"""请分析以下最近{days}天内的学术论文列表，生成每日摘要报告。

## 搜索关键词
{', '.join(keywords)}

## 论文列表
{papers_info}

## 报告要求

请生成Markdown格式的每日报告，标题格式为：
`# 每日学术资讯报告 - YYYY-MM-DD 主题名称`

报告包含以下部分：
1. **## 最新研究进展** - 简要概述最重要的发现
2. **## 新方法新技术** - 列出出现的新方法
3. **## 研究趋势** - 分析当前研究趋势
4. **## 重点论文推荐** - 列出3-5篇最重要的论文及其亮点

注意：
- 报告使用中文撰写
- Markdown格式要规范
- 内容要简洁专业
- 不要包含参考文献链接（在下方单独列出）
"""
        response = await self._llm_call(prompt, self.system_prompt)

        # 构建参考文献
        references = []
        for i, p in enumerate(top_papers[:10], 1):
            title = p.get('title', 'Unknown')
            url = p.get('url', '')
            source = p.get('source', '')
            if url:
                references.append(f"[{i}]: {url}")
            else:
                references.append(f"[{i}]: {source}")

        # 返回结构化报告
        # 从响应中提取标题（第一行）
        title_lines = response.strip().split('\n')
        title = title_lines[0].lstrip('# ').strip() if title_lines else f"每日学术资讯报告 - {datetime.now().strftime('%Y-%m-%d')}"

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "title": title,
            "topic": title,
            "keywords": keywords,
            "papers_found": len(papers),
            "summary": response,
            "content": f"{response}\n\n---\n\n## 参考文献\n\n" + "\n".join(references) if references else response,
            "new_methods": [],
            "trends": [],
            "top_papers": [{"title": p.get("title", ""), "reason": ""} for p in papers[:5]],
            "references": references
        }

    def run_sync(
        self,
        keywords: Optional[List[str]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """同步运行每日监控（用于定时任务）"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.execute(keywords, {"days": days}))

    def schedule_daily(
        self,
        hour: int = 8,
        minute: int = 0
    ) -> str:
        """
        生成cron表达式用于每日定时执行

        返回格式用于调度器
        """
        return f"0 {minute} {hour} * * *"  # 每天早上{hour}:{minute}执行