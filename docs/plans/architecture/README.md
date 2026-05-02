# Paper Agent 开发计划架构

> 版本：v2.0
> 规划日期：2026-05-03
> 基于：未来框架设计 v2.1 + 17份调研报告 + 已实现架构

---

## 概览

本文档目录包含 Paper Agent 各模块的详细开发计划，按 `docs/implemented/architecture/` 的模块结构组织。

## 模块列表

| 模块 | 开发计划 | 对应现状 | 规划状态 |
|------|----------|----------|----------|
| [core](core/) | [core模块开发计划.md](core/core模块开发计划.md) | LLMConfig + 路由 | 已规划 |
| [unified](unified/) | [unified模块开发计划.md](unified/unified模块开发计划.md) | MasterSupervisor + CircuitBreaker | 已规划 |
| [agents](agents/) | [agents模块开发计划.md](agents/agents模块开发计划.md) | BaseAgent + ReActLoop | **新增待规划** |
| [server](server/) | [server模块开发计划.md](server/server模块开发计划.md) | HTTP API Server | **新增待规划** |
| [orchestration](orchestration/) | [orchestration模块开发计划.md](orchestration/orchestration模块开发计划.md) | MasterSupervisor兼容层 | **新增待规划** |
| [harness](harness/) | [harness模块开发计划.md](harness/harness模块开发计划.md) | CircuitBreaker/HITL兼容层 | **新增待规划** |
| [memory](memory/) | [memory模块开发计划.md](memory/memory模块开发计划.md) | UnifiedMemoryManager v4 | 已规划 |
| [search](search/) | [search模块开发计划.md](search/search模块开发计划.md) | 6源学术搜索 | 已规划 |
| [evaluation](evaluation/) | [evaluation模块开发计划.md](evaluation/evaluation模块开发计划.md) | QualityEvaluator | 已规划 |
| [retrieval](retrieval/) | [retrieval模块开发计划.md](retrieval/retrieval模块开发计划.md) | AdaptiveRetrieval + HyDE | 已规划 |
| [knowledge_graph](knowledge_graph/) | [knowledge_graph模块开发计划.md](knowledge_graph/knowledge_graph模块开发计划.md) | GraphRAG | 已规划 |
| [langgraph-workflow](langgraph-workflow/) | [langgraph_workflow模块开发计划.md](langgraph-workflow/langgraph_workflow模块开发计划.md) | 5条工作流 + 22节点 | 已规划 |
| [storage](storage/) | [storage模块开发计划.md](storage/storage模块开发计划.md) | SQLite + ChromaDB | 已规划 |
| [tools](tools/) | [tools模块开发计划.md](tools/tools模块开发计划.md) | PDF解析 + 工具系统 | 已规划 |
| [paper_agents](paper_agents/) | [paper_agents模块开发计划.md](paper_agents/paper_agents模块开发计划.md) | 论文流水线 Agent | 已规划 |
| [diagnostic](diagnostic/) | [diagnostic模块开发计划.md](diagnostic/diagnostic模块开发计划.md) | 诊断框架 + 7诊断Agent | 已规划 |

## 与未来框架设计 v2.1 对应关系

### 协议层

| 未来框架设计 | 涉及模块 |
|-------------|----------|
| MCP 协议集成 | core + search + tools |
| A2A 协议 | unified + orchestration + agents |
| Agent Skills | tools + agents |
| AG-UI | core + server |

### 核心系统

| 未来框架设计 | 涉及模块 |
|-------------|----------|
| 记忆系统 v4.0 | memory + storage |
| 意图路由三级级联 | core + unified |
| Evaluator/Harness | evaluation + unified |
| PDF 解析升级 | tools |

### 数据层

| 未来框架设计 | 涉及模块 |
|-------------|----------|
| PostgreSQL + Qdrant + Neo4j | storage + memory + knowledge_graph |
| Redis 分布式缓存 | storage |

## 开发优先级

### P0（必须实现）

1. **agents** - BaseAgent Skill封装 + ReActLoop多样化
2. **server** - AG-UI协议 + SSE事件推送
3. **core** - MCP Client + 意图路由三级级联
4. **unified** - A2A 协议基础 + HITL 可配置中断
5. **memory** - 智能触发 + 遗忘曲线
6. **search** - MCP Server 封装
7. **paper_agents** - Generator-Critic 循环
8. **evaluation** - 5维度 QualityEvaluator

### P1（重要）

1. **retrieval** - 意图感知检索
2. **knowledge_graph** - TEMPR + CARA
3. **langgraph-workflow** - Checkpoint 持久化
4. **tools** - Marker + PDF-Extract-Kit
5. **storage** - PostgreSQL + Qdrant
6. **orchestration** - 三级级联路由 + A2A分发
7. **harness** - 多级CircuitBreaker + Diff审批

### P2（增强）

1. **knowledge_graph** - G6 可视化
2. **retrieval** - SelfRAG 自适应
3. **storage** - Redis 缓存 + 迁移工具

## 开发顺序建议

```
Phase 1（协议层）:
  server (AG-UI + SSE)
  agents (BaseAgent + Skill)
      ↓
  core (MCP/IntentRouter)
      ↓
  unified (A2A/HITL)

Phase 2（核心功能）:
  orchestration (A2A Dispatcher)
  memory (智能触发)
  search (MCP Server)
  paper_agents (Generator-Critic)

Phase 3（质量保障）:
  evaluation (5维度)
  harness (CircuitBreaker + HITL)
  retrieval (意图感知)

Phase 4（存储层）:
  storage (PG/Qdrant/Neo4j)
  knowledge_graph (存储+推理)

Phase 5（工具增强）:
  tools (PDF解析)
  langgraph-workflow (Checkpoint)
```

## 相关文档

- [未来框架设计 v2.1](../PaperAgent未来框架设计.md) - 整体架构设计
- [各模块开发计划](../各模块开发计划.md) - 汇总开发计划
- [implemented/architecture/](../implemented/architecture/) - 已实现架构文档

---

**版本**：v2.0
**更新日期**：2026-05-03
