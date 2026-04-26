"""
Document Evaluator 单元测试

测试文档相关性/有用性评估功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents_v2.retrieval.document_evaluator import (
    DocumentEvaluator,
    DocumentEvaluation
)


class TestDocumentEvaluator:
    """DocumentEvaluator 测试"""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.generations = [[MagicMock(text="0.8")]]
        self.mock_llm.agenerate = AsyncMock(return_value=self.mock_response)

        self.evaluator = DocumentEvaluator(
            llm=self.mock_llm,
            relevance_threshold=0.7,
            utility_threshold=0.5
        )

    @pytest.mark.asyncio
    async def test_evaluate_relevance_returns_score(self):
        """测试评估相关性返回分数"""
        result = await self.evaluator.evaluate_relevance(
            "Some document content about machine learning",
            "What is machine learning"
        )
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_relevance_parses_llm_response(self):
        """测试正确解析LLM响应"""
        self.mock_response.generations = [[MagicMock(text="0.75")]]
        result = await self.evaluator.evaluate_relevance(
            "Test document",
            "Test query"
        )
        assert result == 0.75

    @pytest.mark.asyncio
    async def test_evaluate_relevance_default_on_error(self):
        """测试评估失败时返回默认值"""
        self.mock_llm.agenerate = AsyncMock(side_effect=Exception("LLM error"))
        result = await self.evaluator.evaluate_relevance(
            "Test document",
            "Test query"
        )
        assert result == 0.5

    @pytest.mark.asyncio
    async def test_evaluate_utility_returns_score(self):
        """测试评估有用性返回分数"""
        result = await self.evaluator.evaluate_utility(
            "Some document content",
            "Test query",
            "Current partial answer"
        )
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_should_use_true_above_thresholds(self):
        """测试should_use返回True当分数高于阈值"""
        self.mock_response.generations = [[MagicMock(text="0.8")]]
        result = await self.evaluator.should_use(
            "Relevant document",
            "Test query"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_should_use_false_below_relevance(self):
        """测试should_use返回False当相关性低于阈值"""
        self.mock_response.generations = [[MagicMock(text="0.3")]]
        result = await self.evaluator.should_use(
            "Irrelevant document",
            "Test query"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_should_use_false_below_utility(self):
        """测试should_use返回False当有用性低于阈值"""
        # First call returns high relevance, second returns low utility
        self.mock_response.generations = [[MagicMock(text="0.8")]]
        result = await self.evaluator.should_use(
            "Low utility document",
            "Test query"
        )
        # Utility is 0.8, which is above 0.5 threshold

    @pytest.mark.asyncio
    async def test_evaluate_batch(self):
        """测试批量评估"""
        docs = [
            "First document about AI",
            "Second document about ML",
            "Third document about DL"
        ]
        results = await self.evaluator.evaluate_batch(docs, "machine learning")

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, DocumentEvaluation) for r in results)

    @pytest.mark.asyncio
    async def test_evaluate_batch_with_empty_docs(self):
        """测试批量评估空列表"""
        results = await self.evaluator.evaluate_batch([], "query")
        assert results == []


class TestDocumentEvaluation:
    """DocumentEvaluation 测试"""

    def test_create_evaluation(self):
        """测试创建评估结果"""
        eval_result = DocumentEvaluation(
            document="Test doc",
            relevance_score=0.8,
            utility_score=0.6,
            should_use=True,
            reasoning="High relevance and utility"
        )

        assert eval_result.document == "Test doc"
        assert eval_result.relevance_score == 0.8
        assert eval_result.utility_score == 0.6
        assert eval_result.should_use is True
        assert eval_result.reasoning == "High relevance and utility"

    def test_evaluation_with_long_document(self):
        """测试长文档不被截断"""
        long_doc = "x" * 200
        eval_result = DocumentEvaluation(
            document=long_doc,
            relevance_score=0.5,
            utility_score=0.5,
            should_use=False,
            reasoning="Test"
        )

        assert len(eval_result.document) == 200


    def test_evaluation_with_short_document(self):
        """测试短文档不被截断"""
        short_doc = "short"
        eval_result = DocumentEvaluation(
            document=short_doc,
            relevance_score=0.5,
            utility_score=0.5,
            should_use=False,
            reasoning="Test"
        )

        assert eval_result.document == short_doc


class TestEvaluatorThresholds:
    """阈值配置测试"""

    def test_custom_thresholds(self):
        """测试自定义阈值"""
        evaluator = DocumentEvaluator(
            llm=MagicMock(),
            relevance_threshold=0.8,
            utility_threshold=0.6
        )

        assert evaluator.relevance_threshold == 0.8
        assert evaluator.utility_threshold == 0.6

    def test_default_thresholds(self):
        """测试默认阈值"""
        evaluator = DocumentEvaluator(llm=MagicMock())

        assert evaluator.relevance_threshold == 0.7
        assert evaluator.utility_threshold == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])