"""项目管理服务"""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Project
from src.agents_v3.research_workspace.storage import (
    JSONStorage,
    get_project_storage,
    get_storage,
    list_project_dirs,
    load_all_projects,
    remove_project_storage,
    rename_project_storage,
    resolve_project_ref,
    sanitize_dirname,
    unique_dirname,
)


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
        # 生成唯一目录名
        base_dir = sanitize_dirname(name)
        existing = {d.name for d in list_project_dirs(self.storage.data_dir)}
        dir_name = unique_dirname(base_dir, existing)

        project = Project(
            project_id=f"proj_{uuid.uuid4().hex[:8]}",
            name=name,
            dir_name=dir_name,
            description=description,
            discipline=discipline,
            education_level=education_level,
            research_goal=research_goal,
        )

        # 创建项目目录并写入 project.json
        ps = get_project_storage(dir_name)
        ps.save_project_metadata(project.model_dump())
        logger.info(f"Created project: {project.project_id} - {name} -> {dir_name}/")
        return project

    def list_projects(self) -> list[Project]:
        items = load_all_projects(self.storage.data_dir)
        return [Project(**i) for i in items]

    def get_project(self, ref: str) -> Project | None:
        """通过 project_id 或 dir_name 查找项目"""
        try:
            dir_name = resolve_project_ref(ref, self.storage.data_dir)
        except KeyError:
            return None
        ps = get_project_storage(dir_name)
        data = ps.load_project_metadata()
        if data:
            return Project(**data)
        return None

    def update_project(self, project_id: str, **updates: Any) -> Project | None:
        """更新项目，如果改名则同步重命名目录"""
        try:
            dir_name = resolve_project_ref(project_id, self.storage.data_dir)
        except KeyError:
            return None

        ps = get_project_storage(dir_name)
        data = ps.load_project_metadata()
        if not data:
            return None

        data.update(updates)
        data["updated_at"] = datetime.now().isoformat()

        # 如果名称变了，需要重命名目录
        if "name" in updates and updates["name"] != data.get("name"):
            new_base = sanitize_dirname(updates["name"])
            existing = {d.name for d in list_project_dirs(self.storage.data_dir)}
            existing.discard(dir_name)  # 排除自身
            new_dir_name = unique_dirname(new_base, existing)
            if new_dir_name != dir_name:
                rename_project_storage(dir_name, new_dir_name, self.storage.data_dir)
                data["dir_name"] = new_dir_name
                ps = get_project_storage(new_dir_name)

        ps.save_project_metadata(data)
        return Project(**data)

    def delete_project(self, project_id: str) -> bool:
        """删除项目（移除整个目录）"""
        try:
            dir_name = resolve_project_ref(project_id, self.storage.data_dir)
        except KeyError:
            return False

        project_dir = self.storage.data_dir / "projects" / dir_name
        if project_dir.exists():
            shutil.rmtree(project_dir)
        remove_project_storage(dir_name)
        logger.info(f"Deleted project directory: {dir_name}")
        return True

    def get_project_stats(self, ref: str) -> dict[str, int]:
        try:
            dir_name = resolve_project_ref(ref, self.storage.data_dir)
        except KeyError:
            return {"error": "project not found"}

        ps = get_project_storage(dir_name)
        papers = ps.load_collection("papers")
        cards = ps.load_collection("paper_cards")
        evidence = ps.load_collection("evidence_records")
        reports = ps.load_collection("reports")

        parsed = [p for p in papers if p.get("status") in ("parsed", "card_ready", "evidence_ready")]

        return {
            "paper_count": len(papers),
            "parsed_count": len(parsed),
            "card_count": len(cards),
            "evidence_count": len(evidence),
            "graph_node_count": 0,
            "report_count": len(reports),
        }
