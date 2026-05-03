"""
实体对齐器
Entity Aligner
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

from ..schema.academic_kg_schema import Entity, EntityType


@dataclass
class EntityCluster:
    """实体聚类"""
    canonical_entity: Entity
    variants: List[Entity]
    similarity_score: float = 1.0


@dataclass
class AuthorFeatures:
    """作者特征"""
    name: str
    affiliation: Optional[str] = None
    coauthors: List[str] = field(default_factory=list)
    venues: List[str] = field(default_factory=list)
    paper_count: int = 0
    year_range: Tuple[int, int] = (2000, 2026)


class AuthorDisambiguation:
    """作者消歧"""

    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model

        # 名字规范化规则
        self.name_normalization = {
            # 移除中间名首字母
            r'\b([A-Z])\.\s*([A-Z])\.': r'\1\2',
            # 统一连字符
            r'\s*-\s*': '-',
            # 移除学位信息
            r',?\s*(Ph\.?\s*D\.?|M\.?\s*D\.?|Prof\.?)': '',
        }

    def normalize_name(self, name: str) -> str:
        """规范化作者名字"""
        normalized = name.strip()

        for pattern, replacement in self.name_normalization.items():
            normalized = re.sub(pattern, replacement, normalized)

        return normalized.strip()

    def extract_features(self, entity: Entity) -> AuthorFeatures:
        """提取作者特征"""
        return AuthorFeatures(
            name=entity.name,
            affiliation=entity.properties.get("affiliation"),
            coauthors=entity.properties.get("coauthors", []),
            venues=entity.properties.get("venues", []),
            paper_count=entity.properties.get("paper_count", 0),
            year_range=entity.properties.get("year_range", (2000, 2026))
        )

    def calculate_similarity(
        self,
        author1: AuthorFeatures,
        author2: AuthorFeatures
    ) -> float:
        """计算两个作者的相似度"""
        score = 0.0
        weights = {
            "name": 0.4,
            "affiliation": 0.25,
            "coauthors": 0.2,
            "venues": 0.15
        }

        # 名字相似度（规范化后）
        name_sim = self._name_similarity(author1.name, author2.name)
        score += name_sim * weights["name"]

        # 机构相似度
        if author1.affiliation and author2.affiliation:
            aff_sim = self._affiliation_similarity(
                author1.affiliation, author2.affiliation
            )
            score += aff_sim * weights["affiliation"]

        # 合作者重叠
        coauthor_sim = self._coauthor_similarity(
            author1.coauthors, author2.coauthors
        )
        score += coauthor_sim * weights["coauthors"]

        # 发表场所重叠
        venue_sim = self._venue_similarity(author1.venues, author2.venues)
        score += venue_sim * weights["venues"]

        return score

    def _name_similarity(self, name1: str, name2: str) -> float:
        """计算名字相似度"""
        norm1 = self.normalize_name(name1).lower()
        norm2 = self.normalize_name(name2).lower()

        if norm1 == norm2:
            return 1.0

        # 检查姓氏是否相同
        lastname1 = norm1.split()[-1] if norm1 else ""
        lastname2 = norm2.split()[-1] if norm2 else ""

        if lastname1 and lastname1 == lastname2:
            return 0.8

        # 计算编辑距离
        edit_dist = self._levenshtein_distance(norm1, norm2)
        max_len = max(len(norm1), len(norm2))

        if max_len == 0:
            return 0.0

        return 1.0 - edit_dist / max_len

    def _affiliation_similarity(self, aff1: str, aff2: str) -> float:
        """计算机构相似度"""
        aff1_lower = aff1.lower()
        aff2_lower = aff2.lower()

        if aff1_lower == aff2_lower:
            return 1.0

        # 检查关键词重叠
        keywords1 = set(re.findall(r'\b\w+\b', aff1_lower))
        keywords2 = set(re.findall(r'\b\w+\b', aff2_lower))

        overlap = keywords1 & keywords2
        union = keywords1 | keywords2

        if not union:
            return 0.0

        return len(overlap) / len(union)

    def _coauthor_similarity(
        self,
        coauthors1: List[str],
        coauthors2: List[str]
    ) -> float:
        """计算合作者重叠度"""
        if not coauthors1 or not coauthors2:
            return 0.0

        set1 = set(coauthors1)
        set2 = set(coauthors2)

        overlap = set1 & set2
        union = set1 | set2

        return len(overlap) / len(union) if union else 0.0

    def _venue_similarity(
        self,
        venues1: List[str],
        venues2: List[str]
    ) -> float:
        """计算发表场所重叠度"""
        if not venues1 or not venues2:
            return 0.0

        set1 = set(v.lower() for v in venues1)
        set2 = set(v.lower() for v in venues2)

        overlap = set1 & set2
        union = set1 | set2

        return len(overlap) / len(union) if union else 0.0

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def disambiguate(self, authors: List[Entity]) -> List[EntityCluster]:
        """作者消歧，聚类同名作者"""
        if len(authors) < 2:
            return [EntityCluster(canonical_entity=authors[0], variants=[])]

        # 按规范化名字分组
        name_groups: Dict[str, List[Entity]] = {}

        for author in authors:
            norm_name = self.normalize_name(author.name)
            if norm_name not in name_groups:
                name_groups[norm_name] = []
            name_groups[norm_name].append(author)

        # 对每个名字组进行消歧
        clusters = []

        for norm_name, group in name_groups.items():
            if len(group) == 1:
                clusters.append(EntityCluster(
                    canonical_entity=group[0],
                    variants=[]
                ))
            else:
                # 两两比较，计算相似度
                used = set()
                for i, author1 in enumerate(group):
                    if i in used:
                        continue

                    cluster_entities = [author1]
                    used.add(i)

                    author1_features = self.extract_features(author1)

                    for j, author2 in enumerate(group[i + 1:], start=i + 1):
                        if j in used:
                            continue

                        author2_features = self.extract_features(author2)
                        similarity = self.calculate_similarity(
                            author1_features, author2_features
                        )

                        if similarity > 0.7:  # 阈值
                            cluster_entities.append(author2)
                            used.add(j)

                    # 选择paper_count最多的作为canonical
                    canonical = max(
                        cluster_entities,
                        key=lambda e: e.properties.get("paper_count", 0)
                    )

                    clusters.append(EntityCluster(
                        canonical_entity=canonical,
                        variants=[e for e in cluster_entities if e != canonical],
                        similarity_score=0.85
                    ))

        return clusters


class EntityAligner:
    """实体对齐器"""

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold

    def align_entities(
        self,
        entities: List[Entity],
        reference_entities: Optional[List[Entity]] = None
    ) -> List[Tuple[Entity, Optional[Entity]]]:
        """对齐实体"""
        if reference_entities is None:
            # 自对齐：去重合并相似的实体
            return self._self_align(entities)
        else:
            # 与参考集对齐
            return self._reference_align(entities, reference_entities)

    def _self_align(
        self,
        entities: List[Entity]
    ) -> List[Tuple[Entity, Optional[Entity]]]:
        """自对齐"""
        aligned = []
        used_indices = set()

        for i, entity in enumerate(entities):
            if i in used_indices:
                continue

            # 查找相似的实体
            similar = [entity]
            used_indices.add(i)

            for j, other in enumerate(entities[i + 1:], start=i + 1):
                if j in used_indices:
                    continue

                if self._entities_match(entity, other):
                    similar.append(other)
                    used_indices.add(j)

            # 选择最佳实体
            canonical = self._select_canonical(similar)
            aligned.append((canonical, None))

        return aligned

    def _reference_align(
        self,
        entities: List[Entity],
        reference: List[Entity]
    ) -> List[Tuple[Entity, Optional[Entity]]]:
        """与参考集对齐"""
        aligned = []
        ref_dict = {e.name: e for e in reference}

        for entity in entities:
            if entity.name in ref_dict:
                aligned.append((entity, ref_dict[entity.name]))
            else:
                aligned.append((entity, None))

        return aligned

    def _entities_match(self, e1: Entity, e2: Entity) -> bool:
        """判断两个实体是否匹配"""
        if e1.type != e2.type:
            return False

        # 名字完全匹配
        if e1.name == e2.name:
            return True

        # 简单相似度判断
        name_sim = self._name_similarity(e1.name, e2.name)
        return name_sim > self.similarity_threshold

    def _name_similarity(self, name1: str, name2: str) -> float:
        """计算名字相似度"""
        if name1 == name2:
            return 1.0

        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        union = len(words1 | words2)

        return overlap / union if union else 0.0

    def _select_canonical(self, entities: List[Entity]) -> Entity:
        """选择最佳实体作为代表"""
        # 优先选择属性最多的
        return max(entities, key=lambda e: len(e.properties))
