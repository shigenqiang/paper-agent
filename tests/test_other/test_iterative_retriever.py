"""
Iterative Retriever 单元测试

测试迭代式检索功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents_v2.retrieval.iterative_retriever import (
    IterativeRetriever,
    AdaptiveRetriever,
    RetrievalResult,
    RetrievalStep,
    iterative_retrieve
)


class TestIterativeRetriever:
    """IterativeRetriever 测试"""

    def setup_method(self):
        self.mock_retriever = MagicMock()
        self.mock_retriever.retrieve = AsyncMock(return_value=[])

        self.mock_controller = MagicMock()
        self.mock_controller.evaluate_documents = AsyncMock(return_value=[])
        self.mock_controller._rewrite_query = AsyncMock(return_value="rewritten query")

        with patch('src.agents_v2.retrieval.iterative_retriever.logger'):
            self.iterative = IterativeRetriever(
                base_retriever=self.mock_retriever,
                self_rag_controller=self.mock_controller,
                max_iterations=3,
                min_relevant_docs=5,
                relevance_threshold=0.7
            )

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self):
        """测试空检索结果"""
        self.mock_retriever.retrieve = AsyncMock(return_value=[])

        result = await self.iterative.retrieve("test query")

        assert isinstance(result, RetrievalResult)
        assert result.documents == []
        assert result.converged is False

    @pytest.mark.asyncio
    async def test_retrieve_single_iteration(self):
        """测试单次迭代"""
        mock_docs = ["doc1", "doc2"]
        self.mock_retriever.retrieve = AsyncMock(return_value=mock_docs)

        mock_evals = [
            MagicMock(should_use=True, relevance_score=0.8),
            MagicMock(should_use=True, relevance_score=0.9)
        ]
        self.mock_controller.evaluate_documents = AsyncMock(return_value=mock_evals)

        result = await self.iterative.retrieve("test query", top_k=10)

        assert len(result.documents) == 2
        assert result.iterations >= 1

    @pytest.mark.asyncio
    async def test_retrieve_max_iterations(self):
        """测试最大迭代次数"""
        self.mock_retriever.retrieve = AsyncMock(
            return_value=["doc1", "doc2", "doc3"]
        )

        mock_evals = [
            MagicMock(should_use=False, relevance_score=0.3),
            MagicMock(should_use=False, relevance_score=0.3),
            MagicMock(should_use=False, relevance_score=0.3)
        ]
        self.mock_controller.evaluate_documents = AsyncMock(return_value=mock_evals)

        result = await self.iterative.retrieve("test query")

        assert result.iterations == self.iterative.max_iterations

    @pytest.mark.asyncio
    async def test_retrieve_converged_early(self):
        """测试提前收敛"""
        self.mock_retriever.retrieve = AsyncMock(
            return_value=["doc1", "doc2", "doc3", "doc4", "doc5"]
        )

        mock_evals = [
            MagicMock(should_use=True, relevance_score=0.9),
            MagicMock(should_use=True, relevance_score=0.9),
            MagicMock(should_use=True, relevance_score=0.9),
            MagicMock(should_use=True, relevance_score=0.9),
            MagicMock(should_use=True, relevance_score=0.9)
        ]
        self.mock_controller.evaluate_documents = AsyncMock(return_value=mock_evals)

        result = await self.iterative.retrieve("test query")

        assert result.converged is True
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_retrieve_with_query_rewrite(self):
        """测试带查询改写的检索"""
        self.mock_retriever.retrieve = AsyncMock(
            side_effect=[
                ["irrelevant1", "irrelevant2"],
                ["relevant1"]
            ]
        )

        mock_evals_iter1 = [
            MagicMock(should_use=False, relevance_score=0.2),
            MagicMock(should_use=False, relevance_score=0.2)
        ]
        mock_evals_iter2 = [
            MagicMock(should_use=True, relevance_score=0.9)
        ]

        self.mock_controller.evaluate_documents = AsyncMock(
            side_effect=[mock_evals_iter1, mock_evals_iter2]
        )

        rewriter = AsyncMock(return_value="rewritten query")
        self.iterative.set_query_rewriter(rewriter)

        result = await self.iterative.retrieve("original query")

        # 返回的result包含query_history
        assert isinstance(result, RetrievalResult)
        assert len(result.query_history) >= 1

    def test_deduplicate(self):
        """测试去重"""
        docs = ["doc1", "doc2", "doc1", "doc3", "doc2"]
        result = self.iterative._deduplicate(docs)

        assert len(result) == 3
        assert "doc1" in result
        assert "doc2" in result
        assert "doc3" in result

    @pytest.mark.asyncio
    async def test_retrieve_with_feedback(self):
        """测试带反馈的检索"""
        self.mock_retriever.retrieve = AsyncMock(return_value=["doc1"])

        result = await self.iterative.retrieve_with_feedback(
            "original query",
            "I need more about deep learning"
        )

        assert isinstance(result, RetrievalResult)


class TestRetrievalResult:
    """RetrievalResult 测试"""

    def test_create_result(self):
        """测试创建检索结果"""
        result = RetrievalResult(
            documents=["doc1", "doc2"],
            iterations=2,
            query_history=["q1", "q2"],
            total_time=1.5,
            converged=True
        )

        assert len(result.documents) == 2
        assert result.iterations == 2
        assert result.converged is True
        assert result.total_time == 1.5

    def test_result_with_metadata(self):
        """测试带元数据的检索结果"""
        result = RetrievalResult(
            documents=["doc1"],
            iterations=1,
            query_history=["query"],
            total_time=0.5,
            converged=True,
            metadata={"strategy": "iterative", "difficulty": 0.6}
        )

        assert result.metadata["strategy"] == "iterative"


class TestRetrievalStep:
    """RetrievalStep 测试"""

    def test_create_step(self):
        """测试创建检索步骤"""
        step = RetrievalStep(
            iteration=1,
            query="test query",
            documents_retrieved=["d1", "d2"],
            documents_used=["d1"],
            evaluation_summary={"relevant": 1, "total": 2}
        )

        assert step.iteration == 1
        assert step.query == "test query"
        assert len(step.documents_retrieved) == 2
        assert len(step.documents_used) == 1


class TestAdaptiveRetriever:
    """AdaptiveRetriever 测试"""

    def setup_method(self):
        self.mock_base = MagicMock()
        self.mock_base.retrieve = AsyncMock(return_value=[])

        mock_controller = MagicMock()
        mock_controller.evaluate_documents = AsyncMock(return_value=[])

        with patch('src.agents_v2.retrieval.iterative_retriever.logger'):
            self.iterative = IterativeRetriever(
                base_retriever=self.mock_base,
                self_rag_controller=mock_controller
            )

            self.adaptive = AdaptiveRetriever(
                iterative_retriever=self.iterative
            )

    @pytest.mark.asyncio
    async def test_classify_difficulty_default(self):
        """测试默认难度分类"""
        difficulty = await self.adaptive.classify_difficulty("simple query")
        assert difficulty <= 1.0
        assert difficulty >= 0.0

    @pytest.mark.asyncio
    async def test_classify_difficulty_complex_query(self):
        """测试复杂查询难度"""
        difficulty = await self.adaptive.classify_difficulty(
            "分析比较综合评估这些深度学习方法的效果和优缺点"
        )
        assert difficulty > 0.5

    @pytest.mark.asyncio
    async def test_retrieve_low_difficulty(self):
        """测试低难度检索策略"""
        self.mock_base.retrieve = AsyncMock(return_value=[])

        result = await self.adaptive.retrieve("what is AI")
        # 难度>=0.3时使用iterative策略
        assert result.metadata.get("strategy") in ["simple", "iterative"]

    @pytest.mark.asyncio
    async def test_retrieve_high_difficulty(self):
        """测试高难度检索策略"""
        self.mock_base.retrieve = AsyncMock(return_value=[])

        result = await self.adaptive.retrieve(
            "分析比较综合评估这些深度学习方法的效果和优缺点"
        )
        assert result.metadata.get("strategy") == "enhanced_iterative"


class TestIterativeRetrieverEdgeCases:
    """边界情况测试"""

    def setup_method(self):
        self.mock_retriever = MagicMock()
        self.mock_retriever.retrieve = AsyncMock(return_value=[])

        mock_controller = MagicMock()
        mock_controller.evaluate_documents = AsyncMock(return_value=[])
        mock_controller._rewrite_query = AsyncMock(return_value="q")

        with patch('src.agents_v2.retrieval.iterative_retriever.logger'):
            self.iterative = IterativeRetriever(
                base_retriever=self.mock_retriever,
                self_rag_controller=mock_controller
            )

    @pytest.mark.asyncio
    async def test_retrieve_exception_handling(self):
        """测试异常处理"""
        self.mock_retriever.retrieve = AsyncMock(
            side_effect=Exception("Retrieval error")
        )

        result = await self.iterative.retrieve("test query")
        assert result.documents == []

    def test_get_stats_empty(self):
        """测试空统计"""
        stats = self.iterative.get_retrieval_stats()
        assert stats["status"] == "no_history"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])