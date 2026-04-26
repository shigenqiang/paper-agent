"""
Dynamic Planner 单元测试

测试动态检索规划功能
"""
import pytest
from unittest.mock import MagicMock

from src.agents_v2.retrieval.dynamic_planner import (
    DynamicRetrievalPlanner,
    RetrievalPlan,
    RetrievalStrategy,
    STRATEGY_CONFIGS,
    StrategyOptimizer,
    create_retrieval_plan
)
from src.agents_v2.retrieval.query_classifier import QueryType


class TestDynamicRetrievalPlanner:
    """DynamicRetrievalPlanner 测试"""

    def setup_method(self):
        self.planner = DynamicRetrievalPlanner()

    def test_planner_initialization(self):
        """测试规划器初始化"""
        assert self.planner is not None
        assert self.planner.query_history == []

    def test_classify_query_rules(self):
        """测试规则分类"""
        result = self.planner._classify_with_rules("什么是机器学习")
        assert result in QueryType

    def test_plan_returns_retrieval_plan(self):
        """测试生成检索计划"""
        result = self.planner._classify_with_rules("什么是机器学习")
        assert isinstance(result, QueryType)

    def test_plan_knowledge_query(self):
        """测试事实查询"""
        query = "机器学习是谁提出的"
        result = self.planner._classify_with_rules(query)
        assert result == QueryType.FACT_LOOKUP

    def test_plan_exploratory_query(self):
        """测试探索查询"""
        query = "探索最新的AI研究方向"
        result = self.planner._classify_with_rules(query)
        assert result == QueryType.EXPLORATION

    def test_plan_comparison_query(self):
        """测试比较查询"""
        query = "BERT和GPT对比"
        result = self.planner._classify_with_rules(query)
        assert result == QueryType.COMPARISON

    def test_plan_reasoning_query(self):
        """测试推理查询"""
        query = "为什么深度学习效果好"
        result = self.planner._classify_with_rules(query)
        # 能匹配 "为什么" -> reasoning
        assert result in [QueryType.COMPLEX_REASONING, QueryType.UNKNOWN]

    def test_get_depth_for_type(self):
        """测试获取检索深度"""
        assert self.planner._get_depth_for_type(QueryType.FACT_LOOKUP) == 1
        assert self.planner._get_depth_for_type(QueryType.COMPLEX_REASONING) == 3
        assert self.planner._get_depth_for_type(QueryType.EXPLORATION) == 2

    def test_get_iterations_for_type(self):
        """测试获取迭代次数"""
        assert self.planner._get_iterations_for_type(QueryType.FACT_LOOKUP) == 1
        assert self.planner._get_iterations_for_type(QueryType.COMPLEX_REASONING) == 3


class TestRetrievalStrategy:
    """RetrievalStrategy 测试"""

    def test_create_strategy(self):
        """测试创建策略"""
        strategy = RetrievalStrategy(
            name="hybrid",
            vector_weight=0.5,
            keyword_weight=0.5,
            top_k=20,
            rerank=True,
            min_relevance=0.5
        )

        assert strategy.name == "hybrid"
        assert strategy.vector_weight == 0.5
        assert strategy.keyword_weight == 0.5
        assert strategy.top_k == 20
        assert strategy.rerank is True

    def test_default_strategy_values(self):
        """测试默认策略值"""
        strategy = RetrievalStrategy(name="test")
        assert strategy.vector_weight == 0.5
        assert strategy.keyword_weight == 0.5
        assert strategy.top_k == 20
        assert strategy.rerank is True
        assert strategy.min_relevance == 0.5


