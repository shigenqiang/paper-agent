"""
自主学习引擎 - Self Learning Engine

核心功能:
1. 从失败中学习
2. 技能自动优化
3. 新任务适应
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class LearningEpisode:
    """学习 episode"""
    task: str
    attempts: int
    success: bool
    final_strategy: str
    metrics: Dict[str, float]
    timestamp: float = field(default_factory=time.time)
    error_message: str = ""


@dataclass
class StrategyAdjustment:
    """策略调整"""
    strategy_name: str
    adjustment_type: str  # "increase", "decrease", "replace"
    change_amount: float
    reason: str
    resulting_score: float


class SelfLearningEngine:
    """自主学习引擎

    通过观察执行结果自动优化策略和技能。
    """

    def __init__(self,
                 memory_window: int = 100,
                 improvement_threshold: float = 0.05):
        """初始化

        Args:
            memory_window: 保留的历史 episode 数量
            improvement_threshold: 触发策略调整的改进阈值
        """
        self.memory_window = memory_window
        self.improvement_threshold = improvement_threshold
        self._episodes: deque = deque(maxlen=memory_window)
        self._strategies: Dict[str, float] = {}  # strategy_name -> score
        self._skill_registry: Dict[str, Callable] = {}
        self._learning_rules: List[Dict] = []

    def record_attempt(self, task: str, success: bool, strategy_used: str,
                       metrics: Dict = None, error: str = ""):
        """记录一次尝试

        Args:
            task: 任务描述
            success: 是否成功
            strategy_used: 使用的策略
            metrics: 指标
            error: 错误信息
        """
        episode = LearningEpisode(
            task=task,
            attempts=1,
            success=success,
            final_strategy=strategy_used,
            metrics=metrics or {},
            error_message=error
        )

        self._episodes.append(episode)
        self._update_strategy_score(strategy_used, success)

        logger.info(f"记录尝试: task={task[:30]}, success={success}, strategy={strategy_used}")

    def _update_strategy_score(self, strategy: str, success: bool):
        """更新策略分数"""
        if strategy not in self._strategies:
            self._strategies[strategy] = 0.5

        # 指数移动平均
        alpha = 0.3
        self._strategies[strategy] = alpha * (1.0 if success else 0.0) + (1 - alpha) * self._strategies[strategy]

    async def analyze_failures(self) -> List[str]:
        """分析失败模式

        Returns:
            List[str]: 失败模式列表
        """
        failed_episodes = [e for e in self._episodes if not e.success]

        if not failed_episodes:
            return []

        # 简单聚类：按错误消息分组
        error_groups: Dict[str, List] = {}
        for episode in failed_episodes:
            error_key = episode.error_message[:50] if episode.error_message else "unknown"
            if error_key not in error_groups:
                error_groups[error_key] = []
            error_groups[error_key].append(episode)

        patterns = []
        for error_key, episodes in error_groups.items():
            if len(episodes) >= 2:
                patterns.append(f"重复错误 ({len(episodes)}次): {error_key}")

        return patterns

    async def suggest_improvements(self) -> List[StrategyAdjustment]:
        """建议策略改进

        Returns:
            List[StrategyAdjustment]: 策略调整建议
        """
        suggestions = []

        # 分析最近成功的策略
        recent_successes = [e for e in self._episodes if e.success][-10:]

        if len(recent_successes) < 3:
            return suggestions

        # 找出成功率高但使用率低的策略
        strategy_success = {}
        for episode in recent_successes:
            strategy = episode.final_strategy
            if strategy not in strategy_success:
                strategy_success[strategy] = {"success": 0, "total": 0}
            strategy_success[strategy]["total"] += 1
            strategy_success[strategy]["success"] += 1

        for strategy, stats in strategy_success.items():
            if stats["total"] >= 3 and stats["success"] / stats["total"] > 0.8:
                suggestions.append(StrategyAdjustment(
                    strategy_name=strategy,
                    adjustment_type="increase",
                    change_amount=0.2,
                    reason=f"成功率 {stats['success']/stats['total']:.1%}",
                    resulting_score=min(1.0, self._strategies.get(strategy, 0) + 0.2)
                ))

        return suggestions

    async def learn_from_success(self, task: str) -> Optional[str]:
        """从成功中学习，提取成功策略

        Args:
            task: 任务描述

        Returns:
            Optional[str]: 提取的策略
        """
        # 找最相似的成功任务
        similar = [e for e in self._episodes if e.success and task in e.task]

        if not similar:
            return None

        # 返回最成功的一次使用的策略
        best = max(similar, key=lambda e: sum(e.metrics.values()) if e.metrics else 0.5)
        return best.final_strategy

    def register_skill(self, name: str, skill_fn: Callable):
        """注册技能函数

        Args:
            name: 技能名称
            skill_fn: 技能函数
        """
        self._skill_registry[name] = skill_fn
        logger.info(f"注册技能: {name}")

    async def execute_with_learning(self,
                                     task: str,
                                     primary_strategy: str,
                                     fallback_strategies: List[str] = None) -> Dict[str, Any]:
        """带学习的执行

        Args:
            task: 任务
            primary_strategy: 主策略
            fallback_strategies: 备用策略列表

        Returns:
            Dict: 执行结果
        """
        if fallback_strategies is None:
            fallback_strategies = []

        strategies_to_try = [primary_strategy] + fallback_strategies

        last_error = ""
        for i, strategy in enumerate(strategies_to_try):
            try:
                logger.info(f"尝试策略: {strategy}")

                # 模拟执行
                result = await self._execute_strategy(strategy, task)

                if result.get("success"):
                    self.record_attempt(task, True, strategy, result.get("metrics", {}))
                    return result
                else:
                    last_error = result.get("error", "unknown")
                    self.record_attempt(task, False, strategy, {}, error=last_error)

            except Exception as e:
                last_error = str(e)
                self.record_attempt(task, False, strategy, {}, error=last_error)
                logger.error(f"策略 {strategy} 执行失败: {e}")

        # 所有策略都失败
        return {
            "success": False,
            "error": last_error,
            "attempts": len(strategies_to_try)
        }

    async def _execute_strategy(self, strategy: str, task: str) -> Dict[str, Any]:
        """执行策略"""
        # 检查是否有注册的技能
        if strategy in self._skill_registry:
            try:
                result = await self._skill_registry[strategy](task)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # 默认模拟执行
        return {"success": True, "result": f"Executed {strategy} for {task}"}

    def get_learning_stats(self) -> Dict[str, Any]:
        """获取学习统计

        Returns:
            Dict: 统计信息
        """
        total = len(self._episodes)
        successes = sum(1 for e in self._episodes if e.success)

        return {
            "total_episodes": total,
            "success_rate": successes / total if total > 0 else 0,
            "strategy_scores": self._strategies.copy(),
            "skill_count": len(self._skill_registry),
            "recent_failures": len([e for e in self._episodes if not e.success][-5:])
        }

    def clear_history(self):
        """清除历史记录"""
        self._episodes.clear()
        logger.info("清除学习历史")


# 便捷函数
def create_learning_engine(memory_window: int = 100) -> SelfLearningEngine:
    """创建学习引擎"""
    return SelfLearningEngine(memory_window=memory_window)