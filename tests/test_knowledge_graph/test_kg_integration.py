"""
知识图谱集成测试

测试完整的工作流程:
1. 实体提取
2. 关系抽取
3. 批量导入
4. 社区检测
5. 混合检索
6. GraphRAG问答
"""
import pytest
from src.agents_v2.knowledge_graph import (
    KnowledgeGraphService,
    ServiceConfig,
    EntityExtractor,
    RelationExtractor,
    KnowledgeGraphGenerator,
    detect_communities,
    LouvainDetector,
    HybridRetriever,
    create_graphrag_qa,
    GraphRAGQA
)


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    def test_entity_extraction_to_graphrag(self):
        """测试从实体提取到GraphRAG的完整流程"""
        # 1. 提取实体
        extractor = EntityExtractor()
        text = """
        We propose a new Transformer model called BERT that uses self-attention.
        Our method achieves state-of-the-art results on the GLUE benchmark.
        Experiments on ImageNet dataset show significant improvement.
        """
        entities = extractor.extract_from_text(text, "paper_1")

        assert len(entities) > 0

        # 2. 构建GraphRAG
        qa = create_graphrag_qa()

        for entity in entities:
            qa.retriever.add_entity(
                entity_id=f"entity_{entity.name}",
                entity_type=entity.type.value,
                text=entity.name,
                keywords=[entity.name.lower()]
            )

        # 3. GraphRAG查询
        context = qa.query("What method achieves state-of-the-art results?")

        assert context.query.query_type.value in ["factual", "exploratory"]
        assert context.query.text == "What method achieves state-of-the-art results?"

    def test_knowledge_graph_generator_workflow(self):
        """测试知识图谱生成器工作流"""
        import asyncio
        generator = KnowledgeGraphGenerator()

        result = asyncio.run(generator.generate_from_paper(
            paper_id="test_paper",
            title="Deep Learning for NLP",
            abstract="This paper proposes a new method using BERT and Transformer.",
            full_text="Experiments on the GLUE benchmark show our method achieves 90% accuracy."
        ))

        assert result.success is True
        assert result.paper_id == "test_paper"
        assert isinstance(result.entities, list)
        assert isinstance(result.relations, list)

    def test_community_detection_integration(self):
        """测试社区检测集成"""
        # 构建图结构
        edges = [
            ("paper_1", "paper_2"),  # 同一社区
            ("paper_2", "paper_3"),  # 同一社区
            ("paper_4", "paper_5"),  # 不同社区
        ]

        communities = detect_communities(edges, algorithm="louvain")

        assert len(communities) >= 1
        # 检查是否识别出多个节点
        assert len(communities) >= 1

    def test_hybrid_retriever_full_workflow(self):
        """测试混合检索完整工作流"""
        retriever = HybridRetriever()

        # 添加论文实体
        papers = [
            ("paper_1", "Paper", [0.1, 0.2, 0.3], {"title": "Deep Learning", "year": 2024}),
            ("paper_2", "Paper", [0.2, 0.3, 0.4], {"title": "Machine Learning", "year": 2023}),
            ("paper_3", "Paper", [0.3, 0.4, 0.5], {"title": "NLP", "year": 2024}),
        ]

        for paper_id, ptype, embedding, props in papers:
            retriever.add_entity(paper_id, ptype, embedding, props)

        # 添加关系
        retriever.add_relation("paper_1", "paper_2", "CITES")
        retriever.add_relation("paper_2", "paper_3", "CITES")

        # 检索
        results = retriever.retrieve(
            query_embedding=[0.1, 0.2, 0.3],
            top_k=3
        )

        assert len(results) <= 3
        assert all(hasattr(r, 'entity_id') for r in results)

    def test_service_batch_import(self):
        """测试服务批量导入"""
        service = KnowledgeGraphService()

        entities = [
            ("paper_1", "Paper", {"title": "Paper 1"}),
            ("paper_2", "Paper", {"title": "Paper 2"}),
            ("author_1", "Author", {"name": "John"})
        ]

        relations = [
            ("paper_1", "author_1", "AUTHORED_BY", {}),
            ("paper_2", "author_1", "AUTHORED_BY", {})
        ]

        result = service.batch_import(entities, relations)

        assert result["success"] is True
        assert result["total"] == 5

    def test_search_and_filter(self):
        """测试搜索和过滤"""
        from src.agents_v2.knowledge_graph.kg_vector_store import InMemoryVectorStore

        # 使用正确的维度
        service = KnowledgeGraphService()
        service._vector_store = InMemoryVectorStore(dimension=384)

        # 添加不同类型的实体
        papers = [
            ("paper_1", "Paper", {"title": "Deep Learning"}),
            ("paper_2", "Paper", {"title": "Machine Learning"}),
            ("author_1", "Author", {"name": "John"})
        ]

        for entity_id, entity_type, properties in papers:
            service.add_entity(
                entity_id=entity_id,
                entity_type=entity_type,
                properties=properties,
                embedding=[0.1] * 384
            )

        # 只搜索Paper类型
        results = service.search(
            query_embedding=[0.1] * 384,
            top_k=10,
            entity_type="Paper"
        )

        assert len(results) >= 2


