"""
Paper Agent - generates paper cards from parsed papers.

Takes a Paper object and produces a PaperCard with structured fields:
research question, method, key findings, limitations, future work, etc.
"""

from __future__ import annotations

import logging

from src.agent_v3.agents.base import BaseAgent
from src.agent_v3.core.config import AppConfig
from src.agent_v3.models import Paper, PaperCard

logger = logging.getLogger(__name__)

PAPER_CARD_SYSTEM_PROMPT = """你是一个学术论文分析专家。你的任务是从论文全文中提取结构化信息，生成论文卡片(Paper Card)。

请严格按照JSON格式输出，不要输出任何其他内容。"""

PAPER_CARD_PROMPT = """请从以下论文全文中提取结构化信息，生成论文卡片。

## 论文标题
{title}

## 论文全文（前6000字）
{full_text}

请输出JSON格式：
{{
  "research_question": "这篇论文要解决什么研究问题？",
  "method": "使用了什么方法？",
  "dataset_or_sample": "使用了什么数据集或样本？",
  "key_findings": ["发现1", "发现2", ...],
  "limitations": ["局限1", "局限2", ...],
  "future_work": ["未来方向1", ...],
  "related_topics": ["主题1", "主题2", ...],
  "possible_innovation_points": ["可探索的创新点1", ...]
}}

注意：
- key_findings、limitations、future_work、related_topics、possible_innovation_points 是数组
- 如果论文中没有明确提到某项，留空数组[]
- 不要编造信息，只提取论文中实际提到的内容"""


class PaperAgent(BaseAgent):
    """Generate paper cards from parsed papers."""

    def __init__(self, config: AppConfig):
        super().__init__(config, name="paper_agent")

    async def generate_card(self, paper: Paper) -> PaperCard:
        """
        Generate a PaperCard from a Paper object.

        Args:
            paper: Parsed paper with full_text

        Returns:
            PaperCard with structured fields
        """
        title = paper.metadata.title
        text = paper.full_text[:6000]  # Cap to avoid token limits

        prompt = PAPER_CARD_PROMPT.format(title=title, full_text=text)

        try:
            result = await self.call_llm(
                prompt, PAPER_CARD_SYSTEM_PROMPT, json_mode=True
            )
        except Exception as e:
            logger.error(f"Paper card generation failed for '{title}': {e}")
            return PaperCard(
                paper_id=paper.paper_id,
                title=title,
                authors=paper.metadata.authors,
                year=paper.metadata.year,
                venue=paper.metadata.venue,
                abstract=paper.metadata.abstract or "",
            )

        return PaperCard(
            paper_id=paper.paper_id,
            title=title,
            authors=paper.metadata.authors,
            year=paper.metadata.year,
            venue=paper.metadata.venue,
            abstract=paper.metadata.abstract or "",
            research_question=result.get("research_question", ""),
            method=result.get("method", ""),
            dataset_or_sample=result.get("dataset_or_sample", ""),
            key_findings=result.get("key_findings", []),
            limitations=result.get("limitations", []),
            future_work=result.get("future_work", []),
            related_topics=result.get("related_topics", []),
            possible_innovation_points=result.get("possible_innovation_points", []),
        )

    async def generate_cards(self, papers: list[Paper]) -> list[PaperCard]:
        """Generate paper cards for multiple papers."""
        cards = []
        for paper in papers:
            card = await self.generate_card(paper)
            cards.append(card)
            logger.info(f"Generated card: {card.title[:50]}")
        return cards
