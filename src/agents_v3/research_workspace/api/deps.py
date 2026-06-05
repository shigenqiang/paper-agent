"""API 依赖注入"""

from __future__ import annotations

from loguru import logger

from src.agents_v3.research_workspace.services.evidence_table import EvidenceTableService
from src.agents_v3.research_workspace.services.graph_extractor import GraphExtractor
from src.agents_v3.research_workspace.services.graph_service import GraphService
from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator
from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.services.paper_card import PaperCardGenerator
from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.parser.service import ParserService
from src.agents_v3.research_workspace.services.project_service import ProjectService
from src.agents_v3.research_workspace.services.report_service import ReportService
from src.agents_v3.research_workspace.services.review_generator import LiteratureReviewGenerator
from src.agents_v3.research_workspace.services.scope import RetrievalScopeService
from src.agents_v3.research_workspace.services.scope_qa import ScopeQAService
from src.agents_v3.research_workspace.storage import get_storage
from src.agents_v3.research_workspace.api.tasks import TaskService


# ── 依赖工厂 ──

def get_storage_dep():
    return get_storage()


def get_project_service() -> ProjectService:
    return ProjectService(storage=get_storage())


def get_task_service() -> TaskService:
    return TaskService(storage=get_storage())


def get_paper_library(project_ref: str) -> PaperLibraryService:
    from src.agents_v3.research_workspace.search.factory import create_default_adapters
    adapters = list(create_default_adapters().values())
    storage = get_storage()
    return PaperLibraryService(storage=storage, search_adapters=adapters, global_storage=storage, pg_storage=storage)


def get_parser_service(project_ref: str) -> ParserService:
    return ParserService(storage=get_storage())


def get_card_generator(project_ref: str) -> PaperCardGenerator:
    return PaperCardGenerator(storage=get_storage())


def get_evidence_service(project_ref: str) -> EvidenceTableService:
    return EvidenceTableService(storage=get_storage())


def get_graph_service(project_ref: str) -> GraphService:
    return GraphService(storage=get_storage())


def get_graph_extractor(project_ref: str) -> GraphExtractor:
    return GraphExtractor(storage=get_storage())


def get_scope_service(project_ref: str) -> RetrievalScopeService:
    return RetrievalScopeService(storage=get_storage())


def get_qa_service(project_ref: str) -> ScopeQAService:
    return ScopeQAService(storage=get_storage())


def get_review_generator(project_ref: str) -> LiteratureReviewGenerator:
    return LiteratureReviewGenerator(storage=get_storage())


def get_innovation_generator(project_ref: str) -> InnovationReportGenerator:
    return InnovationReportGenerator(storage=get_storage())


def get_report_service(project_ref: str) -> ReportService:
    return ReportService(storage=get_storage())


def get_llm() -> LLMService:
    return get_llm_service()
