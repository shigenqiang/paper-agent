"""P0 单元测试：创新点报告生成器 Chain of Verification + 反面证据 + PromptRegistry

不依赖真实 LLM API / PostgreSQL。
使用 FakeLLMService + 内存 mock storage。
"""

import json
import pytest

from src.agents_v3.research_workspace.llm.service import FakeLLMService
from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    InnovationGenerationResult,
    InnovationVerificationResult,
    InnovationPoint,
    RetrievalScope,
)
from src.agents_v3.research_workspace.models.enums import ScopeType


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

INNOVATION_SUCCESS_RESPONSE = json.dumps({
    "innovation_points": [
        {
            "name": "跨模态对比学习",
            "description": "将对比学习应用于跨模态场景",
            "why_innovative": "现有方法未考虑跨模态对齐",
            "research_foundation": "基于 CLIP 等工作",
            "feasibility": "high",
            "risk": "数据需求大",
            "possible_topic": "跨模态对比学习在多语言场景的应用",
        },
    ],
})

INNOVATION_VERIFICATION_RESPONSE = json.dumps({
    "verifications": [
        {
            "claim": "将对比学习应用于跨模态场景",
            "innovation_id": "ip_test1234",
            "verification_status": "verified",
            "supporting_evidence_ids": ["ev1"],
            "counter_evidence_ids": [],
            "note": "有证据支撑",
        },
    ],
})

INNOVATION_VERIFICATION_WITH_COUNTER_RESPONSE = json.dumps({
    "verifications": [
        {
            "claim": "将对比学习应用于跨模态场景",
            "innovation_id": "ip_test1234",
            "verification_status": "contradicted",
            "supporting_evidence_ids": ["ev1"],
            "counter_evidence_ids": ["ev2"],
            "note": "存在反面证据",
        },
    ],
})


# ── 测试用例 ──────────────────────────────────────────


class TestPromptRegistry:
    """测试创新点 PromptRegistry 集成"""

    def test_innovation_prompts_registered(self):
        from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
        r = get_prompt_registry()
        for name in ["innovation_generation", "innovation_verification"]:
            p = r.get(name)
            assert p is not None, f"{name} not registered"
            assert p.system_prompt, f"{name} has empty system_prompt"

    def test_innovation_prompt_has_full_text(self):
        from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
        r = get_prompt_registry()
        p = r.get("innovation_generation")
        assert "JSON" in p.system_prompt
        assert "innovation_points" in p.system_prompt

    def test_innovation_verification_schema(self):
        from src.agents_v3.research_workspace.llm.prompts import get_prompt_registry
        r = get_prompt_registry()
        p = r.get("innovation_verification")
        assert p.output_schema_name == "InnovationVerificationResult"


class TestInnovationGenerationResult:
    """测试 InnovationGenerationResult 模型"""

    def test_model_parse(self):
        data = json.loads(INNOVATION_SUCCESS_RESPONSE)
        result = InnovationGenerationResult(**data)
        assert len(result.innovation_points) == 1
        assert result.innovation_points[0].name == "跨模态对比学习"

    def test_model_roundtrip(self):
        data = json.loads(INNOVATION_SUCCESS_RESPONSE)
        result = InnovationGenerationResult(**data)
        dumped = result.model_dump()
        assert dumped["innovation_points"][0]["name"] == "跨模态对比学习"


class TestInnovationPoint:
    """测试 InnovationPoint 新字段"""

    def test_new_fields_defaults(self):
        ip = InnovationPoint(innovation_id="ip_1", name="test")
        assert ip.verification_status == "unverified"
        assert ip.verified_claims == []
        assert ip.counter_evidence_ids == []

    def test_new_fields_set(self):
        ip = InnovationPoint(
            innovation_id="ip_1",
            name="test",
            verification_status="verified",
            counter_evidence_ids=["ev2"],
        )
        assert ip.verification_status == "verified"
        assert ip.counter_evidence_ids == ["ev2"]


class TestCounterEvidenceDetection:
    """测试反面证据检测"""

    def test_detect_counter_evidence_with_negation(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)

        candidates = [
            {
                "innovation_id": "ip_1",
                "name": "method X",
                "description": "method X for improving accuracy",
                "counter_evidence_ids": [],
            },
        ]
        signals = {
            "evidence_records": [
                EvidenceRecord(
                    evidence_id="ev1", paper_id="p1",
                    finding="method X is not effective for accuracy improvement",
                ),
            ],
        }
        result = gen._detect_counter_evidence(candidates, signals)
        assert "ev1" in result[0]["counter_evidence_ids"]

    def test_detect_counter_evidence_no_overlap(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)

        candidates = [
            {
                "innovation_id": "ip_1",
                "name": "quantum computing",
                "description": "quantum computing for protein folding",
                "counter_evidence_ids": [],
            },
        ]
        signals = {
            "evidence_records": [
                EvidenceRecord(
                    evidence_id="ev1", paper_id="p1",
                    finding="method X is not effective for accuracy improvement",
                ),
            ],
        }
        result = gen._detect_counter_evidence(candidates, signals)
        assert len(result[0]["counter_evidence_ids"]) == 0


