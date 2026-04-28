"""
Agent链路追踪Mixin测试
"""
import pytest
from src.agents_v2.chain_tracer_mixin import (
    ChainTracerMixin,
    TracedAgentMixin,
    MultiAgentChainTracker,
    get_multi_agent_tracker
)
from src.agents_v2.chain_tracer import ChainPhase, ChainStatus


class MockAgent(ChainTracerMixin):
    """用于测试的Mock Agent"""

    def __init__(self, name: str = "MockAgent"):
        self.name = name
        self.init_chain_tracer(use_global=False)

    def process_sync(self, data: str) -> str:
        """同步处理方法"""
        with self.trace_chain(ChainPhase.EXECUTION, "process_sync") as span:
            span.add_attribute("input_length", len(data))
            return f"processed: {data}"

    async def process_async(self, data: str) -> str:
        """异步处理方法"""
        async with self.trace_async(ChainPhase.GENERATION, "process_async") as span:
            span.add_attribute("input_length", len(data))
            return f"async processed: {data}"


class MockTracedAgent(TracedAgentMixin):
    """带追踪的Mock Agent"""

    def __init__(self, name: str = "MockTracedAgent"):
        self.name = name
        self.init_chain_tracer(use_global=False)

    async def execute(self, task: str) -> str:
        """执行任务"""
        return f"executed: {task}"

    async def failing_execute(self, task: str) -> str:
        """会失败的任务"""
        raise ValueError("Task failed")


class TestChainTracerMixin:
    """测试ChainTracerMixin"""

    def test_init_chain_tracer(self):
        """测试初始化追踪器"""
        agent = MockAgent()
        assert agent.tracer is not None
        assert agent.trace_context is None

    def test_start_end_trace(self):
        """测试开始和结束追踪"""
        agent = MockAgent()

        ctx = agent.start_agent_trace()
        assert ctx is not None
        assert agent.trace_context == ctx

        agent.end_agent_trace()
        assert ctx.status == ChainStatus.COMPLETED

    def test_trace_chain(self):
        """测试链路追踪上下文"""
        agent = MockAgent()
        agent.start_agent_trace()

        with agent.trace_chain(ChainPhase.INPUT, "test_op", input_data={"key": "value"}) as span:
            assert span is not None
            assert span.operation == "test_op"
            assert span.phase == ChainPhase.INPUT

        agent.end_agent_trace()

    def test_nested_trace(self):
        """测试嵌套追踪"""
        agent = MockAgent()
        agent.start_agent_trace()

        with agent.trace_chain(ChainPhase.INPUT, "outer") as outer:
            with agent.trace_chain(ChainPhase.RETRIEVAL, "inner1"):
                pass
            with agent.trace_chain(ChainPhase.GENERATION, "inner2"):
                pass

        spans = agent.get_trace_spans()
        assert len(spans) == 3

        agent.end_agent_trace()

    def test_sync_process_with_trace(self):
        """测试同步处理带追踪"""
        agent = MockAgent()
        agent.start_agent_trace()

        result = agent.process_sync("test data")

        assert result == "processed: test data"

        summary = agent.get_trace_summary()
        assert summary is not None
        assert summary["total_spans"] >= 1

        agent.end_agent_trace()

    def test_get_trace_summary(self):
        """测试获取追踪摘要"""
        agent = MockAgent()
        agent.start_agent_trace()

        with agent.trace_chain(ChainPhase.RETRIEVAL, "op1"):
            pass
        with agent.trace_chain(ChainPhase.GENERATION, "op2"):
            pass

        summary = agent.get_trace_summary()

        assert summary is not None
        assert summary["total_spans"] == 2
        assert "retrieval" in summary["phase_stats"]
        assert "generation" in summary["phase_stats"]

        agent.end_agent_trace()


class TestTracedAgentMixin:
    """测试TracedAgentMixin"""

    @pytest.mark.asyncio
    async def test_traced_execute_success(self):
        """测试成功执行"""
        agent = MockTracedAgent()
        agent.start_agent_trace()

        result = await agent.traced_execute("test task")

        assert result == "executed: test task"

        summary = agent.get_trace_summary()
        assert summary["total_spans"] >= 1

        agent.end_agent_trace()

    @pytest.mark.asyncio
    async def test_traced_execute_failure(self):
        """测试失败执行"""
        agent = MockTracedAgent()
        agent.start_agent_trace()

        # 在关闭前获取摘要
        summary_before = agent.get_trace_summary()
        assert summary_before is not None

        try:
            await agent.traced_execute("failing task")
        except ValueError as e:
            assert "Task failed" in str(e)
            # 异常后立即获取spans（此时trace尚未关闭）
            spans = agent.get_trace_spans()
            assert len(spans) >= 1
            # 验证有span包含error信息
            error_spans = [s for s in spans if s.get("error")]
            assert len(error_spans) >= 1
        finally:
            agent.end_agent_trace(ChainStatus.FAILED)


class TestMultiAgentChainTracker:
    """测试多Agent链路追踪器"""

    def test_create_tracker(self):
        """测试创建追踪器"""
        tracker = MultiAgentChainTracker()
        assert tracker is not None
        assert tracker.get_tracer() is not None

    def test_start_end_trace(self):
        """测试开始和结束追踪"""
        tracker = MultiAgentChainTracker()

        ctx = tracker.start_trace()
        assert ctx is not None

        tracker.end_trace()

        assert ctx.status == ChainStatus.COMPLETED

    def test_track_agent(self):
        """测试追踪Agent"""
        tracker = MultiAgentChainTracker()
        tracker.start_trace()

        with tracker.track_agent("agent1", ChainPhase.INPUT, "process"):
            pass

        with tracker.track_agent("agent2", ChainPhase.RETRIEVAL, "search"):
            pass

        spans = tracker.get_tracer().get_current_context().spans
        assert len(spans) == 2

        tracker.end_trace()

    def test_get_all_traces(self):
        """测试获取所有追踪"""
        tracker = MultiAgentChainTracker()

        for i in range(3):
            tracker.start_trace()
            tracker.end_trace()

        traces = tracker.get_all_traces(limit=10)
        assert len(traces) == 3

    def test_global_tracker(self):
        """测试全局多Agent追踪器"""
        tracker1 = get_multi_agent_tracker()
        tracker2 = get_multi_agent_tracker()

        assert tracker1 is tracker2


class TestIntegration:
    """集成测试"""

    def test_multiple_agents_tracking(self):
        """测试多个Agent追踪"""
        agent1 = MockAgent("Agent1")
        agent2 = MockAgent("Agent2")

        # Agent1开始追踪
        agent1.start_agent_trace()
        with agent1.trace_chain(ChainPhase.INPUT, "agent1_input"):
            pass
        agent1.end_agent_trace()

        # Agent2开始追踪
        agent2.start_agent_trace()
        with agent2.trace_chain(ChainPhase.RETRIEVAL, "agent2_search"):
            pass
        agent2.end_agent_trace()

        # 验证两个Agent独立追踪
        assert agent1.trace_context != agent2.trace_context

    def test_trace_with_tags(self):
        """测试带标签的追踪"""
        agent = MockAgent()
        agent.start_agent_trace()

        with agent.trace_chain(
            ChainPhase.EXECUTION,
            "tagged_op",
            tags={"env": "test", "version": "1.0"}
        ) as span:
            assert span.tags["env"] == "test"
            assert span.tags["version"] == "1.0"

        agent.end_agent_trace()
