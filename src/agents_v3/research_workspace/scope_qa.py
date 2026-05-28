"""基于 Scope 的 QA 服务 - 增强版"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    QAResponse,
    RetrievalScope,
    ScopeType,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage

# ── System Prompt ──────────────────────────────────────

QA_SYSTEM_PROMPT = """你是一个学术论文分析助手。根据提供的论文证据和上下文回答用户问题。

规则：
1. 你只能基于给定 Scope 和 Evidence 回答，不要使用外部知识
2. 不得引用输入中不存在的 paper_id 或 evidence_id
3. 如果证据不足，必须说明不确定性或拒答
4. 每个关键结论尽量绑定 evidence_id
5. 不要把图谱路径当作事实来源，路径只解释关系
6. 保持学术严谨性

输出格式（JSON）：
{
  "answer": "详细回答",
  "key_points": [
    {"text": "要点描述", "evidence_ids": ["ev1"], "paper_ids": ["p1"]}
  ],
  "supporting_evidence_ids": ["ev1"],
  "supporting_paper_ids": ["p1"],
  "source_quotes": [{"evidence_id": "ev1", "quote": "原文引用"}],
  "uncertainty": "不确定性说明",
  "confidence": 0.75,
  "suggested_actions": ["generate_literature_review"]
}"""

# ── 意图分类 ──────────────────────────────────────────

_INTENT_RULES: list[tuple[list[str], str]] = [
    (["综述", "文献综述", "研究现状"], "review_generation"),
    (["创新", "创新点", "选题", "论文题目"], "innovation_generation"),
    (["不足", "局限", "limitation", "缺陷", "短板"], "limitation_analysis"),
    (["方法", "method", "模型", "实验设计", "方法论"], "method_analysis"),
    (["比较", "对比", "区别", "优劣", "compare"], "method_compare"),
    (["发现", "结论", "结果", "finding", "成果"], "finding_summary"),
    (["gap", "空白", "未来工作", "创新机会", "研究方向"], "gap_analysis"),
    (["支撑", "证据", "是否能证明", "支持"], "evidence_check"),
    (["趋势", "演进", "年份", "近年来", "发展"], "trend_analysis"),
]

# 意图对证据字段的偏好
_INTENT_FIELD_PREFS: dict[str, list[str]] = {
    "summary": ["finding", "topic", "method"],
    "limitation_analysis": ["limitation", "future_work"],
    "method_analysis": ["method", "data_or_sample", "finding"],
    "method_compare": ["method", "finding", "limitation"],
    "finding_summary": ["finding", "topic"],
    "gap_analysis": ["future_work", "limitation", "finding"],
    "evidence_check": ["source_quote", "finding"],
    "trend_analysis": ["topic", "finding", "method"],
    "innovation_generation": ["future_work", "limitation", "finding"],
    "review_generation": ["finding", "topic", "method"],
}


class ScopeQAService:
    """基于选定范围的问答服务"""

    def __init__(self, storage: JSONStorage | None = None, llm_service: LLMService | None = None):
        self.storage = storage or get_storage()
        self.scope_service = RetrievalScopeService(storage=self.storage)
        self.llm = llm_service or get_llm_service()

    def answer(
        self, project_id: str, question: str, scope_payload: dict[str, Any]
    ) -> QAResponse:
        # 1. Resolve scope
        scope = self.scope_service.resolve(project_id, scope_payload)
        guard = self.scope_service.build_scope_guard(scope)

        # 2. Check empty scope
        empty_reason = scope.metadata.get("empty_reason", "")
        if empty_reason:
            return self._empty_scope_response(scope, empty_reason)

        # 3. Classify intent
        intent = self.classify_intent(question)

        # 4. Retrieve context
        context = self.retrieve_context(question, scope, intent)

        # 5. Check evidence scarcity
        evidence = context.get("evidence_records", [])
        if len(evidence) < 2:
            return QAResponse(
                answer="当前范围内可用证据不足，无法生成可靠回答。",
                intent=intent,
                scope_summary=scope.summary,
                uncertainty=f"仅找到 {len(evidence)} 条证据，需要至少 2 条",
                suggested_actions=["expand_scope", "build_evidence_table", "generate_paper_cards"],
                retrieval_diagnostics=context.get("diagnostics", {}),
            )

        # 6. Generate answer
        response = self.generate_answer(question, context, scope, intent)

        # 7. Validate against scope guard
        response = self._validate_response(response, guard)

        # 8. Save to history
        self._save_qa_history(project_id, question, scope_payload, scope, intent, context, response)

        logger.info(f"QA: intent={intent}, papers={len(scope.paper_ids)}, evidence={len(evidence)}")
        return response

    def classify_intent(self, question: str) -> str:
        q = question.lower()
        for keywords, intent in _INTENT_RULES:
            if any(kw in q for kw in keywords):
                return intent
        return "summary"

    def retrieve_context(
        self, question: str, scope: RetrievalScope, intent: str = "summary"
    ) -> dict[str, Any]:
        evidence_records = self.scope_service.to_evidence_records(scope)
        paper_cards = self.scope_service.to_paper_cards(scope)
        graph_context = self.scope_service.to_graph_context(scope)

        # Score and rank evidence
        scored = self._score_evidence(evidence_records, question, intent)
        top_evidence_dicts = [s["evidence"] for s in scored[:12]]

        diagnostics = {
            "candidate_evidence_count": len(evidence_records),
            "selected_evidence_count": len(top_evidence_dicts),
            "top_score": scored[0]["score"] if scored else 0,
            "intent": intent,
        }

        return {
            "scope_summary": scope.summary,
            "paper_count": len(scope.paper_ids),
            "evidence_records": top_evidence_dicts,
            "all_evidence_ids": [e.evidence_id for e in evidence_records],
            "paper_cards": paper_cards[:8],
            "graph_nodes": graph_context.get("nodes", [])[:20],
            "graph_edges": graph_context.get("edges", [])[:30],
            "diagnostics": diagnostics,
        }

    def _score_evidence(
        self, evidence_records: list, question: str, intent: str
    ) -> list[dict]:
        """对证据打分排序"""
        q_words = set(re.findall(r"\w+", question.lower()))
        preferred_fields = _INTENT_FIELD_PREFS.get(intent, ["finding", "topic"])

        scored = []
        for ev in evidence_records:
            score = 0.0
            ev_dict = ev.model_dump() if hasattr(ev, "model_dump") else ev

            # Intent field match
            for field in preferred_fields:
                val = ev_dict.get(field, "")
                if val and val != "unknown":
                    score += 4

            # Keyword match in finding/limitation/future_work
            for field in ("finding", "limitation", "future_work"):
                val = (ev_dict.get(field, "") or "").lower()
                if val and val != "unknown":
                    matches = sum(1 for w in q_words if w in val)
                    score += min(matches, 3)

            # Keyword match in topic/method
            for field in ("topic", "method"):
                val = (ev_dict.get(field, "") or "").lower()
                if val and val != "unknown":
                    if any(w in val for w in q_words):
                        score += 2

            # Source quote bonus
            if ev_dict.get("source_quote"):
                score += 1

            # Evidence strength
            strength = ev_dict.get("evidence_strength", "medium")
            if strength == "high":
                score += 1
            elif strength == "low":
                score -= 1

            scored.append({"evidence": ev_dict, "score": score})

        scored.sort(key=lambda x: -x["score"])
        return scored

    def generate_answer(
        self,
        question: str,
        context: dict[str, Any],
        scope: RetrievalScope,
        intent: str,
    ) -> QAResponse:
        evidence = context.get("evidence_records", [])
        paper_count = context.get("paper_count", 0)

        # Build structured prompt
        evidence_text = self._build_evidence_text(evidence)
        cards_text = self._build_cards_text(context.get("paper_cards", []))
        graph_text = self._build_graph_text(context.get("graph_nodes", []), context.get("graph_edges", []))

        user_prompt = f"""[Scope]
{context['scope_summary']}
论文数量：{paper_count}
允许的证据 IDs：{', '.join(context.get('all_evidence_ids', [])[:20])}

