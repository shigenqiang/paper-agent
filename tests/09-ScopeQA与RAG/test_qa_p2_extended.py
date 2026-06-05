"""P2 扩展测试：ScopeQA 深层分支覆盖

覆盖：_vector_retrieve_evidence, _score_evidence, _graphrag_search,
generate_answer with graph_answer, _validate_response, _qa_review_revise 异常路径
"""

import pytest
from unittest.mock import MagicMock, patch

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


# ── Helpers ───────────────────────────────────────────


def _make_scored(eid, pid, score=1.0):
    return ScoredEvidence(
        evidence_id=eid, paper_id=pid, score=score,
        finding=f"finding {eid}", topic="test", method="unknown",
        evidence_strength="medium",
    )


def _make_qa_response(answer="test", confidence=0.5, evidence_ids=None, papers=None):
    return QAResponse(
        answer=answer, intent="summary", scope_summary="test",
        confidence=confidence, evidence_records=evidence_ids or [],
        supporting_papers=papers or [], uncertainty="test",
    )


def _make_scope(paper_ids=None, evidence_ids=None):
    return RetrievalScope(
        scope_type=ScopeType.SELECTED_PAPERS, project_id="proj1",
        paper_ids=paper_ids or ["p1", "p2", "p3", "p4", "p5"],
        evidence_ids=evidence_ids or ["ev1", "ev2"],
    )


# ── Test _score_evidence ──────────────────────────────


class TestScoreEvidence:

    def _make_gen(self):
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage()
        return gen

    def test_intent_field_bonus(self):
        """intent=summary → finding/topic 字段匹配得 4 分"""
        gen = self._make_gen()
        records = [{"evidence_id": "ev1", "paper_id": "p1", "finding": "test finding", "topic": "NLP", "method": "unknown"}]
        scored = gen._score_evidence(records, "test question", "summary")
        assert scored[0].score_breakdown.get("intent_field", 0) >= 4

    def test_keyword_match(self):
        """关键词匹配 finding 字段"""
        gen = self._make_gen()
        records = [{"evidence_id": "ev1", "paper_id": "p1", "finding": "deep learning for NLP tasks", "topic": "x", "method": "unknown"}]
        scored = gen._score_evidence(records, "deep learning NLP", "summary")
        assert scored[0].score_breakdown.get("keyword", 0) > 0

    def test_topic_method_match(self):
        """topic/method 字段匹配得 2 分"""
        gen = self._make_gen()
        records = [{"evidence_id": "ev1", "paper_id": "p1", "finding": "", "topic": "transformer", "method": "unknown"}]
        scored = gen._score_evidence(records, "transformer model", "summary")
        assert scored[0].score_breakdown.get("topic_method", 0) >= 2

    def test_source_quote_bonus(self):
        """有 source_quote 得 1 分"""
        gen = self._make_gen()
        records = [{"evidence_id": "ev1", "paper_id": "p1", "finding": "", "topic": "", "method": "unknown", "source_quote": "exact quote"}]
        scored = gen._score_evidence(records, "test", "summary")
        assert scored[0].score_breakdown.get("source_quote", 0) == 1

    def test_high_strength_bonus(self):
        """high strength +1"""
        gen = self._make_gen()
        records = [{"evidence_id": "ev1", "paper_id": "p1", "finding": "", "topic": "", "method": "unknown", "evidence_strength": "high"}]
        scored = gen._score_evidence(records, "test", "summary")
        assert scored[0].score_breakdown.get("strength", 0) == 1

    def test_low_strength_penalty(self):
        """low strength -2"""
        gen = self._make_gen()
        records = [{"evidence_id": "ev1", "paper_id": "p1", "finding": "", "topic": "", "method": "unknown", "evidence_strength": "low"}]
        scored = gen._score_evidence(records, "test", "summary")
        assert scored[0].score_breakdown.get("strength", 0) == -2

    def test_rejected_evidence_skipped(self):
        """review_status=rejected 的证据被跳过"""
        gen = self._make_gen()
        records = [
            {"evidence_id": "ev1", "paper_id": "p1", "finding": "", "topic": "", "method": "unknown", "review_status": "rejected"},
            {"evidence_id": "ev2", "paper_id": "p2", "finding": "", "topic": "", "method": "unknown"},
        ]
        scored = gen._score_evidence(records, "test", "summary")
        assert len(scored) == 1
        assert scored[0].evidence_id == "ev2"

    def test_sorted_by_score_desc(self):
        """结果按分数降序排列"""
        gen = self._make_gen()
        records = [
            {"evidence_id": "ev_low", "paper_id": "p1", "finding": "", "topic": "", "method": "unknown"},
            {"evidence_id": "ev_high", "paper_id": "p2", "finding": "matching content", "topic": "matching_topic", "method": "unknown", "evidence_strength": "high", "source_quote": "q"},
        ]
        scored = gen._score_evidence(records, "matching content matching_topic", "summary")
        assert scored[0].evidence_id == "ev_high"

    def test_low_quality_status_penalty(self):
        """review_status=low 降权 -2"""
        gen = self._make_gen()
        records = [{"evidence_id": "ev1", "paper_id": "p1", "finding": "", "topic": "", "method": "unknown", "review_status": "low"}]
        scored = gen._score_evidence(records, "test", "summary")
        assert scored[0].score_breakdown.get("low_quality", 0) == -2


