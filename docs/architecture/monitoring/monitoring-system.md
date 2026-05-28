# Monitoring 可观测性详解

> 位置: `src/agents_v2/monitoring/`

## 一、架构概览

```
monitoring/
├── __init__.py
├── alerts.py              # 告警系统 (24KB)
├── chain_debugger.py      # 链路调试 (9KB)
├── chain_monitor.py       # 链路监控 (7KB)
├── chain_tracer.py       # 链路追踪 (21KB)
├── chain_tracer_mixin.py # 追踪混入 (8KB)
├── dashboard.py          # 监控仪表盘 (45KB)
├── docs_monitor.py       # 文档监控 (10KB)
├── latency_tracker.py    # 延迟追踪 (6KB)
├── optimizer.py          # 性能优化 (10KB)
├── quality_tracker.py    # 质量追踪 (14KB)
└── structured_logging.py # 结构化日志 (16KB)
```

## 二、核心组件

### 2.1 ChainTracer 链路追踪

```python
class ChainTracer:
    """LangGraph链路过追踪"""

    def __init__(self):
        self.spans: List[Span] = []

    async def start_span(
        self,
        name: str,
        node_name: str,
        parent_span_id: str = None
    ) -> Span:
        """开始一个追踪span"""
        span = Span(
            id=str(uuid.uuid4()),
            name=name,
            node_name=node_name,
            parent_id=parent_span_id,
            start_time=time.time()
        )
        self.spans.append(span)
        return span

    def end_span(self, span_id: str, status: str = "success"):
        """结束span"""
        span = self._get_span(span_id)
        span.duration_ms = (time.time() - span.start_time) * 1000
        span.status = status

    async def trace_node(
        self,
        node_name: str,
        func: Callable,
        *args, **kwargs
    ):
        """追踪节点执行"""
        span = await self.start_span(f"node.{node_name}", node_name)

        try:
            result = await func(*args, **kwargs)
            self.end_span(span.id, "success")
            return result
        except Exception as e:
            self.end_span(span.id, f"error: {type(e).__name__}")
            raise
```

### 2.2 LatencyTracker 延迟追踪

```python
class LatencyTracker:
    """延迟追踪器"""

    def __init__(self):
        self.latencies: Dict[str, List[float]] = defaultdict(list)

    def track(self, operation: str, duration_ms: float):
        """记录延迟"""
        self.latencies[operation].append(duration_ms)

    def get_percentiles(
        self,
        operation: str
    ) -> Dict[str, float]:
        """获取百分位延迟"""
        values = sorted(self.latencies[operation])
        n = len(values)

        return {
            "p50": values[int(n * 0.5)],
            "p75": values[int(n * 0.75)],
            "p90": values[int(n * 0.9)],
            "p95": values[int(n * 0.95)],
            "p99": values[int(n * 0.99)]
        }

    def get_stats(self, operation: str) -> LatencyStats:
        """获取延迟统计"""
        values = self.latencies[operation]
        return LatencyStats(
            count=len(values),
            mean=np.mean(values),
            median=np.median(values),
            std=np.std(values),
            min=min(values),
            max=max(values)
        )
```

### 2.3 QualityTracker 质量追踪

```python
class QualityTracker:
    """输出质量追踪"""

    def track(
        self,
        agent_name: str,
        quality_score: float,
        dimensions: Dict[str, float] = None
    ):
        """追踪质量评分"""
        record = QualityRecord(
            agent_name=agent_name,
            score=quality_score,
            dimensions=dimensions or {},
            timestamp=datetime.now()
        )
        self.records.append(record)

    def get_agent_quality_trend(
        self,
        agent_name: str,
        window: int = 100
    ) -> QualityTrend:
        """获取Agent质量趋势"""
        recent = [
            r for r in self.records
            if r.agent_name == agent_name
        ][-window:]

        scores = [r.score for r in recent]

        return QualityTrend(
            agent_name=agent_name,
            window=window,
            avg_score=np.mean(scores),
            min_score=min(scores),
            max_score=max(scores),
            trend="stable" if len(scores) < 10 else self._calculate_trend(scores)
        )
```

### 2.4 Alerts 告警系统

```python
class AlertManager:
    """告警管理器"""

    ALERT_RULES = {
        "high_latency": {
            "threshold": 5000,  # 5秒
            "severity": "warning",
            "message": "操作延迟超过5秒"
        },
        "error_rate": {
            "threshold": 0.05,  # 5%错误率
            "severity": "critical",
            "message": "错误率超过5%"
        },
        "circuit_open": {
            "severity": "critical",
            "message": "熔断器打开"
        }
    }

    async def check_and_alert(self, metric_name: str, value: float):
        """检查指标并触发告警"""
        rule = self.ALERT_RULES.get(metric_name)

        if rule and value > rule["threshold"]:
            await self._send_alert(
                severity=rule["severity"],
                message=rule["message"],
                metric=metric_name,
                value=value
            )
```

### 2.5 StructuredLogging 结构化日志

```python
class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, logger_name: str):
        self.logger = get_logging_logger(logger_name)

    def log(
        self,
        level: str,
        message: str,
        context: dict = None
    ):
        """结构化日志记录"""
        log_data = {
            "message": message,
            "timestamp": datetime.now().isoformat(),
            **(context or {})
        }

        getattr(self.logger, level)(log_data)

    def log_agent_execution(
        self,
        agent_name: str,
        input_size: int,
        output_size: int,
        duration_ms: float,
        success: bool
    ):
        """记录Agent执行日志"""
        self.log("info", "Agent execution", {
            "agent_name": agent_name,
            "input_size": input_size,
            "output_size": output_size,
            "duration_ms": duration_ms,
            "success": success,
            "event_type": "agent_execution"
        })
```

## 三、Dashboard 监控仪表盘

```python
class MonitoringDashboard:
    """监控仪表盘"""

    def get_overview(self) -> DashboardOverview:
        """获取总览数据"""
        return DashboardOverview(
            total_requests=self.counter.total,
            success_rate=self.counter.success_rate,
            avg_latency=self.latency_tracker.get_stats("all").mean,
            active_circuits=self.circuit_breaker.get_open_count(),
            quality_score=self.quality_tracker.get_overall_score()
        )

    def get_agent_performance(self) -> List[AgentPerformance]:
        """获取各Agent性能"""
        ...

    def get_trending_issues(self) -> List[TrendingIssue]:
        """获取趋势问题"""
        ...
```

## 四、关键指标

| 指标类别 | 指标名 | 说明 |
|----------|--------|------|
| **延迟** | latency.p50/p95/p99 | 操作延迟百分位 |
| **吞吐** | throughput.rps | 每秒请求数 |
| **错误** | error.rate | 错误率 |
| **质量** | quality.score | 质量评分 |
| **熔断** | circuit.state | 熔断状态 |

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/monitoring/`
