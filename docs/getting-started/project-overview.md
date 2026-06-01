# PaperAgent 项目概述

## 项目定位

PaperAgent 是一个**论文知识库分析系统**，面向研究生和早期研究者。核心功能：从论文集合中提取结构化知识、构建知识图谱、生成可溯源的文献综述和创新点报告。

**不是**通用 AI 写作工具，**不是**全论文写作平台。

---

## 解决什么问题

研究者通常需要阅读数十篇论文，手动整理笔记、绘制关系图、撰写综述。这个过程：

- **耗时**：阅读 30 篇论文可能需要数周
- **容易遗漏**：人工难以发现跨论文的共同局限和研究空白
- **难以追溯**：综述中的结论往往缺乏明确的证据来源

PaperAgent 自动化了这个过程。

---

## 技术架构

### 后端 (Python FastAPI)
- **位置**: `src/agents_v3/research_workspace/`
- **核心框架**: FastAPI + Uvicorn
- **Python 文件**: 56 个
- **存储**: PostgreSQL (结构化数据) + Qdrant (向量) + JSON (轻量备选)
- **LLM**: OpenAI 兼容接口（可配置）

### 前端 (React + Vite)
- **位置**: `frontend/`
- **框架**: React 18 + Vite + React Router v6
- **状态管理**: Zustand
- **图谱可视化**: D3.js force-directed
- **页面**: 论文库 / 知识图谱 / 研究QA / 成果报告
- **主题**: 深空实验室（深色 + 琥珀高亮）
- **启动**: `cd frontend && npm run dev`（端口 3000）

---

## 核心工作流

```
① 创建研究项目
② 搜索/导入论文 (arXiv / OpenAlex / Semantic Scholar)
③ 解析 PDF → 分块
④ 生成论文卡片 (LLM)
⑤ 构建证据表
⑥ 构建知识图谱
⑦ Scope QA (RAG 范围问答)
⑧ 生成文献综述
⑨ 生成创新点报告
```

---

## 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 项目管理 | `project_service.py` | 项目 CRUD |
| 论文库 | `paper_library.py` | 搜索/导入/管理论文 |
| PDF 解析 | `parser_service.py` | PDF → PaperChunk |
| 论文卡片 | `paper_card.py` | LLM 提取结构化卡片 |
| 证据表 | `evidence_table.py` | 证据记录生成 |
| 知识图谱 | `graph_service.py` | 实体关系图构建 |
| 范围问答 | `scope_qa.py` | RAG + 意图路由 |
| 文献综述 | `review_generator.py` | 结构化综述生成 |
| 创新点报告 | `innovation_generator.py` | Gap 分析 + 创新点 |
| 报告管理 | `report_service.py` | 存储 + 导出 |

---

## 搜索系统

多源学术搜索 + BM25 排序 + LLM 查询优化：

```
用户查询 → LLM 查询优化 → 策略生成 → 扇出(3源)
                                          │
                     ┌────────────────────┼────────────────────┐
                     ▼                    ▼                    ▼
                 arXiv              OpenAlex          Semantic Scholar
                     │                    │                    │
                     └────────────────────┼────────────────────┘
                                          ▼
                                    合并 → 去重 → BM25 排序 → 相关性过滤 → 返回
```

**排序算法**: BM25 相关性 (55%) + 质量评分 (25%) + 来源优先级 (20%)

---

## 存储架构

支持两种存储后端，通过 `config.yaml` 切换：

| 后端 | 说明 | 适用场景 |
|------|------|----------|
| PostgreSQL | 16 张表，支持 CASCADE 删除 | 生产环境 |
| JSON 文件 | 每项目独立目录 | 开发/小规模 |

向量存储使用 Qdrant，支持论文分块的语义检索。

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rw/projects` | 创建项目 |
| `GET` | `/api/rw/projects` | 项目列表 |
| `POST` | `/api/rw/projects/{ref}/papers/search` | 搜索论文 |
| `POST` | `/api/rw/projects/{ref}/papers/search/commit` | 确认入库 |
| `POST` | `/api/rw/projects/{ref}/papers/parse` | 解析论文 |
| `POST` | `/api/rw/projects/{ref}/cards` | 生成卡片 |
| `POST` | `/api/rw/projects/{ref}/evidence/build` | 构建证据 |
| `POST` | `/api/rw/projects/{ref}/kg/build` | 构建图谱 |
| `POST` | `/api/rw/projects/{ref}/qa` | Scope QA |
| `POST` | `/api/rw/projects/{ref}/reports/literature-review` | 文献综述 |
| `POST` | `/api/rw/projects/{ref}/reports/innovation` | 创新点报告 |

完整 API 文档：`http://localhost:8000/docs`

---

## 与旧版本的区别

当前版本（v3 research_workspace）是完全重写，与旧版本有本质区别：

| | 旧版本 | 当前版本 |
|---|---|---|
| 架构 | 40+ Agent 系统 | 单一 research_workspace 管线 |
| 后端 | aiohttp | FastAPI |
| 存储 | SQLite + ChromaDB | PostgreSQL + Qdrant |
| 前端 | React + Vite | 无（纯 API） |
| 图谱 | Neo4j | NetworkX |
| 搜索 | 多 Agent 分散 | 统一 SearchOrchestrator |

---

## 统计

| 指标 | 数值 |
|------|------|
| 源码 .py 文件 | 56 |
| 测试用例 | 438 |
| 搜索源 | 3 (arXiv, OpenAlex, Semantic Scholar) |
| 存储后端 | 2 (PostgreSQL, JSON) |
| API 端点 | 15+ |
