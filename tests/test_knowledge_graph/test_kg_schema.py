"""
知识图谱数据模型与索引测试
"""
import pytest
from src.agents_v2.knowledge_graph import kg_schema


class TestNodeType:
    """NodeType枚举测试"""

    def test_node_types(self):
        """测试节点类型存在"""
        assert kg_schema.NodeType.PAPER.value == "Paper"
        assert kg_schema.NodeType.AUTHOR.value == "Author"
        assert kg_schema.NodeType.VENUE.value == "Venue"
        assert kg_schema.NodeType.METHOD.value == "Method"
        assert kg_schema.NodeType.DATASET.value == "Dataset"


class TestRelationType:
    """RelationType枚举测试"""

    def test_relation_types(self):
        """测试关系类型存在"""
        assert kg_schema.RelationType.CITES.value == "CITES"
        assert kg_schema.RelationType.AUTHORED_BY.value == "AUTHORED_BY"
        assert kg_schema.RelationType.PUBLISHED_IN.value == "PUBLISHED_IN"
        assert kg_schema.RelationType.USES.value == "USES"


class TestPropertyDefinition:
    """PropertyDefinition类测试"""

    def test_creation(self):
        """测试创建"""
        prop = kg_schema.PropertyDefinition(
            name="title",
            type="string",
            indexed=True,
            required=True
        )
        assert prop.name == "title"
        assert prop.type == "string"
        assert prop.indexed is True
        assert prop.required is True

    def test_default_values(self):
        """测试默认值"""
        prop = kg_schema.PropertyDefinition(name="test", type="string")
        assert prop.indexed is False
        assert prop.unique is False
        assert prop.required is False
        assert prop.default is None


class TestNodeSchema:
    """NodeSchema类测试"""

    def test_creation(self):
        """测试创建"""
        schema = kg_schema.NodeSchema(
            type=kg_schema.NodeType.PAPER,
            labels=["Entity", "Paper"],
            properties=[
                kg_schema.PropertyDefinition("paper_id", "string", indexed=True)
            ]
        )
        assert schema.type == kg_schema.NodeType.PAPER
        assert len(schema.labels) == 2

    def test_get_indexed_properties(self):
        """测试获取索引属性"""
        schema = kg_schema.NodeSchema(
            type=kg_schema.NodeType.PAPER,
            properties=[
                kg_schema.PropertyDefinition("id", "string", indexed=True),
                kg_schema.PropertyDefinition("title", "string", indexed=True),
                kg_schema.PropertyDefinition("abstract", "string"),
            ]
        )
        indexed = schema.get_indexed_properties()
        assert "id" in indexed
        assert "title" in indexed
        assert "abstract" not in indexed

    def test_get_required_properties(self):
        """测试获取必需属性"""
        schema = kg_schema.NodeSchema(
            type=kg_schema.NodeType.PAPER,
            properties=[
                kg_schema.PropertyDefinition("id", "string", required=True),
                kg_schema.PropertyDefinition("title", "string", required=True),
                kg_schema.PropertyDefinition("abstract", "string"),
            ]
        )
        required = schema.get_required_properties()
        assert len(required) == 2
        assert "id" in required
        assert "title" in required


class TestRelationshipSchema:
    """RelationshipSchema类测试"""

    def test_creation(self):
        """测试创建"""
        schema = kg_schema.RelationshipSchema(
            type=kg_schema.RelationType.CITES,
            source_types=[kg_schema.NodeType.PAPER],
            target_types=[kg_schema.NodeType.PAPER],
            properties=[
                kg_schema.PropertyDefinition("context", "string")
            ]
        )
        assert schema.type == kg_schema.RelationType.CITES
        assert kg_schema.NodeType.PAPER in schema.source_types
        assert kg_schema.NodeType.PAPER in schema.target_types


class TestSchemaManager:
    """SchemaManager类测试"""

    def test_creation(self):
        """测试创建"""
        manager = kg_schema.SchemaManager()
        assert len(manager._node_schemas) > 0
        assert len(manager._relation_schemas) > 0

    def test_get_node_schema(self):
        """测试获取节点Schema"""
        manager = kg_schema.SchemaManager()
        schema = manager.get_node_schema(kg_schema.NodeType.PAPER)
        assert schema is not None
        assert schema.type == kg_schema.NodeType.PAPER

    def test_get_relation_schema(self):
        """测试获取关系Schema"""
        manager = kg_schema.SchemaManager()
        schema = manager.get_relation_schema(kg_schema.RelationType.CITES)
        assert schema is not None

    def test_validate_valid_node(self):
        """测试验证有效节点"""
        manager = kg_schema.SchemaManager()
        is_valid, errors = manager.validate_node(
            kg_schema.NodeType.PAPER,
            {"paper_id": "p1", "title": "Test Paper"}
        )
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_required(self):
        """测试验证缺少必需属性"""
        manager = kg_schema.SchemaManager()
        is_valid, errors = manager.validate_node(
            kg_schema.NodeType.PAPER,
            {"title": "Test Paper"}  # 缺少paper_id
        )
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_invalid_type(self):
        """测试验证无效类型"""
        manager = kg_schema.SchemaManager()
        is_valid, errors = manager.validate_node(
            kg_schema.NodeType.PAPER,
            {"paper_id": 123, "title": "Test Paper"}  # paper_id应该是string
        )
        assert is_valid is False

    def test_register_node_schema(self):
        """测试注册节点Schema"""
        manager = kg_schema.SchemaManager()
        new_schema = kg_schema.NodeSchema(
            type=kg_schema.NodeType.TASK,
            properties=[]
        )
        manager.register_node_schema(new_schema)
        assert manager.get_node_schema(kg_schema.NodeType.TASK) is not None

    def test_get_index_recommendations(self):
        """测试获取索引推荐"""
        manager = kg_schema.SchemaManager()
        recs = manager.get_index_recommendations()
        assert "nodes" in recs
        assert len(recs["nodes"]) > 0

    def test_generate_cypher_constraints(self):
        """测试生成约束语句"""
        manager = kg_schema.SchemaManager()
        cypher = manager.generate_cypher_constraints()
        assert len(cypher) > 0
        assert any("CONSTRAINT" in c for c in cypher)

    def test_generate_cypher_indexes(self):
        """测试生成索引语句"""
        manager = kg_schema.SchemaManager()
        cypher = manager.generate_cypher_indexes()
        assert len(cypher) > 0
        assert any("INDEX" in c for c in cypher)


