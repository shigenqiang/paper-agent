"""Scope 解析与 QA 路由"""

from __future__ import annotations

from fastapi import APIRouter

from src.agents_v3.research_workspace.api.deps import (
    get_project_service,
    get_qa_service,
    get_scope_service,
)
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import (
    ApiResponse,
    QARequest,
    ScopeResolveRequest,
)

router = APIRouter(prefix="/api/rw/projects/{project_ref}", tags=["scope-qa"])


def _resolve_project(project_ref: str):
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


@router.post("/scope/resolve")
def resolve_scope(project_ref: str, req: ScopeResolveRequest):
    project = _resolve_project(project_ref)
    svc = get_scope_service(project_ref)
    return ApiResponse(data=svc.resolve(project.project_id, req.model_dump()).model_dump())


@router.get("/scope/filters")
def get_scope_filters(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_scope_service(project_ref)
    return ApiResponse(data=svc.get_scope_filters(project.project_id))


@router.post("/qa")
def ask_question(project_ref: str, req: QARequest):
    project = _resolve_project(project_ref)
    svc = get_qa_service(project_ref)
    response = svc.answer(project.project_id, req.question, req.scope.model_dump())
    return ApiResponse(data=response.model_dump())
