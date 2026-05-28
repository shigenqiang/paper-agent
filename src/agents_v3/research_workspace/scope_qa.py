"""基于 Scope 的 QA 服务 - LLM 驱动"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm_service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    QARequest,
    QAResponse,
    RetrievalScope,
    ScopeType,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import get_storage

QA_SYSTEM_PROMPT = """你是一个学术论文分析助手。根据提供的论文证据和上下文回答用户问题。

要求：
1. 回答必须基于提供的证据，不要编造
2. 如果证据不足，明确说明
3. 引用具体的论文和发现
4. 保持学术严谨性

输出格式（JSON）：
{
  "answer": "详细回答",
  "key_points": ["要点1", "要点2"],
  "uncertainty": "不确定声明"
}"""


class ScopeQAService:
    """基于选定范围的问答服务"""

    def __init__(self, llm_service: LLMService | None = None):
        self.storage = get_storage()
        self.scope_service = RetrievalScopeService()
        self.llm = llm_service or get_llm_service()

    def answer(
        self, project_id: str, question: str, scope_payload: dict[str, Any]
    ) -> QAResponse:
        scope = self.scope_service.resolve(project_id, scope_payload)
        intent = self.classify_intent(question)
        context = self.retrieve_context(question, scope)
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
        evidence_records = self.scope_service.to_evidence_records(scope)
        paper_cards = []
        for pid in scope.paper_ids:
            cards = self.storage.query("paper_cards", {"paper_id": pid})
            paper_cards.extend(cards)

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
        # 构建证据摘要
        evidence_summary = self._build_evidence_summary(context)

        user_prompt = f"""范围：{context['scope_summary']}
论文数量：{context['paper_count']}

证据摘要：
{evidence_summary}

用户问题：{question}

请基于以上证据回答问题。"""

        try:
            result = self.llm.invoke_json(QA_SYSTEM_PROMPT, user_prompt)
            answer = result.get("answer", "")
            uncertainty = result.get("uncertainty", "该结论仅基于当前选择范围，不代表全领域。")
        except Exception as e:
            logger.error(f"LLM QA failed: {e}")
            answer = self._fallback_answer(question, context, intent)
            uncertainty = "该结论基于规则提取，可能不够准确。"

        supporting_papers = list({e.get("paper_id") for e in context.get("evidence_records", []) if e.get("paper_id")})
        evidence_ids = [e.get("evidence_id") for e in context.get("evidence_records", []) if e.get("evidence_id")]

        return QAResponse(
            answer=answer,
            intent=intent,
            scope_summary=f"基于当前选择的 {len(scope.paper_ids)} 篇论文",
            supporting_papers=supporting_papers[:10],
            evidence_records=evidence_ids[:10],
            graph_paths=[],
            uncertainty=uncertainty,
            suggested_actions=self._build_suggested_actions(intent),
        )

    def _build_evidence_summary(self, context: dict[str, Any]) -> str:
        parts = []
        evidence = context.get("evidence_records", [])

        for e in evidence[:20]:  # 限制数量
            part = f"- 论文 {e.get('paper_id', '?')}"
            if e.get("topic"):
                part += f" | 主题: {e['topic']}"
            if e.get("method"):
                part += f" | 方法: {e['method']}"
            if e.get("finding") and e["finding"] != "unknown":
                part += f" | 发现: {e['finding']}"
            if e.get("limitation") and e["limitation"] != "unknown":
                part += f" | 局限: {e['limitation']}"
            parts.append(part)

        return "\n".join(parts) if parts else "无可用证据"

    def _fallback_answer(self, question: str, context: dict[str, Any], intent: str) -> str:
        """LLM 失败时的降级回答"""
        evidence = context.get("evidence_records", [])

        if intent == "limitation_analysis":
            limitations = [e["limitation"] for e in evidence if e.get("limitation") and e["limitation"] != "unknown"]
            if limitations:
                return "根据当前选择范围内的论文，主要研究不足包括：\n" + "\n".join(f"- {l}" for l in limitations[:5])
            return "在当前选择范围内，未找到明确的研究不足记录。"

        if intent == "method_analysis":
            methods = list({e["method"] for e in evidence if e.get("method") and e["method"] != "unknown"})
            if methods:
                return "根据当前选择范围内的论文，主要研究方法包括：\n" + "\n".join(f"- {m}" for m in methods[:5])
            return "在当前选择范围内，未找到明确的研究方法记录。"

        findings = [e["finding"] for e in evidence if e.get("finding") and e["finding"] != "unknown"]
        if findings:
            return "根据当前选择范围内的论文，主要研究发现包括：\n" + "\n".join(f"- {f}" for f in findings[:5])
        return "在当前选择范围内，未找到明确的研究发现。请尝试更具体的问题。"

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
