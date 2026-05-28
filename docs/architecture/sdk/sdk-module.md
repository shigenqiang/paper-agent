# SDK 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/sdk/`

## 模块概述

sdk 模块提供对外 SDK 接口：

- **agent.py**：Agent SDK
- **context.py**：上下文管理
- **tool.py**：工具定义

## 目录结构

```
sdk/
├── __init__.py
├── agent.py                  # Agent SDK (21KB)
├── context.py                # 上下文管理 (7KB)
└── tool.py                   # 工具定义 (9KB)
```

## 核心组件

### Agent SDK

```python
class AgentSDK:
    def __init__(self, config: SDKConfig)
    async def create_agent(self, name: str, capabilities: list[str]) -> Agent
    async def execute(self, agent_id: str, input: str) -> str
    async def get_status(self, agent_id: str) -> AgentStatus
```

### Context

上下文管理器：
- 会话上下文
- 请求上下文
- 临时状态

### Tool

工具定义：
```python
class Tool(BaseModel):
    name: str
    description: str
    parameters: dict
    handler: Callable
```

## 与其他模块关系

```
外部调用
        │
        ▼
    sdk/AgentSDK
        │
        ├─► agents/             # Agent 执行
        ├─► unified/           # 编排逻辑
        └─► memory/             # 记忆系统
```

---

**版本**：v1.0
**更新日期**：2026-05-03