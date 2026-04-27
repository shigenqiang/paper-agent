"""
数据流追踪与监控模块

扩展功能:
1. 数据流追踪与可视化
2. 仪表盘设计
3. 异常检测与告警
4. 自动恢复机制

设计原则:
- 实时追踪系统状态
- 快速检测异常
- 提供可视化界面
"""
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DataFlowStep:
    """数据流步骤"""
    step_id: str
    step_name: str
    status: str  # "pending", "processing", "completed", "failed"
    start_time: float
    end_time: Optional[float] = None
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """告警"""
    level: AlertLevel
    message: str
    source: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)


class DataFlowTracker:
    """数据流追踪器

    追踪整个处理流程的每个步骤
    """

    def __init__(self):
        self.flows: Dict[str, List[DataFlowStep]] = defaultdict(list)
        self.current_flow_id: Optional[str] = None

    def start_flow(self, flow_id: str, name: str) -> str:
        """开始一个新的数据流"""
        self.current_flow_id = flow_id
        self.flows[flow_id] = []

        logger.info(f"Started flow {flow_id}: {name}")

        return flow_id

    def add_step(
        self,
        flow_id: str,
        step_name: str,
        input_data: Any = None
    ) -> str:
        """添加一个步骤"""
        step_id = f"{flow_id}_step_{len(self.flows[flow_id])}"

        step = DataFlowStep(
            step_id=step_id,
            step_name=step_name,
            status="pending",
            start_time=time.time(),
            input_data=input_data
        )

        self.flows[flow_id].append(step)

        return step_id

    def update_step(
        self,
        flow_id: str,
        step_id: str,
        status: str,
        output_data: Any = None,
        error: Optional[str] = None
    ):
        """更新步骤状态"""
        if flow_id not in self.flows:
            return

        for step in self.flows[flow_id]:
            if step.step_id == step_id:
                step.status = status
                if status == "completed" or status == "failed":
                    step.end_time = time.time()

                if output_data is not None:
                    step.output_data = output_data

                if error:
                    step.error = error

                logger.info(f"Step {step_id} -> {status}")
                break

    def get_flow(self, flow_id: str) -> List[DataFlowStep]:
        """获取数据流"""
        return self.flows.get(flow_id, [])

    def get_flow_duration(self, flow_id: str) -> float:
        """获取数据流总时长"""
        steps = self.flows.get(flow_id, [])
        if not steps:
            return 0.0

        start = min(s.start_time for s in steps)
        end = max(s.end_time or time.time() for s in steps)

        return end - start

    def get_flow_summary(self, flow_id: str) -> Dict[str, Any]:
        """获取数据流摘要"""
        steps = self.flows.get(flow_id, [])

        completed = sum(1 for s in steps if s.status == "completed")
        failed = sum(1 for s in steps if s.status == "failed")
        pending = sum(1 for s in steps if s.status == "pending")
        processing = sum(1 for s in steps if s.status == "processing")

        return {
            "flow_id": flow_id,
            "total_steps": len(steps),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "processing": processing,
            "duration": self.get_flow_duration(flow_id),
            "steps": [
                {
                    "name": s.step_name,
                    "status": s.status,
                    "duration": (s.end_time - s.start_time) if s.end_time else None
                }
                for s in steps
            ]
        }

    def export_flow(self, flow_id: str) -> str:
        """导出数据流为JSON格式（用于可视化）"""
        summary = self.get_flow_summary(flow_id)
        return json.dumps(summary, indent=2, ensure_ascii=False)


class AnomalyDetector:
    """异常检测器

    基于阈值和基线检测系统异常
    """

    def __init__(self):
        self.alert_thresholds: Dict[str, Dict[str, float]] = {
            "latency": {"warning": 2.0, "critical": 5.0},  # 秒
            "error_rate": {"warning": 0.05, "critical": 0.1},  # 5%, 10%
        }
        self.baseline_metrics: Dict[str, float] = {}
        self.alert_history: List[Alert] = []

    def set_baseline(self, name: str, value: float):
        """设置基线值"""
        self.baseline_metrics[name] = value

    def detect_anomaly(
        self,
        metric_name: str,
        current_value: float
    ) -> Tuple[bool, Optional[Alert]]:
        """检测异常

        Returns:
            Tuple[bool, Optional[Alert]]: (是否异常, 告警对象)
        """
        # 检查是否超过阈值
        if metric_name in self.alert_thresholds:
            thresholds = self.alert_thresholds[metric_name]

            if current_value > thresholds.get("critical", float('inf')):
                alert = Alert(
                    level=AlertLevel.CRITICAL,
                    message=f"{metric_name} 超过临界值: {current_value:.2f}",
                    source="anomaly_detector",
                    timestamp=datetime.now().isoformat(),
                    details={"metric": metric_name, "value": current_value}
                )
                self.alert_history.append(alert)
                return True, alert

            elif current_value > thresholds.get("warning", float('inf')):
                alert = Alert(
                    level=AlertLevel.WARNING,
                    message=f"{metric_name} 超过警告值: {current_value:.2f}",
                    source="anomaly_detector",
                    timestamp=datetime.now().isoformat(),
                    details={"metric": metric_name, "value": current_value}
                )
                self.alert_history.append(alert)
                return True, alert

        # 检查是否偏离基线
        if metric_name in self.baseline_metrics:
            baseline = self.baseline_metrics[metric_name]
            deviation = abs(current_value - baseline) / baseline if baseline > 0 else 0

            if deviation > 0.5:  # 偏离超过50%
                alert = Alert(
                    level=AlertLevel.WARNING,
                    message=f"{metric_name} 偏离基线: 当前={current_value:.2f}, 基线={baseline:.2f}",
                    source="anomaly_detector",
                    timestamp=datetime.now().isoformat(),
                    details={"metric": metric_name, "value": current_value, "baseline": baseline}
                )
                self.alert_history.append(alert)
                return True, alert

        return False, None

    def check_latency(self, operation: str, duration: float) -> Optional[Alert]:
        """检查延迟是否正常"""
        _, alert = self.detect_anomaly("latency", duration)

        if alert:
            alert.source = f"latency_check:{operation}"
            return alert

        return None

    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """获取最近的告警"""
        return self.alert_history[-count:]


