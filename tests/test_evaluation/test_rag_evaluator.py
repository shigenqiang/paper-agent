"""
RAG Evaluator Tests

Tests for:
- RAGEvaluator: RAG system evaluation
- RetrievalMetrics: Retrieval metrics calculation
"""
import pytest
from src.agents_v2.evaluation.rag_evaluator import (
    RAGEvaluator,
    RetrievalMetrics,
    RetrievalEvalResult,
    GenerationEvalResult,
    RAGEvalResult,
    EvaluationMetric,
    evaluate_rag,
    evaluate_retrieval
)


class TestRetrievalMetrics:
    """RetrievalMetrics Tests"""

    def test_precision_at_k(self):
        """Test precision at k"""
        retrieved = ["doc1", "doc2", "doc3", "doc4"]
        relevant = ["doc1", "doc3"]
        precision = RetrievalMetrics.precision_at_k(retrieved, relevant, 4)
        assert precision == 0.5  # 2 hits out of 4

    def test_precision_at_k_zero(self):
        """Test precision at k with zero k"""
        retrieved = ["doc1", "doc2"]
        relevant = ["doc1"]
        precision = RetrievalMetrics.precision_at_k(retrieved, relevant, 0)
        assert precision == 0.0

    def test_recall_at_k(self):
        """Test recall at k"""
        retrieved = ["doc1", "doc2", "doc3", "doc4"]
        relevant = ["doc1", "doc2", "doc3"]
        recall = RetrievalMetrics.recall_at_k(retrieved, relevant, 3)
        assert recall == 1.0  # All 3 relevant docs retrieved in top 3

    def test_recall_at_k_partial(self):
        """Test recall at k with partial retrieval"""
        retrieved = ["doc1", "doc2"]
        relevant = ["doc1", "doc2", "doc3"]
        recall = RetrievalMetrics.recall_at_k(retrieved, relevant, 2)
        assert recall == 2/3  # 2 out of 3 relevant retrieved

    def test_average_precision(self):
        """Test average precision"""
        retrieved = ["doc1", "doc2", "doc3", "doc4"]
        relevant = ["doc1", "doc3"]
        ap = RetrievalMetrics.average_precision(retrieved, relevant)
        # doc1 at position 1 (precision 1/1)
        # doc3 at position 3 (precision 2/3)
        # AP = (1 + 2/3) / 2 = 5/6
        assert ap > 0.8

    def test_mean_average_precision(self):
        """Test mean average precision"""
        retrieved_list = [
            ["doc1", "doc2", "doc3"],
            ["doc1", "doc2", "doc3"]
        ]
        relevant_list = [
            ["doc1", "doc3"],
            ["doc2"]
        ]
        map_score = RetrievalMetrics.mean_average_precision(retrieved_list, relevant_list)
        assert 0 <= map_score <= 1.0


class TestRetrievalEvalResult:
    """RetrievalEvalResult Tests"""

    def test_create_result(self):
        """Test creating retrieval eval result"""
        result = RetrievalEvalResult(
            precision=0.8,
            recall=0.7,
            f1=0.75,
            mrr=0.9,
            ndcg=0.85
        )
        assert result.precision == 0.8
        assert result.recall == 0.7
        assert result.f1 == 0.75


class TestGenerationEvalResult:
    """GenerationEvalResult Tests"""

    def test_create_result(self):
        """Test creating generation eval result"""
        result = GenerationEvalResult(
            relevance=0.9,
            faithfulness=0.85,
            accuracy=0.8
        )
        assert result.relevance == 0.9
        assert result.faithfulness == 0.85


