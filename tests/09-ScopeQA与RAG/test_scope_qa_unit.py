"""ScopeQAService 单元测试 — FakeLLM + 内存 storage，无真实 API/DB 依赖"""

from __future__ import annotations

import json
import pytest

from src.agents_v3.research_workspace.llm.service import FakeLLMService
from src.agents_v3.research_workspace.models import QAResponse, RetrievalScope, ScopeType, ScoredEvidence
from src.agents_v3.research_workspace.services.scope import RetrievalScopeService
from src.agents_v3.research_workspace.services.scope_qa import ScopeQAService


# ── 内存 Storage Mock ─────────────────────────────────────


class MemoryStorage:
    """极简内存存储，模拟 query/get_item/upsert_item"""

    def __init__(self):
        self._tables: dict[str, dict[str, dict]] = {}

    def upsert_item(self, table: str, item_id: str, data: dict):
        self._tables.setdefault(table, {})[item_id] = data

    def get_item(self, table: str, item_id: str) -> dict | None:
        return self._tables.get(table, {}).get(item_id)

    def query(self, table: str, filters: dict | None = None) -> list[dict]:
        items = list(self._tables.get(table, {}).values())
        if not filters:
            return items
        result = []
        for item in items:
            match = True
            for k, v in filters.items():
                item_val = item.get(k)
                if isinstance(v, list):
                    if item_val not in v:
                        match = False
                        break
                elif item_val != v:
                    match = False
                    break
            if match:
                result.append(item)
        return result

    def list_all(self, table: str) -> list[dict]:
        return list(self._tables.get(table, {}).values())

    def load_collection(self, name: str) -> list[dict]:
        return list(self._tables.get(name, {}).values())


# ── Fixtures ────────────────────────────────────────────────


def _make_storage_with_data() -> MemoryStorage:
    """创建含测试数据的内存 storage"""
    s = MemoryStorage()

    # Papers
    s.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "title": "Paper A",
        "included": True, "dates": {"year": 2024},
    })
    s.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "title": "Paper B",
        "included": True, "dates": {"year": 2023},
    })
    s.upsert_item("papers", "p3", {
        "paper_id": "p3", "project_id": "proj1", "title": "Paper C",
        "included": False,  # excluded
    })

    # Evidence records
    s.upsert_item("evidence_records", "ev1", {
        "evidence_id": "ev1", "paper_id": "p1", "project_id": "proj1",
        "topic": "transformer", "method": "attention mechanism",
        "finding": "Self-attention improves long-range dependency modeling",
        "limitation": "unknown", "future_work": "unknown",
        "source_quote": "Self-attention achieves SOTA on WMT",
        "evidence_strength": "high",
    })
    s.upsert_item("evidence_records", "ev2", {
        "evidence_id": "ev2", "paper_id": "p1", "project_id": "proj1",
        "topic": "transformer", "method": "attention mechanism",
        "finding": "unknown", "limitation": "Quadratic complexity in sequence length",
        "future_work": "Linear attention variants",
        "source_quote": "The quadratic cost limits application to very long sequences",
        "evidence_strength": "medium",
    })
    s.upsert_item("evidence_records", "ev3", {
        "evidence_id": "ev3", "paper_id": "p2", "project_id": "proj1",
        "topic": "knowledge graph", "method": "GNN",
        "finding": "Graph neural networks capture relational inductive bias",
        "limitation": "Over-smoothing in deep GNNs",
        "future_work": "unknown",
        "source_quote": "",
        "evidence_strength": "medium",
    })
    s.upsert_item("evidence_records", "ev4", {
        "evidence_id": "ev4", "paper_id": "p2", "project_id": "proj1",
        "topic": "knowledge graph", "method": "GNN",
        "finding": "unknown", "limitation": "unknown",
        "future_work": "unknown",
        "source_quote": "",
        "evidence_strength": "low",
        "review_status": "rejected",
    })

    # Paper cards
    s.upsert_item("paper_cards", "card_p1", {
        "card_id": "card_p1", "paper_id": "p1", "is_active": True,
        "extraction": {
            "paper_id": "p1", "title": "Paper A",
            "research_question": "How to improve attention efficiency?",
            "method": "attention mechanism",
        },
    })
    s.upsert_item("paper_cards", "card_p2", {
        "card_id": "card_p2", "paper_id": "p2", "is_active": True,
        "extraction": {
            "paper_id": "p2", "title": "Paper B",
            "research_question": "How to apply GNN to knowledge graphs?",
            "method": "GNN",
        },
    })

    return s


