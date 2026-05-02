"""
Checkpoint Manager - 检查点管理器

提供任务状态持久化和断点恢复功能。
"""
from typing import Any, Callable, Coroutine, Dict, List, Optional
from dataclasses import dataclass, field
from src.agents_v2.logging_config import get_logging_logger

import time
import json

from pathlib import Path

logger = get_logging_logger(__name__)


@dataclass
class AgentState:
    """Agent执行状态"""
    agent_id: str
    status: str  # running/waiting/completed/failed
    current_action: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    local_memory: Dict[str, Any] = field(default_factory=dict)
    checkpoint_ids: List[str] = field(default_factory=list)


@dataclass
class MemorySnapshot:
    """记忆快照"""
    short_term: Dict[str, Any] = field(default_factory=dict)
    session: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)
    episodic: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Checkpoint:
    """任务检查点"""
    task_id: str
    phase: str
    checkpoint_id: str
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, AgentState] = field(default_factory=dict)
    memory_snapshot: MemorySnapshot = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    parent_checkpoint_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 序列化 memory_snapshot
        mem = self.memory_snapshot
        if isinstance(mem, MemorySnapshot):
            mem_dict = {
                "short_term": mem.short_term,
                "session": mem.session,
                "long_term": mem.long_term,
                "episodic": mem.episodic,
            }
        elif isinstance(mem, dict):
            mem_dict = mem
        else:
            mem_dict = {}

        return {
            "task_id": self.task_id,
            "phase": self.phase,
            "checkpoint_id": self.checkpoint_id,
            "state_snapshot": self.state_snapshot,
            "agent_states": {
                k: {
                    "agent_id": v.agent_id,
                    "status": v.status,
                    "current_action": v.current_action,
                    "context": v.context,
                    "local_memory": v.local_memory,
                    "checkpoint_ids": v.checkpoint_ids
                }
                for k, v in self.agent_states.items()
            },
            "memory_snapshot": mem_dict,
            "timestamp": self.timestamp,
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "metadata": self.metadata
        }


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    recovered_phase: str = ""
    checkpoint_id: str = ""
    error: str = ""


