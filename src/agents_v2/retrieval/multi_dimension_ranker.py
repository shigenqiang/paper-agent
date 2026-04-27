"""
多维度排序器 - Multi-Dimension Ranker

功能:
1. 多维度评分
2. 维度权重配置
3. 综合排序
4. 个性化排序

设计原则:
- 可配置的评分维度
- 灵活的权重调整
- 多种排序策略
"""
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class RankingStrategy(str, Enum):
    """排序策略"""
    WEIGHTED_SUM = "weighted_sum"       # 加权求和
    TOPSIS = "topsis"                   # TOPSIS多准则决策
    RRF = "rrf"                         # Reciprocal Rank Fusion
    LEARNING_TO_RANK = "learning_to_rank"  # 学习排序


@dataclass
class RankItem:
    """排序项"""
    item_id: str
    score: float = 0.0
    dimensions: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RankingResult:
    """排序结果"""
    ranked_items: List[RankItem]
    total_score: Dict[str, float]  # item_id -> total_score
    metadata: Dict[str, Any] = field(default_factory=dict)


class DimensionScorer:
    """维度评分器基类"""

    def score(self, item: Dict[str, Any]) -> float:
        """计算维度分数"""
        raise NotImplementedError


class RelevanceScorer(DimensionScorer):
    """相关性评分器"""

    def __init__(self, boost_exact_match: bool = True):
        self.boost_exact_match = boost_exact_match

    def score(self, item: Dict[str, Any], query: str = "") -> float:
        """计算相关性分数

        Args:
            item: 待评分项
            query: 查询字符串

        Returns:
            float: 0.0 - 1.0 的相关性分数
        """
        if not query:
            return 0.5  # 无查询时返回中等分数

        text = item.get("text", "").lower()
        query_terms = set(query.lower().split())

        if not text:
            return 0.0

        # 计算术语覆盖率
        matched = sum(1 for term in query_terms if term in text)
        coverage = matched / len(query_terms) if query_terms else 0

        # 检查精确匹配
        exact_boost = 1.2 if query.lower() in text else 1.0

        # 计算最终分数
        score = coverage * exact_boost
        return min(1.0, score)


class QualityScorer(DimensionScorer):
    """质量评分器"""

    def score(self, item: Dict[str, Any]) -> float:
        """计算质量分数

        Args:
            item: 待评分项

        Returns:
            float: 0.0 - 1.0 的质量分数
        """
        # 从元数据提取质量指标
        metrics = item.get("metadata", {})

        # 来源质量
        source_scores = {
            "arxiv": 0.9,
            "pubmed": 0.85,
            "semantic_scholar": 0.8,
            "web": 0.5
        }
        source = metrics.get("source", "").lower()
        source_score = source_scores.get(source, 0.5)

        # 引用数（归一化）
        citations = metrics.get("citations", 0)
        citation_score = min(1.0, citations / 100)

        # 新鲜度（时间衰减）
        days_old = metrics.get("days_old", 365)
        freshness_score = max(0.3, 1.0 - (days_old / 3650))  # 10年完全衰减到0.3

        # 综合质量分
        quality = (source_score * 0.3 + citation_score * 0.4 + freshness_score * 0.3)
        return min(1.0, quality)


class DiversityScorer(DimensionScorer):
    """多样性评分器"""

    def __init__(self):
        self.selected_topics: Dict[str, int] = defaultdict(int)

    def score(self, item: Dict[str, Any]) -> float:
        """计算多样性分数

        Args:
            item: 待评分项

        Returns:
            float: 0.0 - 1.0 的多样性分数
        """
        topics = item.get("metadata", {}).get("topics", [])

        if not topics:
            return 0.5

        # 计算主题新颖度
        novelty = 0.0
        for topic in topics:
            if self.selected_topics.get(topic, 0) == 0:
                novelty += 1.0
            else:
                novelty += 1.0 / (1 + self.selected_topics[topic])

        # 归一化
        diversity = novelty / len(topics) if topics else 0
        return min(1.0, diversity)

    def update_selection(self, topics: List[str]):
        """更新已选主题"""
        for topic in topics:
            self.selected_topics[topic] += 1


