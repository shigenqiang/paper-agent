"""Agent SDK"""
from .agent import Agent, AgentConfig, AgentState, Permission, ToolCallRequest, ToolCallResult
from .tool import tool, ToolDefinition, ToolRegistry, get_tool, list_tools, get_tool_schemas, get_mcp_tool_schemas
from .context import ContextCompressor

def estimate_tokens(text: str) -> int:
    return len(text) // 4
