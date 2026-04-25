"""
统一Agent框架 - 融合Pipeline型与问题导向型Agent

核心设计：
1. 双层Supervisor架构
   - MasterSupervisor: 全局状态管理与路由
   - PhaseSupervisor: 各阶段内部协调

2. 问题导向 + Pipeline流程融合
   - 诊断阶段: 问题导向Agent并 行诊断
   - 执行阶段: Pipeline型Agent顺序执行
   - 完善阶段: 问题导向Agent针对性修复

3. 状态机驱动
   - PHASE_ROUTING: 根据问题类型路由到对应Agent
   - QUALITY_GATES: 质量门控检查
   - ITERATION_CONTROL: 迭代次数控制

4. 错误处理机制
   - CircuitBreaker: 熔断器防止级联失败
   - FallbackHandler: 降级处理
   - RetryPolicy: 重试策略

使用方式:
agent = MasterSupervisor(llm_config)
result = await agent.run("full_paper", {"topic": "深度学习在医学影像中的应用"})
"""
from .state_model import PaperState, PhaseStatus, QualityScore, AgentResult
from .master_supervisor import MasterSupervisor
from .phase_supervisor import PhaseSupervisor
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from .error_handler import FallbackHandler, RetryPolicy

__all__ = [
    "PaperState",
    "PhaseStatus",
    "QualityScore",
    "AgentResult",
    "MasterSupervisor",
    "PhaseSupervisor",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "FallbackHandler",
    "RetryPolicy",
]