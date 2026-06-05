"""P0 单元测试：综述生成器 Review-Revise 循环 + H/V ratio + PromptRegistry

不依赖真实 LLM API / PostgreSQL。
使用 FakeLLMService + 内存 mock storage。
"""

import json
import pytest

from src.agents_v3.research_workspace.llm.service import FakeLLMService
from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    ReviewGenerationResult,
    ReviewVerificationResult,
    ClaimVerification,
    RetrievalScope,
)
from src.agents_v3.research_workspace.models.enums import ScopeType


# ── Mock Storage ──────────────────────────────────────


class MockStorage:
    """内存 dict 模拟 storage"""

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
                if item.get(k) != v:
                    match = False
                    break
            if match:
                result.append(item)
        return result

    def list_all(self, table: str):
        return list(self._data.get(table, {}).values())

    def delete_item(self, table: str, item_id: str):
        self._data.get(table, {}).pop(item_id, None)


# ── Fixtures ──────────────────────────────────────────


def _make_evidence(eid: str, pid: str, finding: str = "test finding", limitation: str = "") -> dict:
    return {
        "evidence_id": eid,
        "paper_id": pid,
        "topic": "test topic",
        "finding": finding,
        "limitation": limitation,
        "evidence_strength": "medium",
    }


def _make_paper(pid: str, title: str = "Test Paper") -> dict:
    return {
        "paper_id": pid,
        "title": title,
        "authors": [{"name": "Author One"}],
        "dates": {"year": 2024},
        "source": {"venue": "Test Venue"},
        "identifiers": {"doi": "10.1234/test"},
    }


REVIEW_SUCCESS_RESPONSE = json.dumps({
    "sections": [
        {
            "section_id": "background",
            "title": "研究背景",
            "content": "本研究探讨了 test topic 的最新进展。",
            "paper_ids": ["p1"],
            "evidence_ids": ["ev1"],
        },
        {
            "section_id": "methods",
            "title": "主要研究方法",
            "content": "采用了多种方法进行研究。",
            "paper_ids": ["p1", "p2"],
            "evidence_ids": ["ev1", "ev2"],
        },
        {
            "section_id": "findings",
            "title": "主要研究发现",
            "content": "研究发现了重要结果。",
            "paper_ids": ["p1"],
            "evidence_ids": ["ev1"],
        },
        {
            "section_id": "limitations",
            "title": "研究不足",
            "content": "存在一些局限性。",
            "paper_ids": ["p2"],
            "evidence_ids": ["ev2"],
        },
        {
            "section_id": "future_trends",
            "title": "未来研究趋势",
            "content": "未来可进一步探索。",
            "paper_ids": [],
            "evidence_ids": [],
        },
    ],
    "overall_limitations": "本综述基于有限证据。",
})

REVIEW_VERIFICATION_PASS_RESPONSE = json.dumps({
    "claim_verifications": [
        {
            "claim": "本研究探讨了 test topic",
            "section_id": "background",
            "verification_status": "verified",
            "supporting_evidence_ids": ["ev1"],
            "note": "有证据支撑",
        },
    ],
    "summary": "所有声明均有证据支撑。",
})

REVIEW_VERIFICATION_FAIL_RESPONSE = json.dumps({
    "claim_verifications": [
        {
            "claim": "本研究探讨了 test topic",
            "section_id": "background",
            "verification_status": "unverified",
            "supporting_evidence_ids": [],
            "note": "无证据",
        },
        {
            "claim": "采用了多种方法",
            "section_id": "methods",
            "verification_status": "contradicted",
            "supporting_evidence_ids": [],
            "note": "与证据矛盾",
        },
    ],
    "summary": "多条声明缺乏证据支撑。",
})

REVISED_RESPONSE = json.dumps({
    "sections": [
        {
            "section_id": "background",
            "title": "研究背景",
            "content": "修订后的背景内容。",
            "paper_ids": ["p1"],
            "evidence_ids": ["ev1"],
        },
        {
            "section_id": "methods",
            "title": "主要研究方法",
            "content": "修订后的方法内容。",
            "paper_ids": ["p1"],
            "evidence_ids": ["ev1"],
        },
        {
            "section_id": "findings",
            "title": "主要研究发现",
            "content": "修订后的发现。",
            "paper_ids": ["p1"],
            "evidence_ids": ["ev1"],
        },
        {
            "section_id": "limitations",
            "title": "研究不足",
            "content": "修订后的局限。",
            "paper_ids": ["p2"],
            "evidence_ids": ["ev2"],
        },
        {
            "section_id": "future_trends",
            "title": "未来研究趋势",
            "content": "修订后的趋势。",
            "paper_ids": [],
            "evidence_ids": [],
        },
    ],
    "overall_limitations": "修订后的限制说明。",
})


