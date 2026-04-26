"""
Execution Replay - 执行回放功能

当Agent执行时间过长时，可以回放之前的执行状态。
支持:
1. 慢查询检测与警告
2. 执行过程回放
3. 部分结果提前返回
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReplayEntry:
    """回放条目"""
    event_type: str  # "start", "progress", "complete", "error"
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SlowExecutionWarning:
    """慢执行警告"""
    recording_id: str
    elapsed_ms: float
    expected_ms: float
    slowdown_factor: float
    progress: float
    partial_result: Optional[Any] = None


@dataclass
class EarlyResult:
    """提前结果"""
    partial_result: Any
    completeness: float
    is_final: bool
    estimated_remaining_time: float


class ExecutionReplay:
    """
    执行回放功能

    当Agent执行时间过长时，可以回放之前的执行状态
    支持:
    1. 慢查询检测与警告
    2. 执行过程回放
    3. 部分结果提前返回

    使用示例:
        replay = ExecutionReplay()

        # 开始记录
        recording_id = replay.start_recording("task_1", "agent_1", "outline_generation")

        # 记录进度
        replay.record_progress(recording_id, 0.5, {"outline": "..."})

        # 检查是否过慢
        warning = replay.check_slow_execution(recording_id, expected_duration_ms=5000)
        if warning:
            print(f"Execution is slow: {warning.slowdown_factor:.1f}x")

        # 生成提前结果
        early = replay.generate_early_result(recording_id, quality_threshold=0.6)
        if early:
            return early.partial_result
    """

    def __init__(self, slow_threshold_ms: float = 30000):
        """
        初始化执行回放

        Args:
            slow_threshold_ms: 慢执行阈值（毫秒），默认30秒
        """
        self._replay_buffer: Dict[str, List[ReplayEntry]] = {}
        self._slow_threshold_ms = slow_threshold_ms
        self._recording_counter = 0

    def start_recording(
        self,
        task_id: str,
        agent_id: str,
        operation: str
    ) -> str:
        """
        开始记录执行

        Args:
            task_id: 任务ID
            agent_id: Agent ID
            operation: 操作名称

        Returns:
            str: 录制ID
        """
        self._recording_counter += 1
        recording_id = f"{task_id}_{agent_id}_{self._recording_counter}"

        self._replay_buffer[recording_id] = [
            ReplayEntry(
                event_type="start",
                timestamp=time.time(),
                data={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "operation": operation
                }
            )
        ]

        logger.debug(f"Started recording: {recording_id}")
        return recording_id

    def record_progress(
        self,
        recording_id: str,
        progress: float,
        partial_result: Any = None
    ) -> None:
        """
        记录进度

        Args:
            recording_id: 录制ID
            progress: 进度 (0-1)
            partial_result: 部分结果
        """
        if recording_id not in self._replay_buffer:
            logger.warning(f"Recording not found: {recording_id}")
            return

        entry = ReplayEntry(
            event_type="progress",
            timestamp=time.time(),
            data={
                "progress": progress,
                "partial_result": partial_result
            }
        )

        self._replay_buffer[recording_id].append(entry)
        logger.debug(f"Recorded progress for {recording_id}: {progress:.1%}")

    def record_completion(
        self,
        recording_id: str,
        result: Any,
        quality_score: float = 1.0
    ) -> None:
        """
        记录完成

        Args:
            recording_id: 录制ID
            result: 最终结果
            quality_score: 质量分数
        """
        if recording_id not in self._replay_buffer:
            logger.warning(f"Recording not found: {recording_id}")
            return

        entry = ReplayEntry(
            event_type="complete",
            timestamp=time.time(),
            data={
                "result": result,
                "quality_score": quality_score
            }
        )

        self._replay_buffer[recording_id].append(entry)
        logger.debug(f"Recorded completion for {recording_id}")

    def record_error(
        self,
        recording_id: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录错误

        Args:
            recording_id: 录制ID
            error: 错误信息
            error_details: 错误详情
        """
        if recording_id not in self._replay_buffer:
            logger.warning(f"Recording not found: {recording_id}")
            return

        entry = ReplayEntry(
            event_type="error",
            timestamp=time.time(),
            data={
                "error": error,
                "error_details": error_details or {}
            }
        )

        self._replay_buffer[recording_id].append(entry)
        logger.debug(f"Recorded error for {recording_id}: {error}")

    def check_slow_execution(
        self,
        recording_id: str,
        expected_duration_ms: float
    ) -> Optional[SlowExecutionWarning]:
        """
        检查是否执行过慢

        Args:
            recording_id: 录制ID
            expected_duration_ms: 预期持续时间（毫秒）

        Returns:
            Optional[SlowExecutionWarning]: 如果过慢返回警告，否则返回None
        """
        if recording_id not in self._replay_buffer:
            return None

        entries = self._replay_buffer[recording_id]
        if not entries:
            return None

        start_time = entries[0].timestamp
        elapsed_ms = (time.time() - start_time) * 1000

        if elapsed_ms > self._slow_threshold_ms:
            # 获取最新进度
            latest_entry = entries[-1]
            progress = 0.0
            partial_result = None

            if latest_entry.event_type == "progress":
                progress = latest_entry.data.get("progress", 0)
                partial_result = latest_entry.data.get("partial_result")

            return SlowExecutionWarning(
                recording_id=recording_id,
                elapsed_ms=elapsed_ms,
                expected_ms=expected_duration_ms,
                slowdown_factor=elapsed_ms / expected_duration_ms if expected_duration_ms > 0 else 0,
                progress=progress,
                partial_result=partial_result
            )

        return None

    def generate_early_result(
        self,
        recording_id: str,
        quality_threshold: float = 0.6
    ) -> Optional[EarlyResult]:
        """
        生成提前结果

        当任务还未完成但已经有足够进展时，可以返回部分结果

        Args:
            recording_id: 录制ID
            quality_threshold: 最低质量阈值

        Returns:
            Optional[EarlyResult]: 如果有足够的部分结果返回，否则返回None
        """
        if recording_id not in self._replay_buffer:
            return None

        entries = self._replay_buffer[recording_id]

        # 找到最新的部分结果
        for entry in reversed(entries):
            if entry.event_type == "progress" and entry.data.get("partial_result"):
                partial = entry.data["partial_result"]
                progress = entry.data.get("progress", 0)

                # 检查部分结果的质量
                if self._estimate_quality(partial) >= quality_threshold:
                    # 估算剩余时间
                    start_time = entries[0].timestamp
                    elapsed = time.time() - start_time
                    remaining = self._estimate_remaining_time(progress, elapsed)

                    return EarlyResult(
                        partial_result=partial,
                        completeness=progress,
                        is_final=False,
                        estimated_remaining_time=remaining
                    )

        return None

    def replay(self, recording_id: str) -> List[ReplayEntry]:
        """
        回放执行过程

        Args:
            recording_id: 录制ID

        Returns:
            List[ReplayEntry]: 回放条目列表
        """
        return self._replay_buffer.get(recording_id, [])

    def get_execution_summary(self, recording_id: str) -> Dict[str, Any]:
        """
        获取执行摘要

        Args:
            recording_id: 录制ID

        Returns:
            Dict: 执行摘要
        """
        if recording_id not in self._replay_buffer:
            return {}

        entries = self._replay_buffer[recording_id]
        if not entries:
            return {}

        start_entry = entries[0]
        end_entry = entries[-1] if len(entries) > 1 else start_entry

        # 计算总时长
        total_duration_ms = (end_entry.timestamp - start_entry.timestamp) * 1000

        # 获取最终状态
        status = "unknown"
        result = None
        error = None
        progress = 0.0

        for entry in reversed(entries):
            if entry.event_type == "complete":
                status = "completed"
                result = entry.data.get("result")
                break
            elif entry.event_type == "error":
                status = "error"
                error = entry.data.get("error")
                break
            elif entry.event_type == "progress":
                progress = entry.data.get("progress", 0)
                status = "in_progress"

        return {
            "recording_id": recording_id,
            "operation": start_entry.data.get("operation", "unknown"),
            "agent_id": start_entry.data.get("agent_id", "unknown"),
            "task_id": start_entry.data.get("task_id", "unknown"),
            "status": status,
            "total_duration_ms": total_duration_ms,
            "progress": progress,
            "result": result,
            "error": error,
            "entry_count": len(entries)
        }

    def _estimate_quality(self, partial_result: Any) -> float:
        """
        估算部分结果的质量

        Args:
            partial_result: 部分结果

        Returns:
            float: 估算的质量分数 (0-1)
        """
        if partial_result is None:
            return 0.0

        # 简单的质量估算策略
        if isinstance(partial_result, dict):
            # 检查是否有必要的字段
            required_fields = ["outline", "draft", "content", "result"]
            has_content = any(field in partial_result for field in required_fields)

            if has_content:
                # 检查内容长度
                content = next((partial_result[f] for f in required_fields if f in partial_result), "")
                if isinstance(content, str) and len(content) > 100:
                    return 0.7
                elif isinstance(content, dict):
                    return 0.7
                elif isinstance(content, str):
                    return 0.4

            return 0.3

        elif isinstance(partial_result, str):
            if len(partial_result) > 100:
                return 0.6
            return 0.3

        return 0.5

    def _estimate_remaining_time(self, progress: float, elapsed: float) -> float:
        """
        估算剩余时间

        Args:
            progress: 当前进度 (0-1)
            elapsed: 已用时间（秒）

        Returns:
            float: 估算的剩余时间（秒）
        """
        if progress <= 0:
            return elapsed  # 无法估算，返回已用时间

        # 基于当前进度估算总时间
        estimated_total = elapsed / progress
        remaining = estimated_total - elapsed

        return max(0, remaining)

    def clear_recording(self, recording_id: str) -> bool:
        """
        清除录制记录

        Args:
            recording_id: 录制ID

        Returns:
            bool: 是否成功清除
        """
        if recording_id in self._replay_buffer:
            del self._replay_buffer[recording_id]
            return True
        return False

    def clear_all(self) -> int:
        """
        清除所有录制记录

        Returns:
            int: 清除的录制数量
        """
        count = len(self._replay_buffer)
        self._replay_buffer.clear()
        return count

    def get_active_recordings(self) -> List[str]:
        """
        获取所有活跃的录制ID

        Returns:
            List[str]: 录制ID列表
        """
        return list(self._replay_buffer.keys())

    def get_recording_count(self) -> int:
        """获取录制数量"""
        return len(self._replay_buffer)


