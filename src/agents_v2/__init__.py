"""新架构Agent模块"""
from .core.base_agent import (
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

# Agent Skills (SKILL.md standard)
from .skills import SkillsLoader, SkillDefinition

# Claude Agent SDK-style framework
from .sdk import (
    tool,
    Agent,
    AgentConfig,
    AgentState,
    Permission,
    ToolDefinition,
    ToolRegistry,
    ToolCallRequest,
    ToolCallResult,
    ContextCompressor,
    get_tool,
    list_tools,
    get_tool_schemas,
    get_mcp_tool_schemas,
    estimate_tokens,
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
    "Citation",
    # Agent Skills
    "SkillsLoader",
    "SkillDefinition",
    # Claude Agent SDK
    "tool",
    "Agent",
    "AgentConfig",
    "AgentState",
    "Permission",
    "ToolDefinition",
    "ToolRegistry",
    "ToolCallRequest",
    "ToolCallResult",
    "ContextCompressor",
    "get_tool",
    "list_tools",
    "get_tool_schemas",
    "get_mcp_tool_schemas",
    "estimate_tokens",
]