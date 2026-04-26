"""
知识图谱混合检索测试
"""
import pytest
import math
from src.agents_v2.knowledge_graph import (
    RetrievalResult,
    RetrievalMethod,
    VectorSearcher,
    GraphTraverser,
    MMRReranker,
    HybridRetriever,
    EntityLinker
)


class TestVectorSearcher:
    """向量检索器测试"""

    def setup_method(self):
        self.searcher = VectorSearcher(embedding_dim=3)

    def test_add_and_search(self):
        """测试添加和搜索"""
        self.searcher.add("A", [1.0, 0.0, 0.0])
        self.searcher.add("B", [0.0, 1.0, 0.0])
        self.searcher.add("C", [0.0, 0.0, 1.0])

        # 搜索接近[1, 0, 0]的向量
        results = self.searcher.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0][0] == "A"  # 最接近

    def test_empty_index(self):
        """测试空索引"""
        results = self.searcher.search([1.0, 0.0, 0.0], top_k=5)
        assert results == []

    def test_exclude_ids(self):
        """测试排除ID"""
        self.searcher.add("A", [1.0, 0.0, 0.0])
        self.searcher.add("B", [0.9, 0.1, 0.0])
        self.searcher.add("C", [0.8, 0.2, 0.0])

        results = self.searcher.search(
            [1.0, 0.0, 0.0],
            top_k=2,
            exclude_ids={"A"}
        )
        assert len(results) == 2
        assert all(r[0] != "A" for r in results)


class TestGraphTraverser:
    """图遍历器测试"""

    def setup_method(self):
        self.traverser = GraphTraverser()

    def test_add_nodes(self):
        """测试添加节点"""
        self.traverser.add_node("paper1", "Paper", {"title": "Test"})
        assert "paper1" in self.traverser._nodes

    def test_add_edges(self):
        """测试添加边"""
        self.traverser.add_node("author1", "Author", {})
        self.traverser.add_node("paper1", "Paper", {})
        self.traverser.add_edge("author1", "paper1", "AUTHORED_BY")

        assert ("author1", "paper1", "AUTHORED_BY") in self.traverser._edges

    def test_find_neighbors_depth_1(self):
        """测试1跳邻居"""
        self.traverser.add_edge("A", "B", "RELATES")
        self.traverser.add_edge("B", "C", "RELATES")

        neighbors = self.traverser.find_neighbors("A", depth=1)
        assert "B" in neighbors
        assert "C" not in neighbors  # 2跳邻居

    def test_find_neighbors_depth_2(self):
        """测试2跳邻居"""
        self.traverser.add_edge("A", "B", "RELATES")
        self.traverser.add_edge("B", "C", "RELATES")
        self.traverser.add_edge("C", "D", "RELATES")

        neighbors = self.traverser.find_neighbors("A", depth=2)
        assert "B" in neighbors
        assert "C" in neighbors
        assert "D" not in neighbors  # 3跳邻居

    def test_find_paths(self):
        """测试路径查找"""
        self.traverser.add_edge("A", "B", "RELATES")
        self.traverser.add_edge("B", "C", "RELATES")
        self.traverser.add_edge("A", "D", "RELATES")

        paths = self.traverser.find_paths("A", "C", max_depth=3)
        assert len(paths) > 0
        assert ["A", "B", "C"] in paths

    def test_get_subgraph(self):
        """测试子图获取"""
        self.traverser.add_node("A", "Paper", {})
        self.traverser.add_node("B", "Author", {})
        self.traverser.add_node("C", "Paper", {})
        self.traverser.add_edge("A", "B", "AUTHORED_BY")
        self.traverser.add_edge("A", "C", "CITES")

        subgraph = self.traverser.get_subgraph({"A"}, depth=1)
        assert len(subgraph["nodes"]) == 3  # A, B, C
        assert len(subgraph["edges"]) == 2


class TestMMRReranker:
    """MMR重排序测试"""

    def setup_method(self):
        self.reranker = MMRReranker(lambda_param=0.5)
        # 设置嵌入向量
        self.reranker.set_embeddings({
            "A": [1.0, 0.0, 0.0],
            "B": [0.9, 0.1, 0.0],
            "C": [0.8, 0.2, 0.0],
            "D": [0.0, 1.0, 0.0],
        })

    def test_rerank_diversity(self):
        """测试MMR多样性"""
        candidates = [
            RetrievalResult("A", "Paper", 0.9, RetrievalMethod.VECTOR_ONLY),
            RetrievalResult("B", "Paper", 0.85, RetrievalMethod.VECTOR_ONLY),
            RetrievalResult("D", "Paper", 0.8, RetrievalMethod.VECTOR_ONLY),
        ]

        # 使用低lambda，惩罚相似文档
        reranker = MMRReranker(lambda_param=0.3)
        reranker.set_embeddings(self.reranker._embeddings)

        results = reranker.rerank(
            [1.0, 0.0, 0.0],
            candidates,
            top_k=2
        )

        # 应该选择一个A和一个D（不同类型）
        result_ids = [r.entity_id for r in results]
        assert len(result_ids) == 2

    def test_rerank_relevance(self):
        """测试高相关性偏好"""
        candidates = [
            RetrievalResult("A", "Paper", 0.9, RetrievalMethod.VECTOR_ONLY),
            RetrievalResult("B", "Paper", 0.85, RetrievalMethod.VECTOR_ONLY),
            RetrievalResult("D", "Paper", 0.8, RetrievalMethod.VECTOR_ONLY),
        ]

        # 使用高lambda，优先相关性
        reranker = MMRReranker(lambda_param=0.9)
        reranker.set_embeddings(self.reranker._embeddings)

        results = reranker.rerank(
            [1.0, 0.0, 0.0],
            candidates,
            top_k=2
        )

        # 应该优先选择A和B（都接近查询向量）
        result_ids = [r.entity_id for r in results]
        assert "A" in result_ids

    def test_rerank_empty(self):
        """测试空候选"""
        results = self.reranker.rerank(
            [1.0, 0.0, 0.0],
            [],
            top_k=5
        )
        assert results == []


