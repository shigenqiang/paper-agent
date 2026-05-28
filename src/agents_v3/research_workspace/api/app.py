"""FastAPI 应用与路由"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from loguru import logger

from src.agents_v3.research_workspace.api.deps import (
    get_card_generator,
    get_evidence_service,
    get_graph_service,
    get_innovation_generator,
    get_paper_library,
    get_parser_service,
    get_project_service,
    get_qa_service,
    get_report_service,
    get_review_generator,
    get_scope_service,
    get_task_service,
)
from src.agents_v3.research_workspace.api.errors import (
    APIError,
    NotFoundError,
    api_error_handler,
    generic_error_handler,
)
from src.agents_v3.research_workspace.api.models import (
    ApiMeta,
    ApiResponse,
    PaperImportBibtexRequest,
    PaperImportDoiRequest,
    PaperUpdateRequest,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    QARequest,
    ReportGenerateRequest,
    ScopeResolveRequest,
    SearchCommitRequest,
    SearchPapersRequest,
    TaskResponse,
)
from src.agents_v3.research_workspace.search.base import SearchQuery


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期管理"""
    logger.info("Service starting up")
    yield
    # ── 关闭时清理 ──
    from src.agents_v3.research_workspace.storage import _global_storage, _project_storages
    logger.info(f"Service shutting down, {_project_storages.__len__()} project caches to clear")
    _project_storages.clear()
    logger.info("Cleanup done")


def _resolve_project(project_ref: str):
    """解析 project_ref 得到 Project 对象，找不到则抛 NotFoundError"""
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


