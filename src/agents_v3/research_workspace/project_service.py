"""项目管理服务"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Project
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


class ProjectService:
    """研究项目 CRUD"""

    def __init__(self, storage: JSONStorage | None = None):
        self.storage = storage or get_storage()

    def create_project(
        self,
        name: str,
        description: str = "",
        discipline: str = "",
        education_level: str = "",
        research_goal: str = "",
    ) -> Project:
        project = Project(
            project_id=f"proj_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            discipline=discipline,
            education_level=education_level,
            research_goal=research_goal,
        )
        self.storage.upsert_item("projects", project.project_id, project.model_dump())
        logger.info(f"Created project: {project.project_id} - {name}")
        return project

    def list_projects(self) -> list[Project]:
        items = self.storage.load_collection("projects")
        return [Project(**i) for i in items]

    def get_project(self, project_id: str) -> Project | None:
        item = self.storage.get_item("projects", project_id)
        if item:
            return Project(**item)
        return None

    def update_project(self, project_id: str, **updates: Any) -> Project | None:
        item = self.storage.get_item("projects", project_id)
        if not item:
            return None
        item.update(updates)
        item["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("projects", project_id, item)
        return Project(**item)

    def delete_project(self, project_id: str) -> bool:
        return self.storage.delete_item("projects", project_id)

    def get_project_stats(self, project_id: str) -> dict[str, int]:
        papers = self.storage.query("papers", {"project_id": project_id})
        cards = self.storage.query("paper_cards", {"project_id": project_id})
        evidence = self.storage.query("evidence_records", {"project_id": project_id})
        reports = self.storage.query("reports", {"project_id": project_id})

        parsed = [p for p in papers if p.get("status") in ("parsed", "card_ready", "evidence_ready")]

        return {
            "paper_count": len(papers),
            "parsed_count": len(parsed),
            "card_count": len(cards),
            "evidence_count": len(evidence),
            "graph_node_count": 0,
            "report_count": len(reports),
        }
