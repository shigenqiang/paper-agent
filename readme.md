# Paper Agent

<p align="center">
  <strong>论文知识库分析 Agent</strong>
</p>

<p align="center">
  将论文集合转化为可追溯的研究理解，自动生成文献综述与创新点报告
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#核心功能">核心功能</a> ·
  <a href="#工作原理">工作原理</a> ·
  <a href="#api">API</a> ·
  <a href="#贡献">贡献</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/tests-166%20passed-brightgreen.svg" alt="Tests">
</p>

---

## 什么是 Paper Agent？

Paper Agent 是一个面向研究者的**论文知识库分析系统**。它不是通用的 AI 写作工具，而是专注于一个核心问题：

> **如何从一批论文中，提取结构化知识，发现研究空白，并生成有证据支撑的文献综述和创新点报告？**

### 它解决什么问题？

研究者通常需要阅读数十篇论文，手动整理笔记、绘制关系图、撰写综述。这个过程：

- **耗时**：阅读 30 篇论文可能需要数周
- **容易遗漏**：人工难以发现跨论文的共同局限和研究空白
- **难以追溯**：综述中的结论往往缺乏明确的证据来源

Paper Agent 自动化了这个过程。

### 与现有工具的区别

| | 通用 AI 助手 | 文献管理工具 | **Paper Agent** |
|---|---|---|---|
| 输入 | 单个问题 | 论文列表 | **项目级论文集合** |
| 分析方式 | 自由问答 | 标签分类 | **结构化提取 + 知识图谱** |
| 产出 | 通用回答 | 引用格式 | **文献综述 + 创新点报告** |
| 可追溯性 | 无 | 引用链接 | **结论 → 证据 → 论文 → 段落** |
| 知识结构 | 无 | 扁平标签 | **图谱：论文-主题-方法-发现-局限-空白** |

---

## 核心功能

### 论文管理
- 上传 PDF 文件
- 从学术搜索引擎导入
- 批量导入 DOI / BibTeX

### 知识提取
- **论文卡片**：自动提取研究问题、方法、数据集、关键发现、局限性
- **证据表**：从卡片生成结构化证据记录
- **知识图谱**：构建论文 → 主题 → 方法 → 发现 → 局限 → 空白的关系图

### 智能分析
- **Scope QA**：基于选中论文/主题/子图的限定范围问答
- **文献综述**：自动生成结构化综述（背景、主题、方法、发现、不足、趋势）
- **创新点报告**：基于图谱空白和共同局限，发现可行的创新方向

### 可追溯性
- 每条结论关联到具体证据
- 每条证据关联到论文和段落
- 创新点必须绑定支撑论文，拒绝无证据的泛化表述

---

## 工作原理

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   论文入库   │ ──▶ │   论文解析   │ ──▶ │   论文卡片   │
│  PDF/DOI/搜索 │     │  文本分块    │     │  结构化提取  │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  文献综述    │ ◀── │  Scope QA   │ ◀── │   证据表     │
│  结构化生成  │     │  范围限定问答 │     │  证据聚合    │
└─────────────┘     └─────────────┘     └─────────────┘
        ▲                                     │
        │           ┌─────────────┐           │
        └────────── │  知识图谱    │ ◀─────────┘
                    │  关系发现    │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  创新点报告  │
                    │  Gap 分析    │
                    └─────────────┘
```

### 三个核心中间层

系统不直接从 PDF 生成报告，而是经过三个结构化中间层：

1. **Paper Card** — 论文的结构化摘要
2. **Evidence Record** — 可查询的证据单元
3. **Knowledge Graph** — 实体关系网络

这保证了产出的可验证性。

### Scope-based QA

问答不是通用聊天，而是基于用户选定的范围：

```python
# 只基于选中的 3 篇论文回答
qa.answer(project_id, "这些研究有什么共同不足？", {
    "type": "selected_papers",
    "selected_paper_ids": ["paper_001", "paper_002", "paper_003"]
})

# 基于某个主题的所有论文回答
qa.answer(project_id, "反馈机制的研究方法有哪些？", {
    "type": "topic_group",
    "selected_topic_ids": ["feedback_mechanism"]
})