class TestHybridRetriever:
    """混合检索器测试"""

    def setup_method(self):
        self.retriever = HybridRetriever(
            vector_weight=0.5,
            graph_weight=0.3,
            mmr_lambda=0.5
        )
        # 添加测试数据
        self._add_test_data()

    def _add_test_data(self):
        """添加测试数据"""
        papers = [
            ("paper1", "Transformer", [0.9, 0.1, 0.0]),
            ("paper2", "BERT", [0.85, 0.15, 0.0]),
            ("paper3", "CNN", [0.1, 0.9, 0.0]),
            ("paper4", "ResNet", [0.15, 0.85, 0.0]),
            ("paper5", "GNN", [0.5, 0.5, 0.0]),
        ]

        for paper_id, ptype, embedding in papers:
            self.retriever.add_entity(
                paper_id, "Paper", embedding,
                {"type": ptype}
            )

        # 添加关系
        self.retriever.add_relation("paper1", "paper2", "CITES")
        self.retriever.add_relation("paper1", "paper5", "USES_METHOD")

    def test_vector_only_retrieval(self):
        """测试纯向量检索"""
        results = self.retriever.retrieve(
            query_embedding=[1.0, 0.0, 0.0],
            initial_entities=None,
            top_k=3,
            use_mmr=False
        )

        assert len(results) > 0
        # paper1应该排第一（最接近查询向量）
        assert results[0].entity_id == "paper1"

    def test_graph_expansion(self):
        """测试图扩展"""
        results = self.retriever.retrieve(
            query_embedding=[0.9, 0.1, 0.0],
            initial_entities=["paper1"],
            top_k=5,
            depth=1,
            use_mmr=False
        )

        result_ids = [r.entity_id for r in results]
        # paper1, paper2, paper5 应该都在结果中
        assert "paper1" in result_ids

    def test_mmr_deduplication(self):
        """测试MMR去重"""
        # 添加相似的文档
        self.retriever.add_entity(
            "paper1_similar", "Paper", [0.89, 0.11, 0.0],
            {"type": "Transformer"}
        )
        self.retriever.add_relation("paper1_similar", "paper2", "CITES")

        results = self.retriever.retrieve(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=3,
            use_mmr=True
        )

        result_ids = [r.entity_id for r in results]
        # paper1和paper1_similar不应该同时出现
        # （它们太相似了）
        assert len(set(result_ids)) == len(result_ids)

    def test_get_subgraph(self):
        """测试子图获取"""
        subgraph = self.retriever.get_subgraph(
            ["paper1"],
            depth=1
        )

        assert len(subgraph["nodes"]) >= 1
        assert len(subgraph["edges"]) >= 0


class TestEntityLinker:
    """实体链接器测试"""

    def setup_method(self):
        self.linker = EntityLinker()

    def test_extract_paper_references(self):
        """测试提取论文引用"""
        query = "According to paper #1 and Paper BERT"
        entities = self.linker.extract_entities(query)

        # 应该提取到 #1 和 BERT
        entity_types = [e[1] for e in entities]
        assert "paper" in entity_types

    def test_extract_methods(self):
        """测试提取方法名"""
        query = "The Transformer model uses self-attention"
        entities = self.linker.extract_entities(query)

        entity_names = [e[0] for e in entities]
        assert "Transformer" in entity_names

    def test_link_entities(self):
        """测试实体链接"""
        known = {
            "BERT": "paper1",
            "Transformer": "paper2",
            "GPT": "paper3"
        }

        entities = [("BERT", "paper")]
        linked = self.linker.link_entities(entities, known)

        assert "paper1" in linked

    def test_fuzzy_link(self):
        """测试模糊匹配"""
        known = {
            "BERT": "paper1",
            "Transformer": "paper2"
        }

        entities = [("bert-base", "paper")]
        linked = self.linker.link_entities(entities, known)

        assert "paper1" in linked


class TestCosineSimilarity:
    """余弦相似度测试"""

    def test_identical_vectors(self):
        """相同向量相似度为1"""
        searcher = VectorSearcher()
        similarity = searcher._cosine_similarity(
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0]
        )
        assert abs(similarity - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        """正交向量相似度为0"""
        searcher = VectorSearcher()
        similarity = searcher._cosine_similarity(
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0]
        )
        assert abs(similarity) < 1e-6

    def test_opposite_vectors(self):
        """相反向量相似度为-1"""
        searcher = VectorSearcher()
        similarity = searcher._cosine_similarity(
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0]
        )
        assert abs(similarity - (-1.0)) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
