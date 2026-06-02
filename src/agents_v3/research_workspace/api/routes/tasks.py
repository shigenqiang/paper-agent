"""任务查询路由"""

from __future__ import annotations

from fastapi import APIRouter

from src.agents_v3.research_workspace.api.deps import get_task_service
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import ApiResponse

router = APIRouter(prefix="/api/rw/tasks", tags=["tasks"])


@router.get("/{task_id}")
def get_task(task_id: str):
    svc = get_task_service()
    task = svc.get_task(task_id)
    if not task:
        raise NotFoundError("task", task_id)
    return ApiResponse(data=task)


@router.get("")
def list_tasks(project_ref: str | None = None, status: str | None = None):
    svc = get_task_service()
    return ApiResponse(data=svc.list_tasks(project_ref, status))
