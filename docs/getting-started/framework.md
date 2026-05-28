# Paper Agent 框架与实现情况

## 项目概述

Paper Agent 是一个**论文知识库分析系统**，面向研究生和早期研究者。核心功能：从论文集合中提取结构化知识、构建知识图谱、生成可溯源的文献综述和创新点报告。

**技术栈：** Python 3.11+ / Pydantic v2 / LangChain / FastAPI / MiniMax-M2.7

---

## 整体架构

```
┌─────────────────────────────────────────────────────┐
│                   入口层 (Entry)                      │
│   CLI (cli.py)          FastAPI (api/app.py)         │
└──────────────┬──────────────────┬────────────────────┘
               │                  │
┌──────────────▼──────────────────▼────────────────────┐
│                 核心管线 (Pipeline)                     │
│                                                       │
│  ProjectService                                       │
│      ↓                                                │
│  PaperLibraryService (导入论文元数据)                   │
│      ↓                                                │
│  ParserService (PDF → PaperChunk)                     │
│      ↓                                                │
│  PaperCardGenerator (LLM → PaperCard)                 │
│      ↓                                                │
│  EvidenceTableService (→ EvidenceRecord)              │
│      ↓                                                │
│  GraphService (→ KnowledgeGraph)                      │
│      ↓                                                │
│  ScopeQAService (范围问答)                             │
│      ↓                                                │
│  ReviewGenerator / InnovationGenerator (报告生成)      │
│      ↓                                                │
│  ReportService (存储 + Markdown导出)                   │
│                                                       │
└───────────┬──────────┬──────────┬────────────────────┘
            │          │          │
┌───────────▼──┐ ┌─────▼────┐ ┌──▼──────────┐
│  LLM 层      │ │ 搜索层    │ │ 评估层       │
│  llm/        │ │ search/  │ │ evaluation/  │
└──────────────┘ └──────────┘ └──────────────┘
```

---

## 目录结构

```
src/
├── agents_v3/                          # 主系统 (43 .py, 1.1M)
│   ├── __init__.py                     # v0.1.0
│   ├── cli.py                          # CLI 入口
│   └── research_workspace/             # 核心模块
│       ├── models.py                   # 20+ Pydantic 数据模型
│       ├── storage.py                  # JSON 文件持久化
│       ├── project_service.py          # 项目 CRUD
│       ├── paper_library.py            # 论文元数据管理
│       ├── parser_service.py           # PDF 解析 → PaperChunk
│       ├── paper_card.py               # LLM 论文卡片提取
│       ├── evidence_table.py           # 证据记录生成
│       ├── graph_service.py            # 知识图谱构建
│       ├── scope.py                    # 检索范围解析
│       ├── scope_qa.py                 # 范围问答 + 意图路由
│       ├── review_generator.py         # 文献综述生成
│       ├── innovation_generator.py     # 创新点报告生成
│       ├── report_service.py           # 报告存储/导出
│       ├── llm/                        # LLM 抽象层 (5 .py)
│       │   ├── service.py              # LLMService, FakeLLMService
│       │   ├── prompts.py              # PromptRegistry 模板管理
│       │   ├── json_utils.py           # JSON 提取/修复
│       │   ├── errors.py              # LLM 异常层次
│       │   └── logging.py             # LLM 调用日志
│       ├── search/                     # 多源学术搜索 (11 .py)
│       │   ├── orchestrator.py         # 搜索编排 (扇出/合并/排序)
│       │   ├── arxiv_client.py         # arXiv API 适配器
│       │   ├── crossref_client.py      # CrossRef API 适配器
│       │   ├── openalex_client.py      # OpenAlex API 适配器
│       │   ├── strategies.py           # 查询策略生成
│       │   ├── merger.py               # 结果合并
│       │   ├── dedup.py                # 去重
│       │   ├── ranking.py              # 相关性排序
│       │   ├── cache.py                # 搜索缓存
│       │   ├── rate_limit.py           # 源级限流
│       │   └── factory.py              # 适配器工厂
│       ├── evaluation/                 # 质量评估框架 (5 .py)
│       │   ├── evaluator.py            # 评估管线
│       │   ├── gates.py               # 质量门禁
│       │   ├── golden.py              # 黄金测试集
│       │   ├── metrics.py             # 指标收集
│       │   └── logging_utils.py       # 结构化日志
│       └── api/                        # FastAPI REST 层 (5 .py)
│           ├── app.py                  # 应用工厂 + 路由
│           ├── deps.py                 # 依赖注入
│           ├── models.py              # 请求/响应模型
│           ├── errors.py              # 错误处理
│           └── tasks.py               # 异步任务管理
│
├── models/                             # 基础模型 (2 .py)
│   ├── state.py                        # 状态模型
│   └── task.py                         # 任务模型
│
└── service.py                          # 顶层服务入口

tests/
└── agents_v3/                          # 测试 (30 .py, 208K)
    └── research_workspace/
        ├── conftest.py                 # 测试夹具
        ├── test_e2e_smoke.py           # 端到端冒烟测试
        ├── test_api.py                 # API 测试
        ├── test_models.py              # 模型测试
        ├── test_project_service.py     # 项目服务测试
        ├── test_paper_library.py       # 论文库测试
        ├── test_parser_service.py      # 解析器测试
        ├── test_paper_card_generator.py # 卡片生成测试
        ├── test_evidence_table_service.py # 证据表测试
        ├── test_graph_service.py       # 知识图谱测试
        ├── test_scope_qa.py            # 范围问答测试
        ├── test_review_generator.py    # 综述生成测试
        ├── test_innovation_generator.py # 创新点测试
        ├── test_report_service.py      # 报告服务测试
        ├── test_llm_service.py         # LLM 服务测试
        ├── test_storage.py             # 存储测试
        ├── test_evaluation.py          # 评估测试
        ├── test_retrieval_scope.py     # 检索范围测试
        ├── test_search_*.py            # 搜索相关测试 (8个)
        └── test_rate_limit.py          # 限流测试

demos/
└── agent_v3_demo.py                    # Agent v3 演示脚本
```

