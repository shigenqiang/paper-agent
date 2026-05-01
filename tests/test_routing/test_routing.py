"""
路由模块单元测试

测试路由优化、Agent选择和回退处理功能
"""
import pytest
from src.agents_v2.routing import (
    RoutingOptimizer,
    RouteResult,
    RouteStrategy,
    AgentSelector,
    SelectionCriteria,
    SelectionResult,
    FallbackRouter,
    FallbackResult,
    FallbackStrategy,
)
from src.agents_v2.routing import IntentType


class TestRouteStrategy:
    """RouteStrategy 测试"""

    def test_all_strategies_exist(self):
        """测试所有策略存在"""
        assert RouteStrategy.FAST.value == "fast"
        assert RouteStrategy.ACCURATE.value == "accurate"
        assert RouteStrategy.BALANCED.value == "balanced"
        assert RouteStrategy.COST_AWARE.value == "cost_aware"


class TestRouteResult:
    """RouteResult 测试"""

    def test_route_result_creation(self):
        """测试创建路由结果"""
        result = RouteResult(
            intent=IntentType.LITERATURE_SEARCH,
            strategy=RouteStrategy.BALANCED,
            total_cost=0.5,
            total_time=1.0,
            confidence=0.9
        )
        assert result.intent == IntentType.LITERATURE_SEARCH
        assert result.confidence == 0.9

    def test_to_dict(self):
        """测试转换为字典"""
        result = RouteResult(
            intent=IntentType.LITERATURE_SEARCH,
            strategy=RouteStrategy.BALANCED
        )
        d = result.to_dict()
        assert d["intent"] == "literature_search"
        assert d["strategy"] == "balanced"


class TestRoutingOptimizer:
    """RoutingOptimizer 测试"""

    def setup_method(self):
        self.optimizer = RoutingOptimizer()

    def test_optimize_literature_search(self):
        """测试文献搜索路由优化"""
        result = self.optimizer.optimize(
            intent=IntentType.LITERATURE_SEARCH,
            strategy=RouteStrategy.BALANCED
        )
        assert result.intent == IntentType.LITERATURE_SEARCH
        assert len(result.route) > 0

    def test_optimize_full_paper(self):
        """测试完整论文路由"""
        result = self.optimizer.optimize(
            intent=IntentType.FULL_PAPER,
            strategy=RouteStrategy.ACCURATE
        )
        assert len(result.route) > 2

    def test_optimize_fast_strategy(self):
        """测试快速策略"""
        result = self.optimizer.optimize(
            intent=IntentType.LITERATURE_SEARCH,
            strategy=RouteStrategy.FAST
        )
        # 快速策略应该使用更少的步骤
        assert len(result.route) <= 3

    def test_optimize_unknown_intent(self):
        """测试未知意图"""
        result = self.optimizer.optimize(
            intent=IntentType.UNKNOWN,
            strategy=RouteStrategy.BALANCED
        )
        assert result.confidence == 0.0

    def test_get_available_routes(self):
        """测试获取可用路由"""
        routes = self.optimizer.get_available_routes()
        assert "literature_search" in routes
        assert "full_paper" in routes


class TestSelectionCriteria:
    """SelectionCriteria 测试"""

    def test_default_criteria(self):
        """测试默认标准"""
        criteria = SelectionCriteria()
        assert not criteria.prioritize_speed
        assert not criteria.prioritize_accuracy

    def test_custom_criteria(self):
        """测试自定义标准"""
        criteria = SelectionCriteria(
            prioritize_speed=True,
            max_latency=1.0
        )
        assert criteria.prioritize_speed
        assert criteria.max_latency == 1.0


class TestSelectionResult:
    """SelectionResult 测试"""

    def test_selection_result_creation(self):
        """测试创建选择结果"""
        result = SelectionResult(
            selected_agent="PaperSearchAgent",
            confidence=0.9,
            reasoning="Best match"
        )
        assert result.selected_agent == "PaperSearchAgent"
        assert result.confidence == 0.9

    def test_to_dict(self):
        """测试转换为字典"""
        result = SelectionResult(
            selected_agent="PaperSearchAgent",
            confidence=0.9
        )
        d = result.to_dict()
        assert d["selected_agent"] == "PaperSearchAgent"


