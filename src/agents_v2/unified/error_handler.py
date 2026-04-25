"""
错误处理与降级策略

提供:
1. FallbackHandler: 降级处理
2. RetryPolicy: 重试策略
3. ErrorContext: 错误上下文
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"      # 不影响流程，可忽略
    MEDIUM = "medium"  # 需要注意，但可继续
    HIGH = "high"    # 需要干预
    CRITICAL = "critical"  # 流程必须停止


@dataclass
class ErrorContext:
    """错误上下文"""
    error: Exception
    phase: str
    agent_name: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """重试策略配置"""
    max_retries: int = 3
    initial_delay: float = 1.0  # 初始延迟(秒)
    max_delay: float = 60.0    # 最大延迟(秒)
    exponential_base: float = 2.0  # 指数退避基数
    retry_on: tuple = (Exception,)  # 可重试的异常类型


class FallbackHandler:
    """
    降级处理handler

    当Agent执行失败时，提供降级策略：
    1. 使用默认/缓存结果
    2. 跳过可选阶段
    3. 返回最小可用输出
    """

    # 各阶段降级策略
    PHASE_FALLBACKS = {
        "topic": {
            "default_output": {
                "selected_topic": {
                    "title": "待定研究主题",
                    "scope": "需要进一步明确",
                    "novelty_score": 0.3
                },
                "feasibility_report": {"score": 0.5, "concerns": ["需要用户确认"]}
            },
            "skip_allowed": False
        },
        "literature": {
            "default_output": {
                "papers": [],
                "literature_map": {},
                "gaps_identified": []
            },
            "skip_allowed": True  # 可以跳过，使用已有文献
        },
        "methodology": {
            "default_output": {
                "recommended_methods": [],
                " rigor_assessment": {"score": 0.4}
            },
            "skip_allowed": True
        },
        "argument": {
            "default_output": {
                "argument_framework": {},
                "logical_gaps": ["论证框架未建立"]
            },
            "skip_allowed": False
        },
        "writing": {
            "default_output": {
                "outline": [],
                "draft_sections": [],
                "report": "内容生成失败"
            },
            "skip_allowed": False
        },
        "polish": {
            "default_output": {
                "polished_text": "",
                "issues_identified": []
            },
            "skip_allowed": True
        }
    }

    def __init__(self, enable_caching: bool = True):
        self.enable_caching = enable_caching
        self.cache: Dict[str, Any] = {}

    def get_fallback(
        self,
        phase: str,
        context: Dict[str, Any],
        error: Optional[Exception] = None
    ) -> Dict[str, Any]:
        """
        获取降级输出

        Args:
            phase: 当前阶段
            context: 上下文
            error: 发生的错误

        Returns:
            降级后的输出
        """
        logger.warning(f"Using fallback for phase: {phase}")

        fallback_config = self.PHASE_FALLBACKS.get(phase, {})
        default_output = fallback_config.get("default_output", {})

        # 如果有缓存且启用，优先使用缓存
        if self.enable_caching and phase in self.cache:
            logger.info(f"Using cached result for phase: {phase}")
            return self.cache[phase]

        # 添加错误信息到输出
        if error:
            default_output["_error"] = str(error)
            default_output["_fallback_used"] = True

        return default_output

    def cache_result(self, phase: str, result: Dict[str, Any]):
        """缓存阶段结果"""
        if self.enable_caching:
            self.cache[phase] = result
            logger.debug(f"Cached result for phase: {phase}")

    def get_cached(self, phase: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        return self.cache.get(phase)

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()


class ErrorAccumulator:
    """错误累积器 - 收集并分析错误"""

    def __init__(self, max_errors: int = 50):
        self.max_errors = max_errors
        self.errors: List[ErrorContext] = []

    def add(self, context: ErrorContext):
        """添加错误"""
        self.errors.append(context)
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)

    def get_by_phase(self, phase: str) -> List[ErrorContext]:
        """获取特定阶段的错误"""
        return [e for e in self.errors if e.phase == phase]

    def get_by_severity(self, severity: ErrorSeverity) -> List[ErrorContext]:
        """获取特定严重程度的错误"""
        return [e for e in self.errors if e.severity == severity]

    def has_critical(self) -> bool:
        """是否有严重错误"""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)

    def summary(self) -> Dict[str, Any]:
        """生成错误摘要"""
        return {
            "total_errors": len(self.errors),
            "by_phase": {
                phase: len(self.get_by_phase(phase))
                for phase in set(e.phase for e in self.errors)
            },
            "by_severity": {
                sev.value: len(self.get_by_severity(sev))
                for sev in ErrorSeverity
            },
            "has_critical": self.has_critical()
        }


class RecoveryStrategy:
    """恢复策略"""

    @staticmethod
    def should_retry(error: Exception, retry_policy: RetryPolicy, current_retry: int) -> bool:
        """判断是否应该重试"""
        if current_retry >= retry_policy.max_retries:
            return False

        return isinstance(error, retry_policy.retry_on)

    @staticmethod
    def get_delay(retry_policy: RetryPolicy, current_retry: int) -> float:
        """计算延迟时间"""
        delay = retry_policy.initial_delay * (retry_policy.exponential_base ** current_retry)
        return min(delay, retry_policy.max_delay)


async def execute_with_retry(
    func: Callable,
    retry_policy: Optional[RetryPolicy] = None,
    fallback_handler: Optional[FallbackHandler] = None,
    phase: str = "unknown",
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    带重试和降级的执行

    Args:
        func: 要执行的函数
        retry_policy: 重试策略
        fallback_handler: 降级处理
        phase: 当前阶段
        context: 上下文

    Returns:
        执行结果
    """
    retry_policy = retry_policy or RetryPolicy()
    current_retry = 0

    while True:
        try:
            result = await func()
            return result
        except Exception as e:
            if not RecoveryStrategy.should_retry(e, retry_policy, current_retry):
                logger.error(f"Max retries reached for phase {phase}: {e}")

                # 尝试降级
                if fallback_handler:
                    return fallback_handler.get_fallback(phase, context or {}, e)
                raise

            current_retry += 1
            delay = RecoveryStrategy.get_delay(retry_policy, current_retry)
            logger.warning(f"Retry {current_retry}/{retry_policy.max_retries} for {phase}, delay={delay}s")
            time.sleep(delay)