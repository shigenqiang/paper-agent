"""关系抽取器"""
from typing import List, Dict, Any, Optional
import logging
from abc import ABC, abstractmethod

from src.knowledge.extraction.base_extractor import BaseExtractor, ExtractedRelation, ExtractedEntity

logger = logging.getLogger(__name__)


class RelationExtractor(ABC):
    """关系抽取器接口"""

    @abstractmethod
    async def extract(
        self,
        text: str,
        entities: List[ExtractedEntity],
        **kwargs
    ) -> List[ExtractedRelation]:
        """抽取关系"""
        pass


class PatternBasedRelationExtractor(RelationExtractor):
    """基于模式的关系抽取器"""

    def __init__(
        self,
        patterns: Dict[str, str],
        max_distance: int = 50
    ):
        """
        Args:
            patterns: 关系类型到正则表达式的映射
            max_distance: 实体间的最大距离（字符数）
        """
        self.patterns = patterns
        self.max_distance = max_distance

    async def extract(
        self,
        text: str,
        entities: List[ExtractedEntity],
        relation_types: Optional[List[str]] = None,
        **kwargs
    ) -> List[ExtractedRelation]:
        """使用正则表达式抽取关系"""
        import re

        if relation_types is None:
            relation_types = list(self.patterns.keys())

        relations = []

        # 创建实体位置映射
        entity_positions = [(e.start_pos, e) for e in entities]
        entity_positions.sort()

        for relation_type in relation_types:
            if relation_type not in self.patterns:
                continue

            pattern = self.patterns[relation_type]
            matches = re.finditer(pattern, text)

            for match in matches:
                # 找到附近的实体
                match_pos = match.start()
                nearby_entities = self._find_nearby_entities(
                    entity_positions,
                    match_pos
                )

                # 尝试配对实体
                for i, (pos1, entity1) in enumerate(nearby_entities):
                    for (pos2, entity2) in nearby_entities[i+1:]:
                        # 检查距离
                        if abs(pos2 - pos1) <= self.max_distance:
                            relation_id = self._create_relation_id(
                                entity1.id,
                                entity2.id,
                                relation_type
                            )

                            relation = ExtractedRelation(
                                id=relation_id,
                                source_id=entity1.id,
                                target_id=entity2.id,
                                relation_type=relation_type,
                                confidence=0.6
                            )
                            relations.append(relation)

        logger.info(f"Extracted {len(relations)} relations using patterns")
        return relations

    def _find_nearby_entities(
        self,
        entity_positions: List[tuple],
        position: int
    ) -> List[tuple]:
        """找到位置附近的实体"""
        nearby = []

        for pos, entity in entity_positions:
            if abs(pos - position) <= self.max_distance:
                nearby.append((pos, entity))

        return nearby

    def _create_relation_id(
        self,
        source_id: str,
        target_id: str,
        relation_type: str
    ) -> str:
        """创建关系ID"""
        import hashlib
        content = f"{source_id}_{target_id}_{relation_type}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class ConceptRelationExtractor(RelationExtractor):
    """概念关系抽取器 - 用于概念图谱"""

    def __init__(self, concept_graph):
        self.concept_graph = concept_graph

    async def extract(
        self,
        text: str,
        entities: List[ExtractedEntity],
        **kwargs
    ) -> List[ExtractedRelation]:
        """
        抽取概念关系

        基于概念图谱的层次结构抽取关系
        """
        relations = []

        if self.concept_graph is None:
            return relations

        # 创建实体ID到实体的映射
        entity_map = {e.id: e for e in entities}

        # 抽取层次关系
        for entity in entities:
            if entity.properties and "parent_id" in entity.properties:
                parent_id = entity.properties["parent_id"]

                # 检查父实体是否也在实体列表中
                if parent_id in entity_map:
                    relation_id = self._create_relation_id(
                        parent_id,
                        entity.id,
                        "包含"
                    )

                    relation = ExtractedRelation(
                        id=relation_id,
                        source_id=parent_id,
                        target_id=entity.id,
                        relation_type="包含",
                        confidence=0.9
                    )
                    relations.append(relation)

        logger.info(f"Extracted {len(relations)} concept relations")
        return relations

    def _create_relation_id(
        self,
        source_id: str,
        target_id: str,
        relation_type: str
    ) -> str:
        """创建关系ID"""
        import hashlib
        content = f"{source_id}_{target_id}_{relation_type}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class DependencyBasedRelationExtractor(RelationExtractor):
    """基于依存分析的关系抽取器"""

    def __init__(self, relation_patterns: Dict[str, Dict[str, Any]]):
        """
        Args:
            relation_patterns: 关系模式配置
                {
                    "包含": {
                        "dependency": "nmod",
                        "pos_pattern": ["NOUN", "PROPN"]
                    }
                }
        """
        self.relation_patterns = relation_patterns

    async def extract(
        self,
        text: str,
        entities: List[ExtractedEntity],
        **kwargs
    ) -> List[ExtractedRelation]:
        """
        使用依存分析抽取关系

        注意：这是一个示例实现，实际应用中应该：
        1. 使用spaCy或Stanza进行依存分析
        2. 根据依存关系识别实体间的关系
        """
        try:
            import spacy
            nlp = spacy.load("zh_core_web_sm")
        except Exception as e:
            logger.warning(f"spaCy not available, skipping dependency analysis: {e}")
            return []

        doc = nlp(text)
        relations = []

        # 创建实体到span的映射
        entity_spans = self._map_entities_to_spans(doc, entities)

        # 分析依存关系
        for token in doc:
            if token.head == token:
                continue

            # 检查是否涉及实体
            source_entity = self._find_entity_at_token(token.head, entity_spans)
            target_entity = self._find_entity_at_token(token, entity_spans)

            if source_entity and target_entity:
                # 匹配关系模式
                for relation_type, pattern in self.relation_patterns.items():
                    if self._match_pattern(token, pattern):
                        relation_id = self._create_relation_id(
                            source_entity.id,
                            target_entity.id,
                            relation_type
                        )

                        relation = ExtractedRelation(
                            id=relation_id,
                            source_id=source_entity.id,
                            target_id=target_entity.id,
                            relation_type=relation_type,
                            confidence=0.7
                        )
                        relations.append(relation)
                        break

        logger.info(f"Extracted {len(relations)} relations using dependency analysis")
        return relations

    def _map_entities_to_spans(
        self,
        doc,
        entities: List[ExtractedEntity]
    ) -> Dict[int, ExtractedEntity]:
        """将实体映射到文档的token位置"""
        entity_map = {}

        for entity in entities:
            # 找到实体文本在文档中的位置
            for token in doc:
                if entity.text.lower() in token.text.lower():
                    entity_map[token.i] = entity
                    break

        return entity_map

    def _find_entity_at_token(
        self,
        token,
        entity_spans: Dict[int, ExtractedEntity]
    ) -> Optional[ExtractedEntity]:
        """在token位置查找实体"""
        # 检查当前token
        if token.i in entity_spans:
            return entity_spans[token.i]

        # 检查子树中的token
        for child in token.children:
            entity = self._find_entity_at_token(child, entity_spans)
            if entity:
                return entity

        return None

    def _match_pattern(self, token, pattern: Dict[str, Any]) -> bool:
        """检查token是否匹配模式"""
        # 检查依存关系
        if "dependency" in pattern:
            if token.dep_ != pattern["dependency"]:
                return False

        # 检查词性
        if "pos_pattern" in pattern:
            if token.pos_ not in pattern["pos_pattern"]:
                return False

        return True

    def _create_relation_id(
        self,
        source_id: str,
        target_id: str,
        relation_type: str
    ) -> str:
        """创建关系ID"""
        import hashlib
        content = f"{source_id}_{target_id}_{relation_type}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
