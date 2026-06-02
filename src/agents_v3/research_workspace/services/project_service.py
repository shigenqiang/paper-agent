"""项目管理服务"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Project
from src.agents_v3.research_workspace.storage import get_storage


class ProjectService:
    """研究项目 CRUD（PostgreSQL）"""

    def __init__(self, storage=None):
        self.storage = storage or get_storage()

    def create_project(
        self,
        name: str,
        description: str = "",
        discipline: str = "",
        education_level: str = "",
        research_goal: str = "",
    ) -> Project:
        # 检查项目名是否已存在
        existing = self.list_projects()
        for p in existing:
            if p.name == name:
                from src.agents_v3.research_workspace.api.errors import ConflictError
                raise ConflictError("project", "name", name)

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        project = Project(
            project_id=project_id,
            name=name,
            description=description,
            discipline=discipline,
            education_level=education_level,
            research_goal=research_goal,
        )
        self.storage.upsert("projects", project_id, project.model_dump())
        logger.info(f"Created project: {project_id} - {name}")
        return project

    def list_projects(self) -> list[Project]:
        items = self.storage.list_all("projects")
        return [Project(**i) for i in items if i]

    def get_project(self, ref: str) -> Project | None:
        """通过 project_id 或 name 查找项目"""
        data = self.storage.get("projects", ref)
        if not data:
            results = self.storage.query("projects", {"project_id": ref})
            data = results[0] if results else None
        if not data:
            results = self.storage.query("projects", {"name": ref})
            data = results[0] if results else None
        return Project(**data) if data else None

    def update_project(self, project_id: str, **updates: Any) -> Project | None:
        """更新项目"""
        data = self.storage.get("projects", project_id)
        if not data:
            results = self.storage.query("projects", {"project_id": project_id})
            data = results[0] if results else None
        if not data:
            return None

        data.update(updates)
        data["updated_at"] = datetime.now().isoformat()
        self.storage.upsert("projects", project_id, data)
        return Project(**data)

    def delete_project(self, project_id: str) -> bool:
        """删除项目及其全部关联数据"""
        data = self.storage.get("projects", project_id)
        if not data:
            results = self.storage.query("projects", {"project_id": project_id})
            data = results[0] if results else None
        if not data:
            return False

        try:
            self.storage.delete_project_data(project_id)
        except Exception as e:
            logger.warning(f"Failed to delete project data: {e}")

        self.storage.delete_item("projects", project_id)
        logger.info(f"Deleted project: {project_id}")
        return True

    def get_project_stats(self, ref: str) -> dict[str, int]:
        """获取项目统计"""
        project = self.get_project(ref)
        if not project:
            return {"error": "project not found"}

        pid = project.project_id
        papers = self.storage.query("papers", {"project_id": pid})
        cards = self.storage.query("paper_cards", {"project_id": pid})
        evidence = self.storage.query("evidence_records", {"project_id": pid})
        reports = self.storage.query("reports", {"project_id": pid})
        parsed = [p for p in papers if p.get("status") in ("parsed", "card_ready", "evidence_ready")]

        return {
            "paper_count": len(papers),
            "parsed_count": len(parsed),
            "card_count": len(cards),
            "evidence_count": len(evidence),
            "graph_node_count": 0,
            "report_count": len(reports),
        }
