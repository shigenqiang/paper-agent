"""JSON 文件持久化层"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

DEFAULT_DATA_DIR = Path("data/research_workspace")


class JSONStorage:
    """基于 JSON 文件的简单持久化"""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _collection_path(self, name: str) -> Path:
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
            "paper_cards": "card_id",
            "evidence_records": "evidence_id",
            "reports": "report_id",
            "report_versions": "version_id",
            "graphs": "project_id",
            "chunks": "paper_id",
            "paper_chunks": "chunk_id",
            "parse_results": "parse_id",
            "graphs": "graph_id",
            "qa_history": "qa_id",
            "tasks": "task_id",
            "search_sessions": "session_id",
            "search_cache": "cache_key",
        }
        return mapping.get(name, "id")

    def ensure_dirs(self) -> None:
        for subdir in ["files", "graphs", "chunks"]:
            (self.data_dir / subdir).mkdir(parents=True, exist_ok=True)


_storage: JSONStorage | None = None


def get_storage(data_dir: Path | str | None = None) -> JSONStorage:
    global _storage
    if _storage is None:
        _storage = JSONStorage(data_dir)
        _storage.ensure_dirs()
    return _storage
