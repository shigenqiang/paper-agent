"""
会话级记忆 - Session Memory

职责: 任务内跨Agent共享
- 位置: Redis / 内存
- 范围: 任务内跨Agent共享
- 特性: 自动摘要生成，定期将重要信息沉淀到长期记忆
- 实现: 借鉴Mem0的滚动摘要机制
"""
import asyncio
import time
import json
import hashlib
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from .types import MemoryEntry, MemoryType


@dataclass
class SessionConfig:
    """会话配置"""
    session_id: str
    task_id: str
    max_entries: int = 500          # 最大条目数
    summary_trigger_count: int = 30  # 触发摘要的消息数
    summary_interval_seconds: float = 300  # 摘要生成间隔（5分钟）
    persist_threshold: float = 0.7  # 持久化到长期记忆的阈值


class SessionMemory:
    """
    会话级记忆 - 任务内跨Agent共享

    特点:
    - 多Agent并发安全 (通过asyncio.Lock)
    - 自动摘要生成
    - 支持将重要信息同步到长期记忆
    """

    def __init__(
        self,
        config: SessionConfig,
        long_term_memory: Optional[Any] = None  # 长期记忆引用
    ):
        self.config = config
        self.long_term_memory = long_term_memory

        # 内存存储
        self._entries: Dict[str, MemoryEntry] = {}
        self._agent_contexts: Dict[str, Dict[str, Any]] = {}  # agent_id -> context
        self._shared_messages: List[Dict[str, Any]] = []  # 共享消息历史

        # 摘要状态
        self._last_summary_time: float = 0
        self._summary_count: int = 0

        # 锁
        self._lock = asyncio.Lock()

    async def store_message(
        self,
        agent_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        存储跨Agent共享的消息

        Args:
            agent_id: Agent ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据

        Returns:
            message_id
        """
        async with self._lock:
            # 生成消息ID
            msg_id = hashlib.md5(
                f"{self.config.session_id}{agent_id}{content}{time.time()}".encode()
            ).hexdigest()[:16]

            message = {
                "message_id": msg_id,
                "agent_id": agent_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "timestamp": time.time()
            }

            self._shared_messages.append(message)

            # 更新Agent上下文
            if agent_id not in self._agent_contexts:
                self._agent_contexts[agent_id] = {
                    "message_count": 0,
                    "last_active": time.time()
                }
            self._agent_contexts[agent_id]["message_count"] += 1
            self._agent_contexts[agent_id]["last_active"] = time.time()

            # 检查是否需要生成摘要
            if len(self._shared_messages) >= self.config.summary_trigger_count:
                await self._maybe_generate_summary()

            return msg_id

    async def get_messages(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取共享消息

        Args:
            agent_id: 可选的Agent过滤
            limit: 返回数量限制
            offset: 起始偏移

        Returns:
            消息列表
        """
        async with self._lock:
            messages = self._shared_messages

            if agent_id:
                messages = [m for m in messages if m["agent_id"] == agent_id]

            return messages[offset:offset + limit]

    async def get_context_for_agent(
        self,
        agent_id: str,
        max_messages: int = 20
    ) -> str:
        """
        为特定Agent生成上下文字符串

        Args:
            agent_id: Agent ID
            max_messages: 最大消息数

        Returns:
            格式化的上下文字符串
        """
        messages = await self.get_messages(limit=max_messages)

        if not messages:
            return ""

        parts = [f"## Session: {self.config.session_id}\n"]
        parts.append(f"### Shared Messages (last {len(messages)})\n")

        for msg in messages[-max_messages:]:
            parts.append(
                f"[{msg['agent_id']}] {msg['role']}: {msg['content'][:100]}..."
            )

        return "\n".join(parts)

    async def set_agent_context(
        self,
        agent_id: str,
        context_key: str,
        context_value: Any
    ) -> None:
        """
        设置Agent特定上下文（跨Agent共享）

        Args:
            agent_id: Agent ID
            context_key: 上下文键
            context_value: 上下文值
        """
        async with self._lock:
            if agent_id not in self._agent_contexts:
                self._agent_contexts[agent_id] = {}

            self._agent_contexts[agent_id][context_key] = context_value
            self._agent_contexts[agent_id]["last_active"] = time.time()

    async def get_agent_context(
        self,
        agent_id: str,
        context_key: str,
        default: Any = None
    ) -> Any:
        """获取Agent上下文"""
        async with self._lock:
            return self._agent_contexts.get(agent_id, {}).get(context_key, default)

    async def get_all_agent_contexts(self) -> Dict[str, Dict[str, Any]]:
        """获取所有Agent的上下文"""
        async with self._lock:
            return self._agent_contexts.copy()

    async def _maybe_generate_summary(self) -> None:
        """检查并生成摘要"""
        current_time = time.time()

        # 检查时间间隔
        if current_time - self._last_summary_time < self.config.summary_interval_seconds:
            return

        await self.generate_summary()
        self._last_summary_time = current_time

    async def generate_summary(self) -> str:
        """
        生成会话摘要 (待集成LLM)

        当前实现为简单版本，完整版需要LLM参与

        Returns:
            摘要字符串
        """
        async with self._lock:
            if not self._shared_messages:
                return ""

            self._summary_count += 1

            # 简单摘要：统计信息
            agent_counts = defaultdict(int)
            total_messages = len(self._shared_messages)

            for msg in self._shared_messages:
                agent_counts[msg["agent_id"]] += 1

            summary = f"""## Session Summary (Summary #{self._summary_count})

### Statistics
- Total Messages: {total_messages}
- Session Duration: {time.time() - self._shared_messages[0]['timestamp']:.0f}s
- Agents: {len(agent_counts)}

### Agent Activity
"""

            for agent_id, count in agent_counts.items():
                summary += f"- {agent_id}: {count} messages\n"

            # 检查是否应该持久化到长期记忆
            if self.long_term_memory and self._summary_count % 3 == 0:
                # 每3次摘要持久化一次
                await self._persist_summary_to_long_term(summary)

            return summary

    async def _persist_summary_to_long_term(self, summary: str) -> None:
        """将摘要持久化到长期记忆"""
        if not self.long_term_memory:
            return

        try:
            await self.long_term_memory.remember(
                key=f"session_summary_{self.config.session_id}_{self._summary_count}",
                value={
                    "session_id": self.config.session_id,
                    "task_id": self.config.task_id,
                    "summary": summary,
                    "message_count": len(self._shared_messages)
                },
                tags=["session_summary", self.config.task_id],
                persist=True,
                importance=0.6
            )
        except Exception:
            pass  # 静默失败，不影响主流程

    async def sync_to_long_term(
        self,
        key: str,
        value: Any,
        importance: float = 0.5
    ) -> None:
        """
        同步重要记忆到长期记忆

        Args:
            key: 记忆键
            value: 记忆值
            importance: 重要性
        """
        if not self.long_term_memory:
            return

        if importance >= self.config.persist_threshold:
            await self.long_term_memory.remember(
                key=key,
                value=value,
                tags=["synced_from_session", self.config.task_id],
                persist=True,
                importance=importance
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "session_id": self.config.session_id,
            "task_id": self.config.task_id,
            "total_messages": len(self._shared_messages),
            "summary_count": self._summary_count,
            "active_agents": len(self._agent_contexts),
            "memory_type": MemoryType.SESSION.value
        }
