"""
Error Recovery System - 错误恢复系统

提供细粒度的错误分类和智能恢复策略。
底层使用 core/error_recovery.py 的共享原语。
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

from ..core.error_recovery import (
    ErrorCategory,
    CircuitBreaker,
    retry_with_backoff,
    with_fallback,
    classify_error as core_classify_error,
)

logger = logging.getLogger(__name__)


# 保留原有枚举用于向后兼容，映射到 core ErrorCategory
class UnifiedErrorCategory(str, Enum):
    """错误类别（unified子系统专用）"""
    INVALID_INPUT = "invalid_input"
    TIMEOUT = "timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_CONTEXT_OVERFLOW = "llm_context_overflow"
    EXTERNAL_API_FAILURE = "external_api_failure"
    VALIDATION_FAILURE = "validation_failure"
    SYSTEM_ERROR = "system_error"
    USER_ERROR = "user_error"


# 向后兼容别名
ErrorCategory = UnifiedErrorCategory


class RetryAction(str, Enum):
    """重试动作"""
    RETRY = "retry"
    ABORT = "abort"
    FALLBACK = "fallback"
    SKIP = "skip"


@dataclass
class RecoveryStep:
    """恢复步骤"""
    action: str
    target: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    estimated_time: float = 0.0


@dataclass
class RecoveryPlan:
    """恢复计划"""
    steps: List[RecoveryStep] = field(default_factory=list)
    estimated_total_time: float = 0.0
    fallback_available: bool = True
    fallback_plan: Optional["RecoveryPlan"] = None


@dataclass
class ErrorRecord:
    """错误记录"""
    error_id: str
    category: ErrorCategory
    message: str
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    recovered: bool = False


class GranularErrorRecovery:
    """
    细粒度错误恢复策略

    根据错误类型、上下文、严重程度选择最优恢复策略

    使用示例:
        recovery = GranularErrorRecovery()

        # 获取恢复计划
        plan = recovery.get_recovery_plan(error, context)

        # 执行恢复
        result = await recovery.execute(plan)
    """

    # 错误类型 -> 恢复策略映射
    ERROR_RECOVERY_STRATEGY_MAP = {
        ErrorCategory.INVALID_INPUT: [
            {"strategy": "validate_and_retry", "timeout": 5, "max_attempts": 2},
            {"strategy": "use_defaults", "timeout": 1, "max_attempts": 1},
        ],
        ErrorCategory.TIMEOUT: [
            {"strategy": "retry_with_backoff", "timeout": 30, "max_attempts": 3},
            {"strategy": "reduce_scope", "timeout": 15, "max_attempts": 1},
        ],
        ErrorCategory.LLM_RATE_LIMIT: [
            {"strategy": "rate_limit_backoff", "timeout": 60, "max_attempts": 5},
            {"strategy": "switch_to_cache", "timeout": 5, "max_attempts": 1},
        ],
        ErrorCategory.LLM_CONTEXT_OVERFLOW: [
            {"strategy": "truncate_context", "timeout": 10, "max_attempts": 1},
            {"strategy": "summarize_history", "timeout": 30, "max_attempts": 2},
            {"strategy": "split_task", "timeout": 60, "max_attempts": 1},
        ],
        ErrorCategory.EXTERNAL_API_FAILURE: [
            {"strategy": "retry", "timeout": 15, "max_attempts": 3},
            {"strategy": "fallback_to_cache", "timeout": 5, "max_attempts": 1},
            {"strategy": "skip_with_warning", "timeout": 1, "max_attempts": 1},
        ],
    }

    def __init__(self):
        self._recovery_history: List[Dict[str, Any]] = []
        self._strategy_success_rates: Dict[str, float] = {}

    def get_recovery_plan(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryPlan:
        """
        生成恢复计划

        Args:
            error: 错误
            context: 恢复上下文

        Returns:
            RecoveryPlan: 包含具体的恢复步骤
        """
        category = self._classify_error(error)
        strategies = self.ERROR_RECOVERY_STRATEGY_MAP.get(
            category,
            [{"strategy": "log_and_continue", "timeout": 5, "max_attempts": 1}]
        )

        # 选择最佳策略（基于历史成功率）
        best_strategy = self._select_best_strategy(strategies)

        # 生成具体的恢复步骤
        plan = self._generate_recovery_steps(best_strategy, error, context)

        return plan

    def _classify_error(self, error: Exception) -> ErrorCategory:
        """分类错误（优先使用 core 分类器）"""
        core_cat = core_classify_error(error)
        mapping = {
            "rate_limit": ErrorCategory.LLM_RATE_LIMIT,
            "quota": ErrorCategory.LLM_RATE_LIMIT,
            "timeout": ErrorCategory.TIMEOUT,
            "connection": ErrorCategory.EXTERNAL_API_FAILURE,
            "context_overflow": ErrorCategory.LLM_CONTEXT_OVERFLOW,
            "invalid_input": ErrorCategory.INVALID_INPUT,
            "external_api": ErrorCategory.EXTERNAL_API_FAILURE,
        }
        return mapping.get(core_cat.value, ErrorCategory.SYSTEM_ERROR)

    def _select_best_strategy(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """选择最佳策略（基于历史成功率）"""
        for strategy in strategies:
            strategy_name = strategy["strategy"]
            success_rate = self._strategy_success_rates.get(strategy_name, 0.5)

            if success_rate >= 0.7:
                return strategy

        return strategies[0] if strategies else {"strategy": "log_and_continue"}

    def _generate_recovery_steps(
        self,
        strategy: Dict[str, Any],
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryPlan:
        """生成具体的恢复步骤"""
        strategy_name = strategy["strategy"]

        steps = []
        estimated_time = 0.0

        if strategy_name == "retry_with_backoff":
            delay = self._calculate_backoff(context.get("attempt_count", 0))
            steps.extend([
                RecoveryStep(
                    action="wait",
                    target="system",
                    parameters={"duration": delay},
                    description=f"等待{delay}秒后重试"
                ),
                RecoveryStep(
                    action="retry",
                    target=context.get("failed_operation", "unknown"),
                    parameters=self._prepare_retry_params(context),
                    description=f"重试操作 {context.get('failed_operation', 'unknown')}"
                )
            ])
            estimated_time = delay + 10

        elif strategy_name == "truncate_context":
            max_tokens = context.get("max_tokens", 4000)
            steps.extend([
                RecoveryStep(
                    action="analyze_context",
                    target="context_window",
                    parameters={},
                    description="分析上下文哪些部分可以截断"
                ),
                RecoveryStep(
                    action="truncate",
                    target="oldest_messages",
                    parameters={"keep_recent": max_tokens // 2},
                    description="截断历史消息，保留最近一半"
                ),
                RecoveryStep(
                    action="retry",
                    target=context.get("failed_operation", "unknown"),
                    description="重试操作"
                )
            ])
            estimated_time = 15

        elif strategy_name == "switch_to_cache":
            steps.extend([
                RecoveryStep(
                    action="check_cache",
                    target=context.get("failed_operation", "unknown"),
                    parameters={},
                    description="检查是否有缓存的可用结果"
                ),
                RecoveryStep(
                    action="use_cached_result",
                    target="cache",
                    parameters={},
                    description="使用缓存结果"
                )
            ])
            estimated_time = 5

        elif strategy_name == "reduce_scope":
            steps.extend([
                RecoveryStep(
                    action="reduce_task_scope",
                    target="task",
                    parameters={"reduction_factor": 0.5},
                    description="减少任务范围"
                ),
                RecoveryStep(
                    action="retry",
                    target=context.get("failed_operation", "unknown"),
                    description="重试缩小后的任务"
                )
            ])
            estimated_time = 10

        else:  # log_and_continue
            steps.append(RecoveryStep(
                action="log",
                target="error",
                parameters={"message": str(error)},
                description="记录错误并继续"
            ))
            estimated_time = 1

        return RecoveryPlan(
            steps=steps,
            estimated_total_time=estimated_time,
            fallback_available=True
        )

    def _calculate_backoff(self, attempt_count: int, base: float = 1.0, max_delay: float = 60.0) -> float:
        """计算退避时间"""
        delay = base * (2 ** attempt_count)
        return min(delay, max_delay)

    def _prepare_retry_params(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """准备重试参数"""
        return {
            "operation": context.get("failed_operation"),
            "parameters": context.get("original_parameters", {})
        }

    def record_recovery_result(
        self,
        strategy_name: str,
        success: bool,
        duration: float
    ) -> None:
        """记录恢复结果用于学习"""
        # 更新成功率统计
        if strategy_name not in self._strategy_success_rates:
            self._strategy_success_rates[strategy_name] = 0.5

        current = self._strategy_success_rates[strategy_name]
        # 指数移动平均
        self._strategy_success_rates[strategy_name] = current * 0.9 + (1.0 if success else 0.0) * 0.1

        self._recovery_history.append({
            "strategy": strategy_name,
            "success": success,
            "duration": duration,
            "timestamp": time.time()
        })

    async def execute(self, plan: RecoveryPlan) -> Dict[str, Any]:
        """执行恢复计划"""
        results = []

        for step in plan.steps:
            try:
                result = await self._execute_step(step)
                results.append({"step": step.action, "success": True, "result": result})
            except Exception as e:
                results.append({"step": step.action, "success": False, "error": str(e)})

                # 如果步骤失败，尝试fallback
                if plan.fallback_plan:
                    return await self.execute(plan.fallback_plan)

                break

        return {
            "success": all(r.get("success", False) for r in results),
            "steps_executed": len(results),
            "results": results
        }

    async def _execute_step(self, step: RecoveryStep) -> Any:
        """执行单个恢复步骤"""
        action = step.action

        if action == "wait":
            import asyncio
            await asyncio.sleep(step.parameters.get("duration", 1))
            return {"waited": step.parameters.get("duration")}

        elif action == "retry":
            # 这里应该执行重试逻辑
            return {"retried": step.target}

        elif action == "truncate":
            return {"truncated": step.target}

        elif action == "use_cached_result":
            return {"used_cache": True}

        return {"completed": action}


def create_error_recovery() -> GranularErrorRecovery:
    """创建错误恢复系统"""
    return GranularErrorRecovery()
