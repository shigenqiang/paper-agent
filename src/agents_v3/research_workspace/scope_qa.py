"""基于 Scope 的 QA 服务"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    QARequest,
    QAResponse,
    RetrievalScope,
    ScopeType,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import get_storage


class ScopeQAService:
    """基于选定范围的问答服务"""

    def __init__(self):
        self.storage = get_storage()
        self.scope_service = RetrievalScopeService()

    def answer(
        self, project_id: str, question: str, scope_payload: dict[str, Any]
    ) -> QAResponse:
        # 1. Resolve scope
        scope = self.scope_service.resolve(project_id, scope_payload)

        # 2. Classify intent
        intent = self.classify_intent(question)

        # 3. Retrieve context
        context = self.retrieve_context(question, scope)

        # 4. Generate answer
        response = self.generate_answer(question, context, scope, intent)

        logger.info(f"QA: intent={intent}, papers={len(scope.paper_ids)}")
        return response

    def classify_intent(self, question: str) -> str:
        q = question.lower()
        if "综述" in q or "文献综述" in q:
            return "review_generation"
        if "创新" in q or "创新点" in q:
            return "innovation_generation"
        if "不足" in q or "局限" in q:
            return "limitation_analysis"
        if "方法" in q:
            return "method_analysis"
        if "比较" in q or "区别" in q:
            return "comparison"
        return "summary"

    def retrieve_context(self, question: str, scope: RetrievalScope) -> dict[str, Any]:
        # Get evidence records
        evidence_records = self.scope_service.to_evidence_records(scope)

        # Get paper cards
        paper_cards = []
        for pid in scope.paper_ids:
            cards = self.storage.query("paper_cards", {"paper_id": pid})
            paper_cards.extend(cards)

        # Get graph context
        graph_context = self.scope_service.to_graph_context(scope)

        return {
            "scope_summary": scope.summary,
            "paper_count": len(scope.paper_ids),
            "evidence_records": [e.model_dump() for e in evidence_records],
            "paper_cards": paper_cards,
            "graph_nodes": graph_context.get("nodes", []),
            "graph_edges": graph_context.get("edges", []),
        }

    def generate_answer(
        self,
        question: str,
        context: dict[str, Any],
        scope: RetrievalScope,
        intent: str,
    ) -> QAResponse:
        evidence = context.get("evidence_records", [])
        paper_cards = context.get("paper_cards", [])

        # Build answer based on intent
        if intent == "limitation_analysis":
            answer = self._answer_limitations(evidence, paper_cards)
        elif intent == "method_analysis":
            answer = self._answer_methods(evidence, paper_cards)
        elif intent == "comparison":
            answer = self._answer_comparison(evidence, paper_cards)
        else:
            answer = self._answer_summary(evidence, paper_cards)

        # Build suggested actions
        suggested_actions = self._build_suggested_actions(intent)

        # Build supporting evidence
        supporting_papers = list({e.get("paper_id") for e in evidence if e.get("paper_id")})
        evidence_ids = [e.get("evidence_id") for e in evidence if e.get("evidence_id")]

        return QAResponse(
            answer=answer,
            intent=intent,
            scope_summary=f"基于当前选择的 {len(scope.paper_ids)} 篇论文",
            supporting_papers=supporting_papers[:10],
            evidence_records=evidence_ids[:10],
            graph_paths=[],
            uncertainty="该结论仅基于当前选择范围，不代表全领域。",
            suggested_actions=suggested_actions,
        )

    def _answer_limitations(
        self, evidence: list[dict], cards: list[dict]
    ) -> str:
        limitations = []
        for e in evidence:
            if e.get("limitation") and e["limitation"] != "unknown":
                limitations.append(e["limitation"])

        if not limitations:
            return "在当前选择范围内，未找到明确的研究不足记录。"

        unique = list(dict.fromkeys(limitations))[:5]
        parts = ["根据当前选择范围内的论文，主要研究不足包括：\n"]
        for i, lim in enumerate(unique, 1):
            parts.append(f"{i}. {lim}")
        return "\n".join(parts)

    def _answer_methods(
        self, evidence: list[dict], cards: list[dict]
    ) -> str:
        methods = []
        for e in evidence:
            if e.get("method") and e["method"] != "unknown":
                methods.append(e["method"])

        if not methods:
            return "在当前选择范围内，未找到明确的研究方法记录。"

        unique = list(dict.fromkeys(methods))[:5]
        parts = ["根据当前选择范围内的论文，主要研究方法包括：\n"]
        for i, m in enumerate(unique, 1):
            parts.append(f"{i}. {m}")
        return "\n".join(parts)

    def _answer_comparison(
        self, evidence: list[dict], cards: list[dict]
    ) -> str:
        if len(cards) < 2:
            return "需要至少 2 篇论文才能进行比较分析。"

        parts = ["根据当前选择范围内的论文比较：\n"]
        for card in cards[:3]:
            title = card.get("title", card.get("paper_id", "未知"))
            method = card.get("method", "unknown")
            parts.append(f"- {title}: 方法={method}")
        return "\n".join(parts)

    def _answer_summary(
        self, evidence: list[dict], cards: list[dict]
    ) -> str:
        findings = []
        for e in evidence:
            if e.get("finding") and e["finding"] != "unknown":
                findings.append(e["finding"])

        if not findings:
            return "在当前选择范围内，未找到明确的研究发现。请尝试更具体的问题。"

        unique = list(dict.fromkeys(findings))[:5]
        parts = ["根据当前选择范围内的论文，主要研究发现包括：\n"]
        for i, f in enumerate(unique, 1):
            parts.append(f"{i}. {f}")
        return "\n".join(parts)

    def _build_suggested_actions(self, intent: str) -> list[str]:
        actions = []
        if intent == "innovation_generation" or "创新" in intent:
            actions.append("generate_innovation_report")
        if intent == "review_generation" or "综述" in intent:
            actions.append("generate_literature_review")
        if not actions:
            actions = ["generate_literature_review", "generate_innovation_report"]
        actions.append("expand_to_project_scope")
        return actions
