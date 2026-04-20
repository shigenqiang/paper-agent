"""小模型知识抽取器"""
from typing import List, Dict, Any, Optional
import re
import logging

from src.knowledge.extraction.base_extractor import (
    BaseExtractor,
    ExtractedEntity,
    ExtractedRelation
)

logger = logging.getLogger(__name__)


class SmallModelExtractor(BaseExtractor):
    """基于小模型/规则的知识抽取器

    适用于简单、常规的实体和关系抽取
    """

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        entity_patterns: Optional[Dict[str, str]] = None,
        relation_patterns: Optional[Dict[str, str]] = None
    ):
        super().__init__(confidence_threshold)
        self.entity_patterns = entity_patterns or self._get_default_entity_patterns()
        self.relation_patterns = relation_patterns or self._get_default_relation_patterns()

    def _get_default_entity_patterns(self) -> Dict[str, str]:
        """获取默认的实体识别模式"""
        return {
            # 数字
            "数字": r'\d+(?:\.\d+)?(?:%|k|K|m|M|b|B)?',
            # 日期
            "日期": r'\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?',
            # URL
            "URL": r'https?://[^\s]+',
            # 邮箱
            "邮箱": r'[\w.-]+@[\w.-]+\.\w+',
            # 引用格式 [1], [2-3]
            "引用": r'\[\d+(?:-\d+)?\]',
            # 版本号
            "版本": r'v?\d+(?:\.\d+)+',
        }

    def _get_default_relation_patterns(self) -> Dict[str, str]:
        """获取默认的关系识别模式"""
        return {
            "属于": r'(?:是|属于|为)\s*([^\s,。]+)',
            "包含": r'(?:包含|包括|含有)\s*([^\s,。]+)',
            "解决": r'(?:解决|处理|应对)\s*([^\s,。]+)',
            "使用": r'(?:使用|采用|利用)\s*([^\s,。]+)',
            "改进": r'(?:改进|优化|提升)\s*([^\s,。]+)',
        }

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        **kwargs
    ) -> List[ExtractedEntity]:
        """
        使用规则模式抽取实体

        Args:
            text: 输入文本
            entity_types: 要抽取的实体类型，默认使用所有可用类型
        """
        if entity_types is None:
            entity_types = list(self.entity_patterns.keys())

        entities = []

        for entity_type in entity_types:
            if entity_type not in self.entity_patterns:
                continue

            pattern = self.entity_patterns[entity_type]
            matches = re.finditer(pattern, text)

            for match in matches:
                entity_id = self.create_entity_id(match.group(), entity_type)

                entity = ExtractedEntity(
                    id=entity_id,
                    text=match.group(),
                    type=entity_type,
                    confidence=0.7,  # 规则匹配的置信度
                    start_pos=match.start(),
                    end_pos=match.end()
                )

                entities.append(entity)

        logger.info(f"Extracted {len(entities)} entities using small model")
        return entities

    async def extract_relations(
        self,
        text: str,
        entities: List[ExtractedEntity],
        relation_types: Optional[List[str]] = None,
        **kwargs
    ) -> List[ExtractedRelation]:
        """
        使用规则模式抽取关系

        Args:
            text: 输入文本
            entities: 已抽取的实体列表
            relation_types: 要抽取的关系类型
        """
        if relation_types is None:
            relation_types = list(self.relation_patterns.keys())

        relations = []

        # 创建实体文本到ID的映射
        entity_text_map = {e.text: e.id for e in entities}

        for relation_type in relation_types:
            if relation_type not in self.relation_patterns:
                continue

            pattern = self.relation_patterns[relation_type]
            matches = re.finditer(pattern, text)

            for match in matches:
                target_text = match.group(1)

                # 查找目标实体
                if target_text in entity_text_map:
                    target_id = entity_text_map[target_text]

                    # 查找源实体（在匹配之前的实体）
                    source_id = self._find_source_entity(
                        text[:match.start()],
                        entities,
                        target_id
                    )

                    if source_id:
                        relation_id = self.create_relation_id(
                            source_id,
                            target_id,
                            relation_type
                        )

                        relation = ExtractedRelation(
                            id=relation_id,
                            source_id=source_id,
                            target_id=target_id,
                            relation_type=relation_type,
                            confidence=0.6  # 规则匹配的置信度
                        )

                        relations.append(relation)

        logger.info(f"Extracted {len(relations)} relations using small model")
        return relations

    def _find_source_entity(
        self,
        text: str,
        entities: List[ExtractedEntity],
        exclude_id: str
    ) -> Optional[str]:
        """在文本中查找源实体"""
        # 找到在文本中最近的实体
        for entity in sorted(entities, key=lambda e: e.start_pos, reverse=True):
            if entity.id != exclude_id and entity.end_pos <= len(text):
                return entity.id

        return None

    def add_entity_pattern(self, entity_type: str, pattern: str):
        """添加实体识别模式"""
        self.entity_patterns[entity_type] = pattern

    def add_relation_pattern(self, relation_type: str, pattern: str):
        """添加关系识别模式"""
        self.relation_patterns[relation_type] = pattern


class KeywordExtractor(BaseModel):
    """关键词提取器 - 用于识别文本中的关键术语"""

    def __init__(
        self,
        min_keyword_length: int = 2,
        max_keyword_length: int = 10,
        stop_words: Optional[set] = None
    ):
        self.min_keyword_length = min_keyword_length
        self.max_keyword_length = max_keyword_length
        self.stop_words = stop_words or self._get_default_stop_words()

    def _get_default_stop_words(self) -> set:
        """获取默认停用词"""
        return {
            '的', '了', '是', '在', '和', '与', '或', '但是', '因为', '所以',
            '如果', '那么', '这', '那', '这些', '那些', '一个', '一些', '一种',
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'of', 'to', 'in', 'on', 'at',
            'for', 'with', 'by', 'from', 'as', 'and', 'or', 'but', 'not', 'no'
        }

    def extract(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        提取关键词

        Args:
            text: 输入文本
            top_k: 返回前k个关键词

        Returns:
            关键词列表，每个包含text和score
        """
        import re
        from collections import Counter

        # 分词（简化版）
        words = re.findall(r'\b\w+\b', text.lower())

        # 过滤停用词和长度
        filtered_words = [
            word for word in words
            if (len(word) >= self.min_keyword_length and
                len(word) <= self.max_keyword_length and
                word not in self.stop_words)
        ]

        # 统计词频
        word_counts = Counter(filtered_words)

        # 获取top_k
        top_words = word_counts.most_common(top_k)

        # 计算分数（归一化）
        max_count = top_words[0][1] if top_words else 1

        keywords = []
        for word, count in top_words:
            keywords.append({
                "text": word,
                "score": count / max_count,
                "count": count
            })

        return keywords
