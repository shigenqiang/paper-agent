"""
工具模块 - 统一管理Agent工具

提供:
1. 工具规格定义 (ToolSpec, ParameterSpec)
2. 工具注册表 (ToolRegistry)
3. 工具协同引擎 (ToolCoordinationEngine)
4. 内置工具 (buildin_tools)
"""
from .tool_spec import (
    ToolSpec,
    ParameterSpec,
    ParameterType,
    ValidationResult,
    ToolResult
)
from .registry import (
    ToolRegistry,
    get_tool_registry,
    register_builtin_tools
)
from .tool_coordinator import (
    ToolCoordinationEngine,
    DependencyType,
    ToolDependency,
    ExecutionPlan,
    get_coordination_engine
)
from .buildin_tools import register_all
from .extended_search import register_extended
from .paper_tools import register_paper_tools

__all__ = [
    # 工具规格
    "ToolSpec",
    "ParameterSpec",
    "ParameterType",
    "ValidationResult",
    "ToolResult",
    # 注册表
    "ToolRegistry",
    "get_tool_registry",
    "register_builtin_tools",
    # 协同引擎
    "ToolCoordinationEngine",
    "DependencyType",
    "ToolDependency",
    "ExecutionPlan",
    "get_coordination_engine",
    # 内置工具
    "register_all",
    "register_extended",
    "register_paper_tools"
]
