"""
Performance Optimizer Tests
"""
import pytest
import time


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer"""

    def test_record_metric(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer, MetricType

        optimizer = PerformanceOptimizer()
        optimizer.record_metric(MetricType.LATENCY, 100, "ms", tags={"operation": "test"})
        optimizer.record_metric(MetricType.LATENCY, 200, "ms", tags={"operation": "test"})

        stats = optimizer.get_latency_stats()
        assert stats["count"] == 2
        assert stats["avg"] == 150.0

    def test_get_metrics_with_filter(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer, MetricType

        optimizer = PerformanceOptimizer()
        optimizer.record_metric(MetricType.LATENCY, 100, "ms", tags={"op": "A"})
        optimizer.record_metric(MetricType.LATENCY, 200, "ms", tags={"op": "B"})
        optimizer.record_metric(MetricType.THROUGHPUT, 10, "req/s", tags={"op": "A"})

        latency_metrics = optimizer.get_metrics(MetricType.LATENCY)
        assert len(latency_metrics) == 2

        filtered = optimizer.get_metrics(tags={"op": "A"})
        assert len(filtered) == 2

    def test_latency_stats_empty(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()
        stats = optimizer.get_latency_stats()
        assert stats["count"] == 0
        assert stats["avg"] == 0

    def test_find_bottlenecks(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer, MetricType

        optimizer = PerformanceOptimizer()
        # Add high latency metrics
        for _ in range(20):
            optimizer.record_metric(MetricType.LATENCY, 1500, "ms")

        bottlenecks = optimizer.find_bottlenecks()
        assert len(bottlenecks) > 0
        assert any("latency" in b.lower() for b in bottlenecks)

    def test_benchmark_check(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test within target
        passed, status = optimizer.check_benchmark("intent_routing", 40)
        assert passed is True
        assert status == "target_met"

        # Test exceeded
        passed, status = optimizer.check_benchmark("intent_routing", 150)
        assert passed is False
        assert status == "exceeded"

    def test_optimization_suggestions(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer, MetricType

        optimizer = PerformanceOptimizer()
        for _ in range(20):
            optimizer.record_metric(MetricType.LATENCY, 1500, "ms")

        suggestions = optimizer.get_optimization_suggestions()
        assert len(suggestions) > 0

    def test_operation_timer(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer, MetricType

        optimizer = PerformanceOptimizer()
        with optimizer.create_timer("test_operation"):
            time.sleep(0.01)

        stats = optimizer.get_latency_stats("test_operation")
        assert stats["count"] == 1
        assert stats["avg"] > 0

    def test_throughput_stats(self):
        from src.agents_v2.performance.optimizer import PerformanceOptimizer, MetricType

        optimizer = PerformanceOptimizer()
        now = time.time()
        for i in range(5):
            optimizer.record_metric(MetricType.THROUGHPUT, 1, "req/s",
                                   tags={"timestamp": str(now + i)})

        stats = optimizer.get_throughput_stats()
        assert stats["count"] == 5


class TestErrorRecovery:
    """Test Error Recovery System"""

    def test_error_classification(self):
        from src.agents_v2.unified.error_recovery import GranularErrorRecovery, ErrorCategory

        recovery = GranularErrorRecovery()

        # Test timeout classification
        plan = recovery.get_recovery_plan(Exception("timeout error"), {"failed_operation": "search"})
        assert isinstance(plan.steps, list)

    def test_retry_with_backoff_strategy(self):
        from src.agents_v2.unified.error_recovery import GranularErrorRecovery

        recovery = GranularErrorRecovery()
        plan = recovery.get_recovery_plan(
            Exception("timeout"),
            {"failed_operation": "search", "attempt_count": 2}
        )

        assert len(plan.steps) > 0
        step_names = [s.action for s in plan.steps]
        assert "wait" in step_names or "retry" in step_names

    def test_rate_limit_strategy(self):
        from src.agents_v2.unified.error_recovery import GranularErrorRecovery

        recovery = GranularErrorRecovery()
        plan = recovery.get_recovery_plan(
            Exception("rate limit exceeded"),
            {"failed_operation": "search"}
        )

        assert plan is not None

    def test_truncate_context_strategy(self):
        from src.agents_v2.unified.error_recovery import GranularErrorRecovery

        recovery = GranularErrorRecovery()
        plan = recovery.get_recovery_plan(
            Exception("context overflow"),
            {"failed_operation": "search", "max_tokens": 4000}
        )

        assert len(plan.steps) > 0

    def test_strategy_success_rate_recording(self):
        from src.agents_v2.unified.error_recovery import GranularErrorRecovery

        recovery = GranularErrorRecovery()
        recovery.record_recovery_result("retry_with_backoff", True, 1.5)
        recovery.record_recovery_result("retry_with_backoff", False, 0.5)

        # Success rate should be updated
        assert "retry_with_backoff" in recovery._strategy_success_rates


class TestToolVersionManager:
    """Test Tool Version Manager"""

    def test_register_tool(self):
        from src.agents_v2.tools.tool_version import ToolVersionManager

        manager = ToolVersionManager()
        manager.register_tool(
            tool_id="search",
            name="Search",
            tool_func=lambda: None,
            version="1.0.0"
        )

        tool = manager.get_tool("search")
        assert tool is not None
        assert tool.tool_id == "search"

    def test_add_version(self):
        from src.agents_v2.tools.tool_version import ToolVersionManager

        manager = ToolVersionManager()
        manager.register_tool("search", "Search", lambda: None, "1.0.0")
        result = manager.add_version("search", lambda: None, "2.0.0")

        assert result is True
        versions = manager.list_versions("search")
        assert "2.0.0" in versions

    def test_switch_version(self):
        from src.agents_v2.tools.tool_version import ToolVersionManager

        manager = ToolVersionManager()
        manager.register_tool("search", "Search", lambda: None, "1.0.0")
        manager.add_version("search", lambda: None, "2.0.0")

        result = manager.switch_version("search", "2.0.0")
        assert result is True

        current = manager.get_current_version("search")
        assert current.version == "2.0.0"

    def test_record_usage(self):
        from src.agents_v2.tools.tool_version import ToolVersionManager

        manager = ToolVersionManager()
        manager.register_tool("search", "Search", lambda: None, "1.0.0")

        manager.record_usage("search", success=True)
        manager.record_usage("search", success=False)

        info = manager.get_tool_info("search")
        assert info["current_version_info"]["usage_count"] == 2


class TestSkillEvolution:
    """Test Skill Evolution Engine"""

    def test_record_usage(self):
        from src.agents_v2._archive.evolution.skill_evolution import SkillEvolutionEngine

        engine = SkillEvolutionEngine()
        engine.record_usage("writer", success=True, quality=0.8, latency=2.0)

        metrics = engine.get_metrics("writer")
        assert metrics is not None
        assert metrics.total_usage == 1

    def test_get_success_rate(self):
        from src.agents_v2._archive.evolution.skill_evolution import SkillEvolutionEngine

        engine = SkillEvolutionEngine()
        for _ in range(5):
            engine.record_usage("test_skill", success=True, quality=0.8, latency=1.0)
        for _ in range(5):
            engine.record_usage("test_skill", success=False, quality=0.5, latency=3.0)

        rate = engine.get_success_rate("test_skill")
        assert rate == 0.5

    def test_improvement_suggestions(self):
        from src.agents_v2._archive.evolution.skill_evolution import SkillEvolutionEngine

        engine = SkillEvolutionEngine(min_success_rate=0.8)

        # Add a skill with low success rate
        for _ in range(10):
            engine.record_usage("poor_skill", success=False, quality=0.3, latency=10.0)

        suggestions = engine.get_improvement_suggestions()
        assert len(suggestions) > 0


class TestTrustFeedbackSystem:
    """Test Trust Feedback System"""

    def test_record_feedback(self):
        from src.agents_v2._archive.trust.feedback import TrustFeedbackSystem

        system = TrustFeedbackSystem()
        fb_id = system.record_feedback(
            source="user",
            target="agent_1",
            feedback_type="positive",
            quality_score=0.9
        )

        assert fb_id is not None
        trust = system.get_trust_score("agent_1")
        assert trust is not None
        assert trust.score > 0.5

    def test_trust_score_update(self):
        from src.agents_v2._archive.trust.feedback import TrustFeedbackSystem

        system = TrustFeedbackSystem()

        system.record_feedback("user", "agent", "positive", 0.9)
        system.record_feedback("user", "agent", "negative", 0.3)

        trust = system.get_trust_score("agent")
        assert trust.total_feedback == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])