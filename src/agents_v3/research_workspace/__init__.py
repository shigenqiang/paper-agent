"""研究工作空间模块 - 论文知识库分析 Agent 核心"""

# ── LLM 子包 ──────────────────────────────────────
from src.agents_v3.research_workspace.llm.service import (
    LLMConfig, LLMService, LLMCallResult, FakeLLMService, get_llm_service, reset_llm_service,
)
from src.agents_v3.research_workspace.llm.errors import (
    LLMServiceError, LLMProviderError, LLMTimeoutError, LLMRateLimitError,
    EmptyLLMResponseError, JsonExtractionError, StructuredOutputError, JsonRepairError,
)
from src.agents_v3.research_workspace.llm.prompts import PromptRegistry, PromptTemplateSpec, get_prompt_registry

# ── 搜索子包 ──────────────────────────────────────
from src.agents_v3.research_workspace.search import (
    ArxivClient, BaseSearchAdapter, SearchQuery, SearchResult,
)

# ── 核心模型 ──────────────────────────────────────
from src.agents_v3.research_workspace.models import (
    CardQualityReport, ChunkType, EvidenceRecord, ExtractedClaim,
    GraphEdge, GraphNode, InnovationPoint, KnowledgeGraph,
    NodeType, EdgeType, Paper, PaperCard, PaperCardExtractionResult,
    PaperChunk, PaperStatus, ParseResult, Project,
    QARequest, QAResponse, Report, ReportType, ReportVersion,
    RetrievalDiagnostics, RetrievalResult, RetrievalScope, ScopeType,
)

# ── 存储 ──────────────────────────────────────────
from src.agents_v3.research_workspace.storage import (
    JSONStorage, StorageBackend, PostgresStorage, VectorStorage,
    get_storage, get_project_storage, get_postgres_storage, get_vector_storage,
    sanitize_dirname, unique_dirname, load_all_projects, resolve_project_ref,
    list_project_dirs, remove_project_storage, rename_project_storage,
)

# ── 核心业务服务 ──────────────────────────────────
from src.agents_v3.research_workspace.services.project_service import ProjectService
from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.parser.service import ParserService
from src.agents_v3.research_workspace.services.paper_card import PaperCardGenerator
from src.agents_v3.research_workspace.services.evidence_table import EvidenceTableService
from src.agents_v3.research_workspace.services.graph_service import GraphService
from src.agents_v3.research_workspace.services.scope import RetrievalScopeService
from src.agents_v3.research_workspace.services.scope_qa import ScopeQAService
from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
from src.agents_v3.research_workspace.services.hierarchical_retriever import HierarchicalRetriever
from src.agents_v3.research_workspace.services.report_service import ReportService

# ── 评估子包 ──────────────────────────────────────
from src.agents_v3.research_workspace.evaluation.evaluator import EvaluationResult
from src.agents_v3.research_workspace.evaluation.gates import QualityGateResult, QualityGateSummary
from src.agents_v3.research_workspace.evaluation.metrics import MetricRecord, MetricsCollector

# ── API 子包 ──────────────────────────────────────
from src.agents_v3.research_workspace.api.app import app, create_app
from src.agents_v3.research_workspace.api.tasks import TaskService

__all__ = [
    "ArxivClient", "BaseSearchAdapter", "CardQualityReport", "ChunkType",
    "EvaluationResult", "EvidenceRecord", "ExtractedClaim", "FakeLLMService",
    "GraphEdge", "GraphNode", "HierarchicalRetriever", "InnovationPoint", "InnovationReportGenerator",
    "JSONStorage", "KnowledgeGraph", "LLMCallResult", "LLMConfig",
    "LLMProviderError", "LLMRateLimitError", "LLMService", "LLMServiceError",
    "LLMTimeoutError", "LiteratureReviewGenerator", "MetricRecord",
    "MetricsCollector", "NodeType", "EdgeType", "Paper", "PaperCard",
    "PaperCardExtractionResult", "PaperCardGenerator", "PaperChunk",
    "PaperLibraryService", "PaperStatus", "ParseResult", "ParserService",
    "PostgresStorage", "Project", "ProjectService", "PromptRegistry", "PromptTemplateSpec",
    "QARequest", "QAResponse", "QualityGateResult", "QualityGateSummary",
    "Report", "ReportService", "ReportType", "ReportVersion",
    "RetrievalDiagnostics", "RetrievalResult", "RetrievalScope", "RetrievalScopeService",
    "ScopeQAService", "ScopeType",
    "SearchQuery", "SearchResult", "StorageBackend", "TaskService",
    "VectorStorage", "app", "create_app", "get_llm_service", "get_postgres_storage",
    "get_project_storage", "get_prompt_registry", "get_storage", "get_vector_storage",
    "reset_llm_service",
]
