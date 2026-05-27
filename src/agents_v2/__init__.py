"""新架构Agent模块"""

# 加载环境变量（最早执行）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
from .workflow.unified import (
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

# 论文搜索和报告系统
from .agents.report import (
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
from .infra.skills import SkillsLoader, SkillDefinition

# Claude Agent SDK-style framework
from .api.sdk import (
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