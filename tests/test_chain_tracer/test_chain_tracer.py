"""
全链路追踪测试
"""
import pytest
from src.agents_v2.chain_tracer import (
    ChainTracer,
    ChainTraceContext,
    ChainSpan,
    ChainPhase,
    ChainStatus,
    ChainListener,
    LoggingChainListener,
    MetricsChainListener,
    chain_trace,
    trace_phase,
    get_chain_tracer,
    set_chain_tracer
)


class TestChainTraceContext:
    """测试链路追踪上下文"""

    def test_create_context(self):
        """测试创建上下文"""
        ctx = ChainTraceContext()
        assert ctx.trace_id is not None
        assert ctx.trace_id.startswith("tr_")
        assert ctx.status == ChainStatus.RUNNING

    def test_create_context_with_id(self):
        """测试使用指定ID创建上下文"""
        ctx = ChainTraceContext("custom_trace_123")
        assert ctx.trace_id == "custom_trace_123"

    def test_create_span(self):
        """测试创建span"""
        ctx = ChainTraceContext()
        span = ctx.create_span(
            phase=ChainPhase.INPUT,
            operation="process_query",
            input_data={"query": "test"}
        )

        assert span.span_id.startswith("sp_")
        assert span.phase == ChainPhase.INPUT
        assert span.operation == "process_query"
        assert span.trace_id == ctx.trace_id

    def test_span_hierarchy(self):
        """测试span层级关系"""
        ctx = ChainTraceContext()

        # 创建根span
        root = ctx.create_span(ChainPhase.INPUT, "root")
        assert root.depth == 0
        assert root.parent_span_id is None

        # 创建子span
        child = ctx.create_span(ChainPhase.RETRIEVAL, "child", parent_span_id=root.span_id)
        assert child.depth == 1
        assert child.parent_span_id == root.span_id

        # 创建孙子span
        grandchild = ctx.create_span(ChainPhase.GENERATION, "grandchild", parent_span_id=child.span_id)
        assert grandchild.depth == 2
        assert grandchild.parent_span_id == child.span_id

    def test_finish_span(self):
        """测试结束span"""
        ctx = ChainTraceContext()
        span = ctx.create_span(ChainPhase.INPUT, "test")

        ctx.finish_span(span.span_id, output_data={"result": "ok"})

        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.status == ChainStatus.COMPLETED
        assert span.output_data == {"result": "ok"}

    def test_finish_span_with_error(self):
        """测试span错误"""
        ctx = ChainTraceContext()
        span = ctx.create_span(ChainPhase.INPUT, "test")

        ctx.finish_span(span.span_id, error=ValueError("test error"))

        assert span.status == ChainStatus.FAILED
        assert "ValueError" in span.error
        assert "test error" in span.error

    def test_get_summary(self):
        """测试获取摘要"""
        ctx = ChainTraceContext()

        # 创建多个span
        span1 = ctx.create_span(ChainPhase.INPUT, "input")
        ctx.finish_span(span1.span_id)

        span2 = ctx.create_span(ChainPhase.RETRIEVAL, "retrieve")
        ctx.finish_span(span2.span_id)

        summary = ctx.get_summary()

        assert summary["trace_id"] == ctx.trace_id
        assert summary["total_spans"] == 2
        assert "input" in summary["phase_stats"]
        assert "retrieval" in summary["phase_stats"]

    def test_sanitize_sensitive_data(self):
        """测试敏感数据脱敏"""
        ctx = ChainTraceContext()
        span = ctx.create_span(
            ChainPhase.INPUT, "test",
            input_data={
                "password": "secret123",
                "api_key": "key_abc",
                "query": "normal query"
            }
        )

        assert span.input_data["password"] == "***REDACTED***"
        assert span.input_data["api_key"] == "***REDACTED***"
        assert span.input_data["query"] == "normal query"

    def test_truncate_long_values(self):
        """测试截断长数据"""
        ctx = ChainTraceContext()
        span = ctx.create_span(
            ChainPhase.INPUT, "test",
            input_data={"long_text": "x" * 2000}
        )

        assert len(span.input_data["long_text"]) < 2000
        assert span.input_data["long_text"].endswith("...[truncated]")


class TestChainSpan:
    """测试链路跨度"""

    def test_add_tag(self):
        """测试添加标签"""
        ctx = ChainTraceContext()
        span = ctx.create_span(ChainPhase.INPUT, "test")

        span.add_tag("env", "production")
        span.add_tag("version", "1.0")

        assert span.tags["env"] == "production"
        assert span.tags["version"] == "1.0"

    def test_add_attribute(self):
        """测试添加属性"""
        ctx = ChainTraceContext()
        span = ctx.create_span(ChainPhase.INPUT, "test")

        span.add_attribute("count", 42)
        span.add_attribute("ratio", 0.95)

        assert span.attributes["count"] == 42
        assert span.attributes["ratio"] == 0.95

    def test_add_event(self):
        """测试添加事件"""
        ctx = ChainTraceContext()
        span = ctx.create_span(ChainPhase.INPUT, "test")

        span.add_event("checkpoint", checkpoint=1)
        span.add_event("milestone", extra="halfway")

        assert len(span.events) == 2
        assert span.events[0]["checkpoint"] == 1


