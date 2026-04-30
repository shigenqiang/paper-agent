"""
Claude Agent SDK-style framework for Paper Agent.

Provides:
- @tool decorator: Convert Python functions to tools with auto schema generation
- Agent class: With lifecycle hooks (preToolUse/postToolUse), tool use loop, subagents
- ContextCompressor: Auto context compression for long-running conversations
- ToolRegistry: Global tool registry with MCP-compatible schema export

Usage:
    from src.agents_v2.sdk import Agent, AgentConfig, tool

    @tool
    async def search_papers(query: str, max_results: int = 10) -> dict:
        '''Search academic papers.'''
        ...

    agent = Agent(
        name="research_agent",
        system_prompt="You are a research assistant.",
        tools=[search_papers],
    )

    result = await agent.run("Find papers about graph neural networks")
"""

from .tool import (
    tool,
    ToolDefinition,
    ToolRegistry,
    tool_registry,
    get_tool,
    list_tools,
    get_tool_schemas,
    get_mcp_tool_schemas,
)
from .agent import (
    Agent,
    AgentConfig,
    AgentState,
    Permission,
    ToolCallRequest,
    ToolCallResult,
)
from .context import ContextCompressor, CompressionResult, estimate_tokens

__all__ = [
    # Tool decorator
    "tool",
    "ToolDefinition",
    "ToolRegistry",
    "tool_registry",
    "get_tool",
    "list_tools",
    "get_tool_schemas",
    "get_mcp_tool_schemas",
    # Agent
    "Agent",
    "AgentConfig",
    "AgentState",
    "Permission",
    "ToolCallRequest",
    "ToolCallResult",
    # Context
    "ContextCompressor",
    "CompressionResult",
    "estimate_tokens",
]
