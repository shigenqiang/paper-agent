"""
监控告警 - 错误率告警、性能告警

提供:
1. AlertManager: 告警管理器
2. RateLimiter: 限流器
3. AlertChannel: 告警渠道（日志、Webhook、Email、Slack等）
4. AlertRule: 告警规则引擎
5. AlertAggregator: 告警聚合器
"""
import time
import os
import asyncio
import json
import hashlib
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    MEMORY_HIGH = "memory_high"
    CPU_HIGH = "cpu_high"
    AGENT_FAILURE = "agent_failure"
    TOOL_FAILURE = "tool_failure"
    DATABASE_UNAVAILABLE = "database_unavailable"
    REDIS_UNAVAILABLE = "redis_unavailable"


@dataclass
class Alert:
    """告警"""
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    alert_id: str = ""
    source: str = ""
    deduplication_key: str = ""

    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = hashlib.md5(
                f"{self.alert_type.value}:{self.message}:{self.timestamp}".encode()
            ).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "source": self.source,
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


class EmailAlertChannel(AlertChannel):
    """Email告警渠道"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        min_severity: AlertSeverity = AlertSeverity.ERROR
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.min_severity = min_severity

    def send(self, alert: Alert):
        """发送告警到Email"""
        if not self._should_send(alert):
            return

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity.value.upper()}] Paper Agent Alert: {alert.alert_type.value}"
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)

            # 创建HTML内容
            html_content = self._create_html_content(alert)
            msg.attach(MIMEText(html_content, 'html'))

            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Alert email sent: {alert.message}")

        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")

    def _should_send(self, alert: Alert) -> bool:
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        return severity_order.index(alert.severity) >= severity_order.index(self.min_severity)

    def _create_html_content(self, alert: Alert) -> str:
        timestamp = datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        severity_colors = {
            AlertSeverity.INFO: '#17a2b8',
            AlertSeverity.WARNING: '#ffc107',
            AlertSeverity.ERROR: '#dc3545',
            AlertSeverity.CRITICAL: '#8b0000'
        }
        color = severity_colors.get(alert.severity, '#6c757d')

        metadata_html = ""
        for key, value in alert.metadata.items():
            metadata_html += f"<tr><td><b>{key}</b></td><td>{value}</td></tr>"

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="border-left: 4px solid {color}; padding: 10px; margin: 10px 0;">
                <h2 style="color: {color}; margin: 0;">
                    [{alert.severity.value.upper()}] {alert.alert_type.value}
                </h2>
            </div>
            <p><b>Time:</b> {timestamp}</p>
            <p><b>Message:</b> {alert.message}</p>
            <p><b>Alert ID:</b> {alert.alert_id}</p>
            <h3>Details:</h3>
            <table style="border-collapse: collapse; width: 100%;">
                {metadata_html or '<tr><td>No additional details</td></tr>'}
            </table>
        </body>
        </html>
        """


class SlackAlertChannel(AlertChannel):
    """Slack告警渠道"""

    def __init__(
        self,
        webhook_url: str,
        channel: str = "#alerts",
        min_severity: AlertSeverity = AlertSeverity.WARNING
    ):
        self.webhook_url = webhook_url
        self.channel = channel
        self.min_severity = min_severity

    async def send(self, alert: Alert):
        """发送告警到Slack"""
        if not self._should_send(alert):
            return

        try:
            import aiohttp

            severity_emoji = {
                AlertSeverity.INFO: ":information_source:",
                AlertSeverity.WARNING: ":warning:",
                AlertSeverity.ERROR: ":x:",
                AlertSeverity.CRITICAL: ":fire:"
            }
            emoji = severity_emoji.get(alert.severity, ":bell:")

            payload = {
                "channel": self.channel,
                "username": "Paper Agent Alerts",
                "icon_emoji": emoji,
                "attachments": [{
                    "color": self._get_severity_color(alert.severity),
                    "title": f"[{alert.severity.value.upper()}] {alert.alert_type.value}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Alert ID", "value": alert.alert_id, "short": True},
                        {"title": "Time", "value": datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S'), "short": True}
                    ],
                    "footer": "Paper Agent Monitoring"
                }]
            }

            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                )

            logger.info(f"Alert sent to Slack: {alert.message}")

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def _should_send(self, alert: Alert) -> bool:
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        return severity_order.index(alert.severity) >= severity_order.index(self.min_severity)

    def _get_severity_color(self, severity: AlertSeverity) -> str:
        colors = {
            AlertSeverity.INFO: "#17a2b8",
            AlertSeverity.WARNING: "#ffc107",
            AlertSeverity.ERROR: "#dc3545",
            AlertSeverity.CRITICAL: "#8b0000"
        }
        return colors.get(severity, "#6c757d")


