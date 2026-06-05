"""P2 单元测试：ScopeQA 增强 — GraphRAG routing + Hybrid Retrieval + Review-Revise + Compression

不依赖真实 LLM API / PostgreSQL。
使用 FakeLLMService + 内存 mock storage。
"""

import pytest

from src.agents_v3.research_workspace.models import (
    QAResponse,
    RetrievalScope,
    ScoredEvidence,
)
from src.agents_v3.research_workspace.models.enums import ScopeType
from src.agents_v3.research_workspace.services.scope_qa import ScopeQAService


# ── Mock Storage ──────────────────────────────────────


class MockStorage:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get_item(self, table: str, item_id: str):
        return self._data.get(table, {}).get(item_id)

    def upsert_item(self, table: str, item_id: str, item: dict):
        self._data.setdefault(table, {})[item_id] = item

    def query(self, table: str, filters: dict):
        items = self._data.get(table, {}).values()
        result = []
        for item in items:
            match = True
            for k, v in filters.items():
                if isinstance(v, list):
                    if item.get(k) not in v:
                        match = False
                        break
                elif item.get(k) != v:
                    match = False
                    break
            if match:
                result.append(item)
        return result

    def list_all(self, table: str):
        return list(self._data.get(table, {}).values())


# ── Fixtures ──────────────────────────────────────────


def _make_scored_evidence(eid: str, pid: str, score: float = 1.0, topic: str = "test", method: str = "unknown") -> ScoredEvidence:
    return ScoredEvidence(
        evidence_id=eid,
        paper_id=pid,
        finding=f"finding from {eid}",
        topic=topic,
        method=method,
        score=score,
        evidence_strength="medium",
    )


def _make_qa_response(
    answer: str = "test answer",
    confidence: float = 0.5,
    evidence_ids: list[str] | None = None,
) -> QAResponse:
    return QAResponse(
        answer=answer,
        intent="summary",
        scope_summary="test scope",
        confidence=confidence,
        evidence_records=evidence_ids or [],
        uncertainty="test uncertainty",
    )


# ── Test Compress Evidence ────────────────────────────


class TestCompressEvidence:

    def test_compress_empty(self):
        gen = ScopeQAService.__new__(ScopeQAService)
        assert gen._compress_evidence([]) == []

    def test_compress_by_topic_limit(self):
        """每个 topic 最多保留 3 条"""
        gen = ScopeQAService.__new__(ScopeQAService)
        evidence = [
            {"evidence_id": f"ev{i}", "topic": "A", "finding": "x" * 100, "evidence_strength": "medium"}
            for i in range(5)
        ]
        result = gen._compress_evidence(evidence)
        assert len(result) == 3

    def test_compress_by_token_budget(self):
        """token 预算截断"""
        gen = ScopeQAService.__new__(ScopeQAService)
        evidence = [
            {"evidence_id": f"ev{i}", "topic": f"T{i}", "finding": "x" * 2000, "evidence_strength": "medium"}
            for i in range(10)
        ]
        result = gen._compress_evidence(evidence, token_budget=500)
        assert len(result) < 10

    def test_compress_prefers_high_strength(self):
        """高优先级证据优先保留"""
        gen = ScopeQAService.__new__(ScopeQAService)
        evidence = [
            {"evidence_id": "ev_low", "topic": "A", "finding": "low", "evidence_strength": "low"},
            {"evidence_id": "ev_high", "topic": "A", "finding": "high", "evidence_strength": "high"},
            {"evidence_id": "ev_med", "topic": "A", "finding": "med", "evidence_strength": "medium"},
        ]
        result = gen._compress_evidence(evidence)
        ids = [e["evidence_id"] for e in result]
        assert ids[0] == "ev_high"


# ── Test Merge Scored ─────────────────────────────────


class TestMergeScored:

    def test_merge_empty_keyword(self):
        scored = ScopeQAService._merge_scored([], [_make_scored_evidence("ev1", "p1")])
        assert len(scored) == 1
        assert scored[0].evidence_id == "ev1"

    def test_merge_empty_vector(self):
        scored = ScopeQAService._merge_scored([_make_scored_evidence("ev1", "p1")], [])
        assert len(scored) == 1
        assert scored[0].evidence_id == "ev1"

    def test_merge_rrf_fusion(self):
        """RRF 融合：两边都有的结果排名应提升"""
        kw = [_make_scored_evidence("ev1", "p1", 3.0), _make_scored_evidence("ev2", "p2", 2.0)]
        vec = [_make_scored_evidence("ev2", "p2", 0.9), _make_scored_evidence("ev3", "p3", 0.8)]
        scored = ScopeQAService._merge_scored(kw, vec)
        ids = [s.evidence_id for s in scored]
        # ev2 在两边都有，RRF score 最高
        assert ids[0] == "ev2"

    def test_merge_preserves_all(self):
        kw = [_make_scored_evidence("ev1", "p1")]
        vec = [_make_scored_evidence("ev2", "p2")]
        scored = ScopeQAService._merge_scored(kw, vec)
        assert len(scored) == 2


# ── Test QA Review-Revise ─────────────────────────────


class TestQAReviewRevise:

    def test_high_confidence_skips_revision(self):
        """高置信度答案跳过修订"""
        gen = ScopeQAService.__new__(ScopeQAService)
        response = _make_qa_response(confidence=0.8, evidence_ids=["ev1"])
        result = gen._qa_review_revise("q", {"evidence_records": [{"evidence_id": "ev1"}]}, None, "summary", response)
        assert result is response  # 同一对象，未修订

    def test_valid_evidence_skips_revision(self):
        """无幻觉且置信度 >= 0.4 跳过修订"""
        gen = ScopeQAService.__new__(ScopeQAService)
        response = _make_qa_response(confidence=0.5, evidence_ids=["ev1"])
        context = {"evidence_records": [{"evidence_id": "ev1"}]}
        result = gen._qa_review_revise("q", context, None, "summary", response)
        assert result is response

    def test_hallucinated_evidence_triggers_revision(self):
        """幻觉证据触发修订"""
        from unittest.mock import MagicMock
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.llm = MagicMock()
        gen.llm.invoke_json.return_value = {
            "answer": "revised answer",
            "confidence": 0.6,
            "evidence_records": ["ev1"],
            "uncertainty": "revised uncertainty",
        }
        response = _make_qa_response(confidence=0.3, evidence_ids=["ev_missing"])
        context = {"evidence_records": [{"evidence_id": "ev1"}]}
        result = gen._qa_review_revise("q", context, None, "summary", response)
        assert result.answer == "revised answer"
        assert result.confidence == 0.6


# ── Test GraphRAG Routing ─────────────────────────────


class TestGraphRAGRouting:

    def test_small_scope_skips_graphrag(self):
        """论文数 < 3 跳过 GraphRAG"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage()
        scope = RetrievalScope(
            scope_type=ScopeType.SELECTED_PAPERS, project_id="proj1",
            paper_ids=["p1"], evidence_ids=["ev1"],
        )
        result = gen._graphrag_search("proj1", "test", scope, "summary", {})
        assert result is None
