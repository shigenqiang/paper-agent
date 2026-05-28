"""ScopeQAService 测试"""

import pytest

from src.agents_v3.research_workspace.scope_qa import ScopeQAService


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.scope_qa.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.scope.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return ScopeQAService()


@pytest.fixture
def sample_data(service):
    storage = service.storage
    storage.upsert_item("papers", "p1", {
        "paper_id": "p1", "project_id": "proj1", "title": "Paper 1", "included": True,
    })
    storage.upsert_item("papers", "p2", {
        "paper_id": "p2", "project_id": "proj1", "title": "Paper 2", "included": True,
    })
    storage.upsert_item("evidence_records", "e1", {
        "evidence_id": "e1",
        "project_id": "proj1",
        "paper_id": "p1",
        "topic": "feedback",
        "method": "experiment",
        "finding": "Improved test scores",
        "limitation": "Small sample size",
    })
    storage.upsert_item("evidence_records", "e2", {
        "evidence_id": "e2",
        "project_id": "proj1",
        "paper_id": "p2",
        "topic": "feedback",
        "method": "survey",
        "finding": "Higher engagement",
        "limitation": "Short duration",
    })
    storage.upsert_item("paper_cards", "card1", {
        "card_id": "card1",
        "paper_id": "p1",
        "project_id": "proj1",
        "method": "experiment",
        "title": "Paper 1",
    })
    storage.upsert_item("paper_cards", "card2", {
        "card_id": "card2",
        "paper_id": "p2",
        "project_id": "proj1",
        "method": "survey",
        "title": "Paper 2",
    })
    return storage


class TestScopeQAService:
    def test_classify_intent_limitation_returns_limitation_analysis(self, service):
        assert service.classify_intent("这些论文的不足是什么？") == "limitation_analysis"

    def test_classify_intent_method_returns_method_analysis(self, service):
        assert service.classify_intent("用了什么方法？") == "method_analysis"

    def test_classify_intent_review_returns_review_generation(self, service):
        assert service.classify_intent("写一篇文献综述") == "review_generation"

    def test_classify_intent_innovation_returns_innovation_generation(self, service):
        assert service.classify_intent("有什么创新点？") == "innovation_generation"

    def test_classify_intent_comparison_returns_method_compare(self, service):
        assert service.classify_intent("比较这些论文") == "method_compare"

    def test_classify_intent_default_returns_summary(self, service):
        assert service.classify_intent("这些论文讲了什么？") == "summary"

    def test_answer_returns_valid_response_with_evidence(self, service, sample_data):
        response = service.answer("proj1", "这些论文讲了什么？", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1", "p2"],
        })
        assert response.answer
        assert response.scope_summary
        assert len(response.supporting_papers) > 0

    def test_answer_limitation_returns_limitation_content(self, service, sample_data):
        response = service.answer("proj1", "这些论文的不足是什么？", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1", "p2"],
        })
        assert "不足" in response.answer or "局限" in response.answer
        assert response.intent == "limitation_analysis"

    def test_answer_method_returns_method_content(self, service, sample_data):
        response = service.answer("proj1", "用了什么方法？", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1", "p2"],
        })
        assert "experiment" in response.answer or "survey" in response.answer

    def test_answer_innovation_suggests_report_generation(self, service, sample_data):
        response = service.answer("proj1", "有什么创新点？", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1", "p2"],
        })
        assert "generate_innovation_report" in response.suggested_actions

    def test_answer_includes_uncertainty_statement(self, service, sample_data):
        response = service.answer("proj1", "讲了什么？", {
            "type": "selected_papers",
            "selected_paper_ids": ["p1"],
        })
        assert response.uncertainty

    def test_answer_no_evidence_handles_gracefully(self, service, sample_data):
        response = service.answer("proj1", "讲了什么？", {
            "type": "selected_papers",
            "selected_paper_ids": ["nonexistent"],
        })
        assert response.answer