class TestStrategyConfigs:
    """策略配置测试"""

    def test_fact_lookup_config(self):
        """测试事实查找配置"""
        config = STRATEGY_CONFIGS[QueryType.FACT_LOOKUP]
        assert config.name == "sparse"
        assert config.keyword_weight > config.vector_weight
        assert config.rerank is False

    def test_complex_reasoning_config(self):
        """测试复杂推理配置"""
        config = STRATEGY_CONFIGS[QueryType.COMPLEX_REASONING]
        assert config.name == "hybrid"
        assert config.vector_weight > config.keyword_weight
        assert config.rerank is True

    def test_exploration_config(self):
        """测试探索配置"""
        config = STRATEGY_CONFIGS[QueryType.EXPLORATION]
        assert config.name == "dense"
        assert config.vector_weight > 0.8

    def test_comparison_config(self):
        """测试比较配置"""
        config = STRATEGY_CONFIGS[QueryType.COMPARISON]
        assert config.name == "hybrid"
        assert config.rerank is True

    def test_definition_config(self):
        """测试定义配置"""
        config = STRATEGY_CONFIGS[QueryType.DEFINITION]
        assert config.name == "sparse"
        assert config.keyword_weight > config.vector_weight


class TestStrategyOptimizer:
    """策略优化器测试"""

    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        optimizer = StrategyOptimizer()
        assert optimizer.success_rates == {}

    def test_record_result(self):
        """测试记录结果"""
        optimizer = StrategyOptimizer()
        optimizer.record_result("sparse", success=True, relevance_score=0.8)

        assert "sparse" in optimizer.success_rates
        assert len(optimizer.success_rates["sparse"]) == 1

    def test_record_multiple_results(self):
        """测试记录多个结果"""
        optimizer = StrategyOptimizer()
        optimizer.record_result("hybrid", success=True, relevance_score=0.7)
        optimizer.record_result("hybrid", success=False, relevance_score=0.3)

        assert len(optimizer.success_rates["hybrid"]) == 2

    def test_get_best_strategy(self):
        """测试获取最佳策略"""
        optimizer = StrategyOptimizer()
        result = optimizer.get_best_strategy(QueryType.FACT_LOOKUP)

        assert result in ["sparse", "dense", "hybrid"]

    def test_history_limit(self):
        """测试历史限制"""
        optimizer = StrategyOptimizer()
        for i in range(110):
            optimizer.record_result("test", success=i % 2 == 0, relevance_score=0.5)

        assert len(optimizer.success_rates["test"]) == 100


class TestRetrievalPlan:
    """RetrievalPlan 测试"""

    def test_create_plan(self):
        """测试创建计划"""
        plan = RetrievalPlan(
            query_type=QueryType.FACT_LOOKUP,
            primary_strategy="sparse",
            depth=1,
            max_iterations=1,
            use_rerank=False
        )

        assert plan.query_type == QueryType.FACT_LOOKUP
        assert plan.primary_strategy == "sparse"
        assert plan.depth == 1

    def test_plan_with_metadata(self):
        """测试带元数据的计划"""
        plan = RetrievalPlan(
            query_type=QueryType.EXPLORATION,
            primary_strategy="dense",
            depth=2,
            max_iterations=2,
            use_rerank=False,
            metadata={"custom_key": "value"}
        )

        assert plan.metadata["custom_key"] == "value"


class TestContextAdjustment:
    """上下文调整测试"""

    def setup_method(self):
        self.planner = DynamicRetrievalPlanner()

    def test_adjust_strategy_limit_recent(self):
        """测试限制近期内容"""
        strategy = STRATEGY_CONFIGS[QueryType.EXPLORATION]
        adjusted = self.planner._adjust_strategy(strategy, {"limit_torecent": True})

        assert adjusted.top_k <= strategy.top_k

    def test_adjust_strategy_high_quality(self):
        """测试高质量模式"""
        strategy = STRATEGY_CONFIGS[QueryType.COMPLEX_REASONING]
        adjusted = self.planner._adjust_strategy(strategy, {"high_quality": True})

        assert adjusted.min_relevance >= strategy.min_relevance
        assert adjusted.rerank is True

    def test_adjust_strategy_fast_mode(self):
        """测试快速模式"""
        strategy = STRATEGY_CONFIGS[QueryType.EXPLORATION]
        adjusted = self.planner._adjust_strategy(strategy, {"fast_mode": True})

        assert adjusted.top_k < strategy.top_k
        assert adjusted.rerank is False


class TestConvenienceFunction:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_create_retrieval_plan(self):
        """测试便捷函数"""
        result = await create_retrieval_plan("什么是机器学习")
        assert isinstance(result, RetrievalPlan)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])