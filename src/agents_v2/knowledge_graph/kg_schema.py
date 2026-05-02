"""
知识图谱数据模型与索引模块

功能:
1. 数据模型定义 (节点类型、关系类型)
2. 索引管理 (属性索引、关系索引)
3. 约束管理 (唯一性约束、存在性约束)
4. 查询优化提示
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class NodeType(str, Enum):
    """节点类型"""
    PAPER = "Paper"
    AUTHOR = "Author"
    VENUE = "Venue"
    METHOD = "Method"
    DATASET = "Dataset"
    TASK = "Task"
    METRIC = "Metric"
    FIELD = "Field"


class RelationType(str, Enum):
    """关系类型"""
    CITES = "CITES"
    AUTHORED_BY = "AUTHORED_BY"
    PUBLISHED_IN = "PUBLISHED_IN"
    USES = "USES"
    PROPOSES = "PROPOSES"
    COMPARED_WITH = "COMPARED_WITH"
    BASED_ON = "BASED_ON"
    FOLLOWS = "FOLLOWS"
    RELATED_TO = "RELATED_TO"


@dataclass
class PropertyDefinition:
    """属性定义"""
    name: str
    type: str  # "string", "int", "float", "bool", "list"
    indexed: bool = False
    unique: bool = False
    required: bool = False
    default: Any = None


@dataclass
class NodeSchema:
    """节点Schema"""
    type: NodeType
    properties: List[PropertyDefinition] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)

    def get_indexed_properties(self) -> List[str]:
        return [p.name for p in self.properties if p.indexed]

    def get_required_properties(self) -> List[str]:
        return [p.name for p in self.properties if p.required]


@dataclass
class RelationshipSchema:
    """关系Schema"""
    type: RelationType
    source_types: List[NodeType]
    target_types: List[NodeType]
    properties: List[PropertyDefinition] = field(default_factory=list)

    def get_indexed_properties(self) -> List[str]:
        return [p.name for p in self.properties if p.indexed]


class SchemaManager:
    """
    Schema管理器

    管理知识图谱的节点和关系Schema
    """

    def __init__(self):
        self._node_schemas: Dict[NodeType, NodeSchema] = {}
        self._relation_schemas: Dict[RelationType, RelationshipSchema] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """初始化默认Schema"""
        # Paper节点
        self.register_node_schema(NodeSchema(
            type=NodeType.PAPER,
            labels=["Entity", "Paper"],
            properties=[
                PropertyDefinition("paper_id", "string", indexed=True, unique=True, required=True),
                PropertyDefinition("title", "string", indexed=True, required=True),
                PropertyDefinition("abstract", "string"),
                PropertyDefinition("year", "int", indexed=True),
                PropertyDefinition("citation_count", "int", indexed=True),
                PropertyDefinition("venue", "string", indexed=True),
                PropertyDefinition("doi", "string"),
                PropertyDefinition("authors", "list"),
                PropertyDefinition("keywords", "list", indexed=True),
                PropertyDefinition("created_at", "float"),
                PropertyDefinition("updated_at", "float"),
            ]
        ))

        # Author节点
        self.register_node_schema(NodeSchema(
            type=NodeType.AUTHOR,
            labels=["Entity", "Author"],
            properties=[
                PropertyDefinition("author_id", "string", indexed=True, unique=True, required=True),
                PropertyDefinition("name", "string", indexed=True, required=True),
                PropertyDefinition("institution", "string", indexed=True),
                PropertyDefinition("h_index", "int", indexed=True),
                PropertyDefinition("paper_count", "int"),
                PropertyDefinition("created_at", "float"),
                PropertyDefinition("updated_at", "float"),
            ]
        ))

        # Venue节点
        self.register_node_schema(NodeSchema(
            type=NodeType.VENUE,
            labels=["Entity", "Venue"],
            properties=[
                PropertyDefinition("venue_id", "string", indexed=True, unique=True, required=True),
                PropertyDefinition("name", "string", indexed=True, required=True),
                PropertyDefinition("type", "string"),  # conference, journal
                PropertyDefinition("rank", "string"),
                PropertyDefinition("created_at", "float"),
                PropertyDefinition("updated_at", "float"),
            ]
        ))

        # Method节点
        self.register_node_schema(NodeSchema(
            type=NodeType.METHOD,
            labels=["Entity", "Method"],
            properties=[
                PropertyDefinition("method_id", "string", indexed=True, unique=True, required=True),
                PropertyDefinition("name", "string", indexed=True, required=True),
                PropertyDefinition("category", "string", indexed=True),
                PropertyDefinition("complexity", "string"),
                PropertyDefinition("created_at", "float"),
                PropertyDefinition("updated_at", "float"),
            ]
        ))

        # Dataset节点
        self.register_node_schema(NodeSchema(
            type=NodeType.DATASET,
            labels=["Entity", "Dataset"],
            properties=[
                PropertyDefinition("dataset_id", "string", indexed=True, unique=True, required=True),
                PropertyDefinition("name", "string", indexed=True, required=True),
                PropertyDefinition("size", "string"),
                PropertyDefinition("task", "string", indexed=True),
                PropertyDefinition("created_at", "float"),
                PropertyDefinition("updated_at", "float"),
            ]
        ))

        # 关系Schema
        self.register_relation_schema(RelationshipSchema(
            type=RelationType.CITES,
            source_types=[NodeType.PAPER],
            target_types=[NodeType.PAPER],
            properties=[
                PropertyDefinition("context", "string"),
                PropertyDefinition("created_at", "float"),
            ]
        ))

        self.register_relation_schema(RelationshipSchema(
            type=RelationType.AUTHORED_BY,
            source_types=[NodeType.PAPER],
            target_types=[NodeType.AUTHOR],
            properties=[
                PropertyDefinition("position", "int"),
                PropertyDefinition("corresponding", "bool"),
                PropertyDefinition("created_at", "float"),
            ]
        ))

        self.register_relation_schema(RelationshipSchema(
            type=RelationType.PUBLISHED_IN,
            source_types=[NodeType.PAPER],
            target_types=[NodeType.VENUE],
            properties=[
                PropertyDefinition("year", "int"),
                PropertyDefinition("created_at", "float"),
            ]
        ))

        self.register_relation_schema(RelationshipSchema(
            type=RelationType.USES,
            source_types=[NodeType.PAPER, NodeType.METHOD],
            target_types=[NodeType.DATASET, NodeType.METHOD],
            properties=[
                PropertyDefinition("context", "string"),
                PropertyDefinition("created_at", "float"),
            ]
        ))

    def register_node_schema(self, schema: NodeSchema) -> None:
        """注册节点Schema"""
        self._node_schemas[schema.type] = schema

    def register_relation_schema(self, schema: RelationshipSchema) -> None:
        """注册关系Schema"""
        self._relation_schemas[schema.type] = schema

    def get_node_schema(self, node_type: NodeType) -> Optional[NodeSchema]:
        """获取节点Schema"""
        return self._node_schemas.get(node_type)

    def get_relation_schema(self, rel_type: RelationType) -> Optional[RelationshipSchema]:
        """获取关系Schema"""
        return self._relation_schemas.get(rel_type)

    def validate_node(
        self,
        node_type: NodeType,
        properties: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        验证节点属性

        Returns:
            (is_valid, error_messages)
        """
        schema = self.get_node_schema(node_type)
        if not schema:
            return False, [f"Unknown node type: {node_type}"]

        errors = []
        for prop in schema.properties:
            if prop.required and prop.name not in properties:
                errors.append(f"Required property missing: {prop.name}")
            if prop.name in properties:
                value = properties[prop.name]
                if not self._validate_property_type(prop.type, value):
                    errors.append(f"Property {prop.name} has invalid type")

        return len(errors) == 0, errors

    def _validate_property_type(self, expected_type: str, value: Any) -> bool:
        """验证属性类型"""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "int":
            return isinstance(value, int)
        elif expected_type == "float":
            return isinstance(value, (int, float))
        elif expected_type == "bool":
            return isinstance(value, bool)
        elif expected_type == "list":
            return isinstance(value, list)
        return True

    def get_index_recommendations(self) -> Dict[str, List[str]]:
        """获取索引推荐"""
        recommendations = {"nodes": [], "relationships": []}

        for schema in self._node_schemas.values():
            indexed = schema.get_indexed_properties()
            if indexed:
                recommendations["nodes"].append(
                    f"{schema.type.value}: {', '.join(indexed)}"
                )

        return recommendations

    def generate_cypher_constraints(self) -> List[str]:
        """生成Cypher约束语句"""
        cypher = []

        for schema in self._node_schemas.values():
            for prop in schema.properties:
                if prop.unique:
                    cypher.append(
                        f"CREATE CONSTRAINT {prop.name}_unique IF NOT EXISTS "
                        f"FOR (n:{schema.type.value}) REQUIRE n.{prop.name} IS UNIQUE"
                    )

        return cypher

    def generate_cypher_indexes(self) -> List[str]:
        """生成Cypher索引语句"""
        cypher = []

        for schema in self._node_schemas.values():
            for prop in schema.properties:
                if prop.indexed and not prop.unique:
                    cypher.append(
                        f"CREATE INDEX {prop.name}_index IF NOT EXISTS "
                        f"FOR (n:{schema.type.value}) ON (n.{prop.name})"
                    )

        return cypher


