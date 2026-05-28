"""质量门禁"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents_v3.research_workspace.evaluation.evaluator import EvaluationResult


class QualityGateResult(BaseModel):
    gate_name: str
    passed: bool
    required: bool = True
    metric_name: str
    actual: float | bool | str
    expected: float | bool | str
    operator: str
    failures: list[str] = Field(default_factory=list)


class QualityGateSummary(BaseModel):
    passed: bool
    total_gates: int
    passed_gates: int
    failed_gates: int
    required_failures: int
    gates: list[QualityGateResult] = Field(default_factory=list)


def check_gate(
    name: str, metric_name: str,
    actual: float | bool | str, expected: float | bool | str,
    operator: str = ">=", required: bool = True,
) -> QualityGateResult:
    if operator == ">=":
        passed = actual >= expected
    elif operator == "<=":
        passed = actual <= expected
    elif operator == "==":
        passed = actual == expected
    elif operator == ">":
        passed = actual > expected
    elif operator == "<":
        passed = actual < expected
    else:
        passed = False

    return QualityGateResult(
        gate_name=name, passed=passed, required=required,
        metric_name=metric_name, actual=actual, expected=expected,
        operator=operator,
        failures=[] if passed else [f"{metric_name}: {actual} {operator} {expected} failed"],
    )


def run_quality_gates(evaluations: list[EvaluationResult]) -> QualityGateSummary:
    gates = []
    gate_specs = [
        ("scope_guard", "scope_guard", 1.0, "==", True),
        ("citation_coverage", "citation_coverage", 0.8, ">=", True),
        ("report_traceability", "report_traceability", 0.8, ">=", True),
        ("innovation_specificity", "innovation_specificity", 0.7, ">=", False),
        ("generic_text", "generic_text", 0.8, ">=", False),
        ("redaction", "redaction", 1.0, "==", True),
    ]

    eval_map = {e.name: e for e in evaluations}

    for gate_name, metric_name, expected, operator, required in gate_specs:
        ev = eval_map.get(metric_name)
        if ev and ev.score is not None:
            gate = check_gate(gate_name, metric_name, ev.score, expected, operator, required)
        elif ev:
            gate = QualityGateResult(
                gate_name=gate_name, passed=ev.passed, required=required,
                metric_name=metric_name, actual=ev.passed, expected=True,
                operator="==", failures=ev.failures,
            )
        else:
            gate = QualityGateResult(
                gate_name=gate_name, passed=not required, required=required,
                metric_name=metric_name, actual="missing", expected=expected,
                operator=operator, failures=[f"evaluation '{metric_name}' not found"],
            )
        gates.append(gate)

    failed = [g for g in gates if not g.passed]
    required_failures = [g for g in failed if g.required]

    return QualityGateSummary(
        passed=len(required_failures) == 0,
        total_gates=len(gates), passed_gates=len(gates) - len(failed),
        failed_gates=len(failed), required_failures=len(required_failures), gates=gates,
    )