# 基于知识图谱子图回答
qa.answer(project_id, "这个方向有什么创新空间？", {
    "type": "graph_subgraph",
    "selected_graph_node_ids": ["topic:feedback_mechanism"],
    "graph_hops": 2
})
```

每条回答都声明范围，并列出支撑证据。

### 创新点反泛化

创新点报告内置反泛化检查，拒绝无证据支撑的泛化表述：

```
✗ "使用深度学习"        → 无具体证据，被拒绝
✗ "扩展样本量"          → 无具体论文支撑，被拒绝
✓ "将 X 方法迁移到 Y 领域" → 有 3 篇论文支撑图谱 Gap，被接受
```

### 搜索排序算法

搜索结果使用 **查询词覆盖率 × 字段加权 TF + 多维质量评分** 进行排序。

#### 相关性（TF + 覆盖率）

不依赖 BM25（小语料下 IDF 无意义），直接衡量查询词在论文各字段中的出现程度：

```
relevance = weighted_tf × coverage

weighted_tf = Σ (字段词频 × 字段权重)
coverage    = 匹配到的查询词数 / 总查询词数
```

各字段权重：

| 字段 | 权重 | 说明 |
|------|------|------|
| title | 3.0 | 标题最能反映论文主题 |
| keywords | 2.5 | 关键词高度相关 |
| abstract | 1.5 | 摘要是核心内容 |
| concepts | 1.0 | OpenAlex 概念标签 |
| venue | 0.5 | 期刊/会议名 |

覆盖率惩罚只匹配少量查询词的论文：如果查询有 4 个词，某论文只匹配到 1 个，分数仅为匹配 4 个的 1/4。

#### 质量评分

质量分衡量论文学术影响力，归一化到 [0, 1]：

```
quality = 0.75 × citation + 0.10 × velocity + 0.15 × recency
```

| 维度 | 权重 | 计算方式 |
|------|------|----------|
| 引用数 | 75% | `√citations / √max_citations`，平方根归一化，高引用区分度更好 |
| 引用速度 | 10% | `citations / age`，年均引用数，log 压缩归一化 |
| 新近性 | 15% | `e^(-0.08 × age)`，指数衰减，对经典论文更宽容 |

#### 最终分数

```
final = 0.55 × relevance + 0.25 × quality + 0.20 × source_priority
```

| 维度 | 权重 | 说明 |
|------|------|------|
| 相关性 | 55% | 查询词覆盖率 × 字段加权 TF |
| 质量 | 25% | 引用数 + 引用速度 + 完整度 + 新近性 |
| 来源优先级 | 20% | 数据源可信度（OpenAlex > arXiv > S2） |

---

## 快速开始

### 安装

```bash
git clone https://github.com/shigenqiang/paper-agent.git
cd paper-agent

# 安装依赖
pip install -e .

# 或仅安装核心依赖
pip install pydantic loguru pdfplumber fastapi uvicorn
```

### 配置

复制 `.env.example` 为 `.env`，填入 LLM API 密钥：

```bash
# MiMo API (Anthropic 兼容)
ANTHROPIC_BASE_URL=https://your-api-endpoint
ANTHROPIC_AUTH_TOKEN=your-token
ANTHROPIC_MODEL=mimo-v2.5-pro

# Semantic Scholar API Key（可选，提升搜索限额）
# 免费申请：https://www.semanticscholar.org/product/api#api-key-form
S2_API_KEY=your-semantic-scholar-api-key
```

### 启动服务

```bash
# 使用 Makefile（默认 anaconda Python，端口 8000）
make service

# 指定端口
make service PORT=9000

# 直接启动
python -m src.service --port 8000
```

### Makefile 命令

| 命令 | 说明 |
|------|------|
| `make service` | 启动服务（推荐） |
| `make install` | 安装项目依赖 |
| `make test` | 运行测试 |
| `make lint` | 代码检查 |
| `make clean` | 清理缓存和日志 |
| `make migrate` | 迁移平铺 JSON 到项目目录隔离 |
| `make docker-build` | 构建 Docker 镜像 |
| `make help` | 查看所有命令 |

### 运行测试

```bash
make test
# 或
python -m pytest tests/ -v
```

---

## HTTP API

服务启动后访问 `http://localhost:8000/docs` 查看 Swagger 文档。