class QueryOptimizer:
    """
    查询优化器

    提供查询优化建议
    """

    def __init__(self, schema_manager: Optional[SchemaManager] = None):
        self.schema_manager = schema_manager or SchemaManager()

    def optimize_match_pattern(
        self,
        pattern: str
    ) -> Dict[str, Any]:
        """
        优化MATCH模式

        Args:
            pattern: Cypher MATCH模式

        Returns:
            {
                "optimized": bool,
                "suggestions": List[str],
                "estimated_cost": str
            }
        """
        suggestions = []

        # 检查是否使用了索引属性
        if "WHERE" in pattern:
            suggestions.append("确保WHERE子句使用的属性有索引")

        # 检查是否使用了LOAD CSV
        if "LOAD CSV" in pattern:
            suggestions.append("使用PERIODIC COMMIT避免内存溢出")

        # 检查是否使用了星号
        if "*" in pattern and pattern.count("*") > 1:
            suggestions.append("避免使用RETURN *，明确指定需要的属性")

        return {
            "optimized": len(suggestions) == 0,
            "suggestions": suggestions,
            "estimated_cost": "medium" if suggestions else "low"
        }

    def suggest_relation_pattern(
        self,
        source_type: NodeType,
        target_type: NodeType,
        depth: int = 1
    ) -> str:
        """
        推荐关系模式

        Args:
            source_type: 源节点类型
            target_type: 目标节点类型
            depth: 关系深度

        Returns:
            优化的Cypher模式
        """
        if depth == 1:
            return f"(a:{source_type.value})-[]->(b:{target_type.value})"
        else:
            return f"(a:{source_type.value})-[]->{{depth}}-(b:{target_type.value})"

    def get_hint_for_query_type(self, query_type: str) -> List[str]:
        """
        获取查询类型提示

        Args:
            query_type: "neighbor", "path", "aggregation", "fulltext"

        Returns:
            优化提示列表
        """
        hints = {
            "neighbor": [
                "使用CALL db.getSubgraph获取子图",
                "避免使用深度过大的遍历",
            ],
            "path": [
                "使用最短路径算法",
                "限制路径长度",
            ],
            "aggregation": [
                "使用聚合函数替代全表扫描",
                "添加适当的GROUP BY",
            ],
            "fulltext": [
                "使用全文索引",
                "使用CONTAINS替代正则表达式",
            ],
        }
        return hints.get(query_type, [])