class TestChainTracer:
    """测试链路追踪器"""

    def test_start_end_trace(self):
        """测试开始和结束追踪"""
        tracer = ChainTracer()

        ctx = tracer.start_trace()
        assert ctx is not None
        assert tracer.get_current_context() == ctx

        tracer.end_trace()
        assert ctx.status == ChainStatus.COMPLETED

    def test_trace_context_manager(self):
        """测试追踪上下文管理器"""
        tracer = ChainTracer()
        tracer.start_trace()

        with tracer.trace(ChainPhase.INPUT, "test_operation") as span:
            assert span.operation == "test_operation"
            assert span.phase == ChainPhase.INPUT

        assert len(tracer.get_current_context().spans) == 1

    def test_nested_traces(self):
        """测试嵌套追踪"""
        tracer = ChainTracer()
        tracer.start_trace()

        with tracer.trace(ChainPhase.INPUT, "outer") as outer_span:
            with tracer.trace(ChainPhase.RETRIEVAL, "inner1") as inner1:
                pass
            with tracer.trace(ChainPhase.GENERATION, "inner2") as inner2:
                pass

        context = tracer.get_current_context()
        assert len(context.spans) == 3

        # 验证层级关系
        spans = list(context.spans.values())
        outer = spans[0]
        inner1 = spans[1]
        inner2 = spans[2]

        assert outer.parent_span_id is None
        assert inner1.parent_span_id == outer.span_id
        assert inner2.parent_span_id == outer.span_id

    def test_auto_start_trace(self):
        """测试自动创建追踪"""
        tracer = ChainTracer()

        with tracer.trace(ChainPhase.INPUT, "test") as span:
            pass

        assert tracer.get_current_context() is not None

    def test_get_trace(self):
        """测试获取指定追踪"""
        tracer = ChainTracer()

        ctx1 = tracer.start_trace("trace_1")
        tracer.end_trace()

        ctx2 = tracer.start_trace("trace_2")
        tracer.end_trace()

        result = tracer.get_trace("trace_1")
        assert result is not None
        assert result.trace_id == "trace_1"

    def test_get_all_traces(self):
        """测试获取所有追踪"""
        tracer = ChainTracer()

        for i in range(3):
            ctx = tracer.start_trace(f"trace_{i}")
            tracer.end_trace()

        traces = tracer.get_all_traces(limit=10)
        assert len(traces) == 3


class TestLoggingChainListener:
    """测试日志监听器"""

    def test_listener_callbacks(self):
        """测试监听器回调"""
        listener = LoggingChainListener()

        ctx = ChainTraceContext()
        span = ctx.create_span(ChainPhase.INPUT, "test")

        # 测试回调不抛出异常
        listener.on_span_start(span)
        listener.on_span_end(span)
        listener.on_trace_start(ctx)
        listener.on_trace_end(ctx)
        listener.on_error(span, ValueError("test"))


class TestMetricsChainListener:
    """测试指标监听器"""

    def test_metrics_collection(self):
        """测试指标收集"""
        listener = MetricsChainListener()

        ctx = ChainTraceContext()

        # 创建并结束多个span
        for i in range(3):
            span = ctx.create_span(ChainPhase.INPUT, f"span_{i}")
            ctx.finish_span(span.span_id)
            listener.on_span_end(span)

        # 创建一个错误span
        error_span = ctx.create_span(ChainPhase.RETRIEVAL, "error_span")
        ctx.finish_span(error_span.span_id, error=ValueError("test"))
        listener.on_error(error_span, ValueError("test"))
        listener.on_span_end(error_span)  # Error spans still count as spans

        metrics = listener.get_metrics()

        assert metrics["total_spans"] == 4
        assert metrics["total_errors"] == 1
        assert metrics["phase_counts"]["input"] == 3


class TestGlobalTracer:
    """测试全局追踪器"""

    def test_get_set_global_tracer(self):
        """测试获取和设置全局追踪器"""
        tracer = ChainTracer()
        set_chain_tracer(tracer)

        result = get_chain_tracer()
        assert result is tracer

    def test_global_chain_trace(self):
        """测试全局追踪上下文"""
        tracer = ChainTracer()
        set_chain_tracer(tracer)

        with chain_trace(ChainPhase.INPUT, "global_test") as span:
            assert span is not None

    def test_trace_phase_decorator(self):
        """测试阶段追踪装饰器"""
        tracer = ChainTracer()
        set_chain_tracer(tracer)

        @trace_phase(ChainPhase.RETRIEVAL)
        def sample_function(x):
            return x * 2

        tracer.start_trace()
        result = sample_function(21)
        tracer.end_trace()

        assert result == 42


class TestChainPhases:
    """测试链路阶段"""

    def test_all_phases(self):
        """测试所有阶段"""
        phases = list(ChainPhase)
        assert len(phases) >= 8
        assert ChainPhase.INPUT in phases
        assert ChainPhase.ROUTING in phases
        assert ChainPhase.PLANNING in phases
        assert ChainPhase.EXECUTION in phases
        assert ChainPhase.RETRIEVAL in phases
        assert ChainPhase.GENERATION in phases
        assert ChainPhase.VALIDATION in phases
        assert ChainPhase.OUTPUT in phases


class TestChainStatus:
    """测试链路状态"""

    def test_all_statuses(self):
        """测试所有状态"""
        statuses = list(ChainStatus)
        assert ChainStatus.STARTED in statuses
        assert ChainStatus.RUNNING in statuses
        assert ChainStatus.COMPLETED in statuses
        assert ChainStatus.FAILED in statuses
        assert ChainStatus.CANCELLED in statuses
