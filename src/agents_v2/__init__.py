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

__all__ = [
    "BaseAgent",
    "AgentInput",
    "AgentOutput",
    "AgentCapability",
    "LLMConfig",
    "Tool",
    "VirtualTool"
]
