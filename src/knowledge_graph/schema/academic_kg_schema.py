"""
学术论文知识图谱Schema定义
Academic Paper Knowledge Graph Schema
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class EntityType(str, Enum):
    """实体类型枚举"""
    PAPER = "Paper"
    AUTHOR = "Author"
    INSTITUTION = "Institution"
    VENUE = "Venue"
    KEYWORD = "Keyword"
    METHOD = "Method"
    DATASET = "Dataset"


class RelationType(str, Enum):
    """关系类型枚举"""
    # 论文-作者关系
    AUTHORED_BY = "AUTHORED_BY"
    AUTHOR_OF = "AUTHOR_OF"

    # 论文-机构关系
    AFFILIATED_WITH = "AFFILIATED_WITH"
    HAS_AUTHOR = "HAS_AUTHOR"

    # 论文-发表场所关系
    PUBLISHED_IN = "PUBLISHED_IN"
    PUBLISHED_PAPERS = "PUBLISHED_PAPERS"

    # 论文-关键词关系
    HAS_KEYWORD = "HAS_KEYWORD"
    KEYWORD_OF_PAPERS = "KEYWORD_OF_PAPERS"

    # 论文-引用关系
    CITES = "CITES"
    CITED_BY = "CITED_BY"

    # 论文-方法关系
    USES_METHOD = "USES_METHOD"
    USED_IN_PAPERS = "USED_IN_PAPERS"

    # 论文-数据集关系
    USES_DATASET = "USES_DATASET"
    DATASET_USED_IN = "DATASET_USED_IN"

    # 作者-合作关系
    COLLABORATES_WITH = "COLLABORATES_WITH"


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = EntityType(self.type)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Entity":
        return cls(
            id=data["id"],
            name=data["name"],
            type=EntityType(data["type"]),
            properties=data.get("properties", {})
        )


@dataclass
class Relation:
    """知识图谱关系"""
    source: str  # 源实体ID
    target: str  # 目标实体ID
    type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = RelationType(self.type)

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Relation":
        return cls(
            source=data["source"],
            target=data["target"],
            type=RelationType(data["type"]),
            properties=data.get("properties", {})
        )


@dataclass
class ParsedDocument:
    """解析后的文档"""
    file_path: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    pages: List[Dict] = field(default_factory=list)
    sections: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "content": self.content,
            "metadata": self.metadata,
            "pages": self.pages,
            "sections": self.sections
        }


class AcademicKGSchema:
    """学术论文知识图谱Schema"""

    # 实体类型定义
    ENTITY_TYPES = {
        "Paper": {
            "description": "学术论文",
            "attributes": ["title", "abstract", "year", "venue", "doi", "url"],
            "examples": ["Attention Is All You Need"]
        },
        "Author": {
            "description": "作者",
            "attributes": ["name", "affiliation", "email", "orcid"],
            "examples": ["Yann LeCun", "Yoshua Bengio"]
        },
        "Institution": {
            "description": "机构",
            "attributes": ["name", "country", "type", "url"],
            "examples": ["MIT", "Stanford University", "清华大学"]
        },
        "Venue": {
            "description": "发表场所（期刊/会议）",
            "attributes": ["name", "type", "publisher", "abbr"],
            "examples": ["NeurIPS", "Nature", "ICML"]
        },
        "Keyword": {
            "description": "关键词",
            "attributes": ["name", "frequency"],
            "examples": ["deep learning", "reinforcement learning", "transformer"]
        },
        "Method": {
            "description": "研究方法/模型",
            "attributes": ["name", "category"],
            "examples": ["Transformer", "GAN", "BERT", "ResNet"]
        },
        "Dataset": {
            "description": "数据集",
            "attributes": ["name", "task", "size"],
            "examples": ["ImageNet", "GLUE", "MNIST", "COCO"]
        }
    }

    # 关系类型定义
    RELATION_TYPES = {
        "AUTHORED_BY": {
            "source": "Paper",
            "target": "Author",
            "description": "论文作者关系",
            "reverse": "AUTHOR_OF"
        },
        "AFFILIATED_WITH": {
            "source": "Author",
            "target": "Institution",
            "description": "作者所属机构",
            "reverse": "HAS_AUTHOR"
        },
        "PUBLISHED_IN": {
            "source": "Paper",
            "target": "Venue",
            "description": "论文发表场所",
            "reverse": "PUBLISHED_PAPERS"
        },
        "HAS_KEYWORD": {
            "source": "Paper",
            "target": "Keyword",
            "description": "论文关键词",
            "reverse": "KEYWORD_OF_PAPERS"
        },
        "CITES": {
            "source": "Paper",
            "target": "Paper",
            "description": "论文引用关系",
            "reverse": "CITED_BY"
        },
        "USES_METHOD": {
            "source": "Paper",
            "target": "Method",
            "description": "论文使用方法",
            "reverse": "USED_IN_PAPERS"
        },
        "USES_DATASET": {
            "source": "Paper",
            "target": "Dataset",
            "description": "论文使用数据集",
            "reverse": "DATASET_USED_IN"
        },
        "COLLABORATES_WITH": {
            "source": "Author",
            "target": "Author",
            "description": "作者合作关系"
        }
    }

    @classmethod
    def get_entity_attributes(cls, entity_type: str) -> List[str]:
        """获取实体类型的属性列表"""
        return cls.ENTITY_TYPES.get(entity_type, {}).get("attributes", [])

    @classmethod
    def get_relation_schema(cls, relation_type: str) -> Dict:
        """获取关系类型的Schema"""
        return cls.RELATION_TYPES.get(relation_type, {})

    @classmethod
    def get_reverse_relation(cls, relation_type: str) -> Optional[str]:
        """获取反向关系类型"""
        schema = cls.RELATION_TYPES.get(relation_type, {})
        return schema.get("reverse")

    @classmethod
    def validate_entity(cls, entity: Entity) -> bool:
        """验证实体是否符合Schema"""
        if entity.type.value not in cls.ENTITY_TYPES:
            return False
        return True

    @classmethod
    def validate_relation(cls, relation: Relation) -> bool:
        """验证关系是否符合Schema"""
        rel_type = relation.type.value
        if rel_type not in cls.RELATION_TYPES:
            return False

        schema = cls.RELATION_TYPES[rel_type]
        return True

    @classmethod
    def get_cypher_constraint_statements(cls) -> List[str]:
        """生成Neo4j约束Cypher语句"""
        statements = []
        for entity_type in cls.ENTITY_TYPES:
            statements.append(
                f"CREATE CONSTRAINT IF NOT EXISTS FOR (e:{entity_type}) "
                f"REQUIRE e.id IS UNIQUE"
            )
        return statements

    @classmethod
    def get_cypher_index_statements(cls) -> List[str]:
        """生成Neo4j索引Cypher语句"""
        statements = []
        statements.append("CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.title)")
        statements.append("CREATE INDEX IF NOT EXISTS FOR (a:Author) ON (a.name)")
        statements.append("CREATE INDEX IF NOT EXISTS FOR (v:Venue) ON (v.name)")
        return statements
