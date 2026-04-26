"""
Chain Debugger - 链路调试器

提供链路调试和快照功能。
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class DebugLevel(str, Enum):
    """调试级别"""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    VERBOSE = "verbose"


@dataclass
class DebugSnapshot:
    """调试快照"""
    snapshot_id: str
    chain_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    phase: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "chain_id": self.chain_id,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
            "state": self.state,
            "events": self.events,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ChainDebugger:
    """
    链路调试器

    功能:
    - 快照链路状态
    - 回放执行过程
    - 诊断问题

    使用示例:
        debugger = ChainDebugger()

        debugger.snapshot(chain_id="123", phase="literature", state=current_state)

        snapshots = debugger.get_snapshots(chain_id="123")
    """

    def __init__(self, max_snapshots: int = 100, level: DebugLevel = DebugLevel.BASIC):
        """
        初始化链路调试器

        Args:
            max_snapshots: 最大快照数
            level: 调试级别
        """
        self.max_snapshots = max_snapshots
        self.level = level
        self._snapshots: List[DebugSnapshot] = []
        self._snapshot_count = 0
        self._breakpoints: Dict[str, Callable] = {}

    def snapshot(
        self,
        chain_id: str,
        phase: str = "",
        state: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        **metadata
    ) -> DebugSnapshot:
        """
        创建快照

        Args:
            chain_id: 链路ID
            phase: 当前阶段
            state: 状态数据
            events: 事件列表
            **metadata: 额外元数据

        Returns:
            DebugSnapshot: 创建的快照
        """
        self._snapshot_count += 1

        snapshot = DebugSnapshot(
            snapshot_id=f"snap_{self._snapshot_count}",
            chain_id=chain_id,
            phase=phase,
            state=state or {},
            events=events or [],
            metadata=metadata
        )

        self._snapshots.append(snapshot)

        # 裁剪快照
        if len(self._snapshots) > self.max_snapshots:
            self._snapshots = self._snapshots[-self.max_snapshots:]

        # 检查断点
        self._check_breakpoint(snapshot)

        return snapshot

    def _check_breakpoint(self, snapshot: DebugSnapshot):
        """检查断点"""
        for key, handler in self._breakpoints.items():
            if self._matches_breakpoint(key, snapshot):
                try:
                    handler(snapshot)
                except Exception as e:
                    print(f"Breakpoint handler error: {e}")

    def _matches_breakpoint(self, key: str, snapshot: DebugSnapshot) -> bool:
        """检查是否匹配断点条件"""
        if key.startswith("chain_id:"):
            target_chain = key.split(":", 1)[1]
            return snapshot.chain_id == target_chain
        if key.startswith("phase:"):
            target_phase = key.split(":", 1)[1]
            return snapshot.phase == target_phase
        return False

    def add_breakpoint(self, condition: str, handler: Callable):
        """
        添加断点

        Args:
            condition: 条件 (如 "chain_id:123", "phase:literature")
            handler: 处理函数
        """
        self._breakpoints[condition] = handler

    def remove_breakpoint(self, condition: str):
        """移除断点"""
        if condition in self._breakpoints:
            del self._breakpoints[condition]

    def get_snapshots(
        self,
        chain_id: Optional[str] = None,
        phase: Optional[str] = None,
        limit: int = 50
    ) -> List[DebugSnapshot]:
        """获取快照列表"""
        snapshots = self._snapshots

        if chain_id:
            snapshots = [s for s in snapshots if s.chain_id == chain_id]

        if phase:
            snapshots = [s for s in snapshots if s.phase == phase]

        return snapshots[-limit:]

    def get_latest(self, chain_id: Optional[str] = None) -> Optional[DebugSnapshot]:
        """获取最新快照"""
        snapshots = self.get_snapshots(chain_id=chain_id, limit=1)
        return snapshots[-1] if snapshots else None

    def compare(self, snapshot_id1: str, snapshot_id2: str) -> Dict[str, Any]:
        """比较两个快照"""
        snap1 = self._find_snapshot(snapshot_id1)
        snap2 = self._find_snapshot(snapshot_id2)

        if not snap1 or not snap2:
            return {"error": "Snapshot not found"}

        # 比较状态变化
        state_diff = self._diff_dict(snap1.state, snap2.state)

        return {
            "snapshot1": snap1.snapshot_id,
            "snapshot2": snap2.snapshot_id,
            "time_diff_seconds": (snap2.timestamp - snap1.timestamp).total_seconds(),
            "state_changes": state_diff,
            "phase_change": snap1.phase != snap2.phase
        }

    def _find_snapshot(self, snapshot_id: str) -> Optional[DebugSnapshot]:
        """查找快照"""
        for s in self._snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def _diff_dict(self, d1: Dict, d2: Dict) -> Dict[str, Any]:
        """计算字典差异"""
        diff = {"added": {}, "removed": {}, "changed": {}}

        all_keys = set(d1.keys()) | set(d2.keys())

        for key in all_keys:
            if key not in d1:
                diff["added"][key] = d2[key]
            elif key not in d2:
                diff["removed"][key] = d1[key]
            elif d1[key] != d2[key]:
                diff["changed"][key] = {"from": d1[key], "to": d2[key]}

        return diff

    def replay(
        self,
        chain_id: str,
        start_snapshot: Optional[str] = None,
        end_snapshot: Optional[str] = None
    ) -> List[DebugSnapshot]:
        """
        回放链路执行

        Args:
            chain_id: 链路ID
            start_snapshot: 起始快照
            end_snapshot: 结束快照

        Returns:
            List[DebugSnapshot]: 快照序列
        """
        snapshots = self.get_snapshots(chain_id=chain_id, limit=1000)

        if start_snapshot:
            start_idx = next((i for i, s in enumerate(snapshots) if s.snapshot_id == start_snapshot), 0)
            snapshots = snapshots[start_idx:]

        if end_snapshot:
            end_idx = next((i for i, s in enumerate(snapshots) if s.snapshot_id == end_snapshot), len(snapshots))
            snapshots = snapshots[:end_idx + 1]

        return snapshots

    def export(self, chain_id: str, file_path: str) -> bool:
        """导出调试数据"""
        snapshots = self.get_snapshots(chain_id=chain_id, limit=10000)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in snapshots], f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False

    def import_(self, file_path: str) -> int:
        """导入调试数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            count = 0
            for item in data:
                snapshot = DebugSnapshot(
                    snapshot_id=item["snapshot_id"],
                    chain_id=item["chain_id"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    phase=item.get("phase", ""),
                    state=item.get("state", {}),
                    events=item.get("events", []),
                    metadata=item.get("metadata", {})
                )
                self._snapshots.append(snapshot)
                count += 1

            return count
        except Exception as e:
            print(f"Import failed: {e}")
            return 0

    def clear(self):
        """清除所有快照"""
        self._snapshots.clear()
        self._snapshot_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_snapshots": len(self._snapshots),
            "max_snapshots": self.max_snapshots,
            "debug_level": self.level.value,
            "breakpoints": list(self._breakpoints.keys()),
            "chains": list(set(s.chain_id for s in self._snapshots))
        }


def create_debugger(level: DebugLevel = DebugLevel.BASIC) -> ChainDebugger:
    """创建链路调试器"""
    return ChainDebugger(level=level)