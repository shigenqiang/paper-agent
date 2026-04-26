"""
上下文持久化 - Checkpoint Persistence

支持检查点保存和恢复机制，用于:
1. 任务中断恢复
2. 状态回滚
3. 增量检查点
"""
import os
import json
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ContextCheckpoint:
    """上下文检查点"""
    checkpoint_id: str
    task_id: str
    context_data: Dict[str, Any]
    state: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """序列化检查点"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "context_data": self.context_data,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "version": self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextCheckpoint":
        """反序列化检查点"""
        data = data.copy()
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class ContextPersistence:
    """
    上下文持久化管理器

    功能:
    - 保存/加载检查点
    - 自动清理过期检查点
    - 检查点列表管理
    """

    def __init__(self, storage_path: str = ".checkpoints"):
        self.storage_path = Path(storage_path)
        self._index_path = self.storage_path / "index.json"
        self._lock = asyncio.Lock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """获取检查点文件路径"""
        return self.storage_path / f"{checkpoint_id}.json"

    def _load_index(self) -> Dict[str, Any]:
        """加载索引"""
        if not self._index_path.exists():
            return {"checkpoints": {}, "task_index": {}}

        try:
            with open(self._index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"checkpoints": {}, "task_index": {}}

    def _save_index(self, index: Dict[str, Any]) -> None:
        """保存索引"""
        with open(self._index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    async def save_checkpoint(
        self,
        task_id: str,
        context_data: Dict[str, Any],
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存检查点

        Args:
            task_id: 任务ID
            context_data: 上下文数据
            state: 状态数据
            metadata: 额外元数据

        Returns:
            checkpoint_id
        """
        async with self._lock:
            checkpoint_id = f"{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

            checkpoint = ContextCheckpoint(
                checkpoint_id=checkpoint_id,
                task_id=task_id,
                context_data=context_data,
                state=state,
                metadata=metadata or {}
            )

            # 保存检查点文件
            checkpoint_path = self._get_checkpoint_path(checkpoint_id)
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

            # 更新索引
            index = self._load_index()
            index["checkpoints"][checkpoint_id] = {
                "path": str(checkpoint_path),
                "task_id": task_id,
                "created_at": checkpoint.created_at.isoformat(),
                "size": checkpoint_path.stat().st_size
            }

            # 更新任务索引
            if task_id not in index["task_index"]:
                index["task_index"][task_id] = []
            index["task_index"][task_id].append(checkpoint_id)

            self._save_index(index)

            return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[ContextCheckpoint]:
        """
        加载检查点

        Args:
            checkpoint_id: 检查点ID

        Returns:
            ContextCheckpoint或None
        """
        checkpoint_path = self._get_checkpoint_path(checkpoint_id)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ContextCheckpoint.from_dict(data)
        except Exception:
            return None

    async def list_checkpoints(self, task_id: Optional[str] = None) -> List[str]:
        """
        列出检查点

        Args:
            task_id: 可选的任务ID过滤

        Returns:
            检查点ID列表
        """
        index = self._load_index()

        if task_id:
            return index.get("task_index", {}).get(task_id, [])

        return list(index.get("checkpoints", {}).keys())

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        删除检查点

        Args:
            checkpoint_id: 检查点ID

        Returns:
            是否成功删除
        """
        async with self._lock:
            checkpoint_path = self._get_checkpoint_path(checkpoint_id)

            if not checkpoint_path.exists():
                return False

            # 获取索引
            index = self._load_index()
            checkpoint_info = index.get("checkpoints", {}).get(checkpoint_id)

            if not checkpoint_info:
                return False

            # 删除文件
            checkpoint_path.unlink()

            # 更新索引
            task_id = checkpoint_info.get("task_id")
            if task_id and task_id in index.get("task_index", {}):
                index["task_index"][task_id] = [
                    cid for cid in index["task_index"][task_id]
                    if cid != checkpoint_id
                ]

            del index["checkpoints"][checkpoint_id]
            self._save_index(index)

            return True

    async def cleanup_old_checkpoints(self, task_id: str, keep_count: int = 5) -> int:
        """
        清理旧的检查点，保留最新的N个

        Args:
            task_id: 任务ID
            keep_count: 保留数量

        Returns:
            删除数量
        """
        async with self._lock:
            checkpoint_ids = await self.list_checkpoints(task_id)

            if len(checkpoint_ids) <= keep_count:
                return 0

            # 按时间排序，保留最新的
            to_delete = checkpoint_ids[:-keep_count]
            deleted = 0

            for checkpoint_id in to_delete:
                if await self.delete_checkpoint(checkpoint_id):
                    deleted += 1

            return deleted

    async def get_latest_checkpoint(self, task_id: str) -> Optional[ContextCheckpoint]:
        """
        获取任务的最新检查点

        Args:
            task_id: 任务ID

        Returns:
            最新的ContextCheckpoint或None
        """
        checkpoint_ids = await self.list_checkpoints(task_id)

        if not checkpoint_ids:
            return None

        # 按时间排序获取最新的
        latest_id = sorted(checkpoint_ids)[-1]
        return await self.load_checkpoint(latest_id)


# 全局单例
_persistence_instance: Optional[ContextPersistence] = None


def get_persistence(storage_path: str = ".checkpoints") -> ContextPersistence:
    """获取持久化管理器单例"""
    global _persistence_instance
    if _persistence_instance is None:
        _persistence_instance = ContextPersistence(storage_path=storage_path)
    return _persistence_instance
