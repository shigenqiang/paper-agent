# knowledge_graph 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/knowledge_graph/knowledge-graph.md`
> 现状：KGService/GraphRAG/Embeddings/Community/KGBatchOperations 已实现

---

## 一、模块概述

### 1.1 现有架构

```
knowledge_graph/
├── kg_service.py             # KG服务 ✅
├── kg_graphrag.py           # GraphRAG问答 ✅
├── kg_embeddings.py         # 向量嵌入 ✅
├── kg_community.py          # 社区检测 ✅
└── kg_batch_operations.py   # 批量操作 ✅
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **KGService** | 基础 CRUD | 高级查询 + 推理 |
| **GraphRAG** | 基础 | TEMPR + CARA 自适应推理 |
| **存储** | 内存/文件 | Neo4j + Qdrant |
| **可视化** | 基础 | 交互式 G6 可视化 |

---

## 二、任务清单

### 2.1 GraphRAG 增强（P1）

**目标**：集成 Hindsight TEMPR + CARA

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| TEMPR 时序检索 | P1 | 时间维度记忆检索 | `src/agents_v2/knowledge_graph/tempr_retriever.py` |
| CARA 自适应推理 | P1 | 上下文自适应推理 | `src/agents_v2/knowledge_graph/cara_engine.py` |
| 图谱记忆整合 | P1 | 与记忆系统融合 | `src/agents_v2/knowledge_graph/memory_integration.py` |

### 2.2 存储层升级（P1）

**目标**：Neo4j + Qdrant 融合存储

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Neo4j 连接器 | P1 | 图谱存储 | `src/agents_v2/knowledge_graph/neo4j_connector.py` |
| Qdrant 集成 | P1 | 向量索引 | `src/agents_v2/knowledge_graph/qdrant_store.py` |
| 统一查询接口 | P2 | 混合查询 | `src/agents_v2/knowledge_graph/unified_query.py` |

### 2.3 可视化增强（P2）

**目标**：交互式知识图谱

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| G6 可视化集成 | P2 | 前端图谱展示 | `frontend/src/components/KnowledgeGraph.tsx` |
| 社区检测可视化 | P2 | 社区聚类展示 | `frontend/src/components/CommunityView.tsx` |
| 实体交互 | P2 | 点击查看详情 | `frontend/src/components/EntityDetail.tsx` |

---

## 三、实施计划

```
Week 1:
  - Neo4j 连接器实现
  - Qdrant 集成

Week 2:
  - TEMPR 时序检索实现
  - CARA 引擎实现

Week 3:
  - 图谱记忆整合
  - 可视化增强
```

---

## 四、验收标准

- [ ] Neo4j 图谱存储正常
- [ ] Qdrant 向量检索正常
- [ ] TEMPR 时序检索正常
- [ ] CARA 推理正常

---

**版本**：v1.0
**规划日期**：2026-05-02
