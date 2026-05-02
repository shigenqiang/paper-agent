"""
动态工具注册表 - 支持运行时动态注册和卸载工具

功能:
1. 运行时动态注册/注销工具
2. 线程安全的并发访问
3. 基于任务上下文的工具选择
4. 工具变更观察者模式
"""
from src.agents_v2.logging_config import get_logging_logger

import asyncio
import time

from typing import Any, Callable, Dict, List, Optional, Protocol, Set
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class ToolEvent(Enum):
    REGISTER = "register"
    UNREGISTER = "unregister"
    UPDATE = "update"


@dataclass
class ToolObserver:
    """工具变更观察者"""
    callback: Callable[[ToolEvent, Any], None]
    name: str = ""


class DynamicToolRegistry:
    """
    支持运行时动态注册的工具注册表

    特性:
    - 线程安全的并发注册/注销
    - 基于任务上下文的工具筛选
    - 观察者模式通知变更
    - 工具适用性检查

    使用方式:
        registry = DynamicToolRegistry()

        # 注册工具
        await registry.register(ToolSpec(...))

        # 注销工具
        await registry.unregister("tool_name")

        # 根据任务上下文获取工具
        tools = registry.get_for_context({"task_type": "research"})

        # 订阅变更通知
        registry.subscribe(my_observer)
    """

    def __init__(self):
        self._tools: Dict[str, Any] = {}  # tool_name -> ToolSpec
        self._lock = asyncio.Lock()
        self._observers: List[ToolObserver] = []
        self._execution_history: List[Dict] = []
        self._register_time: Dict[str, float] = {}

    async def register(self, tool: Any) -> bool:
        """
        注册工具（异步、线程安全）

        Args:
            tool: 工具规格对象（需要有 name, description, is_applicable 属性）

        Returns:
            是否注册成功（False 表示工具已存在）
        """
        async with self._lock:
            if tool.name in self._tools:
                logger.warning(f"Tool {tool.name} already registered")
                return False

            self._tools[tool.name] = tool
            self._register_time[tool.name] = time.time()
            logger.info(f"Registered tool: {tool.name}")

            await self._notify_observers(ToolEvent.REGISTER, tool)
            return True

    async def unregister(self, tool_name: str) -> bool:
        """
        注销工具（异步、线程安全）

        Args:
            tool_name: 工具名称

        Returns:
            是否注销成功（False 表示工具不存在）
        """
        async with self._lock:
            if tool_name not in self._tools:
                logger.warning(f"Tool {tool_name} not found for unregistration")
                return False

            tool = self._tools.pop(tool_name)
            self._register_time.pop(tool_name, None)
            logger.info(f"Unregistered tool: {tool_name}")

            await self._notify_observers(ToolEvent.UNREGISTER, tool)
            return True

    async def update(self, tool: Any) -> bool:
        """
        更新工具（异步、线程安全）

        Args:
            tool: 更新的工具规格对象

        Returns:
            是否更新成功（False 表示工具不存在）
        """
        async with self._lock:
            if tool.name not in self._tools:
                logger.warning(f"Tool {tool.name} not found for update")
                return False

            self._tools[tool.name] = tool
            logger.info(f"Updated tool: {tool.name}")

            await self._notify_observers(ToolEvent.UPDATE, tool)
            return True

    def get(self, tool_name: str) -> Optional[Any]:
        """
        获取工具

        Args:
            tool_name: 工具名称

        Returns:
            工具规格对象或 None
        """
        return self._tools.get(tool_name)

    def list_all(self) -> List[Any]:
        """
        列出所有已注册的工具

        Returns:
            工具列表
        """
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def get_for_context(self, context: Dict[str, Any]) -> List[Any]:
        """
        根据任务上下文获取适用的工具

        Args:
            context: 任务上下文，包含 task_type, domain 等信息

        Returns:
            适用的工具列表
        """
        applicable = []
        for tool in self._tools.values():
            if self._is_tool_applicable(tool, context):
                applicable.append(tool)
        return applicable

    def search(self, query: str) -> List[Any]:
        """
        搜索工具

        Args:
            query: 搜索关键词（匹配名称或描述）

        Returns:
            匹配的工具列表
        """
        query_lower = query.lower()
        results = []
        for tool in self._tools.values():
            if (query_lower in tool.name.lower() or
                query_lower in getattr(tool, 'description', '').lower()):
                results.append(tool)
        return results

    def list_by_category(self, category: str) -> List[Any]:
        """
        按分类列出工具

        Args:
            category: 工具分类

        Returns:
            该分类下的工具列表
        """
        return [
            tool for tool in self._tools.values()
            if getattr(tool, 'category', '') == category
        ]

    def get_categories(self) -> Set[str]:
        """获取所有工具分类"""
        return {
            getattr(tool, 'category', 'uncategorized')
            for tool in self._tools.values()
        }

    def subscribe(self, callback: Callable[[ToolEvent, Any], None], name: str = "") -> None:
        """
        订阅工具变更事件

        Args:
            callback: 回调函数，签名为 (event: ToolEvent, tool: Any) -> None
            name: 观察者名称（用于取消订阅）
        """
        observer = ToolObserver(callback=callback, name=name)
        self._observers.append(observer)
        logger.debug(f"Observer '{name}' subscribed to tool events")

    def unsubscribe(self, name: str) -> bool:
        """
        取消订阅

        Args:
            name: 观察者名称

        Returns:
            是否成功取消订阅
        """
        for i, observer in enumerate(self._observers):
            if observer.name == name:
                self._observers.pop(i)
                logger.debug(f"Observer '{name}' unsubscribed from tool events")
                return True
        return False

    def _is_tool_applicable(self, tool: Any, context: Dict[str, Any]) -> bool:
        """
        检查工具是否适用于给定上下文

        Args:
            tool: 工具对象
            context: 任务上下文

        Returns:
            是否适用
        """
        # 如果工具有 is_applicable 方法，调用它
        if hasattr(tool, 'is_applicable') and callable(tool.is_applicable):
            try:
                return tool.is_applicable(context)
            except Exception:
                return True  # 出错时默认适用

        # 如果工具有 tags，检查是否匹配上下文
        tags = getattr(tool, 'tags', []) or []
        task_type = context.get('task_type', '')
        domain = context.get('domain', '')

        # 简单匹配：标签包含任务类型或领域
        if task_type and task_type.lower() in [t.lower() for t in tags]:
            return True
        if domain and domain.lower() in [t.lower() for t in tags]:
            return True

        # 默认适用
        return True

    async def _notify_observers(self, event: ToolEvent, tool: Any) -> None:
        """通知所有观察者"""
        for observer in self._observers:
            try:
                if asyncio.iscoroutinefunction(observer.callback):
                    await observer.callback(event, tool)
                else:
                    observer.callback(event, tool)
            except Exception as e:
                logger.error(f"Observer callback failed: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_calls = len(self._execution_history)
        return {
            "total_tools": len(self._tools),
            "categories": list(self.get_categories()),
            "observers": len(self._observers),
            "total_calls": total_calls,
        }

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行工具（便捷方法）

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            执行结果字典
        """
        tool = self.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool not found: {tool_name}"}

        start_time = time.time()
        try:
            handler = getattr(tool, 'handler', None)
            if not handler:
                return {"success": False, "error": f"Tool {tool_name} has no handler"}

            result = await handler(**arguments)
            return {
                "success": True,
                "result": result,
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }


# 全局动态工具注册表实例
_dynamic_registry: Optional[DynamicToolRegistry] = None


def get_dynamic_tool_registry() -> DynamicToolRegistry:
    """
    获取全局动态工具注册表

    Returns:
        全局 DynamicToolRegistry 实例
    """
    global _dynamic_registry
    if _dynamic_registry is None:
        _dynamic_registry = DynamicToolRegistry()
    return _dynamic_registry
