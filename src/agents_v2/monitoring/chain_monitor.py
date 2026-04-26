"""
Chain Monitor - 链路监控器

监控链路执行事件和状态。
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio


class EventType(str, Enum):
    """事件类型"""
    CHAIN_START = "chain_start"
    CHAIN_END = "chain_end"
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    ERROR = "error"
    WARNING = "warning"
    RETRY = "retry"
    FALLBACK = "fallback"


@dataclass
class ChainEvent:
    """链路事件"""
    event_id: str
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    chain_id: str = ""
    phase: str = ""
    agent: str = ""
    duration_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if isinstance(self.event_type, Enum) else self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "chain_id": self.chain_id,
            "phase": self.phase,
            "agent": self.agent,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class ChainMonitor:
    """
    链路监控器

    功能:
    - 记录链路事件
    - 统计分析
    - 异常检测

    使用示例:
        monitor = ChainMonitor()

        with monitor.track_event("phase_start", phase="literature"):
            # 执行操作
            pass

        stats = monitor.get_stats()
    """

    def __init__(self, max_events: int = 10000):
        """
        初始化链路监控器

        Args:
            max_events: 最大事件数
        """
        self.max_events = max_events
        self._events: List[ChainEvent] = []
        self._event_count = 0
        self._handlers: Dict[EventType, List[Callable]] = {e: [] for e in EventType}

    def record_event(self, event: ChainEvent):
        """记录事件"""
        self._events.append(event)
        self._event_count += 1

        # 裁剪事件列表
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]

        # 触发处理器
        self._trigger_handlers(event)

    def create_event(
        self,
        event_type: EventType,
        chain_id: str = "",
        phase: str = "",
        agent: str = "",
        **kwargs
    ) -> ChainEvent:
        """创建事件"""
        return ChainEvent(
            event_id=f"evt_{self._event_count}",
            event_type=event_type,
            chain_id=chain_id,
            phase=phase,
            agent=agent,
            **kwargs
        )

    def track_event(
        self,
        event_type: EventType,
        chain_id: str = "",
        phase: str = "",
        agent: str = "",
    ):
        """追踪事件的上下文管理器"""
        return ChainEventContext(self, event_type, chain_id, phase, agent)

    def _trigger_handlers(self, event: ChainEvent):
        """触发事件处理器"""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")

    def on_event(self, event_type: EventType, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def get_events(
        self,
        chain_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[ChainEvent]:
        """获取事件列表"""
        events = self._events

        if chain_id:
            events = [e for e in events if e.chain_id == chain_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._events)
        errors = sum(1 for e in self._events if not e.success)
        by_type = {}

        for event_type in EventType:
            count = sum(1 for e in self._events if e.event_type == event_type)
            if count > 0:
                by_type[event_type.value] = count

        return {
            "total_events": total,
            "error_count": errors,
            "error_rate": errors / total if total > 0 else 0,
            "events_by_type": by_type,
            "total_recorded": self._event_count,
        }

    def get_chain_timeline(self, chain_id: str) -> List[Dict[str, Any]]:
        """获取链路时间线"""
        events = self.get_events(chain_id=chain_id, limit=1000)
        return [e.to_dict() for e in events]

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测异常"""
        anomalies = []

        # 检测错误率高的链路
        chain_errors: Dict[str, List[ChainEvent]] = {}
        for event in self._events:
            if event.chain_id and not event.success:
                if event.chain_id not in chain_errors:
                    chain_errors[event.chain_id] = []
                chain_errors[event.chain_id].append(event)

        for chain_id, errors in chain_errors.items():
            error_rate = len(errors) / max(1, len(self.get_events(chain_id=chain_id)))
            if error_rate > 0.5:
                anomalies.append({
                    "type": "high_error_rate",
                    "chain_id": chain_id,
                    "error_rate": error_rate,
                    "error_count": len(errors)
                })

        # 检测长时间运行的事件
        for event in self._events:
            if event.duration_ms > 60000:  # 超过60秒
                anomalies.append({
                    "type": "slow_event",
                    "event_id": event.event_id,
                    "duration_ms": event.duration_ms,
                    "agent": event.agent
                })

        return anomalies

    def clear(self):
        """清除所有事件"""
        self._events.clear()


class ChainEventContext:
    """链路事件上下文"""

    def __init__(
        self,
        monitor: ChainMonitor,
        event_type: EventType,
        chain_id: str,
        phase: str,
        agent: str
    ):
        self.monitor = monitor
        self.event_type = event_type
        self.chain_id = chain_id
        self.phase = phase
        self.agent = agent
        self.start_time: Optional[datetime] = None
        self.event: Optional[ChainEvent] = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        success = exc_type is None

        self.event = self.monitor.create_event(
            event_type=self.event_type,
            chain_id=self.chain_id,
            phase=self.phase,
            agent=self.agent,
            duration_ms=duration_ms,
            success=success,
            error_message=str(exc_val) if exc_val else None
        )

        self.monitor.record_event(self.event)


def create_monitor() -> ChainMonitor:
    """创建链路监控器"""
    return ChainMonitor()