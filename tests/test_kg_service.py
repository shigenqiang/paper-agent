"""
知识图谱统一服务API测试
"""
import pytest
from src.agents_v2.knowledge_graph import kg_service


class TestServiceConfig:
    """ServiceConfig类测试"""

    def test_creation(self):
        """测试创建"""
        config = kg_service.ServiceConfig(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="test_user",
            neo4j_password="test_pass"
        )
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.neo4j_user == "test_user"
        assert config.neo4j_password == "test_pass"

    def test_default_values(self):
        """测试默认值"""
        config = kg_service.ServiceConfig()
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.embedding_dim == 384
        assert config.vector_store_type == "memory"
        assert config.enable_graphrag is True


class TestKnowledgeGraphServiceInit:
    """KnowledgeGraphService初始化测试"""

    def test_creation(self):
        """测试创建"""
        service = kg_service.KnowledgeGraphService()
        assert service._initialized is False
        assert service.config is not None

    def test_custom_config(self):
        """测试自定义配置"""
        config = kg_service.ServiceConfig(
            vector_store_type="qdrant",
            enable_graphrag=False
        )
        service = kg_service.KnowledgeGraphService(config)
        assert service.config.vector_store_type == "qdrant"
        assert service.config.enable_graphrag is False


class TestKnowledgeGraphServiceMethods:
    """KnowledgeGraphService方法测试"""

    def setup_method(self):
        self.service = kg_service.KnowledgeGraphService()

    def test_add_entity(self):
        """测试添加实体"""
        result = self.service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={"title": "Test Paper"},
            embedding=[0.1] * 384
        )

        assert result is True

    def test_add_relation(self):
        """测试添加关系"""
        # 先添加实体
        self.service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={"title": "Paper 1"},
            embedding=[0.1] * 384
        )
        self.service.add_entity(
            entity_id="author_1",
            entity_type="Author",
            properties={"name": "John"},
            embedding=[0.2] * 384
        )

        result = self.service.add_relation(
            source_id="paper_1",
            target_id="author_1",
            relation_type="AUTHORED_BY"
        )

        assert result is True

    def test_delete_entity(self):
        """测试删除实体"""
        self.service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={},
            embedding=[0.1] * 384
        )

        result = self.service.delete_entity("paper_1")
        assert result is True

    def test_delete_entity_not_found(self):
        """测试删除不存在的实体"""
        result = self.service.delete_entity("nonexistent")
        assert result is True  # 不应报错

    def test_search(self):
        """测试检索"""
        self.service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={"title": "Deep Learning"},
            embedding=[0.1] * 384
        )
        self.service.add_entity(
            entity_id="paper_2",
            entity_type="Paper",
            properties={"title": "Machine Learning"},
            embedding=[0.2] * 384
        )

        results = self.service.search(
            query_embedding=[0.1] * 384,
            top_k=10
        )

        assert isinstance(results, list)

    def test_search_with_filter(self):
        """测试带过滤的检索"""
        self.service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={},
            embedding=[0.1] * 384
        )
        self.service.add_entity(
            entity_id="author_1",
            entity_type="Author",
            properties={},
            embedding=[0.2] * 384
        )

        results = self.service.search(
            query_embedding=[0.1] * 384,
            top_k=10,
            entity_type="Paper"
        )

        assert all(r["payload"].get("type") == "Paper" for r in results)

    def test_retrieve(self):
        """测试混合检索"""
        self.service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={},
            embedding=[0.1] * 384
        )

        results = self.service.retrieve(
            query_embedding=[0.1] * 384,
            top_k=5
        )

        assert isinstance(results, list)

    def test_detect_communities(self):
        """测试社区检测"""
        # 添加一些实体和关系
        self.service.add_entity("p1", "Paper", {}, [0.1] * 384)
        self.service.add_entity("p2", "Paper", {}, [0.2] * 384)
        self.service.add_entity("p3", "Paper", {}, [0.3] * 384)
        self.service.add_relation("p1", "p2", "CITES")
        self.service.add_relation("p2", "p3", "CITES")

        communities = self.service.detect_communities(algorithm="louvain")
        assert isinstance(communities, list)

    def test_query_without_graphrag(self):
        """测试禁用GraphRAG时的查询"""
        service = kg_service.KnowledgeGraphService(
            kg_service.ServiceConfig(enable_graphrag=False)
        )

        result = service.query("What is deep learning?")
        assert "error" in result

    def test_batch_import(self):
        """测试批量导入"""
        entities = [
            ("p1", "Paper", {"title": "Paper 1"}),
            ("p2", "Paper", {"title": "Paper 2"})
        ]
        relations = [
            ("p1", "p2", "CITES", {})
        ]

        result = self.service.batch_import(entities, relations)
        assert result["success"] is True

    def test_get_stats(self):
        """测试获取统计"""
        self.service.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            properties={},
            embedding=[0.1] * 384
        )

        stats = self.service.get_stats()
        assert "initialized" in stats
        assert stats["initialized"] is False  # 尚未调用initialize


class TestBatchKnowledgeGraphService:
    """BatchKnowledgeGraphService测试"""

    def test_creation(self):
        """测试创建"""
        batch_service = kg_service.BatchKnowledgeGraphService()
        assert batch_service._main_service is None

    def test_process_batch_empty(self):
        """测试处理空批次"""
        batch_service = kg_service.BatchKnowledgeGraphService()
        result = batch_service.process_batch([])
        assert result.get("success") == 0 or "error" in result

    def test_process_batch_not_initialized(self):
        """测试未初始化时的处理"""
        batch_service = kg_service.BatchKnowledgeGraphService()
        result = batch_service.process_batch([
            {"type": "entity", "entity_id": "p1", "entity_type": "Paper"}
        ])
        assert "error" in result


class TestCreateService:
    """工厂函数测试"""

    def test_create_service(self):
        """测试创建服务"""
        service = kg_service.create_service()
        assert isinstance(service, kg_service.KnowledgeGraphService)

    def test_create_batch_service(self):
        """测试创建批量服务"""
        batch_service = kg_service.create_batch_service()
        assert isinstance(batch_service, kg_service.BatchKnowledgeGraphService)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
