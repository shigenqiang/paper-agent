"""Self-Consistency Decoding for Knowledge Extraction"""
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
import logging

from src.knowledge.extraction.base_extractor import (
    BaseExtractor,
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult
)

logger = logging.getLogger(__name__)


class SelfConsistencyExtractor:
    """Self-Consistency Decoding 抽取器

    通过多次独立抽取并投票聚合结果，提高抽取的准确性和一致性
    """

    def __init__(
        self,
        base_extractor: BaseExtractor,
        n_samples: int = 5,
        aggregation_method: str = "majority_vote"
    ):
        """
        Args:
            base_extractor: 基础抽取器
            n_samples: 独立抽取的次数
            aggregation_method: 聚合方法: "majority_vote", "weighted_vote", "union"
        """
        self.base_extractor = base_extractor
        self.n_samples = n_samples
        self.aggregation_method = aggregation_method

    async def extract_with_consistency(
        self,
        text: str,
        extract_relations: bool = True,
        **kwargs
    ) -> ExtractionResult:
        """
        使用Self-Consistency进行抽取

        流程:
        1. 独立执行n_samples次抽取
        2. 聚合抽取结果
        3. 返回一致化后的结果
        """
        import time
        start_time = time.time()

        # 执行多次抽取
        extraction_results = []
        for i in range(self.n_samples):
            try:
                result = await self.base_extractor.extract(
                    text,
                    extract_relations=extract_relations,
                    **kwargs
                )
                extraction_results.append(result)
            except Exception as e:
                logger.warning(f"Extraction attempt {i + 1} failed: {e}")

        if not extraction_results:
            return ExtractionResult()

        # 聚合结果
        aggregated_entities = self._aggregate_entities(
            [r.entities for r in extraction_results]
        )

        aggregated_relations = []
        if extract_relations:
            aggregated_relations = self._aggregate_relations(
                [r.relations for r in extraction_results]
            )

        processing_time = time.time() - start_time

        result = ExtractionResult(
            entities=aggregated_entities,
            relations=aggregated_relations,
            processing_time=processing_time,
            confidence_threshold=self.base_extractor.confidence_threshold,
            metadata={
                "method": "self_consistency",
                "n_samples": self.n_samples,
                "aggregation_method": self.aggregation_method,
                "successful_samples": len(extraction_results)
            }
        )

        logger.info(
            f"Self-Consistency extraction completed: "
            f"{len(aggregated_entities)} entities, {len(aggregated_relations)} relations"
        )

        return result

    def _aggregate_entities(
        self,
        entity_lists: List[List[ExtractedEntity]]
    ) -> List[ExtractedEntity]:
        """聚合实体抽取结果"""
        if self.aggregation_method == "union":
            return self._union_entities(entity_lists)
        elif self.aggregation_method == "majority_vote":
            return self._majority_vote_entities(entity_lists)
        elif self.aggregation_method == "weighted_vote":
            return self._weighted_vote_entities(entity_lists)
        else:
            return self._majority_vote_entities(entity_lists)

    def _union_entities(
        self,
        entity_lists: List[List[ExtractedEntity]]
    ) -> List[ExtractedEntity]:
        """并集聚合"""
        entity_map = {}

        for entities in entity_lists:
            for entity in entities:
                key = (entity.text.lower(), entity.type)

                if key not in entity_map:
                    entity_map[key] = entity
                else:
                    # 更新置信度为最大值
                    if entity.confidence > entity_map[key].confidence:
                        entity_map[key] = entity

        return list(entity_map.values())

    def _majority_vote_entities(
        self,
        entity_lists: List[List[ExtractedEntity]]
    ) -> List[ExtractedEntity]:
        """多数投票聚合"""
        entity_votes = defaultdict(list)

        # 统计投票
        for entities in entity_lists:
            for entity in entities:
                key = (entity.text.lower(), entity.type)
                entity_votes[key].append(entity)

        # 应用多数投票
        threshold = len(entity_lists) / 2  # 超过半数
        aggregated_entities = []

        for key, votes in entity_votes.items():
            if len(votes) >= threshold:
                # 平均置信度
                avg_confidence = sum(v.confidence for v in votes) / len(votes)
                # 使用第一个实体的属性
                representative = votes[0]
                representative.confidence = avg_confidence
                aggregated_entities.append(representative)

        return aggregated_entities

    def _weighted_vote_entities(
        self,
        entity_lists: List[List[ExtractedEntity]]
    ) -> List[ExtractedEntity]:
        """加权投票聚合（基于置信度）"""
        entity_scores = defaultdict(float)
        entity_map = {}

        for entities in entity_lists:
            for entity in entities:
                key = (entity.text.lower(), entity.type)
                entity_scores[key] += entity.confidence

                if key not in entity_map:
                    entity_map[key] = entity

        # 选择得分最高的实体
        aggregated_entities = []
        threshold = len(entity_lists) * 0.5 * self.base_extractor.confidence_threshold

        for key, score in entity_scores.items():
            if score >= threshold:
                entity = entity_map[key]
                entity.confidence = min(score / len(entity_lists), 1.0)
                aggregated_entities.append(entity)

        return aggregated_entities

    def _aggregate_relations(
        self,
        relation_lists: List[List[ExtractedRelation]]
    ) -> List[ExtractedRelation]:
        """聚合关系抽取结果"""
        if self.aggregation_method == "union":
            return self._union_relations(relation_lists)
        elif self.aggregation_method == "majority_vote":
            return self._majority_vote_relations(relation_lists)
        elif self.aggregation_method == "weighted_vote":
            return self._weighted_vote_relations(relation_lists)
        else:
            return self._majority_vote_relations(relation_lists)

    def _union_relations(
        self,
        relation_lists: List[List[ExtractedRelation]]
    ) -> List[ExtractedRelation]:
        """并集聚合"""
        relation_map = {}

        for relations in relation_lists:
            for relation in relations:
                key = (
                    relation.source_id,
                    relation.target_id,
                    relation.relation_type
                )

                if key not in relation_map:
                    relation_map[key] = relation
                else:
                    if relation.confidence > relation_map[key].confidence:
                        relation_map[key] = relation

        return list(relation_map.values())

    def _majority_vote_relations(
        self,
        relation_lists: List[List[ExtractedRelation]]
    ) -> List[ExtractedRelation]:
        """多数投票聚合"""
        relation_votes = defaultdict(list)

        for relations in relation_lists:
            for relation in relations:
                key = (
                    relation.source_id,
                    relation.target_id,
                    relation.relation_type
                )
                relation_votes[key].append(relation)

        threshold = len(relation_lists) / 2
        aggregated_relations = []

        for key, votes in relation_votes.items():
            if len(votes) >= threshold:
                avg_confidence = sum(v.confidence for v in votes) / len(votes)
                representative = votes[0]
                representative.confidence = avg_confidence
                aggregated_relations.append(representative)

        return aggregated_relations

    def _weighted_vote_relations(
        self,
        relation_lists: List[List[ExtractedRelation]]
    ) -> List[ExtractedRelation]:
        """加权投票聚合"""
        relation_scores = defaultdict(float)
        relation_map = {}

        for relations in relation_lists:
            for relation in relations:
                key = (
                    relation.source_id,
                    relation.target_id,
                    relation.relation_type
                )
                relation_scores[key] += relation.confidence

                if key not in relation_map:
                    relation_map[key] = relation

        threshold = len(relation_lists) * 0.5 * self.base_extractor.confidence_threshold
        aggregated_relations = []

        for key, score in relation_scores.items():
            if score >= threshold:
                relation = relation_map[key]
                relation.confidence = min(score / len(relation_lists), 1.0)
                aggregated_relations.append(relation)

        return aggregated_relations

    def get_consistency_metrics(
        self,
        extraction_results: List[ExtractionResult]
    ) -> Dict[str, Any]:
        """
        计算一致性指标

        Args:
            extraction_results: 多次抽取的结果列表

        Returns:
            一致性指标字典
        """
        if len(extraction_results) < 2:
            return {}

        # 实体一致性
        entity_sets = [
            {(e.text.lower(), e.type) for e in r.entities}
            for r in extraction_results
        ]

        # 计算Jaccard相似度
        jaccard_scores = []
        for i in range(len(entity_sets)):
            for j in range(i + 1, len(entity_sets)):
                intersection = len(entity_sets[i] & entity_sets[j])
                union = len(entity_sets[i] | entity_sets[j])
                jaccard = intersection / union if union > 0 else 0
                jaccard_scores.append(jaccard)

        # 关系一致性
        relation_sets = [
            {(r.source_id, r.target_id, r.relation_type) for r in r.relations}
            for r in extraction_results
        ]

        relation_jaccard_scores = []
        for i in range(len(relation_sets)):
            for j in range(i + 1, len(relation_sets)):
                intersection = len(relation_sets[i] & relation_sets[j])
                union = len(relation_sets[i] | relation_sets[j])
                jaccard = intersection / union if union > 0 else 0
                relation_jaccard_scores.append(jaccard)

        return {
            "entity_jaccard_mean": sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0,
            "entity_jaccard_std": self._std(jaccard_scores) if jaccard_scores else 0,
            "relation_jaccard_mean": sum(relation_jaccard_scores) / len(relation_jaccard_scores) if relation_jaccard_scores else 0,
            "relation_jaccard_std": self._std(relation_jaccard_scores) if relation_jaccard_scores else 0,
            "n_samples": len(extraction_results)
        }

    def _std(self, values: List[float]) -> float:
        """计算标准差"""
        if not values:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


