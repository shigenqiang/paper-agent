"""论文画像、章节、引用上下文"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.agents_v3.research_workspace.models.enums import NodeType, SectionType
from src.agents_v3.research_workspace.models.paper import (
    Author,
    CitationInfo,
    OpenAccessInfo,
    PaperClassification,
    PaperDates,
    PaperIdentifiers,
    PaperSource,
    PaperStatus,
)


class KeyResult(BaseModel):
    """论文关键结果"""
    description: str = ""
    evidence_quote: str = ""
    source_chunk_id: str = ""
    confidence: float = 0.0


class PaperProfile(BaseModel):
    """L1: 论文整体画像"""
    paper_id: str
    project_id: str = ""
    title: str = ""
    abstract: str = ""
    language: str = "en"
    publication_type: str = ""

    identifiers: PaperIdentifiers = Field(default_factory=PaperIdentifiers)
    authors: list[Author] = Field(default_factory=list)
    dates: PaperDates = Field(default_factory=PaperDates)
    source: PaperSource = Field(default_factory=PaperSource)
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo)
    classification: PaperClassification = Field(default_factory=PaperClassification)
    citation: CitationInfo = Field(default_factory=CitationInfo)

    url: str = ""
    source_platform: str = ""
    pdf_path: str = ""
    status: PaperStatus = PaperStatus.IMPORTED

    # ── 引言部分 ──
    research_background: str = ""
    research_motivation: str = ""
    problem_statement: str = ""
    research_gap: str = ""
    research_question: str = "unknown"
    contribution_summary: list[str] = Field(default_factory=list)
    prior_work_summary: str = ""

    # ── 方法与结果 ──
    methodology: str = "unknown"
    data_or_sample: str = "unknown"
    key_findings: list[str] = Field(default_factory=list)
    key_results: list[KeyResult] = Field(default_factory=list)

    # ── 讨论与展望 ──
    limitations: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    possible_gaps: list[str] = Field(default_factory=list)

    # ── 主题与分类 ──
    topics: list[str] = Field(default_factory=list)

    # 引用指标
    citation_count: int = 0
    fwci: float = 0.0
    h_index_author: int = 0

    # 实体提取结果
    extracted_entities: list[str] = Field(default_factory=list)
    section_count: int = 0
    chunk_count: int = 0

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class FigureRef(BaseModel):
    """图表引用"""
    ref_id: str = ""
    caption: str = ""
    page: int = 0


class TableRef(BaseModel):
    """表格引用"""
    ref_id: str = ""
    caption: str = ""
    page: int = 0


class SectionClaim(BaseModel):
    """章节中的核心论点"""
    claim: str = ""
    evidence_quote: str = ""
    source_chunk_id: str = ""
    confidence: float = 0.0


class SectionEntity(BaseModel):
    """章节中提取的实体"""
    entity_id: str = ""
    name: str = ""
    entity_type: str = ""
    mention_text: str = ""
    source_chunk_id: str = ""
    confidence: float = 0.0


class PaperSection(BaseModel):
    """L2: 论文章节"""
    section_id: str
    paper_id: str
    section_type: SectionType = SectionType.UNKNOWN
    section_title: str = ""
    section_index: int = 0
    page_start: int = 0
    page_end: int = 0
    text: str = ""
    summary: str = ""  # LLM 生成的章节摘要（~200 token），用于 L1 向量检索
    token_count: int = 0

    # 结构化提取（通用）
    claims: list[SectionClaim] = Field(default_factory=list)
    entities: list[SectionEntity] = Field(default_factory=list)
    figures: list[FigureRef] = Field(default_factory=list)
    tables: list[TableRef] = Field(default_factory=list)

    # 引言专属字段
    background_points: list[str] = Field(default_factory=list)
    motivation_points: list[str] = Field(default_factory=list)
    gap_points: list[str] = Field(default_factory=list)
    contribution_points: list[str] = Field(default_factory=list)
    prior_work_refs: list[str] = Field(default_factory=list)

    # 方法专属字段
    methods_used: list[str] = Field(default_factory=list)
    datasets_used: list[str] = Field(default_factory=list)
    model_details: list[str] = Field(default_factory=list)

    # 结果专属字段
    key_results: list[dict[str, Any]] = Field(default_factory=list)

    # 讨论/结论专属字段
    limitations: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    implications: list[str] = Field(default_factory=list)

    chunk_ids: list[str] = Field(default_factory=list)
    extraction_status: str = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Reference(BaseModel):
    """结构化参考文献条目"""
    ref_id: str = ""
    citing_paper_id: str = ""
    cited_paper_id: str = ""
    index: int = 0
    raw_text: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""


class CitationContext(BaseModel):
    """引用上下文（Scite 模式）"""
    context_id: str = Field(default_factory=lambda: f"ctx_{uuid.uuid4().hex[:8]}")
    citing_paper_id: str = ""
    cited_paper_id: str = ""
    ref_id: str = ""

    citation_context: str = ""
    surrounding_text: str = ""
    citation_type: str = "mentioning"
    section: str = ""
    source_chunk_id: str = ""

    page_number: int | None = None
    paragraph_index: int | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
