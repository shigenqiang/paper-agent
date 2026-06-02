"""报告生成与导出路由"""

from __future__ import annotations

from fastapi import APIRouter

from src.agents_v3.research_workspace.api.deps import (
    get_innovation_generator,
    get_project_service,
    get_report_service,
    get_review_generator,
)
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import ApiResponse, ReportGenerateRequest

router = APIRouter(prefix="/api/rw/projects/{project_ref}/reports", tags=["reports"])


def _resolve_project(project_ref: str):
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


@router.get("")
def list_reports(project_ref: str, type: str | None = None):
    project = _resolve_project(project_ref)
    svc = get_report_service(project_ref)
    return ApiResponse(data=[r.model_dump() for r in svc.list_reports(project.project_id, type)])


@router.get("/{report_id}")
def get_report(project_ref: str, report_id: str):
    svc = get_report_service(project_ref)
    report = svc.get_report(report_id)
    if not report:
        raise NotFoundError("report", report_id)
    return ApiResponse(data=report.model_dump())


@router.post("/literature-review")
def generate_review(project_ref: str, req: ReportGenerateRequest):
    project = _resolve_project(project_ref)
    svc = get_review_generator(project_ref)
    return ApiResponse(data=svc.generate(project.project_id, req.scope.model_dump(), req.options).model_dump())


@router.post("/innovation")
def generate_innovation(project_ref: str, req: ReportGenerateRequest):
    project = _resolve_project(project_ref)
    svc = get_innovation_generator(project_ref)
    return ApiResponse(data=svc.generate(project.project_id, req.scope.model_dump(), req.options).model_dump())


@router.get("/{report_id}/export/markdown")
def export_markdown(project_ref: str, report_id: str):
    svc = get_report_service(project_ref)
    md = svc.export_markdown(report_id)
    if not md:
        raise NotFoundError("report", report_id)
    return {"content": md, "format": "markdown"}


@router.get("/{report_id}/export/json")
def export_json(project_ref: str, report_id: str):
    svc = get_report_service(project_ref)
    data = svc.export_json(report_id)
    if not data or data == "{}":
        raise NotFoundError("report", report_id)
    return {"content": data, "format": "json"}