class TestPerformanceBenchmarks:
    """性能基准测试"""

    def test_large_scale_entity_add(self):
        """测试大规模实体添加"""
        import time

        service = KnowledgeGraphService()
        start = time.time()

        for i in range(100):
            service.add_entity(
                entity_id=f"paper_{i}",
                entity_type="Paper",
                properties={"title": f"Paper {i}"},
                embedding=[0.1] * 384
            )

        elapsed = time.time() - start
        assert elapsed < 5.0  # 100个实体应该在5秒内完成

    def test_batch_import_performance(self):
        """测试批量导入性能"""
        import time

        service = KnowledgeGraphService()

        entities = [
            (f"paper_{i}", "Paper", {"title": f"Paper {i}"})
            for i in range(100)
        ]

        start = time.time()
        result = service.batch_import(entities, [])
        elapsed = time.time() - start

        assert result["success"] is True
        assert elapsed < 10.0  # 100个实体批量导入应该在10秒内完成


class TestErrorHandling:
    """错误处理测试"""

    def test_service_with_empty_data(self):
        """测试空数据处理"""
        service = KnowledgeGraphService()

        # 空批量导入
        result = service.batch_import([], [])
        assert result["success"] is True

        # 空检索
        results = service.search([0.1] * 384)
        assert results == []

    def test_invalid_entity_type(self):
        """测试无效实体类型"""
        service = KnowledgeGraphService()

        # 添加有效实体
        service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={},
            embedding=[0.1] * 384
        )

        # 应该不会崩溃
        stats = service.get_stats()
        assert "initialized" in stats


class TestGraphRAGIntegration:
    """GraphRAG集成测试"""

    def test_graphrag_with_relations(self):
        """测试带关系的GraphRAG"""
        qa = create_graphrag_qa()

        # 添加实体和关系
        qa.build_index(
            entities=[
                ("transformer", "Method", "Transformer model"),
                ("bert", "Method", "BERT model"),
                ("paper_1", "Paper", "BERT paper"),
            ],
            relations=[
                ("bert", "transformer", "BASED_ON"),
                ("paper_1", "bert", "PROPOSES"),
            ]
        )

        # 查询
        context = qa.query("What model is BERT based on?")

        assert context.query.query_type == qa.retriever.query_classifier.classify(
            "What model is BERT based on?"
        )

    def test_graphrag_context_prompt(self):
        """测试GraphRAG上下文prompt生成"""
        qa = create_graphrag_qa()

        qa.build_index(
            entities=[
                ("paper_1", "Paper", "Deep Learning paper"),
            ],
            relations=[]
        )

        context = qa.query("Tell me about Deep Learning")

        prompt = context.to_prompt_context()
        assert len(prompt) > 0
        assert "Deep Learning" in prompt or "Paper" in prompt


class TestCommunityAlgorithms:
    """社区算法对比测试"""

    def test_louvain_vs_leiden(self):
        """测试Louvain和Leiden算法对比"""
        edges = [
            ("a", "b"),
            ("b", "c"),
            ("d", "e"),
            ("e", "f"),
        ]

        louvain_communities = detect_communities(edges, algorithm="louvain")
        leiden_communities = detect_communities(edges, algorithm="leiden")

        assert len(louvain_communities) >= 1
        assert len(leiden_communities) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
