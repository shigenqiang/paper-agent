# langgraph-workflow 模块开发计划

> 状态：已规划
> 与未来框架设计 v2.1 对齐

## 模块定位

langgraph-workflow 模块是工作流编排核心，提供：
- 5条工作流（search/writing/report/qa/revise）
- 22个节点
- Checkpoint 持久化
- A2A 任务分发
- HITL 可配置中断

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| A2A 协议集成 | A2A 任务分发 + 流式状态更新 |
| Checkpoint | SqliteSaver + PostgresSaver |
| HITL | 可配置中断点 + Diff 审批 |
| 时间旅行 | 状态回退 + 调试 |

## 详细计划

见 `langgraph_workflow模块开发计划.md`

## 进度追踪

- [ ] A2A 任务分发
- [ ] 流式状态更新
- [ ] SqliteSaver
- [ ] PostgresSaver
- [ ] 可配置中断点
- [ ] Diff 审批

---

**版本**：v1.0
**更新日期**：2026-05-02
