"""API 子包"""

from src.agents_v3.research_workspace.api.app import app, create_app
from src.agents_v3.research_workspace.api.deps import (
    get_card_generator,
    get_evidence_service,
    get_graph_service,
    get_innovation_generator,
    get_llm,
    get_paper_library,
    get_parser_service,
    get_project_service,
    get_qa_service,
    get_report_service,
    get_review_generator,
    get_scope_service,
    get_storage_dep,
    get_task_service,
)
from src.agents_v3.research_workspace.api.errors import (
    APIError,
    NotFoundError,
    ScopeEmptyError,
    TaskNotFoundError,
    ValidationError,
    api_error_handler,
    generic_error_handler,
)
from src.agents_v3.research_workspace.api.models import (
    ApiErrorResponse,
    ApiErrorBody,
    ApiListResponse,
    ApiMeta,
    ApiResponse,
    PageInfo,
    PaperImportBibtexRequest,
    PaperImportDoiRequest,
    PaperUpdateRequest,
    PaperUploadRequest,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    QARequest,
    ReportGenerateRequest,
    ScopeResolveRequest,
    SearchCommitRequest,
    SearchPapersRequest,
    TaskResponse,
)
from src.agents_v3.research_workspace.api.tasks import TaskService

__all__ = [
    "APIError", "ApiErrorResponse", "ApiErrorBody", "ApiListResponse", "ApiMeta",
    "ApiResponse", "NotFoundError", "PageInfo", "PaperImportBibtexRequest",
    "PaperImportDoiRequest", "PaperUpdateRequest", "PaperUploadRequest",
    "ProjectCreateRequest", "ProjectUpdateRequest", "QARequest", "ReportGenerateRequest",
    "ScopeEmptyError", "ScopeResolveRequest", "SearchCommitRequest", "SearchPapersRequest",
    "TaskNotFoundError", "TaskResponse", "TaskService", "ValidationError",
    "api_error_handler", "app", "create_app", "generic_error_handler",
    "get_card_generator", "get_evidence_service", "get_graph_service",
    "get_innovation_generator", "get_llm", "get_paper_library", "get_parser_service",
    "get_project_service", "get_qa_service", "get_report_service",
    "get_review_generator", "get_scope_service", "get_storage_dep", "get_task_service",
]
