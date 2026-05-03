"""Schema module - 学术论文知识图谱Schema定义"""

from .academic_kg_schema import (
    AcademicKGSchema,
    Entity,
    EntityType,
    Relation,
    RelationType,
    ParsedDocument,
)

__all__ = [
    "AcademicKGSchema",
    "Entity",
    "EntityType",
    "Relation",
    "RelationType",
    "ParsedDocument",
]
