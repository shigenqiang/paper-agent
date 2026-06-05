"""报告生成与导出路由"""

from __future__ import annotations

import threading

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from src.agents_v3.research_workspace.api.deps import (
    get_innovation_generator,
    get_project_service,
    get_report_service,
    get_review_generator,
    get_task_service,
)
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import ApiListResponse, ApiResponse, PageInfo, ReportGenerateRequest

router = APIRouter(prefix="/api/rw/projects/{project_ref}/reports", tags=["reports"])


def _resolve_project(project_ref: str):
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


@router.get("")
def list_reports(
    project_ref: str,
    type: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    project = _resolve_project(project_ref)
    svc = get_report_service(project_ref)
    items = [r.model_dump() for r in svc.list_reports(project.project_id, type)]
    total = len(items)
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    start = (page - 1) * page_size
    paged = items[start : start + page_size]
    return ApiListResponse(
        data=paged,
        pagination=PageInfo(page=page, page_size=page_size, total=total, has_next=start + page_size < total),
    )


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
    task_svc = get_task_service()
    task = task_svc.create_task("report_literature_review", project.project_id, {
        "scope": req.scope.model_dump(), "options": req.options,
    })

    def _bg():
        try:
            task_svc.update_task(task["task_id"], status="running", progress=0.1)
            task_svc.add_event(task["task_id"], "stage", {"name": "generating"})
            svc = get_review_generator(project_ref)
            result = svc.generate(project.project_id, req.scope.model_dump(), req.options)
            task_svc.update_task(
                task["task_id"], status="completed", progress=1.0,
                result=result.model_dump(),
            )
        except Exception as e:
            task_svc.update_task(task["task_id"], status="failed", error=str(e)[:500])

    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse(status_code=202, content={
        "data": {"task_id": task["task_id"], "status": "queued"},
    })


@router.post("/innovation")
def generate_innovation(project_ref: str, req: ReportGenerateRequest):
    project = _resolve_project(project_ref)
    task_svc = get_task_service()
    task = task_svc.create_task("report_innovation", project.project_id, {
        "scope": req.scope.model_dump(), "options": req.options,
    })

    def _bg():
        try:
            task_svc.update_task(task["task_id"], status="running", progress=0.1)
            task_svc.add_event(task["task_id"], "stage", {"name": "generating"})
            svc = get_innovation_generator(project_ref)
            result = svc.generate(project.project_id, req.scope.model_dump(), req.options)
            task_svc.update_task(
                task["task_id"], status="completed", progress=1.0,
                result=result.model_dump(),
            )
        except Exception as e:
            task_svc.update_task(task["task_id"], status="failed", error=str(e)[:500])

    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse(status_code=202, content={
        "data": {"task_id": task["task_id"], "status": "queued"},
    })


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


@router.get("/{report_id}/export/docx")
def export_docx(project_ref: str, report_id: str):
    svc = get_report_service(project_ref)
    report = svc.get_report(report_id)
    if not report:
        raise NotFoundError("report", report_id)
    data = svc.export_docx(report_id)
    if not data:
        return Response(status_code=500, content="DOCX export failed (python-docx not installed)")
    filename = f"{report.title or report.type.value}_v{report.version}.docx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── 版本管理 ──────────────────────────────────────────


@router.get("/{report_id}/versions")
def list_versions(project_ref: str, report_id: str):
    svc = get_report_service(project_ref)
    versions = svc.list_versions(report_id)
    return ApiResponse(data=[v.model_dump() for v in versions])


@router.post("/{report_id}/versions")
def create_version(project_ref: str, report_id: str, reason: str = "manual"):
    svc = get_report_service(project_ref)
    report = svc.get_report(report_id)
    if not report:
        raise NotFoundError("report", report_id)
    version = svc.create_version(report_id, report.content, reason)
    if not version:
        raise NotFoundError("report", report_id)
    return ApiResponse(data=version.model_dump())


@router.post("/{report_id}/versions/{version_id}/restore")
def restore_version(project_ref: str, report_id: str, version_id: str):
    svc = get_report_service(project_ref)
    report = svc.restore_version(report_id, version_id)
    if not report:
        raise NotFoundError("version", version_id)
    return ApiResponse(data=report.model_dump())


@router.get("/{report_id}/versions/diff")
def diff_versions(project_ref: str, report_id: str, version_a: int, version_b: int):
    svc = get_report_service(project_ref)
    result = svc.diff_versions(report_id, version_a, version_b)
    if result is None:
        raise NotFoundError("version comparison", f"v{version_a} vs v{version_b}")
    return ApiResponse(data=result)