class FileAlertChannel(AlertChannel):
    """文件告警渠道"""

    def __init__(
        self,
        file_path: str = "logs/alerts.jsonl",
        min_severity: AlertSeverity = AlertSeverity.WARNING
    ):
        self.file_path = file_path
        self.min_severity = min_severity
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    def send(self, alert: Alert):
        """写入告警到文件"""
        if not self._should_send(alert):
            return

        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                record = {
                    **alert.to_dict(),
                    "written_at": datetime.now().isoformat(),
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write alert to file: {e}")

    def _should_send(self, alert: Alert) -> bool:
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        return severity_order.index(alert.severity) >= severity_order.index(self.min_severity)


class AlertAggregator:
    """
    告警聚合器

    防止告警风暴，自动聚合相似告警
    """

    def __init__(self, aggregation_window: int = 300):
        self.aggregation_window = aggregation_window
        self._alert_groups: Dict[str, List[Alert]] = defaultdict(list)
        self._last_aggregated: Dict[str, float] = {}

    def add(self, alert: Alert) -> Optional[Alert]:
        """
        添加告警到聚合器

        Returns:
            如果应该发送聚合告警，返回聚合后的告警；否则返回None
        """
        key = self._get_aggregation_key(alert)

        if key not in self._alert_groups:
            self._alert_groups[key] = []

        self._alert_groups[key].append(alert)
        self._cleanup(key)

        # 检查是否需要发送聚合告警
        count = len(self._alert_groups[key])
        if count >= 10 or alert.severity == AlertSeverity.CRITICAL:
            aggregated = self._create_aggregated_alert(key)
            self._last_aggregated[key] = time.time()
            return aggregated

        return None

    def _get_aggregation_key(self, alert: Alert) -> str:
        """获取聚合键"""
        return f"{alert.alert_type.value}:{alert.source or 'unknown'}"

    def _cleanup(self, key: str):
        """清理过期的告警"""
        now = time.time()
        cutoff = now - self.aggregation_window
        self._alert_groups[key] = [
            a for a in self._alert_groups[key]
            if a.timestamp > cutoff
        ]

    def _create_aggregated_alert(self, key: str) -> Alert:
        """创建聚合告警"""
        alerts = self._alert_groups[key]
        if not alerts:
            raise ValueError("No alerts to aggregate")

        first = alerts[0]
        count = len(alerts)

        message = f"{first.message} (occurred {count} times)"

        aggregated = Alert(
            alert_type=first.alert_type,
            severity=first.severity,
            message=message,
            metadata={
                "aggregated_count": count,
                "first_occurrence": alerts[0].timestamp,
                "last_occurrence": alerts[-1].timestamp,
                "sample_alerts": [a.to_dict() for a in alerts[:3]]
            },
            source=first.source,
            deduplication_key=key
        )

        return aggregated


class AlertRule:
    """
    告警规则

    定义条件触发告警的规则
    """

    def __init__(
        self,
        name: str,
        condition: Callable[[Dict], bool],
        alert_type: AlertType,
        severity: AlertSeverity,
        message_template: str,
        cooldown: int = 300
    ):
        self.name = name
        self.condition = condition
        self.alert_type = alert_type
        self.severity = severity
        self.message_template = message_template
        self.cooldown = cooldown
        self._last_triggered: Dict[str, float] = {}

    def evaluate(self, metrics: Dict[str, Any], entity_id: str = "default") -> Optional[Alert]:
        """评估规则"""
        now = time.time()

        # 检查冷却期
        if entity_id in self._last_triggered:
            if now - self._last_triggered[entity_id] < self.cooldown:
                return None

        try:
            if self.condition(metrics):
                self._last_triggered[entity_id] = now
                return Alert(
                    alert_type=self.alert_type,
                    severity=self.severity,
                    message=self.message_template.format(**metrics),
                    metadata={"rule": self.name, "metrics": metrics},
                    source=entity_id
                )
        except Exception as e:
            logger.error(f"Alert rule {self.name} evaluation failed: {e}")

        return None


class AlertRuleEngine:
    """
    告警规则引擎

    管理多个告警规则并自动评估
    """

    def __init__(self):
        self._rules: List[AlertRule] = []

    def add_rule(self, rule: AlertRule):
        """添加规则"""
        self._rules.append(rule)

    def evaluate(self, metrics: Dict[str, Any], entity_id: str = "default") -> List[Alert]:
        """评估所有规则"""
        alerts = []
        for rule in self._rules:
            alert = rule.evaluate(metrics, entity_id)
            if alert:
                alerts.append(alert)
        return alerts

    def remove_rule(self, name: str):
        """移除规则"""
        self._rules = [r for r in self._rules if r.name != name]

    def get_rules(self) -> List[str]:
        """获取所有规则名称"""
        return [r.name for r in self._rules]


class AlertManager:
    """
    告警管理器

    使用方式:
        manager = AlertManager()
        manager.add_channel(LogAlertChannel())

        # 触发告警
        manager.trigger(AlertType.ERROR_RATE, AlertSeverity.WARNING, "Error rate exceeded 5%")
    """

    def __init__(self, enable_aggregation: bool = True):
        self._channels: List[AlertChannel] = []
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._alert_history: List[Alert] = []
        self._alert_rule_engine = AlertRuleEngine()
        self._aggregator = AlertAggregator() if enable_aggregation else None

    def add_channel(self, channel: AlertChannel):
        """添加告警渠道"""
        self._channels.append(channel)

    def remove_channel(self, channel: AlertChannel):
        """移除告警渠道"""
        if channel in self._channels:
            self._channels.remove(channel)

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self._alert_rule_engine.add_rule(rule)

    def trigger(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = ""
    ):
        """触发告警"""
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata or {},
            source=source
        )

        return self._send_alert(alert)

    def _send_alert(self, alert: Alert):
        """发送告警（通过渠道）"""
        # 如果有聚合器，先处理聚合
        if self._aggregator:
            aggregated = self._aggregator.add(alert)
            if aggregated:
                self._deliver_alert(aggregated)
            self._deliver_alert(alert)
        else:
            self._deliver_alert(alert)

        # 记录告警历史
        self._alert_history.append(alert)
        if len(self._alert_history) > 1000:
            self._alert_history = self._alert_history[-500:]

        return alert

    def _deliver_alert(self, alert: Alert):
        """通过所有渠道发送告警"""
        for channel in self._channels:
            try:
                if asyncio.iscoroutinefunction(channel.send):
                    asyncio.create_task(channel.send(alert))
                else:
                    channel.send(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via channel {channel}: {e}")

    def evaluate_rules(self, metrics: Dict[str, Any], entity_id: str = "default") -> List[Alert]:
        """评估所有告警规则"""
        alerts = self._alert_rule_engine.evaluate(metrics, entity_id)
        for alert in alerts:
            self._send_alert(alert)
        return alerts

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
