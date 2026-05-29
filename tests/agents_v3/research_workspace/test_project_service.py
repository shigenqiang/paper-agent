"""ProjectService 测试"""

import pytest

from src.agents_v3.research_workspace.project_service import ProjectService


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.storage._global_storage", None
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.project_service.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return ProjectService()


class TestProjectService:
    def test_create_project_returns_valid_project(self, service):
        p = service.create_project("Test Project", description="A test")
        assert p.name == "Test Project"
        assert p.project_id.startswith("proj_")

    def test_list_projects_returns_all_created(self, service):
        service.create_project("P1")
        service.create_project("P2")
        projects = service.list_projects()
        assert len(projects) == 2

    def test_get_project_returns_matching_project(self, service):
        p = service.create_project("Test")
        found = service.get_project(p.project_id)
        assert found is not None
        assert found.name == "Test"

    def test_get_nonexistent_returns_none(self, service):
        assert service.get_project("missing") is None

    def test_update_project_modifies_fields(self, service):
        p = service.create_project("Old Name")
        updated = service.update_project(p.project_id, name="New Name")
        assert updated.name == "New Name"

    def test_update_nonexistent_returns_none(self, service):
        assert service.update_project("missing", name="x") is None

    def test_delete_project_removes_from_storage(self, service):
        p = service.create_project("To Delete")
        assert service.delete_project(p.project_id) is True
        assert service.get_project(p.project_id) is None

    def test_delete_nonexistent_returns_false(self, service):
        assert service.delete_project("missing") is False

    def test_get_project_stats_returns_zero_counts(self, service):
        p = service.create_project("Stats Test")
        stats = service.get_project_stats(p.project_id)
        assert stats["paper_count"] == 0
        assert stats["card_count"] == 0
