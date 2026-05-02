# harness 模块开发计划

> 状态：待规划
> 与未来框架设计 v2.1 对齐

## 模块定位

harness 模块是质量保障兼容层，提供：
- CircuitBreaker 熔断器
- HITLManager 人机协作
- ExecutionReplay 执行回放
- ErrorHandler 错误处理

## 与已实现架构对应

| 已实现文件 | 功能 |
|-----------|------|
| `src/agents_v2/harness/__init__.py` | 兼容层（从 unified 导出）|

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| CircuitBreaker | 多级熔断 + 指标监控 |
| HITL Manager | 可配置中断 + Diff 审批 |
| Evaluator | 5维度质量评估 |
| AuditTrail | 完整审计溯源 |

## 详细计划

见 `harness模块开发计划.md`

## 进度追踪

- [ ] CircuitBreaker 增强
- [ ] HITL 中断可配置
- [ ] Diff 审批视图
- [ ] 评估体系完善

---

**版本**：v1.0
**更新日期**：2026-05-03