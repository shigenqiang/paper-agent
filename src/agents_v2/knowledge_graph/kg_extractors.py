"""
知识图谱信息提取模块

功能:
1. 实体提取 (Entity Extraction)
2. 关系提取 (Relation Extraction)
3. 知识图谱生成 (Knowledge Graph Generation)
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """实体类型"""
    METHOD = "method"
    DATASET = "dataset"
    TASK = "task"
    METRIC = "metric"
    AUTHOR = "author"
    MODEL = "model"
    PAPER = "paper"
    VENUE = "venue"


class RelationType(str, Enum):
    """关系类型"""
    PROPOSED_BY = "proposed_by"
    USES = "uses"
    CITES = "cites"
    COMPARED_WITH = "compared_with"
    PUBLISHED_IN = "published_in"
    AUTHORED_BY = "authored_by"


@dataclass
class ExtractedEntity:
    """提取的实体"""
    name: str
    type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    mentions: List[str] = field(default_factory=list)


@dataclass
class ExtractedRelation:
    """提取的关系"""
    source: str
    target: str
    relation: RelationType
    context: str = ""


@dataclass
class KnowledgeGraphResult:
    """知识图谱生成结果"""
    success: bool
    paper_id: str
    entities: List[ExtractedEntity] = field(default_factory=list)
    relations: List[ExtractedRelation] = field(default_factory=list)
    error: Optional[str] = None


class EntityExtractor:
    """
    实体提取器

    从文本中提取各类实体
    """

    def __init__(self):
        self.entity_patterns = {
            EntityType.METHOD: [
                r"\b(Transformer|BERT|GPT|LSTM|CNN|RNN|GAN|ResNet|ViT)\b",
                r"\b(\w+ attention|\w+ network|\w+ model)\b",
            ],
            EntityType.DATASET: [
                r"\b(ImageNet|COCO|MNIST|SQuAD|Wikipedia)\b",
                r"\b(\w+ dataset|\w+ benchmark)\b",
            ],
            EntityType.TASK: [
                r"\b(classification|detection|segmentation|translation|generation)\b",
                r"\b(\w+ task|\w+ learning)\b",
            ],
            EntityType.METRIC: [
                r"\b(\d+\.?\d*%\s*(accuracy|precision|recall|F1))\b",
                r"\b(BLEU|ROUGE|METEOR|mAP)\b",
            ],
            EntityType.MODEL: [
                r"\b(\w+Net|\w+Model|\w+Former)\b",
            ],
        }

    def extract_from_text(
        self,
        text: str,
        paper_id: str
    ) -> List[ExtractedEntity]:
        """
        从文本中提取实体

        Args:
            text: 输入文本
            paper_id: 论文ID

        Returns:
            提取的实体列表
        """
        entities = []

        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[-1]

                    name = match.strip()
                    if len(name) < 2:
                        continue

                    # 检查是否已存在
                    if not any(e.name == name for e in entities):
                        entities.append(ExtractedEntity(
                            name=name,
                            type=entity_type,
                            mentions=[match]
                        ))

        return entities


class RelationExtractor:
    """
    关系提取器

    从文本和实体中提取关系
    """

    def __init__(self):
        self.relation_patterns = {
            RelationType.PROPOSED_BY: [
                r"we propose",
                r"we present",
                r"we introduce",
                r"proposed (?:method|model|approach)",
            ],
            RelationType.USES: [
                r"uses? (?:the )?(\w+)",
                r"based on (\w+)",
                r"with (\w+)",
            ],
            RelationType.CITES: [
                r"cite[s]? (\w+)",
                r"(\w+) show[s]? that",
            ],
        }

    def extract_from_text(
        self,
        text: str,
        entities: List[ExtractedEntity],
        paper_id: Optional[str]
    ) -> List[ExtractedRelation]:
        """
        从文本中提取关系

        Args:
            text: 输入文本
            entities: 已提取的实体列表
            paper_id: 论文ID

        Returns:
            提取的关系列表
        """
        relations = []
        text_lower = text.lower()

        # 基于模式提取关系
        for rel_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[-1]

                    # 查找匹配的实体
                    for entity in entities:
                        if match.lower() in entity.name.lower():
                            relations.append(ExtractedRelation(
                                source=entity.name,
                                target=paper_id or "",
                                relation=rel_type,
                                context=text[:200]
                            ))

        # 基于共现提取关系
        if len(entities) > 1:
            for i, e1 in enumerate(entities):
                for e2 in entities[i+1:]:
                    if e1.type != e2.type:
                        relations.append(ExtractedRelation(
                            source=e1.name,
                            target=e2.name,
                            relation=RelationType.USES,
                            context="co-occurrence"
                        ))

        return relations


class KnowledgeGraphGenerator:
    """
    知识图谱生成器

    整合实体提取和关系提取
    """

    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()

    async def generate_from_paper(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        full_text: str = ""
    ) -> KnowledgeGraphResult:
        """
        从论文生成知识图谱

        Args:
            paper_id: 论文ID
            title: 论文标题
            abstract: 论文摘要
            full_text: 论文全文

        Returns:
            KnowledgeGraphResult
        """
        try:
            # 合并文本
            combined_text = f"{title} {abstract} {full_text}"

            # 提取实体
            entities = self.entity_extractor.extract_from_text(combined_text, paper_id)

            # 提取关系
            relations = self.relation_extractor.extract_from_text(
                combined_text,
                entities,
                paper_id
            )

            return KnowledgeGraphResult(
                success=True,
                paper_id=paper_id,
                entities=entities,
                relations=relations
            )

        except Exception as e:
            logger.error(f"Knowledge graph generation error: {e}")
            return KnowledgeGraphResult(
                success=False,
                paper_id=paper_id,
                error=str(e)
            )

    def generate_from_texts(
        self,
        texts: List[Tuple[str, str, str]]
    ) -> List[KnowledgeGraphResult]:
        """
        批量生成

        Args:
            texts: [(paper_id, title, text), ...]

        Returns:
            结果列表
        """
        results = []
        for paper_id, title, text in texts:
            result = asyncio.run(self.generate_from_paper(
                paper_id=paper_id,
                title=title,
                abstract=text[:500] if len(text) > 500 else text,
                full_text=text
            ))
            results.append(result)
        return results
