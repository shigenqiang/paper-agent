"""FastAPI 应用与路由"""

from __future__ import annotations

import time
import uuid
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
    QARequest,
    ReportGenerateRequest,
    ScopeResolveRequest,
    SearchCommitRequest,
    SearchPapersRequest,
    TaskResponse,
)
from src.agents_v3.research_workspace.search.base import SearchQuery


def create_app(storage=None) -> FastAPI:
    if storage is not None:
        from src.agents_v3.research_workspace.api import deps as deps_module
        deps_module.get_storage = lambda: storage

    app = FastAPI(
        title="Paper Agent Research Workspace API",
        version="3.0.0",
        description="论文知识库分析 Agent API",
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

    @app.post("/api/rw/projects", status_code=201)
    def create_project(req: ProjectCreateRequest):
        svc = get_project_service()
        project = svc.create_project(req.name)
        return ApiResponse(data=project.model_dump())

    @app.get("/api/rw/projects")
    def list_projects():
        svc = get_project_service()
        projects = svc.list_projects()
        return ApiResponse(data=[p.model_dump() for p in projects])

    @app.get("/api/rw/projects/{project_id}")
    def get_project(project_id: str):
        svc = get_project_service()
        project = svc.get_project(project_id)
        if not project:
            raise NotFoundError("project", project_id)
        return ApiResponse(data=project.model_dump())

    @app.get("/api/rw/projects/{project_id}/stats")
    def get_project_stats(project_id: str):
        svc = get_project_service()
        stats = svc.get_project_stats(project_id)
        return ApiResponse(data=stats)

    @app.delete("/api/rw/projects/{project_id}", status_code=200)
    def delete_project(project_id: str):
        svc = get_project_service()
        ok = svc.delete_project(project_id)
        if not ok:
            raise NotFoundError("project", project_id)
        return ApiResponse(data={"deleted": True})

    @app.get("/api/rw/projects/{project_id}/papers")
    def list_papers(project_id: str, status: str | None = None, included: bool | None = None):
        svc = get_paper_library()
        filters = {}
        if status:
            filters["status"] = status
        if included is not None:
            filters["included"] = included
        papers = svc.list_papers(project_id, filters or None)
        return ApiResponse(data=[p.model_dump() for p in papers])

    @app.post("/api/rw/projects/{project_id}/papers/import/doi")
    def import_doi(project_id: str, req: PaperImportDoiRequest):
        svc = get_paper_library()
        papers = svc.import_doi_list(project_id, req.dois)
        return ApiResponse(data=[p.model_dump() for p in papers])

    @app.post("/api/rw/projects/{project_id}/papers/import/bibtex")
    def import_bibtex(project_id: str, req: PaperImportBibtexRequest):
        svc = get_paper_library()
        papers = svc.import_bibtex(project_id, req.bibtex)
        return ApiResponse(data=[p.model_dump() for p in papers])

    @app.get("/api/rw/papers/{paper_id}")
    def get_paper(paper_id: str):
        svc = get_paper_library()
        paper = svc.get_paper(paper_id)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.patch("/api/rw/papers/{paper_id}")
    def update_paper(paper_id: str, req: PaperUpdateRequest):
        svc = get_paper_library()
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        paper = svc.update_paper(paper_id, **updates)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.post("/api/rw/papers/{paper_id}/include")
    def include_paper(paper_id: str):
        svc = get_paper_library()
        paper = svc.mark_included(paper_id)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.post("/api/rw/papers/{paper_id}/exclude")
    def exclude_paper(paper_id: str, reason: str = ""):
        svc = get_paper_library()
        paper = svc.mark_excluded(paper_id, reason)
        if not paper:
            raise NotFoundError("paper", paper_id)
        return ApiResponse(data=paper.model_dump())

    @app.post("/api/rw/projects/{project_id}/papers/search")
    def search_papers(project_id: str, req: SearchPapersRequest):
        svc = get_paper_library()
        query = SearchQuery(
            query=req.query, sources=req.sources, limit=req.limit,
            year_from=req.year_from, year_to=req.year_to, use_cache=req.use_cache,
        )
        session = svc.search_candidates(project_id, query)
        return ApiResponse(data={
            "session_id": session.session_id,
            "results": [r.model_dump() for r in session.results],
            "result_count": len(session.results),
        })

    @app.post("/api/rw/projects/{project_id}/papers/search/commit")
    def commit_search(project_id: str, req: SearchCommitRequest):
        svc = get_paper_library()
        papers = svc.commit_search_results(project_id, req.session_id, req.selected_result_ids)
        return ApiResponse(data=[p.model_dump() for p in papers])

    @app.post("/api/rw/papers/{paper_id}/parse")
    def parse_paper(paper_id: str):
        svc = get_parser_service()
        result = svc.parse_paper(paper_id)
        return ApiResponse(data=result)

    @app.post("/api/rw/projects/{project_id}/papers/parse")
    def parse_project_papers(project_id: str):
        svc = get_parser_service()
        result = svc.parse_project_papers(project_id)
        return ApiResponse(data=result)

    @app.post("/api/rw/projects/{project_id}/cards")
    def generate_cards(project_id: str, only_missing: bool = True):
        svc = get_card_generator()
        cards = svc.batch_generate(project_id, only_missing=only_missing)
        return ApiResponse(data=[c.model_dump() for c in cards])

    @app.post("/api/rw/projects/{project_id}/evidence/build")
    def build_evidence(project_id: str):
        svc = get_evidence_service()
        records = svc.build_for_project(project_id)
        return ApiResponse(data=[e.model_dump() for e in records])

    @app.post("/api/rw/projects/{project_id}/kg/build")
    def build_graph(project_id: str):
        svc = get_graph_service()
        graph = svc.build_project_graph(project_id)
        return ApiResponse(data={"node_count": len(graph.nodes), "edge_count": len(graph.edges)})

    @app.get("/api/rw/projects/{project_id}/kg")
    def get_graph(project_id: str):
        svc = get_graph_service()
        graph = svc.get_graph(project_id)
        return ApiResponse(data={
            "nodes": [n.model_dump() for n in graph.nodes],
            "edges": [e.model_dump() for e in graph.edges],
        })

    @app.get("/api/rw/projects/{project_id}/kg/stats")
    def get_graph_stats(project_id: str):
        svc = get_graph_service()
        return ApiResponse(data=svc.get_stats(project_id))

    @app.post("/api/rw/projects/{project_id}/kg/subgraph")
    def get_subgraph(project_id: str, node_ids: list[str], hops: int = 1):
        svc = get_graph_service()
        return ApiResponse(data=svc.get_subgraph(project_id, node_ids, hops=hops))

    @app.get("/api/rw/projects/{project_id}/kg/gaps")
    def find_gaps(project_id: str, min_confidence: float = 0.5):
        svc = get_graph_service()
        return ApiResponse(data=svc.find_gaps(project_id, min_confidence=min_confidence))

    @app.post("/api/rw/projects/{project_id}/scope/resolve")
    def resolve_scope(project_id: str, req: ScopeResolveRequest):
        svc = get_scope_service()
        return ApiResponse(data=svc.resolve(project_id, req.model_dump()).model_dump())

    @app.get("/api/rw/projects/{project_id}/scope/filters")
    def get_scope_filters(project_id: str):
        svc = get_scope_service()
        return ApiResponse(data=svc.get_scope_filters(project_id))

    @app.post("/api/rw/projects/{project_id}/qa")
    def ask_question(project_id: str, req: QARequest):
        svc = get_qa_service()
        response = svc.answer(project_id, req.question, req.scope.model_dump())
        return ApiResponse(data=response.model_dump())

    @app.get("/api/rw/projects/{project_id}/reports")
    def list_reports(project_id: str, type: str | None = None):
        svc = get_report_service()
        return ApiResponse(data=[r.model_dump() for r in svc.list_reports(project_id, type)])

    @app.get("/api/rw/reports/{report_id}")
    def get_report(report_id: str):
        svc = get_report_service()
        report = svc.get_report(report_id)
        if not report:
            raise NotFoundError("report", report_id)
        return ApiResponse(data=report.model_dump())

    @app.post("/api/rw/projects/{project_id}/reports/literature-review")
    def generate_review(project_id: str, req: ReportGenerateRequest):
        svc = get_review_generator()
        return ApiResponse(data=svc.generate(project_id, req.scope.model_dump(), req.options).model_dump())

    @app.post("/api/rw/projects/{project_id}/reports/innovation")
    def generate_innovation(project_id: str, req: ReportGenerateRequest):
        svc = get_innovation_generator()
        return ApiResponse(data=svc.generate(project_id, req.scope.model_dump(), req.options).model_dump())

    @app.get("/api/rw/reports/{report_id}/export/markdown")
    def export_markdown(report_id: str):
        svc = get_report_service()
        md = svc.export_markdown(report_id)
        if not md:
            raise NotFoundError("report", report_id)
        return {"content": md, "format": "markdown"}

    @app.get("/api/rw/reports/{report_id}/export/json")
    def export_json(report_id: str):
        svc = get_report_service()
        data = svc.export_json(report_id)
        if not data or data == "{}":
            raise NotFoundError("report", report_id)
        return {"content": data, "format": "json"}

    @app.get("/api/rw/tasks/{task_id}")
    def get_task(task_id: str):
        svc = get_task_service()
        task = svc.get_task(task_id)
        if not task:
            raise NotFoundError("task", task_id)
        return ApiResponse(data=task)

    @app.get("/api/rw/tasks")
    def list_tasks(project_id: str | None = None, status: str | None = None):
        svc = get_task_service()
        return ApiResponse(data=svc.list_tasks(project_id, status))

    return app


app = create_app()
