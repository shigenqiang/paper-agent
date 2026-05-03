"""
冲突消解器
Conflict Resolver
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ResolutionStrategy(str, Enum):
    """消解策略"""
    LATEST = "latest"                    # 最新值优先
    MAJORITY = "majority"               # 多数投票
    SOURCE_QUALITY = "source_quality"   # 来源质量
    TRUST_WEIGHT = "trust_weight"       # 信任权重
    COMBINED = "combined"               # 综合策略


@dataclass
class ValueWithSource:
    """带来源的值"""
    value: Any
    source: str
    confidence: float = 1.0
    trust_weight: float = 1.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class ConflictInfo:
    """冲突信息"""
    property_name: str
    values: List[ValueWithSource]
    resolved_value: Any = None
    strategy: ResolutionStrategy = ResolutionStrategy.TRUST_WEIGHT


class ConflictResolver:
    """知识冲突消解器"""

    def __init__(self, default_strategy: ResolutionStrategy = ResolutionStrategy.TRUST_WEIGHT):
        self.default_strategy = default_strategy
        self.strategies = {
            ResolutionStrategy.LATEST: self._resolve_by_latest,
            ResolutionStrategy.MAJORITY: self._resolve_by_majority,
            ResolutionStrategy.SOURCE_QUALITY: self._resolve_by_source_quality,
            ResolutionStrategy.TRUST_WEIGHT: self._resolve_by_trust_weight,
            ResolutionStrategy.COMBINED: self._resolve_by_combined,
        }

    def resolve(
        self,
        conflicting_values: List[ValueWithSource],
        strategy: Optional[ResolutionStrategy] = None
    ) -> Any:
        """解决冲突"""
        if not conflicting_values:
            return None

        if len(conflicting_values) == 1:
            return conflicting_values[0].value

        strategy = strategy or self.default_strategy
        strategy_func = self.strategies.get(strategy, self._resolve_by_trust_weight)

        return strategy_func(conflicting_values)

    def resolve_property_conflicts(
        self,
        entity_properties: Dict[str, List[ValueWithSource]],
        strategy: Optional[ResolutionStrategy] = None
    ) -> Dict[str, Any]:
        """解决实体属性的冲突"""
        resolved = {}

        for prop_name, values in entity_properties.items():
            resolved[prop_name] = self.resolve(values, strategy)

        return resolved

    def _resolve_by_latest(self, values: List[ValueWithSource]) -> Any:
        """基于最新值的策略"""
        # 假设metadata中包含timestamp
        def get_timestamp(v: ValueWithSource) -> int:
            return v.metadata.get("timestamp", 0)

        if all(get_timestamp(v) == 0 for v in values):
            return values[0].value

        latest = max(values, key=get_timestamp)
        return latest.value

    def _resolve_by_majority(self, values: List[ValueWithSource]) -> Any:
        """多数投票策略"""
        value_counts: Dict[Any, int] = {}

        for v in values:
            value_counts[v.value] = value_counts.get(v.value, 0) + 1

        return max(value_counts, key=value_counts.get)

    def _resolve_by_source_quality(self, values: List[ValueWithSource]) -> Any:
        """来源质量策略"""
        source_quality = {
            "official": 1.0,
            "verified": 0.9,
            "peer_reviewed": 0.85,
            "inferred": 0.6,
            "user_generated": 0.3,
        }

        def get_source_quality(v: ValueWithSource) -> float:
            source_type = v.metadata.get("source_type", "inferred")
            return source_quality.get(source_type, 0.5)

        weighted_scores = []
        for v in values:
            quality = get_source_quality(v)
            confidence = v.confidence
            score = quality * confidence
            weighted_scores.append((v.value, score))

        return max(weighted_scores, key=lambda x: x[1])[0]

    def _resolve_by_trust_weight(self, values: List[ValueWithSource]) -> Any:
        """基于信任权重的策略"""
        weighted_scores: Dict[Any, float] = {}

        for v in values:
            score = v.confidence * v.trust_weight
            weighted_scores[v.value] = weighted_scores.get(v.value, 0) + score

        return max(weighted_scores, key=weighted_scores.get)

    def _resolve_by_combined(self, values: List[ValueWithSource]) -> Any:
        """综合策略：结合信任权重、来源质量和一致性"""
        # 步骤1：计算综合分数
        scored_values: Dict[Any, float] = {}

        for v in values:
            # 信任权重分数 (40%)
            trust_score = v.trust_weight * 0.4

            # 来源质量分数 (30%)
            source_quality_scores = {
                "official": 1.0, "verified": 0.9, "peer_reviewed": 0.85,
                "inferred": 0.6, "user_generated": 0.3
            }
            source_type = v.metadata.get("source_type", "inferred")
            source_score = source_quality_scores.get(source_type, 0.5) * 0.3

            # 一致性分数 (30%) - 计算该值与其他值的共识程度
            consistency_score = self._calculate_consistency(v.value, values) * 0.3

            total_score = trust_score + source_score + consistency_score
            scored_values[v.value] = scored_values.get(v.value, 0) + total_score

        return max(scored_values, key=scored_values.get)

    def _calculate_consistency(
        self,
        value: Any,
        all_values: List[ValueWithSource]
    ) -> float:
        """计算一致性分数"""
        same_count = sum(1 for v in all_values if v.value == value)
        return same_count / len(all_values)

    def resolve_with_custom_rule(
        self,
        values: List[ValueWithSource],
        rule_func: Callable[[List[ValueWithSource]], Any]
    ) -> Any:
        """使用自定义规则解决冲突"""
        return rule_func(values)

    def detect_conflicts(
        self,
        properties: Dict[str, List[ValueWithSource]]
    ) -> List[ConflictInfo]:
        """检测冲突"""
        conflicts = []

        for prop_name, values in properties.items():
            unique_values = set(v.value for v in values)

            if len(unique_values) > 1:
                conflict = ConflictInfo(
                    property_name=prop_name,
                    values=values,
                    resolved_value=self.resolve(values)
                )
                conflicts.append(conflict)

        return conflicts

    def merge_entity_properties(
        self,
        base: Dict[str, Any],
        updates: List[Dict[str, Any]],
        strategy: Optional[ResolutionStrategy] = None
    ) -> Dict[str, Any]:
        """合并实体属性"""
        merged = base.copy()

        for update in updates:
            for key, value in update.items():
                if key not in merged:
                    merged[key] = value
                else:
                    # 转换为ValueWithSource格式
                    values = [
                        ValueWithSource(value=merged[key], source="base"),
                        ValueWithSource(value=value, source="update")
                    ]
                    merged[key] = self.resolve(values, strategy)

        return merged
