"""API 依赖注入"""

from __future__ import annotations

from pathlib import Path

from src.agents_v3.research_workspace.evidence_table import EvidenceTableService
from src.agents_v3.research_workspace.graph_service import GraphService
from src.agents_v3.research_workspace.innovation_generator import InnovationReportGenerator
from src.agents_v3.research_workspace.llm_service import LLMService, get_llm_service
from src.agents_v3.research_workspace.paper_card import PaperCardGenerator
from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.parser_service import ParserService
from src.agents_v3.research_workspace.project_service import ProjectService
from src.agents_v3.research_workspace.report_service import ReportService
from src.agents_v3.research_workspace.review_generator import LiteratureReviewGenerator
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.scope_qa import ScopeQAService
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage
from src.agents_v3.research_workspace.task_service import TaskService


def get_storage_dep() -> JSONStorage:
    return get_storage()


def get_project_service(storage: JSONStorage | None = None) -> ProjectService:
    return ProjectService(storage=storage or get_storage())


def get_paper_library(storage: JSONStorage | None = None) -> PaperLibraryService:
    return PaperLibraryService(storage=storage or get_storage())


def get_parser_service(storage: JSONStorage | None = None) -> ParserService:
    return ParserService(storage=storage or get_storage())


def get_card_generator(storage: JSONStorage | None = None) -> PaperCardGenerator:
    return PaperCardGenerator(storage=storage or get_storage())


def get_evidence_service(storage: JSONStorage | None = None) -> EvidenceTableService:
    return EvidenceTableService(storage=storage or get_storage())


def get_graph_service(storage: JSONStorage | None = None) -> GraphService:
    return GraphService(storage=storage or get_storage())


def get_scope_service(storage: JSONStorage | None = None) -> RetrievalScopeService:
    return RetrievalScopeService(storage=storage or get_storage())


def get_qa_service(storage: JSONStorage | None = None) -> ScopeQAService:
    return ScopeQAService(storage=storage or get_storage())


def get_review_generator(storage: JSONStorage | None = None) -> LiteratureReviewGenerator:
    return LiteratureReviewGenerator(storage=storage or get_storage())


def get_innovation_generator(storage: JSONStorage | None = None) -> InnovationReportGenerator:
    return InnovationReportGenerator(storage=storage or get_storage())


def get_report_service(storage: JSONStorage | None = None) -> ReportService:
    return ReportService(storage=storage or get_storage())


def get_task_service(storage: JSONStorage | None = None) -> TaskService:
    return TaskService(storage=storage or get_storage())


def get_llm() -> LLMService:
    return get_llm_service()