class DashboardGenerator:
    """仪表盘生成器

    生成监控数据的可视化展示
    """

    def __init__(self):
        self.metrics_history: Dict[str, List[Tuple[float, float]]] = defaultdict(list)  # (timestamp, value)

    def record_metric(self, name: str, value: float):
        """记录指标"""
        self.metrics_history[name].append((time.time(), value))

        # 限制存储数量
        if len(self.metrics_history[name]) > 100:
            self.metrics_history[name] = self.metrics_history[name][-100:]

    def generate_ascii_dashboard(self, metrics: Dict[str, float]) -> str:
        """生成ASCII格式的仪表盘"""
        lines = []

        # 标题
        lines.append("=" * 60)
        lines.append(" Paper Agent System Monitor ".center(60))
        lines.append("=" * 60)
        lines.append(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
        lines.append("-" * 60)

        # 关键指标
        lines.append("\n## Key Metrics")

        for name, value in metrics.items():
            if "latency" in name.lower():
                lines.append(f"  {name}: {value:.3f}s")
            elif "rate" in name.lower():
                lines.append(f"  {name}: {value:.2%}")
            elif "count" in name.lower():
                lines.append(f"  {name}: {int(value)}")
            else:
                lines.append(f"  {name}: {value}")

        lines.append("-" * 60)

        return "\n".join(lines)

    def generate_html_snippet(self) -> str:
        """生成HTML片段（可用于嵌入）"""
        return f"""
        <div id="paper-agent-monitor" style="
            font-family: monospace;
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            max-width: 600px;
        ">
            <h3 style="margin-top: 0;">Paper Agent Monitor</h3>
            <div id="metrics">
                <p>Loading metrics...</p>
            </div>
            <div style="color: #666; font-size: 0.8em;">
                Last updated: {datetime.now().strftime('%H:%M:%S')}
            </div>
        </div>
        """


class AutoRecoveryManager:
    """自动恢复管理器

    当检测到异常时自动执行恢复操作
    """

    def __init__(self):
        self.recovery_actions: Dict[str, callable] = {}
        self.recovery_history: List[Dict[str, Any]] = []

    def register_recovery_action(self, condition: str, action: callable):
        """注册恢复动作

        Args:
            condition: 触发条件（如 "high_latency", "error_rate_spike"）
            action: 恢复动作（异步函数）
        """
        self.recovery_actions[condition] = action
        logger.info(f"Registered recovery action for: {condition}")

    async def execute_recovery(self, alert: Alert) -> bool:
        """执行恢复动作

        Args:
            alert: 告警对象

        Returns:
            bool: 是否恢复成功
        """
        condition = alert.details.get("metric", "")

        if condition in self.recovery_actions:
            action = self.recovery_actions[condition]

            logger.info(f"Executing recovery action for: {condition}")

            try:
                await action(alert)
                self.recovery_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "alert": alert.message,
                    "action": condition,
                    "success": True
                })
                return True

            except Exception as e:
                logger.error(f"Recovery action failed: {e}")
                self.recovery_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "alert": alert.message,
                    "action": condition,
                    "success": False,
                    "error": str(e)
                })
                return False

        logger.warning(f"No recovery action registered for: {condition}")
        return False

    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计"""
        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r.get("success"))

        return {
            "total_recoveries": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0
        }


# 便捷函数
def create_monitor() -> Tuple[DataFlowTracker, AnomalyDetector, AutoRecoveryManager]:
    """创建监控组件"""
    tracker = DataFlowTracker()
    detector = AnomalyDetector()
    recovery = AutoRecoveryManager()

    return tracker, detector, recovery