"""
动态检索规划器 - Dynamic Retrieval Planner

根据query特点动态选择最优检索策略:
- fact_lookup: 事实性问题 -> sparse(BM25)
- complex_reasoning: 复杂推理 -> hybrid
- exploration: 探索性 -> dense
- comparison: 比较类 -> hybrid+rerank
- definition: 定义类 -> sparse
"""
from src.agents_v2.logging_config import get_logging_logger

import time

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

# Re-export QueryType from query_classifier for backward compatibility
from .query_classifier import QueryType, QueryTypeClassifier

logger = get_logging_logger(__name__)


@dataclass
class RetrievalPlan:
    """检索计划"""
    query_type: QueryType
    primary_strategy: str  # sparse/dense/hybrid
    depth: int            # 检索深度
    max_iterations: int   # 最大迭代次数
    use_rerank: bool      # 是否使用重排序
    query_rewrite: str = "" # 改写后的查询
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalStrategy:
    """检索策略配置"""
    name: str
    vector_weight: float = 0.5    # 向量检索权重
    keyword_weight: float = 0.5   # 关键词检索权重
    top_k: int = 20              # 候选数量
    rerank: bool = True           # 是否重排序
    min_relevance: float = 0.5   # 最小相关性阈值


# 策略配置表
STRATEGY_CONFIGS = {
    QueryType.FACT_LOOKUP: RetrievalStrategy(
        name="sparse",
        vector_weight=0.2,
        keyword_weight=0.8,
        top_k=10,
        rerank=False
    ),
    QueryType.COMPLEX_REASONING: RetrievalStrategy(
        name="hybrid",
        vector_weight=0.6,
        keyword_weight=0.4,
        top_k=30,
        rerank=True
    ),
    QueryType.EXPLORATION: RetrievalStrategy(
        name="dense",
        vector_weight=0.9,
        keyword_weight=0.1,
        top_k=20,
        rerank=False
    ),
    QueryType.COMPARISON: RetrievalStrategy(
        name="hybrid",
        vector_weight=0.5,
        keyword_weight=0.5,
        top_k=30,
        rerank=True
    ),
    QueryType.DEFINITION: RetrievalStrategy(
        name="sparse",
        vector_weight=0.1,
        keyword_weight=0.9,
        top_k=15,
        rerank=False
    )
}


