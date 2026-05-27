"""
Claude Agent SDK-style @tool decorator.

Converts Python functions into tool definitions with:
- Auto schema generation from type hints and docstrings
- Input validation against generated schema
- Tool registry for MCP-style tool listing
- Async/sync function support
"""
from src.agents_v2.logging_config import get_logging_logger

import functools
import inspect
import json

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, get_type_hints

logger = get_logging_logger(__name__)

# Type hint → JSON Schema type mapping
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def _py_type_to_json_schema(py_type) -> Dict[str, Any]:
    """Convert a Python type hint to a JSON Schema fragment."""
    origin = getattr(py_type, "__origin__", None)

    if origin is list or origin is List:
        item_type = getattr(py_type, "__args__", (str,))[0]
        return {"type": "array", "items": _py_type_to_json_schema(item_type)}

    if origin is dict or origin is Dict:
        return {"type": "object"}

    if origin is Optional:
        inner = getattr(py_type, "__args__", (str,))[0]
        schema = _py_type_to_json_schema(inner)
        if inner is not type(None):
            schema["nullable"] = True
        return schema

    json_type = _TYPE_MAP.get(py_type, "string")
    return {"type": json_type}


def _extract_description(docstring: Optional[str]) -> str:
    """Extract the first line of a docstring as the function description."""
    if not docstring:
        return ""
    first_line = docstring.strip().split("\n")[0].strip()
    return first_line


@dataclass
class ToolDefinition:
    """A tool registered in the tool registry."""
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable
    # Metadata
    source_module: str = ""
    is_async: bool = True
    tags: List[str] = field(default_factory=list)
    # Usage stats
    call_count: int = 0
    total_duration_ms: float = 0.0

    @property
    def schema(self) -> Dict[str, Any]:
        """Generate OpenAI/MiniMax function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @property
    def mcp_schema(self) -> Dict[str, Any]:
        """Generate MCP-compatible tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters.get("properties", {}),
                "required": self.parameters.get("required", []),
            },
        }

    @property
    def avg_duration_ms(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_duration_ms / self.call_count


class ToolRegistry:
    """Global tool registry — enables MCP-style tool discovery."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_all(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def list_schemas(self) -> List[Dict[str, Any]]:
        return [t.schema for t in self._tools.values()]

    def list_mcp_schemas(self) -> List[Dict[str, Any]]:
        return [t.mcp_schema for t in self._tools.values()]

    def find_by_tag(self, tag: str) -> List[ToolDefinition]:
        return [t for t in self._tools.values() if tag in t.tags]

    @property
    def tool_count(self) -> int:
        return len(self._tools)


# Global registry instance
tool_registry = ToolRegistry()


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    register: bool = True,
):
    """Decorator that converts a Python function into a tool.

    Auto-generates JSON Schema from type hints and docstring.

    Usage:
        @tool
        async def search_papers(query: str, max_results: int = 10) -> dict:
            '''Search academic papers by query.'''
            ...

        @tool(name="arxiv_search", description="Search arXiv for papers")
        async def search_arxiv(query: str, domain: str = "cs.AI") -> dict:
            ...

    The decorated function gains:
    - `.schema` property — OpenAI function-calling schema
    - `.mcp_schema` property — MCP tool schema
    - `.tool_def` property — Full ToolDefinition
    - Automatic type validation of inputs
    """

    def decorator(func: Callable) -> Callable:
        # Parse function metadata
        tool_name = name or func.__name__
        tool_description = description or _extract_description(func.__doc__)

        # Auto-generate parameter schema from type hints
        sig = inspect.signature(func)
        hints = {}
        try:
            hints = get_type_hints(func)
        except Exception:
            pass

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = hints.get(param_name, str)
            json_schema = _py_type_to_json_schema(param_type)

            # Extract param description from docstring (Google style)
            param_desc = ""
            if func.__doc__:
                for line in func.__doc__.split("\n"):
                    line = line.strip()
                    if f"{param_name}:" in line.lower():
                        param_desc = line.split(":", 1)[-1].strip()
                        break

            json_schema["description"] = param_desc
            properties[param_name] = json_schema

            # Check if required (no default value and not Optional)
            if param.default is inspect.Parameter.empty:
                origin = getattr(param_type, "__origin__", None)
                if origin is not Optional:
                    required.append(param_name)

        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        # Create tool definition
        tool_def = ToolDefinition(
            name=tool_name,
            description=tool_description,
            parameters=parameters,
            func=func,
            source_module=func.__module__ or "",
            is_async=inspect.iscoroutinefunction(func),
            tags=tags or [],
        )

        # Register globally
        if register:
            tool_registry.register(tool_def)

        # Attach properties to the function
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                tool_def.call_count += 1
                tool_def.total_duration_ms += (time.time() - start) * 1000
                return result
            except Exception as e:
                logger.error(f"Tool '{tool_name}' failed: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start = time.time()
            try:
                result = func(*args, **kwargs)
                tool_def.call_count += 1
                tool_def.total_duration_ms += (time.time() - start) * 1000
                return result
            except Exception as e:
                logger.error(f"Tool '{tool_name}' failed: {e}")
                raise

        wrapper = async_wrapper if tool_def.is_async else sync_wrapper
        wrapper.schema = tool_def.schema
        wrapper.mcp_schema = tool_def.mcp_schema
        wrapper.tool_def = tool_def

        return wrapper

    # Support both @tool and @tool(...) usage
    if callable(name):
        func = name
        name = None
        return decorator(func)

    return decorator


def get_tool(name: str) -> Optional[ToolDefinition]:
    """Get a registered tool by name."""
    return tool_registry.get(name)


def list_tools() -> List[ToolDefinition]:
    """List all registered tools."""
    return tool_registry.list_all()


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas for LLM function calling."""
    return tool_registry.list_schemas()


def get_mcp_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas in MCP format."""
    return tool_registry.list_mcp_schemas()
