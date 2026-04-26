"""
Process Quality Tracker - 过程质量追踪器

在Agent执行的每个关键节点记录质量数据，形成完整的质量变化曲线。
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckpoint:
    """质量检查点"""
    checkpoint_id: str
    phase_name: str
    sub_step: str
    timestamp: float = field(default_factory=time.time)

    # 质量维度
    completeness: float = 0.0
    correctness: float = 0.0
    coherence: float = 0.0
    relevance: float = 0.0

    # 元数据
    input_quality: float = 0.0
    processing_time_ms: float = 0.0
    tokens_used: int = 0

    # 问题标记
    issues_detected: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "phase_name": self.phase_name,
            "sub_step": self.sub_step,
            "timestamp": self.timestamp,
            "completeness": self.completeness,
            "correctness": self.correctness,
            "coherence": self.coherence,
            "relevance": self.relevance,
            "input_quality": self.input_quality,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
            "issues_detected": self.issues_detected,
            "suggestions": self.suggestions,
            "overall_score": self.overall_score
        }

    @property
    def overall_score(self) -> float:
        """计算综合分数"""
        weights = {"completeness": 0.25, "correctness": 0.30, "coherence": 0.20, "relevance": 0.25}
        return sum(getattr(self, dim) * weight for dim, weight in weights.items())


@dataclass
class QualityTrend:
    """质量趋势"""
    phase_name: str
    checkpoint_count: int
    overall_score: float
    completeness_trend: str  # "improving", "stable", "declining"
    correctness_trend: str
    issues_count: int
    average_processing_time: float
    status: str = "unknown"


class ProcessQualityTracker:
    """
    过程质量追踪器

    在Agent执行的每个关键节点记录质量数据
    形成完整的质量变化曲线

    使用示例:
        tracker = ProcessQualityTracker("writing")

        # 记录检查点
        tracker.record_checkpoint(
            sub_step="outline_generation",
            quality_metrics={"completeness": 0.8, "correctness": 0.9},
            metadata={"processing_time_ms": 1500, "tokens_used": 500}
        )

        # 获取趋势
        trend = tracker.get_quality_trend()
    """

    def __init__(self, phase_name: str):
        self.phase_name = phase_name
        self._checkpoints: List[QualityCheckpoint] = []
        self._quality_thresholds = {
            "completeness": 0.7,
            "correctness": 0.75,
            "coherence": 0.7,
            "relevance": 0.8
        }
        self._checkpoint_counter = 0

    def record_checkpoint(
        self,
        sub_step: str,
        quality_metrics: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> QualityCheckpoint:
        """
        记录质量检查点

        Args:
            sub_step: 子步骤名称
            quality_metrics: 质量指标 {"completeness": 0-1, "correctness": 0-1, ...}
            metadata: 元数据 {"processing_time_ms": float, "tokens_used": int, ...}

        Returns:
            QualityCheckpoint: 创建的检查点
        """
        self._checkpoint_counter += 1
        checkpoint_id = f"{self.phase_name}_{sub_step}_{self._checkpoint_counter}"

        checkpoint = QualityCheckpoint(
            checkpoint_id=checkpoint_id,
            phase_name=self.phase_name,
            sub_step=sub_step,
            timestamp=time.time(),
            completeness=quality_metrics.get("completeness", 0.0),
            correctness=quality_metrics.get("correctness", 0.0),
            coherence=quality_metrics.get("coherence", 0.0),
            relevance=quality_metrics.get("relevance", 0.0),
            input_quality=metadata.get("input_quality", 0.0),
            processing_time_ms=metadata.get("processing_time_ms", 0.0),
            tokens_used=metadata.get("tokens_used", 0),
            issues_detected=metadata.get("issues", []),
            suggestions=metadata.get("suggestions", [])
        )

        self._checkpoints.append(checkpoint)

        # 检查是否需要预警
        self._check_quality_alerts(checkpoint)

        return checkpoint

    def _check_quality_alerts(self, checkpoint: QualityCheckpoint) -> None:
        """检查质量告警"""
        for dimension, threshold in self._quality_thresholds.items():
            value = getattr(checkpoint, dimension, 0.0)
            if value < threshold:
                logger.warning(
                    f"Quality alert: {self.phase_name}.{checkpoint.sub_step}.{dimension} "
                    f"= {value:.2f} < {threshold}"
                )

    def get_quality_trend(self) -> QualityTrend:
        """获取质量趋势"""
        if not self._checkpoints:
            return QualityTrend(
                phase_name=self.phase_name,
                checkpoint_count=0,
                overall_score=0.0,
                completeness_trend="no_data",
                correctness_trend="no_data",
                issues_count=0,
                average_processing_time=0.0,
                status="no_data"
            )

        # 计算各维度的趋势
        completeness_trend = self._calculate_trend("completeness")
        correctness_trend = self._calculate_trend("correctness")

        # 计算总体分数
        overall_score = sum(cp.overall_score for cp in self._checkpoints) / len(self._checkpoints)

        # 计算平均处理时间
        avg_time = sum(cp.processing_time_ms for cp in self._checkpoints) / len(self._checkpoints)

        # 统计问题数
        issues_count = sum(len(cp.issues_detected) for cp in self._checkpoints)

        # 确定状态
        status = self._determine_status(overall_score, completeness_trend, correctness_trend)

        return QualityTrend(
            phase_name=self.phase_name,
            checkpoint_count=len(self._checkpoints),
            overall_score=overall_score,
            completeness_trend=completeness_trend,
            correctness_trend=correctness_trend,
            issues_count=issues_count,
            average_processing_time=avg_time,
            status=status
        )

    def _calculate_trend(self, dimension: str) -> str:
        """计算维度趋势"""
        if len(self._checkpoints) < 2:
            return "insufficient_data"

        values = [getattr(cp, dimension, 0.0) for cp in self._checkpoints]

        # 简单趋势判断：比较前半和后半的平均值
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid if mid > 0 else 0
        second_half = sum(values[mid:]) / (len(values) - mid) if len(values) - mid > 0 else 0

        diff = second_half - first_half

        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"

    def _determine_status(
        self,
        overall_score: float,
        completeness_trend: str,
        correctness_trend: str
    ) -> str:
        """确定状态"""
        if overall_score >= 0.8 and completeness_trend != "declining" and correctness_trend != "declining":
            return "healthy"
        elif overall_score >= 0.6:
            return "warning"
        else:
            return "critical"

    def get_bottlenecks(self) -> List[str]:
        """获取瓶颈分析"""
        bottlenecks = []

        if not self._checkpoints:
            return bottlenecks

        # 检查处理时间异常
        avg_time = sum(cp.processing_time_ms for cp in self._checkpoints) / len(self._checkpoints)
        slow_checkpoints = [cp for cp in self._checkpoints if cp.processing_time_ms > avg_time * 2]
        if slow_checkpoints:
            bottlenecks.append(f"Slow processing: {[cp.sub_step for cp in slow_checkpoints]}")

        # 检查质量问题
        low_quality = [cp for cp in self._checkpoints if cp.correctness < 0.6]
        if low_quality:
            bottlenecks.append(f"Low correctness: {[cp.sub_step for cp in low_quality]}")

        # 检查低完整性
        low_completeness = [cp for cp in self._checkpoints if cp.completeness < 0.5]
        if low_completeness:
            bottlenecks.append(f"Low completeness: {[cp.sub_step for cp in low_completeness]}")

        return bottlenecks

    def get_checkpoint_by_id(self, checkpoint_id: str) -> Optional[QualityCheckpoint]:
        """根据ID获取检查点"""
        for cp in self._checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                return cp
        return None

    def get_recent_checkpoints(self, n: int = 5) -> List[QualityCheckpoint]:
        """获取最近的N个检查点"""
        return self._checkpoints[-n:]

    def get_phase_summary(self) -> Dict[str, Any]:
        """获取阶段总结"""
        trend = self.get_quality_trend()
        bottlenecks = self.get_bottlenecks()

        return {
            "phase_name": self.phase_name,
            "total_checkpoints": len(self._checkpoints),
            "quality_trend": {
                "overall_score": trend.overall_score,
                "status": trend.status,
                "completeness_trend": trend.completeness_trend,
                "correctness_trend": trend.correctness_trend
            },
            "bottlenecks": bottlenecks,
            "total_processing_time_ms": sum(cp.processing_time_ms for cp in self._checkpoints),
            "average_processing_time_ms": trend.average_processing_time,
            "total_tokens_used": sum(cp.tokens_used for cp in self._checkpoints),
            "issues_count": trend.issues_count
        }

    def set_threshold(self, dimension: str, threshold: float):
        """设置质量阈值"""
        if dimension in self._quality_thresholds:
            self._quality_thresholds[dimension] = threshold

    def clear(self):
        """清除所有检查点"""
        self._checkpoints.clear()
        self._checkpoint_counter = 0


class MultiPhaseQualityTracker:
    """
    多阶段质量追踪器

    追踪整个论文生成流程中所有阶段的质量数据
    """

    def __init__(self):
        self._phase_trackers: Dict[str, ProcessQualityTracker] = {}
        self._global_checkpoints: List[QualityCheckpoint] = []

    def get_or_create_tracker(self, phase_name: str) -> ProcessQualityTracker:
        """获取或创建阶段追踪器"""
        if phase_name not in self._phase_trackers:
            self._phase_trackers[phase_name] = ProcessQualityTracker(phase_name)
        return self._phase_trackers[phase_name]

    def record_global_checkpoint(
        self,
        phase_name: str,
        sub_step: str,
        quality_metrics: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> QualityCheckpoint:
        """记录全局检查点"""
        tracker = self.get_or_create_tracker(phase_name)
        checkpoint = tracker.record_checkpoint(sub_step, quality_metrics, metadata)
        self._global_checkpoints.append(checkpoint)
        return checkpoint

    def get_phase_trackers(self) -> Dict[str, ProcessQualityTracker]:
        """获取所有阶段追踪器"""
        return self._phase_trackers

    def get_all_trends(self) -> Dict[str, QualityTrend]:
        """获取所有阶段的趋势"""
        return {
            phase: tracker.get_quality_trend()
            for phase, tracker in self._phase_trackers.items()
        }

    def get_global_summary(self) -> Dict[str, Any]:
        """获取全局总结"""
        phases = list(self._phase_trackers.keys())
        trends = self.get_all_trends()

        overall_scores = [t.overall_score for t in trends.values() if t.overall_score > 0]
        avg_overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0

        total_issues = sum(t.issues_count for t in trends.values())
        total_time = sum(
            sum(cp.processing_time_ms for cp in tracker._checkpoints)
            for tracker in self._phase_trackers.values()
        )

        return {
            "total_phases": len(phases),
            "phases": phases,
            "average_overall_score": avg_overall,
            "total_issues": total_issues,
            "total_processing_time_ms": total_time,
            "phase_summaries": {
                phase: tracker.get_phase_summary()
                for phase, tracker in self._phase_trackers.items()
            },
            "global_trends": {
                phase: {
                    "overall_score": t.overall_score,
                    "status": t.status,
                    "completeness_trend": t.completeness_trend,
                    "correctness_trend": t.correctness_trend
                }
                for phase, t in trends.items()
            }
        }

    def clear(self):
        """清除所有数据"""
        for tracker in self._phase_trackers.values():
            tracker.clear()
        self._global_checkpoints.clear()


def create_quality_tracker(phase_name: str) -> ProcessQualityTracker:
    """创建质量追踪器"""
    return ProcessQualityTracker(phase_name)


def create_global_tracker() -> MultiPhaseQualityTracker:
    """创建全局质量追踪器"""
    return MultiPhaseQualityTracker()
