"""
Agent Communication Protocol - Agent通信协议

标准化的Agent间通信协议实现。
"""
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import uuid
import logging

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """消息类型"""
    REQUEST = "request"      # 请求
    RESPONSE = "response"    # 响应
    QUERY = "query"          # 查询
    NOTIFY = "notify"        # 通知
    ERROR = "error"          # 错误
    HANDOFF = "handoff"     # 交接
    FEEDBACK = "feedback"   # 反馈
    HEARTBEAT = "heartbeat"  # 心跳


class MessagePriority(str, Enum):
    """消息优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Attachment:
    """附件"""
    name: str
    content_type: str
    data: Any


@dataclass
class AgentMessage:
    """
    Agent通信消息格式

    Attributes:
        id: 消息唯一ID (UUID)
        sender: 发送者Agent ID
        receiver: 接收者 (None=广播)
        message_type: 消息类型
        content: 消息内容
        metadata: 元数据
        timestamp: 时间戳
        reply_to: 回复目标消息ID
        conversation_id: 对话ID
        priority: 优先级
        attachments: 附件列表
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: Optional[str] = None  # None = broadcast
    message_type: MessageType = MessageType.REQUEST
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None
    conversation_id: str = ""
    priority: MessagePriority = MessagePriority.NORMAL
    attachments: List[Attachment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value if isinstance(self.message_type, Enum) else self.message_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "conversation_id": self.conversation_id,
            "priority": self.priority.value if isinstance(self.priority, Enum) else self.priority,
            "attachments": [
                {"name": a.name, "content_type": a.content_type}
                for a in self.attachments
            ]
        }


class AgentCommunicationBus:
    """
    Agent通信总线

    提供标准化的Agent间通信。

    使用示例:
        bus = AgentCommunicationBus()

        # 订阅消息
        await bus.subscribe(agent, [MessageType.REQUEST, MessageType.QUERY])

        # 发布消息
        await bus.publish(AgentMessage(
            sender="agent_1",
            receiver="agent_2",
            message_type=MessageType.REQUEST,
            content="process_task"
        ))

        # 接收消息
        async for message in bus.receive("agent_2"):
            print(message.content)
    """

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self._subscribers: Dict[str, Set['Agent']] = {}
        self._message_queues: Dict[str, asyncio.Queue] = {}
        self._message_history: List[AgentMessage] = []
        self._routing_rules: Dict[MessageType, Callable] = {}
        self._conversation_index: Dict[str, List[AgentMessage]] = {}

    async def publish(self, message: AgentMessage) -> None:
        """
        发布消息

        Args:
            message: 消息对象
        """
        # 记录历史
        self._message_history.append(message)
        if len(self._message_history) > self.max_history:
            self._message_history = self._message_history[-self.max_history:]

        # 更新对话索引
        if message.conversation_id:
            if message.conversation_id not in self._conversation_index:
                self._conversation_index[message.conversation_id] = []
            self._conversation_index[message.conversation_id].append(message)

        # 路由消息
        if message.receiver:
            # 单播
            await self._deliver_to_agent(message.receiver, message)
        else:
            # 广播
            await self._broadcast(message)

    async def subscribe(self, agent: 'Agent', message_types: List[MessageType]) -> None:
        """
        订阅消息类型

        Args:
            agent: Agent实例
            message_types: 感兴趣的消息类型列表
        """
        agent_id = agent.id

        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = set()
            self._message_queues[agent_id] = asyncio.Queue()

        for msg_type in message_types:
            # 存储订阅关系
            pass

        logger.debug(f"Agent {agent_id} subscribed to {[mt.value for mt in message_types]}")

    async def receive(self, agent_id: str) -> AgentMessage:
        """
        接收消息（异步迭代器）

        Args:
            agent_id: Agent ID

        Yields:
            AgentMessage: 收到的消息
        """
        queue = self._message_queues.get(agent_id)
        if not queue:
            queue = asyncio.Queue()
            self._message_queues[agent_id] = queue

        while True:
            try:
                message = await queue.get()
                yield message
            except asyncio.CancelledError:
                break

    async def _deliver_to_agent(self, agent_id: str, message: AgentMessage) -> None:
        """投递消息到指定Agent"""
        queue = self._message_queues.get(agent_id)
        if queue:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(f"Message queue full for agent {agent_id}")

    async def _broadcast(self, message: AgentMessage) -> None:
        """广播消息到所有订阅者"""
        for agent_id, queue in self._message_queues.items():
            if agent_id != message.sender:  # 不发给自己
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    pass

    def get_conversation(self, conversation_id: str) -> List[AgentMessage]:
        """获取对话历史"""
        return self._conversation_index.get(conversation_id, [])

    def get_history(
        self,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentMessage]:
        """获取消息历史"""
        messages = self._message_history

        if sender:
            messages = [m for m in messages if m.sender == sender]

        if receiver:
            messages = [m for m in messages if m.receiver == receiver]

        return messages[-limit:]


class Agent:
    """Agent基类（用于通信协议演示）"""

    def __init__(self, agent_id: str, bus: Optional[AgentCommunicationBus] = None):
        self.id = agent_id
        self.bus = bus
        self._running = False

    async def send_message(
        self,
        receiver: str,
        content: str,
        message_type: MessageType = MessageType.REQUEST,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """发送消息"""
        if not self.bus:
            return ""

        message = AgentMessage(
            sender=self.id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            priority=priority,
            metadata=metadata or {},
            conversation_id=f"{self.id}_{receiver}"
        )

        await self.bus.publish(message)
        return message.id

    async def broadcast(
        self,
        content: str,
        message_type: MessageType = MessageType.NOTIFY
    ) -> str:
        """广播消息"""
        if not self.bus:
            return ""

        message = AgentMessage(
            sender=self.id,
            receiver=None,  # 广播
            message_type=message_type,
            content=content
        )

        await self.bus.publish(message)
        return message.id

    async def receive(self) -> AgentMessage:
        """接收消息"""
        if not self.bus:
            raise StopAsyncIteration

        async for msg in self.bus.receive(self.id):
            return msg


def create_communication_bus(max_history: int = 10000) -> AgentCommunicationBus:
    """创建通信总线"""
    return AgentCommunicationBus(max_history=max_history)
