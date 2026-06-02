"""数据模型子包 — re-export 全部公共类"""

from src.agents_v3.research_workspace.models.enums import (
    ChunkType,
    EdgeType,
    NodeType,
    PaperStatus,
    ReportType,
    ScopeType,
    SectionType,
)
from src.agents_v3.research_workspace.models.paper import (
    Author,
    CitationInfo,
    OpenAccessInfo,
    Paper,
    PaperChunk,
    PaperClassification,
    PaperDates,
    PaperIdentifiers,
    PaperSource,
    ParseResult,
)
from src.agents_v3.research_workspace.models.paper_profile import (
    CitationContext,
    FigureRef,
    KeyResult,
    PaperProfile,
    PaperSection,
    Reference,
    SectionClaim,
    SectionEntity,
    TableRef,
)
from src.agents_v3.research_workspace.models.knowledge_graph import (
    AuthorNode,
    FindingNode,
    GapNode,
    GraphEdge,
    GraphNode,
    InnovationNode,
    KGEdge,
    KGNodeBase,
    KnowledgeGraph,
    LimitationNode,
    MaterialNode,
    MethodNode,
    MetricNode,
    PaperNode,
    TaskNode,
    TopicNode,
    VenueNode,
)
from src.agents_v3.research_workspace.models.reports import (
    CardQualityReport,
    EvidenceRecord,
    ExtractedClaim,
    InnovationPoint,
    PaperCard,
    PaperCardExtractionResult,
    Project,
    QARequest,
    QAResponse,
    Report,
    ReportVersion,
    RetrievalDiagnostics,
    RetrievalResult,
    RetrievalScope,
    SourceSpan,
)

__all__ = [
    # enums
    "ChunkType", "EdgeType", "NodeType", "PaperStatus", "ReportType",
    "ScopeType", "SectionType",
    # paper
    "Author", "CitationInfo", "OpenAccessInfo", "Paper", "PaperChunk",
    "PaperClassification", "PaperDates", "PaperIdentifiers", "PaperSource",
    "ParseResult",
    # paper_profile
    "CitationContext", "FigureRef", "KeyResult", "PaperProfile", "PaperSection",
    "Reference", "SectionClaim", "SectionEntity", "TableRef",
    # knowledge_graph
    "AuthorNode", "FindingNode", "GapNode", "GraphEdge", "GraphNode",
    "InnovationNode", "KGEdge", "KGNodeBase", "KnowledgeGraph",
    "LimitationNode", "MaterialNode", "MethodNode", "MetricNode",
    "PaperNode", "TaskNode", "TopicNode", "VenueNode",
    # reports
    "CardQualityReport", "EvidenceRecord", "ExtractedClaim", "InnovationPoint",
    "PaperCard", "PaperCardExtractionResult", "Project", "QARequest",
    "QAResponse", "Report", "ReportVersion", "RetrievalDiagnostics",
    "RetrievalResult", "RetrievalScope", "SourceSpan",
]
