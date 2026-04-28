"""
Cost Tracker - 成本追踪器

提供精确的Token消耗和成本控制功能。
"""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token使用记录"""
    agent_id: str
    operation: str
    input_tokens: int
    output_tokens: int
    model: str
    timestamp: float = field(default_factory=time.time)
    cost_usd: float = 0.0
    latency_ms: float = 0.0


@dataclass
class CostReport:
    """成本报告"""
    total_budget: float
    total_spent: float
    remaining: float
    input_tokens: int
    output_tokens: int
    operation_breakdown: Dict[str, float]
    agent_breakdown: Dict[str, float]
    utilization_percent: float


@dataclass
class BudgetTracker:
    """预算追踪器"""
    total_budget_usd: float
    spent_usd: float = 0.0
    warning_threshold: float = 0.8

    @property
    def remaining_usd(self) -> float:
        return self.total_budget_usd - self.spent_usd

    def can_afford(self, estimated_cost: float) -> bool:
        """检查是否能负担"""
        return self.remaining_usd >= estimated_cost

    def record_usage(self, usage: TokenUsage) -> None:
        """记录使用量"""
        self.spent_usd += usage.cost_usd

        if self.spent_usd / self.total_budget_usd >= self.warning_threshold:
            self._trigger_warning()

    def _trigger_warning(self) -> None:
        """触发警告"""
        logger.warning(f"Budget warning: {self.spent_usd / self.total_budget_usd * 100:.1f}% used")


class CostTracker:
    """
    实时成本追踪器

    功能:
    - 追踪每次LLM调用的token消耗
    - 实时计算USD成本
    - 按操作和Agent分组统计
    - 预算警告

    使用示例:
        tracker = CostTracker(total_budget=10.0)

        # 追踪操作
        await tracker.track_operation(
            agent_id="writer",
            operation="draft_write",
            input_text="Hello world",
            output_text="Response",
            model="gpt-4"
        )

        # 获取报告
        report = tracker.get_report()
        print(f"Total spent: ${report.total_spent:.4f}")
    """

    # 模型定价 (per 1K tokens)
    MODEL_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "gemini-pro": {"input": 0.00125, "output": 0.005},
    }

    def __init__(self, total_budget: float = 10.0, warning_threshold: float = 0.8):
        self.total_budget = total_budget
        self.warning_threshold = warning_threshold

        self.reset()

    def reset(self) -> None:
        """重置所有统计"""
        self.total_spent = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.operation_costs: Dict[str, float] = {}
        self.operation_tokens: Dict[str, int] = {}
        self.agent_costs: Dict[str, float] = {}
        self.agent_tokens: Dict[str, int] = {}
        self._usage_records: List[TokenUsage] = []
        self._warnings_triggered = set()

    async def track_operation(
        self,
        agent_id: str,
        operation: str,
        input_text: str,
        output_text: str,
        model: str,
        latency_ms: float = 0.0,
        custom_pricing: Optional[Dict[str, float]] = None
    ) -> TokenUsage:
        """
        追踪单个操作的成本

        Args:
            agent_id: Agent ID
            operation: 操作名称
            input_text: 输入文本
            output_text: 输出文本
            model: 模型名称
            latency_ms: 延迟（毫秒）
            custom_pricing: 自定义定价

        Returns:
            TokenUsage: 使用记录
        """
        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(output_text)

        # 获取定价
        pricing = custom_pricing or self.MODEL_PRICING.get(model, {"input": 0.01, "output": 0.03})

        # 计算成本
        cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

        usage = TokenUsage(
            agent_id=agent_id,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            timestamp=time.time(),
            cost_usd=cost,
            latency_ms=latency_ms
        )

        self._record_usage(usage)
        return usage

    def _record_usage(self, usage: TokenUsage) -> None:
        """内部记录使用"""
        # 更新总计
        self.total_spent += usage.cost_usd
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens

        # 按操作分组
        if usage.operation not in self.operation_costs:
            self.operation_costs[usage.operation] = 0.0
            self.operation_tokens[usage.operation] = 0
        self.operation_costs[usage.operation] += usage.cost_usd
        self.operation_tokens[usage.operation] += usage.input_tokens + usage.output_tokens

        # 按Agent分组
        if usage.agent_id not in self.agent_costs:
            self.agent_costs[usage.agent_id] = 0.0
            self.agent_tokens[usage.agent_id] = 0
        self.agent_costs[usage.agent_id] += usage.cost_usd
        self.agent_tokens[usage.agent_id] += usage.input_tokens + usage.output_tokens

        # 记录
        self._usage_records.append(usage)

        # 检查预算警告
        self._check_budget_warning()

    def _check_budget_warning(self) -> None:
        """检查预算警告"""
        if self.total_budget <= 0:
            return

        utilization = self.total_spent / self.total_budget

        if utilization >= self.warning_threshold and "budget_warning" not in self._warnings_triggered:
            logger.warning(
                f"Budget warning: {utilization * 100:.1f}% used "
                f"(${self.total_spent:.4f} / ${self.total_budget:.2f})"
            )
            self._warnings_triggered.add("budget_warning")

    def _estimate_tokens(self, text: str) -> int:
        """
        估算token数量

        规则:
        - 中文: 约2 tokens/字
        - 英文: 约1.5 tokens/词
        """
        if not text:
            return 0

        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        english_words = len(text.split()) - chinese_chars

        return int(chinese_chars * 2 + english_words * 1.5)

    def get_report(self) -> CostReport:
        """获取成本报告"""
        return CostReport(
            total_budget=self.total_budget,
            total_spent=self.total_spent,
            remaining=self.total_budget - self.total_spent,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            operation_breakdown=self.operation_costs.copy(),
            agent_breakdown=self.agent_costs.copy(),
            utilization_percent=(self.total_spent / self.total_budget * 100) if self.total_budget > 0 else 0
        )

    def get_usage_records(
        self,
        agent_id: Optional[str] = None,
        operation: Optional[str] = None,
        limit: int = 100
    ) -> List[TokenUsage]:
        """获取使用记录"""
        records = self._usage_records

        if agent_id:
            records = [r for r in records if r.agent_id == agent_id]

        if operation:
            records = [r for r in records if r.operation == operation]

        return records[-limit:]

    def get_operation_stats(self) -> Dict[str, Any]:
        """获取操作统计"""
        return {
            op: {
                "cost_usd": self.operation_costs[op],
                "total_tokens": self.operation_tokens[op],
                "call_count": sum(1 for r in self._usage_records if r.operation == op)
            }
            for op in self.operation_costs.keys()
        }

    def get_agent_stats(self) -> Dict[str, Any]:
        """获取Agent统计"""
        return {
            agent: {
                "cost_usd": self.agent_costs[agent],
                "total_tokens": self.agent_tokens[agent],
                "call_count": sum(1 for r in self._usage_records if r.agent_id == agent)
            }
            for agent in self.agent_costs.keys()
        }

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> float:
        """估算成本"""
        pricing = self.MODEL_PRICING.get(model, {"input": 0.01, "output": 0.03})
        return (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

    def can_proceed(self, estimated_cost: float) -> bool:
        """检查是否可以继续（预算足够）"""
        return (self.total_spent + estimated_cost) <= self.total_budget


class CostTrackerDecorator:
    """成本追踪装饰器"""

    def __init__(self, tracker: CostTracker, agent_id: str):
        self.tracker = tracker
        self.agent_id = agent_id

    async def track(
        self,
        operation: str,
        model: str
    ) -> Callable:
        """装饰器函数"""
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                # 记录开始时间
                start_time = time.time()

                # 执行函数
                result = await func(*args, **kwargs)

                # 估算成本
                latency_ms = (time.time() - start_time) * 1000

                # 获取输入输出文本
                input_text = str(args) if args else ""
                output_text = str(result) if result else ""

                # 追踪
                await self.tracker.track_operation(
                    agent_id=self.agent_id,
                    operation=operation,
                    input_text=input_text,
                    output_text=output_text,
                    model=model,
                    latency_ms=latency_ms
                )

                return result

            return wrapper
        return decorator


def create_cost_tracker(total_budget: float = 10.0) -> CostTracker:
    """创建成本追踪器"""
    return CostTracker(total_budget=total_budget)
