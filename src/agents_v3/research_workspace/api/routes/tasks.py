"""任务查询路由"""

from __future__ import annotations

import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.agents_v3.research_workspace.api.deps import get_task_service
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import ApiListResponse, ApiResponse, PageInfo

router = APIRouter(prefix="/api/rw/tasks", tags=["tasks"])


@router.get("/{task_id}")
def get_task(task_id: str):
    svc = get_task_service()
    task = svc.get_task(task_id)
    if not task:
        raise NotFoundError("task", task_id)
    return ApiResponse(data=task)


@router.get("")
def list_tasks(
    project_ref: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    svc = get_task_service()
    items = svc.list_tasks(project_ref, status)
    total = len(items)
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    start = (page - 1) * page_size
    paged = items[start : start + page_size]
    return ApiListResponse(
        data=paged,
        pagination=PageInfo(page=page, page_size=page_size, total=total, has_next=start + page_size < total),
    )


@router.get("/{task_id}/stream")
def stream_task(task_id: str):
    """SSE 端点：实时推送任务进度和事件"""
    svc = get_task_service()
    task = svc.get_task(task_id)
    if not task:
        raise NotFoundError("task", task_id)

    def event_generator():
        sent_events = 0
        last_progress = -1.0

        while True:
            current = svc.get_task(task_id)
            if not current:
                yield _sse_event("error", {"message": "task not found"})
                break

            # 推送进度变化
            progress = current.get("progress", 0)
            if progress != last_progress:
                yield _sse_event("progress", {
                    "progress": progress,
                    "status": current.get("status", ""),
                })
                last_progress = progress

            # 推送新事件
            events = current.get("events", [])
            for ev in events[sent_events:]:
                yield _sse_event(ev.get("type", "event"), ev.get("data", {}))
            sent_events = len(events)

            # 终态检查
            status = current.get("status", "")
            if status in ("completed", "failed", "cancelled"):
                yield _sse_event("done", {
                    "status": status,
                    "result": current.get("result"),
                    "error": current.get("error", ""),
                })
                break

            time.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    """格式化 SSE 事件"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"