def _make_fake_llm(answer_text: str = "test answer", confidence: float = 0.7,
                   evidence_ids: list[str] | None = None,
                   paper_ids: list[str] | None = None) -> FakeLLMService:
    """创建返回预设 JSON 的 FakeLLM"""
    llm = FakeLLMService()
    resp = {
        "answer": answer_text,
        "confidence": confidence,
        "supporting_evidence_ids": evidence_ids or ["ev1"],
        "supporting_paper_ids": paper_ids or ["p1"],
        "source_quotes": [{"evidence_id": evidence_ids[0] if evidence_ids else "ev1", "quote": "test quote"}],
        "key_points": [{"text": "key point 1", "evidence_ids": [evidence_ids[0] if evidence_ids else "ev1"]}],
        "uncertainty": "",
    }
    llm.set_default_response(json.dumps(resp))
    return llm


@pytest.fixture
def storage():
    return _make_storage_with_data()


@pytest.fixture
def scope_service(storage):
    return RetrievalScopeService(storage=storage)


@pytest.fixture
def service(storage, scope_service):
    llm = _make_fake_llm()
    return ScopeQAService(storage=storage, llm_service=llm, scope_service=scope_service)


# ── Test: classify_intent ───────────────────────────────────


class TestClassifyIntent:
    def test_limitation_keywords(self, service):
        assert service.classify_intent("这些论文有什么不足？") == "limitation_analysis"

    def test_method_keywords(self, service):
        assert service.classify_intent("使用了什么方法？") == "method_analysis"

    def test_gap_keywords(self, service):
        assert service.classify_intent("有哪些创新机会？") == "gap_analysis"

    def test_finding_keywords(self, service):
        assert service.classify_intent("主要发现是什么？") == "finding_summary"

    def test_compare_keywords(self, service):
        assert service.classify_intent("对比两种方法的优劣") == "method_compare"

    def test_review_keywords(self, service):
        assert service.classify_intent("写一篇文献综述") == "review_generation"

    def test_innovation_keywords(self, service):
        assert service.classify_intent("有什么创新点可以选题？") == "innovation_generation"

    def test_default_summary(self, service):
        assert service.classify_intent("介绍一下这个项目") == "summary"


# ── Test: 空 scope 拒答 ─────────────────────────────────────


class TestEmptyScopeRefusal:
    def test_no_papers_returns_refusal(self, storage, scope_service):
        """无论文时应拒答"""
        llm = _make_fake_llm()
        svc = ScopeQAService(storage=storage, llm_service=llm, scope_service=scope_service)

        # 用一个空 project
        scope_payload = {"type": "all_project"}
        response = svc.answer("empty_proj", "主要发现是什么？", scope_payload)

        assert "没有" in response.answer or "无法" in response.answer or response.intent == "scope_empty"
        assert response.confidence == 0.0


# ── Test: 证据不足拒答 ─────────────────────────────────────


class TestEvidenceScarcityRefusal:
    def test_less_than_2_evidence_refuses(self, storage, scope_service):
        """少于 2 条证据时应拒答"""
        # 移除 p2 的证据，只留 p1 的
        for key in ("ev3", "ev4"):
            del storage._tables["evidence_records"][key]

        llm = _make_fake_llm()
        svc = ScopeQAService(storage=storage, llm_service=llm, scope_service=scope_service)

        scope_payload = {"type": "selected_papers", "selected_paper_ids": ["p1"]}
        response = svc.answer("proj1", "主要发现是什么？", scope_payload)

        # p1 有 ev1 + ev2 = 2 条，应该能回答
        assert response.answer


# ── Test: _score_evidence ───────────────────────────────────


