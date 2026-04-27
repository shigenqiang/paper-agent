"""
Skill Evolution - 技能演化系统

基于使用反馈自动改进技能。
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class SkillEvolutionType(str, Enum):
    """技能演化类型"""
    REFINEMENT = "refinement"  # 精化
    EXTENSION = "extension"    # 扩展
    COMPOSITION = "composition"  # 组合
    PRUNING = "pruning"       # 剪枝


@dataclass
class EvolutionRecord:
    """演化记录"""
    record_id: str
    skill_id: str
    evolution_type: SkillEvolutionType
    trigger: str  # 触发原因
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    improvement: float  # 改进程度
    timestamp: float = field(default_factory=time.time)


@dataclass
class SkillMetrics:
    """技能指标"""
    skill_id: str
    success_count: int = 0
    failure_count: int = 0
    total_usage: int = 0
    avg_quality: float = 0.0
    avg_latency: float = 0.0
    last_used: float = 0.0


class SkillEvolutionEngine:
    """
    技能演化引擎

    功能:
    - 追踪技能使用情况
    - 分析失败模式
    - 触发技能改进
    - 记录演化历史

    使用示例:
        engine = SkillEvolutionEngine()

        # 记录技能使用
        engine.record_usage("draft_writer", success=True, quality=0.8, latency=2.5)

        # 获取需要改进的技能
        suggestions = engine.get_improvement_suggestions()
    """

    def __init__(
        self,
        min_success_rate: float = 0.7,
        max_avg_latency: float = 10.0
    ):
        self.min_success_rate = min_success_rate
        self.max_avg_latency = max_avg_latency

        self._skill_metrics: Dict[str, SkillMetrics] = {}
        self._evolution_history: List[EvolutionRecord] = {}
        self._evolution_counter = 0

    def record_usage(
        self,
        skill_id: str,
        success: bool,
        quality: float,
        latency: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录技能使用

        Args:
            skill_id: 技能ID
            success: 是否成功
            quality: 质量分数 (0-1)
            latency: 延迟（秒）
            context: 上下文信息
        """
        if skill_id not in self._skill_metrics:
            self._skill_metrics[skill_id] = SkillMetrics(skill_id=skill_id)

        metrics = self._skill_metrics[skill_id]

        metrics.total_usage += 1
        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1

        # 更新平均质量
        n = metrics.total_usage
        metrics.avg_quality = (metrics.avg_quality * (n - 1) + quality) / n

        # 更新平均延迟
        metrics.avg_latency = (metrics.avg_latency * (n - 1) + latency) / n

        metrics.last_used = time.time()

    def get_metrics(self, skill_id: str) -> Optional[SkillMetrics]:
        """获取技能指标"""
        return self._skill_metrics.get(skill_id)

    def get_success_rate(self, skill_id: str) -> float:
        """获取成功率"""
        metrics = self._skill_metrics.get(skill_id)
        if not metrics or metrics.total_usage == 0:
            return 0.0
        return metrics.success_count / metrics.total_usage

    def get_all_metrics(self) -> Dict[str, SkillMetrics]:
        """获取所有技能指标"""
        return self._skill_metrics.copy()

    def get_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """
        获取改进建议

        Returns:
            改进建议列表
        """
        suggestions = []

        for skill_id, metrics in self._skill_metrics.items():
            if metrics.total_usage < 5:
                continue

            # 检查成功率
            success_rate = metrics.success_count / metrics.total_usage
            if success_rate < self.min_success_rate:
                suggestions.append({
                    "skill_id": skill_id,
                    "issue": "low_success_rate",
                    "current_value": success_rate,
                    "threshold": self.min_success_rate,
                    "priority": "high" if success_rate < 0.5 else "medium",
                    "suggestion": "需要分析失败模式并改进"
                })

            # 检查延迟
            if metrics.avg_latency > self.max_avg_latency:
                suggestions.append({
                    "skill_id": skill_id,
                    "issue": "high_latency",
                    "current_value": metrics.avg_latency,
                    "threshold": self.max_avg_latency,
                    "priority": "medium",
                    "suggestion": "考虑优化或使用更快的替代方案"
                })

            # 检查质量
            if metrics.avg_quality < 0.6:
                suggestions.append({
                    "skill_id": skill_id,
                    "issue": "low_quality",
                    "current_value": metrics.avg_quality,
                    "threshold": 0.6,
                    "priority": "medium",
                    "suggestion": "需要提高输出质量"
                })

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return suggestions

    def trigger_evolution(
        self,
        skill_id: str,
        evolution_type: SkillEvolutionType,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any]
    ) -> str:
        """
        触发技能演化

        Args:
            skill_id: 技能ID
            evolution_type: 演化类型
            before_state: 演化前状态
            after_state: 演化后状态

        Returns:
            str: 演化记录ID
        """
        self._evolution_counter += 1
        record_id = f"evo_{self._evolution_counter}"

        # 计算改进程度
        before_score = self._calculate_score(before_state)
        after_score = self._calculate_score(after_state)
        improvement = after_score - before_score

        record = EvolutionRecord(
            record_id=record_id,
            skill_id=skill_id,
            evolution_type=evolution_type,
            trigger="auto",
            before_state=before_state,
            after_state=after_state,
            improvement=improvement
        )

        if skill_id not in self._evolution_history:
            self._evolution_history[skill_id] = []
        self._evolution_history[skill_id].append(record)

        logger.info(f"Skill evolution triggered: {skill_id} ({evolution_type.value}), improvement: {improvement:.3f}")
        return record_id

    def _calculate_score(self, state: Dict[str, Any]) -> float:
        """计算状态分数"""
        # 简单实现：基于几个关键指标
        success_rate = state.get("success_rate", 0.5)
        avg_quality = state.get("avg_quality", 0.5)
        avg_latency_normalized = 1.0 - min(state.get("avg_latency", 5.0) / 20.0, 1.0)

        return success_rate * 0.4 + avg_quality * 0.4 + avg_latency_normalized * 0.2

    def get_evolution_history(
        self,
        skill_id: Optional[str] = None
    ) -> List[EvolutionRecord]:
        """获取演化历史"""
        if skill_id:
            return self._evolution_history.get(skill_id, [])
        else:
            # 返回所有历史
            all_records = []
            for records in self._evolution_history.values():
                all_records.extend(records)
            return sorted(all_records, key=lambda x: x.timestamp, reverse=True)

    def get_skill_report(self, skill_id: str) -> Dict[str, Any]:
        """获取技能报告"""
        metrics = self._skill_metrics.get(skill_id)
        history = self._evolution_history.get(skill_id, [])

        if not metrics:
            return {"skill_id": skill_id, "found": False}

        success_rate = metrics.success_count / metrics.total_usage if metrics.total_usage > 0 else 0

        return {
            "skill_id": skill_id,
            "metrics": {
                "total_usage": metrics.total_usage,
                "success_rate": success_rate,
                "avg_quality": metrics.avg_quality,
                "avg_latency": metrics.avg_latency,
                "last_used": metrics.last_used
            },
            "evolution_count": len(history),
            "total_improvement": sum(e.improvement for e in history),
            "recent_improvements": [
                {"type": e.evolution_type.value, "improvement": e.improvement}
                for e in history[-3:]
            ]
        }

    def prune_skill(self, skill_id: str) -> bool:
        """
        剪枝技能

        如果技能长期表现不佳，标记为可删除
        """
        metrics = self._skill_metrics.get(skill_id)
        if not metrics:
            return False

        # 如果超过100次使用但成功率仍然很低
        if metrics.total_usage > 100:
            success_rate = metrics.success_count / metrics.total_usage
            if success_rate < 0.3:
                logger.warning(f"Skill {skill_id} marked for pruning: success_rate={success_rate:.2f}")
                return True

        return False


def create_evolution_engine() -> SkillEvolutionEngine:
    """创建技能演化引擎"""
    return SkillEvolutionEngine()
