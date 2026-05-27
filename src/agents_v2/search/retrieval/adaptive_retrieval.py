"""
自适应检索器 - Adaptive Retriever

功能:
1. 自适应检索策略选择
2. 动态参数调整
3. 性能监控
4. 策略切换

设计原则:
- 根据查询难度自适应
- 性能驱动的策略选择
- 可配置的决策逻辑
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time


class RetrievalStrategy(str, Enum):
    """检索策略"""
    SPARSE = "sparse"  # 关键词检索
    DENSE = "dense"  # 向量检索
    HYBRID = "hybrid"  # 混合检索
    SEMANTIC = "semantic"  # 语义检索


@dataclass
class QueryComplexity:
    """查询复杂度"""
    level: str  # "simple", "moderate", "complex"
    estimated_tokens: int
    has_entities: bool
    is_temporal: bool
    is_comparative: bool


@dataclass
class RetrievalConfig:
    """检索配置"""
    strategy: RetrievalStrategy
    top_k: int = 10
    similarity_threshold: float = 0.7
    max_retries: int = 3
    timeout: float = 30.0


@dataclass
class RetrievalResult:
    """检索结果"""
    documents: List[Any]
    strategy_used: RetrievalStrategy
    retrieval_time: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdaptiveRetrievalPlanner:
    """自适应检索规划器"""

    def __init__(
        self,
        sparse_retriever: Optional[Callable] = None,
        dense_retriever: Optional[Callable] = None,
        hybrid_retriever: Optional[Callable] = None
    ):
        self.sparse_retriever = sparse_retriever
        self.dense_retriever = dense_retriever
        self.hybrid_retriever = hybrid_retriever

        # 性能历史
        self._performance_history: Dict[RetrievalStrategy, List[float]] = {
            RetrievalStrategy.SPARSE: [],
            RetrievalStrategy.DENSE: [],
            RetrievalStrategy.HYBRID: [],
            RetrievalStrategy.SEMANTIC: []
        }

    def analyze_query_complexity(self, query: str) -> QueryComplexity:
        """分析查询复杂度

        Args:
            query: 用户查询

        Returns:
            QueryComplexity: 查询复杂度评估
        """
        query_lower = query.lower()

        # 简单特征
        word_count = len(query.split())
        char_count = len(query)

        # 检测实体
        entity_indicators = ["谁", "什么", "哪里", "when", "where", "who", "what"]
        has_entities = any(ind in query_lower for ind in entity_indicators)

        # 检测时间相关
        temporal_indicators = ["何时", "年份", "时候", "when", "year", "date"]
        is_temporal = any(ind in query_lower for ind in temporal_indicators)

        # 检测比较
        comparative_indicators = ["对比", "比较", "差异", "vs", "versus", "compare"]
        is_comparative = any(ind in query_lower for ind in comparative_indicators)

        # 判断复杂度级别
        if word_count <= 5 and not has_entities:
            level = "simple"
        elif word_count <= 15 and not is_comparative:
            level = "moderate"
        else:
            level = "complex"

        return QueryComplexity(
            level=level,
            estimated_tokens=word_count,
            has_entities=has_entities,
            is_temporal=is_temporal,
            is_comparative=is_comparative
        )

    def select_strategy(
        self,
        query: str,
        complexity: Optional[QueryComplexity] = None
    ) -> RetrievalStrategy:
        """选择检索策略

        Args:
            query: 用户查询
            complexity: 查询复杂度

        Returns:
            RetrievalStrategy: 选定的检索策略
        """
        complexity = complexity or self.analyze_query_complexity(query)

        # 根据查询特征选择策略
        if complexity.is_comparative:
            return RetrievalStrategy.HYBRID

        if complexity.level == "simple":
            # 简单查询使用稀疏检索
            return RetrievalStrategy.SPARSE

        elif complexity.level == "moderate":
            # 中等复杂度使用混合检索
            return RetrievalStrategy.HYBRID

        else:
            # 复杂查询使用密集检索
            return RetrievalStrategy.DENSE

    def adjust_config(
        self,
        strategy: RetrievalStrategy,
        complexity: QueryComplexity
    ) -> RetrievalConfig:
        """调整检索配置

        Args:
            strategy: 检索策略
            complexity: 查询复杂度

        Returns:
            RetrievalConfig: 调整后的配置
        """
        base_config = RetrievalConfig(strategy=strategy)

        # 根据复杂度调整top_k
        if complexity.level == "simple":
            base_config.top_k = 5
        elif complexity.level == "moderate":
            base_config.top_k = 10
        else:
            base_config.top_k = 15

        # 根据复杂度调整相似度阈值
        if complexity.level == "complex":
            base_config.similarity_threshold = 0.6
        else:
            base_config.similarity_threshold = 0.7

        return base_config

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> RetrievalResult:
        """自适应检索

        Args:
            query: 用户查询
            top_k: 返回结果数

        Returns:
            RetrievalResult: 检索结果
        """
        start_time = time.time()

        # 分析查询
        complexity = self.analyze_query_complexity(query)

        # 选择策略
        strategy = self.select_strategy(query, complexity)

        # 调整配置
        config = self.adjust_config(strategy, complexity)
        if top_k:
            config.top_k = top_k

        # 执行检索
        documents = []
        confidence = 0.5

        try:
            if strategy == RetrievalStrategy.SPARSE and self.sparse_retriever:
                documents = await self.sparse_retriever(query, config.top_k)
                confidence = 0.7
            elif strategy == RetrievalStrategy.DENSE and self.dense_retriever:
                documents = await self.dense_retriever(query, config.top_k)
                confidence = 0.75
            elif strategy == RetrievalStrategy.HYBRID and self.hybrid_retriever:
                documents = await self.hybrid_retriever(query, config.top_k)
                confidence = 0.85
            else:
                # 默认返回空
                documents = []

        except Exception:
            documents = []
            confidence = 0.0

        retrieval_time = time.time() - start_time

        # 记录性能
        self._performance_history[strategy].append(retrieval_time)
        if len(self._performance_history[strategy]) > 100:
            self._performance_history[strategy] = self._performance_history[strategy][-50:]

        return RetrievalResult(
            documents=documents,
            strategy_used=strategy,
            retrieval_time=retrieval_time,
            confidence=confidence,
            metadata={
                "complexity": complexity.level,
                "query_tokens": complexity.estimated_tokens
            }
        )

    def get_strategy_performance(self) -> Dict[str, float]:
        """获取各策略的性能统计"""
        performance = {}

        for strategy, times in self._performance_history.items():
            if times:
                performance[strategy] = sum(times) / len(times)
            else:
                performance[strategy] = 0.0

        return performance


# 便捷函数
async def adaptive_retrieve(
    query: str,
    top_k: int = 10
) -> RetrievalResult:
    """便捷自适应检索函数"""
    planner = AdaptiveRetrievalPlanner()
    return await planner.retrieve(query, top_k)
