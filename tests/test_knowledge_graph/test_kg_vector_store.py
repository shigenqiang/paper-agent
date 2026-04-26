"""
知识图谱向量存储测试
"""
import pytest
import math
from dataclasses import dataclass
from src.agents_v2.knowledge_graph import kg_vector_store


class TestVectorSearchResult:
    """VectorSearchResult类测试"""

    def test_creation(self):
        """测试创建"""
        result = kg_vector_store.VectorSearchResult(
            id="test_1",
            score=0.95,
            payload={"title": "Test Paper"}
        )
        assert result.id == "test_1"
        assert result.score == 0.95
        assert result.payload["title"] == "Test Paper"

    def test_default_payload(self):
        """测试默认payload"""
        result = kg_vector_store.VectorSearchResult(
            id="test_1",
            score=0.5
        )
        assert result.payload == {}


class TestInMemoryVectorStore:
    """InMemoryVectorStore类测试"""

    def test_creation(self):
        """测试创建"""
        store = kg_vector_store.InMemoryVectorStore(dimension=768)
        assert store.dimension == 768
        assert store.count() == 0

    def test_default_dimension(self):
        """测试默认维度"""
        store = kg_vector_store.InMemoryVectorStore()
        assert store.dimension == 768

    def test_upsert_and_count(self):
        """测试插入和计数"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [0.1, 0.2, 0.3])
        assert store.count() == 1

        store.upsert("e2", [0.4, 0.5, 0.6])
        assert store.count() == 2

    def test_upsert_update(self):
        """测试更新"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [0.1, 0.2, 0.3], {"title": "V1"})
        store.upsert("e1", [0.1, 0.2, 0.3], {"title": "V2"})

        assert store.count() == 1
        results = store.search([0.1, 0.2, 0.3])
        assert len(results) == 1
        assert results[0].payload["title"] == "V2"

    def test_upsert_dimension_mismatch(self):
        """测试维度不匹配"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        with pytest.raises(ValueError, match="dimension"):
            store.upsert("e1", [0.1, 0.2])  # 2维

    def test_search_empty(self):
        """测试空搜索"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        results = store.search([0.1, 0.2, 0.3])
        assert results == []

    def test_search_basic(self):
        """测试基本搜索"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [1.0, 0.0, 0.0])
        store.upsert("e2", [0.0, 1.0, 0.0])
        store.upsert("e3", [0.0, 0.0, 1.0])

        results = store.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].id == "e1"  # 完全匹配
        assert results[0].score == pytest.approx(1.0)

    def test_search_with_filter(self):
        """测试过滤搜索"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [1.0, 0.0, 0.0], {"type": "paper", "year": 2024})
        store.upsert("e2", [0.0, 1.0, 0.0], {"type": "author", "year": 2023})
        store.upsert("e3", [0.0, 0.0, 1.0], {"type": "paper", "year": 2023})

        results = store.search(
            [1.0, 0.0, 0.0],
            top_k=10,
            filter_payload={"type": "paper"}
        )
        assert len(results) == 2
        assert all(r.payload["type"] == "paper" for r in results)

    def test_search_filter_list(self):
        """测试列表过滤"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [1.0, 0.0, 0.0], {"type": "paper", "year": 2024})
        store.upsert("e2", [0.0, 1.0, 0.0], {"type": "paper", "year": 2023})
        store.upsert("e3", [0.0, 0.0, 1.0], {"type": "author", "year": 2022})

        results = store.search(
            [1.0, 0.0, 0.0],
            top_k=10,
            filter_payload={"year": [2023, 2024]}
        )
        assert len(results) == 2

    def test_delete(self):
        """测试删除"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [1.0, 0.0, 0.0])
        store.upsert("e2", [0.0, 1.0, 0.0])

        assert store.delete("e1") is True
        assert store.count() == 1

        assert store.delete("nonexistent") is False
        assert store.count() == 1

    def test_delete_cascade_payload(self):
        """测试删除时payload也删除"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [1.0, 0.0, 0.0], {"title": "Test"})

        store.delete("e1")
        results = store.search([1.0, 0.0, 0.0])
        assert len(results) == 0

    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)

        # 相同向量
        sim = store._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert sim == pytest.approx(1.0)

        # 正交向量
        sim = store._cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        assert sim == pytest.approx(0.0)

        # 相反向量
        sim = store._cosine_similarity([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0])
        assert sim == pytest.approx(-1.0)

        # 零向量
        sim = store._cosine_similarity([0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert sim == pytest.approx(0.0)

    def test_matches_filter(self):
        """测试过滤器匹配"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)

        # 精确匹配
        assert store._matches_filter(
            {"type": "paper", "year": 2024},
            {"type": "paper"}
        ) is True

        # 不匹配
        assert store._matches_filter(
            {"type": "paper", "year": 2024},
            {"type": "author"}
        ) is False

        # 列表匹配
        assert store._matches_filter(
            {"year": 2024},
            {"year": [2023, 2024]}
        ) is True

        assert store._matches_filter(
            {"year": 2022},
            {"year": [2023, 2024]}
        ) is False

        # 缺失键
        assert store._matches_filter(
            {"type": "paper"},
            {"year": 2024}
        ) is False


