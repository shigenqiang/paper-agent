"""
Innovation-Point Report generator for Agent v3.

Generates innovation points from knowledge graph gaps, shared limitations,
method-task missing links, and future work aggregation (AGENT.md §2).
"""

from __future__ import annotations

import logging

from src.agent_v3.agents.base import BaseAgent
from src.agent_v3.core.config import AppConfig
from src.agent_v3.models import (
    EvidenceRecord,
    InnovationPoint,
    InnovationReport,
    KnowledgeGraph,
    PaperCard,
    RetrievalScope,
)

logger = logging.getLogger(__name__)

INNOVATION_SYSTEM_PROMPT = """你是一个学术创新点分析专家。你需要基于论文卡片、证据表和知识图谱中的研究空白(Gap)和局限性(Limitation)，提出可行的研究创新点。

创新点要求：
1. 必须有具体的论文证据支撑
2. 不能是泛泛的表述（如"结合深度学习"、"扩大样本量"）
3. 必须说明为什么是创新的（现有研究的空白在哪里）
4. 必须评估可行性和风险

请严格按照JSON格式输出。"""

INNOVATION_PROMPT = """请基于以下论文信息分析创新点。

## 研究范围
{scope_description}

## 论文卡片（含局限性和未来方向）
{cards_text}

## 证据表（研究空白和局限性）
{gaps_text}

## 知识图谱关系
{kg_text}

请输出JSON格式：
{{
  "title": "创新点分析报告",
  "innovation_points": [
    {{
      "name": "创新点名称",
      "description": "详细描述",
      "why_innovative": "为什么是创新的（现有研究的空白）",
      "existing_research": "已有研究基础",
      "research_gap": "具体的研究空白",
      "supporting_papers": ["支撑论文1标题", "支撑论文2标题"],
      "contradictory_evidence": "可能存在的反对证据或限制",
      "feasibility": "可行性评估（高/中/低）及理由",
      "risk": "风险评估",
      "possible_topic": "可能的论文题目建议"
    }}
  ]
}}

注意：
- 每个创新点必须引用具体论文
- 不要提出泛泛的创新点（如"结合深度学习"）
- 每个创新点必须有支撑论文和研究空白的对应关系
- 至少提出3个创新点"""


class InnovationReportGenerator(BaseAgent):
    """Generate innovation-point reports from project data."""

    def __init__(self, config: AppConfig):
        super().__init__(config, name="innovation_report")

    async def generate(
        self,
        cards: list[PaperCard],
        evidence: list[EvidenceRecord],
        kg: KnowledgeGraph,
        scope: RetrievalScope | None = None,
    ) -> InnovationReport:
        """
        Generate an innovation-point report.

        Args:
            cards: Paper cards
            evidence: Evidence records
            kg: Knowledge graph
            scope: Optional retrieval scope

        Returns:
            InnovationReport with innovation points
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
                f"- 局限: {'; '.join(c.limitations)}\n"
                f"- 未来方向: {'; '.join(c.future_work)}\n"
                f"- 可能的创新点: {'; '.join(c.possible_innovation_points)}"
                for c in filtered_cards
            )
            or "无论文"
        )

        # Focus on gaps and limitations
        gaps_text = (
            "\n".join(
                f"- [{e.evidence_strength}] {e.finding}\n"
                f"  局限: {e.limitation}\n"
                f"  未来方向: {e.future_work}\n"
                f"  主题: {e.topic}"
                for e in filtered_evidence
                if e.limitation or e.future_work
            )
            or "无明确研究空白"
        )

        kg_text = self._build_kg_gaps(kg, filtered_cards)

        prompt = INNOVATION_PROMPT.format(
            scope_description=scope_desc,
            cards_text=cards_text,
            gaps_text=gaps_text,
            kg_text=kg_text,
        )

        try:
            result = await self.call_llm(
                prompt, INNOVATION_SYSTEM_PROMPT, json_mode=True
            )
        except Exception as e:
            logger.error(f"Innovation report generation failed: {e}")
            return InnovationReport(title="生成失败", full_text=str(e))

        # Parse innovation points
        points = []
        for p in result.get("innovation_points", []):
            points.append(
                InnovationPoint(
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    why_innovative=p.get("why_innovative", ""),
                    existing_research=p.get("existing_research", ""),
                    research_gap=p.get("research_gap", ""),
                    supporting_papers=p.get("supporting_papers", []),
                    contradictory_evidence=p.get("contradictory_evidence", ""),
                    feasibility=p.get("feasibility", ""),
                    risk=p.get("risk", ""),
                    possible_topic=p.get("possible_topic", ""),
                )
            )

        # Build full text
        full_text = f"# {result.get('title', '创新点分析报告')}\n\n"
        for i, p in enumerate(points, 1):
            full_text += f"## 创新点 {i}: {p.name}\n\n"
            full_text += f"**描述**: {p.description}\n\n"
            full_text += f"**创新性**: {p.why_innovative}\n\n"
            full_text += f"**已有研究**: {p.existing_research}\n\n"
            full_text += f"**研究空白**: {p.research_gap}\n\n"
            full_text += f"**支撑论文**: {', '.join(p.supporting_papers)}\n\n"
            full_text += f"**反对证据**: {p.contradictory_evidence}\n\n"
            full_text += f"**可行性**: {p.feasibility}\n\n"
            full_text += f"**风险**: {p.risk}\n\n"
            full_text += f"**建议题目**: {p.possible_topic}\n\n---\n\n"

        return InnovationReport(
            title=result.get("title", "创新点分析报告"),
            innovation_points=points,
            full_text=full_text,
        )

    def _build_kg_gaps(self, kg: KnowledgeGraph, cards: list[PaperCard]) -> str:
        """Build KG gap analysis context."""
        paper_ids = {c.paper_id for c in cards}
        node_map = {n.node_id: n.label for n in kg.nodes}

        lines = []
        for e in kg.edges:
            if e.source_id in paper_ids or e.target_id in paper_ids:
                src = node_map.get(e.source_id, e.source_id)
                tgt = node_map.get(e.target_id, e.target_id)
                lines.append(f"- {src} --[{e.relation.value}]--> {tgt}")

        # Also include gap and innovation nodes
        gap_nodes = [
            n
            for n in kg.nodes
            if n.node_type.value in ("Gap", "InnovationPoint", "Limitation")
        ]
        for n in gap_nodes:
            lines.append(f"- [{n.node_type.value}] {n.label}")

        return "\n".join(lines[:50]) or "无图谱空白信息"
