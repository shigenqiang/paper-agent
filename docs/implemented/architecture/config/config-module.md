# Config 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/config/`

## 模块概述

config 模块提供配置管理：

- **__init__.py**：配置模型与加载

## 目录结构

```
config/
└── __init__.py               # 配置管理 (17KB)
```

## 核心组件

### 配置模型

```python
class LLMConfig(BaseModel):
    model: str
    temperature: float
    max_tokens: int
    timeout: int

class AgentConfig(BaseModel):
    name: str
    llm: LLMConfig
    capabilities: list[str]
    tools: list[str]

class SystemConfig(BaseModel):
    agents: dict[str, AgentConfig]
    memory: MemoryConfig
    search: SearchConfig
    evaluation: EvalConfig
```

### 配置加载

```python
def load_config(path: str) -> SystemConfig
def save_config(config: SystemConfig, path: str)
```

## 与其他模块关系

```
config/
        │
        ▼
    agents/BaseAgent        # Agent 配置
    memory/                  # 记忆配置
    search/                  # 搜索配置
    unified/                 # 编排配置
```

---

**版本**：v1.0
**更新日期**：2026-05-03