"""新架构Agent模块"""
from .base_agent import (
    BaseAgent,
    AgentInput,
    AgentOutput,
    AgentCapability,
    LLMConfig,
    Tool,
    VirtualTool
)

# 统一框架
from .unified import (
    MasterSupervisor,
    PhaseSupervisor,
    PaperState,
    CircuitBreaker,
    CircuitBreakerOpen,
    FallbackHandler,
    RetryPolicy,
    ProblemType,
    PhaseStatus,
    QualityLevel
)

# 统计学问答系统
from .qa import (
    QueryRouter,
    PaperSearchAgent,
    ReportGenerator,
    DailyWatcher,
    CitationManager,
    QuestionType,
    RoutingDecision,
    Paper,
    SearchResult,
    PaperReport,
    DailyPaperReport,
    Citation
)

__all__ = [
    # Base agent
    "BaseAgent",
    "AgentInput",
    "AgentOutput",
    "AgentCapability",
    "LLMConfig",
    "Tool",
    "VirtualTool",
    # 统一框架
    "MasterSupervisor",
    "PhaseSupervisor",
    "PaperState",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "FallbackHandler",
    "RetryPolicy",
    "ProblemType",
    "PhaseStatus",
    "QualityLevel",
    # 统计学问答系统
    "QueryRouter",
    "PaperSearchAgent",
    "ReportGenerator",
    "DailyWatcher",
    "CitationManager",
    "QuestionType",
    "RoutingDecision",
    "Paper",
    "SearchResult",
    "PaperReport",
    "DailyPaperReport",
    "Citation"
]