# orchestration 模块开发计划

> 状态：待规划
> 与未来框架设计 v2.1 对齐

## 模块定位

orchestration 模块是编排逻辑兼容层，提供：
- MasterSupervisor 导出（向后兼容）
- PhaseSupervisor 导出
- IntentRouter 导出
- 状态模型导出

## 与已实现架构对应

| 已实现文件 | 功能 |
|-----------|------|
| `src/agents_v2/orchestration/__init__.py` | 兼容层（从 unified 导出）|

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| A2A 协议 | Agent 间协调 |
| 阶段编排 | PhaseSupervisor 增强 |
| 意图路由 | 三级级联路由 |

## 详细计划

见 `orchestration模块开发计划.md`

## 进度追踪

- [ ] 编排器增强
- [ ] 阶段协调优化
- [ ] 意图路由升级

---

**版本**：v1.0
**更新日期**：2026-05-03