class CheckpointManager:
    """
    检查点管理器

    功能:
    - 自动保存检查点
    - 从检查点恢复
    - 清理旧检查点

    使用示例:
        manager = CheckpointManager(storage_path=".checkpoints")

        # 保存检查点
        checkpoint_id = await manager.save_checkpoint(task_id, phase, state)

        # 恢复
        result = await manager.recover_from_checkpoint(checkpoint_id)
    """

    def __init__(
        self,
        storage_path: str = ".checkpoints",
        max_checkpoints_per_task: int = 10
    ):
        self.storage_path = Path(storage_path)
        self.max_checkpoints_per_task = max_checkpoints_per_task
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._task_checkpoints: Dict[str, List[str]] = {}

        # 恢复钩子：注册自定义的恢复逻辑
        self._agent_state_restorer: Optional[Callable[[str, "AgentState"], Coroutine]] = None
        self._memory_restorer: Optional[Callable[["MemorySnapshot"], Coroutine]] = None
        self._state_applier: Optional[Callable[[Dict[str, Any]], Coroutine]] = None

        # 确保存储目录存在
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def register_agent_restorer(self, fn: Callable[[str, "AgentState"], Coroutine]) -> None:
        """注册Agent状态恢复函数"""
        self._agent_state_restorer = fn

    def register_memory_restorer(self, fn: Callable[["MemorySnapshot"], Coroutine]) -> None:
        """注册记忆恢复函数"""
        self._memory_restorer = fn

    def register_state_applier(self, fn: Callable[[Dict[str, Any]], Coroutine]) -> None:
        """注册状态应用函数（用于恢复工作流状态等）"""
        self._state_applier = fn

    async def save_checkpoint(
        self,
        task_id: str,
        phase: str,
        state_snapshot: Dict[str, Any],
        agent_states: Optional[Dict[str, AgentState]] = None,
        memory_snapshot: Optional[MemorySnapshot] = None,
        parent_checkpoint_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存检查点

        Args:
            task_id: 任务ID
            phase: 当前阶段
            state_snapshot: 状态快照
            agent_states: Agent状态
            memory_snapshot: 记忆快照
            parent_checkpoint_id: 父检查点ID
            metadata: 元数据

        Returns:
            str: 检查点ID
        """
        timestamp = time.time()
        checkpoint_id = f"{task_id}_{phase}_{int(timestamp * 1000)}"

        checkpoint = Checkpoint(
            task_id=task_id,
            phase=phase,
            checkpoint_id=checkpoint_id,
            state_snapshot=state_snapshot,
            agent_states=agent_states or {},
            memory_snapshot=memory_snapshot or MemorySnapshot(),
            timestamp=timestamp,
            parent_checkpoint_id=parent_checkpoint_id,
            metadata=metadata or {}
        )

        # 持久化到磁盘
        await self._persist_to_disk(checkpoint_id, checkpoint)

        # 更新内存索引
        self._checkpoints[checkpoint_id] = checkpoint

        if task_id not in self._task_checkpoints:
            self._task_checkpoints[task_id] = []
        self._task_checkpoints[task_id].append(checkpoint_id)

        # 清理旧检查点
        await self._cleanup_old_checkpoints(task_id)

        logger.info(f"Saved checkpoint: {checkpoint_id}")
        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        加载检查点

        Args:
            checkpoint_id: 检查点ID

        Returns:
            Optional[Checkpoint]: 检查点对象
        """
        # 先检查内存
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]

        # 从磁盘加载
        path = self._get_checkpoint_path(checkpoint_id)
        if not path.exists():
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            checkpoint = self._dict_to_checkpoint(data)
            self._checkpoints[checkpoint_id] = checkpoint
            return checkpoint

        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None

    async def recover_from_checkpoint(self, checkpoint_id: str) -> RecoveryResult:
        """
        从检查点恢复

        Args:
            checkpoint_id: 检查点ID

        Returns:
            RecoveryResult: 恢复结果
        """
        checkpoint = await self.load_checkpoint(checkpoint_id)

        if not checkpoint:
            return RecoveryResult(
                success=False,
                error=f"Checkpoint not found: {checkpoint_id}"
            )

        try:
            # 恢复Agent状态
            for agent_id, agent_state in checkpoint.agent_states.items():
                await self._restore_agent_state(agent_id, agent_state)

            # 恢复记忆
            if checkpoint.memory_snapshot:
                await self._restore_memory_snapshot(checkpoint.memory_snapshot)

            # 恢复工作流状态（通过注册的钩子）
            if self._state_applier and checkpoint.state_snapshot:
                try:
                    await self._state_applier(checkpoint.state_snapshot)
                    logger.info(f"Applied state snapshot from checkpoint {checkpoint_id}")
                except Exception as e:
                    logger.warning(f"State applier failed: {e}")

            logger.info(f"Recovered from checkpoint: {checkpoint_id}")

            return RecoveryResult(
                success=True,
                recovered_phase=checkpoint.phase,
                checkpoint_id=checkpoint_id
            )

        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return RecoveryResult(
                success=False,
                checkpoint_id=checkpoint_id,
                error=str(e)
            )

    def get_latest_checkpoint(self, task_id: str) -> Optional[str]:
        """获取任务的最新检查点ID"""
        checkpoints = self._task_checkpoints.get(task_id, [])
        return checkpoints[-1] if checkpoints else None

    def get_checkpoint_chain(self, task_id: str) -> List[str]:
        """获取检查点链"""
        return self._task_checkpoints.get(task_id, [])

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        if checkpoint_id not in self._checkpoints:
            return False

        checkpoint = self._checkpoints[checkpoint_id]

        # 从磁盘删除
        path = self._get_checkpoint_path(checkpoint_id)
        if path.exists():
            path.unlink()

        # 从内存移除
        del self._checkpoints[checkpoint_id]

        # 从任务列表移除
        task_id = checkpoint.task_id
        if task_id in self._task_checkpoints:
            self._task_checkpoints[task_id].remove(checkpoint_id)

        logger.info(f"Deleted checkpoint: {checkpoint_id}")
        return True

    async def _persist_to_disk(self, checkpoint_id: str, checkpoint: Checkpoint) -> None:
        """持久化到磁盘"""
        task_dir = self.storage_path / checkpoint.task_id
        task_dir.mkdir(exist_ok=True)

        path = task_dir / f"{checkpoint_id}.json"

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """获取检查点文件路径"""
        # 从checkpoint_id提取task_id
        parts = checkpoint_id.split('_')
        if len(parts) >= 1:
            task_id = parts[0]
        else:
            task_id = "unknown"

        return self.storage_path / task_id / f"{checkpoint_id}.json"

    def _dict_to_checkpoint(self, data: Dict[str, Any]) -> Checkpoint:
        """将字典转换为Checkpoint对象"""
        # 转换agent_states
        agent_states = {}
        for k, v in data.get("agent_states", {}).items():
            agent_states[k] = AgentState(
                agent_id=v["agent_id"],
                status=v["status"],
                current_action=v.get("current_action", ""),
                context=v.get("context", {}),
                local_memory=v.get("local_memory", {}),
                checkpoint_ids=v.get("checkpoint_ids", [])
            )

        # 转换memory_snapshot
        mem_data = data.get("memory_snapshot", {})
        memory_snapshot = MemorySnapshot(
            short_term=mem_data.get("short_term", {}),
            session=mem_data.get("session", {}),
            long_term=mem_data.get("long_term", {}),
            episodic=mem_data.get("episodic", [])
        )

        return Checkpoint(
            task_id=data["task_id"],
            phase=data["phase"],
            checkpoint_id=data["checkpoint_id"],
            state_snapshot=data.get("state_snapshot", {}),
            agent_states=agent_states,
            memory_snapshot=memory_snapshot,
            timestamp=data.get("timestamp", time.time()),
            parent_checkpoint_id=data.get("parent_checkpoint_id"),
            metadata=data.get("metadata", {})
        )

    async def _restore_agent_state(self, agent_id: str, agent_state: AgentState) -> None:
        """
        恢复Agent状态

        优先使用注册的恢复钩子，否则执行默认恢复逻辑：
        - 恢复 agent context 和 local_memory 到内存缓存
        - 记录恢复日志
        """
        if self._agent_state_restorer:
            try:
                await self._agent_state_restorer(agent_id, agent_state)
                logger.info(f"Restored agent {agent_id} via registered restorer")
                return
            except Exception as e:
                logger.warning(f"Registered restorer failed for agent {agent_id}: {e}, falling back to default")

        # 默认恢复：将状态存入内存缓存供后续查询
        cache_key = f"_restored_agent_{agent_id}"
        self._checkpoints[cache_key] = Checkpoint(
            task_id=agent_id,
            phase="restored",
            checkpoint_id=cache_key,
            state_snapshot={
                "status": agent_state.status,
                "current_action": agent_state.current_action,
                "context": agent_state.context,
                "local_memory": agent_state.local_memory,
            },
            metadata={"restored_from_checkpoint": True, "restored_at": time.time()},
        )
        logger.info(f"Restored agent {agent_id} state (status={agent_state.status}, action={agent_state.current_action})")

    async def _restore_memory_snapshot(self, memory_snapshot: MemorySnapshot) -> None:
        """
        恢复记忆快照

        优先使用注册的恢复钩子，否则尝试通过 UnifiedMemoryManager 恢复：
        - 短期记忆：写入 short_term keys
        - 会话记忆：写入 session entries
        - 长期记忆：写入 long_term entries
        - 情景记忆：写入 episodic entries
        """
        if self._memory_restorer:
            try:
                await self._memory_restorer(memory_snapshot)
                logger.info("Restored memory via registered restorer")
                return
            except Exception as e:
                logger.warning(f"Registered memory restorer failed: {e}, falling back to default")

        # 默认恢复：尝试通过统一记忆管理器恢复
        restored_counts = {"short_term": 0, "session": 0, "long_term": 0, "episodic": 0}

        try:
            from ..memory.unified import UnifiedMemoryManager

            manager = UnifiedMemoryManager()

            # 恢复短期记忆
            for key, value in memory_snapshot.short_term.items():
                try:
                    await manager.short_term.add(key=key, value=value)
                    restored_counts["short_term"] += 1
                except Exception as e:
                    logger.debug(f"Failed to restore short_term key '{key}': {e}")

            # 恢复会话记忆
            for key, value in memory_snapshot.session.items():
                try:
                    await manager.session.add(key=key, value=value)
                    restored_counts["session"] += 1
                except Exception as e:
                    logger.debug(f"Failed to restore session key '{key}': {e}")

            # 恢复长期记忆
            for key, value in memory_snapshot.long_term.items():
                try:
                    await manager.long_term.add(key=key, value=value)
                    restored_counts["long_term"] += 1
                except Exception as e:
                    logger.debug(f"Failed to restore long_term key '{key}': {e}")

            # 恢复情景记忆
            for entry in memory_snapshot.episodic:
                try:
                    await manager.episodic.add(**entry)
                    restored_counts["episodic"] += 1
                except Exception as e:
                    logger.debug(f"Failed to restore episodic entry: {e}")

        except ImportError:
            logger.warning("UnifiedMemoryManager not available, memory snapshot stored but not applied")
        except Exception as e:
            logger.warning(f"Memory restoration partially failed: {e}")

        total = sum(restored_counts.values())
        logger.info(f"Memory snapshot restored: {restored_counts} (total={total})")

    async def _cleanup_old_checkpoints(self, task_id: str) -> None:
        """清理旧检查点"""
        checkpoints = self._task_checkpoints.get(task_id, [])

        if len(checkpoints) <= self.max_checkpoints_per_task:
            return

        # 删除超出限制的旧检查点
        to_delete = checkpoints[:-self.max_checkpoints_per_task]

        for checkpoint_id in to_delete:
            await self.delete_checkpoint(checkpoint_id)


def create_checkpoint_manager(
    storage_path: str = ".checkpoints",
    max_checkpoints_per_task: int = 10
) -> CheckpointManager:
    """创建检查点管理器"""
    return CheckpointManager(
        storage_path=storage_path,
        max_checkpoints_per_task=max_checkpoints_per_task
    )
