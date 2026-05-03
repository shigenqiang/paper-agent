"""
学术知识图谱构建器
Academic Graph Builder
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from ..schema.academic_kg_schema import (
    Entity, Relation, EntityType, RelationType, ParsedDocument
)
from ..parser.pdf_parser import PDFAcademicParser
from ..parser.text_preprocessor import TextPreprocessor
from ..extraction.ner import AcademicNER
from ..extraction.relation_extractor import AcademicRelationExtractor
from .neo4j_client import Neo4jClient
from .vector_store import VectorStoreClient


@dataclass
class BuildResult:
    """构建结果"""
    total_documents: int
    total_entities: int
    total_relations: int
    entity_types: Dict[str, int]
    relation_types: Dict[str, int]
    errors: List[str]


class AcademicGraphBuilder:
    """学术知识图谱构建器"""

    def __init__(
        self,
        neo4j_client: Optional[Neo4jClient] = None,
        vector_store: Optional[VectorStoreClient] = None,
        use_ner_model: bool = False
    ):
        self.neo4j = neo4j_client
        self.vector_store = vector_store

        # 初始化组件
        self.parser = PDFAcademicParser()
        self.preprocessor = TextPreprocessor()
        self.ner = AcademicNER(use_transformers=use_ner_model)
        self.relation_extractor = AcademicRelationExtractor()

        # 状态
        self._entities: List[Entity] = []
        self._relations: List[Relation] = []
        self._entity_counter = 0
        self._relation_counter = 0

    def build_from_documents(
        self,
        documents: List[str],
        batch_size: int = 10
    ) -> BuildResult:
        """从文档列表构建知识图谱"""
        total_entities = 0
        total_relations = 0
        entity_types: Dict[str, int] = {}
        relation_types: Dict[str, int] = {}
        errors: List[str] = []

        for i, doc_path in enumerate(documents):
            try:
                # 解析文档
                parsed_doc = self.parser.parse(doc_path)

                # 提取实体
                entities = self._extract_entities(parsed_doc)
                total_entities += len(entities)
                self._entities.extend(entities)

                # 更新实体类型统计
                for entity in entities:
                    etype = entity.type.value
                    entity_types[etype] = entity_types.get(etype, 0) + 1

                # 抽取关系
                relations = self._extract_relations(parsed_doc, entities)
                total_relations += len(relations)
                self._relations.extend(relations)

                # 更新关系类型统计
                for relation in relations:
                    rtype = relation.type.value
                    relation_types[rtype] = relation_types.get(rtype, 0) + 1

            except Exception as e:
                errors.append(f"Error processing {doc_path}: {str(e)}")

        # 存储到数据库
        if self.neo4j:
            self._store_to_neo4j()

        return BuildResult(
            total_documents=len(documents),
            total_entities=total_entities,
            total_relations=total_relations,
            entity_types=entity_types,
            relation_types=relation_types,
            errors=errors
        )

    def build_from_directory(
        self,
        directory: str,
        file_patterns: List[str] = ["*.pdf", "*.txt", "*.md"],
        batch_size: int = 10
    ) -> BuildResult:
        """从目录构建知识图谱"""
        directory = Path(directory)

        documents = []
        for pattern in file_patterns:
            documents.extend(directory.glob(pattern))

        return self.build_from_documents(
            [str(d) for d in documents],
            batch_size=batch_size
        )

    def _extract_entities(self, doc: ParsedDocument) -> List[Entity]:
        """从文档中提取实体"""
        # 识别实体
        recognized = self.ner.extract_from_document(doc)

        # 转换为Entity
        entities = []
        for rec in recognized:
            entity_id = self._generate_entity_id()
            entity = Entity(
                id=entity_id,
                name=rec.text,
                type=rec.type,
                properties={
                    "confidence": rec.confidence,
                    "start_pos": rec.start_pos,
                    "end_pos": rec.end_pos,
                    "source_document": doc.file_path
                }
            )
            entities.append(entity)

        return entities

    def _extract_relations(
        self,
        doc: ParsedDocument,
        entities: List[Entity]
    ) -> List[Relation]:
        """从文档中抽取关系"""
        # 抽取关系
        recognized = self.relation_extractor.extract_relations(
            doc.content, entities
        )

        # 转换为Relation
        relations = []
        for rec in recognized:
            # 查找源实体和目标实体ID
            source_id = self._find_entity_id_by_text(rec.source_text, entities)
            target_id = self._find_entity_id_by_text(rec.target_text, entities)

            if source_id and target_id:
                relation_id = self._generate_relation_id()
                relation = Relation(
                    source=source_id,
                    target=target_id,
                    type=rec.type,
                    properties={
                        "confidence": rec.confidence,
                        "context": rec.context
                    }
                )
                relations.append(relation)

        return relations

    def _generate_entity_id(self) -> str:
        """生成实体ID"""
        self._entity_counter += 1
        return f"entity_{self._entity_counter}"

    def _generate_relation_id(self) -> str:
        """生成关系ID"""
        self._relation_counter += 1
        return f"relation_{self._relation_counter}"

    def _find_entity_id_by_text(
        self,
        text: str,
        entities: List[Entity]
    ) -> Optional[str]:
        """根据文本查找实体ID"""
        for entity in entities:
            if entity.name == text:
                return entity.id
            if text in entity.name or entity.name in text:
                return entity.id
        return None

    def _store_to_neo4j(self):
        """存储到Neo4j"""
        if not self.neo4j:
            return

        # 确保Schema创建
        self.neo4j.create_schema()

        # 插入实体
        self.neo4j.insert_entities(self._entities)

        # 插入关系
        self.neo4j.insert_relations(self._relations)

    def add_entity(self, entity: Entity) -> str:
        """添加实体"""
        entity.id = entity.id or self._generate_entity_id()
        self._entities.append(entity)

        if self.neo4j:
            self.neo4j.insert_entity(entity)

        return entity.id

    def add_relation(self, relation: Relation) -> str:
        """添加关系"""
        relation_id = self._generate_relation_id()
        self._relations.append(relation)

        if self.neo4j:
            self.neo4j.insert_relation(relation)

        return relation_id

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        for entity in self._entities:
            if entity.id == entity_id:
                return entity
        return None

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        """获取关系"""
        for relation in self._relations:
            if f"{relation.source}_{relation.target}" == relation_id:
                return relation
        return None

    def find_entities_by_type(
        self,
        entity_type: EntityType
    ) -> List[Entity]:
        """查找指定类型的所有实体"""
        return [e for e in self._entities if e.type == entity_type]

    def find_relations_by_type(
        self,
        relation_type: RelationType
    ) -> List[Relation]:
        """查找指定类型的所有关系"""
        return [r for r in self._relations if r.type == relation_type]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        entity_types: Dict[str, int] = {}
        relation_types: Dict[str, int] = {}

        for entity in self._entities:
            etype = entity.type.value
            entity_types[etype] = entity_types.get(etype, 0) + 1

        for relation in self._relations:
            rtype = relation.type.value
            relation_types[rtype] = relation_types.get(rtype, 0) + 1

        return {
            "total_entities": len(self._entities),
            "total_relations": len(self._relations),
            "entity_types": entity_types,
            "relation_types": relation_types
        }

    def export_to_dict(self) -> Dict:
        """导出为字典"""
        return {
            "entities": [e.to_dict() for e in self._entities],
            "relations": [r.to_dict() for r in self._relations]
        }

    def clear(self):
        """清空所有数据"""
        self._entities.clear()
        self._relations.clear()
        self._entity_counter = 0
        self._relation_counter = 0

        if self.neo4j:
            self.neo4j.clear_graph()