class TestQueryOptimizer:
    """QueryOptimizer类测试"""

    def test_creation(self):
        """测试创建"""
        optimizer = kg_schema.QueryOptimizer()
        assert optimizer.schema_manager is not None

    def test_optimize_match_pattern(self):
        """测试优化MATCH模式"""
        optimizer = kg_schema.QueryOptimizer()

        # 优化建议
        result = optimizer.optimize_match_pattern(
            "MATCH (p:Paper) WHERE p.year > 2020 RETURN p"
        )
        assert "suggestions" in result

    def test_suggest_relation_pattern(self):
        """测试推荐关系模式"""
        optimizer = kg_schema.QueryOptimizer()
        pattern = optimizer.suggest_relation_pattern(
            kg_schema.NodeType.PAPER,
            kg_schema.NodeType.AUTHOR
        )
        assert "Paper" in pattern
        assert "Author" in pattern

    def test_get_hint_for_query_type(self):
        """测试获取查询类型提示"""
        optimizer = kg_schema.QueryOptimizer()
        hints = optimizer.get_hint_for_query_type("neighbor")
        assert len(hints) > 0


class TestIndexManager:
    """IndexManager类测试"""

    def test_creation(self):
        """测试创建"""
        manager = kg_schema.IndexManager()
        assert len(manager._custom_indexes) == 0

    def test_create_composite_index(self):
        """测试创建组合索引"""
        manager = kg_schema.IndexManager()
        cypher = manager.create_composite_index(
            "paper_year_citation",
            "Paper",
            ["year", "citation_count"]
        )
        assert "COMPOSITE" in cypher or "INDEX" in cypher
        assert "year" in cypher

    def test_create_relationship_index(self):
        """测试创建关系索引"""
        manager = kg_schema.IndexManager()
        cypher = manager.create_relationship_index(
            "cites_context",
            "CITES",
            ["context"]
        )
        assert "CITES" in cypher

    def test_suggest_indexes_for_queries(self):
        """测试查询索引推荐"""
        manager = kg_schema.IndexManager()
        queries = [
            "MATCH (p:Paper) WHERE p.year = 2024 RETURN p",
            "MATCH (a:Author) WHERE a.name = 'John' RETURN a"
        ]
        suggestions = manager.suggest_indexes_for_queries(queries)
        assert len(suggestions) > 0


class TestDataModelValidator:
    """DataModelValidator类测试"""

    def test_creation(self):
        """测试创建"""
        validator = kg_schema.DataModelValidator()
        assert validator.schema_manager is not None

    def test_validate_consistency_valid(self):
        """测试验证有效数据"""
        validator = kg_schema.DataModelValidator()
        nodes = [
            ("p1", "Paper", {"paper_id": "p1", "title": "Paper 1"}),
            ("p2", "Paper", {"paper_id": "p2", "title": "Paper 2"})
        ]
        relations = [
            ("p1", "p2", "CITES", {})
        ]

        result = validator.validate_consistency(nodes, relations)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_consistency_missing_node(self):
        """测试验证缺失节点"""
        validator = kg_schema.DataModelValidator()
        nodes = [("p1", "Paper", {"paper_id": "p1", "title": "Paper 1"})]
        relations = [
            ("p1", "p2", "CITES", {})  # p2不存在
        ]

        result = validator.validate_consistency(nodes, relations)
        assert result["valid"] is False
        assert any("p2" in e for e in result["errors"])

    def test_check_orphan_nodes(self):
        """测试检查孤立节点"""
        validator = kg_schema.DataModelValidator()
        nodes = ["p1", "p2", "p3"]
        relations = [("p1", "p2", "CITES")]

        orphans = validator.check_orphan_nodes(nodes, relations)
        assert "p3" in orphans
        assert "p1" not in orphans

    def test_validate_consistency_stats(self):
        """测试验证统计信息"""
        validator = kg_schema.DataModelValidator()
        nodes = [
            ("p1", "Paper", {}),
            ("p2", "Paper", {}),
            ("p1", "Paper", {})  # 重复
        ]
        relations = [("p1", "p2", "CITES", {})]

        result = validator.validate_consistency(nodes, relations)
        assert result["stats"]["total_nodes"] == 3
        assert result["stats"]["unique_nodes"] == 2


class TestCreateDefaultSchemaManager:
    """create_default_schema_manager工厂函数测试"""

    def test_create(self):
        """测试创建"""
        manager = kg_schema.create_default_schema_manager()
        assert isinstance(manager, kg_schema.SchemaManager)
        assert len(manager._node_schemas) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
