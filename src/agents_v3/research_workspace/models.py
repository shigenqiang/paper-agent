"""研究工作空间数据模型"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── 枚举 ──────────────────────────────────────────────


class PaperStatus(str, Enum):
    IMPORTED = "imported"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    CARD_READY = "card_ready"
    EVIDENCE_READY = "evidence_ready"
    FAILED = "failed"


class ChunkType(str, Enum):
    TITLE = "title"
    ABSTRACT = "abstract"
    BODY = "body"
    METHOD = "method"
    RESULT = "result"
    DISCUSSION = "discussion"
    LIMITATION = "limitation"
    CONCLUSION = "conclusion"
    REFERENCE = "reference"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


class ReportType(str, Enum):
    LITERATURE_REVIEW = "literature_review"
    INNOVATION_REPORT = "innovation_report"


class ScopeType(str, Enum):
    ALL_PROJECT = "all_project"
    SELECTED_PAPERS = "selected_papers"
    TOPIC_GROUP = "topic_group"
    METHOD_GROUP = "method_group"
    GRAPH_SUBGRAPH = "graph_subgraph"
    YEAR_RANGE = "year_range"


class NodeType(str, Enum):
    PAPER = "Paper"
    AUTHOR = "Author"
    TOPIC = "Topic"
    TASK = "Task"
    METHOD = "Method"
    DATASET = "Dataset"
    FINDING = "Finding"
    LIMITATION = "Limitation"
    GAP = "Gap"
    INNOVATION = "InnovationPoint"


class EdgeType(str, Enum):
    BELONGS_TO_TOPIC = "BELONGS_TO_TOPIC"
    USES_METHOD = "USES_METHOD"
    USES_DATASET = "USES_DATASET"
    REPORTS_FINDING = "REPORTS_FINDING"
    HAS_LIMITATION = "HAS_LIMITATION"
    SUGGESTS_GAP = "SUGGESTS_GAP"
    SUPPORTS_INNOVATION = "SUPPORTS_INNOVATION"
    CITES = "CITES"


# ── 项目 ──────────────────────────────────────────────


class Project(BaseModel):
    project_id: str
    name: str
    dir_name: str = ""  # 文件系统安全的目录名
    description: str = ""
    discipline: str = ""
    education_level: str = ""
    research_goal: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── 论文子模型 ─────────────────────────────────────────


class Author(BaseModel):
    """论文作者"""
    name: str = ""
    given_name: str = ""
    family_name: str = ""
    orcid: str = ""
    affiliations: list[str] = Field(default_factory=list)


class PaperIdentifiers(BaseModel):
    """论文标识符集合"""
    doi: str = ""
    arxiv_id: str = ""
    pubmed_id: str = ""
    openalex_id: str = ""
    semantic_scholar_id: str = ""


class PaperDates(BaseModel):
    """论文日期信息"""
    year: int | None = None
    published_date: str = ""


class PaperSource(BaseModel):
    """论文来源 (期刊/会议/预印本)"""
    venue: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""


class OpenAccessInfo(BaseModel):
    """开放获取信息"""
    is_oa: bool = False
    oa_status: str = ""
    pdf_url: str = ""
    license: str = ""


class PaperClassification(BaseModel):
    """论文分类信息"""
    categories: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    fields_of_study: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)


class CitationInfo(BaseModel):
    """引用信息"""
    citation_count: int | None = None
    influential_citation_count: int | None = None
    reference_count: int | None = None
    references: list[str] = Field(default_factory=list)


# ── 论文 ──────────────────────────────────────────────


class Paper(BaseModel):
    paper_id: str
    project_id: str
    title: str = ""
    abstract: str = ""
    language: str = ""
    publication_type: str = ""

    identifiers: PaperIdentifiers = Field(default_factory=PaperIdentifiers)
    authors: list[Author] = Field(default_factory=list)
    dates: PaperDates = Field(default_factory=PaperDates)
    source: PaperSource = Field(default_factory=PaperSource)
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo)
    classification: PaperClassification = Field(default_factory=PaperClassification)
    citation: CitationInfo = Field(default_factory=CitationInfo)

    url: str = ""
    source_platform: str = ""  # arxiv/crossref/openalex/upload/bibtex/doi
    source_payload: dict[str, Any] = Field(default_factory=dict)

    status: PaperStatus = PaperStatus.IMPORTED
    pdf_path: str = ""
    error_message: str = ""
    included: bool = True
    exclude_reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperChunk(BaseModel):
    chunk_id: str
    paper_id: str
    chunk_index: int = 0
    section_title: str = ""
    section_type: str = ""  # abstract/method/result/discussion/conclusion/reference/...
    chunk_type: str = "body"  # body/reference/table/figure_caption/title/abstract
    text: str = ""
    start_char: int = 0
    end_char: int = 0
    page_start: int = 0
    page_end: int = 0
    token_count: int = 0
    parser_name: str = "pdfplumber"
    quality_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParseResult(BaseModel):
    parse_id: str = Field(default_factory=lambda: f"parse_{uuid.uuid4().hex[:8]}")
    paper_id: str
    project_id: str = ""
    parser_name: str = "pdfplumber"
    status: str = "pending"  # pending/parsing/success/failed/partial
    page_count: int = 0
    section_count: int = 0
    chunk_count: int = 0
    body_chunk_count: int = 0
    reference_count: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    error_message: str = ""
    started_at: str = ""
    finished_at: str = ""


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
    project_id: str
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

    extraction_method: str = "llm"  # llm / fallback / manual / imported
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
    project_id: str
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


# ── 知识图谱 ──────────────────────────────────────────


class GraphNode(BaseModel):
    node_id: str
    node_type: NodeType
    label: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    project_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


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
    graph_paths: list[list[str]] = Field(default_factory=list)
    uncertainty: str = ""
    suggested_actions: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    retrieval_diagnostics: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


# ── 报告 ──────────────────────────────────────────────


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
    status: str = "draft"  # draft / final / archived
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
