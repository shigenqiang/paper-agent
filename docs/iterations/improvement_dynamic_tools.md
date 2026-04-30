# 改进建议：动态工具注册

**日期**：2026-04-30
**优先级**：中

---

## 1. 背景

当前工具系统在 Agent 初始化时静态加载，无法满足运行时动态工具管理需求。

---

## 2. 设计方案

### 2.1 核心类

```python
# tools/dynamic_registry.py
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import asyncio

@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    tags: List[str] = field(default_factory=list)

    def is_applicable(self, context: dict) -> bool:
        """检查工具是否适用于给定上下文"""
        return True

class DynamicToolRegistry:
    """支持运行时动态注册的工具注册表"""

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._lock = asyncio.Lock()
        self._observers: List[Callable] = []

    async def register(self, tool: ToolSpec) -> bool:
        """注册工具"""
        async with self._lock:
            if tool.name in self._tools:
                return False
            self._tools[tool.name] = tool
            await self._notify_observers("register", tool)
            return True

    async def unregister(self, tool_name: str) -> bool:
        """注销工具"""
        async with self._lock:
            if tool_name not in self._tools:
                return False
            tool = self._tools.pop(tool_name)
            await self._notify_observers("unregister", tool)
            return True

    async def update(self, tool: ToolSpec) -> bool:
        """更新工具"""
        async with self._lock:
            if tool.name not in self._tools:
                return False
            self._tools[tool.name] = tool
            await self._notify_observers("update", tool)
            return True

    def get(self, tool_name: str) -> Optional[ToolSpec]:
        """获取工具"""
        return self._tools.get(tool_name)

    def list_all(self) -> List[ToolSpec]:
        """列出所有工具"""
        return list(self._tools.values())

    def get_for_context(self, context: dict) -> List[ToolSpec]:
        """根据上下文获取适用工具"""
        return [
            tool for tool in self._tools.values()
            if tool.is_applicable(context)
        ]

    def search(self, query: str) -> List[ToolSpec]:
        """搜索工具"""
        query_lower = query.lower()
        return [
            tool for tool in self._tools.values()
            if query_lower in tool.name.lower()
            or query_lower in tool.description.lower()
        ]

    async def _notify_observers(self, event: str, tool: ToolSpec):
        """通知观察者"""
        for observer in self._observers:
            try:
                await observer(event, tool)
            except Exception:
                pass

    def subscribe(self, observer: Callable):
        """订阅工具变更事件"""
        self._observers.append(observer)
```

### 2.2 任务上下文工具选择

```python
# tools/task_context_selector.py
class TaskContextToolSelector:
    """基于任务上下文动态选择工具"""

    def __init__(self, registry: DynamicToolRegistry):
        self.registry = registry

    async def select_tools(
        self,
        task: dict,
        max_tools: int = 5
    ) -> List[ToolSpec]:
        """为任务选择最合适的工具"""
        context = self._build_context(task)
        available = self.registry.get_for_context(context)

        # 按相关性排序
        scored = [
            (tool, self._score_tool(tool, context))
            for tool in available
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [tool for tool, _ in scored[:max_tools]]

    def _build_context(self, task: dict) -> dict:
        """构建任务上下文"""
        return {
            "task_type": task.get("type"),
            "domain": task.get("domain"),
            "complexity": task.get("complexity", "medium"),
        }

    def _score_tool(self, tool: ToolSpec, context: dict) -> float:
        """计算工具相关性分数"""
        score = 0.5

        if context.get("task_type") in tool.tags:
            score += 0.3

        return score
```

---

## 3. 使用示例

```python
# 初始化
registry = DynamicToolRegistry()

# 静态注册
await registry.register(ToolSpec(
    name="search",
    description="Search for information",
    parameters={"query": {"type": "string"}},
    handler=search_handler,
    tags=["research", "information"]
))

# 运行时动态注册
async def register_custom_tool():
    tool = ToolSpec(
        name="custom_analysis",
        description="Custom analysis tool",
        parameters={},
        handler=custom_handler,
        tags=["custom"]
    )
    await registry.register(tool)

# 任务时选择工具
selector = TaskContextToolSelector(registry)
selected = await selector.select_tools({
    "type": "research",
    "domain": "academic"
})
```

---

## 4. 迁移计划

### Phase 1：并行运行
- 创建 `DynamicToolRegistry` 与现有 `ToolRegistry` 并行
- 新功能使用新类

### Phase 2：渐进迁移
- 将现有工具逐步迁移到新注册表
- 保持接口兼容

### Phase 3：完全迁移
- 移除旧的静态注册表
- 统一使用动态注册

---

## 5. 参考

- [CrewAI 工具系统](https://docs.crewai.com/)
- [LangGraph 工具绑定](https://langchain-ai.github.io/langgraph/)