class DynamicRetrievalPlanner:
    """动态检索策略规划器"""

    def __init__(self, llm: Any = None):
        """初始化规划器

        Args:
            llm: 可选的LLM实例，用于query分类
        """
        self.llm = llm
        self.strategy_optimizer = StrategyOptimizer()
        self.query_history: List[Dict] = []
        self._classifier = QueryTypeClassifier()

    async def classify_query(self, query: str) -> QueryType:
        """使用LLM进行query分类

        Args:
            query: 查询字符串

        Returns:
            QueryType: 查询类型
        """
        if self.llm:
            return await self._classify_with_llm(query)
        return self._classifier.classify(query)

    async def _classify_with_llm(self, query: str) -> QueryType:
        """使用LLM进行query分类"""
        prompt = f"""
分析以下查询的特点，选择最合适的检索类型：

Query: {query}

类型说明：
- fact_lookup: 事实查找，如"什么是X"、"X的作者是谁"
- complex_reasoning: 复杂推理，需要多步推导或综合分析
- exploration: 探索性查询，了解新领域或发现新信息
- comparison: 比较类，需要对比多个选项的异同
- definition: 定义类，需要准确解释某个概念

返回格式：只返回类型名称，不要其他内容
"""
        try:
            result = await self.llm.agenerate([prompt])
            response = result.generations[0][0].text.strip().lower()

            type_mapping = {
                "fact_lookup": QueryType.FACT_LOOKUP,
                "complex_reasoning": QueryType.COMPLEX_REASONING,
                "exploration": QueryType.EXPLORATION,
                "comparison": QueryType.COMPARISON,
                "definition": QueryType.DEFINITION
            }

            for key, qtype in type_mapping.items():
                if key in response:
                    return qtype

            return QueryType.UNKNOWN

        except Exception as e:
            logger.warning(f"LLM分类失败，使用规则分类: {e}")
            return self._classifier.classify(query)

    def _classify_with_rules(self, query: str) -> QueryType:
        """使用规则进行query分类（委托给QueryTypeClassifier）"""
        return self._classifier.classify(query)

    async def plan(self, query: str, context: Optional[Dict] = None) -> RetrievalPlan:
        """生成检索计划

        Args:
            query: 查询字符串
            context: 可选的上下文信息

        Returns:
            RetrievalPlan: 检索计划
        """
        start_time = time.time()

        # 1. 分类查询
        query_type = await self.classify_query(query)

        # 2. 获取策略配置
        strategy = STRATEGY_CONFIGS.get(query_type, STRATEGY_CONFIGS[QueryType.FACT_LOOKUP])

        # 3. 根据上下文调整策略
        adjusted_strategy = self._adjust_strategy(strategy, context or {})

        # 4. 记录历史
        self.query_history.append({
            "query": query,
            "query_type": query_type.value,
            "strategy": adjusted_strategy.name,
            "timestamp": time.time()
        })

        # 5. 生成计划
        plan = RetrievalPlan(
            query_type=query_type,
            primary_strategy=adjusted_strategy.name,
            depth=self._get_depth_for_type(query_type),
            max_iterations=self._get_iterations_for_type(query_type),
            use_rerank=adjusted_strategy.rerank,
            metadata={
                "vector_weight": adjusted_strategy.vector_weight,
                "keyword_weight": adjusted_strategy.keyword_weight,
                "top_k": adjusted_strategy.top_k,
                "min_relevance": adjusted_strategy.min_relevance,
                "planning_time": time.time() - start_time
            }
        )

        logger.info(f"检索计划生成: {query_type.value} -> {adjusted_strategy.name}")

        return plan

    def _adjust_strategy(self, strategy: RetrievalStrategy, context: Dict) -> RetrievalStrategy:
        """根据上下文调整策略"""
        adjusted = RetrievalStrategy(
            name=strategy.name,
            vector_weight=strategy.vector_weight,
            keyword_weight=strategy.keyword_weight,
            top_k=strategy.top_k,
            rerank=strategy.rerank,
            min_relevance=strategy.min_relevance
        )

        # 如果有明确的搜索范围限制
        if context.get("limit_torecent"):
            adjusted.top_k = min(adjusted.top_k, 10)

        # 如果用户要求高质量
        if context.get("high_quality"):
            adjusted.min_relevance = 0.7
            adjusted.rerank = True

        # 如果是快速查询
        if context.get("fast_mode"):
            adjusted.top_k = 5
            adjusted.rerank = False

        return adjusted

    def _get_depth_for_type(self, query_type: QueryType) -> int:
        """根据查询类型获取检索深度"""
        depth_map = {
            QueryType.FACT_LOOKUP: 1,
            QueryType.COMPLEX_REASONING: 3,
            QueryType.EXPLORATION: 2,
            QueryType.COMPARISON: 3,
            QueryType.DEFINITION: 1,
            QueryType.UNKNOWN: 2
        }
        return depth_map.get(query_type, 1)

    def _get_iterations_for_type(self, query_type: QueryType) -> int:
        """根据查询类型获取最大迭代次数"""
        iterations_map = {
            QueryType.FACT_LOOKUP: 1,
            QueryType.COMPLEX_REASONING: 3,
            QueryType.EXPLORATION: 2,
            QueryType.COMPARISON: 2,
            QueryType.DEFINITION: 1,
            QueryType.UNKNOWN: 2
        }
        return iterations_map.get(query_type, 1)

    def get_strategy_config(self, plan: RetrievalPlan) -> RetrievalStrategy:
        """获取策略配置"""
        return RetrievalStrategy(
            name=plan.primary_strategy,
            vector_weight=plan.metadata.get("vector_weight", 0.5),
            keyword_weight=plan.metadata.get("keyword_weight", 0.5),
            top_k=plan.metadata.get("top_k", 20),
            rerank=plan.use_rerank,
            min_relevance=plan.metadata.get("min_relevance", 0.5)
        )


class StrategyOptimizer:
    """策略优化器 - 基于历史反馈优化策略"""

    def __init__(self):
        self.success_rates: Dict[str, List[float]] = {}

    def record_result(self, strategy_name: str, success: bool, relevance_score: float):
        """记录策略执行结果

        Args:
            strategy_name: 策略名称
            success: 是否成功
            relevance_score: 相关性分数
        """
        if strategy_name not in self.success_rates:
            self.success_rates[strategy_name] = []

        # 综合成功率和相关性
        score = 1.0 if success else 0.0
        self.success_rates[strategy_name].append(score * 0.5 + relevance_score * 0.5)

        # 保持最近100条记录
        if len(self.success_rates[strategy_name]) > 100:
            self.success_rates[strategy_name] = self.success_rates[strategy_name][-100:]

    def get_best_strategy(self, query_type: QueryType) -> str:
        """获取最佳策略

        Args:
            query_type: 查询类型

        Returns:
            str: 最佳策略名称
        """
        # 简单返回配置表中的默认策略
        strategy = STRATEGY_CONFIGS.get(query_type)
        if strategy:
            return strategy.name
        return "hybrid"


# 便捷函数
async def create_retrieval_plan(query: str, context: Optional[Dict] = None) -> RetrievalPlan:
    """创建检索计划的便捷函数

    Args:
        query: 查询字符串
        context: 可选上下文

    Returns:
        RetrievalPlan: 检索计划
    """
    planner = DynamicRetrievalPlanner()
    return await planner.plan(query, context)
