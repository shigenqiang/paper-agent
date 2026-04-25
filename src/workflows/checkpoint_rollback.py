"""状态快照与回滚机制 - Checkpoint & Rollback

提供完整的状态管理能力：
1. 关键节点前自动保存快照
2. 失败时回滚到上一个健康状态
3. 支持多个恢复点
4. 与LangGraph状态机集成
"""
import logging
from typing import Dict, Any, Optional, List, Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RollbackReason(str, Enum):
    """回滚原因枚举"""
    SEARCH_FAILED = "search_failed"
    READING_FAILED = "reading_failed"
    ANALYSIS_FAILED = "analysis_failed"
    CRITIQUE_FAILED = "critique_failed"
    WRITING_FAILED = "writing_failed"
    PARTIAL_FAILURE = "partial_failure"
    QUALITY_BELOW_THRESHOLD = "quality_below_threshold"
    MANUAL_TRIGGER = "manual_trigger"


@dataclass
class Checkpoint:
    """状态快照"""
    name: str
    timestamp: datetime
    state: Dict[str, Any]
    node_name: str
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "node_name": self.node_name,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class SnapshotManager:
    """
    快照管理器 - 负责保存和恢复状态快照

    使用示例:
        sm = SnapshotManager(max_snapshots=10)
        sm.save("before_search", state, "search_node")
        # ... 执行可能失败的操作 ...
        if failed:
            restored_state = sm.restore("before_search")
    """

    def __init__(self, max_snapshots: int = 10):
        self.snapshots: Dict[str, Checkpoint] = {}
        self.max_snapshots = max_snapshots
        self._history: List[str] = []  # 保存顺序记录

    def save(
        self,
        name: str,
        state: Dict[str, Any],
        node_name: str = "",
        metadata: Dict[str, Any] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """保存快照"""
        checkpoint = Checkpoint(
            name=name,
            timestamp=datetime.now(),
            state=deepcopy(state),
            node_name=node_name,
            success=success,
            error=error,
            metadata=metadata or {}
        )

        self.snapshots[name] = checkpoint
        self._history.append(name)

        # 清理旧快照
        self._cleanup()

        logger.info(f"Snapshot saved: {name} at {node_name}")

    def restore(self, name: str) -> Optional[Dict[str, Any]]:
        """恢复到指定快照"""
        if name not in self.snapshots:
            logger.error(f"Snapshot not found: {name}")
            return None

        checkpoint = self.snapshots[name]
        logger.info(f"Restoring snapshot: {name}")
        return deepcopy(checkpoint.state)

    def restore_latest(self) -> Optional[Dict[str, Any]]:
        """恢复到最新快照"""
        if not self._history:
            return None
        return self.restore(self._history[-1])

    def restore_previous(self) -> Optional[Dict[str, Any]]:
        """恢复到上一个快照（排除当前）"""
        if len(self._history) < 2:
            return None
        return self.restore(self._history[-2])

    def get_checkpoint_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取快照信息"""
        if name not in self.snapshots:
            return None
        return self.snapshots[name].to_dict()

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有快照"""
        return [cp.to_dict() for cp in self.snapshots.values()]

    def _cleanup(self):
        """清理超过数量的旧快照"""
        if len(self.snapshots) <= self.max_snapshots:
            return

        # 删除最旧的
        excess = len(self.snapshots) - self.max_snapshots
        for _ in range(excess):
            if self._history:
                oldest = self._history.pop(0)
                if oldest in self.snapshots:
                    del self.snapshots[oldest]


class RollbackController:
    """
    回滚控制器 - 基于检查点提供条件回滚能力

    使用示例:
        rc = RollbackController()
        rc.save("before_critique", state)
        # ... 执行critique ...
        if not critique_passed:
            state = rc.rollback("before_critique")
    """

    def __init__(self, snapshot_manager: Optional[SnapshotManager] = None):
        self.snapshot_manager = snapshot_manager or SnapshotManager()
        self._rollback_count = 0
        self._max_rollbacks = 3

    @property
    def can_rollback(self) -> bool:
        return self._rollback_count < self._max_rollbacks

    def save(self, name: str, state: Dict[str, Any], node: str = "") -> None:
        """保存回滚点"""
        self.snapshot_manager.save(name, state, node)

    def rollback(
        self,
        checkpoint_name: Optional[str] = None,
        reason: RollbackReason = RollbackReason.MANUAL_TRIGGER
    ) -> Optional[Dict[str, Any]]:
        """执行回滚"""
        if not self.can_rollback:
            logger.error(f"Max rollbacks ({self._max_rollbacks}) exceeded")
            return None

        if checkpoint_name:
            restored = self.snapshot_manager.restore(checkpoint_name)
        else:
            restored = self.snapshot_manager.restore_latest()

        if restored:
            self._rollback_count += 1
            logger.info(f"Rollback executed: {checkpoint_name}, reason: {reason}, count: {self._rollback_count}")

            # 标记状态
            restored["_rollback"] = True
            restored["_rollback_reason"] = reason.value
            restored["_rollback_count"] = self._rollback_count

        return restored

    def reset(self):
        """重置回滚计数（当状态进入新阶段时）"""
        self._rollback_count = 0


class QualityGate:
    """
    质量门 - 基于阈值判断是否继续或回滚

    使用示例:
        gate = QualityGate()
        gate.add_threshold("papers_count", min=5, max=100)
        gate.add_threshold("analysis_score", min=0.6)

        result = gate.evaluate(state)
        if not result.passed:
            if result.should_rollback:
                state = controller.rollback("before_analysis")
    """

    def __init__(self, thresholds: Dict[str, Any] = None):
        self.thresholds = thresholds or {}

    def add_threshold(
        self,
        key: str,
        min_val: float = None,
        max_val: float = None,
        required: bool = True
    ):
        """添加质量阈值"""
        self.thresholds[key] = {
            "min": min_val,
            "max": max_val,
            "required": required
        }

    def evaluate(self, state: Dict[str, Any]) -> "QualityResult":
        """评估状态是否满足质量要求"""
        violations = []
        missing_fields = []

        for key, threshold in self.thresholds.items():
            value = state.get(key)

            if value is None:
                if threshold["required"]:
                    missing_fields.append(key)
                continue

            if threshold["min"] is not None and value < threshold["min"]:
                violations.append(f"{key}={value} < min={threshold['min']}")

            if threshold["max"] is not None and value > threshold["max"]:
                violations.append(f"{key}={value} > max={threshold['max']}")

        passed = len(violations) == 0 and len(missing_fields) == 0

        return QualityResult(
            passed=passed,
            violations=violations,
            missing_fields=missing_fields,
            should_rollback=not passed and len(missing_fields) > 0,
            should_retry=not passed and len(violations) > 0
        )

    def reset(self):
        """重置阈值"""
        self.thresholds = {}


@dataclass
class QualityResult:
    """质量评估结果"""
    passed: bool
    violations: List[str]
    missing_fields: List[str]
    should_rollback: bool = False
    should_retry: bool = False


# ========== LangGraph 集成节点 ==========

def create_checkpoint_node(
    checkpoint_name: str,
    snapshot_manager: SnapshotManager = None
):
    """
    创建检查点节点工厂

    使用示例:
        checkpoint_node = create_checkpoint_node("after_search", snapshot_manager)
        builder.add_node("checkpoint_after_search", checkpoint_node)
    """
    sm = snapshot_manager or SnapshotManager()

    async def checkpoint_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # 保存当前状态
        sm.save(checkpoint_name, state, node_name=checkpoint_name)
        # 返回原始状态（不做任何修改）
        return state

    return checkpoint_node


def create_rollback_condition(
    quality_gate: QualityGate,
    controller: RollbackController,
    checkpoint_to_restore: str
) -> Callable:
    """
    创建基于质量门的回滚条件函数

    使用示例:
        should_rollback = create_rollback_condition(quality_gate, controller, "before_analysis")
        builder.add_conditional_edges("analysis_node", should_rollback, {
            True: "rollback_to_checkpoint",
            False: "continue"
        })
    """
    def condition(state: Dict[str, Any]) -> bool:
        result = quality_gate.evaluate(state)

        if result.should_rollback and controller.can_rollback:
            # 标记需要回滚
            state["_needs_rollback"] = True
            state["_rollback_checkpoint"] = checkpoint_to_restore
            return True

        state["_needs_rollback"] = False
        return False

    return condition


class PipelineState:
    """
    支持检查点和回滚的流水线状态管理器

    使用示例:
        ps = PipelineState(max_checkpoints=5)
        ps.save_checkpoint("after_search", {"papers": [...]})
        ps.save_checkpoint("after_reading", {"analyses": [...]})

        if critique_failed:
            restored = ps.restore("after_search")
    """

    def __init__(self, max_checkpoints: int = 5):
        self.manager = SnapshotManager(max_checkpoints=max_checkpoints)
        self.controller = RollbackController(self.manager)
        self.current_checkpoint: Optional[str] = None

    def save(self, name: str, state: Dict[str, Any], node: str = "") -> None:
        """保存检查点"""
        self.current_checkpoint = name
        self.manager.save(name, state, node)

    def restore(self, name: str = None) -> Optional[Dict[str, Any]]:
        """恢复检查点"""
        if name:
            return self.manager.restore(name)
        return self.controller.rollback()

    def restore_previous(self) -> Optional[Dict[str, Any]]:
        """恢复到上一个检查点"""
        return self.manager.restore_previous()

    def list(self) -> List[Dict[str, Any]]:
        """列出所有检查点"""
        return self.manager.list_checkpoints()

    @property
    def rollback_count(self) -> int:
        return self.controller._rollback_count

    def reset_rollback_count(self):
        """重置回滚计数（新阶段开始时调用）"""
        self.controller.reset()


# ========== 全局实例 ==========

_pipeline_state: Optional[PipelineState] = None


def get_pipeline_state() -> PipelineState:
    """获取流水线状态管理器单例"""
    global _pipeline_state
    if _pipeline_state is None:
        _pipeline_state = PipelineState()
    return _pipeline_state


def save_checkpoint(name: str, state: Dict[str, Any], node: str = "") -> None:
    """快捷函数：保存检查点"""
    get_pipeline_state().save(name, state, node)


def restore_checkpoint(name: str = None) -> Optional[Dict[str, Any]]:
    """快捷函数：恢复检查点"""
    return get_pipeline_state().restore(name)