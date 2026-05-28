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
    RetrievalScope, ScopeType,
)

# ── 存储 ──────────────────────────────────────────
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage

# ── 核心业务服务 ──────────────────────────────────
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
    "GraphEdge", "GraphNode", "InnovationPoint", "InnovationReportGenerator",
    "JSONStorage", "KnowledgeGraph", "LLMCallResult", "LLMConfig",
    "LLMProviderError", "LLMRateLimitError", "LLMService", "LLMServiceError",
    "LLMTimeoutError", "LiteratureReviewGenerator", "MetricRecord",
    "MetricsCollector", "NodeType", "EdgeType", "Paper", "PaperCard",
    "PaperCardExtractionResult", "PaperCardGenerator", "PaperChunk",
    "PaperLibraryService", "PaperStatus", "ParseResult", "ParserService",
    "Project", "ProjectService", "PromptRegistry", "PromptTemplateSpec",
    "QARequest", "QAResponse", "QualityGateResult", "QualityGateSummary",
    "Report", "ReportService", "ReportType", "ReportVersion",
    "RetrievalScope", "RetrievalScopeService", "ScopeQAService", "ScopeType",
    "SearchQuery", "SearchResult", "TaskService", "app", "create_app",
    "get_llm_service", "get_prompt_registry", "get_storage", "reset_llm_service",
]
