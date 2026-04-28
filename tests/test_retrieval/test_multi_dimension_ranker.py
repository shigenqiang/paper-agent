"""
Multi-Dimension Ranker Tests

Tests for:
- MultiDimensionRanker: Multi-dimension ranking
- PersonalizationRanker: Personalized ranking
- DimensionScorer: Various dimension scorers
"""
import pytest
from src.agents_v2.retrieval.multi_dimension_ranker import (
    MultiDimensionRanker,
    PersonalizationRanker,
    RelevanceScorer,
    QualityScorer,
    DiversityScorer,
    RankingStrategy,
    RankItem,
    rank_results,
    rank_with_personalization
)


class TestRelevanceScorer:
    """RelevanceScorer Tests"""

    def test_score_with_query(self):
        """Test scoring with query"""
        scorer = RelevanceScorer()
        item = {"text": "machine learning is great"}
        score = scorer.score(item, "machine learning")
        assert score > 0.5

    def test_score_exact_match_boost(self):
        """Test exact match boost"""
        scorer = RelevanceScorer(boost_exact_match=True)
        item = {"text": "machine learning is great"}
        exact_score = scorer.score(item, "machine learning")
        partial_score = scorer.score(item, "machine")
        assert exact_score >= partial_score

    def test_score_no_query(self):
        """Test scoring without query"""
        scorer = RelevanceScorer()
        item = {"text": "some text"}
        score = scorer.score(item, "")
        assert score == 0.5

    def test_score_empty_text(self):
        """Test scoring with empty text"""
        scorer = RelevanceScorer()
        item = {"text": ""}
        score = scorer.score(item, "query")
        assert score == 0.0


class TestQualityScorer:
    """QualityScorer Tests"""

    def test_score_with_metadata(self):
        """Test scoring with quality metadata"""
        scorer = QualityScorer()
        item = {
            "metadata": {
                "source": "arxiv",
                "citations": 50,
                "days_old": 100
            }
        }
        score = scorer.score(item)
        assert 0 <= score <= 1.0

    def test_score_no_metadata(self):
        """Test scoring without metadata"""
        scorer = QualityScorer()
        item = {}
        score = scorer.score(item)
        assert 0 <= score <= 1.0

    def test_score_citation_normalization(self):
        """Test citation count normalization"""
        scorer = QualityScorer()
        low_citations = {"metadata": {"citations": 10}}
        high_citations = {"metadata": {"citations": 500}}
        score_low = scorer.score(low_citations)
        score_high = scorer.score(high_citations)
        assert score_high >= score_low


class TestDiversityScorer:
    """DiversityScorer Tests"""

    def test_score_new_topic(self):
        """Test scoring with new topic"""
        scorer = DiversityScorer()
        item = {"metadata": {"topics": ["ai"]}}
        score = scorer.score(item)
        assert score == 1.0

    def test_score_repeated_topic(self):
        """Test scoring with repeated topic"""
        scorer = DiversityScorer()
        scorer.update_selection(["ai"])

        item = {"metadata": {"topics": ["ai"]}}
        score = scorer.score(item)
        assert score < 1.0

    def test_update_selection(self):
        """Test updating selection"""
        scorer = DiversityScorer()
        scorer.update_selection(["ai", "ml"])
        assert scorer.selected_topics["ai"] == 1
        assert scorer.selected_topics["ml"] == 1


class TestRankItem:
    """RankItem Tests"""

    def test_create_rank_item(self):
        """Test creating a rank item"""
        item = RankItem(
            item_id="item1",
            score=0.8,
            dimensions={"relevance": 0.9, "quality": 0.7},
            metadata={"source": "arxiv"}
        )
        assert item.item_id == "item1"
        assert item.score == 0.8
        assert item.dimensions["relevance"] == 0.9