class ConsistencyAnalyzer:
    """一致性分析器 - 分析抽取结果的质量"""

    @staticmethod
    def analyze_entity_overlap(
        result1: ExtractionResult,
        result2: ExtractionResult
    ) -> Dict[str, Any]:
        """分析两个抽取结果的实体重叠度"""
        entities1 = {(e.text.lower(), e.type) for e in result1.entities}
        entities2 = {(e.text.lower(), e.type) for e in result2.entities}

        intersection = len(entities1 & entities2)
        union = len(entities1 | entities2)

        precision = intersection / len(entities1) if entities1 else 0
        recall = intersection / len(entities2) if entities2 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "intersection": intersection,
            "union": union,
            "jaccard": intersection / union if union > 0 else 0
        }

    @staticmethod
    def analyze_relation_overlap(
        result1: ExtractionResult,
        result2: ExtractionResult
    ) -> Dict[str, Any]:
        """分析两个抽取结果的关系重叠度"""
        relations1 = {
            (r.source_id, r.target_id, r.relation_type)
            for r in result1.relations
        }
        relations2 = {
            (r.source_id, r.target_id, r.relation_type)
            for r in result2.relations
        }

        intersection = len(relations1 & relations2)
        union = len(relations1 | relations2)

        precision = intersection / len(relations1) if relations1 else 0
        recall = intersection / len(relations2) if relations2 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "intersection": intersection,
            "union": union,
            "jaccard": intersection / union if union > 0 else 0
        }
