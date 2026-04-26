"""
Cross-Encoder Reranker 单元测试

测试文档重排序功能
"""
import pytest
from unittest.mock import MagicMock, patch

from src.agents_v2.retrieval.cross_encoder_reranker import (
    CrossEncoderReranker,
    HybridReranker,
    RerankedDoc,
    rerank_documents
)


class TestCrossEncoderReranker:
    """CrossEncoderReranker 测试"""

    def setup_method(self):
        with patch('src.agents_v2.retrieval.cross_encoder_reranker.logger'):
            self.reranker = CrossEncoderReranker()

    def test_reranker_initialization(self):
        """测试重排序器初始化"""
        assert self.reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def test_reranker_without_model(self):
        """测试无模型时的简单重排序"""
        candidates = [
            "Machine learning is a subset of AI",
            "Deep learning uses neural networks",
            "Python is a programming language"
        ]

        result = self.reranker._rerank_simple("machine learning", candidates, top_k=3)

        assert len(result) == 3
        assert all(isinstance(r, RerankedDoc) for r in result)
        # 第一个应该是ML相关的
        assert result[0].doc == candidates[0]

    def test_rerank_empty_candidates(self):
        """测试空候选列表"""
        result = self.reranker._rerank_simple("query", [], top_k=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_async(self):
        """测试异步重排序"""
        candidates = ["doc1", "doc2", "doc3"]
        result = await self.reranker.rerank("query", candidates, top_k=2)

        assert len(result) == 2
        assert result[0].rank == 1
        assert result[1].rank == 2

    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self):
        """测试top_k限制"""
        candidates = [f"Document {i}" for i in range(20)]
        result = await self.reranker.rerank("test query", candidates, top_k=5)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_compute_similarity(self):
        """测试单文档相似度计算"""
        result = await self.reranker.compute_similarity(
            "machine learning",
            "Machine learning is great"
        )

        assert isinstance(result, float)
        assert 0.0 <= result <= 10.0  # 简单实现会返回非归一化分数

    def test_get_scores_batch(self):
        """测试批量评分"""
        documents = ["doc1 about AI", "doc2 about ML", "doc3 about DL"]
        scores = self.reranker.get_scores_batch("machine learning", documents)

        assert len(scores) == 3
        assert all(isinstance(s, (int, float)) for s in scores)

    def test_extract_key_phrases(self):
        """测试关键短语提取"""
        text = "machine learning is great"
        phrases = self.reranker._extract_key_phrases(text)

        assert "machine learning" in phrases
        assert "learning is great" in phrases
        assert "is great" in phrases


class TestRerankedDoc:
    """RerankedDoc 测试"""

    def test_create_reranked_doc(self):
        """测试创建重排序文档"""
        doc = RerankedDoc(
            doc="Test document",
            score=0.95,
            rank=1,
            original_rank=5
        )

        assert doc.doc == "Test document"
        assert doc.score == 0.95
        assert doc.rank == 1
        assert doc.original_rank == 5

    def test_reranked_doc_with_metadata(self):
        """测试带元数据的重排序文档"""
        doc = RerankedDoc(
            doc="Test",
            score=0.8,
            rank=2,
            metadata={"method": "cross_encoder"}
        )

        assert doc.metadata["method"] == "cross_encoder"


class TestHybridReranker:
    """HybridReranker 测试"""

    def setup_method(self):
        with patch('src.agents_v2.retrieval.cross_encoder_reranker.logger'):
            self.hybrid = HybridReranker()

    def test_hybrid_initialization(self):
        """测试混合重排序器初始化"""
        assert self.hybrid.vector_weight == 0.4
        assert self.hybrid.cross_encoder_weight == 0.4
        assert self.hybrid.bm25_weight == 0.2

    def test_custom_weights(self):
        """测试自定义权重"""
        hybrid = HybridReranker(
            vector_weight=0.3,
            cross_encoder_weight=0.5,
            bm25_weight=0.2
        )

        assert hybrid.vector_weight == 0.3
        assert hybrid.cross_encoder_weight == 0.5

    @pytest.mark.asyncio
    async def test_hybrid_rerank(self):
        """测试混合重排序"""
        candidates = ["AI document", "ML document", "DL document"]
        result = await self.hybrid.rerank("machine learning", candidates, top_k=3)

        assert len(result) == 3
        assert all(isinstance(r, RerankedDoc) for r in result)

    @pytest.mark.asyncio
    async def test_hybrid_with_vector_scores(self):
        """测试带向量分数的混合重排序"""
        candidates = ["doc1", "doc2", "doc3"]
        vector_scores = [0.9, 0.7, 0.5]
        result = await self.hybrid.rerank(
            "query",
            candidates,
            vector_scores=vector_scores,
            top_k=3
        )

        assert len(result) == 3

    def test_normalize_scores(self):
        """测试分数归一化"""
        scores = [0.1, 0.5, 0.9]
        normalized = self.hybrid._normalize_scores(scores)

        assert min(normalized) >= 0.0
        assert max(normalized) <= 1.0
        assert len(normalized) == 3

    def test_normalize_scores_same_values(self):
        """测试相同分数的归一化"""
        scores = [0.5, 0.5, 0.5]
        normalized = self.hybrid._normalize_scores(scores)

        assert all(s == 0.5 for s in normalized)

    def test_normalize_empty_scores(self):
        """测试空分数列表"""
        normalized = self.hybrid._normalize_scores([])
        assert normalized == []


class TestRerankingEdgeCases:
    """重排序边界情况测试"""

    def setup_method(self):
        with patch('src.agents_v2.retrieval.cross_encoder_reranker.logger'):
            self.reranker = CrossEncoderReranker()

    @pytest.mark.asyncio
    async def test_rerank_single_candidate(self):
        """测试单个候选"""
        result = await self.reranker.rerank("query", ["single doc"], top_k=1)

        assert len(result) == 1
        assert result[0].rank == 1

    @pytest.mark.asyncio
    async def test_rerank_all_same_docs(self):
        """测试完全相同的文档"""
        candidates = ["same", "same", "same"]
        result = await self.reranker.rerank("test", candidates, top_k=3)

        assert len(result) == 3

    def test_unicode_documents(self):
        """测试Unicode文档"""
        candidates = ["人工智能文档", "机器学习文档"]
        result = self.reranker._rerank_simple("人工智能", candidates, top_k=2)

        assert len(result) == 2


class TestConvenienceFunction:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_rerank_documents_default(self):
        """测试默认重排序"""
        result = await rerank_documents("query", ["doc1", "doc2"], top_k=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_rerank_documents_simple(self):
        """测试简单重排序"""
        result = await rerank_documents(
            "machine learning",
            ["doc1", "doc2", "doc3"],
            method="simple",
            top_k=3
        )
        assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])