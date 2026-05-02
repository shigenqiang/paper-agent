# paper_agents 模块开发计划

> 状态：已规划
> 与未来框架设计 v2.1 对齐

## 模块定位

paper_agents 模块是论文流水线核心，提供：
- TopicAgent 选题
- LiteratureAgent 文献
- OutlineAgent 大纲
- DraftWriterAgent 写作
- ReviewerAgent 评审
- PolisherAgent 润色

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| 六阶段写作流水线 | 选题→综述→大纲→写作→润色→终审 |
| Generator-Critic | Writer + Reviewer 配对迭代 |
| 5维度评审 | 学术规范/研究质量/内容完整/表达/逻辑 |
| 质量阈值 | ≥7.0 通过，否则返修 |

## 详细计划

见 `paper_agents模块开发计划.md`

## 进度追踪

- [ ] TopicAgent 增强（研究空白 + 可行性）
- [ ] LiteratureAgent 增强（深度探索 + 质量筛选）
- [ ] Generator-Critic 循环
- [ ] 迭代控制器
- [ ] 5维度 Reviewer
- [ ] Polisher 润色

---

**版本**：v1.0
**更新日期**：2026-05-02
