# Agents 框架

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/agents/`

## 模块概述

agents 模块是 Agent 核心执行框架，提供：
- **BaseAgent**：统一基类，定义 Agent 标准执行流程
- **ReActLoop**：ReAct 执行器，支持 Thought→Action→Observation 循环
- **角色化 Agent**：Searcher/Writer/Reviewer/Polisher 等专业角色

## 目录结构

```
agents/
├── __init__.py
├── base/
│   ├── __init__.py
│   └── base_agent.py       # BaseAgent 基类 (361行)
│       - AgentInput        # 输入模型
│       - AgentOutput       # 输出模型
│       - AgentCapability   # 能力描述
│       - LLMConfig         # LLM 配置
│       - Tool              # 工具定义
├── loops/
│   ├── __init__.py
│   └── react_loop.py      # ReActExecutor (546行)
│       - Thought           # 思考步骤
│       - Action           # 动作步骤
│       - Observation       # 观察步骤
└── roles/
    └── __init__.py         # 角色化 Agent
```

## 核心组件

### BaseAgent

BaseAgent 是所有 Agent 的基类，提供统一的执行框架：

```python
class BaseAgent:
    def __init__(
        self,
        name: str,
        llm_config: LLMConfig,
        capabilities: list[AgentCapability],
        tools: list[Tool]
    )
```

**核心方法**：
- `execute(input: AgentInput) -> AgentOutput`：执行 Agent
- `_init_llm()`：初始化 LLM
- `_build_messages()`：构建消息
- `_llm_call()`：调用 LLM
- `_parse_response()`：解析响应

### AgentInput / AgentOutput

```python
class AgentInput(BaseModel):
    user_message: str
    context: dict = {}
    session_id: str | None = None

class AgentOutput(BaseModel):
    response: str
    tool_calls: list[ToolCall] = []
    metadata: dict = {}
```

### LLMConfig

```python
class LLMConfig(BaseModel):
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
```

### ReActExecutor

ReAct Loop 执行器，支持多步推理：

```
Thought → Action → Observation → Thought → ...
```

**步骤类型**：
- **Thought**：推理下一步行动
- **Action**：执行工具调用
- **Observation**：获取执行结果

## 角色化 Agent

| Agent | 职责 | 触发阶段 |
|-------|------|----------|
| Searcher | 文献检索 | 选题、综述 |
| Writer | 章节撰写 | 写作阶段 |
| Reviewer | 结构化审稿 | 每章后 |
| Polisher | 语言润色 | 润色阶段 |

## 执行流程

```
Agent.execute(input)
    │
    ├─► _init_llm()
    │       └─ 初始化 LLM 配置
    │
    ├─► _build_messages()
    │       └─ 构建 system/user 消息
    │
    ├─► _llm_call()
    │       └─ 调用 LLM API
    │
    ├─► _clean_thinking_blocks()
    │       └─ 清洗 <thinking> 标签
    │
    └─► _parse_response()
            └─ 解析 LLM 输出
```

## 与其他模块关系

```
unified/IntentRouter
        │
        ▼
    BaseAgent.execute()
        │
        ├─► memory/          # 记忆读写
        ├─► tools/           # 工具调用
        ├─► search/          # 文献检索
        └─► evaluation/       # 质量评估
```

---

**版本**：v1.0
**更新日期**：2026-05-03