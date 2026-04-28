"""
Checkpoint Manager - 检查点管理器

提供任务状态持久化和断点恢复功能。
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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
            "memory_snapshot": self.memory_snapshot,
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

        # 确保存储目录存在
        self.storage_path.mkdir(parents=True, exist_ok=True)

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
        """恢复Agent状态"""
        # 实际实现中，这里会调用Agent的恢复方法
        logger.debug(f"Restored state for agent: {agent_id}, status: {agent_state.status}")

    async def _restore_memory_snapshot(self, memory_snapshot: MemorySnapshot) -> None:
        """恢复记忆快照"""
        # 实际实现中，这里会恢复各层记忆
        logger.debug("Restored memory snapshot")

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