class TestQdrantVectorStore:
    """QdrantVectorStore类测试"""

    def test_creation(self):
        """测试创建"""
        store = kg_vector_store.QdrantVectorStore(
            url="localhost:6333",
            collection_name="test_papers",
            dimension=768
        )
        assert store.url == "localhost:6333"
        assert store.collection_name == "test_papers"
        assert store.dimension == 768
        assert store.api_key is None
        assert store._initialized is False

    def test_default_values(self):
        """测试默认值"""
        store = kg_vector_store.QdrantVectorStore()
        assert store.url == "localhost:6333"
        assert store.collection_name == "default"
        assert store.dimension == 768
        assert store.api_key is None

    def test_get_client_not_installed(self):
        """测试客户端未安装"""
        store = kg_vector_store.QdrantVectorStore()

        # 模拟导入失败
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "qdrant_client":
                raise ImportError("No module named 'qdrant_client'")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            store._client = None
            with pytest.raises(ImportError, match="qdrant-client"):
                store._get_client()
        finally:
            builtins.__import__ = original_import


class TestEmbeddingModel:
    """EmbeddingModel类测试"""

    def test_creation(self):
        """测试创建"""
        model = kg_vector_store.EmbeddingModel(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu"
        )
        assert model.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert model.device == "cpu"
        assert model._model is None

    def test_default_values(self):
        """测试默认值"""
        model = kg_vector_store.EmbeddingModel()
        assert model.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert model.device == "cpu"

    def test_encode_query(self):
        """测试encode_query方法存在"""
        model = kg_vector_store.EmbeddingModel()
        assert hasattr(model, 'encode_query')
        assert callable(model.encode_query)


class TestCreateVectorStore:
    """create_vector_store工厂函数测试"""

    def test_create_memory_store(self):
        """测试创建内存存储"""
        store = kg_vector_store.create_vector_store("memory", dimension=256)
        assert isinstance(store, kg_vector_store.InMemoryVectorStore)
        assert store.dimension == 256

    def test_create_qdrant_store(self):
        """测试创建Qdrant存储"""
        store = kg_vector_store.create_vector_store(
            "qdrant",
            url="localhost:6333",
            collection_name="test",
            dimension=768
        )
        assert isinstance(store, kg_vector_store.QdrantVectorStore)
        assert store.url == "localhost:6333"

    def test_unknown_store_type(self):
        """测试未知存储类型"""
        with pytest.raises(ValueError, match="Unknown store type"):
            kg_vector_store.create_vector_store("unknown")


class TestVectorSearchResultDataclass:
    """VectorSearchResult数据类字段测试"""

    def test_fields(self):
        """测试所有字段"""
        result = kg_vector_store.VectorSearchResult(
            id="entity_1",
            score=0.878,
            payload={"paper_title": "Deep Learning", "citation_count": 100}
        )
        assert result.id == "entity_1"
        assert result.score == 0.878
        assert result.payload["paper_title"] == "Deep Learning"
        assert result.payload["citation_count"] == 100


class TestCosineSimilarityEdgeCases:
    """余弦相似度边界情况测试"""

    def setup_method(self):
        self.store = kg_vector_store.InMemoryVectorStore(dimension=5)

    def test_zero_vector(self):
        """测试零向量"""
        sim = self.store._cosine_similarity([0.0, 0.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0, 0.0])
        assert sim == 0.0

    def test_both_zero_vectors(self):
        """测试两个零向量"""
        sim = self.store._cosine_similarity([0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0, 0.0])
        assert sim == 0.0

    def test_negative_values(self):
        """测试负值向量"""
        v1 = [0.5, -0.5, 0.3, -0.3, 0.1]
        v2 = [-0.5, 0.5, -0.3, 0.3, -0.1]
        sim = self.store._cosine_similarity(v1, v2)
        assert sim == pytest.approx(-1.0)

    def test_high_dimensional(self):
        """测试高维向量"""
        dimension = 1536
        store = kg_vector_store.InMemoryVectorStore(dimension=dimension)
        v1 = [0.1] * dimension
        v2 = [0.1] * dimension
        sim = store._cosine_similarity(v1, v2)
        assert sim == pytest.approx(1.0)


class TestInMemoryStoreTopK:
    """top_k限制测试"""

    def test_top_k_less_than_results(self):
        """测试top_k小于结果数"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        for i in range(10):
            store.upsert(f"e{i}", [float(i), 0.0, 0.0])

        results = store.search([10.0, 0.0, 0.0], top_k=3)
        assert len(results) == 3

    def test_top_k_greater_than_results(self):
        """测试top_k大于结果数"""
        store = kg_vector_store.InMemoryVectorStore(dimension=3)
        store.upsert("e1", [1.0, 0.0, 0.0])
        store.upsert("e2", [0.0, 1.0, 0.0])

        results = store.search([1.0, 0.0, 0.0], top_k=100)
        assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