class ExecutionReplayManager:
    """
    执行回放管理器

    管理多个ExecutionReplay实例，支持按任务或阶段分组
    """

    def __init__(self, slow_threshold_ms: float = 30000):
        self._replays: Dict[str, ExecutionReplay] = {}
        self._slow_threshold_ms = slow_threshold_ms

    def get_or_create_replay(self, key: str) -> ExecutionReplay:
        """
        获取或创建回放实例

        Args:
            key: 键（如任务ID或阶段名）

        Returns:
            ExecutionReplay: 回放实例
        """
        if key not in self._replays:
            self._replays[key] = ExecutionReplay(slow_threshold_ms=self._slow_threshold_ms)
        return self._replays[key]

    def start_recording(
        self,
        group_key: str,
        task_id: str,
        agent_id: str,
        operation: str
    ) -> str:
        """
        开始录制

        Args:
            group_key: 分组键
            task_id: 任务ID
            agent_id: Agent ID
            operation: 操作名称

        Returns:
            str: 录制ID
        """
        replay = self.get_or_create_replay(group_key)
        return replay.start_recording(task_id, agent_id, operation)

    def get_global_summary(self) -> Dict[str, Any]:
        """获取全局摘要"""
        return {
            "total_groups": len(self._replays),
            "total_recordings": sum(r.get_recording_count() for r in self._replays.values()),
            "groups": {
                key: r.get_recording_count()
                for key, r in self._replays.items()
            }
        }


def create_replay(slow_threshold_ms: float = 30000) -> ExecutionReplay:
    """创建执行回放实例"""
    return ExecutionReplay(slow_threshold_ms=slow_threshold_ms)


def create_replay_manager(slow_threshold_ms: float = 30000) -> ExecutionReplayManager:
    """创建执行回放管理器"""
    return ExecutionReplayManager(slow_threshold_ms=slow_threshold_ms)