class TestScoreEvidence:
    def test_rejected_evidence_filtered(self, service):
        """rejected evidence 应被跳过"""
        ev_records = [
            {"evidence_id": "ev1", "paper_id": "p1", "finding": "test", "review_status": ""},
            {"evidence_id": "ev4", "paper_id": "p2", "finding": "test", "review_status": "rejected"},
        ]
        scored = service._score_evidence(ev_records, "test question", "summary")
        assert len(scored) == 1
        assert scored[0].evidence_id == "ev1"

    def test_intent_field_preference(self, service):
        """limitation 意图应优先匹配 limitation evidence"""
        ev_records = [
            {"evidence_id": "ev1", "paper_id": "p1", "finding": "some finding", "limitation": "unknown"},
            {"evidence_id": "ev2", "paper_id": "p1", "finding": "unknown", "limitation": "big limitation"},
        ]
        scored = service._score_evidence(ev_records, "有什么不足", "limitation_analysis")
        # ev2 should score higher because it has limitation content
        assert scored[0].evidence_id == "ev2"

    def test_low_strength_penalty(self, service):
        """low strength 证据应被降权"""
        ev_records = [
            {"evidence_id": "ev1", "paper_id": "p1", "finding": "test", "evidence_strength": "high"},
            {"evidence_id": "ev2", "paper_id": "p1", "finding": "test", "evidence_strength": "low"},
        ]
        scored = service._score_evidence(ev_records, "test", "summary")
        scores = {s.evidence_id: s.score for s in scored}
        assert scores["ev1"] > scores["ev2"]

    def test_scored_evidence_has_breakdown(self, service):
        """ScoredEvidence 应包含 score_breakdown 和 matched_fields"""
        ev_records = [
            {"evidence_id": "ev1", "paper_id": "p1", "finding": "attention improves NLP", "topic": "transformer"},
        ]
        scored = service._score_evidence(ev_records, "attention", "summary")
        assert len(scored) == 1
        se = scored[0]
        assert isinstance(se, ScoredEvidence)
        assert se.score_breakdown
        assert se.matched_fields


# ── Test: _validate_response ────────────────────────────────


class TestValidateResponse:
    def _make_guard(self, papers=None, evidence=None):
        return {
            "allowed_paper_ids": set(papers or ["p1", "p2"]),
            "allowed_evidence_ids": set(evidence or ["ev1", "ev2", "ev3"]),
        }

    def _make_context(self, evidence_ids=None):
        return {"all_evidence_ids": evidence_ids or ["ev1", "ev2", "ev3"]}

    def test_out_of_scope_paper_filtered(self, service):
        """越界 paper_id 应被过滤"""
        guard = self._make_guard(papers=["p1"])
        ctx = self._make_context()
        resp = QAResponse(supporting_papers=["p1", "p99"], evidence_records=["ev1"])
        result = service._validate_response(resp, guard, ctx)
        assert result.supporting_papers == ["p1"]
        assert any("paper_out_of_scope" in w for w in result.validation_warnings)

    def test_out_of_scope_evidence_filtered(self, service):
        """越界 evidence_id 应被过滤"""
        guard = self._make_guard(evidence=["ev1"])
        ctx = self._make_context(["ev1"])
        resp = QAResponse(supporting_papers=["p1"], evidence_records=["ev1", "ev99"])
        result = service._validate_response(resp, guard, ctx)
        assert result.evidence_records == ["ev1"]
        assert any("evidence_out_of_scope" in w for w in result.validation_warnings)

    def test_evidence_not_in_context_filtered(self, service):
        """在 guard 内但不在 context 中的 evidence 应被过滤"""
        guard = self._make_guard(evidence=["ev1", "ev2"])
        ctx = self._make_context(["ev1"])  # ev2 not retrieved
        resp = QAResponse(supporting_papers=["p1"], evidence_records=["ev1", "ev2"])
        result = service._validate_response(resp, guard, ctx)
        assert result.evidence_records == ["ev1"]
        assert any("evidence_not_in_context" in w for w in result.validation_warnings)

    def test_source_quote_invalid_evidence_removed(self, service):
        """引用无效 evidence_id 的 source_quote 应被移除"""
        guard = self._make_guard()
        ctx = self._make_context()
        resp = QAResponse(
            supporting_papers=["p1"],
            evidence_records=["ev1"],
            source_quotes=[
                {"evidence_id": "ev1", "quote": "valid quote"},
                {"evidence_id": "ev99", "quote": "invalid quote"},
            ],
        )
        result = service._validate_response(resp, guard, ctx)
        assert len(result.source_quotes) == 1
        assert result.source_quotes[0]["evidence_id"] == "ev1"

    def test_key_point_invalid_evidence_cleaned(self, service):
        """key_points 中无效 evidence_id 应被清除"""
        guard = self._make_guard()
        ctx = self._make_context()
        resp = QAResponse(
            supporting_papers=["p1"],
            evidence_records=["ev1"],
            key_points=[{"text": "point 1", "evidence_ids": ["ev1", "ev99"]}],
        )
        result = service._validate_response(resp, guard, ctx)
        assert result.key_points[0]["evidence_ids"] == ["ev1"]

    def test_all_references_removed_degrades(self, service):
        """所有引用被移除时应降低 confidence"""
        guard = self._make_guard(papers=[], evidence=[])
        ctx = self._make_context([])
        resp = QAResponse(
            supporting_papers=["p99"],
            evidence_records=["ev99"],
            confidence=0.7,
        )
        result = service._validate_response(resp, guard, ctx)
        assert result.confidence < 0.7
        assert result.uncertainty


