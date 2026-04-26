"""
监控告警 - 错误率告警、性能告警

提供:
1. AlertManager: 告警管理器
2. RateLimiter: 限流器
3. AlertChannel: 告警渠道（日志、Webhook等）
"""
import time
import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """告警类型"""
    ERROR_RATE = "error_rate"
    LATENCY_HIGH = "latency_high"
    ERROR_THRESHOLD = "error_threshold"
    TIMEOUT = "timeout"
    CACHE_MISS = "cache_miss"
    RATE_LIMIT = "rate_limit"


@dataclass
class Alert:
    """告警"""
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class AlertChannel:
    """告警渠道基类"""

    def send(self, alert: Alert):
        """发送告警"""
        raise NotImplementedError


class LogAlertChannel(AlertChannel):
    """日志告警渠道"""

    def __init__(self, min_severity: AlertSeverity = AlertSeverity.WARNING):
        self.min_severity = min_severity
        self.logger = logging.getLogger("alerts")

    def send(self, alert: Alert):
        """发送告警到日志"""
        if self._should_send(alert):
            log_method = getattr(self.logger, alert.severity.value, self.logger.warning)
            log_method(f"[{alert.alert_type.value}] {alert.message}", extra=alert.to_dict())

    def _should_send(self, alert: Alert) -> bool:
        """判断是否应该发送"""
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        return severity_order.index(alert.severity) >= severity_order.index(self.min_severity)


class WebhookAlertChannel(AlertChannel):
    """Webhook告警渠道"""

    def __init__(self, webhook_url: str, min_severity: AlertSeverity = AlertSeverity.ERROR):
        self.webhook_url = webhook_url
        self.min_severity = min_severity

    async def send(self, alert: Alert):
        """发送告警到Webhook"""
        if alert.severity.value not in [s.value for s in AlertSeverity] or \
           list(AlertSeverity).index(alert.severity) < list(AlertSeverity).index(self.min_severity):
            return

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.webhook_url,
                    json=alert.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=5)
                )
            logger.info(f"Alert sent to webhook: {alert.message}")
        except Exception as e:
            logger.error(f"Failed to send alert to webhook: {e}")


class AlertManager:
    """
    告警管理器

    使用方式:
        manager = AlertManager()
        manager.add_channel(LogAlertChannel())

        # 触发告警
        manager.trigger(AlertType.ERROR_RATE, AlertSeverity.WARNING, "Error rate exceeded 5%")
    """

    def __init__(self):
        self._channels: List[AlertChannel] = []
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def add_channel(self, channel: AlertChannel):
        """添加告警渠道"""
        self._channels.append(channel)

    def remove_channel(self, channel: AlertChannel):
        """移除告警渠道"""
        if channel in self._channels:
            self._channels.remove(channel)

    def trigger(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """触发告警"""
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata or {}
        )

        for channel in self._channels:
            try:
                channel.send(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via channel {channel}: {e}")

        return alert

    def record_metric(self, metric_name: str, value: float):
        """记录指标（用于告警判断）"""
        self._metrics[metric_name].append(value)

        # 定期清理旧数据
        self._cleanup_if_needed()

    def _cleanup_if_needed(self):
        """清理旧指标数据"""
        now = time.time()
        if now - self._last_cleanup < 60:  # 每分钟最多清理一次
            return

        self._last_cleanup = now
        max_age = 300  # 保留5分钟数据

        for metric_name in list(self._metrics.keys()):
            self._metrics[metric_name] = [
                v for v in self._metrics[metric_name]
                if now - v < max_age
            ]
            if not self._metrics[metric_name]:
                del self._metrics[metric_name]

    def check_error_rate(self, threshold: float = 0.05) -> Optional[Alert]:
        """检查错误率"""
        errors = self._metrics.get("errors", [])
        total = self._metrics.get("total_requests", [])

        if not total:
            return None

        error_count = sum(1 for e in errors if time.time() - e < 60)
        total_count = sum(1 for t in total if time.time() - t < 60)

        if total_count == 0:
            return None

        error_rate = error_count / total_count

        if error_rate > threshold:
            return self.trigger(
                AlertType.ERROR_RATE,
                AlertSeverity.WARNING,
                f"Error rate {error_rate:.2%} exceeded threshold {threshold:.2%}",
                {"error_rate": error_rate, "threshold": threshold}
            )

        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "metrics": {
                name: len(values)
                for name, values in self._metrics.items()
            },
            "channels": len(self._channels)
        }


class RateLimiter:
    """
    限流器

    使用方式:
        limiter = RateLimiter(max_requests=100, window=60)
        if not limiter.is_allowed("user123"):
            return "Rate limit exceeded"
    """

    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - self.window

        # 清理过期记录
        self._requests[key] = [
            t for t in self._requests[key]
            if t > window_start
        ]

        # 检查是否超限
        if len(self._requests[key]) >= self.max_requests:
            return False

        # 记录新请求
        self._requests[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """获取剩余请求数"""
        now = time.time()
        window_start = now - self.window

        recent_requests = [
            t for t in self._requests[key]
            if t > window_start
        ]

        return max(0, self.max_requests - len(recent_requests))

    def reset(self, key: str):
        """重置限流"""
        if key in self._requests:
            del self._requests[key]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "max_requests": self.max_requests,
            "window": self.window,
            "tracked_keys": len(self._requests)
        }


class HealthChecker:
    """
    健康检查器

    使用方式:
        checker = HealthChecker()
        checker.register_check("database", lambda: db.ping())

        health = checker.check()
        if not health["healthy"]:
            print(f"Unhealthy components: {health['unhealthy']}")
    """

    def __init__(self):
        self._checks: Dict[str, Callable[[], bool]] = {}

    def register_check(self, name: str, check_func: Callable[[], bool]):
        """注册健康检查"""
        self._checks[name] = check_func

    def check(self) -> Dict[str, Any]:
        """执行健康检查"""
        results = {}
        unhealthy = []

        for name, check_func in self._checks.items():
            try:
                is_healthy = check_func()
                results[name] = {"healthy": is_healthy}
                if not is_healthy:
                    unhealthy.append(name)
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
                unhealthy.append(name)

        return {
            "healthy": len(unhealthy) == 0,
            "unhealthy": unhealthy,
            "details": results,
            "timestamp": time.time()
        }


# 全局限流器实例
_global_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器"""
    return _global_rate_limiter
