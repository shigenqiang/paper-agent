"""
工具注册表 - 统一管理工具的注册、验证和执行

ToolRegistry: 全局工具注册表
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional
from .tool_spec import ToolSpec, ValidationResult, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表

    统一管理所有工具的注册、验证和执行

    使用方式:
        registry = ToolRegistry()

        # 注册工具
        registry.register(ToolSpec(
            name="search_papers",
            description="搜索学术论文",
            parameters=[...],
            handler=search_handler
        ))

        # 验证调用
        result = registry.validate_call("search_papers", {"query": "deep learning"})
        if not result.success:
            return result.error

        # 执行工具
        result = await registry.execute("search_papers", {"query": "deep learning"})
    """

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._execution_history: List[Dict] = []

    def register(self, spec: ToolSpec) -> None:
        """
        注册工具

        Args:
            spec: 工具规格定义

        Raises:
            ValueError: 如果工具名称已存在
        """
        if spec.name in self._tools:
            logger.warning(f"Tool {spec.name} already registered, overwriting")

        self._tools[spec.name] = spec
        logger.info(f"Registered tool: {spec.name} (category={spec.category})")

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "general"
    ) -> None:
        """
        直接注册函数作为工具

        Args:
            func: 要注册的函数
            name: 工具名称（默认使用函数名）
            description: 工具描述（默认使用函数docstring）
            category: 工具分类
        """
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "No description")

        # 从函数签名推断参数（简化实现）
        import inspect
        sig = inspect.signature(func)
        params = []
        for pname, param in sig.parameters.items():
            if pname in ('kwargs', 'args'):
                continue
            params.append({
                "name": pname,
                "type": "string",  # 简化处理
                "required": param.default is inspect.Parameter.empty,
                "description": f"Parameter {pname}"
            })

        spec = ToolSpec(
            name=tool_name,
            description=tool_desc,
            parameters=params,
            handler=func,
            category=category
        )
        self.register(spec)

    def get(self, name: str) -> Optional[ToolSpec]:
        """获取工具规格"""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """
        列出已注册的工具

        Args:
            category: 可选，按分类过滤

        Returns:
            工具名称列表
        """
        if category:
            return [name for name, spec in self._tools.items() if spec.category == category]
        return list(self._tools.keys())

    def list_categories(self) -> List[str]:
        """列出所有工具分类"""
        return list(set(spec.category for spec in self._tools.values()))

    def validate_call(self, name: str, arguments: Dict) -> ValidationResult:
        """
        验证工具调用参数

        Args:
            name: 工具名称
            arguments: 调用参数

        Returns:
            验证结果
        """
        spec = self._tools.get(name)
        if not spec:
            return ValidationResult(success=False, error=f"Tool not found: {name}")

        return spec.validate(arguments)

    async def execute(self, name: str, arguments: Dict) -> ToolResult:
        """
        执行工具调用

        Args:
            name: 工具名称
            arguments: 调用参数

        Returns:
            工具执行结果
        """
        start_time = time.time()
        spec = self._tools.get(name)

        if not spec:
            return ToolResult(
                success=False,
                error=f"Tool not found: {name}",
                execution_time=time.time() - start_time
            )

        # 验证参数
        validation = spec.validate(arguments)
        if not validation.success:
            return ToolResult(
                success=False,
                error=validation.error,
                execution_time=time.time() - start_time
            )

        try:
            # 执行处理函数
            result = await spec.handler(**validation.validated_params)

            # 记录执行历史
            self._execution_history.append({
                "tool_name": name,
                "arguments": validation.validated_params,
                "success": True,
                "execution_time": time.time() - start_time
            })

            return ToolResult(
                success=True,
                result=result,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Tool execution failed: {name}, error: {e}")

            # 记录失败历史
            self._execution_history.append({
                "tool_name": name,
                "arguments": validation.validated_params,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            })

            return ToolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def execute_sync(self, name: str, arguments: Dict) -> ToolResult:
        """
        同步执行工具调用（用于非async工具）

        Args:
            name: 工具名称
            arguments: 调用参数

        Returns:
            工具执行结果
        """
        start_time = time.time()
        spec = self._tools.get(name)

        if not spec:
            return ToolResult(
                success=False,
                error=f"Tool not found: {name}",
                execution_time=time.time() - start_time
            )

        # 验证参数
        validation = spec.validate(arguments)
        if not validation.success:
            return ToolResult(
                success=False,
                error=validation.error,
                execution_time=time.time() - start_time
            )

        try:
            # 执行处理函数
            result = spec.handler(**validation.validated_params)

            # 如果是协程，等待它
            import asyncio
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)

            return ToolResult(
                success=True,
                result=result,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Tool execution failed: {name}, error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def get_schemas(self) -> List[Dict]:
        """
        生成工具Schema列表供LLM使用

        Returns:
            OpenAI格式的工具Schema列表
        """
        schemas = []
        for name, spec in self._tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.to_openai_schema()
                }
            })
        return schemas

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取工具使用统计

        Returns:
            统计信息字典
        """
        total_calls = len(self._execution_history)
        successful_calls = sum(1 for h in self._execution_history if h["success"])
        failed_calls = total_calls - successful_calls

        tool_stats = {}
        for history in self._execution_history:
            tool_name = history["tool_name"]
            if tool_name not in tool_stats:
                tool_stats[tool_name] = {"calls": 0, "successes": 0, "failures": 0}

            tool_stats[tool_name]["calls"] += 1
            if history["success"]:
                tool_stats[tool_name]["successes"] += 1
            else:
                tool_stats[tool_name]["failures"] += 1

        avg_execution_time = 0.0
        if total_calls > 0:
            avg_execution_time = sum(h["execution_time"] for h in self._execution_history) / total_calls

        return {
            "total_tools": len(self._tools),
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "average_execution_time": avg_execution_time,
            "tool_statistics": tool_stats
        }

    def clear_history(self) -> None:
        """清除执行历史"""
        self._execution_history.clear()


# 全局工具注册表实例
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    获取全局工具注册表

    Returns:
        全局ToolRegistry实例
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def register_builtin_tools() -> None:
    """注册内置工具到全局注册表"""
    from .buildin_tools import register_all

    registry = get_tool_registry()
    register_all(registry)
