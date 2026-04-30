# 发现：工具注册静态化问题

**日期**：2026-04-30
**类型**：工程问题

---

## 1. 问题描述

工具注册在 Agent 初始化时完成，无法在运行时动态添加或移除工具。

---

## 2. 代码证据

```python
# registry.py
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._initialized = False

    async def initialize(self):
        """在 Agent 初始化时加载所有工具"""
        await self._load_buildin_tools()
        await self._load_custom_tools()
        self._initialized = True
```

---

## 3. 问题影响

1. **缺乏灵活性**：无法根据任务动态调整工具集
2. **资源浪费**：所有工具无论是否需要都加载
3. **扩展困难**：新工具需要重启服务
4. **测试复杂**：难以模拟动态工具场景

---

## 4. 竞品方案

### CrewAI 动态注册

```python
@agent.tool("Search")
def search_tool(query: str):
    return search(query)

# 运行时添加
agent.add_tool(custom_tool)
```

### LangGraph ToolNode

```python
tools = [search_tool, calculate_tool]
model = llm.bind_tools(tools)
```

---

## 5. 改进方案

```python
# tools/dynamic_registry.py
class DynamicToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._lock = asyncio.Lock()

    async def register(self, tool: ToolSpec):
        async with self._lock:
            self._tools[tool.name] = tool

    async def unregister(self, tool_name: str):
        async with self._lock:
            self._tools.pop(tool_name, None)

    def get_for_task(self, task_context: dict) -> list[ToolSpec]:
        return [t for t in self._tools.values()
                if self._is_applicable(t, task_context)]
```

---

## 6. 参考

- [CrewAI 工具系统](https://docs.crewai.com/)
- [LangGraph 工具绑定](https://langchain-ai.github.io/langgraph/)
