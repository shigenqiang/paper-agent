"""PDF 下载与解析路由"""

from __future__ import annotations

from fastapi import APIRouter

from src.agents_v3.research_workspace.api.deps import get_parser_service, get_project_service
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import ApiResponse

router = APIRouter(prefix="/api/rw/projects/{project_ref}/papers", tags=["parsing"])


def _resolve_project(project_ref: str):
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


@router.post("/download")
def download_pdfs(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_parser_service(project_ref)
    result = svc.download_all_pdfs(project.project_id)
    return ApiResponse(data=result)


@router.post("/{paper_id}/download")
def download_pdf(project_ref: str, paper_id: str):
    svc = get_parser_service(project_ref)
    result = svc.download_pdf(paper_id)
    return ApiResponse(data=result)


@router.post("/{paper_id}/parse")
def parse_paper(project_ref: str, paper_id: str):
    svc = get_parser_service(project_ref)
    result = svc.parse_paper(paper_id)
    return ApiResponse(data=result)


@router.post("/parse")
def parse_project_papers(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_parser_service(project_ref)
    result = svc.parse_project_papers(project.project_id)
    return ApiResponse(data=result)
