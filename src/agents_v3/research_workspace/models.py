"""研究工作空间数据模型"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

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


class SectionType(str, Enum):
    """论文章节类型（细粒度，比 ChunkType 更精确）"""
    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    EXPERIMENT = "experiment"
    RESULT = "result"
    DISCUSSION = "discussion"
    LIMITATION = "limitation"
    CONCLUSION = "conclusion"
    ACKNOWLEDGMENT = "acknowledgment"
    APPENDIX = "appendix"
    REFERENCE = "reference"
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
    # SciERC 扩展
    METRIC = "Metric"
    OTHER_SCI_TERM = "OtherSciTerm"
    VENUE = "Venue"
    INSTITUTION = "Institution"


class EdgeType(str, Enum):
    BELONGS_TO_TOPIC = "BELONGS_TO_TOPIC"
    USES_METHOD = "USES_METHOD"
    USES_DATASET = "USES_DATASET"
    REPORTS_FINDING = "REPORTS_FINDING"
    HAS_LIMITATION = "HAS_LIMITATION"
    SUGGESTS_GAP = "SUGGESTS_GAP"
    SUPPORTS_INNOVATION = "SUPPORTS_INNOVATION"
    CITES = "CITES"
    # SciERC 核心关系
    USED_FOR = "USED_FOR"           # Method → Task (55.6%)
    CONJUNCTION = "CONJUNCTION"     # Entity ↔ Entity (18.5%)
    HYPONYM_OF = "HYPONYM_OF"      # Entity → Entity (9.8%)
    COMPARE = "COMPARE"             # Method ↔ Method (5%)
    PART_OF = "PART_OF"             # Entity → Entity (5%)
    EVALUATE_FOR = "EVALUATE_FOR"   # Metric → Task (4.4%)
    FEATURE_OF = "FEATURE_OF"       # Property → Entity (1.8%)
    # 扩展关系
    EVALUATED_ON = "EVALUATED_ON"   # Method → Dataset
    EVALUATED_BY = "EVALUATED_BY"   # Method → Metric
    EXTENDS = "EXTENDS"             # Method → Method
    SUBCLASS_OF = "SUBCLASS_OF"
    SUBTASK_OF = "SUBTASK_OF"
    TRAINED_WITH = "TRAINED_WITH"   # Method → Dataset
    ACHIEVES = "ACHIEVES"           # Method → Metric
    AUTHORED_BY = "AUTHORED_BY"
    PUBLISHED_IN = "PUBLISHED_IN"


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
    source_platform: str = ""  # arxiv/openalex/upload/bibtex/doi
    source_payload: dict[str, Any] = Field(default_factory=dict)

    status: PaperStatus = PaperStatus.IMPORTED
    pdf_path: str = ""
    error_message: str = ""
    included: bool = True
    exclude_reason: str = ""
    importance_score: float = 0.0  # 主题相关重要性得分（项目级临时数据，不入库论文池）
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


# ── 三层论文数据结构 ──────────────────────────────────────


class KeyResult(BaseModel):
    """论文关键结果"""
    description: str = ""
    evidence_quote: str = ""
    source_chunk_id: str = ""
    confidence: float = 0.0


class PaperProfile(BaseModel):
    """
    L1: 论文整体画像
    统一 Paper + PaperCard + 引用指标，作为实体提取的输入
    """
    paper_id: str
    project_id: str = ""
    title: str = ""
    abstract: str = ""
    language: str = "en"
    publication_type: str = ""  # journal/conference/preprint/thesis

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

    # ── 引言部分（重点提取） ──
    research_background: str = ""  # 研究背景：领域概况、技术发展脉络
    research_motivation: str = ""  # 研究动机：为什么要做这个研究
    problem_statement: str = ""  # 问题陈述：要解决什么具体问题
    research_gap: str = ""  # 研究空白：现有方法的不足
    research_question: str = "unknown"  # 核心研究问题
    contribution_summary: list[str] = Field(default_factory=list)  # 论文贡献列表（通常引言末尾列出）
    prior_work_summary: str = ""  # 相关工作概述（引言中简要提及的前人工作）

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
    fwci: float = 0.0  # Field-Weighted Citation Impact (OpenAlex, 0-3+)
    h_index_author: int = 0  # 第一作者 h-index

    # 实体提取结果
    extracted_entities: list[str] = Field(default_factory=list)  # entity_id 列表
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
    entity_type: str = ""  # 对应 NodeType
    mention_text: str = ""
    source_chunk_id: str = ""
    confidence: float = 0.0


class PaperSection(BaseModel):
    """
    L2: 论文章节
    表示论文中的逻辑章节（introduction/method/result/discussion 等）
    """
    section_id: str
    paper_id: str
    section_type: SectionType = SectionType.UNKNOWN
    section_title: str = ""
    section_index: int = 0  # 在论文中的顺序
    page_start: int = 0
    page_end: int = 0
    text: str = ""
    token_count: int = 0

    # 结构化提取（通用）
    claims: list[SectionClaim] = Field(default_factory=list)
    entities: list[SectionEntity] = Field(default_factory=list)
    figures: list[FigureRef] = Field(default_factory=list)
    tables: list[TableRef] = Field(default_factory=list)

    # 引言专属字段（section_type == INTRODUCTION 时填充）
    background_points: list[str] = Field(default_factory=list)  # 背景要点
    motivation_points: list[str] = Field(default_factory=list)  # 动机要点
    gap_points: list[str] = Field(default_factory=list)  # 研究空白
    contribution_points: list[str] = Field(default_factory=list)  # 贡献列表
    prior_work_refs: list[str] = Field(default_factory=list)  # 引言中提及的前人文献 ID

    chunk_ids: list[str] = Field(default_factory=list)  # 关联的 L3 chunk
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Reference(BaseModel):
    """结构化参考文献条目"""
    ref_id: str = ""
    paper_id: str = ""
    index: int = 0
    raw_text: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""


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
    table_count: int = 0
    figure_count: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
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


# ── 类型化知识图谱节点 ─────────────────────────────────


class KGNodeBase(BaseModel):
    """KG 节点基类"""
    node_id: str
    node_type: NodeType
    label: str = ""
    description: str = ""
    confidence: float = 1.0
    source_paper_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class PaperNode(KGNodeBase):
    node_type: Literal[NodeType.PAPER] = NodeType.PAPER
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    abstract: str = ""
    citation_count: int = 0
    fwci: float = 0.0


class TaskNode(KGNodeBase):
    node_type: Literal[NodeType.TASK] = NodeType.TASK
    task_domain: str = ""


class MethodNode(KGNodeBase):
    node_type: Literal[NodeType.METHOD] = NodeType.METHOD
    method_type: str = ""  # model/algorithm/framework/technique
    input_type: str = ""
    output_type: str = ""


class MaterialNode(KGNodeBase):
    node_type: Literal[NodeType.DATASET] = NodeType.DATASET
    data_type: str = ""
    size: str = ""
    domain: str = ""


class MetricNode(KGNodeBase):
    node_type: Literal[NodeType.METRIC] = NodeType.METRIC
    metric_type: str = ""  # accuracy/efficiency/quality
    higher_is_better: bool = True


class FindingNode(KGNodeBase):
    node_type: Literal[NodeType.FINDING] = NodeType.FINDING
    evidence_quote: str = ""
    source_chunk_id: str = ""
    evidence_strength: str = "medium"


class LimitationNode(KGNodeBase):
    node_type: Literal[NodeType.LIMITATION] = NodeType.LIMITATION
    limitation_type: str = ""
    evidence_quote: str = ""


class GapNode(KGNodeBase):
    node_type: Literal[NodeType.GAP] = NodeType.GAP
    gap_type: str = ""
    potential_impact: str = ""


class TopicNode(KGNodeBase):
    node_type: Literal[NodeType.TOPIC] = NodeType.TOPIC
    keywords: list[str] = Field(default_factory=list)


class AuthorNode(KGNodeBase):
    node_type: Literal[NodeType.AUTHOR] = NodeType.AUTHOR
    affiliations: list[str] = Field(default_factory=list)
    h_index: int = 0


class VenueNode(KGNodeBase):
    node_type: Literal[NodeType.VENUE] = NodeType.VENUE
    venue_type: str = ""  # journal/conference/workshop
    impact_factor: float = 0.0


class InnovationNode(KGNodeBase):
    node_type: Literal[NodeType.INNOVATION] = NodeType.INNOVATION
    innovation_type: str = ""
    why_innovative: str = ""
    feasibility: str = ""
    risk: str = ""
    supporting_papers: list[str] = Field(default_factory=list)


class KGEdge(BaseModel):
    """类型化 KG 边"""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    confidence: float = 1.0
    evidence: str = ""  # 支撑文本引用
    source_chunk_id: str = ""
    source_paper_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


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
