# retrieval 模块开发计划

> 状态：已规划
> 与未来框架设计 v2.1 对齐

## 模块定位

retrieval 模块是检索增强核心，提供：
- AdaptiveRetrieval 自适应检索
- HyDE 假设文档检索
- Cross-Encoder 重排
- Self-RAG 控制
- 意图感知检索

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| 意图路由融合 | 意图注入 + 重写 + 过滤 |
| AdaptiveRetrieval | 动态策略选择 |
| HyDE | 多假设生成 + 重排 |
| Cross-Encoder | 多模型集成重排 |

## 详细计划

见 `retrieval模块开发计划.md`

## 进度追踪

- [ ] 意图注入
- [ ] 意图重写
- [ ] 意图过滤
- [ ] 多假设 HyDE
- [ ] CrossEncoder 多模型
- [ ] 自适应阈值

---

**版本**：v1.0
**更新日期**：2026-05-02
