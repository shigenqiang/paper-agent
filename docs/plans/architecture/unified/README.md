# unified 模块开发计划

> 状态：已规划
> 与未来框架设计 v2.1 对齐

## 模块定位

unified 模块是 Agent 编排层核心，提供：
- MasterSupervisor 6阶段编排
- CircuitBreaker 熔断保护
- HITL Manager 人机协作
- IntentRouter 意图路由
- Multi-Agent 协作

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| A2A 协议 | AgentCard + A2A Client/Server |
| 多级熔断器 | MultiCircuitBreaker + 指标暴露 |
| HITL 增强 | 可配置中断点 + Diff 审批 |
| 质量保障 Harness | Evaluator + CircuitBreaker + HITL + AuditTrail |

## 详细计划

见 `unified模块开发计划.md`

## 进度追踪

- [ ] AgentCard 定义
- [ ] A2A Client/Server
- [ ] 多级 CircuitBreaker
- [ ] 可配置 HITL 中断点
- [ ] Diff 审批视图

---

**版本**：v1.0
**更新日期**：2026-05-02
