"""
State Persistence - 状态持久化

提供PaperState的持久化和恢复功能。
"""
import json
import os
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .state_model import PaperState, StateMetadata, PaperPhase, StateStatus


@dataclass
class StateStore:
    """状态存储"""
    store_id: str
    location: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    state_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class StatePersistence:
    """
    状态持久化

    功能:
    - 保存状态到文件/数据库
    - 加载状态
    - 状态历史记录
    - 状态快照

    使用示例:
        persistence = StatePersistence(base_path="./states")

        # 保存状态
        persistence.save(state)

        # 加载状态
        loaded = persistence.load("paper_123")

        # 获取历史
        history = persistence.get_history("paper_123")
    """

    def __init__(
        self,
        base_path: str = "./states",
        max_history: int = 10,
        enable_compression: bool = False
    ):
        """
        初始化状态持久化

        Args:
            base_path: 基础路径
            max_history: 最大历史记录数
            enable_compression: 是否启用压缩
        """
        self.base_path = Path(base_path)
        self.max_history = max_history
        self.enable_compression = enable_compression
        self._stores: Dict[str, StateStore] = {}
        self._cache: Dict[str, PaperState] = {}

        # 创建基础目录
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, state: PaperState, store_id: Optional[str] = None) -> bool:
        """
        保存状态

        Args:
            state: 要保存的状态
            store_id: 存储ID（默认使用paper_id）

        Returns:
            bool: 是否成功
        """
        store_id = store_id or state.paper_id
        if not store_id:
            raise ValueError("store_id or state.paper_id is required")

        # 更新元数据
        state.update_metadata()

        # 保存到文件
        file_path = self.base_path / f"{store_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

            # 更新缓存
            self._cache[store_id] = state

            # 保存历史
            self._save_history(store_id, state)

            # 更新存储信息
            self._update_store(store_id)

            return True
        except Exception as e:
            print(f"Failed to save state: {e}")
            return False

    def load(self, store_id: str) -> Optional[PaperState]:
        """
        加载状态

        Args:
            store_id: 存储ID

        Returns:
            PaperState或None
        """
        # 检查缓存
        if store_id in self._cache:
            return self._cache[store_id]

        # 从文件加载
        file_path = self.base_path / f"{store_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = PaperState.from_dict(data)
            self._cache[store_id] = state
            return state
        except Exception as e:
            print(f"Failed to load state: {e}")
            return None

    def delete(self, store_id: str) -> bool:
        """
        删除状态

        Args:
            store_id: 存储ID

        Returns:
            bool: 是否成功
        """
        file_path = self.base_path / f"{store_id}.json"
        history_dir = self.base_path / f"{store_id}_history"

        try:
            if file_path.exists():
                file_path.unlink()

            if history_dir.exists():
                for f in history_dir.iterdir():
                    f.unlink()
                history_dir.rmdir()

            if store_id in self._cache:
                del self._cache[store_id]

            if store_id in self._stores:
                del self._stores[store_id]

            return True
        except Exception as e:
            print(f"Failed to delete state: {e}")
            return False

    def exists(self, store_id: str) -> bool:
        """检查状态是否存在"""
        if store_id in self._cache:
            return True
        file_path = self.base_path / f"{store_id}.json"
        return file_path.exists()

    def list_states(self) -> List[str]:
        """列出所有状态"""
        states = list(self._stores.keys())

        # 扫描目录
        for f in self.base_path.glob("*.json"):
            store_id = f.stem
            if store_id not in states and not store_id.endswith("_history"):
                states.append(store_id)

        return states

    def _save_history(self, store_id: str, state: PaperState):
        """保存历史记录"""
        history_dir = self.base_path / f"{store_id}_history"
        history_dir.mkdir(exist_ok=True)

        # 保存当前状态到历史
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = history_dir / f"{timestamp}.json"

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False)

        # 清理旧的历史记录
        self._cleanup_history(store_id)

    def _cleanup_history(self, store_id: str):
        """清理旧的历史记录"""
        history_dir = self.base_path / f"{store_id}_history"
        if not history_dir.exists():
            return

        history_files = sorted(history_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)

        # 删除超过max_history的历史记录
        for f in history_files[self.max_history:]:
            f.unlink()

    def _update_store(self, store_id: str):
        """更新存储信息"""
        if store_id not in self._stores:
            self._stores[store_id] = StateStore(
                store_id=store_id,
                location=str(self.base_path / f"{store_id}.json")
            )

        store = self._stores[store_id]
        store.updated_at = datetime.now()
        store.state_count = self._count_history(store_id) + 1

    def _count_history(self, store_id: str) -> int:
        """计算历史记录数"""
        history_dir = self.base_path / f"{store_id}_history"
        if not history_dir.exists():
            return 0
        return len(list(history_dir.glob("*.json")))

    def get_history(self, store_id: str) -> List[PaperState]:
        """
        获取状态历史

        Args:
            store_id: 存储ID

        Returns:
            List[PaperState]: 状态历史列表
        """
        history_dir = self.base_path / f"{store_id}_history"
        if not history_dir.exists():
            return []

        history_files = sorted(history_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        states = []

        for f in history_files[:self.max_history]:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                states.append(PaperState.from_dict(data))
            except Exception:
                continue

        return states

    def get_store_info(self, store_id: str) -> Optional[StateStore]:
        """获取存储信息"""
        return self._stores.get(store_id)

    def snapshot(self, store_id: str, snapshot_name: str) -> bool:
        """
        创建快照

        Args:
            store_id: 存储ID
            snapshot_name: 快照名称

        Returns:
            bool: 是否成功
        """
        state = self.load(store_id)
        if not state:
            return False

        snapshots_dir = self.base_path / f"{store_id}_snapshots"
        snapshots_dir.mkdir(exist_ok=True)

        snapshot_file = snapshots_dir / f"{snapshot_name}.json"

        try:
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def restore_snapshot(self, store_id: str, snapshot_name: str) -> Optional[PaperState]:
        """
        恢复快照

        Args:
            store_id: 存储ID
            snapshot_name: 快照名称

        Returns:
            PaperState或None
        """
        snapshots_dir = self.base_path / f"{store_id}_snapshots"
        snapshot_file = snapshots_dir / f"{snapshot_name}.json"

        if not snapshot_file.exists():
            return None

        try:
            with open(snapshot_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PaperState.from_dict(data)
        except Exception:
            return None

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_stores": len(self._stores),
            "cached_states": len(self._cache),
            "base_path": str(self.base_path),
            "max_history": self.max_history,
        }


def create_persistence(base_path: str = "./states") -> StatePersistence:
    """创建状态持久化实例"""
    return StatePersistence(base_path=base_path)