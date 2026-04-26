"""
监控仪表板 - Monitoring Dashboard

实现实时指标收集和展示:
- 请求延迟
- 错误率
- 队列长度
- 资源使用
"""
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""

    def __init__(self, retention_seconds: int = 3600):
        """初始化

        Args:
            retention_seconds: 数据保留时间
        """
        self.retention_seconds = retention_seconds
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}

    def record_latency(self, operation: str, latency: float):
        """记录延迟

        Args:
            operation: 操作名称
            latency: 延迟（秒）
        """
        key = f"latency.{operation}"
        self._metrics[key].append(MetricPoint(time.time(), latency))

    def record_count(self, name: str, count: float = 1):
        """记录计数

        Args:
            name: 指标名称
            count: 增量
        """
        self._counters[name] += count

    def set_gauge(self, name: str, value: float):
        """设置仪表值

        Args:
            name: 指标名称
            value: 值
        """
        self._gauges[name] = value
        self._metrics[name].append(MetricPoint(time.time(), value))

    def get_latency_stats(self, operation: str, window_seconds: float = 60) -> Dict[str, float]:
        """获取延迟统计

        Args:
            operation: 操作名称
            window_seconds: 时间窗口

        Returns:
            Dict: 统计数据 (p50, p95, p99, avg)
        """
        key = f"latency.{operation}"
        cutoff = time.time() - window_seconds

        values = [
            m.value for m in self._metrics.get(key, [])
            if m.timestamp >= cutoff
        ]

        if not values:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0}

        values.sort()
        n = len(values)

        return {
            "p50": values[int(n * 0.5)],
            "p95": values[int(n * 0.95)],
            "p99": values[int(n * 0.99)] if n >= 100 else values[-1],
            "avg": sum(values) / n,
            "count": n
        }

    def get_counter(self, name: str) -> float:
        """获取计数器值

        Args:
            name: 计数器名称

        Returns:
            float: 计数值
        """
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> Optional[float]:
        """获取仪表值

        Args:
            name: 指标名称

        Returns:
            Optional[float]: 值
        """
        return self._gauges.get(name)

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标

        Returns:
            Dict: 所有指标数据
        """
        metrics = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges)
        }

        # 添加最近延迟统计
        latency_keys = [k for k in self._metrics.keys() if k.startswith("latency.")]
        latency_stats = {}
        for key in latency_keys:
            operation = key.replace("latency.", "")
            latency_stats[operation] = self.get_latency_stats(operation)

        metrics["latency"] = latency_stats

        return metrics


class MonitoringDashboard:
    """监控仪表板"""

    def __init__(self):
        """初始化"""
        self.collector = MetricsCollector()
        self._alert_handlers: List[Callable] = []

    def record_request(self, operation: str, latency: float, success: bool):
        """记录请求

        Args:
            operation: 操作名称
            latency: 延迟
            success: 是否成功
        """
        self.collector.record_latency(operation, latency)
        self.collector.record_count("requests.total")
        self.collector.record_count(f"requests.{'success' if success else 'failure'}")

    def record_queue_size(self, queue_name: str, size: int):
        """记录队列大小

        Args:
            queue_name: 队列名称
            size: 大小
        """
        self.collector.set_gauge(f"queue.{queue_name}.size", size)

    def record_cost(self, amount: float):
        """记录成本

        Args:
            amount: 成本金额
        """
        self.collector.record_count("cost.total", amount)

    def register_alert_handler(self, handler: Callable):
        """注册告警处理器

        Args:
            handler: 处理函数
        """
        self._alert_handlers.append(handler)

    async def check_thresholds(self, rules: Dict[str, Dict]) -> List[Dict]:
        """检查阈值并触发告警

        Args:
            rules: 告警规则配置

        Returns:
            List[Dict]: 触发的告警列表
        """
        alerts = []

        for rule_name, rule in rules.items():
            metric_name = rule.get("metric")
            threshold = rule.get("threshold")
            condition = rule.get("condition", ">")  # >, <, >=
            severity = rule.get("severity", "warning")

            # 获取指标值
            if metric_name.startswith("latency."):
                operation = metric_name.replace("latency.", "")
                stats = self.collector.get_latency_stats(operation)
                value = stats.get(rule.get("percentile", "p95"), 0)
            elif metric_name.startswith("queue."):
                value = self.collector.get_gauge(metric_name)
            else:
                value = self.collector.get_counter(metric_name)

            if value is None:
                continue

            # 检查条件
            triggered = False
            if condition == ">" and value > threshold:
                triggered = True
            elif condition == "<" and value < threshold:
                triggered = True
            elif condition == ">=" and value >= threshold:
                triggered = True

            if triggered:
                alert = {
                    "rule": rule_name,
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "severity": severity,
                    "timestamp": time.time()
                }
                alerts.append(alert)

                # 触发处理器
                for handler in self._alert_handlers:
                    try:
                        await handler(alert)
                    except Exception as e:
                        logger.error(f"Alert handler failed: {e}")

        return alerts

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """获取仪表板摘要

        Returns:
            Dict: 仪表板数据
        """
        metrics = self.collector.get_all_metrics()

        return {
            "timestamp": time.time(),
            "requests": {
                "total": metrics["counters"].get("requests.total", 0),
                "success": metrics["counters"].get("requests.success", 0),
                "failure": metrics["counters"].get("requests.failure", 0)
            },
            "latency": metrics.get("latency", {}),
            "queues": {
                k.replace("queue.", "").replace(".size", ""): v
                for k, v in metrics["gauges"].items()
                if k.startswith("queue.")
            },
            "cost": metrics["counters"].get("cost.total", 0)
        }


# 便捷函数
def create_dashboard() -> MonitoringDashboard:
    """创建监控仪表板"""
    return MonitoringDashboard()