"""评估模块测试"""

import pytest

from src.agents_v3.research_workspace.evaluation import (
    EvaluationResult,
    scope_guard_check,
    citation_coverage_check,
    report_traceability_check,
    innovation_specificity_check,
    generic_text_check,
    redaction_check,
    e2e_smoke_check,
    refusal_correctness_check,
)
from src.agents_v3.research_workspace.quality_gates import (
    QualityGateResult,
    QualityGateSummary,
    check_gate,
    run_quality_gates,
)
from src.agents_v3.research_workspace.logging_utils import (
    redact_text,
    hash_text,
    truncate_text,
    sanitize_payload,
    bind_context,
    get_context,
    clear_context,
)
from src.agents_v3.research_workspace.metrics_collector import (
    MetricRecord,
    MetricsCollector,
)
from src.agents_v3.research_workspace.golden_loader import (
    GoldenCase,
    DEFAULT_GOLDEN_CASES,
)


# ── Scope Guard ──────────────────────────────────

class TestScopeGuard:
    def test_passes_when_all_in_scope(self):
        result = scope_guard_check(
            ["p1"], ["e1"], {"p1"}, {"e1"},
        )
        assert result.passed is True

    def test_fails_on_out_of_scope_paper(self):
        result = scope_guard_check(
            ["p1", "p99"], ["e1"], {"p1"}, {"e1"},
        )
        assert result.passed is False
        assert any("p99" in f for f in result.failures)

    def test_fails_on_out_of_scope_evidence(self):
        result = scope_guard_check(
            ["p1"], ["e1", "e99"], {"p1"}, {"e1"},
        )
        assert result.passed is False


# ── Citation Coverage ────────────────────────────

class TestCitationCoverage:
    def test_passes_when_all_cited(self):
        points = [
            {"text": "point1", "evidence_ids": ["e1"]},
            {"text": "point2", "evidence_ids": ["e2"]},
        ]
        result = citation_coverage_check(points, ["e1", "e2"])
        assert result.passed is True
        assert result.score == 1.0

    def test_fails_when_uncited(self):
        points = [
            {"text": "point1", "evidence_ids": ["e1"]},
            {"text": "point2", "evidence_ids": []},
            {"text": "point3", "evidence_ids": []},
            {"text": "point4", "evidence_ids": []},
            {"text": "point5", "evidence_ids": []},
        ]
        result = citation_coverage_check(points, ["e1"])
        assert result.passed is False

    def test_empty_points_passes(self):
        result = citation_coverage_check([], [])
        assert result.passed is True


# ── Report Traceability ─────────────────────────

class TestReportTraceability:
    def test_passes_when_all_in_scope(self):
        result = report_traceability_check(
            ["p1", "p2"], ["e1", "e2"],
            {"p1", "p2"}, {"e1", "e2"},
        )
        assert result.passed is True

    def test_fails_on_violation(self):
        result = report_traceability_check(
            ["p1", "p99"], ["e1"],
            {"p1"}, {"e1"},
        )
        assert result.passed is False


# ── Innovation Specificity ──────────────────────

class TestInnovationSpecificity:
    def test_passes_when_specific(self):
        candidates = [
            {
                "description": "Using LLM feedback to improve self-regulated learning in K-12 math education",
                "gap": "No longitudinal study on LLM feedback effects",
                "supporting_papers": ["p1"],
            },
        ]
        result = innovation_specificity_check(candidates)
        assert result.passed is True

    def test_fails_when_generic(self):
        candidates = [
            {"description": "扩大样本", "gap": ""},
            {"description": "提高效率", "gap": ""},
            {"description": "优化模型", "gap": ""},
            {"description": "加强研究", "gap": ""},
        ]
        result = innovation_specificity_check(candidates)
        assert result.passed is False


# ── Generic Text ─────────────────────────────────

class TestGenericText:
    def test_passes_for_specific_text(self):
        text = "实验组成绩提高了15%。对照组无显著变化。"
        result = generic_text_check(text)
        assert result.passed is True

    def test_fails_for_generic_text(self):
        text = "大量研究表明该方法有效。许多研究证实了这一结论。普遍认为这是正确的。众多学者支持此观点。"
        result = generic_text_check(text)
        assert result.passed is False


# ── Redaction ────────────────────────────────────

class TestRedaction:
    def test_passes_for_clean_logs(self):
        result = redaction_check(["INFO: task completed", "INFO: paper parsed"])
        assert result.passed is True

    def test_fails_for_api_key(self):
        result = redaction_check(["Using key: sk-abc123def456ghi789jkl012"])
        assert result.passed is False


