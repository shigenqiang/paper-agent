"""
Agent链路追踪Mixin

将全链路追踪功能集成到现有Agent

使用方式:
    class MyAgent(BaseAgent, ChainTracerMixin):
        def __init__(self, ...):
            super().__init__(...)
            self.init_chain_tracer()

        async def execute(self, task):
            with self.trace_chain("execution", "process_task") as span:
                # 追踪的执行逻辑
                pass
"""

from typing import Any, Dict, Optional, Callable
from functools import wraps

from .chain_tracer import (
    ChainTracer,
    ChainTraceContext,
    ChainPhase,
    ChainStatus,
    ChainSpan,
    LoggingChainListener,
    MetricsChainListener,
    get_chain_tracer,
    set_chain_tracer,
    chain_trace,
    trace_phase as global_trace_phase
)

logger = get_logging_logger(__name__)


class ChainTracerMixin:
    """
    Agent链路追踪Mixin

    为Agent添加全链路追踪能力

    使用方式:
        class MyAgent(BaseAgent, ChainTracerMixin):
            def __init__(self, ...):
                super().__init__(...)
                self.init_chain_tracer()

            async def execute(self, task):
                with self.trace_chain("execution", "process_task") as span:
                    result = await self.process_task(task)
                    span.add_attribute("result_type", type(result).__name__)
                    return result
    """

    def init_chain_tracer(
        self,
        enable_logging: bool = True,
        enable_metrics: bool = True,
        use_global: bool = True
    ):
        """
        初始化链路追踪器

        Args:
            enable_logging: 启用日志监听器
            enable_metrics: 启用指标监听器
            use_global: 使用全局追踪器
        """
        if use_global:
            self._tracer = get_chain_tracer()
        else:
            listeners = []
            if enable_logging:
                listeners.append(LoggingChainListener())
            if enable_metrics:
                listeners.append(MetricsChainListener())
            self._tracer = ChainTracer(listeners)

        self._trace_context: Optional[ChainTraceContext] = None
        self._current_span_id: Optional[str] = None

        logger.info(f"{self.__class__.__name__} chain tracer initialized")

    def start_agent_trace(self, trace_id: Optional[str] = None) -> ChainTraceContext:
        """
        开始Agent级别的追踪

        Args:
            trace_id: 可选的追踪ID

        Returns:
            追踪上下文
        """
        if not hasattr(self, '_tracer'):
            self.init_chain_tracer()

        self._trace_context = self._tracer.start_trace(trace_id)
        return self._trace_context

    def end_agent_trace(self, status: ChainStatus = ChainStatus.COMPLETED):
        """
        结束Agent追踪

        Args:
            status: 结束状态
        """
        if self._tracer and self._trace_context:
            self._tracer.end_trace(status)

    def trace_chain(
        self,
        phase: ChainPhase,
        operation: str,
        tags: Optional[Dict[str, str]] = None,
        input_data: Optional[Dict[str, Any]] = None
    ):
        """
        链路追踪上下文管理器

        Args:
            phase: 链路阶段
            operation: 操作名称
            tags: 标签
            input_data: 输入数据

        Returns:
            上下文管理器
        """
        if not hasattr(self, '_tracer'):
            self.init_chain_tracer()

        return self._tracer.trace(phase, operation, tags, input_data)

    def trace_phase(self, phase: ChainPhase):
        """
        阶段追踪装饰器工厂

        Args:
            phase: 链路阶段

        用法:
            @self.trace_phase(ChainPhase.RETRIEVAL)
            async def retrieve(self, query):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not hasattr(self, '_tracer'):
                    self.init_chain_tracer()

                with self._tracer.trace(phase, func.__name__) as span:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.set_error(e)
                        raise

            return wrapper
        return decorator

    async def trace_async(
        self,
        phase: ChainPhase,
        operation: str,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        异步链路追踪上下文管理器

        Args:
            phase: 链路阶段
            operation: 操作名称
            tags: 标签

        用法:
            async with self.trace_async(ChainPhase.RETRIEVAL, "search"):
                results = await self.search(query)
        """
        if not hasattr(self, '_tracer'):
            self.init_chain_tracer()

        return self._tracer.trace(phase, operation, tags)

    def get_trace_summary(self) -> Optional[Dict[str, Any]]:
        """获取当前追踪摘要"""
        if self._trace_context:
            return self._trace_context.get_summary()
        return None

    def get_trace_spans(self) -> Optional[List[Dict[str, Any]]]:
        """获取当前追踪的所有span"""
        if self._trace_context:
            return [s.to_dict() for s in self._trace_context.spans.values()]
        return None

    @property
    def tracer(self) -> Optional[ChainTracer]:
        """获取追踪器"""
        return getattr(self, '_tracer', None)

    @property
    def trace_context(self) -> Optional[ChainTraceContext]:
        """获取追踪上下文"""
        return getattr(self, '_trace_context', None)


class TracedAgentMixin(ChainTracerMixin):
    """
    带追踪功能的Agent Mixin

    自动为Agent的execute方法添加追踪
    """

    async def traced_execute(self, task: Any, phase: ChainPhase = ChainPhase.EXECUTION) -> Any:
        """
        带追踪的执行方法

        Args:
            task: 任务
            phase: 执行阶段

        Returns:
            执行结果
        """
        operation_name = f"{self.__class__.__name__}.execute"

        with self.trace_chain(phase, operation_name, input_data={"task": str(task)[:200]}) as span:
            try:
                result = await self.execute(task)
                span.add_attribute("success", True)
                return result
            except Exception as e:
                span.add_attribute("success", False)
                span.add_attribute("error", str(e))
                raise


class MultiAgentChainTracker:
    """
    多Agent链路追踪器

    用于追踪多个Agent协作的场景
    """

    def __init__(self):
        self._tracer = ChainTracer([
            LoggingChainListener(),
            MetricsChainListener()
        ])
        self._agent_traces: Dict[str, ChainTraceContext] = {}

    def start_trace(self, trace_id: Optional[str] = None) -> ChainTraceContext:
        """开始追踪"""
        return self._tracer.start_trace(trace_id)

    def end_trace(self, status: ChainStatus = ChainStatus.COMPLETED):
        """结束追踪"""
        self._tracer.end_trace(status)

    def get_tracer(self) -> ChainTracer:
        """获取追踪器"""
        return self._tracer

    def track_agent(
        self,
        agent_name: str,
        phase: ChainPhase,
        operation: str
    ):
        """
        追踪Agent执行

        Args:
            agent_name: Agent名称
            phase: 执行阶段
            operation: 操作名称
        """
        return self._tracer.trace(phase, operation, tags={"agent": agent_name})

    def get_all_traces(self, limit: int = 100) -> list:
        """获取所有追踪"""
        return self._tracer.get_all_traces(limit)


# 全局多Agent追踪器
_global_multi_tracker: Optional[MultiAgentChainTracker] = None


def get_multi_agent_tracker() -> MultiAgentChainTracker:
    """获取全局多Agent追踪器"""
    global _global_multi_tracker
    if _global_multi_tracker is None:
        _global_multi_tracker = MultiAgentChainTracker()
    return _global_multi_tracker
