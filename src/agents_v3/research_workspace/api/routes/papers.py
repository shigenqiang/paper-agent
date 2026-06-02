"""论文库路由"""

from __future__ import annotations

from fastapi import APIRouter

from src.agents_v3.research_workspace.api.deps import get_paper_library, get_project_service
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import (
    ApiResponse,
    PaperImportBibtexRequest,
    PaperImportDoiRequest,
    PaperUpdateRequest,
    SearchPapersRequest,
)
from src.agents_v3.research_workspace.search.base import SearchQuery

router = APIRouter(prefix="/api/rw/projects/{project_ref}/papers", tags=["papers"])


def _resolve_project(project_ref: str):
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


@router.get("")
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


@router.post("/import/doi")
def import_doi(project_ref: str, req: PaperImportDoiRequest):
    project = _resolve_project(project_ref)
    svc = get_paper_library(project_ref)
    papers = svc.import_doi_list(project.project_id, req.dois)
    return ApiResponse(data=[p.model_dump() for p in papers])


@router.post("/import/bibtex")
def import_bibtex(project_ref: str, req: PaperImportBibtexRequest):
    project = _resolve_project(project_ref)
    svc = get_paper_library(project_ref)
    papers = svc.import_bibtex(project.project_id, req.bibtex)
    return ApiResponse(data=[p.model_dump() for p in papers])


@router.get("/{paper_id}")
def get_paper(project_ref: str, paper_id: str):
    svc = get_paper_library(project_ref)
    paper = svc.get_paper(paper_id)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.patch("/{paper_id}")
def update_paper(project_ref: str, paper_id: str, req: PaperUpdateRequest):
    svc = get_paper_library(project_ref)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    paper = svc.update_paper(paper_id, **updates)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.post("/{paper_id}/include")
def include_paper(project_ref: str, paper_id: str):
    svc = get_paper_library(project_ref)
    paper = svc.mark_included(paper_id)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.post("/{paper_id}/exclude")
def exclude_paper(project_ref: str, paper_id: str, reason: str = ""):
    svc = get_paper_library(project_ref)
    paper = svc.mark_excluded(paper_id, reason)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.post("/search")
def search_papers(project_ref: str, req: SearchPapersRequest):
    project = _resolve_project(project_ref)
    svc = get_paper_library(project_ref)
    query = SearchQuery(
        query=req.query, sources=req.sources, limit=req.limit,
        offset=req.offset,
        year_from=req.year_from, year_to=req.year_to,
        field=req.field,
        use_cache=req.use_cache, force_refresh=req.force_refresh,
    )
    response = svc.search_candidates(project.project_id, query, min_score=req.min_score)
    return ApiResponse(data={
        "query": response.query.query if hasattr(response.query, 'query') else str(response.query),
        "results": [r.model_dump(exclude_defaults=True) for r in response.results],
        "result_count": response.total_count,
    })