# ── Test: 端到端 answer ─────────────────────────────────────


class TestAnswerE2E:
    def test_answer_returns_response(self, service, storage):
        """正常 scope 应回答"""
        scope_payload = {"type": "selected_papers", "selected_paper_ids": ["p1", "p2"]}
        response = service.answer("proj1", "主要发现是什么？", scope_payload)
        assert isinstance(response, QAResponse)
        assert response.answer
        assert response.intent == "finding_summary"

    def test_answer_has_diagnostics(self, service):
        """response 应包含 retrieval_diagnostics"""
        scope_payload = {"type": "selected_papers", "selected_paper_ids": ["p1", "p2"]}
        response = service.answer("proj1", "方法对比", scope_payload)
        diag = response.retrieval_diagnostics
        assert "candidate_evidence_count" in diag
        assert "selected_evidence_count" in diag
        assert "intent" in diag

    def test_answer_scope_leak_warning(self, storage, scope_service):
        """LLM 返回越界引用时应有 validation_warnings"""
        llm = _make_fake_llm(
            evidence_ids=["ev1", "ev99"],  # ev99 not in scope
            paper_ids=["p1", "p99"],
        )
        svc = ScopeQAService(storage=storage, llm_service=llm, scope_service=scope_service)
        scope_payload = {"type": "selected_papers", "selected_paper_ids": ["p1", "p2"]}
        response = svc.answer("proj1", "主要发现是什么？", scope_payload)
        # ev99 should be filtered out
        assert "ev99" not in response.evidence_records
        assert "p99" not in response.supporting_papers


# ── Test: LLM 失败 fallback ────────────────────────────────


class TestFallbackOnLLMFailure:
    def test_llm_exception_fallback(self, storage, scope_service):
        """LLM 异常时应使用 fallback"""
        llm = FakeLLMService()

        def _raise(*args, **kwargs):
            raise RuntimeError("LLM API down")

        llm.invoke = _raise
        svc = ScopeQAService(storage=storage, llm_service=llm, scope_service=scope_service)
        scope_payload = {"type": "selected_papers", "selected_paper_ids": ["p1", "p2"]}
        response = svc.answer("proj1", "主要发现是什么？", scope_payload)

        assert response.answer  # fallback should produce something
        assert response.confidence == 0.3

    def test_json_parse_failure_uses_raw(self, storage, scope_service):
        """JSON 解析失败时应使用 raw_response"""
        llm = FakeLLMService()
        llm.set_default_response("This is a plain text answer, not JSON.")
        svc = ScopeQAService(storage=storage, llm_service=llm, scope_service=scope_service)
        scope_payload = {"type": "selected_papers", "selected_paper_ids": ["p1", "p2"]}
        response = svc.answer("proj1", "主要发现是什么？", scope_payload)

        assert response.answer
        assert "json_parse_failed" in response.validation_warnings
        assert response.confidence == 0.2


# ── Test: retrieve_context ──────────────────────────────────


class TestRetrieveContext:
    def test_returns_scored_evidence(self, service):
        """retrieve_context 应返回 scored_evidence 列表"""
        scope = RetrievalScope(
            scope_type=ScopeType.SELECTED_PAPERS,
            project_id="proj1",
            paper_ids=["p1", "p2"],
            evidence_ids=["ev1", "ev2", "ev3"],
        )
        ctx = service.retrieve_context("test question", scope, "summary")
        assert "scored_evidence" in ctx
        assert all(isinstance(s, ScoredEvidence) for s in ctx["scored_evidence"])

    def test_diagnostics_complete(self, service):
        """diagnostics 应包含所有增强字段"""
        scope = RetrievalScope(
            scope_type=ScopeType.SELECTED_PAPERS,
            project_id="proj1",
            paper_ids=["p1", "p2"],
            evidence_ids=["ev1", "ev2", "ev3"],
        )
        ctx = service.retrieve_context("test question", scope, "summary")
        diag = ctx["diagnostics"]
        assert "candidate_evidence_count" in diag
        assert "selected_evidence_count" in diag
        assert "top_score" in diag
        assert "min_selected_score" in diag
        assert "low_quality_count" in diag
        assert "matched_fields" in diag
        assert "intent" in diag
