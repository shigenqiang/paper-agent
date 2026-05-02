# unified 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/unified/` + 调研报告
> 现状：CircuitBreaker/HITL/IntentRouter/MasterSupervisor 已实现

---

## 一、模块概述

### 1.1 现有架构

```
unified/
├── master_supervisor.py    # MasterSupervisor 6阶段编排 ✅
├── phase_supervisor.py     # 阶段监督器 ✅
├── circuit_breaker.py      # 熔断保护 ✅
├── intent_router.py        # 意图路由 (11种意图) ✅
├── hitl_manager.py         # Human-in-the-Loop ✅
├── state_model.py         # 状态模型 ✅
├── error_handler.py        # 错误处理 ✅
├── translation.py          # 翻译包装器 ✅
├── cache.py               # 结果缓存 ✅
├── monitoring.py          # 指标收集 ✅
├── execution_replay.py    # 执行回放 ✅
└── multi-agent.py         # 多Agent协作 ✅
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **MasterSupervisor** | 6阶段顺序执行 | A2A 协议 + 并行阶段 |
| **IntentRouter** | 2步路由 | 三级级联混合路由 |
| **CircuitBreaker** | 基础熔断 | 多级熔断 + 指标监控 |
| **HITLManager** | 5个中断点 | 可配置中断 + Diff审批 |
| **MultiAgent** | 直接调用 | A2A 协议通信 |

---

## 二、任务清单

### 2.1 MasterSupervisor A2A 升级（P0）

**目标**：通过 A2A 协议实现 Agent 间标准化通信

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| AgentCard 定义 | P0 | 各 Agent 能力描述 | `src/agents_v2/unified/agent_card.py` |
| A2A Client 集成 | P0 | 任务发送/订阅 | `src/agents_v2/unified/a2a_client.py` |
| A2A Server 集成 | P0 | 任务接收处理 | `src/agents_v2/unified/a2a_server.py` |
| 任务生命周期 | P1 | tasks/sendSubscribe | `src/agents_v2/unified/task_lifecycle.py` |

### 2.2 CircuitBreaker 增强（P1）

**目标**：多级熔断 + 完整指标体系

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 多级熔断器 | P1 | 按 Agent 类型分级 | `src/agents_v2/unified/multi_breaker.py` |
| 熔断指标暴露 | P1 | Prometheus 格式 | `src/agents_v2/unified/breaker_metrics.py` |
| 自动恢复策略 | P2 | 自适应冷却时间 | `src/agents_v2/unified/auto_recovery.py` |

### 2.3 HITL Manager 增强（P1）

**目标**：可配置中断 + Diff 审批视图

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 可配置中断点 | P1 | 中断点配置化 | `src/agents_v2/unified/hitl_config.py` |
| Diff 审批视图 | P1 | 补丁 Accept/Reject | `src/agents_v2/unified/diff_view.py` |
| 审批历史记录 | P2 | 完整审批日志 | `src/agents_v2/unified/approval_history.py` |

### 2.4 IntentRouter 三级级联（P0）

**已在 core 模块中规划，详细见 `core/core模块开发计划.md`**

### 2.5 Multi-Agent 协作增强（P1）

**目标**：增强多 Agent 协作机制

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Agent 角色定义 | P1 | 角色能力映射 | `src/agents_v2/unified/agent_roles.py` |
| 任务分发策略 | P1 | 负载均衡 | `src/agents_v2/unified/task_dispatcher.py` |
| 结果聚合 | P2 | 多 Agent 结果合并 | `src/agents_v2/unified/result_aggregator.py` |

---

## 三、A2A 协议集成详解

### 3.1 AgentCard 定义

```json
{
  "name": "PaperAgent-Searcher",
  "description": "学术论文搜索智能体，支持多数据源检索",
  "url": "http://localhost:8000",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "arxiv_search",
      "name": "arXiv 搜索",
      "description": "在 arXiv 数据库中搜索预印本论文",
      "tags": ["academic", "preprint"]
    }
  ]
}
```

### 3.2 任务路由流程

```
用户请求
  ↓
MasterSupervisor
  ↓ (A2A tasks/sendSubscribe)
Searcher Agent ← → Writer Agent
  ↓ (A2A tasks/sendSubscribe)
Reviewer Agent
  ↓
HITL Manager (中断点)
  ↓
输出到前端
```

---

## 四、实施计划

### Phase 1：A2A 协议基础（2周）

```
Week 1:
  - AgentCard 定义和注册
  - A2A Client 实现

Week 2:
  - A2A Server 实现
  - 任务生命周期管理
```

### Phase 2：Harness 增强（2周）

```
Week 3:
  - 多级 CircuitBreaker
  - 熔断指标暴露

Week 4:
  - HITL 可配置中断点
  - Diff 审批视图
```

### Phase 3：Multi-Agent 增强（1周）

```
Week 5:
  - Agent 角色定义
  - 任务分发策略
  - 结果聚合
```

---

## 五、验收标准

- [ ] AgentCard 可通过 `/.well-known/agent.json` 访问
- [ ] Agent 间可通过 A2A 协议通信
- [ ] 多级 CircuitBreaker 正常工作
- [ ] HITL 中断点可配置
- [ ] Diff 视图支持 Accept/Reject

---

**版本**：v1.0
**规划日期**：2026-05-02
