# Orchestration 层

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/orchestration/`

## 模块概述

orchestration 模块是编排逻辑的兼容层，从 `unified/` 导出核心组件：

- **MasterSupervisor**：全局协调器
- **PhaseSupervisor**：阶段协调器
- **IntentRouter**：意图路由
- **状态模型**：PaperState/PhaseStatus 等

## 目录结构

```
orchestration/
└── __init__.py              # 兼容层，从 unified 导出
    import warnings
    warnings.warn("src.agents_v2.orchestration 是新的模块路径...")
    from src.agents_v2.unified import (
        MasterSupervisor,
        PhaseSupervisor,
        IntentRouter,
        IntentType,
        PaperState,
        PhaseStatus,
        ...
    )
```

## 核心组件

### MasterSupervisor

全局协调器，负责：
- 阶段顺序编排
- Agent 任务分发
- 异常处理与恢复

### PhaseSupervisor

阶段协调器，负责：
- 单个阶段的执行控制
- 阶段内 Agent 协调
- 阶段检查点管理

### IntentRouter

意图路由，识别 11 种用户意图：
- paper_search：论文搜索
- literature_review：文献综述
- outline_generation：大纲生成
- writing：写作
- revision：修改
- qa：问答
- report：报告生成
- 其他...

### 状态模型

```python
class PaperState(BaseModel):
    paper_id: str
    title: str | None
    outline: dict | None
    content: dict
    status: PhaseStatus

class PhaseStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

## 与其他模块关系

```
server/api_server.py
        │
        ▼
    orchestration/
        │
        ├─► unified/MasterSupervisor  # 核心编排
        ├─► unified/PhaseSupervisor    # 阶段协调
        └─► unified/IntentRouter       # 意图路由
                │
                ▼
            agents/                    # Agent 执行
```

---

**版本**：v1.0
**更新日期**：2026-05-03