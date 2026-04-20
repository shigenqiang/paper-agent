"""短期记忆（工作记忆）模块"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging
from collections import deque

logger = logging.getLogger(__name__)


class ConversationTurn(BaseModel):
    """对话轮次"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    turn_id: int
    metadata: Optional[Dict[str, Any]] = None


class ShortTermMemory(BaseModel):
    """短期记忆（工作记忆）"""

    session_id: str
    conversation_history: List[ConversationTurn] = []
    current_context: Dict[str, Any] = {}
    max_turns: int = 20  # 最大保存轮次
    context_window: int = 5  # 上下文窗口大小
    created_at: datetime = datetime.now()
    last_accessed: datetime = datetime.now()

    def add_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        """添加对话轮次"""
        turn_id = len(self.conversation_history)
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            turn_id=turn_id,
            metadata=metadata or {}
        )

        self.conversation_history.append(turn)

        # 如果超过最大轮次，移除最旧的
        if len(self.conversation_history) > self.max_turns:
            removed = self.conversation_history.pop(0)
            logger.debug(f"Removed old turn {removed.turn_id} from short-term memory")

        self.last_accessed = datetime.now()
        return turn

    def get_recent_turns(self, n: Optional[int] = None) -> List[ConversationTurn]:
        """获取最近的对话轮次"""
        n = n or self.context_window
        return self.conversation_history[-n:] if self.conversation_history else []

    def get_full_history(self) -> List[ConversationTurn]:
        """获取完整对话历史"""
        return self.conversation_history.copy()

    def get_context_window(self) -> str:
        """获取上下文窗口的字符串表示"""
        recent_turns = self.get_recent_turns()
        context_parts = []
        for turn in recent_turns:
            context_parts.append(f"{turn.role}: {turn.content}")
        return "\n".join(context_parts)

    def get_last_user_message(self) -> Optional[str]:
        """获取最后一条用户消息"""
        for turn in reversed(self.conversation_history):
            if turn.role == "user":
                return turn.content
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """获取最后一条助手消息"""
        for turn in reversed(self.conversation_history):
            if turn.role == "assistant":
                return turn.content
        return None

    def set_context(self, key: str, value: Any) -> None:
        """设置上下文"""
        self.current_context[key] = value
        self.last_accessed = datetime.now()

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self.current_context.get(key, default)

    def clear_context(self) -> None:
        """清空上下文"""
        self.current_context.clear()

    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        if not self.conversation_history:
            return "No conversation history"

        summary_parts = []
        summary_parts.append(f"Session: {self.session_id}")
        summary_parts.append(f"Total turns: {len(self.conversation_history)}")
        summary_parts.append(f"Last activity: {self.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}")

        # 统计用户和助手的轮次
        user_turns = sum(1 for t in self.conversation_history if t.role == "user")
        assistant_turns = sum(1 for t in self.conversation_history if t.role == "assistant")
        summary_parts.append(f"User turns: {user_turns}, Assistant turns: {assistant_turns}")

        return "\n".join(summary_parts)

    def is_stale(self, max_age_minutes: int = 30) -> bool:
        """检查对话是否过期"""
        age = datetime.now() - self.last_accessed
        return age > timedelta(minutes=max_age_minutes)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "conversation_history": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.timestamp.isoformat(),
                    "turn_id": turn.turn_id,
                    "metadata": turn.metadata
                }
                for turn in self.conversation_history
            ],
            "current_context": self.current_context,
            "max_turns": self.max_turns,
            "context_window": self.context_window,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShortTermMemory":
        """从字典创建"""
        conversation_history = [
            ConversationTurn(
                role=turn["role"],
                content=turn["content"],
                timestamp=datetime.fromisoformat(turn["timestamp"]),
                turn_id=turn["turn_id"],
                metadata=turn.get("metadata")
            )
            for turn in data["conversation_history"]
        ]

        return cls(
            session_id=data["session_id"],
            conversation_history=conversation_history,
            current_context=data["current_context"],
            max_turns=data.get("max_turns", 20),
            context_window=data.get("context_window", 5),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
        )