### 项目管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rw/projects` | 创建研究项目 |
| `GET` | `/api/rw/projects` | 项目列表 |
| `GET` | `/api/rw/projects/{ref}` | 项目详情（project_id 或 dir_name） |
| `PATCH` | `/api/rw/projects/{ref}` | 更新项目（含改名） |
| `GET` | `/api/rw/projects/{ref}/stats` | 项目统计 |
| `DELETE` | `/api/rw/projects/{ref}` | 删除项目 |

### 论文库

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rw/projects/{ref}/papers/search` | 搜索候选论文 |
| `POST` | `/api/rw/projects/{ref}/papers/search/commit` | 确认入库 |
| `GET` | `/api/rw/projects/{ref}/papers` | 论文列表 |
| `POST` | `/api/rw/projects/{ref}/papers/{paper_id}/include` | 标记纳入 |
| `POST` | `/api/rw/projects/{ref}/papers/{paper_id}/exclude` | 标记排除 |

### 知识提取

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rw/projects/{ref}/papers/parse` | 解析论文 |
| `POST` | `/api/rw/projects/{ref}/cards` | 生成论文卡片 |
| `POST` | `/api/rw/projects/{ref}/evidence/build` | 构建证据表 |

### 知识图谱

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rw/projects/{ref}/kg/build` | 构建知识图谱 |
| `GET` | `/api/rw/projects/{ref}/kg` | 获取图谱 |
| `GET` | `/api/rw/projects/{ref}/kg/stats` | 图谱统计 |
| `POST` | `/api/rw/projects/{ref}/kg/subgraph` | 子图查询 |
| `GET` | `/api/rw/projects/{ref}/kg/gaps` | 发现研究空白 |

### 分析与生成

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rw/projects/{ref}/qa` | Scope QA |
| `POST` | `/api/rw/projects/{ref}/reports/literature-review` | 文献综述 |
| `POST` | `/api/rw/projects/{ref}/reports/innovation` | 创新点报告 |
| `GET` | `/api/rw/projects/{ref}/reports/{report_id}/export/markdown` | 导出 Markdown |
| `GET` | `/api/rw/projects/{ref}/reports/{report_id}/export/json` | 导出 JSON |

### 使用示例

```bash
# 1. 创建项目
curl -X POST http://localhost:8000/api/rw/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "sparse functional data research"}'

# 2. 搜索论文（用返回的 project_id）
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/papers/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sparse functional data", "sources": ["openalex", "arxiv"], "limit": 10}'

# 3. 确认入库（用返回的 session_id 和选中的 result_id）
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/papers/search/commit \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "selected_result_ids": ["id1", "id2"]}'

# 4. 解析 → 生成卡片 → 构建证据 → 构建图谱
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/papers/parse
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/cards
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/evidence/build
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/kg/build

# 5. QA
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main methods?", "scope": {"type": "all_project"}}'

# 6. 文献综述
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/reports/literature-review \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_project"}}'

# 7. 创新点报告
curl -X POST http://localhost:8000/api/rw/projects/{project_id}/reports/innovation \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_project"}}'
```

### 推荐工作流

```
① POST /api/rw/projects                         → 创建项目
② POST /api/rw/projects/{ref}/papers/search      → 搜索候选论文
③ POST /api/rw/projects/{ref}/papers/search/commit → 确认入库
④ POST /api/rw/projects/{ref}/papers/parse        → 解析论文
⑤ POST /api/rw/projects/{ref}/cards               → 生成论文卡片
⑥ POST /api/rw/projects/{ref}/evidence/build      → 构建证据表
⑦ POST /api/rw/projects/{ref}/kg/build            → 构建知识图谱
⑧ POST /api/rw/projects/{ref}/qa                  → Scope QA
⑨ POST /api/rw/projects/{ref}/reports/literature-review → 文献综述
⑩ POST /api/rw/projects/{ref}/reports/innovation       → 创新点报告
```

---

## 项目结构

