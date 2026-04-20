"""实体抽取器"""
from typing import List, Dict, Any, Optional
import logging
from abc import ABC, abstractmethod

from src.knowledge.extraction.base_extractor import BaseExtractor, ExtractedEntity

logger = logging.getLogger(__name__)


class EntityExtractor(ABC):
    """实体抽取器接口"""

    @abstractmethod
    async def extract(self, text: str, **kwargs) -> List[ExtractedEntity]:
        """抽取实体"""
        pass


class DomainSpecificEntityExtractor(EntityExtractor):
    """领域特定的实体抽取器"""

    def __init__(
        self,
        domain: str = "academic",
        entity_types: Optional[List[str]] = None
    ):
        self.domain = domain
        self.entity_types = entity_types or self._get_domain_entity_types()

    def _get_domain_entity_types(self) -> List[str]:
        """获取领域的实体类型"""
        domain_types = {
            "academic": [
                "作者", "机构", "期刊", "会议",
                "方法", "模型", "算法", "技术",
                "任务", "问题", "应用",
                "数据集", "基准", "指标",
                "引用", "参考文献"
            ],
            "medical": [
                "疾病", "症状", "药物", "治疗",
                "解剖", "基因", "蛋白质",
                "检查", "诊断", "预后"
            ],
            "legal": [
                "法律", "法规", "案例", "当事人",
                "法院", "法官", "律师",
                "罪名", "刑罚", "条款"
            ]
        }

        return domain_types.get(self.domain, ["实体"])

    async def extract(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        **kwargs
    ) -> List[ExtractedEntity]:
        """
        抽取领域特定实体

        注意：这是一个示例实现，实际应用中应该：
        1. 使用NER模型（如spaCy, HuggingFace transformers）
        2. 或者调用大语言模型进行抽取
        """
        if entity_types is None:
            entity_types = self.entity_types

        # 这里应该实现实际的抽取逻辑
        # 示例：使用规则或模型进行抽取

        logger.warning(
            f"DomainSpecificEntityExtractor for {self.domain} "
            "is using placeholder implementation"
        )

        return []


class ConceptEntityExtractor(EntityExtractor):
    """概念实体抽取器 - 用于概念图谱"""

    def __init__(self, concept_graph):
        self.concept_graph = concept_graph

    async def extract(
        self,
        text: str,
        **kwargs
    ) -> List[ExtractedEntity]:
        """
        抽取概念实体

        流程:
        1. 将文本与概念图谱中的概念进行匹配
        2. 提取匹配到的概念作为实体
        """
        entities = []

        if self.concept_graph is None:
            return entities

        # 获取所有概念
        concepts = self.concept_graph.nodes.values()

        for concept in concepts:
            # 简单的字符串匹配
            if concept.name.lower() in text.lower():
                entity = ExtractedEntity(
                    id=concept.id,
                    text=concept.name,
                    type="概念",
                    confidence=0.9,
                    properties={
                        "definition": concept.definition,
                        "parent_id": concept.parent_id
                    }
                )
                entities.append(entity)

        logger.info(f"Extracted {len(entities)} concept entities")
        return entities


class PatternBasedEntityExtractor(EntityExtractor):
    """基于模式的实体抽取器"""

    def __init__(self, patterns: Dict[str, str]):
        """
        Args:
            patterns: 实体类型到正则表达式的映射
                {
                    "日期": r'\d{4}-\d{2}-\d{2}',
                    "邮箱": r'[\w.-]+@[\w.-]+\.\w+'
                }
        """
        self.patterns = patterns

    async def extract(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        **kwargs
    ) -> List[ExtractedEntity]:
        """使用正则表达式抽取实体"""
        import re

        if entity_types is None:
            entity_types = list(self.patterns.keys())

        entities = []
        import hashlib

        for entity_type in entity_types:
            if entity_type not in self.patterns:
                continue

            pattern = self.patterns[entity_type]
            matches = re.finditer(pattern, text)

            for match in matches:
                entity_id = hashlib.md5(
                    f"{match.group()}_{entity_type}".encode()
                ).hexdigest()[:16]

                entity = ExtractedEntity(
                    id=entity_id,
                    text=match.group(),
                    type=entity_type,
                    confidence=0.7,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                entities.append(entity)

        logger.info(f"Extracted {len(entities)} entities using patterns")
        return entities

    def add_pattern(self, entity_type: str, pattern: str):
        """添加抽取模式"""
        self.patterns[entity_type] = pattern

    def remove_pattern(self, entity_type: str):
        """移除抽取模式"""
        if entity_type in self.patterns:
            del self.patterns[entity_type]
