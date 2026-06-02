"""JSON 文件持久化层

两种作用域：
- 全局存储：data/research_workspace/{name}.json（tasks, queries）
- 项目存储：data/research_workspace/projects/{dir_name}/{name}.json

项目元数据存储在各自目录下的 project.json 中，不再使用全局 projects.json。
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from loguru import logger

DEFAULT_DATA_DIR = Path("data/research_workspace")

# 全局集合（不按项目隔离）
GLOBAL_COLLECTIONS = {"tasks", "papers_pool", "queries"}


# ── 工具函数 ──────────────────────────────────────────


def sanitize_dirname(name: str) -> str:
    """将项目名转为文件系统安全的目录名。

    保留中文、字母、数字、点、下划线、连字符。
    特殊字符替换为下划线，合并连续下划线，截断64字符。
    """
    s = name.strip()
    # 替换不安全字符（保留 \w 包含的 Unicode 字母数字 + . -）
    s = re.sub(r"[^\w.\-]", "_", s, flags=re.UNICODE)
    # 合并连续下划线
    s = re.sub(r"_+", "_", s)
    # 去除首尾下划线
    s = s.strip("_")
    # 截断
    if len(s) > 64:
        s = s[:64].rstrip("_")
    return s if s else "untitled"


def unique_dirname(base: str, existing: set[str]) -> str:
    """确保目录名唯一，重名时追加 _2, _3 等后缀。"""
    if base not in existing:
        return base
    i = 2
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


def list_project_dirs(data_dir: Path) -> list[Path]:
    """列出所有包含 project.json 的项目目录。"""
    projects_dir = data_dir / "projects"
    if not projects_dir.exists():
        return []
    result = []
    for d in projects_dir.iterdir():
        if d.is_dir() and (d / "project.json").exists():
            result.append(d)
    return result


def load_all_projects(data_dir: Path) -> list[dict[str, Any]]:
    """扫描 projects/*/project.json，返回所有项目元数据。"""
    result = []
    for d in list_project_dirs(data_dir):
        try:
            with open(d / "project.json", encoding="utf-8") as f:
                result.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load project.json from {d}: {e}")
    return result


def resolve_project_ref(ref: str, data_dir: Path) -> str:
    """通过 project_id 或 dir_name 解析到 dir_name。

    优先匹配 project_id，其次匹配 dir_name。
    Raises KeyError if not found.
    """
    for d in list_project_dirs(data_dir):
        try:
            with open(d / "project.json", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("project_id") == ref:
                return data.get("dir_name", d.name)
            if data.get("dir_name") == ref:
                return data["dir_name"]
        except (json.JSONDecodeError, OSError):
            continue
    raise KeyError(f"Project not found: {ref}")


# ── JSONStorage ──────────────────────────────────────


class JSONStorage:
    """基于 JSON 文件的持久化，支持项目作用域"""

    def __init__(self, data_dir: Path | str | None = None, project_dir_name: str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.project_dir_name = project_dir_name
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if project_dir_name:
            self._project_dir = self.data_dir / "projects" / project_dir_name
            self._project_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._project_dir = None

    def _collection_path(self, name: str) -> Path:
        if self.project_dir_name and name not in GLOBAL_COLLECTIONS:
            return self._project_dir / f"{name}.json"
        return self.data_dir / f"{name}.json"

    def load_collection(self, name: str) -> list[dict[str, Any]]:
        path = self._collection_path(name)
        if not path.exists():
            return []
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load collection {name}: {e}")
            return []

    def save_collection(self, name: str, items: list[dict[str, Any]]) -> None:
        path = self._collection_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def upsert_item(self, name: str, item_id: str, item: dict[str, Any]) -> None:
        items = self.load_collection(name)
        id_field = self._guess_id_field(name)
        found = False
        for i, existing in enumerate(items):
            if existing.get(id_field) == item_id:
                items[i] = item
                found = True
                break
        if not found:
            items.append(item)
        self.save_collection(name, items)

    def get_item(self, name: str, item_id: str) -> dict[str, Any] | None:
        items = self.load_collection(name)
        id_field = self._guess_id_field(name)
        for item in items:
            if item.get(id_field) == item_id:
                return item
        return None

    def delete_item(self, name: str, item_id: str) -> bool:
        items = self.load_collection(name)
        id_field = self._guess_id_field(name)
        new_items = [i for i in items if i.get(id_field) != item_id]
        if len(new_items) < len(items):
            self.save_collection(name, new_items)
            return True
        return False

    def query(self, name: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        items = self.load_collection(name)
        result = []
        for item in items:
            match = True
            for key, value in filters.items():
                if item.get(key) != value:
                    match = False
                    break
            if match:
                result.append(item)
        return result

    def _guess_id_field(self, name: str) -> str:
        mapping = {
            "projects": "project_id",
            "papers": "paper_id",
            "papers_pool": "paper_id",
            "paper_cards": "card_id",
            "evidence_records": "evidence_id",
            "reports": "report_id",
            "report_versions": "version_id",
            "graphs": "graph_id",
            "chunks": "paper_id",
            "paper_chunks": "chunk_id",
            "paper_sections": "section_id",
            "citation_contexts": "context_id",
            "parse_results": "parse_id",
            "qa_history": "qa_id",
            "tasks": "task_id",
            "queries": "query_id",
            "paper_queries": "paper_id",
        }
        return mapping.get(name, "id")

    def ensure_dirs(self) -> None:
        if self._project_dir:
            for subdir in ["files", "graphs", "chunks"]:
                (self._project_dir / subdir).mkdir(parents=True, exist_ok=True)
        else:
            for subdir in ["files", "graphs", "chunks", "papers_pool"]:
                (self.data_dir / subdir).mkdir(parents=True, exist_ok=True)

    # ── 文件夹存储（papers_pool） ──

    def _folder_path(self, name: str) -> Path:
        """获取文件夹存储路径"""
        return self.data_dir / name

    def save_to_folder(self, folder: str, item_id: str, item: dict[str, Any]) -> None:
        """将单个 item 保存为独立 JSON 文件"""
        folder_path = self._folder_path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        # 清理文件名中的特殊字符
        safe_id = item_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        file_path = folder_path / f"{safe_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

    def load_from_folder(self, folder: str, item_id: str) -> dict[str, Any] | None:
        """从文件夹加载单个 item"""
        folder_path = self._folder_path(folder)
        safe_id = item_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        file_path = folder_path / f"{safe_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return None

    def list_folder(self, folder: str) -> list[dict[str, Any]]:
        """列出文件夹中的所有 item"""
        folder_path = self._folder_path(folder)
        if not folder_path.exists():
            return []
        items = []
        for file_path in folder_path.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    items.append(json.load(f))
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load {file_path}: {e}")
        return items

    def delete_from_folder(self, folder: str, item_id: str) -> bool:
        """从文件夹删除单个 item"""
        folder_path = self._folder_path(folder)
        safe_id = item_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        file_path = folder_path / f"{safe_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    # ── 项目元数据 ──

    def load_project_metadata(self) -> dict[str, Any] | None:
        """加载项目目录下的 project.json"""
        if not self._project_dir:
            return None
        path = self._project_dir / "project.json"
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load project.json: {e}")
            return None

    def save_project_metadata(self, project_data: dict[str, Any]) -> None:
        """保存项目元数据到 project.json"""
        if not self._project_dir:
            raise ValueError("Cannot save project metadata on global storage")
        path = self._project_dir / "project.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)


# ── 单例管理 ──────────────────────────────────────────

_global_storage: JSONStorage | None = None
_project_storages: dict[str, JSONStorage] = {}


def get_storage(data_dir: Path | str | None = None) -> JSONStorage:
    """获取全局存储（tasks, queries）"""
    global _global_storage
    if _global_storage is None:
        _global_storage = JSONStorage(data_dir, project_dir_name=None)
        _global_storage.ensure_dirs()
    return _global_storage


def get_project_storage(project_dir_name: str, data_dir: Path | str | None = None) -> JSONStorage:
    """获取项目作用域存储（papers, cards, reports 等）"""
    if project_dir_name not in _project_storages:
        base_dir = data_dir or get_storage().data_dir
        _project_storages[project_dir_name] = JSONStorage(base_dir, project_dir_name=project_dir_name)
        _project_storages[project_dir_name].ensure_dirs()
    return _project_storages[project_dir_name]


def remove_project_storage(project_dir_name: str) -> None:
    """从缓存中移除项目存储（删除项目时调用）"""
    _project_storages.pop(project_dir_name, None)


def cleanup_storage_cache() -> int:
    """清理所有项目存储缓存，返回清理数量（供 shutdown 调用）"""
    count = len(_project_storages)
    _project_storages.clear()
    return count


def rename_project_storage(old_dir_name: str, new_dir_name: str, data_dir: Path | str | None = None) -> None:
    """重命名项目目录并更新缓存"""
    base_dir = Path(data_dir) if data_dir else get_storage().data_dir
    old_path = base_dir / "projects" / old_dir_name
    new_path = base_dir / "projects" / new_dir_name
    if old_path.exists():
        shutil.move(str(old_path), str(new_path))
    # 更新缓存
    if old_dir_name in _project_storages:
        _project_storages[new_dir_name] = _project_storages.pop(old_dir_name)
        _project_storages[new_dir_name].project_dir_name = new_dir_name
        _project_storages[new_dir_name]._project_dir = new_path
