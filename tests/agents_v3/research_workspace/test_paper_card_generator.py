"""PaperCardGenerator 测试"""

import pytest

from src.agents_v3.research_workspace.paper_card import PaperCardGenerator
from src.agents_v3.research_workspace.models import PaperStatus


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.paper_card.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return PaperCardGenerator()


@pytest.fixture
def paper_with_chunks(service):
    storage = service.storage
    storage.upsert_item("papers", "p1", {
        "paper_id": "p1",
        "project_id": "proj1",
        "title": "Test Paper",
        "status": PaperStatus.PARSED.value,
    })
    storage.save_collection("chunks_p1", [
        {
            "chunk_id": "c1",
            "paper_id": "p1",
            "section_title": "abstract",
            "text": "This study found that LLM feedback improves learning outcomes. The results showed significant improvement.",
            "start_char": 0,
            "end_char": 100,
            "token_count": 15,
        },
        {
            "chunk_id": "c2",
            "paper_id": "p1",
            "section_title": "discussion",
            "text": "A limitation of this study is the small sample size. Future work should extend to larger populations.",
            "start_char": 100,
            "end_char": 200,
            "token_count": 18,
        },
    ])
    return storage


class TestPaperCardGenerator:
    def test_generate_nonexistent_paper_returns_none(self, service):
        assert service.generate("missing") is None

    def test_generate_paper_without_chunks_returns_none(self, service):
        service.storage.upsert_item("papers", "p1", {"paper_id": "p1", "project_id": "proj1"})
        assert service.generate("p1") is None

    def test_generate_valid_paper_returns_card(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert card is not None
        assert card.paper_id == "p1"
        assert card.confidence == 0.5

    def test_generate_extracts_findings_from_text(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert len(card.key_findings) > 0
        assert card.key_findings[0] != "unknown"

    def test_generate_creates_source_spans(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert len(card.source_spans) > 0
        assert card.source_spans[0].chunk_id == "c1"

    def test_batch_generate_creates_cards_for_project(self, service, paper_with_chunks):
        cards = service.batch_generate("proj1")
        assert len(cards) == 1

    def test_batch_generate_skips_existing_cards(self, service, paper_with_chunks):
        service.generate("p1")
        cards = service.batch_generate("proj1", only_missing=True)
        assert len(cards) == 0