class MultiDimensionRanker:
    """多维度排序器"""

    def __init__(
        self,
        strategy: RankingStrategy = RankingStrategy.WEIGHTED_SUM
    ):
        self.strategy = strategy

        # 维度权重（可配置）
        self.weights = {
            "relevance": 0.4,
            "quality": 0.3,
            "diversity": 0.2,
            "recency": 0.1
        }

        # 维度评分器
        self.scorer_relevance = RelevanceScorer()
        self.scorer_quality = QualityScorer()
        self.scorer_diversity = DiversityScorer()

    def set_weights(self, weights: Dict[str, float]):
        """设置维度权重

        Args:
            weights: 维度权重字典
        """
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total}, normalizing to 1.0")
            self.weights = {k: v / total for k, v in weights.items()}
        else:
            self.weights = weights

    def rank(
        self,
        items: List[Dict[str, Any]],
        query: str = "",
        top_k: int = 10
    ) -> RankingResult:
        """对项目进行排序

        Args:
            items: 待排序项目列表
            query: 查询字符串
            top_k: 返回前k个结果

        Returns:
            RankingResult: 排序结果
        """
        if not items:
            return RankingResult(ranked_items=[], total_score={})

        # 计算每个项目的多维度分数
        rank_items = []
        for item in items:
            rank_item = self._compute_dimensions(item, query)
            rank_items.append(rank_item)

        # 根据策略排序
        if self.strategy == RankingStrategy.WEIGHTED_SUM:
            ranked = self._rank_weighted_sum(rank_items)
        elif self.strategy == RankingStrategy.TOPSIS:
            ranked = self._rank_topsis(rank_items)
        elif self.strategy == RankingStrategy.RRF:
            ranked = self._rank_rrf(rank_items)
        else:
            ranked = self._rank_weighted_sum(rank_items)

        # 限制返回数量
        ranked = ranked[:top_k]

        # 更新多样性追踪
        for item in ranked:
            topics = item.metadata.get("topics", [])
            self.scorer_diversity.update_selection(topics)

        # 构建结果
        total_scores = {item.item_id: item.score for item in ranked}
        return RankingResult(
            ranked_items=ranked,
            total_score=total_scores,
            metadata={
                "strategy": self.strategy.value,
                "weights": self.weights,
                "total_items": len(items)
            }
        )

    def _compute_dimensions(
        self,
        item: Dict[str, Any],
        query: str
    ) -> RankItem:
        """计算项目各维度分数"""
        item_id = item.get("id", item.get("paper_id", str(hash(str(item)))))

        # 各维度评分
        relevance = self.scorer_relevance.score(item, query)
        quality = self.scorer_quality.score(item)
        diversity = self.scorer_diversity.score(item)
        recency = self._compute_recency(item)

        return RankItem(
            item_id=item_id,
            dimensions={
                "relevance": relevance,
                "quality": quality,
                "diversity": diversity,
                "recency": recency
            },
            metadata=item.get("metadata", {})
        )

    def _compute_recency(self, item: Dict[str, Any]) -> float:
        """计算新鲜度分数"""
        days_old = item.get("metadata", {}).get("days_old", 365)
        return max(0.3, 1.0 - (days_old / 3650))

    def _rank_weighted_sum(self, items: List[RankItem]) -> List[RankItem]:
        """加权求和排序"""
        for item in items:
            item.score = sum(
                item.dimensions.get(dim, 0) * self.weights.get(dim, 0)
                for dim in self.weights
            )
        return sorted(items, key=lambda x: x.score, reverse=True)

    def _rank_topsis(self, items: List[RankItem]) -> List[RankItem]:
        """TOPSIS排序"""
        if not items:
            return []

        # 计算正理想解和负理想解
        dimensions = list(self.weights.keys())
        max_values = {}
        min_values = {}

        for dim in dimensions:
            values = [item.dimensions.get(dim, 0) for item in items]
            max_values[dim] = max(values) if values else 1.0
            min_values[dim] = min(values) if values else 0.0

        # 计算每个项目与理想解的距离
        for item in items:
            pos_distance = 0.0
            neg_distance = 0.0

            for dim in dimensions:
                w = self.weights.get(dim, 0)
                v = item.dimensions.get(dim, 0)

                if max_values[dim] != min_values[dim]:
                    pos_distance += w * ((v - max_values[dim]) ** 2)
                    neg_distance += w * ((v - min_values[dim]) ** 2)
                else:
                    pos_distance += w * ((v - max_values[dim]) ** 2)

            pos_distance = pos_distance ** 0.5
            neg_distance = neg_distance ** 0.5

            # 计算相对接近度
            if pos_distance + neg_distance > 0:
                item.score = neg_distance / (pos_distance + neg_distance)
            else:
                item.score = 0.0

        return sorted(items, key=lambda x: x.score, reverse=True)

    def _rank_rrf(self, items: List[RankItem]) -> List[RankItem]:
        """Reciprocal Rank Fusion排序"""
        # 按每个维度排序，获得排名
        dimensions = list(self.weights.keys())
        dimension_ranks = {dim: [] for dim in dimensions}

        for dim in dimensions:
            sorted_by_dim = sorted(
                items,
                key=lambda x: x.dimensions.get(dim, 0),
                reverse=True
            )
            dimension_ranks[dim] = {
                item.item_id: rank
                for rank, item in enumerate(sorted_by_dim)
            }

        # 计算RRF分数
        rrf_k = 60  # RRF常数
        for item in items:
            rrf_score = 0.0
            for dim in dimensions:
                rank = dimension_ranks[dim].get(item.item_id, len(items))
                rrf_score += self.weights.get(dim, 0) / (rrf_k + rank)
            item.score = rrf_score

        return sorted(items, key=lambda x: x.score, reverse=True)


