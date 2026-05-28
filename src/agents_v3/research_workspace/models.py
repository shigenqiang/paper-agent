"""研究工作空间数据模型"""

from __future__ import annotations

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
    description: str = ""
    discipline: str = ""
    education_level: str = ""
    research_goal: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── 论文 ──────────────────────────────────────────────


class Paper(BaseModel):
    paper_id: str
    project_id: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    abstract: str = ""
    url: str = ""
    source: str = ""
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
    section_title: str = ""
    text: str = ""
    start_char: int = 0
    end_char: int = 0
    token_count: int = 0


# ── 论文卡片 ──────────────────────────────────────────


class SourceSpan(BaseModel):
    field: str
    chunk_id: str
    quote: str = ""


class PaperCard(BaseModel):
    card_id: str
    paper_id: str
    project_id: str
    research_question: str = "unknown"
    method: str = "unknown"
    data_or_sample: str = "unknown"
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    possible_gaps: list[str] = Field(default_factory=list)
    source_spans: list[SourceSpan] = Field(default_factory=list)
    confidence: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


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
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


class ReportVersion(BaseModel):
    version_id: str
    report_id: str
    content: str
    reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
