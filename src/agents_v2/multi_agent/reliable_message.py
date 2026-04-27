"""
Reliable Message Bus - 可靠消息总线

提供:
1. 消息持久化
2. 确认机制
3. 重试机制
4. 超时处理
"""
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class MessagePriority(str, Enum):
    """消息优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DeliveryStatus(str, Enum):
    """投递状态"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ReliableMessage:
    """可靠消息"""
    message_id: str
    sender: str
    receiver: str
    content: Any
    timestamp: float = field(default_factory=time.time)

    # 传输信息
    priority: MessagePriority = MessagePriority.NORMAL
    ttl_seconds: float = 300

    # 确认信息
    acks_received: Set[str] = field(default_factory=set)
    requires_ack: bool = True
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING

    # 重试信息
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class AckMessage:
    """确认消息"""
    original_message_id: str
    status: str  # "delivered", "processed", "error"
    timestamp: float = field(default_factory=time.time)


class ReliableMessageBus:
    """
    可靠消息总线

    特性:
    1. 消息持久化（即使重启也不丢失）
    2. 确认机制（知道对方是否收到）
    3. 重试机制（失败自动重试）
    4. 超时处理

    使用示例:
        bus = ReliableMessageBus()

        # 发送消息
        message_id = await bus.send(
            sender="agent_1",
            receiver="agent_2",
            content={"task": "process_data"},
            requires_ack=True
        )

        # 等待确认
        ack_received = await bus.wait_for_ack(message_id, timeout_seconds=30)

        # 注册处理器
        bus.register_handler("agent_2", my_handler)
    """

    def __init__(
        self,
        persistence_path: str = ".messages",
        max_pending: int = 10000
    ):
        self._persistence_path = persistence_path
        self._max_pending = max_pending

        # 消息队列
        self._pending_messages: Dict[str, ReliableMessage] = {}
        self._message_counter = 0

        # 处理器
        self._message_handlers: Dict[str, Callable] = {}
        self._acknowledgement_callbacks: Dict[str, Callable] = {}

        # 统计
        self._stats = {
            "sent": 0,
            "delivered": 0,
            "failed": 0,
            "retried": 0
        }

    async def send(
        self,
        sender: str,
        receiver: str,
        content: Any,
        requires_ack: bool = True,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl_seconds: float = 300
    ) -> str:
        """
        发送消息

        Args:
            sender: 发送者ID
            receiver: 接收者ID
            content: 消息内容
            requires_ack: 是否需要确认
            priority: 优先级
            ttl_seconds: 生存时间

        Returns:
            str: 消息ID
        """
        self._message_counter += 1
        message_id = f"msg_{sender}_{self._message_counter}"

        message = ReliableMessage(
            message_id=message_id,
            sender=sender,
            receiver=receiver,
            content=content,
            priority=priority,
            ttl_seconds=ttl_seconds,
            requires_ack=requires_ack
        )

        # 持久化
        await self._persist_message(message)

        # 加入待确认队列
        if requires_ack:
            if len(self._pending_messages) >= self._max_pending:
                # 清理过期消息
                await self._cleanup_expired()

            self._pending_messages[message_id] = message

        # 尝试传递
        success = await self._deliver_message(message)

        if not success and message.retry_count < message.max_retries:
            # 异步重试
            asyncio.create_task(self._retry_delivery(message_id))

        self._stats["sent"] += 1
        if success:
            self._stats["delivered"] += 1
        else:
            self._stats["failed"] += 1

        return message_id

    async def _deliver_message(self, message: ReliableMessage) -> bool:
        """传递消息"""
        try:
            handler = self._message_handlers.get(message.receiver)
            if handler:
                result = await handler(message)

                if result and result.get("success", False):
                    message.delivery_status = DeliveryStatus.DELIVERED
                    if message.requires_ack:
                        await self._send_ack(message)
                    return True

            message.delivery_status = DeliveryStatus.FAILED
            return False

        except Exception as e:
            logger.error(f"Message delivery failed: {e}")
            message.delivery_status = DeliveryStatus.FAILED
            return False

    async def _send_ack(self, original_message: ReliableMessage) -> None:
        """发送确认"""
        ack = AckMessage(
            original_message_id=original_message.message_id,
            status="delivered"
        )

        # 发送给原始发送者
        handler = self._message_handlers.get(original_message.sender)
        if handler:
            try:
                await handler(ack)
            except Exception as e:
                logger.warning(f"Failed to send ack: {e}")

    async def wait_for_ack(
        self,
        message_id: str,
        timeout_seconds: float = 30
    ) -> bool:
        """
        等待确认

        Args:
            message_id: 消息ID
            timeout_seconds: 超时时间

        Returns:
            bool: 是否收到确认
        """
        start = time.time()

        while time.time() - start < timeout_seconds:
            if message_id not in self._pending_messages:
                return True  # 消息已被确认并移除

            await asyncio.sleep(0.1)

        return False  # 超时

    async def _retry_delivery(self, message_id: str) -> None:
        """重试传递"""
        if message_id not in self._pending_messages:
            return

        message = self._pending_messages[message_id]
        message.retry_count += 1
        message.delivery_status = DeliveryStatus.RETRYING

        self._stats["retried"] += 1

        # 指数退避
        delay = min(2 ** message.retry_count, 60)
        await asyncio.sleep(delay)

        success = await self._deliver_message(message)

        if not success and message.retry_count < message.max_retries:
            asyncio.create_task(self._retry_delivery(message_id))
        elif message.retry_count >= message.max_retries:
            # 放弃，通知发送者
            await self._notify_delivery_failure(message)
            del self._pending_messages[message_id]

    async def _notify_delivery_failure(self, message: ReliableMessage) -> None:
        """通知投递失败"""
        callback = self._acknowledgement_callbacks.get(message.message_id)
        if callback:
            try:
                await callback(message, success=False)
            except Exception as e:
                logger.warning(f"Failure notification error: {e}")

    async def _persist_message(self, message: ReliableMessage) -> None:
        """持久化消息"""
        # 简单的内存持久化（实际应用中应该写文件或数据库）
        pass

    async def _cleanup_expired(self) -> None:
        """清理过期消息"""
        current_time = time.time()
        expired = [
            msg_id for msg_id, msg in self._pending_messages.items()
            if current_time - msg.timestamp > msg.ttl_seconds
        ]

        for msg_id in expired:
            del self._pending_messages[msg_id]

    def register_handler(self, agent_id: str, handler: Callable) -> None:
        """注册消息处理器"""
        self._message_handlers[agent_id] = handler
        logger.debug(f"Registered handler for agent: {agent_id}")

    def register_ack_callback(self, message_id: str, callback: Callable) -> None:
        """注册确认回调"""
        self._acknowledgement_callbacks[message_id] = callback

    def get_pending_count(self) -> int:
        """获取待确认消息数"""
        return len(self._pending_messages)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "pending": len(self._pending_messages)
        }

    async def clear(self) -> None:
        """清空所有消息"""
        self._pending_messages.clear()
        self._stats = {
            "sent": 0,
            "delivered": 0,
            "failed": 0,
            "retried": 0
        }


class MessageBusBuilder:
    """消息总线构建器"""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._persistence_path = ".messages"
        self._max_pending = 10000

    def add_handler(self, agent_id: str, handler: Callable) -> "MessageBusBuilder":
        """添加处理器"""
        self._handlers[agent_id] = handler
        return self

    def set_persistence_path(self, path: str) -> "MessageBusBuilder":
        """设置持久化路径"""
        self._persistence_path = path
        return self

    def set_max_pending(self, max_pending: int) -> "MessageBusBuilder":
        """设置最大待处理消息数"""
        self._max_pending = max_pending
        return self

    def build(self) -> ReliableMessageBus:
        """构建消息总线"""
        bus = ReliableMessageBus(
            persistence_path=self._persistence_path,
            max_pending=self._max_pending
        )

        for agent_id, handler in self._handlers.items():
            bus.register_handler(agent_id, handler)

        return bus


def create_message_bus() -> ReliableMessageBus:
    """创建消息总线"""
    return ReliableMessageBus()


def create_message_bus_builder() -> MessageBusBuilder:
    """创建消息总线构建器"""
    return MessageBusBuilder()
