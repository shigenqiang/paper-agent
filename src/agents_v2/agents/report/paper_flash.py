"""论文快讯Agent - 热点论文快速解读"""
from src.agents_v2.logging_config import get_logging_logger

import asyncio

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import json

from .base_qa_agent import BaseQAAgent
from .paper_search import PaperSearchAgent

logger = get_logging_logger(__name__)


class FlashType(str, Enum):
    """快讯类型"""
    HOT = "hot"              # 热点论文
    TRENDING = "trending"    # 上升趋势
    CONFERENCE = "conference" # 顶会论文


@dataclass
class FlashReport:
    """论文快讯"""
    title: str
    authors: List[str]
    source: str
    published_date: str
    core_finding: str       # 3句话核心发现
    key_points: List[str]   # 要点列表
    significance: str        # 研究意义
    reading_time: str       # 预估阅读时间
    tldr: str               # 一句话总结
    reason: str = ""        # 入眩原因


@dataclass
class PaperFlashResult:
    """论文快讯结果"""
    type: FlashType
    generated_at: str
    topic: str
    reports: List[Dict[str, Any]]
    papers_analyzed: int
    success: bool


class PaperFlash(BaseQAAgent):
    """
    论文快讯Agent

    功能：
    1. 热点论文快速解读（5分钟内）
    2. arXiv热门追踪
    3. 顶会论文第一时间解读

    使用场景：
    - 每日热点推送
    - 顶会论文速报
    - 特定领域热点追踪
    """

    # 顶会列表
    TOP_CONFERENCES = {
        "NeurIPS": ["neurIPS", "NeurIPS", "NIPS"],
        "ICML": ["ICML"],
        "ICLR": ["ICLR"],
        "CVPR": ["CVPR"],
        "ICCV": ["ICCV"],
        "ECCV": ["ECCV"],
        "AAAI": ["AAAI"],
        "IJCAI": ["IJCAI"],
        "ACL": ["ACL"],
        "EMNLP": ["EMNLP"],
        "NAACL": ["NAACL"],
    }

    def __init__(self):
        super().__init__(
            name="PaperFlash",
            description="论文快讯 - 热点论文快速解读"
        )
        self.search_agent = PaperSearchAgent()
        self.system_prompt = """你是一个专业的学术论文速读专家，擅长：
1. 快速提取论文核心发现
2. 用简洁语言概括要点
3. 评估研究意义和影响

请保持：
- 语言简洁明了
- 突出创新点
- 客观评价局限性"""

    async def execute(
        self,
        flash_type: FlashType = FlashType.HOT,
        topic: Optional[str] = None,
        limit: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行论文快讯生成

        Args:
            flash_type: 快讯类型 (hot/trending/conference)
            topic: 主题关键词（可选）
            limit: 返回数量，默认5
            context: 配置（conference_name等）

        Returns:
            快讯结果字典
        """
        context = context or {}
        topic = topic or "machine learning"

        self.logger.info(f"生成{flash_type}类型论文快讯，主题: {topic}")

        try:
            # 1. 搜索相关论文
            papers = await self._search_papers(flash_type, topic, limit, context)

            if not papers:
                return {
                    "success": False,
                    "error": "未找到相关论文",
                    "type": flash_type,
                    "reports": []
                }

            # 2. 生成快讯
            flash_reports = await self._generate_flash_reports(papers, flash_type, topic)

            result = PaperFlashResult(
                type=flash_type,
                generated_at=datetime.now().isoformat(),
                topic=topic,
                reports=[r for r in flash_reports],
                papers_analyzed=len(papers),
                success=True
            )

            self.logger.info(f"论文快讯生成完成，共{len(flash_reports)}篇")

            return {
                "success": True,
                "type": result.type,
                "generated_at": result.generated_at,
                "topic": result.topic,
                "reports": result.reports,
                "papers_analyzed": result.papers_analyzed
            }

        except Exception as e:
            self.logger.error(f"论文快讯生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "type": flash_type,
                "reports": []
            }

    async def _search_papers(
        self,
        flash_type: FlashType,
        topic: str,
        limit: int,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """搜索论文"""
        try:
            if flash_type == FlashType.HOT:
                # 热点：搜索最新高相关论文
                return await self._search_hot_papers(topic, limit)
            elif flash_type == FlashType.TRENDING:
                # 趋势：搜索近期论文并按引用排序
                return await self._search_trending_papers(topic, limit)
            elif flash_type == FlashType.CONFERENCE:
                # 顶会：搜索特定会议论文
                conference = context.get("conference_name", "NeurIPS")
                return await self._search_conference_papers(topic, conference, limit)
            else:
                return []
        except Exception as e:
            self.logger.error(f"论文搜索失败: {e}")
            return []

    async def _search_hot_papers(
        self,
        topic: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """搜索热点论文"""
        result = await self.search_agent.execute(
            topic,
            {
                "source": "all",
                "time_range": 7,  # 最近7天
                "max_results": limit * 2  # 多搜一些用于筛选
            }
        )
        papers = result.get("papers", [])

        # 按引用数排序，选取top
        sorted_papers = sorted(
            papers,
            key=lambda p: p.get("citations", 0),
            reverse=True
        )
        return sorted_papers[:limit]

    async def _search_trending_papers(
        self,
        topic: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """搜索上升趋势论文"""
        # 搜索最近30天论文
        result = await self.search_agent.execute(
            topic,
            {
                "source": "all",
                "time_range": 30,
                "max_results": limit * 3
            }
        )
        papers = result.get("papers", [])

        # 简单策略：优先选择最新且有较高引用的
        def trending_score(paper):
            citations = paper.get("citations", 0)
            year = paper.get("year", 2020)
            # 新论文且有一定引用量
            return citations * 0.7 + (1 if year >= 2024 else 0) * 10

        sorted_papers = sorted(papers, key=trending_score, reverse=True)
        return sorted_papers[:limit]

    async def _search_conference_papers(
        self,
        topic: str,
        conference: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """搜索顶会论文"""
        # 搜索会议最近一年的论文
        result = await self.search_agent.execute(
            topic,
            {
                "source": "all",
                "time_range": 365,
                "max_results": limit * 2
            }
        )
        papers = result.get("papers", [])

        # 筛选会议论文
        conference_keywords = self.TOP_CONFERENCES.get(conference, [conference])
        filtered = []
        for p in papers:
            title = p.get("title", "").lower()
            source = p.get("source", "").lower()
            if any(kw.lower() in title or kw.lower() in source for kw in conference_keywords):
                filtered.append(p)

        return filtered[:limit]

    async def _generate_flash_reports(
        self,
        papers: List[Dict[str, Any]],
        flash_type: FlashType,
        topic: str
    ) -> List[Dict[str, Any]]:
        """生成快讯报告"""
        reports = []

        for paper in papers:
            try:
                report = await self._generate_single_report(paper, flash_type)
                if report:
                    reports.append(report)
            except Exception as e:
                self.logger.warning(f"生成单篇快讯失败: {e}")
                continue

        return reports

    async def _generate_single_report(
        self,
        paper: Dict[str, Any],
        flash_type: FlashType
    ) -> Optional[Dict[str, Any]]:
        """生成单篇论文快讯"""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")[:1000]  # 限制长度
        authors = paper.get("authors", [])[:5]  # 只取前5个作者
        year = paper.get("year", "")
        source = paper.get("source", "")

        prompt = f"""请为以下论文生成5分钟速读快讯。

## 论文信息
标题: {title}
作者: {', '.join(authors)}
年份: {year}
来源: {source}
摘要: {abstract}

## 快讯要求
请生成JSON格式的论文快讯：

{{
    "title": "论文标题",
    "authors": ["作者列表"],
    "source": "来源",
    "published_date": "发表日期",
    "core_finding": "3句话核心发现",
    "key_points": ["要点1", "要点2", "要点3"],
    "significance": "研究意义和影响",
    "reading_time": "预估阅读时间，如'5分钟'",
    "tldr": "一句话总结（不超过50字）",
    "reason": "入选原因（如'高引用'、'新方法'等）"
}}
"""
        response = await self._llm_call(prompt, self.system_prompt)

        try:
            # 尝试解析JSON
            report_data = json.loads(response)
            # 确保必要字段存在
            report_data.setdefault("title", title)
            report_data.setdefault("authors", authors)
            report_data.setdefault("source", source)
            report_data.setdefault("published_date", str(year))
            return report_data
        except json.JSONDecodeError as e:
            # 降级处理
            self.logger.warning(f"JSON parse failed in _generate_single_report: {e}, raw_input={response[:500] if response else 'empty'}")
            return {
                "title": title,
                "authors": authors,
                "source": source,
                "published_date": str(year),
                "core_finding": response[:300] if response else "生成失败",
                "key_points": [],
                "significance": "",
                "reading_time": "5分钟",
                "tldr": title[:50],
                "reason": "默认入选"
            }

    def run_sync(
        self,
        flash_type: FlashType = FlashType.HOT,
        topic: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """同步运行论文快讯（用于定时任务）"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.execute(flash_type, topic, limit))

    async def generate_daily_flash(
        self,
        topics: Optional[List[str]] = None,
        limit_per_topic: int = 3
    ) -> Dict[str, Any]:
        """
        生成每日多主题快讯

        Args:
            topics: 主题列表，默认机器学习相关
            limit_per_topic: 每个主题的快讯数量

        Returns:
            每日快讯汇总
        """
        topics = topics or [
            "machine learning",
            "deep learning",
            "natural language processing",
            "computer vision"
        ]

        all_reports = []
        topics_processed = 0

        for topic in topics:
            try:
                result = await self.execute(
                    flash_type=FlashType.HOT,
                    topic=topic,
                    limit=limit_per_topic
                )
                if result.get("success"):
                    all_reports.extend(result.get("reports", []))
                    topics_processed += 1
            except Exception as e:
                self.logger.error(f"主题 '{topic}' 快讯生成失败: {e}")
                continue

        return {
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": "daily_flash",
            "topics_processed": topics_processed,
            "total_reports": len(all_reports),
            "reports": all_reports
        }

    async def generate_conference_flash(
        self,
        conference: str,
        topic: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        生成顶会论文快讯

        Args:
            conference: 会议名称 (NeurIPS/ICML/ICLR等)
            topic: 主题关键词
            limit: 返回数量

        Returns:
            顶会快讯
        """
        topic = topic or "machine learning"

        return await self.execute(
            flash_type=FlashType.CONFERENCE,
            topic=topic,
            limit=limit,
            context={"conference_name": conference}
        )


class FlashSubscription:
    """
    论文快讯订阅

    用于配置和管理论文快讯订阅
    """

    def __init__(
        self,
        user_id: str,
        flash_types: List[FlashType],
        topics: List[str],
        limit_per_flash: int = 5
    ):
        self.user_id = user_id
        self.flash_types = flash_types
        self.topics = topics
        self.limit_per_flash = limit_per_flash
        self.enabled = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "flash_types": [t.value for t in self.flash_types],
            "topics": self.topics,
            "limit_per_flash": self.limit_per_flash,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlashSubscription":
        return cls(
            user_id=data["user_id"],
            flash_types=[FlashType(t) for t in data.get("flash_types", ["hot"])],
            topics=data.get("topics", ["machine learning"]),
            limit_per_flash=data.get("limit_per_flash", 5)
        )
