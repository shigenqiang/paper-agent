"""
Literature Review generator for Agent v3.

Generates a traceable literature review from paper cards, evidence table,
and knowledge graph (AGENT.md §1).
"""

from __future__ import annotations

import logging

from src.agent_v3.agents.base import BaseAgent
from src.agent_v3.core.config import AppConfig
from src.agent_v3.models import (
    EvidenceRecord,
    KnowledgeGraph,
    LiteratureReview,
    PaperCard,
    RetrievalScope,
)

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """你是一个学术文献综述写作专家。你需要基于论文卡片、证据表和知识图谱，生成一篇结构化的文献综述。

综述必须：
1. 基于给定证据，不编造
2. 引用具体论文
3. 按主题聚类组织
4. 指出研究趋势和空白

请严格按照JSON格式输出。"""

REVIEW_PROMPT = """请基于以下论文信息生成文献综述。

## 研究范围
{scope_description}

## 论文卡片
{cards_text}

## 证据表
{evidence_text}

## 知识图谱关系
{kg_text}

## 用户研究目标（可选）
{research_goal}

请输出JSON格式：
{{
  "title": "综述标题",
  "research_background": "研究背景段落",
  "topic_clusters": "按主题聚类分析段落，每个主题列出代表论文",
  "representative_papers": "代表性论文和研究时间线段落",
  "main_methods": "主要方法总结段落",
  "main_findings": "主要发现总结段落",
  "limitations": "现有工作局限性段落",
  "future_trends": "未来趋势段落",
  "references": "参考文献列表（按引用顺序）"
}}

注意：
- 每个段落至少引用2-3篇论文
- 引用格式: (作者, 年份) 或 [论文标题]
- 不要编造论文内容"""


class LiteratureReviewGenerator(BaseAgent):
    """Generate literature reviews from project data."""

    def __init__(self, config: AppConfig):
        super().__init__(config, name="literature_review")

    async def generate(
        self,
        cards: list[PaperCard],
        evidence: list[EvidenceRecord],
        kg: KnowledgeGraph,
        scope: RetrievalScope | None = None,
        research_goal: str = "",
    ) -> LiteratureReview:
        """
        Generate a literature review.

        Args:
            cards: Paper cards
            evidence: Evidence records
            kg: Knowledge graph
            scope: Optional retrieval scope
            research_goal: User's research goal

        Returns:
            LiteratureReview with structured sections
        """
        # Filter by scope
        if scope and scope.selected_paper_ids:
            filtered_cards = [
                c for c in cards if c.paper_id in scope.selected_paper_ids
            ]
            filtered_evidence = [
                e for e in evidence if e.paper_id in scope.selected_paper_ids
            ]
            scope_desc = f"选定的{len(filtered_cards)}篇论文"
        else:
            filtered_cards = cards
            filtered_evidence = evidence
            scope_desc = f"项目全部{len(cards)}篇论文"

        # Build context
        cards_text = (
            "\n\n".join(
                f"### {c.title} ({c.year})\n"
                f"- 研究问题: {c.research_question}\n"
                f"- 方法: {c.method}\n"
                f"- 发现: {'; '.join(c.key_findings[:3])}\n"
                f"- 局限: {'; '.join(c.limitations[:2])}\n"
                f"- 主题: {', '.join(c.related_topics)}"
                for c in filtered_cards
            )
            or "无论文"
        )

        evidence_text = (
            "\n".join(
                f"- [{e.evidence_strength}] {e.finding} (主题: {e.topic})"
                for e in filtered_evidence[:30]
            )
            or "无证据"
        )

        kg_text = self._build_kg_summary(kg, filtered_cards)

        prompt = REVIEW_PROMPT.format(
            scope_description=scope_desc,
            cards_text=cards_text,
            evidence_text=evidence_text,
            kg_text=kg_text,
            research_goal=research_goal or "未指定",
        )

        try:
            result = await self.call_llm(prompt, REVIEW_SYSTEM_PROMPT, json_mode=True)
        except Exception as e:
            logger.error(f"Review generation failed: {e}")
            return LiteratureReview(title="生成失败", full_text=str(e))

        # Build full text
        sections = [
            ("## 研究背景", result.get("research_background", "")),
            ("## 主题聚类分析", result.get("topic_clusters", "")),
            ("## 代表性论文与研究时间线", result.get("representative_papers", "")),
            ("## 主要方法", result.get("main_methods", "")),
            ("## 主要发现", result.get("main_findings", "")),
            ("## 现有工作局限性", result.get("limitations", "")),
            ("## 未来趋势", result.get("future_trends", "")),
            ("## 参考文献", result.get("references", "")),
        ]
        full_text = f"# {result.get('title', '文献综述')}\n\n"
        full_text += "\n\n".join(
            f"{heading}\n\n{content}" for heading, content in sections if content
        )

        return LiteratureReview(
            title=result.get("title", "文献综述"),
            research_background=result.get("research_background", ""),
            topic_clusters=result.get("topic_clusters", ""),
            representative_papers=result.get("representative_papers", ""),
            main_methods=result.get("main_methods", ""),
            main_findings=result.get("main_findings", ""),
            limitations=result.get("limitations", ""),
            future_trends=result.get("future_trends", ""),
            references=result.get("references", ""),
            full_text=full_text,
        )

    def _build_kg_summary(self, kg: KnowledgeGraph, cards: list[PaperCard]) -> str:
        """Build KG summary for review generation."""
        paper_ids = {c.paper_id for c in cards}
        node_map = {n.node_id: n.label for n in kg.nodes}

        lines = []
        for e in kg.edges:
            if e.source_id in paper_ids or e.target_id in paper_ids:
                src = node_map.get(e.source_id, e.source_id)
                tgt = node_map.get(e.target_id, e.target_id)
                lines.append(f"- {src} --[{e.relation.value}]--> {tgt}")

        return "\n".join(lines[:50]) or "无图谱关系"