def create_app(storage=None) -> FastAPI:
    if storage is not None:
        from src.agents_v3.research_workspace.api import deps as deps_module
        deps_module.get_storage = lambda: storage

    app = FastAPI(
        lifespan=lifespan,
        title="Paper Agent Research Workspace API",
        version="3.0.0",
        description="论文知识库分析 Agent API",
        swagger_ui_parameters={
            "swagger_js_url": "https://cdn.staticfile.net/swagger-ui-dist/5.11.0/swagger-ui-bundle.js",
            "swagger_css_url": "https://cdn.staticfile.net/swagger-ui-dist/5.11.0/swagger-ui.css",
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        duration = int((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Duration-Ms"] = str(duration)
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "3.0.0"}

    # ── 项目管理 ──

    @app.post("/api/rw/projects", status_code=201)
    def create_project(req: ProjectCreateRequest):
        svc = get_project_service()
        project = svc.create_project(
            name=req.name,
            description=req.description,
            discipline=req.discipline,
            education_level=req.education_level,
            research_goal=req.research_goal,
        )
        return ApiResponse(data=project.model_dump())

    @app.get("/api/rw/projects")
    def list_projects():
        svc = get_project_service()
        projects = svc.list_projects()
        return ApiResponse(data=[p.model_dump() for p in projects])

    @app.get("/api/rw/projects/{project_ref}")
    def get_project(project_ref: str):
        project = _resolve_project(project_ref)
        return ApiResponse(data=project.model_dump())

    @app.patch("/api/rw/projects/{project_ref}")
    def update_project(project_ref: str, req: ProjectUpdateRequest):
        project = _resolve_project(project_ref)
        svc = get_project_service()
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        updated = svc.update_project(project.project_id, **updates)
        if not updated:
            raise NotFoundError("project", project_ref)
        return ApiResponse(data=updated.model_dump())

    @app.get("/api/rw/projects/{project_ref}/stats")
    def get_project_stats(project_ref: str):
        svc = get_project_service()
        stats = svc.get_project_stats(project_ref)
        return ApiResponse(data=stats)

    @app.delete("/api/rw/projects/{project_ref}", status_code=200)
    def delete_project(project_ref: str):
        project = _resolve_project(project_ref)
        svc = get_project_service()
        ok = svc.delete_project(project.project_id)
        if not ok:
            raise NotFoundError("project", project_ref)
        return ApiResponse(data={"deleted": True})

    # ── 论文库 ──

    @app.get("/api/rw/projects/{project_ref}/papers")
    def list_papers(project_ref: str, status: str | None = None, included: bool | None = None):
        project = _resolve_project(project_ref)
        svc = get_paper_library(project_ref)
        filters = {}
        if status:
            filters["status"] = status
        if included is not None:
            filters["included"] = included
        papers = svc.list_papers(project.project_id, filters or None)
        return ApiResponse(data=[p.model_dump() for p in papers])

    @app.post("/api/rw/projects/{project_ref}/papers/import/doi")
    def import_doi(project_ref: str, req: PaperImportDoiRequest):
        project = _resolve_project(project_ref)
        svc = get_paper_library(project_ref)
        papers = svc.import_doi_list(project.project_id, req.dois)
        return ApiResponse(data=[p.model_dump() for p in papers])

    @app.post("/api/rw/projects/{project_ref}/papers/import/bibtex")
    def import_bibtex(project_ref: str, req: PaperImportBibtexRequest):
        project = _resolve_project(project_ref)
        svc = get_paper_library(project_ref)
        papers = svc.import_bibtex(project.project_id, req.bibtex)
        return ApiResponse(data=[p.model_dump() for p in papers])

    @app.get("/api/rw/projects/{project_ref}/papers/{paper_id}")
    def get_paper(project_ref: str, paper_id: str):
        svc = get_paper_library(project_ref)
        paper = svc.get_paper(paper_id)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.patch("/api/rw/projects/{project_ref}/papers/{paper_id}")
    def update_paper(project_ref: str, paper_id: str, req: PaperUpdateRequest):
        svc = get_paper_library(project_ref)
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        paper = svc.update_paper(paper_id, **updates)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.post("/api/rw/projects/{project_ref}/papers/{paper_id}/include")
    def include_paper(project_ref: str, paper_id: str):
        svc = get_paper_library(project_ref)
        paper = svc.mark_included(paper_id)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.post("/api/rw/projects/{project_ref}/papers/{paper_id}/exclude")
    def exclude_paper(project_ref: str, paper_id: str, reason: str = ""):
        svc = get_paper_library(project_ref)
        paper = svc.mark_excluded(paper_id, reason)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.post("/api/rw/projects/{project_ref}/papers/search")
    def search_papers(project_ref: str, req: SearchPapersRequest):
        project = _resolve_project(project_ref)
        svc = get_paper_library(project_ref)
        query = SearchQuery(
            query=req.query, sources=req.sources, limit=req.limit,
            year_from=req.year_from, year_to=req.year_to, use_cache=req.use_cache,
        )
        session = svc.search_candidates(project.project_id, query)
        return ApiResponse(data={
            "session_id": session.session_id,
            "results": [r.model_dump(exclude_defaults=True) for r in session.results],
            "result_count": len(session.results),
        })

    @app.post("/api/rw/projects/{project_ref}/papers/search/commit")
    def commit_search(project_ref: str, req: SearchCommitRequest):
        project = _resolve_project(project_ref)
        svc = get_paper_library(project_ref)
        papers = svc.commit_search_results(project.project_id, req.session_id, req.selected_result_ids)
        return ApiResponse(data=[p.model_dump() for p in papers])

    # ── 解析 ──

    @app.post("/api/rw/projects/{project_ref}/papers/{paper_id}/parse")
    def parse_paper(project_ref: str, paper_id: str):
        svc = get_parser_service(project_ref)
        result = svc.parse_paper(paper_id)
        return ApiResponse(data=result)

    @app.post("/api/rw/projects/{project_ref}/papers/parse")
    def parse_project_papers(project_ref: str):
        project = _resolve_project(project_ref)
        svc = get_parser_service(project_ref)
        result = svc.parse_project_papers(project.project_id)
        return ApiResponse(data=result)

    # ── 知识提取 ──

    @app.post("/api/rw/projects/{project_ref}/cards")
    def generate_cards(project_ref: str, only_missing: bool = True):
        project = _resolve_project(project_ref)
        svc = get_card_generator(project_ref)
        cards = svc.batch_generate(project.project_id, only_missing=only_missing)
        return ApiResponse(data=[c.model_dump() for c in cards])

    @app.post("/api/rw/projects/{project_ref}/evidence/build")
    def build_evidence(project_ref: str):
        project = _resolve_project(project_ref)
        svc = get_evidence_service(project_ref)
        records = svc.build_for_project(project.project_id)
        return ApiResponse(data=[e.model_dump() for e in records])

    # ── 知识图谱 ──

    @app.post("/api/rw/projects/{project_ref}/kg/build")
    def build_graph(project_ref: str):
        project = _resolve_project(project_ref)
        svc = get_graph_service(project_ref)
        graph = svc.build_project_graph(project.project_id)
        return ApiResponse(data={"node_count": len(graph.nodes), "edge_count": len(graph.edges)})

    @app.get("/api/rw/projects/{project_ref}/kg")
    def get_graph(project_ref: str):
        project = _resolve_project(project_ref)
        svc = get_graph_service(project_ref)
        graph = svc.get_graph(project.project_id)
        return ApiResponse(data={
            "nodes": [n.model_dump() for n in graph.nodes],
            "edges": [e.model_dump() for e in graph.edges],
        })

    @app.get("/api/rw/projects/{project_ref}/kg/stats")
    def get_graph_stats(project_ref: str):
        project = _resolve_project(project_ref)
        svc = get_graph_service(project_ref)
        return ApiResponse(data=svc.get_stats(project.project_id))

    @app.post("/api/rw/projects/{project_ref}/kg/subgraph")
    def get_subgraph(project_ref: str, node_ids: list[str], hops: int = 1):
        project = _resolve_project(project_ref)
        svc = get_graph_service(project_ref)
        return ApiResponse(data=svc.get_subgraph(project.project_id, node_ids, hops=hops))

    @app.get("/api/rw/projects/{project_ref}/kg/gaps")
    def find_gaps(project_ref: str, min_confidence: float = 0.5):
        project = _resolve_project(project_ref)
        svc = get_graph_service(project_ref)
        return ApiResponse(data=svc.find_gaps(project.project_id, min_confidence=min_confidence))

    # ── Scope QA ──

    @app.post("/api/rw/projects/{project_ref}/scope/resolve")
    def resolve_scope(project_ref: str, req: ScopeResolveRequest):
        project = _resolve_project(project_ref)
        svc = get_scope_service(project_ref)
        return ApiResponse(data=svc.resolve(project.project_id, req.model_dump()).model_dump())

    @app.get("/api/rw/projects/{project_ref}/scope/filters")
    def get_scope_filters(project_ref: str):
        project = _resolve_project(project_ref)
        svc = get_scope_service(project_ref)
        return ApiResponse(data=svc.get_scope_filters(project.project_id))

    @app.post("/api/rw/projects/{project_ref}/qa")
    def ask_question(project_ref: str, req: QARequest):
        project = _resolve_project(project_ref)
        svc = get_qa_service(project_ref)
        response = svc.answer(project.project_id, req.question, req.scope.model_dump())
        return ApiResponse(data=response.model_dump())

    # ── 报告 ──

    @app.get("/api/rw/projects/{project_ref}/reports")
    def list_reports(project_ref: str, type: str | None = None):
        project = _resolve_project(project_ref)
        svc = get_report_service(project_ref)
        return ApiResponse(data=[r.model_dump() for r in svc.list_reports(project.project_id, type)])

    @app.get("/api/rw/projects/{project_ref}/reports/{report_id}")
    def get_report(project_ref: str, report_id: str):
        svc = get_report_service(project_ref)
        report = svc.get_report(report_id)
        if not report:
            raise NotFoundError("report", report_id)
        return ApiResponse(data=report.model_dump())

    @app.post("/api/rw/projects/{project_ref}/reports/literature-review")
    def generate_review(project_ref: str, req: ReportGenerateRequest):
        project = _resolve_project(project_ref)
        svc = get_review_generator(project_ref)
        return ApiResponse(data=svc.generate(project.project_id, req.scope.model_dump(), req.options).model_dump())

    @app.post("/api/rw/projects/{project_ref}/reports/innovation")
    def generate_innovation(project_ref: str, req: ReportGenerateRequest):
        project = _resolve_project(project_ref)
        svc = get_innovation_generator(project_ref)
        return ApiResponse(data=svc.generate(project.project_id, req.scope.model_dump(), req.options).model_dump())

    @app.get("/api/rw/projects/{project_ref}/reports/{report_id}/export/markdown")
    def export_markdown(project_ref: str, report_id: str):
        svc = get_report_service(project_ref)
        md = svc.export_markdown(report_id)
        if not md:
            raise NotFoundError("report", report_id)
        return {"content": md, "format": "markdown"}

    @app.get("/api/rw/projects/{project_ref}/reports/{report_id}/export/json")
    def export_json(project_ref: str, report_id: str):
        svc = get_report_service(project_ref)
        data = svc.export_json(report_id)
        if not data or data == "{}":
            raise NotFoundError("report", report_id)
        return {"content": data, "format": "json"}

    # ── 任务 ──

    @app.get("/api/rw/tasks/{task_id}")
    def get_task(task_id: str):
        svc = get_task_service()
        task = svc.get_task(task_id)
        if not task:
            raise NotFoundError("task", task_id)
        return ApiResponse(data=task)

    @app.get("/api/rw/tasks")
    def list_tasks(project_ref: str | None = None, status: str | None = None):
        svc = get_task_service()
        return ApiResponse(data=svc.list_tasks(project_ref, status))

    return app


app = create_app()
