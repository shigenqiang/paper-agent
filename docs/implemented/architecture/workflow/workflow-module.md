# Workflow 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/workflow/`

## 模块概述

workflow 模块提供工作流引擎（当前为空目录，保留用于未来扩展）：

- **graph/**：图结构定义
- **runners/**：执行器

## 目录结构

```
workflow/
├── __init__.py
├── graph/                    # 图结构（空）
└── runners/                  # 执行器（空）
```

## 状态

当前为空目录，作为 LangGraph 工作流的补充预留。

实际工作流使用 `langgraph_workflow/` 模块。

## 与其他模块关系

```
langgraph_workflow/           # 实际工作流实现
        │
        ▼
    workflow/                 # 预留扩展
```

---

**版本**：v1.0
**更新日期**：2026-05-03