# ── Test _vector_retrieve_evidence ────────────────────


class TestVectorRetrieveEvidence:

    def test_returns_evidence_from_retriever(self):
        """成功检索返回 ScoredEvidence 列表"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage({
            "evidence_records": {
                "ev1": {"evidence_id": "ev1", "paper_id": "p1", "finding": "test", "topic": "NLP", "method": "BERT", "evidence_strength": "high"},
            },
        })
        mock_result = MagicMock()
        mock_result.paper_id = "p1"
        mock_result.chunk_id = "chunk1"
        mock_result.dense_score = 0.95

        with patch("src.agents_v3.research_workspace.services.hierarchical_retriever.HierarchicalRetriever") as mock_cls:
            mock_cls.return_value.retrieve.return_value = ([mock_result], {})
            scope = _make_scope()
            result = gen._vector_retrieve_evidence("test question", scope)

        assert len(result) == 1
        assert result[0].evidence_id == "ev1"
        assert result[0].score == 0.95

    def test_returns_empty_on_exception(self):
        """检索异常时返回空列表"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage()
        with patch("src.agents_v3.research_workspace.services.hierarchical_retriever.HierarchicalRetriever", side_effect=ImportError("no module")):
            result = gen._vector_retrieve_evidence("test", _make_scope())
        assert result == []

    def test_returns_empty_when_no_evidence_in_storage(self):
        """检索结果的论文在 storage 中无 evidence 记录"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage({"evidence_records": {}})
        mock_result = MagicMock()
        mock_result.paper_id = "p_unknown"
        mock_result.chunk_id = "chunk1"
        mock_result.dense_score = 0.8

        with patch("src.agents_v3.research_workspace.services.hierarchical_retriever.HierarchicalRetriever") as mock_cls:
            mock_cls.return_value.retrieve.return_value = ([mock_result], {})
            result = gen._vector_retrieve_evidence("test", _make_scope())
        assert result == []


# ── Test _graphrag_search branches ────────────────────


class TestGraphRAGSearch:

    def test_global_search_for_summary_intent(self):
        """summary intent 触发 global search"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage()

        mock_gs = MagicMock()
        mock_gs.detect_communities.return_value = None
        mock_gs.build_community_summaries.return_value = None
        mock_gs.global_search.return_value = {"answer": "global answer", "sources": ["p1"]}

        with patch("src.agents_v3.research_workspace.services.graph_service.GraphService", return_value=mock_gs):
            scope = _make_scope()
            result = gen._graphrag_search("proj1", "what is the trend?", scope, "summary", {})

        assert result is not None
        assert result["answer"] == "global answer"
        mock_gs.detect_communities.assert_called_once()
        mock_gs.global_search.assert_called_once()

    def test_local_search_for_method_intent(self):
        """method_analysis intent 触发 local search"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage()

        mock_gs = MagicMock()
        mock_gs.local_search.return_value = {"answer": "local answer", "sources": ["p1"]}

        with patch("src.agents_v3.research_workspace.services.graph_service.GraphService", return_value=mock_gs):
            scope = _make_scope()
            context = {"evidence_records": [{"topic": "NLP", "method": "BERT"}]}
            result = gen._graphrag_search("proj1", "how does BERT work?", scope, "method_analysis", context)

        assert result is not None
        assert result["answer"] == "local answer"
        mock_gs.local_search.assert_called_once()

    def test_returns_none_on_exception(self):
        """GraphService 异常时返回 None"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage()

        with patch("src.agents_v3.research_workspace.services.graph_service.GraphService", side_effect=RuntimeError("db error")):
            scope = _make_scope()
            result = gen._graphrag_search("proj1", "test", scope, "summary", {})

        assert result is None

    def test_returns_none_when_global_search_empty(self):
        """global_search 返回空 answer 时返回 None"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.storage = MockStorage()

        mock_gs = MagicMock()
        mock_gs.global_search.return_value = {"answer": "", "sources": []}

        with patch("src.agents_v3.research_workspace.services.graph_service.GraphService", return_value=mock_gs):
            scope = _make_scope()
            result = gen._graphrag_search("proj1", "test", scope, "summary", {})

        assert result is None


# ── Test _validate_response ───────────────────────────


class TestValidateResponse:

    def test_removes_out_of_scope_papers(self):
        """不在 allowed_paper_ids 中的论文被移除"""
        gen = ScopeQAService.__new__(ScopeQAService)
        response = _make_qa_response(papers=["p1", "p_bad"])
        guard = {"allowed_paper_ids": {"p1", "p2"}, "allowed_evidence_ids": {"ev1"}}
        result = gen._validate_response(response, guard, {"all_evidence_ids": ["ev1"]})
        assert "p_bad" not in result.supporting_papers
        assert "p1" in result.supporting_papers
        assert any("paper_out_of_scope" in w for w in result.validation_warnings)

    def test_removes_out_of_scope_evidence(self):
        """不在 allowed_evidence_ids 中的证据被移除"""
        gen = ScopeQAService.__new__(ScopeQAService)
        response = _make_qa_response(evidence_ids=["ev1", "ev_bad"])
        guard = {"allowed_paper_ids": {"p1"}, "allowed_evidence_ids": {"ev1"}}
        result = gen._validate_response(response, guard, {"all_evidence_ids": ["ev1"]})
        assert "ev_bad" not in result.evidence_records
        assert "ev1" in result.evidence_records

    def test_degrades_when_all_references_removed(self):
        """所有引用被移除时降级"""
        gen = ScopeQAService.__new__(ScopeQAService)
        response = _make_qa_response(confidence=0.6, evidence_ids=["ev_bad"])
        guard = {"allowed_paper_ids": set(), "allowed_evidence_ids": {"ev1"}}
        result = gen._validate_response(response, guard, {"all_evidence_ids": ["ev1"]})
        assert result.confidence < 0.6
        assert "超出当前范围" in result.uncertainty

    def test_validates_source_quotes(self):
        """source_quote 引用无效 evidence 时被移除"""
        gen = ScopeQAService.__new__(ScopeQAService)
        response = _make_qa_response(evidence_ids=["ev1"])
        response.source_quotes = [{"evidence_id": "ev1", "quote": "ok"}, {"evidence_id": "ev_bad", "quote": "bad"}]
        guard = {"allowed_paper_ids": {"p1"}, "allowed_evidence_ids": {"ev1"}}
        result = gen._validate_response(response, guard, {"all_evidence_ids": ["ev1"]})
        assert len(result.source_quotes) == 1
        assert result.source_quotes[0]["evidence_id"] == "ev1"


# ── Test _qa_review_revise edge cases ─────────────────


class TestQAReviewReviseEdgeCases:

    def test_low_confidence_no_hallucination_triggers_revision(self):
        """confidence < 0.4 且无幻觉 → 触发修订"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.llm = MagicMock()
        gen.llm.invoke_json.return_value = {
            "answer": "revised", "confidence": 0.5,
            "evidence_records": ["ev1"], "uncertainty": "less uncertain",
        }
        response = _make_qa_response(confidence=0.2, evidence_ids=["ev1"])
        context = {"evidence_records": [{"evidence_id": "ev1"}]}
        result = gen._qa_review_revise("q", context, None, "summary", response)
        assert result.answer == "revised"

    def test_exception_during_revision_returns_original(self):
        """修订 LLM 异常时返回原始答案"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.llm = MagicMock()
        gen.llm.invoke_json.side_effect = RuntimeError("LLM down")
        response = _make_qa_response(confidence=0.2, evidence_ids=["ev1"])
        context = {"evidence_records": [{"evidence_id": "ev1"}]}
        result = gen._qa_review_revise("q", context, None, "summary", response)
        assert result is response  # 返回原始对象


# ── Test generate_answer with graph_answer ────────────


class TestGenerateAnswerGraphAnswer:

    def test_graph_answer_injected_into_prompt(self):
        """graph_answer 内容应出现在 LLM prompt 中"""
        gen = ScopeQAService.__new__(ScopeQAService)
        gen.llm = MagicMock()
        gen.llm.invoke_json.return_value = {
            "answer": "test", "confidence": 0.7,
            "supporting_evidence_ids": [], "uncertainty": "none",
        }
        gen.storage = MockStorage()

        scope = _make_scope()
        context = {
            "scope_summary": "test scope",
            "paper_count": 5,
            "all_evidence_ids": [],
            "evidence_records": [],
            "paper_cards": [],
            "graph_nodes": [],
            "graph_edges": [],
        }
        graph_answer = {"answer": "GraphRAG found that X is trending", "sources": ["p1"]}

        gen.generate_answer("what is trending?", context, scope, "summary", graph_answer)

        # 验证 prompt 包含 GraphRAG 内容
        call_args = gen.llm.invoke_json.call_args
        prompt = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("user_prompt", "")
        assert "GraphRAG" in prompt or "trending" in prompt
