"""任务状态管理"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.storage import get_storage

# PostgreSQL tasks 表的列: task_id, task_type, status, data(JSONB), events(JSONB), created_at, updated_at
# 其余字段 (project_id, progress, result, error, input) 存入 data JSONB

_DATA_FIELDS = ("project_id", "progress", "result", "error", "input")


class TaskService:
    """任务状态持久化"""

    def __init__(self, storage=None):
        self.storage = storage or get_storage()

    def create_task(
        self, task_type: str, project_id: str = "", input_data: dict | None = None
    ) -> dict[str, Any]:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "queued",
            "data": {
                "project_id": project_id,
                "progress": 0.0,
                "result": None,
                "error": "",
                "input": input_data or {},
            },
            "events": [],
            "created_at": now,
            "updated_at": now,
        }
        self.storage.upsert_item("tasks", task_id, task)
        return self._unpack(task)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        task = self.storage.get_item("tasks", task_id)
        if not task:
            return None
        return self._unpack(task)

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
        data = task.get("data") or {}
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                data = {}

        if status:
            task["status"] = status
        if progress is not None:
            data["progress"] = progress
        if result is not None:
            data["result"] = result
        if error is not None:
            data["error"] = error

        task["data"] = data
        task["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("tasks", task_id, task)
        return self._unpack(task)

    def add_event(self, task_id: str, event_type: str, data: dict | None = None) -> None:
        task = self.storage.get_item("tasks", task_id)
        if not task:
            return
        events = task.get("events") or []
        if isinstance(events, str):
            import json
            try:
                events = json.loads(events)
            except Exception:
                events = []
        event = {
            "type": event_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }
        events.append(event)
        task["events"] = events
        task["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("tasks", task_id, task)

    def list_tasks(
        self, project_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        if project_id:
            tasks = self.storage.query("tasks", {"project_id": project_id})
        else:
            tasks = self.storage.load_collection("tasks")
        result = [self._unpack(t) for t in tasks]
        if status:
            result = [t for t in result if t.get("status") == status]
        return sorted(result, key=lambda t: t.get("created_at", ""), reverse=True)

    @staticmethod
    def _unpack(task: dict[str, Any]) -> dict[str, Any]:
        """将 DB 格式展开为扁平 dict，方便调用方使用"""
        data = task.get("data") or {}
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        return {
            "task_id": task.get("task_id", ""),
            "task_type": task.get("task_type", ""),
            "status": task.get("status", ""),
            "project_id": data.get("project_id", ""),
            "progress": data.get("progress", 0.0),
            "result": data.get("result"),
            "error": data.get("error", ""),
            "input": data.get("input", {}),
            "events": task.get("events") or [],
            "created_at": task.get("created_at", ""),
            "updated_at": task.get("updated_at", ""),
        }
