"""PaperCardGenerator 测试 - 增强版"""

import pytest

from src.agents_v3.research_workspace.paper_card import PaperCardGenerator, ContextSelector
from src.agents_v3.research_workspace.models import (
    PaperCard,
    PaperCardExtractionResult,
    ExtractedClaim,
    PaperStatus,
    SourceSpan,
)


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._global_storage", None)
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
        "authors": ["Alice"],
        "year": 2024,
        "status": PaperStatus.PARSED.value,
    })
    storage.save_collection("paper_chunks", [
        {
            "chunk_id": "c1", "paper_id": "p1", "chunk_index": 0,
            "section_type": "abstract", "chunk_type": "body",
            "text": "This study found that LLM feedback improves learning outcomes significantly.",
            "token_count": 15, "page_start": 1, "page_end": 1,
        },
        {
            "chunk_id": "c2", "paper_id": "p1", "chunk_index": 1,
            "section_type": "method", "chunk_type": "body",
            "text": "We conducted a randomized controlled trial with 200 students using survey methodology.",
            "token_count": 18, "page_start": 2, "page_end": 2,
        },
        {
            "chunk_id": "c3", "paper_id": "p1", "chunk_index": 2,
            "section_type": "result", "chunk_type": "body",
            "text": "The treatment group showed 25% improvement in test scores compared to control.",
            "token_count": 16, "page_start": 3, "page_end": 3,
        },
        {
            "chunk_id": "c4", "paper_id": "p1", "chunk_index": 3,
            "section_type": "discussion", "chunk_type": "body",
            "text": "A limitation of this study is the small sample size. Future work should extend to larger populations.",
            "token_count": 18, "page_start": 4, "page_end": 4,
        },
        {
            "chunk_id": "c5", "paper_id": "p1", "chunk_index": 4,
            "section_type": "reference", "chunk_type": "reference",
            "text": "[1] Smith et al. 2020. [2] Jones et al. 2021.",
            "token_count": 10, "page_start": 5, "page_end": 5,
        },
    ])
    return storage


class TestContextSelector:
    def test_select_covers_sections(self, service, paper_with_chunks):
        chunks = service._get_body_chunks("p1")
        selected = service.context_selector.select(chunks)
        sections = {c.get("section_type") for c in selected}
        assert "abstract" in sections
        # Should include at least some body sections
        assert len(selected) >= 2

    def test_select_excludes_references(self, service, paper_with_chunks):
        chunks = service._get_body_chunks("p1")
        selected = service.context_selector.select(chunks)
        for c in selected:
            assert c.get("chunk_type") != "reference"

    def test_select_respects_token_budget(self, service, paper_with_chunks):
        chunks = service._get_body_chunks("p1")
        selected = service.context_selector.select(chunks, max_total_tokens=500)
        total = sum(c.get("token_count", 0) for c in selected)
        assert total <= 600  # Some tolerance


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
        assert card.confidence > 0

    def test_generate_extracts_findings_from_text(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert len(card.key_findings) > 0
        assert card.key_findings[0] != "unknown"

    def test_generate_creates_source_spans(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert len(card.source_spans) > 0

    def test_generate_sets_extraction_method(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert card.extraction_method in ("llm", "fallback")

    def test_generate_sets_version(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert card.version == 1

    def test_generate_active_card(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert card.active is True

    def test_generate_idempotent(self, service, paper_with_chunks):
        card1 = service.generate("p1")
        card2 = service.generate("p1")
        assert card1.card_id == card2.card_id

    def test_generate_regenerate_creates_new_version(self, service, paper_with_chunks):
        card1 = service.generate("p1")
        card2 = service.generate("p1", regenerate=True)
        assert card2.version > card1.version
        assert card2.active is True

    def test_generate_regenerate_deactivates_old(self, service, paper_with_chunks):
        card1 = service.generate("p1")
        card2 = service.generate("p1", regenerate=True)
        old = service.storage.query("paper_cards", {"card_id": card1.card_id})
        assert old[0]["active"] is False

    def test_fallback_has_low_confidence(self, service, paper_with_chunks):
        card = service.generate("p1")
        if card.extraction_method == "fallback":
            assert card.confidence <= 0.5

    def test_batch_generate_creates_cards_for_project(self, service, paper_with_chunks):
        cards = service.batch_generate("proj1")
        assert len(cards) == 1

    def test_batch_generate_skips_existing_cards(self, service, paper_with_chunks):
        service.generate("p1")
        cards = service.batch_generate("proj1", only_missing=True)
        assert len(cards) == 0

    def test_quality_report_exists(self, service, paper_with_chunks):
        service.generate("p1")
        report = service.get_quality_report("p1")
        assert report is not None
        assert report.paper_id == "p1"
        assert 0 <= report.completeness <= 1
        assert 0 <= report.traceability <= 1

    def test_card_has_input_chunk_ids(self, service, paper_with_chunks):
        card = service.generate("p1")
        assert len(card.input_chunk_ids) > 0

    def test_card_validation_checks_chunk_ids(self, service, paper_with_chunks):
        card = service.generate("p1")
        # Fallback cards may have valid chunk_ids from actual chunks
        for span in card.source_spans:
            if span.chunk_id:
                assert span.chunk_id in ("c1", "c2", "c3", "c4")

    def test_old_format_backward_compat(self, service):
        """旧格式 chunks_{paper_id} 应能被读取"""
        service.storage.upsert_item("papers", "p1", {
            "paper_id": "p1", "project_id": "proj1", "title": "Old Paper",
            "status": PaperStatus.PARSED.value,
        })
        service.storage.save_collection("chunks_p1", [
            {"chunk_id": "c1", "paper_id": "p1", "text": "Found improvement in results. " * 10, "token_count": 30},
        ])
        card = service.generate("p1")
        assert card is not None


class TestExtractionResult:
    def test_extraction_to_card(self, service):
        extraction = PaperCardExtractionResult(
            research_question="How does AI help?",
            method="experiment",
            data_or_sample="100 students",
            key_findings=[ExtractedClaim(text="Improved scores", quote="scores improved", chunk_id="c1")],
            limitations=[ExtractedClaim(text="Small sample", quote="small sample", chunk_id="c2")],
            future_work=[],
            topics=["AI education"],
            possible_gaps=[],
            confidence=0.7,
        )
        card = service._extraction_to_card("p1", "proj1", extraction, ["c1", "c2"], "llm")
        assert card.research_question == "How does AI help?"
        assert len(card.source_spans) == 2
        assert card.extraction_method == "llm"