---

## 各模块实现情况

### 1. 数据模型层 (`research_workspace/models.py`)

| 模型 | 说明 | 状态 |
|------|------|------|
| `Project` | 研究项目 | ✅ 已实现 |
| `Paper` | 论文元数据 | ✅ 已实现 |
| `PaperChunk` | PDF 解析分块 | ✅ 已实现 |
| `PaperCard` | 结构化论文卡片 (问题/方法/发现/局限/空白) | ✅ 已实现 |
| `EvidenceRecord` | 证据记录 | ✅ 已实现 |
| `KnowledgeGraph` | 知识图谱 (节点+边) | ✅ 已实现 |
| `Report` | 文献综述/创新报告 | ✅ 已实现 |
| `QARequest/Response` | 问答请求/响应 | ✅ 已实现 |

**枚举类型：** `PaperStatus`, `ChunkType`, `NodeType`, `EdgeType`, `ScopeType`, `ReportType`

### 2. 核心服务层

| 服务 | 功能 | 状态 | 说明 |
|------|------|------|------|
| `ProjectService` | 项目 CRUD | ✅ | 创建/查询/更新/删除项目 |
| `PaperLibraryService` | 论文导入 | ✅ | 手动/DOI/BibTeX 导入 |
| `ParserService` | PDF 解析 | ✅ | PDF → PaperChunk，基于 pdfplumber |
| `PaperCardGenerator` | 卡片提取 | ✅ | LLM 驱动，提取关键主张/方法/发现/局限 |
| `EvidenceTableService` | 证据聚合 | ✅ | PaperCard → EvidenceRecord |
| `GraphService` | 知识图谱 | ✅ | 节点: Paper/Author/Topic/Method/Gap/Innovation |
| `ScopeQAService` | 范围问答 | ✅ | 意图路由: 综述/创新/空白分析 |
| `ReviewGenerator` | 文献综述 | ✅ | 基于证据+图谱生成 |
| `InnovationGenerator` | 创新报告 | ✅ | 基于图谱+空白分析生成 |
| `ReportService` | 报告管理 | ✅ | 存储 + Markdown 导出 |

### 3. LLM 抽象层 (`llm/`)

| 组件 | 功能 | 状态 |
|------|------|------|
| `LLMService` | OpenAI 兼容 API 封装 | ✅ |
| `FakeLLMService` | 测试用 Mock | ✅ |
| `PromptRegistry` | 提示词模板管理 | ✅ |
| `json_utils` | JSON 提取/修复 | ✅ |
| `errors` | 异常层次 | ✅ |
| `logging` | 调用日志 | ✅ |

**默认模型：** MiniMax-M2.7 (通过 OpenAI 兼容接口)

### 4. 搜索层 (`search/`)

