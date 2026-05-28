"""任务状态管理"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


class TaskService:
    """任务状态持久化"""

    def __init__(self, storage: JSONStorage | None = None):
        self.storage = storage or get_storage()

    def create_task(
        self, task_type: str, project_id: str = "", input_data: dict | None = None
    ) -> dict[str, Any]:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "project_id": project_id,
            "status": "queued",
            "progress": 0.0,
            "result": None,
            "error": "",
            "input": input_data or {},
            "events": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.storage.upsert_item("tasks", task_id, task)
        return task

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self.storage.get_item("tasks", task_id)

    def update_task(
        self, task_id: str,
        status: str | None = None,
        progress: float | None = None,
        result: Any = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        task = self.storage.get_item("tasks", task_id)
        if not task:
            return None
        if status:
            task["status"] = status
        if progress is not None:
            task["progress"] = progress
        if result is not None:
            task["result"] = result
        if error is not None:
            task["error"] = error
        task["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("tasks", task_id, task)
        return task

    def add_event(self, task_id: str, event_type: str, data: dict | None = None) -> None:
        task = self.storage.get_item("tasks", task_id)
        if not task:
            return
        event = {
            "type": event_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }
        task.setdefault("events", []).append(event)
        task["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("tasks", task_id, task)

    def list_tasks(
        self, project_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        if project_id:
            tasks = self.storage.query("tasks", {"project_id": project_id})
        else:
            tasks = self.storage.load_collection("tasks")
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return sorted(tasks, key=lambda t: t.get("created_at", ""), reverse=True)
