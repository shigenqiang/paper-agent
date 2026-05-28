"""ParserService 测试"""

import pytest
from pathlib import Path

from src.agents_v3.research_workspace.parser_service import ParserService
from src.agents_v3.research_workspace.models import PaperStatus


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.parser_service.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return ParserService()


@pytest.fixture
def sample_paper(service, tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    storage = service.storage
    paper_data = {
        "paper_id": "p1",
        "project_id": "proj1",
        "title": "Test Paper",
        "status": PaperStatus.UPLOADED.value,
        "pdf_path": str(pdf_path),
    }
    storage.upsert_item("papers", "p1", paper_data)
    return paper_data


class TestParserService:
    def test_parse_nonexistent_paper_returns_failure(self, service):
        result = service.parse_paper("missing")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_parse_paper_without_pdf_returns_failure(self, service):
        service.storage.upsert_item("papers", "p1", {
            "paper_id": "p1", "project_id": "proj1", "pdf_path": ""
        })
        result = service.parse_paper("p1")
        assert result["success"] is False

    def test_parse_paper_with_valid_pdf_returns_chunks(self, service, sample_paper):
        result = service.parse_paper("p1")
        assert result["success"] is True
        assert result["chunk_count"] > 0

    def test_get_chunks_returns_parsed_chunks(self, service, sample_paper):
        service.parse_paper("p1")
        chunks = service.get_chunks("p1")
        assert len(chunks) > 0
        assert chunks[0].paper_id == "p1"

    def test_parse_project_papers_parses_all_unparsed(self, service, sample_paper):
        result = service.parse_project_papers("proj1")
        assert result["success"] == 1
        assert result["failed"] == 0

    def test_parse_project_skips_already_parsed(self, service, sample_paper):
        service.parse_paper("p1")
        result = service.parse_project_papers("proj1", only_unparsed=True)
        assert result["skipped"] == 1

    def test_parse_missing_pdf_file_returns_failure(self, service):
        service.storage.upsert_item("papers", "p2", {
            "paper_id": "p2",
            "project_id": "proj1",
            "pdf_path": "/nonexistent/file.pdf",
        })
        result = service.parse_paper("p2")
        assert result["success"] is False
