"""
OpenTelemetry 集成模块

提供：
1. 标准 OTEL span 创建
2. 日志集成到 span
3. 多 exporter 支持（Console/Jaeger/Zipkin）
"""
from src.agents_v2.logging_config import get_logging_logger

import os
from typing import Optional

logger = get_logging_logger(__name__)

# 检查 OTEL 是否可用
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. Run: pip install opentelemetry-api opentelemetry-sdk")


class OTELTracer:
    """
    OpenTelemetry 追踪器

    使用方式：
        tracer = OTELTracer()
        tracer.start_span("diagnostic")
        # ... 执行代码 ...
        tracer.end_span(success=True, duration_ms=1234)
    """

    def __init__(
        self,
        service_name: str = "paper-agent",
        enable_console_export: bool = True,
        enable_jaeger: bool = False,
        jaeger_endpoint: str = "http://localhost:14268/api/traces"
    ):
        if not OTEL_AVAILABLE:
            logger.warning("OTELTracer: OpenTelemetry not available")
            self._tracer = None
            return

        self._service_name = service_name
        self._tracer = None
        self._span = None

        # 创建 resource
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: "1.0.0",
        })

        # 创建 provider
        provider = TracerProvider(resource=resource)

        # 添加 exporter
        if enable_console_export:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("OTEL: Console exporter enabled")

        # 注意：Jaeger exporter 需要额外安装
        # pip install opentelemetry-exporter-otlp-proto-grpc
        # if enable_jaeger:
        #     from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        #     jaeger_exporter = JaegerExporter(agent_host_name="localhost", agent_port=6831)
        #     provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # 设置全局 provider
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(service_name)

        logger.info(f"OTEL: Initialized with service_name={service_name}")

    def start_span(
        self,
        name: str,
        attributes: Optional[dict] = None,
        logs: Optional[list] = None
    ):
        """开始一个 span"""
        if not self._tracer:
            return

        self._span = self._tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                self._span.set_attribute(key, value)

        # 记录初始日志
        if logs:
            for log in logs:
                self._span.add_event("log", attributes=log)

        return self._span

    def end_span(
        self,
        success: bool = True,
        duration_ms: Optional[float] = None,
        logs: Optional[list] = None,
        error: Optional[str] = None
    ):
        """结束当前 span"""
        if not self._span:
            return

        # 添加结束时的日志
        if logs:
            for log in logs:
                self._span.add_event("log", attributes=log)

        # 设置 duration
        if duration_ms is not None:
            self._span.set_attribute("duration_ms", duration_ms)

        # 设置状态
        if success:
            self._span.set_status(Status(StatusCode.OK))
        else:
            self._span.set_status(Status(StatusCode.ERROR, str(error) if error else "Unknown error"))
            if error:
                self._span.record_exception(Exception(error))

        self._span.end()
        self._span = None

    def add_event(self, name: str, attributes: Optional[dict] = None):
        """添加 span 事件（日志）"""
        if not self._span:
            return
        self._span.add_event(name, attributes=attributes or {})

    def set_attribute(self, key: str, value):
        """设置 span 属性"""
        if not self._span:
            return
        self._span.set_attribute(key, value)

    def record_exception(self, exception: Exception):
        """记录异常"""
        if not self._span:
            return
        self._span.record_exception(exception)
        self._span.set_status(Status(StatusCode.ERROR, str(exception)))

    def get_current_span(self):
        """获取当前 span"""
        if not OTEL_AVAILABLE:
            return None
        from opentelemetry.trace import trace
        return trace.get_current_span()


# 全局 tracer 实例
_otel_tracer: Optional[OTELTracer] = None


def init_otel_tracer(
    service_name: str = "paper-agent",
    enable_console: bool = True
) -> OTELTracer:
    """初始化全局 OTEL tracer"""
    global _otel_tracer
    _otel_tracer = OTELTracer(
        service_name=service_name,
        enable_console_export=enable_console
    )
    return _otel_tracer


def get_otel_tracer() -> Optional[OTELTracer]:
    """获取全局 OTEL tracer"""
    return _otel_tracer


class SpanContext:
    """
    Span 上下文管理器

    使用方式：
        tracer = get_otel_tracer()
        with SpanContext(tracer, "diagnostic", {"query": "深度学习"}):
            # ... 执行代码 ...
            tracer.add_event("search_complete", {"paper_count": 10})
    """

    def __init__(
        self,
        otel_tracer: OTELTracer,
        span_name: str,
        attributes: Optional[dict] = None,
        logs: Optional[list] = None
    ):
        self._tracer = otel_tracer
        self._span_name = span_name
        self._attributes = attributes
        self._logs = logs
        self._start_time = None

    def __enter__(self):
        if self._tracer:
            self._start_time = __import__("time").time()
            self._tracer.start_span(
                self._span_name,
                attributes=self._attributes,
                logs=self._logs
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._tracer:
            duration_ms = None
            if self._start_time:
                duration_ms = (__import__("time").time() - self._start_time) * 1000

            if exc_type:
                self._tracer.record_exception(exc_val)
                self._tracer.end_span(success=False, duration_ms=duration_ms, error=str(exc_val))
            else:
                self._tracer.end_span(success=True, duration_ms=duration_ms)

        # 返回 False 不抑制异常
        return False