class PersonalizationRanker:
    """个性化排序器"""

    def __init__(self, base_ranker: Optional[MultiDimensionRanker] = None):
        self.base_ranker = base_ranker or MultiDimensionRanker()
        self.user_profiles: Dict[str, Dict[str, float]] = {}

    def set_user_profile(self, user_id: str, preferences: Dict[str, float]):
        """设置用户偏好

        Args:
            user_id: 用户ID
            preferences: 用户偏好字典，如 {"quality": 0.6, "relevance": 0.4}
        """
        self.user_profiles[user_id] = preferences

    def rank_for_user(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        query: str = "",
        top_k: int = 10
    ) -> RankingResult:
        """为用户个性化排序

        Args:
            user_id: 用户ID
            items: 待排序项目
            query: 查询
            top_k: 返回数量

        Returns:
            RankingResult: 排序结果
        """
        # 获取用户偏好
        preferences = self.user_profiles.get(user_id, {})

        if preferences:
            # 使用用户偏好调整权重
            original_weights = self.base_ranker.weights.copy()
            for dim, weight in preferences.items():
                self.base_ranker.weights[dim] = weight

            result = self.base_ranker.rank(items, query, top_k)

            # 恢复原始权重
            self.base_ranker.weights = original_weights
        else:
            result = self.base_ranker.rank(items, query, top_k)

        result.metadata["personalized"] = bool(preferences)
        result.metadata["user_id"] = user_id
        return result


# 便捷函数
def rank_results(
    items: List[Dict[str, Any]],
    query: str = "",
    strategy: str = "weighted_sum",
    top_k: int = 10
) -> RankingResult:
    """便捷排序函数

    Args:
        items: 待排序项目
        query: 查询
        strategy: 排序策略
        top_k: 返回数量

    Returns:
        RankingResult: 排序结果
    """
    ranker = MultiDimensionRanker(RankingStrategy(strategy))
    return ranker.rank(items, query, top_k)


def rank_with_personalization(
    user_id: str,
    items: List[Dict[str, Any]],
    query: str = "",
    preferences: Optional[Dict[str, float]] = None,
    top_k: int = 10
) -> RankingResult:
    """个性化排序便捷函数

    Args:
        user_id: 用户ID
        items: 待排序项目
        query: 查询
        preferences: 用户偏好
        top_k: 返回数量

    Returns:
        RankingResult: 排序结果
    """
    ranker = PersonalizationRanker()
    if preferences:
        ranker.set_user_profile(user_id, preferences)
    return ranker.rank_for_user(user_id, items, query, top_k)