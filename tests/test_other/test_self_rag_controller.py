"""
SELF-RAG Controller 单元测试

测试SELF-RAG反思控制器功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents_v2.retrieval.self_rag_controller import (
    SELF_RAGController,
    RAGResponse,
    DocumentEvaluation,
    self_rag_answer
)


class TestSELFRAGController:
    """SELF-RAG控制器测试"""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.generations = [[MagicMock(text="是")]]
        self.mock_llm.agenerate = AsyncMock(return_value=self.mock_response)

        self.controller = SELF_RAGController(
            llm=self.mock_llm,
            relevance_threshold=0.7,
            utility_threshold=0.5
        )

    @pytest.mark.asyncio
    async def test_should_retrieve_yes(self):
        """测试需要检索"""
        self.mock_response.generations = [[MagicMock(text="是")]]

        result = await self.controller.should_retrieve("最新的人工智能研究")
        assert result is True

    @pytest.mark.asyncio
    async def test_should_retrieve_no(self):
        """测试不需要检索"""
        self.mock_response.generations = [[MagicMock(text="否")]]

        result = await self.controller.should_retrieve("简单的定义问题")
        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_relevance(self):
        """测试相关性评估"""
        self.mock_response.generations = [[MagicMock(text="0.8")]]

        result = await self.controller.evaluate_relevance(
            "Some document content",
            "What is AI"
        )
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_relevance_default(self):
        """测试相关性评估失败时返回默认值"""
        self.mock_llm.agenerate = AsyncMock(side_effect=Exception("error"))

        result = await self.controller.evaluate_relevance("doc", "query")
        assert result == 0.5

    @pytest.mark.asyncio
    async def test_evaluate_utility(self):
        """测试有用性评估"""
        self.mock_response.generations = [[MagicMock(text="0.7")]]

        result = await self.controller.evaluate_utility(
            "Document content",
            "Query",
            "Partial answer"
        )
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_should_use_document_true(self):
        """测试应该使用文档"""
        self.mock_response.generations = [[MagicMock(text="0.8")]]

        result = await self.controller.should_use_document(
            "Relevant document",
            "Test query"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_should_use_document_low_relevance(self):
        """测试低相关性时不使用文档"""
        self.mock_response.generations = [[MagicMock(text="0.3")]]

        result = await self.controller.should_use_document(
            "Irrelevant document",
            "Test query"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_documents(self):
        """测试批量文档评估"""
        docs = ["doc1", "doc2", "doc3"]
        mock_evals = [
            MagicMock(should_use=True, relevance_score=0.8, utility_score=0.7),
            MagicMock(should_use=True, relevance_score=0.9, utility_score=0.8),
            MagicMock(should_use=False, relevance_score=0.3, utility_score=0.2)
        ]

        # 需要先设置评估返回值的顺序
        call_count = [0]
        async def mock_evaluate(*args):
            val = mock_evals[min(call_count[0], len(mock_evals) - 1)]
            call_count[0] += 1
            return val.relevance_score

        async def mock_utility(*args):
            val = mock_evals[min(call_count[0] // 2, len(mock_evals) - 1)]
            return val.utility_score

        self.controller.evaluate_relevance = mock_evaluate
        self.controller.evaluate_utility = mock_utility

        results = await self.controller.evaluate_documents(docs, "query")
        assert len(results) == 3


class TestRAGResponse:
    """RAG响应测试"""

    def test_create_response(self):
        """测试创建响应"""
        response = RAGResponse(
            answer="Test answer",
            used_docs=["[文档1]", "[文档2]"],
            reflection="Used 2 documents",
            retrieval_needed=True,
            documents_evaluated=2
        )

        assert response.answer == "Test answer"
        assert len(response.used_docs) == 2
        assert response.retrieval_needed is True

    def test_response_default_values(self):
        """测试默认值"""
        response = RAGResponse(
            answer="Test",
            used_docs=[],
            reflection="Test"
        )

        assert response.retrieval_needed is True
        assert response.documents_evaluated == 0

    def test_response_with_metadata(self):
        """测试带元数据的响应"""
        response = RAGResponse(
            answer="Test",
            used_docs=[],
            reflection="Test",
            metadata={"generation_time": 1.5}
        )

        assert response.metadata["generation_time"] == 1.5


class TestDocumentEvaluation:
    """文档评估测试"""

    def test_create_evaluation(self):
        """测试创建评估"""
        eval_result = DocumentEvaluation(
            document="Test doc",
            relevance_score=0.8,
            utility_score=0.6,
            should_use=True,
            reasoning="Good match"
        )

        assert eval_result.relevance_score == 0.8
        assert eval_result.should_use is True

    def test_evaluation_long_document(self):
        """测试长文档不被截断"""
        long_doc = "x" * 200
        eval_result = DocumentEvaluation(
            document=long_doc,
            relevance_score=0.5,
            utility_score=0.5,
            should_use=False,
            reasoning="Test"
        )

        # SELF-RAG的DocumentEvaluation不截断文档
        assert len(eval_result.document) == 200


class TestGenerateWithReflection:
    """带反思的生成测试"""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.generations = [[MagicMock(text="Test answer")]]
        self.mock_llm.agenerate = AsyncMock(return_value=self.mock_response)

        self.controller = SELF_RAGController(llm=self.mock_llm)

    @pytest.mark.asyncio
    async def test_generate_with_no_docs(self):
        """测试无文档时生成"""
        result = await self.controller.generate_with_reflection(
            "test query",
            []
        )

        assert isinstance(result, RAGResponse)
        assert result.used_docs == []

    @pytest.mark.asyncio
    async def test_generate_with_docs(self):
        """测试有文档时生成"""
        docs = ["doc1", "doc2"]

        # Mock评估方法
        async def mock_relevance(*args):
            return 0.9

        async def mock_utility(*args):
            return 0.8

        self.controller.evaluate_relevance = mock_relevance
        self.controller.evaluate_utility = mock_utility

        result = await self.controller.generate_with_reflection(
            "test query",
            docs,
            max_context_docs=5
        )

        assert isinstance(result, RAGResponse)


class TestIterativeRAG:
    """迭代RAG测试"""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.generations = [[MagicMock(text="Test answer")]]
        self.mock_llm.agenerate = AsyncMock(return_value=self.mock_response)

        self.controller = SELF_RAGController(llm=self.mock_llm)

    @pytest.mark.asyncio
    async def test_iterative_rag_no_retriever(self):
        """测试无检索器的迭代"""
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])

        result = await self.controller.iterative_rag(
            "test query",
            mock_retriever,
            max_iterations=1
        )

        assert isinstance(result, RAGResponse)

    @pytest.mark.asyncio
    async def test_iterative_rag_with_docs(self):
        """测试有文档的迭代"""
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=["doc1", "doc2"])

        async def mock_relevance(*args):
            return 0.9

        async def mock_utility(*args):
            return 0.8

        self.controller.evaluate_relevance = mock_relevance
        self.controller.evaluate_utility = mock_utility

        result = await self.controller.iterative_rag(
            "test query",
            mock_retriever,
            max_iterations=1
        )

        assert isinstance(result, RAGResponse)


class TestConvenienceFunction:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_self_rag_answer(self):
        """测试便捷函数"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.generations = [[MagicMock(text="Answer")]]
        mock_llm.agenerate = AsyncMock(return_value=mock_response)

        result = await self_rag_answer(
            "test query",
            ["doc1", "doc2"],
            mock_llm
        )

        assert isinstance(result, RAGResponse)


class TestQueryRewrite:
    """查询改写测试"""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.generations = [[MagicMock(text="rewritten query")]]
        self.mock_llm.agenerate = AsyncMock(return_value=self.mock_response)

        self.controller = SELF_RAGController(llm=self.mock_llm)

    @pytest.mark.asyncio
    async def test_rewrite_query(self):
        """测试查询改写"""
        result = await self.controller._rewrite_query(
            "original query",
            ["irrelevant doc"]
        )

        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])