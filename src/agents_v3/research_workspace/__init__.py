"""研究工作空间模块 - 论文知识库分析 Agent 核心"""

from src.agents_v3.research_workspace.llm_service import LLMConfig, LLMService, LLMCallResult, FakeLLMService, get_llm_service
from src.agents_v3.research_workspace.llm_errors import (
    LLMServiceError, LLMProviderError, LLMTimeoutError, LLMRateLimitError,
    EmptyLLMResponseError, JsonExtractionError, StructuredOutputError, JsonRepairError,
)
from src.agents_v3.research_workspace.prompt_registry import PromptRegistry, PromptTemplateSpec, get_prompt_registry
from src.agents_v3.research_workspace.search import (
    ArxivClient,
    BaseSearchAdapter,
    SearchQuery,
    SearchResult,
)
from src.agents_v3.research_workspace.models import (
    CardQualityReport,
    ChunkType,
    EvidenceRecord,
    ExtractedClaim,
    GraphEdge,
    GraphNode,
    InnovationPoint,
    KnowledgeGraph,
    NodeType,
    EdgeType,
    Paper,
    PaperCard,
    PaperCardExtractionResult,
    PaperChunk,
    PaperStatus,
    ParseResult,
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
    "ChunkType",
    "LLMConfig",
    "LLMService",
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
    "ParseResult",
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
