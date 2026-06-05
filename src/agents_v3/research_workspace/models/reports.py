"""项目、报告、论文卡片、证据记录、Scope、QA"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.agents_v3.research_workspace.models.enums import ReportType, ScopeType


# ── 项目 ──────────────────────────────────────────────


class Project(BaseModel):
    project_id: str
    name: str
    description: str = ""
    discipline: str = ""
    education_level: str = ""
    research_goal: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        # 将 None 转换为空字符串
        for k in ('description', 'discipline', 'education_level', 'research_goal'):
            if data.get(k) is None:
                data[k] = ""
        super().__init__(**data)


# ── 论文卡片 ──────────────────────────────────────────


class SourceSpan(BaseModel):
    field: str
    chunk_id: str
    quote: str = ""
    section_type: str = ""


class ExtractedClaim(BaseModel):
    text: str
    quote: str = ""
    chunk_id: str = ""
    section_type: str = ""


class PaperCardExtractionResult(BaseModel):
    research_question: str = "unknown"
    method: str = "unknown"
    data_or_sample: str = "unknown"
    key_findings: list[ExtractedClaim] = Field(default_factory=list)
    limitations: list[ExtractedClaim] = Field(default_factory=list)
    future_work: list[ExtractedClaim] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    possible_gaps: list[ExtractedClaim] = Field(default_factory=list)
    confidence: float = 0.5


class PaperCard(BaseModel):
    card_id: str
    paper_id: str
    version: int = 1
    active: bool = True

    research_question: str = "unknown"
    method: str = "unknown"
    data_or_sample: str = "unknown"
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    possible_gaps: list[str] = Field(default_factory=list)

    source_spans: list[SourceSpan] = Field(default_factory=list)
    input_chunk_ids: list[str] = Field(default_factory=list)

    extraction_method: str = "llm"
    model_name: str = ""
    prompt_version: str = "paper_card_v1"
    confidence: float = 0.0
    quality_score: float = 0.0
    quality_flags: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CardQualityReport(BaseModel):
    card_id: str
    paper_id: str
    completeness: float = 0.0
    traceability: float = 0.0
    specificity: float = 0.0
    quote_match_rate: float = 0.0
    missing_fields: list[str] = Field(default_factory=list)
    weak_fields: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    recommended_action: str = ""


# ── 证据记录 ──────────────────────────────────────────


class EvidenceRecord(BaseModel):
    evidence_id: str
    paper_id: str
    topic: str = ""
    research_question: str = ""
    method: str = ""
    data_or_sample: str = ""
    finding: str = ""
    limitation: str = ""
    future_work: str = ""
    evidence_strength: str = "medium"
    citation_context: str = ""
    source_chunk_id: str = ""
    source_quote: str = ""


# ── Scope ─────────────────────────────────────────────


class RetrievalScope(BaseModel):
    scope_type: ScopeType
    project_id: str
    paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    graph_edge_ids: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    method_ids: list[str] = Field(default_factory=list)
    time_range: list[str] = Field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── QA ────────────────────────────────────────────────


class QARequest(BaseModel):
    question: str
    scope: dict[str, Any] = Field(default_factory=dict)


class QAResponse(BaseModel):
    answer: str = ""
    intent: str = "summary"
    scope_summary: str = ""
    supporting_papers: list[str] = Field(default_factory=list)
    evidence_records: list[str] = Field(default_factory=list)
    source_quotes: list[dict[str, Any]] = Field(default_factory=list)
    key_points: list[dict[str, Any]] = Field(default_factory=list)
    graph_paths: list[Any] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    uncertainty: str = ""
    refusal_reason: str = ""
    suggested_actions: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    retrieval_diagnostics: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


class ScoredEvidence(BaseModel):
    """带评分的证据记录"""
    evidence_id: str
    paper_id: str
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    matched_fields: list[str] = Field(default_factory=list)
    evidence_type: str = ""
    source_quote: str = ""
    evidence_strength: str = "medium"


class QALLMOutput(BaseModel):
    """LLM QA 输出 schema"""
    answer: str = ""
    key_points: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    supporting_paper_ids: list[str] = Field(default_factory=list)
    source_quotes: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: str = ""
    confidence: float = 0.5
    suggested_actions: list[str] = Field(default_factory=list)


# ── 报告 ──────────────────────────────────────────────


class VerifiedClaim(BaseModel):
    """验证过的声明"""
    claim: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: str = "unverified"  # "verified" | "unverified" | "contradicted"
    verification_note: str = ""


class InnovationPoint(BaseModel):
    innovation_id: str
    name: str
    description: str = ""
    why_innovative: str = ""
    research_foundation: str = ""
    gap: str = ""
    supporting_papers: list[str] = Field(default_factory=list)
    limiting_evidence: list[str] = Field(default_factory=list)
    feasibility: str = ""
    risk: str = ""
    possible_topic: str = ""
    scores: dict[str, float] = Field(default_factory=dict)
    verification_status: str = "unverified"  # "verified" | "unverified" | "contradicted"
    verified_claims: list[VerifiedClaim] = Field(default_factory=list)
    counter_evidence_ids: list[str] = Field(default_factory=list)


class ReviewSection(BaseModel):
    """综述章节"""
    section_id: str
    title: str = ""
    content: str = ""
    paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewGenerationResult(BaseModel):
    """LLM 综述生成输出 schema"""
    sections: list[ReviewSection] = Field(default_factory=list)
    overall_limitations: str = ""


class ClaimVerification(BaseModel):
    """声明验证结果"""
    claim: str = ""
    section_id: str = ""
    verification_status: str = "unverified"  # "verified" | "unverified" | "contradicted"
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    note: str = ""


class ReviewVerificationResult(BaseModel):
    """综述审查输出 schema"""
    claim_verifications: list[ClaimVerification] = Field(default_factory=list)
    summary: str = ""


class InnovationPointLLMOutput(BaseModel):
    """LLM 创新点输出 schema（单条）"""
    name: str = ""
    description: str = ""
    why_innovative: str = ""
    research_foundation: str = ""
    feasibility: str = "medium"
    risk: str = ""
    possible_topic: str = ""


class InnovationGenerationResult(BaseModel):
    """LLM 创新点生成输出 schema"""
    innovation_points: list[InnovationPointLLMOutput] = Field(default_factory=list)


class InnovationClaimVerification(BaseModel):
    """创新点声明验证结果"""
    claim: str = ""
    innovation_id: str = ""
    verification_status: str = "unverified"  # "verified" | "unverified" | "contradicted"
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    counter_evidence_ids: list[str] = Field(default_factory=list)
    note: str = ""


class InnovationVerificationResult(BaseModel):
    """创新点验证输出 schema"""
    verifications: list[InnovationClaimVerification] = Field(default_factory=list)


class Report(BaseModel):
    report_id: str
    project_id: str
    type: ReportType
    title: str = ""
    content: str = ""
    scope: dict[str, Any] = Field(default_factory=dict)
    paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    status: str = "draft"
    section_sources: dict[str, Any] = Field(default_factory=dict)
    validation_result: dict[str, Any] = Field(default_factory=dict)
    exported_formats: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


class ReportVersion(BaseModel):
    version_id: str
    report_id: str
    version_number: int = 1
    content: str
    reason: str = ""
    scope_snapshot: dict[str, Any] = Field(default_factory=dict)
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
    paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    validation_result: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ── 检索结果 ────────────────────────────────────────────


class RetrievalResult(BaseModel):
    """单条检索结果，含完整层级上下文"""

    chunk_id: str
    paper_id: str
    section_id: str = ""
    chunk_text: str = ""
    section_title: str = ""
    section_type: str = ""
    paper_title: str = ""
    dense_score: float = 0.0
    layer_scores: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalDiagnostics(BaseModel):
    """检索诊断信息"""

    l0_candidates: int = 0
    l0_selected: int = 0
    l1_candidates: int = 0
    l1_selected: int = 0
    l2_candidates: int = 0
    l2_selected: int = 0
    fallback_used: bool = False
    fallback_reason: str = ""
    duration_ms: int = 0
