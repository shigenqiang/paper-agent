# orchestration 模块开发计划

> 规划日期：2026-05-03
> 基于：`docs/implemented/architecture/orchestration/` + 未来框架设计 v2.1
> 现状：兼容层已实现（从 unified 导出）

---

## 一、模块概述

### 1.1 现有架构

```
orchestration/
└── __init__.py    # 兼容层，从 unified 导出 ✅
    - MasterSupervisor
    - PhaseSupervisor
    - IntentRouter
    - 状态模型
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **MasterSupervisor** | 顺序6阶段 | A2A 并行编排 |
| **PhaseSupervisor** | 基础协调 | 自适应资源分配 |
| **IntentRouter** | 2步路由 | 三级级联混合路由 |

---

## 二、任务清单

### 2.1 MasterSupervisor A2A 升级（P0）

**目标**：A2A 协议编排

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| A2A 任务分发 | P0 | Agent 间任务调度 | `src/agents_v2/orchestration/a2a_dispatcher.py` |
| 并行阶段执行 | P1 | 阶段并行化 | `src/agents_v2/orchestration/parallel_phase.py` |
| 阶段依赖管理 | P1 | DAG 依赖解析 | `src/agents_v2/orchestration/phase_deps.py` |
| 动态负载均衡 | P2 | Agent 负载分配 | `src/agents_v2/orchestration/load_balancer.py` |

### 2.2 PhaseSupervisor 增强（P1）

**目标**：自适应协调

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 自适应检查点 | P1 | 动态保存 | `src/agents_v2/orchestration/adaptive_checkpoint.py` |
| 阶段回滚 | P1 | 失败恢复 | `src/agents_v2/orchestration/phase_rollback.py` |
| 性能监控 | P2 | 阶段耗时追踪 | `src/agents_v2/orchestration/phase_metrics.py` |
| 资源调度 | P2 | Agent 资源分配 | `src/agents_v2/orchestration/resource_scheduler.py` |

### 2.3 IntentRouter 三级级联（P0）

**目标**：低成本高准确率

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Layer 1 关键词 | P0 | <1ms 快速匹配 | `src/agents_v2/orchestration/keyword_router.py` |
| Layer 2 语义向量 | P0 | 语义路由 | `src/agents_v2/orchestration/semantic_router.py` |
| Layer 3 LLM | P0 | 深度分类 | `src/agents_v2/orchestration/llm_classifier.py` |
| 置信度校准 | P1 | 置信度校准 | `src/agents_v2/orchestration/confidence_calibrator.py` |

---

## 三、A2A 编排流程

```
用户请求
  ↓
MasterSupervisor
  ↓
┌─────────────────────────────────────┐
│  PhaseSupervisor (并行)              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │ Phase 1 │ │ Phase 2 │ │ Phase 3 │ │
│  │ (A2A)   │ │ (A2A)   │ │ (A2A)   │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ │
│       └──────────┼──────────┘       │
└──────────────────┼──────────────────┘
                   ↓
              输出/评估
```

---

## 四、实施计划

### Phase 1：三级级联路由（2周）

```
Week 1:
  - Layer 1 关键词路由
  - Layer 2 语义向量路由

Week 2:
  - Layer 3 LLM 分类
  - 置信度校准
```

### Phase 2：A2A 编排（2周）

```
Week 3:
  - A2A 任务分发
  - 并行阶段执行

Week 4:
  - 阶段依赖管理
  - 动态负载均衡
```

### Phase 3：PhaseSupervisor 增强（1周）

```
Week 5:
  - 自适应检查点
  - 阶段回滚
  - 性能监控
```

---

## 五、验收标准

- [ ] 三级级联路由延迟 < 50ms
- [ ] A2A 任务分发正常
- [ ] 并行阶段执行稳定
- [ ] 阶段失败可回滚
- [ ] 置信度校准准确

---

**版本**：v1.0
**规划日期**：2026-05-03