# knowledge_graph 模块开发计划

> 状态：已规划
> 与未来框架设计 v2.1 对齐

## 模块定位

knowledge_graph 模块是知识图谱核心，提供：
- GraphRAG 问答
- TEMPR 时序检索
- CARA 自适应推理
- Neo4j + Qdrant 存储
- 交互式可视化

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| Hindsight TEMPR | 时序实体图谱检索 |
| Hindsight CARA | 自适应推理 |
| 存储层 | Neo4j + Qdrant |
| 可视化 | G6 交互式图谱 |

## 详细计划

见 `knowledge_graph模块开发计划.md`

## 进度追踪

- [ ] Neo4j 连接器
- [ ] Qdrant 集成
- [ ] TEMPR 时序检索
- [ ] CARA 引擎
- [ ] G6 可视化

---

**版本**：v1.0
**更新日期**：2026-05-02
