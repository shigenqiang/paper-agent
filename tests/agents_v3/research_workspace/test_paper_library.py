"""PaperLibraryService 测试"""

import pytest
from pathlib import Path

from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.models import PaperStatus


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.storage._storage", None
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.paper_library.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return PaperLibraryService()


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "test_paper.pdf"
    path.write_bytes(b"%PDF-1.4 fake content")
    return str(path)


class TestPaperLibraryService:
    def test_add_uploaded_paper(self, service, sample_pdf):
        paper = service.add_uploaded_paper("proj1", sample_pdf)
        assert paper.status == PaperStatus.UPLOADED
        assert paper.pdf_path.endswith(".pdf")

    def test_add_nonexistent_file(self, service):
        with pytest.raises(FileNotFoundError):
            service.add_uploaded_paper("proj1", "/nonexistent.pdf")

    def test_add_paper_metadata(self, service):
        meta = {
            "title": "Test Paper",
            "authors": ["Alice", "Bob"],
            "year": 2024,
            "doi": "10.1234/test",
        }
        paper = service.add_paper_metadata("proj1", meta, source="import")
        assert paper.title == "Test Paper"
        assert paper.source == "import"

    def test_add_search_results(self, service):
        results = [
            {"title": "Paper 1", "authors": ["A"]},
            {"title": "Paper 2", "authors": ["B"]},
        ]
        papers = service.add_search_results("proj1", results)
        assert len(papers) == 2
        assert papers[0].source == "search"

    def test_list_papers(self, service, sample_pdf):
        service.add_uploaded_paper("proj1", sample_pdf)
        service.add_paper_metadata("proj1", {"title": "Meta Paper"}, "import")
        papers = service.list_papers("proj1")
        assert len(papers) == 2

    def test_list_papers_isolated(self, service, sample_pdf):
        service.add_uploaded_paper("proj1", sample_pdf)
        service.add_paper_metadata("proj2", {"title": "Other"}, "import")
        assert len(service.list_papers("proj1")) == 1
        assert len(service.list_papers("proj2")) == 1

    def test_get_paper(self, service, sample_pdf):
        paper = service.add_uploaded_paper("proj1", sample_pdf)
        found = service.get_paper(paper.paper_id)
        assert found is not None
        assert found.title == paper.title

    def test_get_nonexistent(self, service):
        assert service.get_paper("missing") is None

    def test_update_paper(self, service, sample_pdf):
        paper = service.add_uploaded_paper("proj1", sample_pdf)
        updated = service.update_paper(paper.paper_id, title="New Title")
        assert updated.title == "New Title"

    def test_mark_included(self, service, sample_pdf):
        paper = service.add_uploaded_paper("proj1", sample_pdf)
        service.mark_excluded(paper.paper_id, "not relevant")
        service.mark_included(paper.paper_id)
        found = service.get_paper(paper.paper_id)
        assert found.included is True

    def test_mark_excluded(self, service, sample_pdf):
        paper = service.add_uploaded_paper("proj1", sample_pdf)
        service.mark_excluded(paper.paper_id, "off topic")
        found = service.get_paper(paper.paper_id)
        assert found.included is False
        assert found.exclude_reason == "off topic"

    def test_import_doi_list(self, service):
        dois = ["10.1234/a", "10.1234/b", "10.1234/c"]
        papers = service.import_doi_list("proj1", dois)
        assert len(papers) == 3
        assert papers[0].doi == "10.1234/a"

    def test_import_bibtex(self, service):
        bibtex = """
        @article{test2024,
            author = {Alice and Bob},
            title = {Test Title},
            year = {2024},
            journal = {Test Journal},
            doi = {10.1234/test}
        }
        """
        papers = service.import_bibtex("proj1", bibtex)
        assert len(papers) == 1
        assert papers[0].title == "Test Title"
        assert papers[0].year == 2024