# ── E2E Smoke ────────────────────────────────────

class TestE2ESmoke:
    def test_passes_when_all_complete(self):
        summary = {
            "project_created": True, "papers_imported": True,
            "papers_parsed": True, "cards_generated": True,
            "evidence_built": True, "graph_built": True,
            "qa_answered": True, "review_generated": True,
            "innovation_generated": True, "report_exported": True,
        }
        result = e2e_smoke_check(summary)
        assert result.passed is True

    def test_fails_when_missing_stages(self):
        summary = {"project_created": True, "papers_imported": True}
        result = e2e_smoke_check(summary)
        assert result.passed is False


# ── Refusal Correctness ─────────────────────────

class TestRefusal:
    def test_correct_refusal(self):
        cases = [
            {"should_refuse": True, "did_refuse": True},
            {"should_refuse": False, "did_refuse": False},
        ]
        result = refusal_correctness_check(cases)
        assert result.passed is True

    def test_incorrect_refusal(self):
        cases = [
            {"should_refuse": True, "did_refuse": False, "uncertainty": ""},
            {"should_refuse": True, "did_refuse": False, "uncertainty": ""},
            {"should_refuse": True, "did_refuse": False, "uncertainty": ""},
            {"should_refuse": True, "did_refuse": False, "uncertainty": ""},
            {"should_refuse": True, "did_refuse": False, "uncertainty": ""},
        ]
        result = refusal_correctness_check(cases)
        assert result.passed is False


# ── Quality Gates ────────────────────────────────

class TestQualityGates:
    def test_check_gate_passes(self):
        gate = check_gate("test", "metric", 0.9, 0.8, ">=")
        assert gate.passed is True

    def test_check_gate_fails(self):
        gate = check_gate("test", "metric", 0.5, 0.8, ">=")
        assert gate.passed is False

    def test_run_quality_gates(self):
        evaluations = [
            EvaluationResult(name="scope_guard", passed=True, score=1.0),
            EvaluationResult(name="citation_coverage", passed=True, score=0.9),
            EvaluationResult(name="redaction", passed=True, score=1.0),
        ]
        summary = run_quality_gates(evaluations)
        assert isinstance(summary, QualityGateSummary)
        assert summary.passed_gates >= 3


# ── Logging Utils ────────────────────────────────

class TestLoggingUtils:
    def test_redact_api_key(self):
        result = redact_text("key: sk-abc123def456ghi789jkl012mno")
        assert "REDACTED" in result

    def test_redact_truncates(self):
        result = redact_text("a" * 500, max_len=100)
        assert len(result) < 150

    def test_hash_deterministic(self):
        assert hash_text("test") == hash_text("test")

    def test_truncate(self):
        result = truncate_text("hello world", max_len=5)
        assert len(result) < 20

    def test_sanitize_removes_sensitive(self):
        payload = {"data": "ok", "api_key": "secret", "normal": "text"}
        result = sanitize_payload(payload)
        assert "api_key" not in result
        assert result["normal"] == "text"

    def test_bind_and_get_context(self):
        bind_context(request_id="req_1", project_id="proj_1")
        ctx = get_context()
        assert ctx["request_id"] == "req_1"
        assert ctx["project_id"] == "proj_1"
        clear_context()


# ── Metrics Collector ────────────────────────────

class TestMetricsCollector:
    def test_record_metric(self):
        collector = MetricsCollector()
        rec = collector.record("test_metric", 42, unit="ms")
        assert rec.metric_name == "test_metric"
        assert rec.value == 42

    def test_summarize(self):
        collector = MetricsCollector()
        collector.record("latency", 100)
        collector.record("latency", 200)
        collector.record("latency", 300)
        summary = collector.summarize("latency")
        assert summary["count"] == 3
        assert summary["avg"] == 200
        assert summary["min"] == 100

    def test_get_records_filtered(self):
        collector = MetricsCollector()
        collector.record("a", 1)
        collector.record("b", 2)
        assert len(collector.get_records("a")) == 1


# ── Golden Cases ─────────────────────────────────

class TestGoldenCases:
    def test_default_cases_exist(self):
        assert len(DEFAULT_GOLDEN_CASES) >= 3

    def test_golden_case_structure(self):
        case = DEFAULT_GOLDEN_CASES[0]
        assert case.case_id
        assert case.target
        assert case.input
        assert case.expected
