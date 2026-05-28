"""研究工作空间模块 - 论文知识库分析 Agent 核心"""

from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    GraphEdge,
    GraphNode,
    InnovationPoint,
    KnowledgeGraph,
    NodeType,
    EdgeType,
    Paper,
    PaperCard,
    PaperChunk,
    PaperStatus,
    Project,
    QARequest,
    QAResponse,
    Report,
    ReportType,
    ReportVersion,
    RetrievalScope,
    ScopeType,
)
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage
from src.agents_v3.research_workspace.project_service import ProjectService
from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.parser_service import ParserService
from src.agents_v3.research_workspace.paper_card import PaperCardGenerator
from src.agents_v3.research_workspace.evidence_table import EvidenceTableService
from src.agents_v3.research_workspace.graph_service import GraphService
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.scope_qa import ScopeQAService
from src.agents_v3.research_workspace.review_generator import LiteratureReviewGenerator
from src.agents_v3.research_workspace.innovation_generator import InnovationReportGenerator
from src.agents_v3.research_workspace.report_service import ReportService

__all__ = [
    "EvidenceRecord",
    "EvidenceTableService",
    "GraphEdge",
    "GraphNode",
    "GraphService",
    "InnovationPoint",
    "InnovationReportGenerator",
    "JSONStorage",
    "KnowledgeGraph",
    "LiteratureReviewGenerator",
    "NodeType",
    "EdgeType",
    "Paper",
    "PaperCard",
    "PaperCardGenerator",
    "PaperChunk",
    "PaperLibraryService",
    "PaperStatus",
    "ParserService",
    "Project",
    "ProjectService",
    "QARequest",
    "QAResponse",
    "Report",
    "ReportService",
    "ReportType",
    "ReportVersion",
    "RetrievalScope",
    "RetrievalScopeService",
    "ScopeQAService",
    "ScopeType",
    "get_storage",
]
