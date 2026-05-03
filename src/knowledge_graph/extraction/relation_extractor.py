"""
学术领域关系抽取
Academic Relation Extraction
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field

from ..schema.academic_kg_schema import (
    Entity, Relation, RelationType, EntityType
)
from .ner import RecognizedEntity


@dataclass
class ExtractedRelation:
    """抽取出的关系"""
    source_text: str
    target_text: str
    type: RelationType
    context: str = ""
    confidence: float = 1.0
    properties: Dict = field(default_factory=dict)


class AcademicRelationExtractor:
    """学术领域关系抽取器"""

    def __init__(self):
        self.relation_patterns = self._init_relation_patterns()
        self.coauthor_patterns = self._init_coauthor_patterns()

    def _init_relation_patterns(self) -> Dict[RelationType, List[str]]:
        """初始化关系模式"""
        return {
            RelationType.CITES: [
                # 显式引用："... showed in [1]" or "... (Smith et al., 2020)"
                r'\[\d+\]',
                r'\([A-Z][a-z]+ et al\.,?\s*\d{4})',
                r'\([A-Z][a-z]+\s+and\s+[A-Z][a-z]+,\s*\d{4}\)',
            ],
            RelationType.AUTHORED_BY: [
                # 隐式作者关系：从文本结构推断
                r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\n',
            ],
            RelationType.HAS_KEYWORD: [
                # 关键词关系
                r'keywords?:\s*([^.\n]+)',
            ],
            RelationType.PUBLISHED_IN: [
                # 发表场所
                r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(\d{4}\)',
            ]
        }

    def _init_coauthor_patterns(self) -> List[str]:
        """初始化合作关系模式"""
        return [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*,\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+and\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[,;]\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[,;]?\s*(?:et al\.?)?',
        ]

    def extract_relations(
        self,
        text: str,
        entities: List[RecognizedEntity]
    ) -> List[ExtractedRelation]:
        """从文本中抽取关系"""
        relations = []

        # 抽取引用关系
        citations = self._extract_citation_relations(text, entities)
        relations.extend(citations)

        # 抽取合作关系
        collaborations = self._extract_collaboration_relations(text, entities)
        relations.extend(collaborations)

        # 抽取关键词关系
        keywords = self._extract_keyword_relations(text, entities)
        relations.extend(keywords)

        # 抽取发表场所关系
        venues = self._extract_venue_relations(text, entities)
        relations.extend(venues)

        return relations

    def _extract_citation_relations(
        self,
        text: str,
        entities: List[RecognizedEntity]
    ) -> List[ExtractedRelation]:
        """抽取引用关系"""
        relations = []

        # 获取论文实体
        paper_entities = [e for e in entities if e.type == EntityType.PAPER]
        if not paper_entities:
            return relations

        # 提取方括号引用 [1], [2,3], [1-5]
        bracket_refs = re.findall(r'\[[\d,\-\s]+\]', text)

        for ref in bracket_refs:
            # 解析引用编号
            ref_nums = self._parse_reference_numbers(ref)
            for num in ref_nums:
                relations.append(ExtractedRelation(
                    source_text="this_paper",
                    target_text=f"ref_{num}",
                    type=RelationType.CITES,
                    context=self._get_citation_context(text, ref),
                    confidence=0.9
                ))

        # 提取作者年份引用 (Smith et al., 2020)
        author_year_refs = re.findall(
            r'([A-Z][a-z]+\s+(?:et al\.|and\s+[A-Z][a-z]+),?\s*\d{4})',
            text
        )

        for ref in author_year_refs:
            relations.append(ExtractedRelation(
                source_text="this_paper",
                target_text=ref,
                type=RelationType.CITES,
                context=self._get_citation_context(text, ref),
                confidence=0.85
            ))

        return relations

    def _extract_collaboration_relations(
        self,
        text: str,
        entities: List[RecognizedEntity]
    ) -> List[ExtractedRelation]:
        """抽取合作关系"""
        relations = []

        # 获取作者实体
        author_entities = [e for e in entities if e.type == EntityType.AUTHOR]

        if len(author_entities) < 2:
            return relations

        # 从作者列表中提取合作关系
        # 查找 "Author1, Author2, ... and AuthorN"
        author_names = [e.text for e in author_entities]

        for i, author1 in enumerate(author_names):
            for author2 in author_names[i + 1:]:
                # 检查是否在文本中相邻出现
                if self._are_authors_adjacent(text, author1, author2):
                    relations.append(ExtractedRelation(
                        source_text=author1,
                        target_text=author2,
                        type=RelationType.COLLABORATES_WITH,
                        confidence=0.8,
                        properties={"type": "coauthor"}
                    ))

        return relations

    def _extract_keyword_relations(
        self,
        text: str,
        entities: List[RecognizedEntity]
    ) -> List[ExtractedRelation]:
        """抽取关键词关系"""
        relations = []

        # 获取论文实体和关键词实体
        paper_entities = [e for e in entities if e.type == EntityType.PAPER]
        keyword_entities = [e for e in entities if e.type == EntityType.KEYWORD]

        if not paper_entities or not keyword_entities:
            return relations

        paper_title = paper_entities[0].text

        for keyword in keyword_entities:
            relations.append(ExtractedRelation(
                source_text=paper_title,
                target_text=keyword.text,
                type=RelationType.HAS_KEYWORD,
                confidence=0.9
            ))

        return relations

    def _extract_venue_relations(
        self,
        text: str,
        entities: List[RecognizedEntity]
    ) -> List[ExtractedRelation]:
        """抽取发表场所关系"""
        relations = []

        # 获取论文和场所实体
        paper_entities = [e for e in entities if e.type == EntityType.PAPER]
        venue_entities = [e for e in entities if e.type == EntityType.VENUE]

        if not paper_entities or not venue_entities:
            return relations

        paper_title = paper_entities[0].text

        for venue in venue_entities:
            relations.append(ExtractedRelation(
                source_text=paper_title,
                target_text=venue.text,
                type=RelationType.PUBLISHED_IN,
                confidence=0.85
            ))

        return relations

    def _parse_reference_numbers(self, ref_str: str) -> List[str]:
        """解析引用编号字符串"""
        numbers = []

        # 移除方括号
        content = ref_str.strip("[]")

        # 分割逗号分隔的编号
        parts = content.split(",")

        for part in parts:
            part = part.strip()
            if "-" in part:
                # 范围，如 "1-5"
                start, end = part.split("-")
                for num in range(int(start), int(end) + 1):
                    numbers.append(str(num))
            else:
                numbers.append(part)

        return numbers

    def _get_citation_context(
        self,
        text: str,
        citation: str,
        window: int = 100
    ) -> str:
        """获取引用上下文"""
        pos = text.find(citation)
        if pos == -1:
            return ""

        start = max(0, pos - window)
        end = min(len(text), pos + len(citation) + window)

        return text[start:end].strip()

    def _are_authors_adjacent(
        self,
        text: str,
        author1: str,
        author2: str,
        max_distance: int = 50
    ) -> bool:
        """检查两个作者是否相邻"""
        pos1 = text.find(author1)
        pos2 = text.find(author2)

        if pos1 == -1 or pos2 == -1:
            return False

        distance = abs(pos2 - pos1)

        return distance < max_distance

    def extract_to_relations(
        self,
        text: str,
        entities: List[RecognizedEntity],
        id_prefix: str = "rel"
    ) -> List[Relation]:
        """将抽取结果转换为Relation列表"""
        extracted = self.extract_relations(text, entities)

        relations = []
        for i, ext in enumerate(extracted):
            # 查找源实体和目标实体的ID
            source_id = self._find_entity_id(ext.source_text, entities)
            target_id = self._find_entity_id(ext.target_text, entities)

            if source_id and target_id:
                relations.append(Relation(
                    source=source_id,
                    target=target_id,
                    type=ext.type,
                    properties={
                        "context": ext.context,
                        "confidence": ext.confidence,
                        **ext.properties
                    }
                ))

        return relations

    def _find_entity_id(
        self,
        text: str,
        entities: List[RecognizedEntity]
    ) -> Optional[str]:
        """查找实体ID"""
        for entity in entities:
            if entity.text == text:
                return f"ent_{entity.start_pos}"
            # 部分匹配
            if text in entity.text or entity.text in text:
                return f"ent_{entity.start_pos}"

        return None

    def extract_citation_network(
        self,
        references_section: str
    ) -> List[Tuple[str, str]]:
        """从参考文献章节提取引用网络"""
        citations = []

        # 解析参考文献列表
        # 格式通常是: [1] Authors. "Title". Venue, Year.
        ref_pattern = r'\[(\d+)\]\s*(.+?)\.\s*"(.+?)"'

        for match in re.finditer(ref_pattern, references_section):
            ref_num = match.group(1)
            authors = match.group(2)
            title = match.group(3)

            # 提取引用中的作者年份信息
            year_match = re.search(r'\((\d{4})\)', match.group(0))
            if year_match:
                year = year_match.group(1)
            else:
                year = "Unknown"

            citations.append((ref_num, f"{authors}, {year}"))

        return citations
