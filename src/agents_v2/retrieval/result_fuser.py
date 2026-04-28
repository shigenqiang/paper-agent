"""
结果融合器 - Result Fusion

功能:
1. 多源检索结果融合
2. 权重优化
3. 分数归一化
4. 融合评估

设计原则:
- 多种融合策略支持
- 可配置的权重
- 公平性保证
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class FusionStrategy(str, Enum):
    """融合策略"""
    WEIGHTED_SUM = "weighted_sum"  # 加权求和
    RRF = "rrf"  # Reciprocal Rank Fusion
    COMBINATION = "combination"  # 组合评分
    SCORE_AVERAGE = "score_average"  # 分数平均
    VOTE = "vote"  # 投票


@dataclass
class ScoredItem:
    """带分数的项"""
    id: str
    score: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusionConfig:
    """融合配置"""
    strategy: FusionStrategy = FusionStrategy.WEIGHTED_SUM
    weights: Dict[str, float] = field(default_factory=dict)  # source -> weight
    rrf_k: int = 60  # RRF参数
    normalization: str = "min_max"  # 归一化方法


class ResultFuser:
    """结果融合器"""

    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()

    def fuse(
        self,
        results_by_source: Dict[str, List[ScoredItem]]
    ) -> List[ScoredItem]:
        """融合多源结果

        Args:
            results_by_source: {source_name: [ScoredItem]}

        Returns:
            List[ScoredItem]: 融合后的结果，按分数降序
        """
        if not results_by_source:
            return []

        # 归一化各来源分数
        normalized = self._normalize_all(results_by_source)

        # 根据策略融合
        if self.config.strategy == FusionStrategy.WEIGHTED_SUM:
            return self._weighted_sum_fusion(normalized)
        elif self.config.strategy == FusionStrategy.RRF:
            return self._rrf_fusion(results_by_source)
        elif self.config.strategy == FusionStrategy.SCORE_AVERAGE:
            return self._score_average_fusion(normalized)
        elif self.config.strategy == FusionStrategy.COMBINATION:
            return self._combination_fusion(normalized)
        else:
            return self._weighted_sum_fusion(normalized)

    def _normalize_all(
        self,
        results_by_source: Dict[str, List[ScoredItem]]
    ) -> Dict[str, List[ScoredItem]]:
        """归一化所有来源的分数"""
        normalized = {}

        for source, items in results_by_source.items():
            if not items:
                normalized[source] = []
                continue

            scores = [item.score for item in items]
            min_score = min(scores)
            max_score = max(scores)

            if max_score == min_score:
                # 如果所有分数相同，设为1
                normalized_items = [
                    ScoredItem(
                        id=item.id,
                        score=1.0,
                        source=item.source,
                        metadata=item.metadata
                    )
                    for item in items
                ]
            else:
                # Min-Max归一化
                normalized_items = [
                    ScoredItem(
                        id=item.id,
                        score=(item.score - min_score) / (max_score - min_score),
                        source=item.source,
                        metadata=item.metadata
                    )
                    for item in items
                ]

            normalized[source] = normalized_items

        return normalized

    def _weighted_sum_fusion(
        self,
        normalized: Dict[str, List[ScoredItem]]
    ) -> List[ScoredItem]:
        """加权求和融合"""
        # 合并所有项
        all_items: Dict[str, List[Tuple[float, float]]] = {}  # id -> [(normalized_score, weight)]

        for source, items in normalized.items():
            weight = self.config.weights.get(source, 1.0)
            for item in items:
                if item.id not in all_items:
                    all_items[item.id] = []
                all_items[item.id].append((item.score, weight))

        # 计算加权分数
        fused_scores = []
        for item_id, score_weight_pairs in all_items.items():
            if len(score_weight_pairs) == 1:
                score, weight = score_weight_pairs[0]
                fused_score = score * weight
            else:
                total_weight = sum(w for _, w in score_weight_pairs)
                weighted_sum = sum(s * w for s, w in score_weight_pairs)
                fused_score = weighted_sum / total_weight

            # 获取元数据（从第一个项）
            metadata = {}
            for source, items in normalized.items():
                for item in items:
                    if item.id == item_id:
                        metadata = item.metadata
                        break

            fused_scores.append(ScoredItem(
                id=item_id,
                score=fused_score,
                source="fused",
                metadata=metadata
            ))

        # 按分数降序排序
        fused_scores.sort(key=lambda x: x.score, reverse=True)
        return fused_scores

    def _rrf_fusion(
        self,
        results_by_source: Dict[str, List[ScoredItem]]
    ) -> List[ScoredItem]:
        """Reciprocal Rank Fusion"""
        k = self.config.rrf_k
        fused_scores: Dict[str, float] = {}

        for source, items in results_by_source.items():
            weight = self.config.weights.get(source, 1.0)

            for rank, item in enumerate(items, 1):
                rrf_score = 1.0 / (k + rank)
                if item.id not in fused_scores:
                    fused_scores[item.id] = 0.0
                fused_scores[item.id] += weight * rrf_score

        # 转换为列表
        fused_items = [
            ScoredItem(
                id=item_id,
                score=score,
                source="fused"
            )
            for item_id, score in fused_scores.items()
        ]

        # 按分数降序排序
        fused_items.sort(key=lambda x: x.score, reverse=True)
        return fused_items

    def _score_average_fusion(
        self,
        normalized: Dict[str, List[ScoredItem]]
    ) -> List[ScoredItem]:
        """分数平均融合"""
        all_items: Dict[str, List[float]] = {}

        for source, items in normalized.items():
            for item in items:
                if item.id not in all_items:
                    all_items[item.id] = []
                all_items[item.id].append(item.score)

        fused_scores = []
        for item_id, scores in all_items.items():
            avg_score = sum(scores) / len(scores)
            fused_scores.append(ScoredItem(
                id=item_id,
                score=avg_score,
                source="fused"
            ))

        fused_scores.sort(key=lambda x: x.score, reverse=True)
        return fused_scores

    def _combination_fusion(
        self,
        normalized: Dict[str, List[ScoredItem]]
    ) -> List[ScoredItem]:
        """组合评分融合 - 结合RRF和加权求和"""
        rrf_results = {k: list(v) for k, v in normalized.items()}
        rrf_fused = self._rrf_fusion(rrf_results)
        rrf_scores = {item.id: item.score for item in rrf_fused}

        weighted_fused = self._weighted_sum_fusion(normalized)
        weighted_scores = {item.id: item.score for item in weighted_fused}

        # 组合分数
        all_ids = set(rrf_scores.keys()) | set(weighted_scores.keys())
        fused_items = []

        for item_id in all_ids:
            rrf_score = rrf_scores.get(item_id, 0)
            weighted_score = weighted_scores.get(item_id, 0)
            # 组合: 0.5 * RRF + 0.5 * Weighted
            combo_score = 0.5 * rrf_score + 0.5 * weighted_score
            fused_items.append(ScoredItem(
                id=item_id,
                score=combo_score,
                source="fused"
            ))

        fused_items.sort(key=lambda x: x.score, reverse=True)
        return fused_items


class WeightOptimizer:
    """权重优化器"""

    def __init__(self):
        self.fuser = ResultFuser()

    def optimize_weights(
        self,
        results_by_source: Dict[str, List[ScoredItem]],
        relevance_labels: Dict[str, float],  # id -> relevance score
        metric: str = "ndcg"
    ) -> Dict[str, float]:
        """优化融合权重

        Args:
            results_by_source: 多源结果
            relevance_labels: 相关性标签
            metric: 评估指标

        Returns:
            Dict[str, float]: 优化后的权重
        """
        # 简单实现：使用各来源的总体平均分数作为初始权重
        weights = {}

        for source, items in results_by_source.items():
            if items:
                avg_score = sum(item.score for item in items) / len(items)
                weights[source] = avg_score
            else:
                weights[source] = 0.1

        # 归一化权重
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights


# 便捷函数
def fuse_results(
    results_by_source: Dict[str, List[ScoredItem]],
    strategy: FusionStrategy = FusionStrategy.WEIGHTED_SUM,
    weights: Optional[Dict[str, float]] = None
) -> List[ScoredItem]:
    """便捷结果融合函数"""
    config = FusionConfig(strategy=strategy, weights=weights or {})
    fuser = ResultFuser(config)
    return fuser.fuse(results_by_source)