```
src/
├── service.py                         # 服务入口（启动 FastAPI）
├── agents_v3/
│   ├── cli.py                         # CLI 命令行工具
│   └── research_workspace/
│       ├── models.py                  # Pydantic 数据模型
│       ├── storage.py                 # JSON 文件持久化（项目目录隔离）
│       ├── project_service.py         # 项目管理
│       ├── paper_library.py           # 论文库管理
│       ├── parser_service.py          # PDF 解析
│       ├── paper_card.py              # 论文卡片生成
│       ├── evidence_table.py          # 证据表构建
│       ├── graph_service.py           # 知识图谱
│       ├── scope.py                   # Scope 解析
│       ├── scope_qa.py                # Scope QA
│       ├── review_generator.py        # 文献综述生成
│       ├── innovation_generator.py    # 创新点报告生成
│       ├── report_service.py          # 报告管理
│       ├── llm/                       # LLM 服务层
│       ├── search/                    # 多源搜索（arXiv/OpenAlex/CrossRef）
│       ├── evaluation/                # 评估与质量门
│       └── api/                       # FastAPI 路由
scripts/
├── migrate_storage.py                 # 存储迁移脚本（项目目录隔离）
└── migrate_paper_model.py             # 论文模型迁移脚本（扁平→子模型）
```

### 数据存储结构

支持 **PostgreSQL**（推荐）和 **JSON 文件** 两种存储后端，通过 `config.yaml` 切换：

```yaml
database:
  postgres:
    enabled: true
    host: localhost
    port: 5432
    database: paper_agent
    user: postgres
    password: "your-password"
  qdrant:
    enabled: true
    host: localhost
    port: 6333

storage_backend: postgres  # 可选: "json", "postgres"
```

**PostgreSQL 模式**：所有数据存储在数据库中，支持 16 张表（projects, papers, paper_chunks, paper_cards, evidence_records, kg_nodes, kg_edges, topic_scores, parse_results, reports, search_sessions, qa_history, paper_references, papers_pool 等）。

**JSON 模式**：每个项目独立目录，轻量可读，适合开发和小规模使用。

删除项目时，PostgreSQL 模式会自动清理：数据库记录（CASCADE 自动删 papers→chunks/cards）+ Qdrant 向量 + 本地 PDF 文件。

### 论文数据模型

论文采用子模型结构，支持 arXiv、CrossRef、OpenAlex、Semantic Scholar、PubMed 五个平台的统一元数据：

```python
class Paper(BaseModel):
    paper_id: str
    project_id: str
    title: str
    abstract: str

    identifiers: PaperIdentifiers    # doi, arxiv_id, pubmed_id, openalex_id, ...
    authors: list[Author]            # name, orcid, affiliations
    dates: PaperDates                # year, published_date
    source: PaperSource              # venue, volume, issue, pages
    open_access: OpenAccessInfo      # is_oa, oa_status, pdf_url
    classification: PaperClassification  # categories, concepts, keywords, mesh_terms
    citation: CitationInfo           # citation_count, references

    url: str
    source_platform: str             # arxiv/crossref/openalex/upload/bibtex/doi
    source_payload: dict             # 平台原始数据
    status: PaperStatus              # imported/parsing/parsed/card_ready/...
```

搜索阶段使用轻量 `SearchResult` 模型，入库时自动转换为子模型结构。

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 类型注解、现代语法 |
| HTTP 服务 | FastAPI + Uvicorn | 异步 Web 框架，自动 Swagger 文档 |
| LLM | LLMService（可配置） | 统一 LLM 调用接口 |
| 数据模型 | Pydantic v2 | 强类型、自动验证 |
| 存储 | PostgreSQL + JSON 文件 | PostgreSQL 存储结构化数据，JSON 作为轻量备选 |
| 向量存储 | Qdrant | 存储论文分块嵌入，支持向量检索 |
| 搜索 | OpenAlex / arXiv / Semantic Scholar / CrossRef | 多源学术搜索 + TF 覆盖率排序 + 去重 |
| PDF 解析 | pdfplumber / PyMuPDF / pdfminer | 多解析器 fallback，自动分块和清洗 |
| 知识图谱 | NetworkX | 实体关系图 + Gap 分析 |
| 日志 | Loguru | 结构化日志 |
| 测试 | pytest | 130+ 测试用例 |
| 代码质量 | Ruff | 格式化和 lint |
| 容器化 | Docker + GHCR | 多阶段构建 |

---

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'Add your feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

### 开发规范

- 遵循 [代码规范](docs/development/代码规范.md)
- 遵循 [项目规范](docs/development/项目规范.md)
- 新增功能必须包含测试
- 运行 `python -m pytest tests/agents_v3/ -v` 确保测试通过

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  如果这个项目对你有帮助，请给一个 ⭐️
</p>
