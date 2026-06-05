"""基于 Scope 的 QA 服务 - 增强版"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    QALLMOutput,
    QAResponse,
    RetrievalScope,
    ScopeType,
    ScoredEvidence,
)
from src.agents_v3.research_workspace.services.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import get_storage

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
    (["不足", "局限", "limitation", "缺陷", "短板"], "limitation_analysis"),
    (["比较", "对比", "区别", "优劣", "compare"], "method_compare"),
    (["方法", "method", "模型", "实验设计", "方法论"], "method_analysis"),
    (["发现", "结论", "结果", "finding", "成果"], "finding_summary"),
    (["gap", "空白", "未来工作", "创新机会", "研究方向"], "gap_analysis"),
    (["创新", "创新点", "选题", "论文题目"], "innovation_generation"),
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

    def __init__(
        self,
        storage=None,
        llm_service: LLMService | None = None,
        scope_service: RetrievalScopeService | None = None,
        graph_service=None,
    ):
        self.storage = storage or get_storage()
        self.scope_service = scope_service or RetrievalScopeService(storage=self.storage)
        self.llm = llm_service or get_llm_service()
        self._graph_service = graph_service

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

        # 4b. GraphRAG routing
        graph_answer = self._graphrag_search(project_id, question, scope, intent, context)

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
        response = self.generate_answer(question, context, scope, intent, graph_answer)

        # 6b. Review-Revise
        response = self._qa_review_revise(question, context, scope, intent, response)

        # 7. Validate against scope guard + context
        response = self._validate_response(response, guard, context)

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

    def _graphrag_search(
        self, project_id: str, question: str, scope: RetrievalScope,
        intent: str, context: dict[str, Any],
    ) -> dict | None:
        """根据 intent 路由到 GraphRAG global/local search"""
        if len(scope.paper_ids) < 3:
            return None

        try:
            from src.agents_v3.research_workspace.services.graph_service import GraphService
            gs = GraphService(storage=self.storage)

            # Global search for broad summary/gap questions
            if intent in ("summary", "gap_analysis", "review_generation", "trend_analysis"):
                gs.detect_communities(project_id)
                gs.build_community_summaries(project_id)
                result = gs.global_search(project_id, question)
                if result.get("answer"):
                    return result

            # Local search for method/comparison questions
            elif intent in ("method_analysis", "method_compare", "finding_summary"):
                seed_ids: list[str] = []
                for ev in context.get("evidence_records", [])[:5]:
                    topic = ev.get("topic", "") if hasattr(ev, "get") else getattr(ev, "topic", "")
                    method = ev.get("method", "") if hasattr(ev, "get") else getattr(ev, "method", "")
                    if topic:
                        seed_ids.append(f"topic:{topic}")
                    if method and method.lower() not in ("unknown", ""):
                        seed_ids.append(f"method:{method}")
                if seed_ids:
                    result = gs.local_search(project_id, question, seed_ids[:5])
                    if result.get("answer"):
                        return result

        except Exception as e:
            logger.debug(f"GraphRAG search skipped: {e}")

        return None

    def retrieve_context(
        self, question: str, scope: RetrievalScope, intent: str = "summary"
    ) -> dict[str, Any]:
        evidence_records = self.scope_service.to_evidence_records(scope)
        paper_cards = self.scope_service.to_paper_cards(scope)
        graph_context = self.scope_service.to_graph_context(scope)

        # Score and rank evidence
        scored = self._score_evidence(evidence_records, question, intent)

        # Hybrid retrieval: vector search complement
        vector_scored = self._vector_retrieve_evidence(question, scope)
        if vector_scored:
            scored = self._merge_scored(scored, vector_scored)

        top_k = scored[:12]
        top_evidence_dicts = [s.model_dump() for s in top_k]

        # 统计 matched_fields
        field_counts: dict[str, int] = {}
        low_quality_count = 0
        for s in scored:
            if s.evidence_strength == "low":
                low_quality_count += 1
            for f in s.matched_fields:
                field_counts[f] = field_counts.get(f, 0) + 1

        diagnostics = {
            "candidate_evidence_count": len(evidence_records),
            "selected_evidence_count": len(top_k),
            "top_score": top_k[0].score if top_k else 0,
            "min_selected_score": top_k[-1].score if top_k else 0,
            "low_quality_count": low_quality_count,
            "matched_fields": field_counts,
            "intent": intent,
        }

        return {
            "scope_summary": scope.summary,
            "paper_count": len(scope.paper_ids),
            "evidence_records": top_evidence_dicts,
            "scored_evidence": top_k,
            "all_evidence_ids": [e.evidence_id for e in evidence_records],
            "paper_cards": paper_cards[:8],
            "graph_nodes": graph_context.get("nodes", [])[:20],
            "graph_edges": graph_context.get("edges", [])[:30],
            "diagnostics": diagnostics,
        }

    def _score_evidence(
        self, evidence_records: list, question: str, intent: str
    ) -> list[ScoredEvidence]:
        """对证据打分排序，返回 ScoredEvidence 列表"""
        q_words = set(re.findall(r"\w+", question.lower()))
        preferred_fields = _INTENT_FIELD_PREFS.get(intent, ["finding", "topic"])

        scored: list[ScoredEvidence] = []
        for ev in evidence_records:
            ev_dict = ev.model_dump() if hasattr(ev, "model_dump") else ev

            # 跳过 rejected evidence
            status = ev_dict.get("review_status", "")
            if status == "rejected":
                continue

            score = 0.0
            breakdown: dict[str, float] = {}
            matched: list[str] = []

            # Intent field match
            for field in preferred_fields:
                val = ev_dict.get(field, "")
                if val and val != "unknown":
                    score += 4
                    breakdown["intent_field"] = breakdown.get("intent_field", 0) + 4
                    matched.append(field)

            # Keyword match in finding/limitation/future_work
            for field in ("finding", "limitation", "future_work"):
                val = (ev_dict.get(field, "") or "").lower()
                if val and val != "unknown":
                    matches = sum(1 for w in q_words if w in val)
                    kw_score = min(matches, 3)
                    if kw_score:
                        score += kw_score
                        breakdown["keyword"] = breakdown.get("keyword", 0) + kw_score
                        if field not in matched:
                            matched.append(field)

            # Keyword match in topic/method
            for field in ("topic", "method"):
                val = (ev_dict.get(field, "") or "").lower()
                if val and val != "unknown":
                    if any(w in val for w in q_words):
                        score += 2
                        breakdown["topic_method"] = breakdown.get("topic_method", 0) + 2
                        if field not in matched:
                            matched.append(field)

            # Source quote bonus
            if ev_dict.get("source_quote"):
                score += 1
                breakdown["source_quote"] = 1

            # Evidence strength
            strength = ev_dict.get("evidence_strength", "medium")
            if strength == "high":
                score += 1
                breakdown["strength"] = 1
            elif strength == "low":
                score -= 2
                breakdown["strength"] = -2

            # 低质量降权
            if status == "low":
                score -= 2
                breakdown["low_quality"] = -2

            scored.append(ScoredEvidence(
                evidence_id=ev_dict.get("evidence_id", ""),
                paper_id=ev_dict.get("paper_id", ""),
                score=score,
                score_breakdown=breakdown,
                matched_fields=matched,
                evidence_type=self._infer_evidence_type(ev_dict),
                source_quote=ev_dict.get("source_quote", ""),
                evidence_strength=strength,
            ))

        scored.sort(key=lambda x: -x.score)
        return scored

    def _vector_retrieve_evidence(self, question: str, scope: RetrievalScope) -> list[ScoredEvidence]:
        """使用 HierarchicalRetriever 进行向量检索"""
        try:
            from src.agents_v3.research_workspace.services.hierarchical_retriever import HierarchicalRetriever
            retriever = HierarchicalRetriever(storage=self.storage)
            results, _diag = retriever.retrieve(
                query_text=question,
                project_id=scope.project_id,
                top_k_papers=5, top_k_sections=10, top_k_chunks=15,
                paper_ids=scope.paper_ids if scope.paper_ids else None,
            )
            # 批量查询命中论文的 evidence records
            hit_paper_ids = list({r.paper_id for r in results})
            all_evs = self.storage.query("evidence_records", {"paper_id": hit_paper_ids}) if hit_paper_ids else []
            ev_by_paper: dict[str, dict] = {}
            for ev in all_evs:
                pid = ev.get("paper_id", "")
                if pid not in ev_by_paper:
                    ev_by_paper[pid] = ev

            evidence: list[ScoredEvidence] = []
            for r in results:
                ev = ev_by_paper.get(r.paper_id)
                if ev:
                    evidence.append(ScoredEvidence(
                        evidence_id=ev.get("evidence_id", r.chunk_id),
                        paper_id=r.paper_id,
                        finding=ev.get("finding", ""),
                        topic=ev.get("topic", ""),
                        method=ev.get("method", ""),
                        score=r.dense_score,
                        evidence_strength=ev.get("evidence_strength", "medium"),
                    ))
            return evidence
        except Exception as e:
            logger.debug(f"Vector retrieval skipped: {e}")
            return []

    @staticmethod
    def _merge_scored(keyword_scored: list[ScoredEvidence], vector_scored: list[ScoredEvidence]) -> list[ScoredEvidence]:
        """合并关键词和向量评分结果（RRF 风格）"""
        seen: dict[str, dict] = {}
        for i, s in enumerate(keyword_scored):
            seen[s.evidence_id] = {"kw_rank": i, "vec_rank": len(keyword_scored), "obj": s}
        for i, s in enumerate(vector_scored):
            if s.evidence_id in seen:
                seen[s.evidence_id]["vec_rank"] = i
            else:
                seen[s.evidence_id] = {"kw_rank": len(keyword_scored), "vec_rank": i, "obj": s}
        k = 60
        for v in seen.values():
            v["rrf"] = 1.0 / (k + v["kw_rank"] + 1) + 1.0 / (k + v["vec_rank"] + 1)
        sorted_items = sorted(seen.values(), key=lambda x: -x["rrf"])
        return [v["obj"] for v in sorted_items]

    @staticmethod
    def _infer_evidence_type(ev_dict: dict) -> str:
        if ev_dict.get("finding") and ev_dict["finding"] != "unknown":
            return "finding"
        if ev_dict.get("limitation") and ev_dict["limitation"] != "unknown":
            return "limitation"
        if ev_dict.get("future_work") and ev_dict["future_work"] != "unknown":
            return "future_work"
        if ev_dict.get("method") and ev_dict["method"] != "unknown":
            return "method"
        return ""

    def generate_answer(
        self,
        question: str,
        context: dict[str, Any],
        scope: RetrievalScope,
        intent: str,
        graph_answer: dict | None = None,
    ) -> QAResponse:
        evidence = context.get("evidence_records", [])
        paper_count = context.get("paper_count", 0)

        # Build structured prompt (compress evidence to fit token budget)
        compressed_evidence = self._compress_evidence(evidence)
        evidence_text = self._build_evidence_text(compressed_evidence)
        cards_text = self._build_cards_text(context.get("paper_cards", []))
        graph_text = self._build_graph_text(context.get("graph_nodes", []), context.get("graph_edges", []))

        # GraphRAG context
        graphrag_section = ""
        if graph_answer and graph_answer.get("answer"):
            graphrag_section = f"\n[GraphRAG 分析]\n{graph_answer['answer'][:500]}\n"

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
{graphrag_section}
请基于以上证据回答问题。每个关键结论请绑定 evidence_id。如果证据不足请说明不确定性。"""

        json_parse_failed = False
        validation_warnings: list[str] = []
        try:
            result = self.llm.invoke_json(QA_SYSTEM_PROMPT, user_prompt)

            # 处理 JSON 解析失败
            if "raw_response" in result and "answer" not in result:
                logger.warning("QA JSON parse failed, using raw_response as answer")
                json_parse_failed = True
                answer = result.get("raw_response", "")[:2000]
                uncertainty = "JSON 解析失败，引用信息不可靠。"
                confidence = 0.2
                supporting_papers = list({e.get("paper_id") for e in evidence[:5] if e.get("paper_id")})
                evidence_ids = [e.get("evidence_id") for e in evidence[:5] if e.get("evidence_id")]
                source_quotes = []
                key_points = []
                suggested = self._build_suggested_actions(intent)
            else:
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

        if json_parse_failed:
            validation_warnings.append("json_parse_failed")

        # 从图谱边中提取路径
        graph_paths = []
        for e in context.get("graph_edges", [])[:10]:
            src = e.get("source_id", "").split(":")[-1][:20]
            tgt = e.get("target_id", "").split(":")[-1][:20]
            rel = e.get("edge_type", "")
            graph_paths.append(f"{src} --{rel}--> {tgt}")

        # 收集引用的图谱节点 ID
        graph_node_ids = [n.get("node_id", "") for n in context.get("graph_nodes", []) if n.get("node_id")]

        return QAResponse(
            answer=answer,
            intent=intent,
            scope_summary=scope.summary,
            supporting_papers=supporting_papers[:10],
            evidence_records=evidence_ids[:10],
            source_quotes=source_quotes,
            key_points=key_points,
            graph_paths=graph_paths,
            graph_node_ids=graph_node_ids,
            uncertainty=uncertainty,
            suggested_actions=suggested or self._build_suggested_actions(intent),
            validation_warnings=validation_warnings,
            retrieval_diagnostics=context.get("diagnostics", {}),
            confidence=confidence,
        )

    def _validate_response(
        self, response: QAResponse, guard: dict[str, Any], context: dict[str, Any] | None = None,
    ) -> QAResponse:
        """校验回答是否越界 + 引用存在性"""
        warnings = []
        allowed_papers = guard.get("allowed_paper_ids", set())
        allowed_evidence = guard.get("allowed_evidence_ids", set())
        retrieved_ids = set(context.get("all_evidence_ids", [])) if context else set()

        # 1. Check papers scope
        valid_papers = []
        for pid in response.supporting_papers:
            if pid in allowed_papers:
                valid_papers.append(pid)
            else:
                warnings.append(f"paper_out_of_scope:{pid}")
        response.supporting_papers = valid_papers

        # 2. Check evidence scope + existence in context
        valid_evidence = []
        for eid in response.evidence_records:
            if eid not in allowed_evidence:
                warnings.append(f"evidence_out_of_scope:{eid}")
            elif retrieved_ids and eid not in retrieved_ids:
                warnings.append(f"evidence_not_in_context:{eid}")
            else:
                valid_evidence.append(eid)
        response.evidence_records = valid_evidence

        # 3. Validate source_quotes reference valid evidence
        valid_quotes = []
        for q in response.source_quotes:
            qeid = q.get("evidence_id", "")
            if qeid in valid_evidence:
                valid_quotes.append(q)
            elif qeid:
                warnings.append(f"quote_evidence_invalid:{qeid}")
        response.source_quotes = valid_quotes

        # 4. Validate key_points evidence_ids
        for kp in response.key_points:
            original = kp.get("evidence_ids", [])
            kp["evidence_ids"] = [e for e in original if e in valid_evidence]
            dropped = [e for e in original if e not in valid_evidence]
            for d in dropped:
                warnings.append(f"key_point_evidence_invalid:{d}")

        # 5. If all references were removed, degrade
        if warnings and not valid_evidence:
            response.uncertainty = "回答中的引用均超出当前范围，已移除。请扩大范围后重试。"
            response.confidence = max(0.1, response.confidence - 0.3)

        response.validation_warnings.extend(warnings)
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

    def _compress_evidence(self, evidence: list[dict], token_budget: int = 3000) -> list[dict]:
        """按 topic 分组截断，控制 token 预算"""
        by_topic: dict[str, list] = {}
        for ev in evidence:
            topic = ev.get("topic", "") or "未分类"
            by_topic.setdefault(topic, []).append(ev)

        strength_order = {"high": 0, "medium": 1, "low": 2}
        compressed: list[dict] = []
        for _topic, evs in by_topic.items():
            evs.sort(key=lambda e: strength_order.get(e.get("evidence_strength", "medium"), 1))
            compressed.extend(evs[:3])

        result: list[dict] = []
        total = 0
        for ev in compressed:
            text = (ev.get("finding", "") or "") + (ev.get("limitation", "") or "")
            tokens = len(text) // 2
            if total + tokens > token_budget:
                break
            result.append(ev)
            total += tokens
        return result

    def _qa_review_revise(
        self, question: str, context: dict[str, Any], scope: RetrievalScope,
        intent: str, response: QAResponse,
    ) -> QAResponse:
        """QA Review-Revise: 验证答案质量，必要时修订"""
        if response.confidence >= 0.7:
            return response

        evidence = context.get("evidence_records", [])
        evidence_ids_in_answer = set(response.evidence_records or [])
        valid_ids = {ev.get("evidence_id") for ev in evidence if ev.get("evidence_id")}
        hallucinated = evidence_ids_in_answer - valid_ids

        if not hallucinated and response.confidence >= 0.4:
            return response

        revision_prompt = f"""原回答存在以下问题：
{f"引用了不存在的证据 ID: {hallucinated}" if hallucinated else ""}
置信度过低: {response.confidence}

请基于相同证据重新回答，确保：
1. 只引用存在的 evidence_id
2. 证据不足时明确说明不确定性
3. 提高结论的精确度

问题: {question}
证据: {self._build_evidence_text(context.get("evidence_records", [])[:8])}
请输出 JSON: {{"answer": "...", "uncertainty": "...", "confidence": 0.0-1.0, "evidence_records": ["evidence_id1", ...]}}"""

        try:
            from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
            registry = get_prompt_registry()
            prompt_spec = registry.get("qa_answer")
            system = prompt_spec.system_prompt if prompt_spec else "你是学术问答专家。"
            revised = self.llm.invoke_json(system, revision_prompt)
            if revised.get("answer"):
                return QAResponse(
                    answer=revised["answer"],
                    intent=response.intent,
                    scope_summary=response.scope_summary,
                    uncertainty=revised.get("uncertainty", response.uncertainty),
                    confidence=revised.get("confidence", response.confidence),
                    supporting_papers=response.supporting_papers,
                    evidence_records=revised.get("evidence_records", response.evidence_records),
                    source_quotes=response.source_quotes,
                    key_points=response.key_points,
                    suggested_actions=response.suggested_actions,
                    retrieval_diagnostics=response.retrieval_diagnostics,
                )
        except Exception as e:
            logger.debug(f"QA revision failed: {e}")

        return response

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

        # node_id → label 映射
        label_map = {}
        for n in nodes:
            nid = n.get("node_id", "")
            label = n.get("label", "")
            if nid and label:
                label_map[nid] = label[:40]

        # 渲染非 Paper 节点（按类型分组）
        non_paper = [n for n in nodes if not n.get("node_id", "").startswith("paper:")]
        if non_paper:
            by_type: dict[str, list] = {}
            for n in non_paper:
                by_type.setdefault(n.get("node_type", "?"), []).append(n)
            for ntype, ns in by_type.items():
                parts.append(f"[{ntype}]")
                for n in ns[:8]:
                    label = n.get("label", "?")[:40]
                    papers = len(n.get("properties", {}).get("paper_ids", []))
                    parts.append(f"  {label} ({papers} 篇)")

        # 渲染边（使用 label 替代 ID）
        if edges:
            parts.append("[关系]")
            for e in edges[:15]:
                src_id = e.get("source_id", "?")
                tgt_id = e.get("target_id", "?")
                src = label_map.get(src_id, src_id.split(":")[-1][:20])
                tgt = label_map.get(tgt_id, tgt_id.split(":")[-1][:20])
                rel = e.get("edge_type", "?")
                parts.append(f"  {src} --{rel}--> {tgt}")

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
            "answer": response.answer,
            "sources": response.evidence_records,
            "metadata": {
                "scope_payload": scope_payload,
                "scope_type": scope.scope_type.value,
                "intent": intent,
                "paper_count": len(scope.paper_ids),
                "evidence_count": len(context.get("evidence_records", [])),
                "supporting_papers": response.supporting_papers,
                "confidence": response.confidence,
                "validation_warnings": response.validation_warnings,
            },
            "created_at": datetime.now().isoformat(),
        }
        self.storage.upsert_item("qa_history", qa_id, record)