| 组件 | 功能 | 状态 |
|------|------|------|
| `SearchOrchestrator` | 多源搜索编排 | ✅ |
| `arxiv_client` | arXiv API | ✅ |
| `crossref_client` | CrossRef API | ✅ |
| `openalex_client` | OpenAlex API | ✅ |
| `strategies` | 查询策略生成 | ✅ |
| `merger` | 结果合并 | ✅ |
| `dedup` | 去重 | ✅ |
| `ranking` | 相关性排序 | ✅ |
| `cache` | 搜索缓存 | ✅ |
| `rate_limit` | 源级限流 | ✅ |
| `factory` | 适配器工厂 | ✅ |

**搜索流程：** 查询 → 策略生成 → 扇出(3源) → 合并 → 去重 → 排序 → 返回

### 5. 评估层 (`evaluation/`)

| 组件 | 功能 | 状态 |
|------|------|------|
| `evaluator` | 评估管线 (引用覆盖/范围保护/脱敏/可追溯性) | ✅ |
| `gates` | 质量门禁 | ✅ |
| `golden` | 黄金测试集 | ✅ |
| `metrics` | 指标收集 | ✅ |
| `logging_utils` | 结构化日志 | ✅ |

### 6. API 层 (`api/`)

| 组件 | 功能 | 状态 |
|------|------|------|
| `app.py` | FastAPI 应用 + 路由 | ✅ |
| `deps.py` | 依赖注入 | ✅ |
| `models.py` | 请求/响应模型 | ✅ |
| `errors.py` | 错误处理 | ✅ |
| `tasks.py` | 异步任务管理 | ✅ |

### 7. 持久化层 (`storage.py`)

- 方案：JSON 文件存储
- 存储位置：可配置目录
- 支持：项目、论文、卡片、证据、图谱、报告

---

## 核心数据流

```
用户输入主题/论文
       │
       ▼
  ProjectService.create_project()
       │
       ▼
  PaperLibraryService.import_papers()
       │  (手动/DOI/BibTeX)
       ▼
  ParserService.parse_pdf()
       │  PDF → PaperChunk[]
       ▼
  PaperCardGenerator.generate()
       │  LLM → PaperCard (问题/方法/发现/局限/空白)
       ▼
  EvidenceTableService.build()
       │  PaperCard[] → EvidenceRecord[]
       ▼
  GraphService.build_graph()
       │  → KnowledgeGraph (节点/边)
       │
       ├──────────────────┐
       ▼                  ▼
  ScopeQAService    ReviewGenerator
  (范围问答)        (文献综述)
       │                  │
       ▼                  ▼
  InnovationGenerator   ReportService
  (创新点报告)          (存储/导出)
```

---

## 配置与部署

### 环境变量

```bash
LLM_PROVIDER=openai
LLM_MODEL=minimax-m2.7
OPENAI_API_KEY=sk-cp-xxxxx
OPENAI_BASE_URL=https://api.minimax.chat/v1
```

### Docker 部署

```bash
make docker-build    # 构建镜像
make service         # 启动服务 (端口 8000)
```

支持三种构建目标：标准运行时、GPU 运行时 (CUDA 11.8)、Alpine 轻量版。

### Makefile 命令

| 命令 | 功能 |
|------|------|
| `make service` | 启动服务 |
| `make install` | 安装依赖 |
| `make test` | 运行测试 |
| `make lint` | Ruff 代码检查 |
| `make clean` | 清理临时文件 |

---

## 测试覆盖

**30 个测试文件**，覆盖所有核心模块：

- 模型层：`test_models.py`
- 服务层：各服务独立测试 (项目/论文/解析/卡片/证据/图谱/问答/综述/创新/报告)
- LLM 层：`test_llm_service.py`
- 搜索层：8 个搜索相关测试 (编排/合并/去重/排序/缓存/集成/模型/会话)
- 评估层：`test_evaluation.py`
- API 层：`test_api.py`
- 端到端：`test_e2e_smoke.py`

---

## 统计

| 指标 | 数值 |
|------|------|
| 源码 .py 文件 | 43 |
| 测试 .py 文件 | 30 |
| 源码大小 | 1.1M |
| 测试大小 | 208K |
| 数据模型 | 20+ Pydantic 模型 |
| 搜索源 | 3 (arXiv, CrossRef, OpenAlex) |
| LLM 支持 | OpenAI 兼容接口 (MiniMax-M2.7) |
