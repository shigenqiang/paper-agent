"""
Scoped QA system for Agent v3.

Supports scope-based answering over selected papers, topics, or graph subgraphs.
Every answer includes: answer, scope, supporting evidence, uncertainty, next actions.
"""

from __future__ import annotations

import logging

from src.agent_v3.agents.base import BaseAgent
from src.agent_v3.core.config import AppConfig
from src.agent_v3.models import (
    EvidenceRecord,
    KnowledgeGraph,
    PaperCard,
    QAAnswer,
    QAQuestion,
)

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """你是一个学术论文分析QA专家。你需要基于给定范围内的论文、证据表和知识图谱来回答问题。

你的回答必须：
1. 基于给定的证据，不要编造
2. 明确指出信息来源
3. 如果证据不足，诚实说明不确定性
4. 建议可能的后续操作

请严格按照JSON格式输出。"""

QA_PROMPT = """请基于以下范围内的论文信息回答问题。

## 研究范围
{scope_description}

## 可用论文卡片
{cards_text}

## 证据表
{evidence_text}

## 知识图谱信息
{kg_text}

## 问题
{question}

请输出JSON格式：
{{
  "answer": "详细回答",
  "supporting_evidence": ["证据1: 引用具体论文和发现", "证据2: ..."],
  "uncertainty": "当前证据的不足或不确定性说明",
  "next_actions": ["建议操作1", "建议操作2"]
}}

注意：
- 回答必须基于给定范围内的证据
- 引用具体论文标题和发现
- 如果证据不足，明确说明"""


class ScopedQA(BaseAgent):
    """Scope-based QA over paper library."""

    def __init__(self, config: AppConfig):
        super().__init__(config, name="scoped_qa")

    async def answer(
        self,
        question: QAQuestion,
        cards: list[PaperCard],
        evidence: list[EvidenceRecord],
        kg: KnowledgeGraph,
    ) -> QAAnswer:
        """
        Answer a question within a given scope.

        Args:
            question: QA question with optional scope
            cards: All paper cards in the project
            evidence: All evidence records
            kg: Project knowledge graph

        Returns:
            QAAnswer with answer, evidence, and next actions
        """
        # Filter by scope
        scope = question.scope
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

        if scope and scope.selected_topic_ids:
            topic_evidence = [
                e for e in filtered_evidence if e.topic in scope.selected_topic_ids
            ]
            if topic_evidence:
                filtered_evidence = topic_evidence
                scope_desc += f"，主题: {', '.join(scope.selected_topic_ids)}"

        if scope and scope.time_range:
            start, end = scope.time_range
            filtered_cards = [
                c for c in filtered_cards if c.year and start <= c.year <= end
            ]
            scope_desc += f"，时间范围: {start}-{end}"

        # Build context
        cards_text = (
            "\n\n".join(
                f"### {c.title}\n"
                f"- 研究问题: {c.research_question}\n"
                f"- 方法: {c.method}\n"
                f"- 发现: {'; '.join(c.key_findings[:3])}\n"
                f"- 局限: {'; '.join(c.limitations[:2])}"
                for c in filtered_cards
            )
            or "无论文信息"
        )

        evidence_text = (
            "\n".join(
                f"- [{e.evidence_strength}] {e.finding} (来源: {e.paper_id}, 主题: {e.topic})"
                for e in filtered_evidence[:20]
            )
            or "无证据记录"
        )

        # Get relevant KG subgraph
        kg_text = self._build_kg_context(kg, filtered_cards)

        prompt = QA_PROMPT.format(
            scope_description=scope_desc,
            cards_text=cards_text,
            evidence_text=evidence_text,
            kg_text=kg_text,
            question=question.question,
        )

        try:
            result = await self.call_llm(prompt, QA_SYSTEM_PROMPT, json_mode=True)
        except Exception as e:
            logger.error(f"QA failed: {e}")
            return QAAnswer(
                answer=f"回答生成失败: {e}",
                scope_description=scope_desc,
                uncertainty="由于技术错误无法生成回答",
            )

        return QAAnswer(
            answer=result.get("answer", ""),
            scope_description=scope_desc,
            supporting_evidence=result.get("supporting_evidence", []),
            uncertainty=result.get("uncertainty", ""),
            next_actions=result.get("next_actions", []),
        )

    def _build_kg_context(self, kg: KnowledgeGraph, cards: list[PaperCard]) -> str:
        """Build KG context text for QA."""
        paper_ids = {c.paper_id for c in cards}
        relevant_nodes = [n for n in kg.nodes if n.node_id in paper_ids]
        relevant_edges = [
            e for e in kg.edges if e.source_id in paper_ids or e.target_id in paper_ids
        ]

        if not relevant_nodes and not relevant_edges:
            return "无知识图谱信息"

        node_map = {n.node_id: n.label for n in kg.nodes}
        lines = []
        for e in relevant_edges[:30]:
            src = node_map.get(e.source_id, e.source_id)
            tgt = node_map.get(e.target_id, e.target_id)
            lines.append(f"- {src} --[{e.relation.value}]--> {tgt}")

        return "\n".join(lines) or "无相关图谱关系"
