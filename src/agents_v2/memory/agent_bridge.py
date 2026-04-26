"""
Agent与记忆系统桥接 - Agent Memory Bridge

提供:
- AgentMemoryBridge: 自动记录和检索
- ContextInjector: 上下文自动注入
"""
import asyncio
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .unified import UnifiedMemoryManager
    from .types import MemoryEntry


class AgentMemoryBridge:
    """
    Agent与记忆系统桥接

    职责:
    - 自动记录Agent执行
    - 上下文自动注入
    - 记忆自动提取触发
    - 执行历史同步
    """

    def __init__(self, memory_manager: "UnifiedMemoryManager"):
        self.memory_manager = memory_manager
        self._agent_contexts: Dict[str, Dict[str, Any]] = {}
        self._extraction_cache: Dict[str, List["MemoryEntry"]] = {}

    async def record_and_retrieve(
        self,
        agent_id: str,
        task_id: str,
        action: str,
        result: Any = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0
    ) -> str:
        """
        记录Agent执行并检索相关记忆

        Args:
            agent_id: Agent ID
            task_id: 任务ID
            action: 执行的动作
            result: 执行结果
            context_snapshot: 上下文快照
            duration_ms: 执行时长

        Returns:
            episode_id
        """
        # 1. 记录执行情节
        episode_id = await self.memory_manager.record_episode(
            agent_id=agent_id,
            action=action,
            result=result,
            context_snapshot=context_snapshot,
            duration_ms=duration_ms,
            success=result is not None
        )

        # 2. 更新Agent上下文
        await self._update_agent_context(agent_id, task_id, action, result)

        # 3. 触发相关记忆检索
        related_memories = await self._retrieve_related_memories(
            agent_id=agent_id,
            task_id=task_id,
            action=action
        )

        return episode_id

    async def _update_agent_context(
        self,
        agent_id: str,
        task_id: str,
        action: str,
        result: Any
    ) -> None:
        """更新Agent上下文缓存"""
        if agent_id not in self._agent_contexts:
            self._agent_contexts[agent_id] = {
                "task_id": task_id,
                "actions": [],
                "last_result": None,
                "last_action_time": 0
            }

        context = self._agent_contexts[agent_id]
        context["actions"].append({
            "action": action,
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        })
        context["last_result"] = result
        context["last_action_time"] = asyncio.get_event_loop().time()

    async def _retrieve_related_memories(
        self,
        agent_id: str,
        task_id: str,
        action: str,
        limit: int = 5
    ) -> List[Any]:
        """检索相关记忆"""
        query = f"{agent_id} {task_id} {action}"
        results = await self.memory_manager.search(
            query=query,
            limit=limit
        )
        return results

    async def inject_context(
        self,
        agent_id: str,
        task_id: str,
        max_tokens: int = 4096
    ) -> str:
        """
        获取Agent的上下文字符串

        Args:
            agent_id: Agent ID
            task_id: 任务ID
            max_tokens: 最大token数

        Returns:
            上下文字符串
        """
        context = await self.memory_manager.get_context_for_agent(
            agent_id=agent_id,
            max_tokens=max_tokens
        )
        return context

    async def trigger_memory_extraction(
        self,
        messages: List[Dict[str, Any]],
        task_id: str
    ) -> Dict[str, List[str]]:
        """
        触发记忆提取

        Args:
            messages: 消息列表
            task_id: 任务ID

        Returns:
            提取统计
        """
        existing_memories = await self.memory_manager.long_term.search(
            query=task_id,
            limit=100
        )

        stats = await self.memory_manager.extractor.extract_and_store(
            messages=messages,
            memory_manager=self.memory_manager,
            task_id=task_id,
            existing_memories=existing_memories
        )

        return stats

    async def get_agent_execution_history(
        self,
        agent_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取Agent执行历史

        Args:
            agent_id: Agent ID
            limit: 返回数量

        Returns:
            执行历史列表
        """
        context = self._agent_contexts.get(agent_id, {})
        actions = context.get("actions", [])
        return actions[-limit:]

    async def get_task_progress(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """
        获取任务进度

        Args:
            task_id: 任务ID

        Returns:
            任务进度信息
        """
        timeline = await self.memory_manager.episodic.get_task_timeline(task_id)
        summary = await self.memory_manager.episodic.get_task_summary(task_id)

        return {
            "task_id": task_id,
            "timeline": timeline,
            "summary": summary,
            "progress_percentage": self._calculate_progress(timeline)
        }

    def _calculate_progress(self, timeline: List[Dict[str, Any]]) -> float:
        """计算任务完成度"""
        if not timeline:
            return 0.0

        successful = sum(1 for e in timeline if e.get("success", False))
        return successful / len(timeline) if timeline else 0.0

    async def find_similar_past_tasks(
        self,
        current_task_id: str,
        current_action: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        查找相似的过去任务

        Args:
            current_task_id: 当前任务ID
            current_action: 当前动作
            limit: 返回数量

        Returns:
            相似任务列表
        """
        query = f"{current_action}"
        results = await self.memory_manager.search(
            query=query,
            limit=limit * 2
        )

        similar_tasks = []
        for result in results:
            if hasattr(result, 'metadata') and result.metadata:
                task_id = result.metadata.get("task_id")
                if task_id and task_id != current_task_id:
                    similar_tasks.append({
                        "task_id": task_id,
                        "content": str(result.content)[:200],
                        "similarity": 0.0  # 简化，实际应计算真实相似度
                    })

            if len(similar_tasks) >= limit:
                break

        return similar_tasks


class ContextInjector:
    """
    上下文自动注入器

    职责:
    - 自动将记忆上下文注入Agent
    - 定时刷新上下文
    - 条件触发注入
    """

    def __init__(self, bridge: AgentMemoryBridge):
        self.bridge = bridge
        self._injection_enabled = True
        self._last_injection_time: Dict[str, float] = {}
        self._injection_interval = 60  # 秒

    async def should_inject(
        self,
        agent_id: str,
        force: bool = False
    ) -> bool:
        """
        判断是否应该注入上下文

        Args:
            agent_id: Agent ID
            force: 强制注入

        Returns:
            是否应该注入
        """
        if not self._injection_enabled and not force:
            return False

        if force:
            return True

        last_time = self._last_injection_time.get(agent_id, 0)
        current_time = asyncio.get_event_loop().time()

        return (current_time - last_time) >= self._injection_interval

    async def inject(
        self,
        agent_id: str,
        task_id: str,
        agent: Any,
        force: bool = False
    ) -> bool:
        """
        执行上下文注入

        Args:
            agent_id: Agent ID
            task_id: 任务ID
            agent: Agent实例
            force: 强制注入

        Returns:
            是否成功注入
        """
        if not await self.should_inject(agent_id, force):
            return False

        try:
            context = await self.bridge.inject_context(
                agent_id=agent_id,
                task_id=task_id
            )

            # 注入到Agent的上下文字段
            if hasattr(agent, 'memory_context'):
                agent.memory_context = context
            elif hasattr(agent, 'context'):
                agent.context = context

            self._last_injection_time[agent_id] = asyncio.get_event_loop().time()
            return True

        except Exception:
            return False

    def enable(self) -> None:
        """启用自动注入"""
        self._injection_enabled = True

    def disable(self) -> None:
        """禁用自动注入"""
        self._injection_enabled = False

    def set_interval(self, seconds: float) -> None:
        """
        设置注入间隔

        Args:
            seconds: 间隔秒数
        """
        self._injection_interval = seconds