class IndexManager:
    """
    索引管理器

    管理Neo4j索引的创建和维护
    """

    def __init__(self):
        self._custom_indexes: Dict[str, Dict[str, Any]] = {}

    def create_composite_index(
        self,
        name: str,
        node_type: str,
        properties: List[str]
    ) -> str:
        """
        创建组合索引

        Returns:
            Cypher语句
        """
        props_str = ", ".join([f"n.{p}" for p in properties])
        return f"CREATE INDEX {name} IF NOT EXISTS FOR (n:{node_type}) ON ({props_str})"

    def create_fulltext_index(
        self,
        name: str,
        node_types: List[str],
        properties: List[str]
    ) -> str:
        """
        创建全文索引

        Returns:
            Cypher语句
        """
        node_str = "|".join(node_types)
        props_str = ", ".join(properties)
        return (
            f"CALL db.index.fulltext.createNodeIndex("
            f"'{name}', ['{node_str}'], ['{props_str}'])"
        )

    def create_relationship_index(
        self,
        name: str,
        rel_type: str,
        properties: List[str]
    ) -> str:
        """
        创建关系索引

        Returns:
            Cypher语句
        """
        props_str = ", ".join([f"r.{p}" for p in properties])
        return f"CREATE INDEX {name} IF NOT EXISTS FOR ()-[r:{rel_type}]-() ON ({props_str})"

    def suggest_indexes_for_queries(
        self,
        queries: List[str]
    ) -> List[str]:
        """
        根据查询推荐索引

        Args:
            queries: Cypher查询列表

        Returns:
            推荐的索引创建语句
        """
        recommendations = []

        # 分析每个查询
        for query in queries:
            # 查找节点类型
            import re
            node_matches = re.findall(r":(\w+)\)", query)

            for node_type in node_matches:
                if node_type in [e.value for e in NodeType]:
                    recommendations.append(
                        f"-- Consider: CREATE INDEX FOR (n:{node_type}) ON (n.id)"
                    )

        return list(set(recommendations))


