"""抽取器基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    """抽取的实体"""
    id: str
    text: str
    type: str
    confidence: float = 0.0
    start_pos: int = 0
    end_pos: int = 0
    properties: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.properties is None:
            self.properties = {}


class ExtractedRelation(BaseModel):
    """抽取的关系"""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    confidence: float = 0.0
    properties: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.properties is None:
            self.properties = {}


class ExtractionResult(BaseModel):
    """抽取结果"""
    entities: List[ExtractedEntity] = []
    relations: List[ExtractedRelation] = []
    metadata: Optional[Dict[str, Any]] = None
    processing_time: float = 0.0
    confidence_threshold: float = 0.5

    def filter_by_confidence(self, threshold: float) -> "ExtractionResult":
        """根据置信度过滤结果"""
        filtered_entities = [
            e for e in self.entities
            if e.confidence >= threshold
        ]
        filtered_relations = [
            r for r in self.relations
            if r.confidence >= threshold
        ]

        return ExtractionResult(
            entities=filtered_entities,
            relations=filtered_relations,
            metadata=self.metadata,
            processing_time=self.processing_time,
            confidence_threshold=threshold
        )

    def get_entity_by_text(self, text: str) -> Optional[ExtractedEntity]:
        """根据文本获取实体"""
        for entity in self.entities:
            if entity.text.lower() == text.lower():
                return entity
        return None

    def get_relations_for_entity(self, entity_id: str) -> List[ExtractedRelation]:
        """获取与实体相关的关系"""
        return [
            r for r in self.relations
            if r.source_id == entity_id or r.target_id == entity_id
        ]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entities": [e.dict() for e in self.entities],
            "relations": [r.dict() for r in self.relations],
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "confidence_threshold": self.confidence_threshold
        }


class BaseExtractor(ABC):
    """抽取器基类"""

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold

    @abstractmethod
    async def extract_entities(
        self,
        text: str,
        **kwargs
    ) -> List[ExtractedEntity]:
        """抽取实体"""
        pass

    @abstractmethod
    async def extract_relations(
        self,
        text: str,
        entities: List[ExtractedEntity],
        **kwargs
    ) -> List[ExtractedRelation]:
        """抽取关系"""
        pass

    async def extract(
        self,
        text: str,
        extract_relations: bool = True,
        **kwargs
    ) -> ExtractionResult:
        """
        完整抽取流程
        """
        import time
        start_time = time.time()

        # 抽取实体
        entities = await self.extract_entities(text, **kwargs)

        # 过滤低置信度实体
        entities = [
            e for e in entities
            if e.confidence >= self.confidence_threshold
        ]

        # 抽取关系
        relations = []
        if extract_relations and entities:
            relations = await self.extract_relations(text, entities, **kwargs)
            relations = [
                r for r in relations
                if r.confidence >= self.confidence_threshold
            ]

        processing_time = time.time() - start_time

        return ExtractionResult(
            entities=entities,
            relations=relations,
            metadata={"extractor_type": self.__class__.__name__},
            processing_time=processing_time,
            confidence_threshold=self.confidence_threshold
        )

    def create_entity_id(self, text: str, entity_type: str) -> str:
        """创建实体ID"""
        import hashlib
        content = f"{text}_{entity_type}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def create_relation_id(
        self,
        source_id: str,
        target_id: str,
        relation_type: str
    ) -> str:
        """创建关系ID"""
        import hashlib
        content = f"{source_id}_{target_id}_{relation_type}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