# ── 测试用例 ──────────────────────────────────────────


class TestPromptRegistry:
    """测试 PromptRegistry 集成"""

    def test_all_prompts_registered(self):
        from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
        r = get_prompt_registry()
        for name in ["review_generation", "review_reviewer", "review_revisor"]:
            p = r.get(name)
            assert p is not None, f"{name} not registered"
            assert p.system_prompt, f"{name} has empty system_prompt"

    def test_review_prompt_has_full_text(self):
        from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
        r = get_prompt_registry()
        p = r.get("review_generation")
        assert "JSON" in p.system_prompt
        assert "sections" in p.system_prompt
        assert "evidence_ids" in p.system_prompt

    def test_review_reviewer_prompt_schema(self):
        from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
        r = get_prompt_registry()
        p = r.get("review_reviewer")
        assert p.output_schema_name == "ReviewVerificationResult"

    def test_review_revisor_prompt_schema(self):
        from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
        r = get_prompt_registry()
        p = r.get("review_revisor")
        assert p.output_schema_name == "ReviewGenerationResult"


class TestHVRatio:
    """测试 H/V ratio 计算"""

    def test_compute_hv_ratio_empty(self):
        from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
        gen = LiteratureReviewGenerator.__new__(LiteratureReviewGenerator)
        assert gen._compute_hv_ratio([]) == 0.0

    def test_compute_hv_ratio_all_verified(self):
        from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
        gen = LiteratureReviewGenerator.__new__(LiteratureReviewGenerator)
        verifications = [
            ClaimVerification(claim="a", verification_status="verified"),
            ClaimVerification(claim="b", verification_status="verified"),
        ]
        assert gen._compute_hv_ratio(verifications) == 0.0

    def test_compute_hv_ratio_half_failed(self):
        from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
        gen = LiteratureReviewGenerator.__new__(LiteratureReviewGenerator)
        verifications = [
            ClaimVerification(claim="a", verification_status="verified"),
            ClaimVerification(claim="b", verification_status="unverified"),
        ]
        assert gen._compute_hv_ratio(verifications) == 0.5

    def test_compute_hv_ratio_all_failed(self):
        from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
        gen = LiteratureReviewGenerator.__new__(LiteratureReviewGenerator)
        verifications = [
            ClaimVerification(claim="a", verification_status="contradicted"),
            ClaimVerification(claim="b", verification_status="unverified"),
        ]
        assert gen._compute_hv_ratio(verifications) == 1.0


class TestHeuristicVerify:
    """测试启发式验证 fallback"""

    def test_heuristic_verify_valid_evidence(self):
        from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
        gen = LiteratureReviewGenerator.__new__(LiteratureReviewGenerator)
        sections = [
            {"section_id": "s1", "content": "test content", "evidence_ids": ["ev1"]},
        ]
        evidence = [EvidenceRecord(evidence_id="ev1", paper_id="p1", finding="test")]
        result = gen._heuristic_verify(sections, evidence)
        assert len(result) == 1
        assert result[0].verification_status == "verified"
        assert "ev1" in result[0].supporting_evidence_ids

    def test_heuristic_verify_missing_evidence(self):
        from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
        gen = LiteratureReviewGenerator.__new__(LiteratureReviewGenerator)
        sections = [
            {"section_id": "s1", "content": "test content", "evidence_ids": ["ev_missing"]},
        ]
        evidence = [EvidenceRecord(evidence_id="ev1", paper_id="p1", finding="test")]
        result = gen._heuristic_verify(sections, evidence)
        assert len(result) == 1
        assert result[0].verification_status == "unverified"


class TestReviewGenerationResult:
    """测试 ReviewGenerationResult 模型"""

    def test_model_parse(self):
        data = json.loads(REVIEW_SUCCESS_RESPONSE)
        result = ReviewGenerationResult(**data)
        assert len(result.sections) == 5
        assert result.sections[0].section_id == "background"
        assert "ev1" in result.sections[0].evidence_ids

    def test_model_roundtrip(self):
        data = json.loads(REVIEW_SUCCESS_RESPONSE)
        result = ReviewGenerationResult(**data)
        dumped = result.model_dump()
        assert dumped["sections"][0]["section_id"] == "background"