class DataModelValidator:
    """
    数据模型验证器

    验证数据模型的一致性和完整性
    """

    def __init__(self, schema_manager: Optional[SchemaManager] = None):
        self.schema_manager = schema_manager or SchemaManager()

    def validate_consistency(
        self,
        nodes: List[Tuple[str, str, Dict]],
        relations: List[Tuple[str, str, str, Dict]]
    ) -> Dict[str, Any]:
        """
        验证数据一致性

        Args:
            nodes: [(entity_id, entity_type, properties), ...]
            relations: [(source_id, target_id, relation_type, properties), ...]

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 检查节点
        node_ids = set()
        for entity_id, entity_type, properties in nodes:
            node_ids.add(entity_id)

            # 验证类型
            try:
                node_type = NodeType(entity_type)
                is_valid, errs = self.schema_manager.validate_node(node_type, properties)
                errors.extend(errs)
            except ValueError:
                warnings.append(f"Unknown node type: {entity_type}")

        # 检查关系
        for source_id, target_id, rel_type, properties in relations:
            if source_id not in node_ids:
                errors.append(f"Source node not found: {source_id}")
            if target_id not in node_ids:
                errors.append(f"Target node not found: {target_id}")

            # 验证关系类型
            try:
                RelationType(rel_type)
            except ValueError:
                warnings.append(f"Unknown relation type: {rel_type}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "total_nodes": len(nodes),
                "total_relations": len(relations),
                "unique_nodes": len(node_ids)
            }
        }

    def check_orphan_nodes(
        self,
        nodes: List[str],
        relations: List[Tuple[str, str, str]]
    ) -> List[str]:
        """
        检查孤立节点

        Returns:
            孤立节点ID列表
        """
        connected = set()
        for source, target, rel_type in relations:
            connected.add(source)
            connected.add(target)

        return [n for n in nodes if n not in connected]


def create_default_schema_manager() -> SchemaManager:
    """创建默认Schema管理器"""
    return SchemaManager()