class TestRAGEvaluator:
    """RAGEvaluator Tests"""

    def setup_method(self):
        self.evaluator = RAGEvaluator()

    def test_evaluate_retrieval_empty(self):
        """Test evaluating empty retrieval"""
        result = self.evaluator.evaluate_retrieval("query", [])
        assert result.precision == 0.0
        assert result.recall == 0.0

    def test_evaluate_retrieval_with_docs(self):
        """Test evaluating retrieval with documents"""
        docs = [
            {"id": "doc1", "text": "machine learning is great"},
            {"id": "doc2", "text": "deep learning is powerful"}
        ]
        result = self.evaluator.evaluate_retrieval("machine learning", docs)
        # Without relevant_docs, precision is not calculated
        assert result.context_utilization > 0

    def test_evaluate_retrieval_with_relevant(self):
        """Test evaluating with relevant docs"""
        docs = [
            {"id": "doc1", "text": "machine learning is great"},
            {"id": "doc2", "text": "deep learning is powerful"}
        ]
        result = self.evaluator.evaluate_retrieval("machine", docs, relevant_docs=["doc1"])
        # Precision = 1/2 = 0.5 (only doc1 is relevant out of 2 retrieved)
        assert result.precision == 0.5
        assert result.recall == 1.0  # doc1 is retrieved (1 out of 1 relevant)

    def test_evaluate_generation(self):
        """Test evaluating generation"""
        docs = [
            {"id": "doc1", "text": "machine learning is a subset of AI"},
            {"id": "doc2", "text": "deep learning uses neural networks"}
        ]
        answer = "Machine learning is part of AI."
        result = self.evaluator.evaluate_generation("What is machine learning?", answer, docs)
        assert result.relevance > 0

    def test_evaluate_generation_with_reference(self):
        """Test generation evaluation with reference"""
        docs = [{"id": "doc1", "text": "test content"}]
        answer = "This is the answer"
        reference = "This is the reference answer"
        result = self.evaluator.evaluate_generation("query", answer, docs, reference)
        assert result.accuracy >= 0

    def test_evaluate_full(self):
        """Test full RAG evaluation"""
        docs = [
            {"id": "doc1", "text": "machine learning is great"},
            {"id": "doc2", "text": "deep learning is powerful"}
        ]
        answer = "Machine learning is a great technology."

        result = self.evaluator.evaluate(
            query="What is machine learning?",
            answer=answer,
            retrieved_docs=docs,
            relevant_docs=["doc1"]
        )

        assert isinstance(result, RAGEvalResult)
        assert 0 <= result.overall_score <= 1.0
        assert result.retrieval is not None
        assert result.generation is not None

    def test_to_dict(self):
        """Test converting result to dictionary"""
        docs = [{"id": "doc1", "text": "test"}]
        result = self.evaluator.evaluate("query", "answer", docs)

        result_dict = result.to_dict()
        assert "retrieval" in result_dict
        assert "generation" in result_dict
        assert "overall_score" in result_dict


class TestContextUtilization:
    """Test context utilization calculation"""

    def setup_method(self):
        self.evaluator = RAGEvaluator()

    def test_context_utilization(self):
        """Test calculating context utilization"""
        docs = [
            {"id": "doc1", "text": "machine learning is great"},
            {"id": "doc2", "text": "deep learning is powerful"}
        ]
        result = self.evaluator.evaluate_retrieval("machine", docs)
        assert result.context_utilization >= 0


class TestFaithfulness:
    """Test faithfulness evaluation"""

    def setup_method(self):
        self.evaluator = RAGEvaluator()

    def test_faithfulness_with_matching_docs(self):
        """Test faithfulness when docs match answer"""
        docs = [{"id": "doc1", "text": "The capital of France is Paris."}]
        answer = "The capital of France is Paris."
        result = self.evaluator.evaluate_generation("What is the capital of France?", answer, docs)
        assert result.faithfulness > 0.5


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_evaluate_rag_function(self):
        """Test evaluate_rag convenience function"""
        docs = [{"id": "doc1", "text": "test content"}]
        result = evaluate_rag("query", "answer", docs)
        assert isinstance(result, RAGEvalResult)

    def test_evaluate_retrieval_function(self):
        """Test evaluate_retrieval convenience function"""
        docs = [{"id": "doc1", "text": "test content"}]
        result = evaluate_retrieval("query", docs)
        assert isinstance(result, RetrievalEvalResult)


class TestEvaluationMetric:
    """Test EvaluationMetric enum"""

    def test_all_metrics_exist(self):
        """Test all evaluation metrics exist"""
        assert EvaluationMetric.RETRIEVAL_PRECISION.value == "retrieval_precision"
        assert EvaluationMetric.RETRIEVAL_RECALL.value == "retrieval_recall"
        assert EvaluationMetric.ANSWER_RELEVANCE.value == "answer_relevance"
        assert EvaluationMetric.ANSWER_FAITHFULNESS.value == "answer_faithfulness"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])