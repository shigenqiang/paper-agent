# langgraph-workflow 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/langgraph-workflow/langgraph-workflow.md`
> 现状：5条工作流/22个节点/状态管理/边定义 已实现

---

## 一、模块概述

### 1.1 现有架构

```
langgraph_workflow/
├── unified_workflow.py      # 统一工作流 (20,797字节) ✅
├── workflow.py            # 基础工作流 ✅
├── state.py               # PaperAgentState ✅
├── edges.py               # 条件边 ✅
├── runner.py              # 运行入口 ✅
├── nodes/                 # 22个节点
│   ├── router.py         # 路由节点 ✅
│   ├── crawler.py        # 爬虫节点 ✅
│   ├── selector.py       # 筛选节点 ✅
│   ├── outline.py        # 大纲节点 ✅
│   ├── writer.py         # 写作节点 ✅
│   ├── reviewer.py       # 评审节点 ✅
│   ├── evaluator.py      # 评估节点 ✅
│   ├── memory.py         # 记忆节点 ✅
│   └── ...              # 13个更多节点
└── observability/         # 可观测性 ✅
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **工作流** | 5条独立 | 统一编排 + A2A 协议 |
| **Checkpoint** | 基础 | LangGraph SqliteSaver/PostgresSaver |
| **HITL** | 5个中断点 | 可配置 + Diff 审批 |
| **状态管理** | 内存 | 持久化 + 恢复 |

---

## 二、任务清单

### 2.1 工作流统一编排（P0）

**目标**：A2A 协议集成

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| A2A 任务分发 | P0 | Agent 间任务路由 | `src/agents_v2/langgraph_workflow/a2a_dispatcher.py` |
| 流式状态更新 | P0 | SSE 推送 | `src/agents_v2/langgraph_workflow/streaming_state.py` |
| 工作流版本管理 | P1 | 版本控制 | `src/agents_v2/langgraph_workflow/versioning.py` |

### 2.2 Checkpoint 增强（P1）

**目标**：持久化检查点

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| SqliteSaver | P1 | SQLite 持久化 | `src/agents_v2/langgraph_workflow/checkpoint_sqlite.py` |
| PostgresSaver | P2 | PG 持久化 | `src/agents_v2/langgraph_workflow/checkpoint_pg.py` |
| 时间旅行调试 | P2 | 状态回退 | `src/agents_v2/langgraph_workflow/time_travel.py` |

### 2.3 HITL 增强（P1）

**目标**：可配置 + Diff 审批

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 可配置中断点 | P1 | 中断点配置化 | `src/agents_v2/langgraph_workflow/hitl_config.py` |
| Diff 审批 | P1 | 补丁视图 | `src/agents_v2/langgraph_workflow/diff_view.py` |
| 审批历史 | P2 | 记录回放 | `src/agents_v2/langgraph_workflow/approval_history.py` |

---

## 三、实施计划

```
Week 1:
  - A2A 任务分发实现
  - 流式状态更新

Week 2:
  - Checkpoint 持久化
  - 可配置中断点

Week 3:
  - Diff 审批视图
  - 时间旅行调试
```

---

## 四、验收标准

- [ ] A2A 协议 Agent 间通信正常
- [ ] Checkpoint 持久化正常
- [ ] 中断点可配置
- [ ] Diff 视图支持 Accept/Reject

---

**版本**：v1.0
**规划日期**：2026-05-02
