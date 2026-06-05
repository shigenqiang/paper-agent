"""质量评估函数"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """评估结果"""
    name: str
    passed: bool
    score: float | None = None
    threshold: float | None = None
    severity: str = "error"  # error / warning / info
    case_id: str | None = None
    project_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


# ── 泛化文本检测 ──────────────────────────────────

_GENERIC_PHRASES = [
    "大量研究表明", "许多研究", "普遍认为", "众多学者", "学界共识",
    "大量文献", "相关研究", "已有研究表明", "需要进一步研究",
    "many studies", "numerous researchers", "it is widely accepted",
    "further research is needed", "more research is needed",
]


# ── Scope Guard 检查 ──────────────────────────────

def scope_guard_check(
    supporting_papers: list[str],
    supporting_evidence: list[str],
    allowed_papers: set[str],
    allowed_evidence: set[str],
) -> EvaluationResult:
    """检查 QA/报告是否越界引用"""
    violations = []
    for pid in supporting_papers:
        if pid and pid not in allowed_papers:
            violations.append(f"paper_out_of_scope:{pid}")
    for eid in supporting_evidence:
        if eid and eid not in allowed_evidence:
            violations.append(f"evidence_out_of_scope:{eid}")

    return EvaluationResult(
        name="scope_guard",
        passed=len(violations) == 0,
        score=1.0 - len(violations) * 0.1 if violations else 1.0,
        threshold=1.0,
        failures=violations,
        details={"violation_count": len(violations)},
    )


# ── 引用覆盖率检查 ──────────────────────────────

def citation_coverage_check(
    key_points: list[dict[str, Any]],
    evidence_ids: list[str],
) -> EvaluationResult:
    """检查回答要点是否有证据支撑"""
    if not key_points:
        return EvaluationResult(
            name="citation_coverage",
            passed=True,
            score=1.0,
            details={"total_points": 0, "cited_points": 0},
        )

    cited = 0
    failures = []
    for i, kp in enumerate(key_points):
        kp_evidence = kp.get("evidence_ids", [])
        if kp_evidence and any(e in evidence_ids for e in kp_evidence):
            cited += 1
        else:
            failures.append(f"uncited_point_{i}")

    coverage = cited / len(key_points) if key_points else 0
    return EvaluationResult(
        name="citation_coverage",
        passed=coverage >= 0.8,
        score=coverage,
        threshold=0.8,
        failures=failures,
        details={"total_points": len(key_points), "cited_points": cited},
    )


# ── 报告可追溯性检查 ──────────────────────────────

def report_traceability_check(
    report_paper_ids: list[str],
    report_evidence_ids: list[str],
    scope_paper_ids: set[str],
    scope_evidence_ids: set[str],
    section_sources: dict[str, Any] | None = None,
) -> EvaluationResult:
    """检查报告引用是否在 scope 内且存在"""
    violations = []
    missing = []

    for pid in report_paper_ids:
        if pid and pid not in scope_paper_ids:
            violations.append(f"paper_out_of_scope:{pid}")

    for eid in report_evidence_ids:
        if eid and eid not in scope_evidence_ids:
            violations.append(f"evidence_out_of_scope:{eid}")

    # Section source coverage
    section_coverage = 0.0
    if section_sources:
        with_sources = sum(1 for s in section_sources.values() if s.get("evidence_ids"))
        section_coverage = with_sources / len(section_sources) if section_sources else 0

    total_refs = len(report_paper_ids) + len(report_evidence_ids)
    violation_rate = len(violations) / total_refs if total_refs else 0
    score = max(0, 1.0 - violation_rate)

    return EvaluationResult(
        name="report_traceability",
        passed=len(violations) == 0,
        score=score,
        threshold=0.8,
        failures=violations,
        details={
            "violation_count": len(violations),
            "section_source_coverage": section_coverage,
        },
    )


# ── 创新点质量检查 ──────────────────────────────

def innovation_specificity_check(candidates: list[dict[str, Any]]) -> EvaluationResult:
    """检查创新点是否具体"""
    if not candidates:
        return EvaluationResult(
            name="innovation_specificity",
            passed=True,
            score=0.0,
            details={"total": 0},
        )

    specific = 0
    gap_supported = 0
    evidence_supported = 0
    failures = []

    generic_phrases = [
        "扩大样本", "提高效率", "优化模型", "加强研究",
        "expand sample", "improve efficiency", "optimize",
    ]

    for i, c in enumerate(candidates):
        desc = (c.get("description", "") or "").lower()
        gap = c.get("gap", "") or ""

        # Specificity: description not generic
        is_generic = any(p in desc for p in generic_phrases)
        if not is_generic and len(desc) > 20:
            specific += 1
        else:
            failures.append(f"generic_candidate_{i}")

        # Gap support
        if gap and gap != "unknown":
            gap_supported += 1

        # Evidence support
        if c.get("supporting_papers") or c.get("supporting_evidence_ids"):
            evidence_supported += 1

    total = len(candidates)
    return EvaluationResult(
        name="innovation_specificity",
        passed=specific / total >= 0.7 if total else True,
        score=specific / total if total else 0,
        threshold=0.7,
        failures=failures,
        details={
            "total": total,
            "specific": specific,
            "gap_supported": gap_supported,
            "evidence_supported": evidence_supported,
            "specificity_rate": specific / total if total else 0,
            "gap_support_rate": gap_supported / total if total else 0,
            "evidence_support_rate": evidence_supported / total if total else 0,
        },
    )


# ── 泛化文本检查 ──────────────────────────────────

def generic_text_check(text: str) -> EvaluationResult:
    """检查文本中泛化套话的比例"""
    if not text:
        return EvaluationResult(name="generic_text", passed=True, score=1.0)

    sentences = re.split(r"[。！？.!?]", text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    if not sentences:
        return EvaluationResult(name="generic_text", passed=True, score=1.0)

    generic_count = 0
    hits = []
    for s in sentences:
        for phrase in _GENERIC_PHRASES:
            if phrase in s:
                generic_count += 1
                hits.append(phrase)
                break

    rate = generic_count / len(sentences)
    return EvaluationResult(
        name="generic_text",
        passed=rate <= 0.2,
        score=1.0 - rate,
        threshold=0.8,
        details={
            "total_sentences": len(sentences),
            "generic_count": generic_count,
            "generic_rate": rate,
            "hits": hits[:5],
        },
    )


# ── 日志脱敏检查 ──────────────────────────────────

_SENSITIVE_MARKERS = ["sk-", "api_key=", "Bearer ", "Authorization:", "OPENAI_API_KEY="]

def redaction_check(log_lines: list[str]) -> EvaluationResult:
    """检查日志是否泄露敏感信息"""
    violations = []
    for i, line in enumerate(log_lines):
        for marker in _SENSITIVE_MARKERS:
            if marker in line and "[REDACTED" not in line:
                violations.append(f"line_{i}: contains '{marker}'")

    return EvaluationResult(
        name="redaction",
        passed=len(violations) == 0,
        score=1.0 - len(violations) * 0.1 if violations else 1.0,
        failures=violations,
        details={"checked_lines": len(log_lines), "violations": len(violations)},
    )


# ── E2E Smoke 检查 ────────────────────────────────

def e2e_smoke_check(summary: dict[str, Any]) -> EvaluationResult:
    """检查端到端流程是否完整"""
    required_stages = [
        "project_created", "papers_imported", "papers_parsed",
        "cards_generated", "evidence_built", "graph_built",
        "qa_answered", "review_generated", "innovation_generated",
        "report_exported",
    ]

    completed = [s for s in required_stages if summary.get(s)]
    missing = [s for s in required_stages if not summary.get(s)]

    return EvaluationResult(
        name="e2e_smoke",
        passed=len(missing) == 0,
        score=len(completed) / len(required_stages),
        threshold=1.0,
        failures=[f"missing:{s}" for s in missing],
        details={
            "completed": len(completed),
            "total": len(required_stages),
            "missing": missing,
        },
    )


# ── Refusal 正确性检查 ────────────────────────────

def refusal_correctness_check(
    cases: list[dict[str, Any]],
) -> EvaluationResult:
    """检查低证据场景是否正确拒答"""
    if not cases:
        return EvaluationResult(name="refusal_correctness", passed=True, score=1.0)

    correct = 0
    failures = []
    for i, case in enumerate(cases):
        should_refuse = case.get("should_refuse", False)
        did_refuse = case.get("did_refuse", False)
        has_uncertainty = bool(case.get("uncertainty", ""))

        if should_refuse and (did_refuse or has_uncertainty):
            correct += 1
        elif not should_refuse and not did_refuse:
            correct += 1
        else:
            failures.append(f"case_{i}: should_refuse={should_refuse}, did_refuse={did_refuse}")

    return EvaluationResult(
        name="refusal_correctness",
        passed=correct / len(cases) >= 0.8,
        score=correct / len(cases),
        threshold=0.8,
        failures=failures,
        details={"total": len(cases), "correct": correct},
    )


# ── Evaluator 类 ────────────────────────────────────


class Evaluator:
    """评估编排器：对报告运行评估检查并产出质量门结果"""

    def __init__(self, storage=None):
        from src.agents_v3.research_workspace.storage import get_storage
        self.storage = storage or get_storage()

    def evaluate_report(self, report_id: str) -> dict[str, Any]:
        """评估单份报告，返回评估结果"""
        report_data = self.storage.get_item("reports", report_id)
        if not report_data:
            return {"error": "report_not_found", "report_id": report_id}

        metadata = report_data.get("metadata") or {}
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        paper_ids = metadata.get("paper_ids", [])
        evidence_ids = metadata.get("evidence_ids", [])
        section_sources = metadata.get("section_sources", {})

        evaluations = []

        # 可追溯性检查
        evaluations.append(report_traceability_check(
            paper_ids, evidence_ids, set(paper_ids), set(evidence_ids), section_sources,
        ))

        # 泛化文本检查
        content = report_data.get("content", "")
        evaluations.append(generic_text_check(content))

        return {
            "report_id": report_id,
            "evaluations": [e.model_dump() for e in evaluations],
            "summary": {
                "total": len(evaluations),
                "passed": sum(1 for e in evaluations if e.passed),
                "failed": sum(1 for e in evaluations if not e.passed),
            },
        }

    def check_quality_gate(self, report_id: str) -> dict[str, Any]:
        """对报告运行质量门"""
        from src.agents_v3.research_workspace.evaluation.gates import run_quality_gates

        eval_result = self.evaluate_report(report_id)
        if "error" in eval_result:
            return eval_result
        evaluations = [EvaluationResult(**e) for e in eval_result["evaluations"]]
        gate_summary = run_quality_gates(evaluations)
        return gate_summary.model_dump()