class TestAgentSelector:
    """AgentSelector 测试"""

    def setup_method(self):
        self.selector = AgentSelector()

    def test_select_literature_search(self):
        """测试选择文献搜索Agent"""
        result = self.selector.select(
            intent=IntentType.LITERATURE_SEARCH
        )
        assert result.selected_agent in self.selector.list_agents()
        assert result.confidence > 0

    def test_select_with_criteria(self):
        """测试带标准的选择"""
        criteria = SelectionCriteria(prioritize_speed=True)
        result = self.selector.select(
            intent=IntentType.LITERATURE_SEARCH,
            criteria=criteria
        )
        assert result.selected_agent is not None

    def test_select_topic_select(self):
        """测试选题Agent选择"""
        result = self.selector.select(intent=IntentType.TOPIC_SELECT)
        assert result.selected_agent in self.selector.list_agents()

    def test_list_agents(self):
        """测试列出Agent"""
        agents = self.selector.list_agents()
        assert len(agents) > 0
        assert "PaperSearchAgent" in agents

    def test_get_agent_capability(self):
        """测试获取Agent能力"""
        cap = self.selector.get_agent_capability("PaperSearchAgent")
        assert cap is not None
        assert cap.name == "PaperSearchAgent"

    def test_register_agent(self):
        """测试注册Agent"""
        from src.agents_v2.routing.agent_selector import AgentCapability

        new_agent = AgentCapability(
            name="CustomAgent",
            supported_intents=[IntentType.LITERATURE_SEARCH],
            success_rate=0.99
        )
        self.selector.register_agent(new_agent)

        agents = self.selector.list_agents()
        assert "CustomAgent" in agents


class TestFallbackStrategy:
    """FallbackStrategy 测试"""

    def test_all_strategies_exist(self):
        """测试所有回退策略存在"""
        assert FallbackStrategy.DEFAULT_INTENT.value == "default_intent"
        assert FallbackStrategy.SIMPLER_PATH.value == "simpler_path"
        assert FallbackStrategy.LAST_SUCCESS.value == "last_success"


class TestFallbackResult:
    """FallbackResult 测试"""

    def test_fallback_result_creation(self):
        """测试创建回退结果"""
        result = FallbackResult(
            original_intent=IntentType.FULL_PAPER,
            resolved_intent=IntentType.DRAFT_WRITE,
            strategy_used=FallbackStrategy.SIMPLER_PATH,
            success=True
        )
        assert result.original_intent == IntentType.FULL_PAPER
        assert result.resolved_intent == IntentType.DRAFT_WRITE

    def test_to_dict(self):
        """测试转换为字典"""
        result = FallbackResult(
            original_intent=IntentType.FULL_PAPER,
            resolved_intent=IntentType.DRAFT_WRITE,
            strategy_used=FallbackStrategy.DEFAULT_INTENT,
            success=True
        )
        d = result.to_dict()
        assert d["original_intent"] == "full_paper"
        assert d["success"] is True


class TestFallbackRouter:
    """FallbackRouter 测试"""

    def setup_method(self):
        self.router = FallbackRouter()

    def test_route_with_fallback_high_confidence(self):
        """测试高置信度不需要回退"""
        result = self.router.route_with_fallback(
            intent=IntentType.LITERATURE_SEARCH,
            confidence=0.8
        )
        assert result.success
        assert result.resolved_intent == IntentType.LITERATURE_SEARCH

    def test_route_with_fallback_low_confidence(self):
        """测试低置信度触发回退"""
        result = self.router.route_with_fallback(
            intent=IntentType.FULL_PAPER,
            confidence=0.3
        )
        assert result.success
        # 应该回退到更简单的意图
        assert result.original_intent == IntentType.FULL_PAPER

    def test_route_with_error(self):
        """测试错误触发回退"""
        result = self.router.route_with_fallback(
            intent=IntentType.DRAFT_WRITE,
            error_message="Agent timeout"
        )
        assert result.success

    def test_add_rule(self):
        """测试添加规则"""
        self.router.add_rule(
            from_intent=IntentType.FULL_PAPER,
            to_intent=IntentType.OUTLINE_GENERATE,
            strategy=FallbackStrategy.SIMPLER_PATH
        )
        result = self.router.route_with_fallback(
            intent=IntentType.FULL_PAPER,
            confidence=0.4
        )
        assert result.resolved_intent == IntentType.OUTLINE_GENERATE

    def test_record_success(self):
        """测试记录成功"""
        self.router.record_success(IntentType.DRAFT_WRITE, IntentType.OUTLINE_GENERATE)
        stats = self.router.get_stats()
        assert "last_successful" in stats

    def test_record_failure(self):
        """测试记录失败"""
        self.router.record_failure(IntentType.DRAFT_WRITE)
        stats = self.router.get_stats()
        assert stats["failure_counts"].get("draft_write", 0) > 0

    def test_clear_stats(self):
        """测试清除统计"""
        self.router.record_failure(IntentType.DRAFT_WRITE)
        self.router.clear_stats()
        stats = self.router.get_stats()
        assert len(stats["failure_counts"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])