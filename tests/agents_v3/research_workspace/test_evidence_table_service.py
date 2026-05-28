"""EvidenceTableService 测试"""

import pytest

from src.agents_v3.research_workspace.evidence_table import EvidenceTableService, normalize_topics
from src.agents_v3.research_workspace.models import PaperCard, RetrievalScope, ScopeType


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.evidence_table.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return EvidenceTableService()


@pytest.fixture
def sample_card(service):
    storage = service.storage
    card_data = {
        "card_id": "card1",
        "paper_id": "p1",
        "project_id": "proj1",
        "research_question": "How does LLM feedback affect learning?",
        "method": "experiment",
        "data_or_sample": "100 students",
        "key_findings": ["Improved test scores by 15%", "Higher engagement"],
        "limitations": ["Small sample size"],
        "future_work": ["Extend to other subjects"],
        "topics": ["feedback mechanism"],
        "possible_gaps": ["Long-term effects"],
        "source_spans": [
            {"field": "key_findings", "chunk_id": "c1", "quote": "found improvement"},
        ],
        "confidence": 0.7,
    }
    storage.upsert_item("paper_cards", "card1", card_data)
    return card_data


class TestEvidenceTableService:
    def test_build_for_paper_returns_evidence_records(self, service, sample_card):
        records = service.build_for_paper("p1")
        assert len(records) > 0
        assert records[0].paper_id == "p1"

    def test_build_for_project_aggregates_all_cards(self, service, sample_card):
        records = service.build_for_project("proj1")
        assert len(records) > 0
        assert all(r.project_id == "proj1" for r in records)

    def test_query_filters_by_paper_id(self, service, sample_card):
        service.build_for_project("proj1")
        records = service.query("proj1", {"paper_id": "p1"})
        assert len(records) > 0

    def test_query_by_scope_filters_papers(self, service, sample_card):
        service.build_for_project("proj1")
        scope = RetrievalScope(
            scope_type=ScopeType.SELECTED_PAPERS,
            project_id="proj1",
            paper_ids=["p1"],
        )
        records = service.query_by_scope(scope)
        assert len(records) > 0
        assert all(r.paper_id == "p1" for r in records)

    def test_query_by_scope_filters_topics(self, service, sample_card):
        service.build_for_project("proj1")
        scope = RetrievalScope(
            scope_type=ScopeType.TOPIC_GROUP,
            project_id="proj1",
            topic_ids=["feedback mechanism"],
        )
        records = service.query_by_scope(scope)
        assert len(records) > 0

    def test_build_for_empty_project_returns_empty(self, service):
        records = service.build_for_project("empty_proj")
        assert len(records) == 0


class TestNormalizeTopics:
    def test_normalize_merges_similar_topics(self):
        cards = [
            PaperCard(card_id="c1", paper_id="p1", project_id="proj1", topics=["LLM feedback"]),
            PaperCard(card_id="c2", paper_id="p2", project_id="proj1", topics=["AI feedback"]),
            PaperCard(card_id="c3", paper_id="p3", project_id="proj1", topics=["automatic feedback"]),
        ]
        result = normalize_topics(cards)
        assert "feedback mechanism" in result
        assert len(result["feedback mechanism"]) == 3

    def test_normalize_keeps_distinct_topics_separate(self):
        cards = [
            PaperCard(card_id="c1", paper_id="p1", project_id="proj1", topics=["topic a"]),
            PaperCard(card_id="c2", paper_id="p2", project_id="proj1", topics=["topic b"]),
        ]
        result = normalize_topics(cards)
        assert len(result) == 2
