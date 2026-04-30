# 改进建议：图执行引擎

**日期**：2026-04-30
**优先级**：高

---

## 1. 背景

本项目当前采用 Supervisor 模式，存在以下问题：
- if-else 硬编码路由
- 难以可视化
- 扩展性差

建议引入图执行引擎，参考 LangGraph 设计。

---

## 2. 设计方案

### 2.1 核心类设计

```python
# workflow/graph_engine.py
from typing import TypedDict, Callable, Dict, List, Optional, Any
from enum import Enum

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class GraphEngine:
    """图执行引擎"""

    def __init__(self, state_class: type):
        self.state_class = state_class
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, List[str]] = {}
        self.conditional_edges: Dict[str, Callable] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, handler: Callable) -> "GraphEngine":
        """添加节点"""
        self.nodes[name] = handler
        return self

    def add_edge(self, from_node: str, to_node: str) -> "GraphEngine":
        """添加普通边"""
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append(to_node)
        return self

    def add_conditional_edge(
        self,
        from_node: str,
        to_nodes: List[str],
        condition: Callable
    ) -> "GraphEngine":
        """添加条件边"""
        self.conditional_edges[from_node] = (to_nodes, condition)
        return self

    def set_entry_point(self, node: str) -> "GraphEngine":
        """设置入口点"""
        self.entry_point = node
        return self

    async def execute(self, initial_state: dict) -> dict:
        """执行图"""
        state = initial_state.copy()

        if not self.entry_point:
            raise ValueError("Entry point not set")

        current_node = self.entry_point
        while current_node:
            # 更新状态
            state["current_node"] = current_node

            # 执行节点
            try:
                result = await self.nodes[current_node](state)
                if isinstance(result, dict):
                    state.update(result)
            except Exception as e:
                state["error"] = str(e)
                break

            # 确定下一个节点
            if current_node in self.conditional_edges:
                to_nodes, condition = self.conditional_edges[current_node]
                current_node = condition(state, to_nodes)
            elif current_node in self.edges:
                current_node = self.edges[current_node][0]
            else:
                current_node = None

        return state
```

### 2.2 使用示例

```python
# 定义状态
class AgentState(TypedDict):
    task_id: str
    current_phase: str
    quality_score: float
    artifacts: dict

# 定义节点
async def diagnostic_node(state: AgentState) -> AgentState:
    result = await diagnostic_agent.execute(state["task_id"])
    return {"quality_score": result.score, "artifacts": {"diagnostic": result.output}}

async def topic_node(state: AgentState) -> AgentState:
    result = await topic_agent.execute(state["task_id"])
    return {"quality_score": result.score, "artifacts": {"topic": result.output}}

# 条件函数
def quality_check(state: AgentState, to_nodes: List[str]) -> str:
    if state["quality_score"] >= 0.8:
        return to_nodes[1]  # 继续下一阶段
    return to_nodes[0]  # 重新执行当前阶段

# 构建图
graph = GraphEngine(AgentState)
graph.add_node("diagnostic", diagnostic_node)
graph.add_node("topic", topic_node)
graph.add_edge("diagnostic", "topic")
graph.add_conditional_edge(
    "topic",
    ["topic", "finish"],  # [retry, finish]
    quality_check
)
graph.set_entry_point("diagnostic")

# 执行
result = await graph.execute({"task_id": "task_123", "quality_score": 0.0, "artifacts": {}})
```

---

## 3. 迁移路径

### Phase 1：并行运行
- 保持现有 Supervisor 模式
- 新增 GraphEngine，仅用于新功能

### Phase 2：渐进迁移
- 将 PhaseSupervisor 逐步改造为节点
- 保留核心逻辑，替换路由机制

### Phase 3：完全迁移
- 移除 Supervisor 模式
- GraphEngine 作为唯一执行引擎

---

## 4. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 迁移复杂 | Phase 1 并行运行，充分测试 |
| 性能下降 | GraphEngine 轻量级，无明显开销 |
| 团队学习成本 | 参照 LangGraph 文档，提供示例 |

---

## 5. 参考

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [StateGraph 源码](https://github.com/langchain-ai/langgraph)
