"""JSON 存储层测试"""

import pytest
import tempfile
from pathlib import Path

from src.agents_v3.research_workspace.storage import JSONStorage


@pytest.fixture
def storage(tmp_path):
    return JSONStorage(data_dir=tmp_path)


class TestJSONStorage:
    def test_empty_collection(self, storage):
        result = storage.load_collection("nonexistent")
        assert result == []

    def test_save_and_load(self, storage):
        items = [{"id": "1", "name": "test"}, {"id": "2", "name": "test2"}]
        storage.save_collection("test", items)
        loaded = storage.load_collection("test")
        assert len(loaded) == 2
        assert loaded[0]["name"] == "test"

    def test_upsert_insert(self, storage):
        storage.upsert_item("projects", "p1", {"project_id": "p1", "name": "Project 1"})
        item = storage.get_item("projects", "p1")
        assert item is not None
        assert item["name"] == "Project 1"

    def test_upsert_update(self, storage):
        storage.upsert_item("projects", "p1", {"project_id": "p1", "name": "Old"})
        storage.upsert_item("projects", "p1", {"project_id": "p1", "name": "New"})
        item = storage.get_item("projects", "p1")
        assert item["name"] == "New"
        items = storage.load_collection("projects")
        assert len(items) == 1

    def test_get_nonexistent(self, storage):
        result = storage.get_item("projects", "missing")
        assert result is None

    def test_delete_existing(self, storage):
        storage.upsert_item("projects", "p1", {"project_id": "p1", "name": "Test"})
        deleted = storage.delete_item("projects", "p1")
        assert deleted is True
        assert storage.get_item("projects", "p1") is None

    def test_delete_nonexistent(self, storage):
        deleted = storage.delete_item("projects", "missing")
        assert deleted is False

    def test_query(self, storage):
        storage.upsert_item("papers", "p1", {"paper_id": "p1", "project_id": "proj1"})
        storage.upsert_item("papers", "p2", {"paper_id": "p2", "project_id": "proj1"})
        storage.upsert_item("papers", "p3", {"paper_id": "p3", "project_id": "proj2"})
        result = storage.query("papers", {"project_id": "proj1"})
        assert len(result) == 2

    def test_query_empty(self, storage):
        result = storage.query("papers", {"project_id": "proj1"})
        assert result == []

    def test_ensure_dirs(self, storage):
        storage.ensure_dirs()
        assert (storage.data_dir / "files").exists()
        assert (storage.data_dir / "graphs").exists()
        assert (storage.data_dir / "chunks").exists()

    def test_corrupted_json(self, storage, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        result = storage.load_collection("bad")
        assert result == []
