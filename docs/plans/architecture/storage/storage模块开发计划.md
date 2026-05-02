# storage 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/storage/storage-layer.md`
> 现状：SQLite + ChromaDB 基础已实现

---

## 一、模块概述

### 1.1 现有架构

```
storage/
└── paper_db.py            # SQLite + ChromaDB ✅
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **论文存储** | JSON/SQLite | PostgreSQL + Qdrant |
| **向量存储** | ChromaDB | Qdrant (生产级) |
| **图谱存储** | 无 | Neo4j 原生 |
| **缓存** | 内存 | Redis 分布式 |

---

## 二、任务清单

### 2.1 存储层升级（P1）

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| PostgreSQL 论文存储 | P1 | 结构化存储 | `src/agents_v2/storage/pg_paper_store.py` |
| Qdrant 向量存储 | P1 | 替换 ChromaDB | `src/agents_v2/storage/qdrant_store.py` |
| Neo4j 图谱存储 | P2 | 实体关系 | `src/agents_v2/storage/neo4j_store.py` |
| Redis 缓存 | P2 | 分布式缓存 | `src/agents_v2/storage/redis_cache.py` |

### 2.2 统一存储接口（P1）

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| StorageAdapter | P1 | 统一接口 | `src/agents_v2/storage/adapter.py` |
| 事务管理 | P2 | ACID 支持 | `src/agents_v2/storage/transaction.py` |
| 迁移工具 | P2 | 数据迁移 | `src/agents_v2/storage/migration.py` |

---

## 三、实施计划

```
Week 1:
  - PostgreSQL 论文存储实现
  - Qdrant 向量存储集成

Week 2:
  - Neo4j 图谱存储
  - Redis 缓存

Week 3:
  - 统一存储接口
  - 迁移工具
```

---

## 四、验收标准

- [ ] PostgreSQL 论文存储正常
- [ ] Qdrant 向量检索正常
- [ ] Neo4j 图谱存储正常
- [ ] Redis 缓存正常

---

**版本**：v1.0
**规划日期**：2026-05-02
