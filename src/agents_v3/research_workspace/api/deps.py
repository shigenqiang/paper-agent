"""API 依赖注入"""

from __future__ import annotations

from typing import Any

from loguru import logger

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


# ── 存储后端选择 ──

def _load_config() -> dict[str, Any]:
    """加载配置文件"""
    import yaml
    from pathlib import Path
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_config = _load_config()
_postgres_storage = None


def _get_postgres_storage():
    """获取 PostgreSQL 存储实例（单例）"""
    global _postgres_storage
    if _postgres_storage is not None:
        return _postgres_storage

    pg_config = _config.get("database", {}).get("postgres", {})
    if not pg_config.get("enabled", False):
        return None

    try:
        from src.agents_v3.research_workspace.postgres_storage import PostgresStorage
        dsn = pg_config.get("dsn")
        if dsn:
            _postgres_storage = PostgresStorage(dsn=dsn)
        else:
            _postgres_storage = PostgresStorage(
                host=pg_config.get("host", "localhost"),
                port=pg_config.get("port", 5432),
                database=pg_config.get("database", "paper_agent"),
                user=pg_config.get("user", "postgres"),
                password=pg_config.get("password", ""),
            )
        return _postgres_storage
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None


def get_storage_backend():
    """获取存储后端（PostgreSQL 或 JSON）"""
    backend = _config.get("storage_backend", "json")
    if backend == "postgres":
        pg = _get_postgres_storage()
        if pg:
            return pg
        logger.warning("PostgreSQL not available, falling back to JSON storage")
    return None  # None 表示使用 JSONStorage


# ── 全局存储（tasks, queries） ──

def get_storage_dep():
    backend = get_storage_backend()
    return backend or get_storage()


def get_project_service() -> ProjectService:
    backend = get_storage_backend()
    if backend:
        return ProjectService(storage=backend)
    return ProjectService(storage=get_storage())


def get_task_service() -> TaskService:
    backend = get_storage_backend()
    if backend:
        return TaskService(storage=backend)
    return TaskService(storage=get_storage())


# ── 项目作用域解析 ──

def _resolve_project_storage(project_ref: str):
    """通过 project_id 或 dir_name 解析到项目存储"""
    backend = get_storage_backend()
    if backend:
        return backend
    dir_name = resolve_project_ref(project_ref, get_storage().data_dir)
    return get_project_storage(dir_name)


# ── 项目作用域服务 ──

def get_paper_library(project_ref: str) -> PaperLibraryService:
    from src.agents_v3.research_workspace.search.factory import create_default_adapters
    adapters = list(create_default_adapters().values())
    storage = _resolve_project_storage(project_ref)
    global_storage = get_storage_backend() or get_storage()
    pg = _get_postgres_storage()
    return PaperLibraryService(storage=storage, search_adapters=adapters, global_storage=global_storage, pg_storage=pg)


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
