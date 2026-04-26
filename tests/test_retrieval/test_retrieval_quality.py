"""
检索质量评估测试

测试混合检索、BM25、向量搜索质量
"""
import pytest
import asyncio
import time
from src.agents_v2.memory.retrieval import (
    RetrievalResult,
    RetrievalQuery,
    QueryType,
    BM25
)


class TestBM25:
    """测试BM25索引器"""

    def test_bm25_indexer_init(self):
        """测试BM25索引器初始化"""
        indexer = BM25()
        assert indexer is not None

    def test_bm25_indexing(self):
        """测试BM25索引"""
        indexer = BM25()

        doc_ids = ["doc1", "doc2", "doc3"]
        texts = [
            "深度学习在医学影像诊断中的应用",
            "自然语言处理技术在客服系统中的使用",
            "强化学习算法研究进展"
        ]

        for doc_id, text in zip(doc_ids, texts):
            indexer.index(doc_id, text)

        assert indexer.doc_count == 3

    def test_bm25_search(self):
        """测试BM25搜索"""
        indexer = BM25()

        doc_ids = ["doc1", "doc2", "doc3"]
        texts = [
            "深度学习在医学影像诊断中的应用",
            "自然语言处理技术在客服系统中的使用",
            "强化学习算法研究进展"
        ]

        for doc_id, text in zip(doc_ids, texts):
            indexer.index(doc_id, text)

        results = indexer.search("深度学习 医学", doc_ids=["doc1", "doc2", "doc3"], limit=2)

        assert isinstance(results, list)

    def test_bm25_empty_query(self):
        """测试空查询"""
        indexer = BM25()
        indexer.index("doc1", "文档内容")

        results = indexer.search("", doc_ids=["doc1"], limit=2)
        assert len(results) == 0

    def test_bm25_limit_results(self):
        """测试结果数量限制"""
        indexer = BM25()

        for i in range(20):
            indexer.index(f"doc{i}", f"文档{i}")

        results = indexer.search("文档", doc_ids=[f"doc{i}" for i in range(20)], limit=5)
        assert len(results) <= 5

    def test_bm25_empty_index(self):
        """测试空索引搜索"""
        indexer = BM25()
        results = indexer.search("查询", doc_ids=[], limit=5)
        assert len(results) == 0

    def test_bm25_scores_sorted(self):
        """测试结果按分数排序"""
        indexer = BM25()

        indexer.index("doc1", "深度学习深度学习深度学习")
        indexer.index("doc2", "深度学习")
        indexer.index("doc3", "机器学习")

        results = indexer.search("深度学习", doc_ids=["doc1", "doc2", "doc3"], limit=3)

        if len(results) >= 2:
            scores = [r[1] for r in results]
            assert scores == sorted(scores, reverse=True)


class TestRetrievalQueryType:
    """测试查询类型"""

    def test_query_type_values(self):
        """测试查询类型枚举值"""
        assert QueryType.FACTUAL == "factual"
        assert QueryType.PROCEDURAL == "procedural"
        assert QueryType.EXPLANATORY == "explanatory"
        assert QueryType.TEMPORAL == "temporal"
        assert QueryType.ENTITY == "entity"


class TestRetrievalPerformance:
    """检索性能测试"""

    def test_indexing_throughput(self):
        """测试索引吞吐量"""
        indexer = BM25()

        start = time.time()
        for i in range(1000):
            indexer.index(f"doc{i}", f"文档{i}内容")
        elapsed = time.time() - start

        docs_per_second = 1000 / elapsed
        assert docs_per_second > 100  # 每秒应处理100+文档

    def test_search_latency(self):
        """测试搜索延迟"""
        indexer = BM25()

        for i in range(100):
            indexer.index(f"doc{i}", f"文档{i}内容")

        start = time.time()
        for _ in range(100):
            indexer.search("文档", doc_ids=[f"doc{i}" for i in range(100)], limit=10)
        elapsed = time.time() - start

        avg_latency = elapsed / 100 * 1000  # ms
        assert avg_latency < 10  # 平均每次搜索少于10ms

    def test_large_scale_indexing(self):
        """测试大规模索引"""
        indexer = BM25()

        start = time.time()
        for i in range(10000):
            indexer.index(f"doc{i}", f"文档{i}内容包含一些中文字符")
        elapsed = time.time() - start

        docs_per_second = 10000 / elapsed
        assert docs_per_second > 1000  # 每秒应处理1000+文档


class TestRetrievalEdgeCases:
    """检索边界情况测试"""

    def test_very_short_query(self):
        """测试超短查询"""
        indexer = BM25()
        indexer.index("doc1", "深度学习内容")

        results = indexer.search("深", doc_ids=["doc1"], limit=5)
        assert isinstance(results, list)

    def test_very_long_query(self):
        """测试超长查询"""
        indexer = BM25()
        indexer.index("doc1", "深度学习")

        long_query = "深度学习 " * 1000
        results = indexer.search(long_query, doc_ids=["doc1"], limit=5)
        assert isinstance(results, list)

    def test_chinese_tokenization(self):
        """测试中文分词"""
        indexer = BM25()

        indexer.index("doc1", "深度学习在计算机视觉中的应用")
        indexer.index("doc2", "自然语言处理技术")

        results = indexer.search("深度学习", doc_ids=["doc1", "doc2"], limit=2)

        # doc1应该比doc2更相关
        if len(results) >= 2:
            assert results[0][0] == "doc1"

    def test_mixed_language(self):
        """测试中英文混合"""
        indexer = BM25()

        indexer.index("doc1", "Deep Learning在图像识别中的应用")
        indexer.index("doc2", "Natural Language Processing技术")

        results = indexer.search("Deep Learning", doc_ids=["doc1", "doc2"], limit=2)

        assert len(results) >= 1