class TestApplyVerification:
    """测试验证结果应用"""

    def test_apply_verified(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)

        candidates = [{"innovation_id": "ip_1", "counter_evidence_ids": []}]
        verifications = [
            {"innovation_id": "ip_1", "verification_status": "verified", "counter_evidence_ids": []},
        ]
        result = gen._apply_verification(candidates, verifications)
        assert result[0]["verification_status"] == "verified"

    def test_apply_contradicted(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)

        candidates = [{"innovation_id": "ip_1", "counter_evidence_ids": []}]
        verifications = [
            {"innovation_id": "ip_1", "verification_status": "contradicted", "counter_evidence_ids": ["ev2"]},
        ]
        result = gen._apply_verification(candidates, verifications)
        assert result[0]["verification_status"] == "contradicted"
        assert "ev2" in result[0]["counter_evidence_ids"]

    def test_apply_no_verifications(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)

        candidates = [{"innovation_id": "ip_1", "counter_evidence_ids": []}]
        verifications = []
        result = gen._apply_verification(candidates, verifications)
        assert result[0]["verification_status"] == "unverified"


class TestHeuristicVerifyInnovations:
    """测试创新点启发式验证"""

    def test_valid_evidence(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)

        candidates = [
            {"innovation_id": "ip_1", "description": "test", "supporting_evidence_ids": ["ev1"]},
        ]
        evidence = [EvidenceRecord(evidence_id="ev1", paper_id="p1")]
        result = gen._heuristic_verify_innovations(candidates, evidence)
        assert result[0]["verification_status"] == "verified"

    def test_missing_evidence(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)

        candidates = [
            {"innovation_id": "ip_1", "description": "test", "supporting_evidence_ids": ["ev_missing"]},
        ]
        evidence = [EvidenceRecord(evidence_id="ev1", paper_id="p1")]
        result = gen._heuristic_verify_innovations(candidates, evidence)
        assert result[0]["verification_status"] == "unverified"


class TestValidateCandidates:
    """测试 _validate_candidates 移除越界候选"""

    def test_removes_out_of_scope(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        gen._is_generic = lambda x: False

        scope = RetrievalScope(
            scope_type=ScopeType.SELECTED_PAPERS,
            project_id="proj1",
            paper_ids=["p1"],
            evidence_ids=["ev1"],
        )
        candidates = [
            {"innovation_id": "ip_1", "supporting_papers": ["p1"], "supporting_evidence_ids": ["ev1"], "description": "valid"},
            {"innovation_id": "ip_2", "supporting_papers": ["p_outside"], "supporting_evidence_ids": ["ev1"], "description": "invalid"},
        ]
        signals = {"evidence_records": [EvidenceRecord(evidence_id="ev1", paper_id="p1")]}
        filtered, validation = gen._validate_candidates(candidates, scope, signals)
        assert len(filtered) == 1
        assert filtered[0]["innovation_id"] == "ip_1"
        assert validation["removed_count"] == 1

    def test_keeps_valid_candidates(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        gen._is_generic = lambda x: False

        scope = RetrievalScope(
            scope_type=ScopeType.SELECTED_PAPERS,
            project_id="proj1",
            paper_ids=["p1"],
            evidence_ids=["ev1"],
        )
        candidates = [
            {"innovation_id": "ip_1", "supporting_papers": ["p1"], "supporting_evidence_ids": ["ev1"], "description": "valid"},
        ]
        signals = {"evidence_records": [EvidenceRecord(evidence_id="ev1", paper_id="p1")]}
        filtered, validation = gen._validate_candidates(candidates, scope, signals)
        assert len(filtered) == 1
        assert validation["removed_count"] == 0
        assert validation["passed"] is True


class TestScoringWithVerification:
    """测试评分中的验证状态和反面证据惩罚"""

    def test_counter_evidence_penalty(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        gen._is_generic = lambda x: False

        signals = {"evidence_records": []}
        candidates = [
            {
                "innovation_id": "ip_1",
                "name": "test",
                "description": "a sufficiently long description for specificity",
                "gap": "specific gap description",
                "source_signal_type": "common_limitation",
                "supporting_papers": ["p1"],
                "supporting_evidence_ids": ["ev1"],
                "feasibility": "high",
                "risk": "specific risk assessment",
                "possible_topic": "a very specific possible topic for testing",
                "research_foundation": "solid research foundation",
                "confidence": 0.5,
                "scores": {},
                "counter_evidence_ids": ["ev2", "ev3"],
                "verification_status": "unverified",
            },
        ]

        result = gen._score_candidates(candidates, signals)
        scores = result[0]["scores"]
        assert "counter_evidence_penalty" in scores
        assert scores["counter_evidence_penalty"] > 0

    def test_verified_bonus(self):
        from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        gen._is_generic = lambda x: False

        signals = {"evidence_records": []}

        # Without verification
        candidates_no_ver = [
            {
                "innovation_id": "ip_1",
                "name": "test",
                "description": "a sufficiently long description for specificity",
                "gap": "specific gap description",
                "source_signal_type": "common_limitation",
                "supporting_papers": ["p1"],
                "supporting_evidence_ids": ["ev1"],
                "feasibility": "high",
                "risk": "specific risk assessment",
                "possible_topic": "a very specific possible topic for testing",
                "research_foundation": "solid research foundation",
                "confidence": 0.5,
                "scores": {},
                "counter_evidence_ids": [],
                "verification_status": "unverified",
            },
        ]

        # With verification
        candidates_ver = [dict(candidates_no_ver[0])]
        candidates_ver[0]["verification_status"] = "verified"

        result_no_ver = gen._score_candidates(candidates_no_ver, signals)
        result_ver = gen._score_candidates(candidates_ver, signals)

        assert result_ver[0]["scores"]["total"] > result_no_ver[0]["scores"]["total"]