class TestMultiDimensionRanker:
    """MultiDimensionRanker Tests"""

    def setup_method(self):
        self.ranker = MultiDimensionRanker()

    def test_rank_empty_list(self):
        """Test ranking empty list"""
        result = self.ranker.rank([])
        assert result.ranked_items == []
        assert result.total_score == {}

    def test_rank_single_item(self):
        """Test ranking single item"""
        items = [{"id": "item1", "text": "test content", "metadata": {}}]
        result = self.ranker.rank(items, query="test")
        assert len(result.ranked_items) == 1
        assert result.ranked_items[0].item_id == "item1"

    def test_rank_multiple_items(self):
        """Test ranking multiple items"""
        items = [
            {"id": "item1", "text": "machine learning", "metadata": {"source": "arxiv"}},
            {"id": "item2", "text": "deep learning neural networks", "metadata": {"source": "pubmed"}},
            {"id": "item3", "text": "natural language processing", "metadata": {"source": "arxiv"}},
        ]
        result = self.ranker.rank(items, query="deep learning", top_k=3)
        assert len(result.ranked_items) == 3
        assert result.metadata["strategy"] == "weighted_sum"

    def test_rank_top_k(self):
        """Test top-k limiting"""
        items = [
            {"id": f"item{i}", "text": f"content {i}", "metadata": {}}
            for i in range(10)
        ]
        result = self.ranker.rank(items, top_k=5)
        assert len(result.ranked_items) == 5

    def test_set_weights(self):
        """Test setting custom weights"""
        self.ranker.set_weights({"relevance": 0.6, "quality": 0.4})
        assert self.ranker.weights["relevance"] == 0.6
        assert self.ranker.weights["quality"] == 0.4

    def test_set_weights_normalized(self):
        """Test weights are normalized"""
        self.ranker.set_weights({"relevance": 0.8, "quality": 0.2})
        total = sum(self.ranker.weights.values())
        assert abs(total - 1.0) < 0.01


class TestRankingStrategies:
    """Test different ranking strategies"""

    def test_weighted_sum_strategy(self):
        """Test weighted sum strategy"""
        ranker = MultiDimensionRanker(RankingStrategy.WEIGHTED_SUM)
        items = [
            {"id": "item1", "text": "test", "metadata": {"source": "arxiv", "citations": 100}},
            {"id": "item2", "text": "test", "metadata": {"source": "web", "citations": 0}},
        ]
        result = ranker.rank(items, query="test")
        assert result.metadata["strategy"] == "weighted_sum"

    def test_topsis_strategy(self):
        """Test TOPSIS strategy"""
        ranker = MultiDimensionRanker(RankingStrategy.TOPSIS)
        items = [
            {"id": "item1", "text": "test", "metadata": {"source": "arxiv", "citations": 100}},
            {"id": "item2", "text": "test", "metadata": {"source": "web", "citations": 0}},
        ]
        result = ranker.rank(items, query="test")
        assert result.metadata["strategy"] == "topsis"

    def test_rrf_strategy(self):
        """Test RRF strategy"""
        ranker = MultiDimensionRanker(RankingStrategy.RRF)
        items = [
            {"id": "item1", "text": "machine", "metadata": {}},
            {"id": "item2", "text": "learning", "metadata": {}},
        ]
        result = ranker.rank(items, query="machine learning")
        assert result.metadata["strategy"] == "rrf"


class TestPersonalizationRanker:
    """PersonalizationRanker Tests"""

    def setup_method(self):
        self.ranker = PersonalizationRanker()

    def test_rank_without_preferences(self):
        """Test ranking without user preferences"""
        items = [
            {"id": "item1", "text": "test", "metadata": {}},
        ]
        result = self.ranker.rank_for_user("user1", items, query="test")
        assert result.metadata["personalized"] is False

    def test_rank_with_preferences(self):
        """Test ranking with user preferences"""
        self.ranker.set_user_profile("user1", {"quality": 0.8, "relevance": 0.2})
        items = [
            {"id": "item1", "text": "test", "metadata": {"source": "arxiv", "citations": 100}},
            {"id": "item2", "text": "test", "metadata": {"source": "web", "citations": 0}},
        ]
        result = self.ranker.rank_for_user("user1", items, query="test")
        assert result.metadata["personalized"] is True
        assert result.metadata["user_id"] == "user1"


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_rank_results_function(self):
        """Test rank_results convenience function"""
        items = [
            {"id": "item1", "text": "test", "metadata": {}},
        ]
        result = rank_results(items, query="test", top_k=1)
        assert len(result.ranked_items) == 1

    def test_rank_with_personalization_function(self):
        """Test rank_with_personalization function"""
        items = [
            {"id": "item1", "text": "test", "metadata": {}},
        ]
        result = rank_with_personalization(
            user_id="user1",
            items=items,
            query="test",
            preferences={"quality": 0.9}
        )
        assert result.metadata["personalized"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])