"""Golden Case 加载器"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GoldenCase(BaseModel):
    """Golden 测试用例"""
    case_id: str
    target: str  # qa / review / innovation / e2e
    description: str
    input: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


def load_golden_cases(
    path: str | Path | None = None,
    target: str | None = None,
) -> list[GoldenCase]:
    """加载 golden cases"""
    if path is None:
        path = Path("tests/fixtures/research_workspace/golden_cases.json")

    path = Path(path)
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    cases = [GoldenCase(**item) for item in data]
    if target:
        cases = [c for c in cases if c.target == target]
    return cases


def save_golden_cases(cases: list[GoldenCase], path: str | Path) -> None:
    """保存 golden cases"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([c.model_dump() for c in cases], f, ensure_ascii=False, indent=2)


# ── 内置 golden cases ──────────────────────────────

DEFAULT_GOLDEN_CASES = [
    GoldenCase(
        case_id="qa_limitation_basic",
        target="qa",
        description="问论文不足时应返回 limitation 相关内容",
        input={
            "question": "这些论文有什么不足？",
            "scope_payload": {"type": "all_project"},
            "project_id": "demo",
        },
        expected={
            "intent": "limitation_analysis",
            "should_have_evidence": True,
            "min_evidence_count": 1,
        },
        tags=["limitation", "basic"],
    ),
    GoldenCase(
        case_id="qa_empty_scope_refuse",
        target="qa",
        description="空 scope 应拒答",
        input={
            "question": "讲了什么？",
            "scope_payload": {"type": "selected_papers", "selected_paper_ids": ["nonexistent"]},
            "project_id": "demo",
        },
        expected={
            "should_refuse": True,
        },
        tags=["refusal", "empty_scope"],
    ),
    GoldenCase(
        case_id="review_has_sections",
        target="review",
        description="综述应包含标准章节",
        input={
            "scope_payload": {"type": "all_project"},
            "project_id": "demo",
        },
        expected={
            "required_sections": ["background", "findings", "limitations"],
            "min_paper_count": 2,
        },
        tags=["review", "structure"],
    ),
    GoldenCase(
        case_id="innovation_not_generic",
        target="innovation",
        description="创新点不应全是泛化建议",
        input={
            "scope_payload": {"type": "all_project"},
            "project_id": "demo",
        },
        expected={
            "min_candidates": 1,
            "max_generic_rate": 0.5,
        },
        tags=["innovation", "quality"],
    ),
]
