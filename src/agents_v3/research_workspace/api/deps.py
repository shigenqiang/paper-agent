"""API 依赖注入"""

from __future__ import annotations

from src.agents_v3.research_workspace.evidence_table import EvidenceTableService
from src.agents_v3.research_workspace.graph_service import GraphService
from src.agents_v3.research_workspace.innovation_generator import InnovationReportGenerator
from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.paper_card import PaperCardGenerator
from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.parser_service import ParserService
from src.agents_v3.research_workspace.project_service import ProjectService
from src.agents_v3.research_workspace.report_service import ReportService
from src.agents_v3.research_workspace.review_generator import LiteratureReviewGenerator
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.scope_qa import ScopeQAService
from src.agents_v3.research_workspace.storage import (
    JSONStorage,
    get_project_storage,
    get_storage,
    resolve_project_ref,
)
from src.agents_v3.research_workspace.api.tasks import TaskService


# ── 全局存储（tasks, search_cache） ──

def get_storage_dep() -> JSONStorage:
    return get_storage()


def get_project_service() -> ProjectService:
    return ProjectService(storage=get_storage())


def get_task_service() -> TaskService:
    return TaskService(storage=get_storage())


# ── 项目作用域解析 ──

def _resolve_project_storage(project_ref: str) -> JSONStorage:
    """通过 project_id 或 dir_name 解析到项目存储"""
    dir_name = resolve_project_ref(project_ref, get_storage().data_dir)
    return get_project_storage(dir_name)


# ── 项目作用域服务 ──

def get_paper_library(project_ref: str) -> PaperLibraryService:
    from src.agents_v3.research_workspace.search.factory import create_default_adapters
    adapters = list(create_default_adapters().values())
    storage = _resolve_project_storage(project_ref)
    return PaperLibraryService(storage=storage, search_adapters=adapters)


def get_parser_service(project_ref: str) -> ParserService:
    return ParserService(storage=_resolve_project_storage(project_ref))


def get_card_generator(project_ref: str) -> PaperCardGenerator:
    return PaperCardGenerator(storage=_resolve_project_storage(project_ref))


def get_evidence_service(project_ref: str) -> EvidenceTableService:
    return EvidenceTableService(storage=_resolve_project_storage(project_ref))


def get_graph_service(project_ref: str) -> GraphService:
    return GraphService(storage=_resolve_project_storage(project_ref))


def get_scope_service(project_ref: str) -> RetrievalScopeService:
    return RetrievalScopeService(storage=_resolve_project_storage(project_ref))


def get_qa_service(project_ref: str) -> ScopeQAService:
    return ScopeQAService(storage=_resolve_project_storage(project_ref))


def get_review_generator(project_ref: str) -> LiteratureReviewGenerator:
    return LiteratureReviewGenerator(storage=_resolve_project_storage(project_ref))


def get_innovation_generator(project_ref: str) -> InnovationReportGenerator:
    return InnovationReportGenerator(storage=_resolve_project_storage(project_ref))


def get_report_service(project_ref: str) -> ReportService:
    return ReportService(storage=_resolve_project_storage(project_ref))


def get_llm() -> LLMService:
    return get_llm_service()
