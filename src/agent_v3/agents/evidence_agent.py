"""
Evidence Agent - extracts evidence records from paper cards.

Takes PaperCard objects and produces EvidenceRecord entries for the evidence table.
"""

from __future__ import annotations

import logging

from src.agent_v3.agents.base import BaseAgent
from src.agent_v3.core.config import AppConfig
from src.agent_v3.models import EvidenceRecord, PaperCard

logger = logging.getLogger(__name__)

EVIDENCE_SYSTEM_PROMPT = """你是一个学术证据提取专家。你的任务是从论文卡片中提取证据记录(Evidence Record)。

一篇论文可能产生多条证据记录（对应不同的研究发现）。
请严格按照JSON格式输出。"""

EVIDENCE_PROMPT = """请从以下论文卡片中提取证据记录。

## 论文卡片
标题: {title}
研究问题: {research_question}
方法: {method}
数据集: {dataset}
关键发现: {key_findings}
局限性: {limitations}
未来工作: {future_work}
相关主题: {topics}

请输出JSON数组，每条记录包含：
[
  {{
    "research_question": "该发现对应的研究问题",
    "method": "使用的具体方法",
    "data_or_sample": "使用的数据或样本",
    "finding": "具体发现",
    "limitation": "相关局限",
    "future_work": "相关未来方向",
    "topic": "所属主题",
    "evidence_strength": "strong/moderate/weak",
    "citation_context": "引用上下文描述"
  }}
]

注意：
- 如果一篇论文有多个独立发现，每个发现一条记录
- evidence_strength: 实验验证=strong, 有数据支撑=moderate, 仅讨论=weak
- 不要编造信息"""


class EvidenceAgent(BaseAgent):
    """Extract evidence records from paper cards."""

    def __init__(self, config: AppConfig):
        super().__init__(config, name="evidence_agent")

    async def extract_evidence(self, card: PaperCard) -> list[EvidenceRecord]:
        """
        Extract evidence records from a paper card.

        Args:
            card: Paper card with structured fields

        Returns:
            List of evidence records
        """
        prompt = EVIDENCE_PROMPT.format(
            title=card.title,
            research_question=card.research_question,
            method=card.method,
            dataset=card.dataset_or_sample,
            key_findings="\n".join(f"- {f}" for f in card.key_findings) or "未提及",
            limitations="\n".join(f"- {l}" for l in card.limitations) or "未提及",
            future_work="\n".join(f"- {f}" for f in card.future_work) or "未提及",
            topics=", ".join(card.related_topics) or "未分类",
        )

        try:
            results = await self.call_llm(
                prompt, EVIDENCE_SYSTEM_PROMPT, json_mode=True
            )
        except Exception as e:
            logger.error(f"Evidence extraction failed for '{card.title}': {e}")
            return [
                EvidenceRecord(
                    paper_id=card.paper_id,
                    research_question=card.research_question,
                    method=card.method,
                    finding=card.key_findings[0] if card.key_findings else "",
                )
            ]

        if isinstance(results, dict):
            results = [results]

        records = []
        for r in results:
            records.append(
                EvidenceRecord(
                    paper_id=card.paper_id,
                    research_question=r.get("research_question", ""),
                    method=r.get("method", ""),
                    data_or_sample=r.get("data_or_sample", ""),
                    finding=r.get("finding", ""),
                    limitation=r.get("limitation", ""),
                    future_work=r.get("future_work", ""),
                    topic=r.get("topic", ""),
                    evidence_strength=r.get("evidence_strength", "moderate"),
                    citation_context=r.get("citation_context", ""),
                )
            )
        return records

    async def extract_all(self, cards: list[PaperCard]) -> list[EvidenceRecord]:
        """Extract evidence from multiple paper cards."""
        all_records = []
        for card in cards:
            records = await self.extract_evidence(card)
            all_records.extend(records)
            logger.info(
                f"Extracted {len(records)} evidence records from '{card.title[:50]}'"
            )
        return all_records
