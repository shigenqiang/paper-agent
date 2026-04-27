"""
Workflow Observability - LangGraph 工作流可观测性

提供：
1. 每节点计时和性能分析
2. Token 使用估算
3. 错误率监控
4. 成本估算
5. 结构化日志
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NodeSpan:
    """节点执行记录"""
    node_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "running"  # running, completed, failed
    error: Optional[str] = None
    token_estimate: int = 0
    paper_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowTrace:
    """工作流完整追踪"""
    trace_id: str = ""
    user_id: str = ""
    session_id: str = ""
    query: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    total_duration_ms: float = 0.0
    nodes: List[NodeSpan] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    errors: List[str] = field(default_factory=list)


class WorkflowTracer:
    """工作流追踪器

    类似 LangSmith 的轻量级本地追踪实现。
    """

    def __init__(self):
        self._active_span: Optional[NodeSpan] = None
        self._spans: List[NodeSpan] = []
        self._trace: Optional[WorkflowTrace] = None
        self._token_rates = {
            "input_per_1k": 0.01,   # $0.01 / 1K input tokens
            "output_per_1k": 0.03,  # $0.03 / 1K output tokens
        }

    def start_trace(self, query: str, user_id: str = "", session_id: str = "") -> WorkflowTrace:
        """开始一次工作流执行追踪"""
        import uuid
        self._trace = WorkflowTrace(
            trace_id=str(uuid.uuid4())[:8],
            user_id=user_id,
            session_id=session_id,
            query=query,
            start_time=time.time(),
        )
        self._spans = []
        return self._trace

    def start_node(self, node_name: str) -> NodeSpan:
        """开始记录一个节点执行"""
        span = NodeSpan(node_name=node_name, start_time=time.time())
        self._active_span = span
        self._spans.append(span)
        logger.info(f"[Trace] 节点 {node_name} 开始执行")
        return span

    def end_node(self, status: str = "completed", error: Optional[str] = None):
        """结束当前节点记录"""
        if not self._active_span:
            return

        self._active_span.end_time = time.time()
        self._active_span.duration_ms = (
            self._active_span.end_time - self._active_span.start_time
        ) * 1000
        self._active_span.status = status
        self._active_span.error = error

        if status == "completed":
            logger.info(
                f"[Trace] 节点 {self._active_span.node_name} 完成, "
                f"耗时 {self._active_span.duration_ms:.1f}ms"
            )
        else:
            logger.warning(
                f"[Trace] 节点 {self._active_span.node_name} 失败: {error}"
            )

        self._active_span = None

    def record_tokens(self, count: int):
        """记录当前节点的 token 估算"""
        if self._active_span:
            self._active_span.token_estimate = count

    def record_paper_count(self, count: int):
        """记录当前节点处理的论文数量"""
        if self._active_span:
            self._active_span.paper_count = count

    def end_trace(self) -> WorkflowTrace:
        """结束追踪并返回报告"""
        if not self._trace:
            return WorkflowTrace()

        self._trace.end_time = time.time()
        self._trace.total_duration_ms = (
            self._trace.end_time - self._trace.start_time
        ) * 1000
        self._trace.nodes = list(self._spans)
        self._trace.total_tokens = sum(s.token_estimate for s in self._spans)
        self._trace.total_cost_usd = self._estimate_cost()
        self._trace.errors = [
            s.error for s in self._spans if s.error
        ]

        logger.info(
            f"[Trace] 工作流追踪完成: {self._trace.trace_id}, "
            f"总耗时 {self._trace.total_duration_ms:.1f}ms, "
            f"节点数 {len(self._trace.nodes)}, "
            f"Token {self._trace.total_tokens}, "
            f"成本 ${self._trace.total_cost_usd:.4f}"
        )

        return self._trace

    def _estimate_cost(self) -> float:
        """估算成本"""
        total = 0.0
        for span in self._spans:
            total += span.token_estimate * self._token_rates["input_per_1k"] / 1000
        return total

    def get_summary(self) -> Dict[str, Any]:
        """获取当前追踪摘要"""
        if not self._trace:
            return {}

        error_count = len([s for s in self._spans if s.error])
        nodes = self._trace.nodes if self._trace.nodes else self._spans
        total_tokens = sum(s.token_estimate for s in self._spans)
        elapsed = (time.time() - self._trace.start_time) * 1000 if self._trace.start_time else 0

        return {
            "trace_id": self._trace.trace_id,
            "query": self._trace.query,
            "total_duration_ms": elapsed,
            "node_count": len(self._spans),
            "total_tokens": total_tokens,
            "total_cost_usd": sum(s.token_estimate * self._token_rates["input_per_1k"] / 1000 for s in self._spans),
            "error_count": error_count,
            "nodes": [
                {
                    "name": s.node_name,
                    "duration_ms": s.duration_ms,
                    "status": s.status,
                    "papers": s.paper_count,
                    "tokens": s.token_estimate,
                }
                for s in self._spans
            ],
        }


class NodeTimingMiddleware:
    """节点计时中间件

    可以包装任何节点执行函数，自动记录计时和状态。
    """

    def __init__(self, tracer: WorkflowTracer):
        self.tracer = tracer

    def wrap(self, node_func, node_name: str):
        """包装节点函数"""
        def wrapped(*args, **kwargs):
            self.tracer.start_node(node_name)
            try:
                result = node_func(*args, **kwargs)
                self.tracer.end_node(status="completed")
                return result
            except Exception as e:
                self.tracer.end_node(status="failed", error=str(e))
                raise
        return wrapped


def create_tracer() -> WorkflowTracer:
    """便捷函数：创建追踪器"""
    return WorkflowTracer()
