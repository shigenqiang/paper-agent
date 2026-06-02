"""项目管理路由"""

from __future__ import annotations

from fastapi import APIRouter

from src.agents_v3.research_workspace.api.deps import (
    get_project_service,
    get_storage_dep,
)
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import (
    ApiResponse,
    ProjectCreateRequest,
    ProjectUpdateRequest,
)

router = APIRouter(prefix="/api/rw/projects", tags=["projects"])


def _resolve_project(project_ref: str):
    """解析 project_ref 得到 Project 对象，找不到则抛 NotFoundError"""
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


@router.post("", status_code=201)
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


@router.get("")
def list_projects():
    svc = get_project_service()
    projects = svc.list_projects()
    return ApiResponse(data=[p.model_dump() for p in projects])


@router.get("/{project_ref}")
def get_project(project_ref: str):
    project = _resolve_project(project_ref)
    return ApiResponse(data=project.model_dump())


@router.patch("/{project_ref}")
def update_project(project_ref: str, req: ProjectUpdateRequest):
    project = _resolve_project(project_ref)
    svc = get_project_service()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = svc.update_project(project.project_id, **updates)
    if not updated:
        raise NotFoundError("project", project_ref)
    return ApiResponse(data=updated.model_dump())


@router.get("/{project_ref}/stats")
def get_project_stats(project_ref: str):
    svc = get_project_service()
    stats = svc.get_project_stats(project_ref)
    return ApiResponse(data=stats)


@router.delete("/{project_ref}", status_code=200)
def delete_project(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_project_service()
    pg = get_storage_dep()

    paper_ids = []
    if pg:
        try:
            rows = pg.query("papers", {"project_id": project.project_id})
            paper_ids = [r["paper_id"] for r in rows]
        except Exception:
            pass

    if paper_ids:
        try:
            from src.agents_v3.research_workspace.storage.vector import VectorStorage
            vs = VectorStorage()
            vs.delete_by_papers(paper_ids)
        except Exception:
            pass

    ok = svc.delete_project(project.project_id, pg=pg)
    if not ok:
        raise NotFoundError("project", project_ref)
    return ApiResponse(data={"deleted": True, "papers_cleaned": len(paper_ids)})