[Question]
{question}
意图：{intent}

[Evidence]
{evidence_text}

[Paper Cards]
{cards_text}

[Graph Context]
{graph_text}

请基于以上证据回答问题。每个关键结论请绑定 evidence_id。如果证据不足请说明不确定性。"""

        try:
            result = self.llm.invoke_json(QA_SYSTEM_PROMPT, user_prompt)
            answer = result.get("answer", "")
            uncertainty = result.get("uncertainty", "该结论仅基于当前选择范围，不代表全领域。")
            confidence = result.get("confidence", 0.5)

            supporting_papers = result.get("supporting_paper_ids", [])
            evidence_ids = result.get("supporting_evidence_ids", [])
            source_quotes = result.get("source_quotes", [])
            key_points = result.get("key_points", [])
            suggested = result.get("suggested_actions", [])

            # If LLM didn't return proper IDs, use retrieved
            if not supporting_papers:
                supporting_papers = list({e.get("paper_id") for e in evidence if e.get("paper_id")})
            if not evidence_ids:
                evidence_ids = [e.get("evidence_id") for e in evidence if e.get("evidence_id")]

        except Exception as e:
            logger.error(f"LLM QA failed: {e}")
            answer = self._fallback_answer(question, context, intent)
            uncertainty = "该结论基于规则提取，可能不够准确。请尝试更具体的问题。"
            confidence = 0.3
            supporting_papers = list({e.get("paper_id") for e in evidence if e.get("paper_id")})
            evidence_ids = [e.get("evidence_id") for e in evidence if e.get("evidence_id")]
            source_quotes = []
            key_points = []
            suggested = self._build_suggested_actions(intent)

        return QAResponse(
            answer=answer,
            intent=intent,
            scope_summary=scope.summary,
            supporting_papers=supporting_papers[:10],
            evidence_records=evidence_ids[:10],
            graph_paths=[],
            uncertainty=uncertainty,
            suggested_actions=suggested or self._build_suggested_actions(intent),
            retrieval_diagnostics=context.get("diagnostics", {}),
            confidence=confidence,
        )

    def _validate_response(
        self, response: QAResponse, guard: dict[str, Any]
    ) -> QAResponse:
        """校验回答是否越界"""
        warnings = []
        allowed_papers = guard.get("allowed_paper_ids", set())
        allowed_evidence = guard.get("allowed_evidence_ids", set())

        # Check papers
        valid_papers = []
        for pid in response.supporting_papers:
            if pid in allowed_papers:
                valid_papers.append(pid)
            else:
                warnings.append(f"paper_out_of_scope:{pid}")
        response.supporting_papers = valid_papers

        # Check evidence
        valid_evidence = []
        for eid in response.evidence_records:
            if eid in allowed_evidence:
                valid_evidence.append(eid)
            else:
                warnings.append(f"evidence_out_of_scope:{eid}")
        response.evidence_records = valid_evidence

        # If all references were removed, degrade
        if warnings and not valid_evidence:
            response.uncertainty = "回答中的引用均超出当前范围，已移除。请扩大范围后重试。"
            response.confidence = max(0.1, response.confidence - 0.3)

        response.validation_warnings = warnings
        return response

    def _empty_scope_response(self, scope: RetrievalScope, empty_reason: str) -> QAResponse:
        """空范围拒答"""
        messages = {
            "no_included_papers": "当前项目没有已纳入的论文。请先导入论文。",
            "no_valid_selected_papers": "选中的论文均无效（可能被排除或不属于当前项目）。",
            "no_matching_topic": "当前范围内没有匹配所选主题的论文。",
            "no_matching_method": "当前范围内没有匹配所选方法的论文。",
            "no_matching_graph_subgraph": "图谱子图未找到相关论文。请先构建知识图谱。",
            "invalid_time_range": "年份范围无效。",
            "no_papers_after_year_filter": "所选年份范围内没有论文。",
        }
        return QAResponse(
            answer=messages.get(empty_reason, "当前范围为空，无法回答。"),
            intent="scope_empty",
            scope_summary=scope.summary,
            uncertainty=empty_reason,
            suggested_actions=scope.metadata.get("suggested_actions", []),
        )

    # ── 上下文构建 ──────────────────────────────────

    def _build_evidence_text(self, evidence: list[dict]) -> str:
        if not evidence:
            return "无可用证据"
        parts = []
        for e in evidence[:12]:
            eid = e.get("evidence_id", "?")
            pid = e.get("paper_id", "?")
            line = f"[{eid}] 论文 {pid}"
            if e.get("topic"):
                line += f" | 主题:{e['topic']}"
            if e.get("method") and e["method"] != "unknown":
                line += f" | 方法:{e['method']}"
            if e.get("finding") and e["finding"] != "unknown":
                line += f" | 发现:{e['finding']}"
            if e.get("limitation") and e["limitation"] != "unknown":
                line += f" | 局限:{e['limitation']}"
            if e.get("future_work") and e["future_work"] != "unknown":
                line += f" | 未来:{e['future_work']}"
            if e.get("source_quote"):
                line += f" | 引用:{e['source_quote'][:80]}"
            parts.append(line)
        return "\n".join(parts)

    def _build_cards_text(self, cards: list[dict]) -> str:
        if not cards:
            return "无可用卡片"
        parts = []
        for c in cards[:8]:
            pid = c.get("paper_id", "?")
            line = f"[{pid}] {c.get('title', '未知')}"
            if c.get("research_question") and c["research_question"] != "unknown":
                line += f" | 问题:{c['research_question'][:50]}"
            if c.get("method") and c["method"] != "unknown":
                line += f" | 方法:{c['method']}"
            parts.append(line)
        return "\n".join(parts)

    def _build_graph_text(self, nodes: list[dict], edges: list[dict]) -> str:
        if not nodes and not edges:
            return "无图谱上下文"
        parts = []
        for e in edges[:10]:
            src = e.get("source_id", "?").split(":")[-1][:15]
            tgt = e.get("target_id", "?").split(":")[-1][:15]
            rel = e.get("edge_type", "?")
            parts.append(f"{src} --{rel}--> {tgt}")
        return "\n".join(parts) if parts else "无图谱关系"

    # ── Fallback ──────────────────────────────────

    def _fallback_answer(self, question: str, context: dict[str, Any], intent: str) -> str:
        evidence = context.get("evidence_records", [])

        if intent == "limitation_analysis":
            items = [e["limitation"] for e in evidence if e.get("limitation") and e["limitation"] != "unknown"]
            if items:
                return "根据当前范围内的论文，主要研究不足包括：\n" + "\n".join(f"- {l}" for l in items[:5])
            return "当前范围内未找到明确的研究不足记录。"

        if intent == "method_analysis":
            items = list({e["method"] for e in evidence if e.get("method") and e["method"] != "unknown"})
            if items:
                return "当前范围内主要研究方法包括：\n" + "\n".join(f"- {m}" for m in items[:5])
            return "当前范围内未找到明确的研究方法记录。"

        if intent == "gap_analysis":
            items = [e.get("future_work", "") for e in evidence if e.get("future_work") and e["future_work"] != "unknown"]
            if items:
                return "当前范围内的研究空白和未来方向：\n" + "\n".join(f"- {f}" for f in items[:5])
            return "当前范围内未找到明确的研究空白记录。"

        findings = [e["finding"] for e in evidence if e.get("finding") and e["finding"] != "unknown"]
        if findings:
            return "当前范围内的主要研究发现：\n" + "\n".join(f"- {f}" for f in findings[:5])
        return "当前范围内未找到明确的研究发现。请尝试更具体的问题。"

    def _build_suggested_actions(self, intent: str) -> list[str]:
        actions = []
        if intent in ("innovation_generation", "gap_analysis"):
            actions.append("generate_innovation_report")
        if intent in ("review_generation", "summary"):
            actions.append("generate_literature_review")
        if not actions:
            actions = ["generate_literature_review", "generate_innovation_report"]
        actions.append("expand_to_project_scope")
        return actions

    # ── QA 历史 ──────────────────────────────────

    def _save_qa_history(
        self, project_id: str, question: str, scope_payload: dict,
        scope: RetrievalScope, intent: str, context: dict, response: QAResponse,
    ) -> None:
        qa_id = f"qa_{uuid.uuid4().hex[:8]}"
        record = {
            "qa_id": qa_id,
            "project_id": project_id,
            "question": question,
            "scope_payload": scope_payload,
            "scope_type": scope.scope_type.value,
            "intent": intent,
            "paper_count": len(scope.paper_ids),
            "evidence_count": len(context.get("evidence_records", [])),
            "supporting_papers": response.supporting_papers,
            "supporting_evidence": response.evidence_records,
            "confidence": response.confidence,
            "validation_warnings": response.validation_warnings,
            "created_at": datetime.now().isoformat(),
        }
        self.storage.upsert_item("qa_history", qa_id, record)
