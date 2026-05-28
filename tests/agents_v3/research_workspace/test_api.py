"""API 集成测试"""

import pytest
from fastapi.testclient import TestClient

from src.agents_v3.research_workspace.api import create_app
from src.agents_v3.research_workspace.storage import JSONStorage


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    storage = JSONStorage(data_dir=tmp_path)
    # Patch get_storage to return our test storage
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.api_deps.get_storage",
        lambda: storage,
    )
    # Also patch all service-level get_storage calls
    for module in [
        "paper_library", "parser_service", "paper_card",
        "evidence_table", "graph_service", "scope",
        "scope_qa", "review_generator", "innovation_generator",
        "report_service", "task_service", "project_service",
    ]:
        monkeypatch.setattr(
            f"src.agents_v3.research_workspace.{module}.get_storage",
            lambda: storage,
        )
    app = create_app(storage=storage)
    return TestClient(app)


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestProjects:
    def test_create_project(self, client):
        resp = client.post("/api/rw/projects", json={"name": "Test Project"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "Test Project"
        assert data["project_id"].startswith("proj_")

    def test_list_projects(self, client):
        client.post("/api/rw/projects", json={"name": "P1"})
        client.post("/api/rw/projects", json={"name": "P2"})
        resp = client.get("/api/rw/projects")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_get_project(self, client):
        create = client.post("/api/rw/projects", json={"name": "Test"})
        pid = create.json()["data"]["project_id"]
        resp = client.get(f"/api/rw/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Test"

    def test_get_nonexistent_project(self, client):
        resp = client.get("/api/rw/projects/nonexistent")
        assert resp.status_code == 404

    def test_delete_project(self, client):
        create = client.post("/api/rw/projects", json={"name": "Test"})
        pid = create.json()["data"]["project_id"]
        resp = client.delete(f"/api/rw/projects/{pid}")
        assert resp.status_code == 200

    def test_get_project_stats(self, client):
        create = client.post("/api/rw/projects", json={"name": "Test"})
        pid = create.json()["data"]["project_id"]
        resp = client.get(f"/api/rw/projects/{pid}/stats")
        assert resp.status_code == 200
        assert "paper_count" in resp.json()["data"]


class TestPapers:
    def _create_project(self, client):
        resp = client.post("/api/rw/projects", json={"name": "Test"})
        return resp.json()["data"]["project_id"]

    def test_import_doi(self, client):
        pid = self._create_project(client)
        resp = client.post(f"/api/rw/projects/{pid}/papers/import/doi", json={
            "dois": ["10.1234/a", "10.1234/b"],
        })
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_import_bibtex(self, client):
        pid = self._create_project(client)
        bibtex = "@article{test, author={Alice and Bob}, title={Test}, year={2024}}"
        resp = client.post(f"/api/rw/projects/{pid}/papers/import/bibtex", json={"bibtex": bibtex})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_list_papers(self, client):
        pid = self._create_project(client)
        client.post(f"/api/rw/projects/{pid}/papers/import/doi", json={"dois": ["10.1/a"]})
        resp = client.get(f"/api/rw/projects/{pid}/papers")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_get_paper(self, client):
        pid = self._create_project(client)
        create = client.post(f"/api/rw/projects/{pid}/papers/import/doi", json={"dois": ["10.1/a"]})
        paper_id = create.json()["data"][0]["paper_id"]
        resp = client.get(f"/api/rw/papers/{paper_id}")
        assert resp.status_code == 200

    def test_update_paper(self, client):
        pid = self._create_project(client)
        create = client.post(f"/api/rw/projects/{pid}/papers/import/doi", json={"dois": ["10.1/a"]})
        paper_id = create.json()["data"][0]["paper_id"]
        resp = client.patch(f"/api/rw/papers/{paper_id}", json={"title": "Updated Title"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Updated Title"

    def test_exclude_paper(self, client):
        pid = self._create_project(client)
        create = client.post(f"/api/rw/projects/{pid}/papers/import/doi", json={"dois": ["10.1/a"]})
        paper_id = create.json()["data"][0]["paper_id"]
        resp = client.post(f"/api/rw/papers/{paper_id}/exclude", params={"reason": "not relevant"})
        assert resp.status_code == 200
        assert resp.json()["data"]["included"] is False


class TestScope:
    def _create_project_with_papers(self, client):
        pid = client.post("/api/rw/projects", json={"name": "Test"}).json()["data"]["project_id"]
        client.post(f"/api/rw/projects/{pid}/papers/import/doi", json={"dois": ["10.1/a", "10.1/b"]})
        return pid

    def test_resolve_scope_all_project(self, client):
        pid = self._create_project_with_papers(client)
        resp = client.post(f"/api/rw/projects/{pid}/scope/resolve", json={"type": "all_project"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["paper_ids"]) == 2

    def test_resolve_scope_selected(self, client):
        pid = self._create_project_with_papers(client)
        papers = client.get(f"/api/rw/projects/{pid}/papers").json()["data"]
        resp = client.post(f"/api/rw/projects/{pid}/scope/resolve", json={
            "type": "selected_papers",
            "selected_paper_ids": [papers[0]["paper_id"]],
        })
        assert resp.status_code == 200
        assert len(resp.json()["data"]["paper_ids"]) == 1

    def test_get_scope_filters(self, client):
        pid = self._create_project_with_papers(client)
        resp = client.get(f"/api/rw/projects/{pid}/scope/filters")
        assert resp.status_code == 200
        assert "papers" in resp.json()["data"]


class TestReports:
    def test_list_reports_empty(self, client):
        pid = client.post("/api/rw/projects", json={"name": "Test"}).json()["data"]["project_id"]
        resp = client.get(f"/api/rw/projects/{pid}/reports")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_get_nonexistent_report(self, client):
        resp = client.get("/api/rw/reports/nonexistent")
        assert resp.status_code == 404


class TestTasks:
    def test_list_tasks_empty(self, client):
        resp = client.get("/api/rw/tasks")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_get_nonexistent_task(self, client):
        resp = client.get("/api/rw/tasks/nonexistent")
        assert resp.status_code == 404


class TestGraph:
    def test_build_graph(self, client):
        pid = client.post("/api/rw/projects", json={"name": "Test"}).json()["data"]["project_id"]
        client.post(f"/api/rw/projects/{pid}/papers/import/doi", json={"dois": ["10.1/a"]})
        # Build evidence first
        ev_resp = client.post(f"/api/rw/projects/{pid}/evidence/build")
        assert ev_resp.status_code == 200
        # Build graph
        resp = client.post(f"/api/rw/projects/{pid}/kg/build")
        assert resp.status_code == 200

    def test_get_graph(self, client):
        pid = client.post("/api/rw/projects", json={"name": "Test"}).json()["data"]["project_id"]
        resp = client.get(f"/api/rw/projects/{pid}/kg")
        assert resp.status_code == 200
        assert "nodes" in resp.json()["data"]

    def test_get_graph_stats(self, client):
        pid = client.post("/api/rw/projects", json={"name": "Test"}).json()["data"]["project_id"]
        resp = client.get(f"/api/rw/projects/{pid}/kg/stats")
        assert resp.status_code == 200
        assert "total_nodes" in resp.json()["data"]
