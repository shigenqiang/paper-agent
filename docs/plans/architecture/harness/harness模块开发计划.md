# harness 模块开发计划

> 规划日期：2026-05-03
> 基于：`docs/implemented/architecture/harness/` + 未来框架设计 v2.1
> 现状：兼容层已实现（从 unified 导出）

---

## 一、模块概述

### 1.1 现有架构

```
harness/
└── __init__.py    # 兼容层，从 unified 导出 ✅
    - CircuitBreaker
    - HITLManager
    - ExecutionReplay
    - ErrorHandler
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **CircuitBreaker** | 基础熔断 | 多级熔断 + 指标监控 |
| **HITLManager** | 5个中断点 | 可配置 + Diff 审批 |
| **Evaluator** | 基础评分 | 5维度 + LLM-as-Judge |
| **AuditTrail** | 基础记录 | 完整溯源 + 基准测试 |

---

## 二、任务清单

### 2.1 CircuitBreaker 增强（P1）

**目标**：多级熔断 + Prometheus 监控

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 多级熔断器 | P1 | 按 Agent 类型分级 | `src/agents_v2/harness/multi_breaker.py` |
| 熔断指标 | P1 | Prometheus 格式 | `src/agents_v2/harness/breaker_metrics.py` |
| 自动恢复 | P2 | 自适应冷却 | `src/agents_v2/harness/auto_recovery.py` |
| 熔断可视化 | P2 | 状态面板 | `src/agents_v2/harness/breaker_dashboard.py` |

### 2.2 HITLManager 增强（P1）

**目标**：可配置中断 + Diff 审批

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 可配置中断点 | P1 | 中断点配置化 | `src/agents_v2/harness/hitl_config.py` |
| Diff 审批视图 | P1 | 补丁 Accept/Reject | `src/agents_v2/harness/diff_view.py` |
| 审批历史 | P2 | 完整审批日志 | `src/agents_v2/harness/approval_history.py` |
| 批量审批 | P2 | 批量操作支持 | `src/agents_v2/harness/batch_approval.py` |

### 2.3 Evaluator 完善（P0）

**目标**：5维度质量评估

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 学术规范性 | P0 | 引用格式/术语/结构 | `src/agents_v2/harness/eval_academic.py` |
| 研究质量 | P0 | 创新性/严谨性/贡献度 | `src/agents_v2/harness/eval_research.py` |
| 内容完整性 | P1 | 文献覆盖/论证完整 | `src/agents_v2/harness/eval_completeness.py` |
| 表达质量 | P1 | 清晰度/连贯性/语法 | `src/agents_v2/harness/eval_expression.py` |
| 逻辑严谨性 | P1 | 因果推理/论据质量 | `src/agents_v2/harness/eval_logic.py` |
| LLM-as-Judge | P1 | 结构化评分 | `src/agents_v2/harness/llm_judge.py` |

### 2.4 AuditTrail 增强（P2）

**目标**：完整溯源 + 基准测试

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| AgentBench 接口 | P2 | 8环境评估 | `src/agents_v2/harness/agent_bench.py` |
| PaperBench 接口 | P2 | 论文复现评估 | `src/agents_v2/harness/paper_bench.py` |
| SWE-bench 接口 | P2 | 代码任务评估 | `src/agents_v2/harness/swe_bench.py` |
| 审计查询 | P2 | 历史追溯 | `src/agents_v2/harness/audit_query.py` |

---

## 三、质量评估维度

| 维度 | 权重 | 核心指标 |
|------|------|---------|
| **学术规范性** | 20% | 引用格式、术语使用、结构规范 |
| **研究质量** | 25% | 创新性、严谨性、贡献度 |
| **内容完整性** | 20% | 文献覆盖、论证完整、局限承认 |
| **表达质量** | 15% | 清晰度、连贯性、语法风格 |
| **逻辑严谨性** | 20% | 因果推理、论据质量、结论推导 |

---

## 四、实施计划

### Phase 1：Evaluator 完善（2周）

```
Week 1:
  - 学术规范性评估
  - 研究质量评估

Week 2:
  - 内容完整性评估
  - 表达质量评估
  - 逻辑严谨性评估
```

### Phase 2：Harness 增强（2周）

```
Week 3:
  - 多级 CircuitBreaker
  - 熔断指标

Week 4:
  - HITL 可配置中断点
  - Diff 审批视图
```

### Phase 3：AuditTrail（1周）

```
Week 5:
  - AgentBench/PaperBench 接口
  - 审计查询
```

---

## 五、验收标准

- [ ] 5维度 QualityEvaluator 完整
- [ ] LLM-as-Judge 评分稳定
- [ ] 多级 CircuitBreaker 正常工作
- [ ] HITL 中断点可配置
- [ ] Diff 视图支持 Accept/Reject
- [ ] AuditBench 基准可调用

---

**版本**：v1.0
**规划日期**：2026-05-03