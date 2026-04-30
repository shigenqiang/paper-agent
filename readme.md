# Paper Agent — 智能论文调研与写作系统

> 基于多 Agent 协作与 Harness 质量保障的学术论文全生命周期辅助平台

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18-61dafb.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 项目简介

Paper Agent 是一个面向大学生的智能论文学术助手，提供从**选题诊断 → 文献综述 → 大纲规划 → 逐章写作 → 修改润色 → 格式输出**的全流程 AI 辅助。系统采用**多 Agent 协作架构**，由专业化 Agent（搜索/规划/写作/评审/润色）在 Harness 层（Evaluator / Checkpoint / CircuitBreaker / HITL）的保障下协同完成写作任务。

### 与现有工具的核心差异

| 维度 | 现有论文工具 | Paper Agent |
|------|-------------|-------------|
| Agent 模式 | 单一 LLM 调用 | **多 Agent 协作 + Harness 质量保障** |
| 写作范式 | "一次生成" | **Generator-Critic 循环 + 多层反思** |
| 人机协作 | 文本编辑器 | **Diff 补丁 + 阶段性审批 (HITL)** |
| 容错能力 | 无 | **CircuitBreaker + Checkpoint 恢复** |
| 可追溯性 | 无 | **完整 AuditTrail + Journal 日志** |

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                       FRONTEND (React 18 + Vite)                   │
│  写作工作台 | 文献浏览器 | 大纲编辑器 | AI 对话 | 知识图谱可视化   │
├──────────────────────────────────────────────────────────────────┤
│                       API GATEWAY (aiohttp :8000)                 │
│  REST + SSE Streaming | X-API-Key Auth | 限流 | 路由             │
├──────────────────────────────────────────────────────────────────┤
│                    ORCHESTRATOR (LangGraph StateGraph)             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  MasterSupervisor: 选题 → 文献 → 大纲 → 写作 → 润色 → 终审  │  │
│  │       ↓               ↓         ↓        ↓        ↓        │  │
│  │  [Checkpoint]    [Checkpoint] [Checkpoint] ... [HITL]      │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                     SPECIALIZED AGENTS                             │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ │
│  │Searcher │ │ Planner  │ │  Writer  │ │Reviewer │ │Polisher │ │
│  │文献检索  │ │大纲规划   │ │章节写作   │ │质量评审  │ │语言润色  │ │
│  └─────────┘ └──────────┘ └──────────┘ └─────────┘ └─────────┘ │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Method   │ │Citation  │ │  Chart   │ │ PlagCheck│           │
│  │Advisor  │ │ Manager  │ │Formatter │ │er Agent  │           │
│  │方法论    │ │引用管理   │ │图表生成   │ │查重检测   │           │
│  └─────────┘ └──────────┘ └──────────┘ └──────────┘           │
├──────────────────────────────────────────────────────────────────┤
│                    HARNESS (质量保障层)                             │
│  Evaluator │ CheckpointManager │ CircuitBreaker │ HITL │ Audit  │
├──────────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                                  │
│  Memory System │ Search Engine │ Knowledge Graph │ LLM Router    │
│  (短期/长期/情景) │ (6+学术数据源)  │ (GraphRAG)      │ (16 模型)    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 核心功能

| 模块 | 功能 | 说明 |
|------|------|------|
| **智能选题** | 研究空白分析、热门趋势、可行性评估 | Agent 驱动的研究空白识别 |
| **文献综述** | 6 源并行搜索、自动筛选、结构化综述 | 借鉴 GPT Researcher 树状递归探索 |
| **大纲规划** | 层级化大纲生成、结构验证、方法论匹配 | Planner + Reviewer 协作 |
| **逐章写作** | 上下文感知、风格一致、逻辑连贯 | Generator-Critic 循环迭代 |
| **智能修改** | 解析审稿意见、多轮精炼、Diff 对比 | SmartReviser + ReportRefiner |
| **语言润色** | 学术语气调整、专业术语规范 | 学术专用模型 |
| **定时报告** | 每日/每周/每月论文报告自动生成 | 多 Agent 并行监控 |
| **对话问答** | 基于论文的智能问答、对比分析 | 意图路由 + 多源搜索 |
| **知识图谱** | 文献关系可视化、GraphRAG 问答、社区检测 | 交互式 KG |
| **格式输出** | LaTeX / Word / PDF / Markdown 多格式 | 引用自动格式化 |

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+ (前端)
- Docker (可选)

### 后端启动

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY 等

# 启动 API 服务
python -m src.main
```

服务运行在 `http://localhost:8000`，健康检查：`/health`

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:5173`

### Docker 部署

```bash
# 完整栈（API + 前端 + 数据库）
docker-compose up -d

# 仅 API 服务
docker-compose up -d paper-agent

# GPU 版本
docker build -f Dockerfile --target runtime-gpu -t paper-agent:gpu .
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + Vite + Ant Design 5 + Tailwind CSS + Zustand + G6 | SPA 写作工作台 |
| **后端** | Python 3.11 + aiohttp + LangChain + Pydantic | 异步 HTTP 服务 |
| **Agent 编排** | LangGraph (StateGraph) | 有向图状态机 + Checkpoint + HITL |
| **LLM 支持** | OpenAI / Anthropic Claude / MiniMax / DeepSeek / Qwen / GLM | 16 个注册模型，6 个提供商 |
| **存储** | JSON 文件持久化 + 内存缓存 | 论文/文献数据重启不丢失 |
| **数据库** (可选) | PostgreSQL + Redis + Neo4j | `docker-compose.yml` profiles |
| **容器化** | Docker 多阶段构建 + Docker Compose + K8s 部署文件 | 3 种构建目标 |

---

## Agent 写作流水线

```
阶段 1: 选题诊断
  Searcher Agent → Planner Agent → Reviewer Agent → [HITL: 人工确认选题]

阶段 2: 文献综述
  Searcher Agent (6 源深度检索) → Writer Agent → Reviewer Agent → [HITL: 审核综述]

阶段 3: 大纲规划
  Planner Agent → Methodology Advisor → Reviewer Agent → [HITL: 确认大纲]

阶段 4: 逐章写作 (Generator-Critic 循环)
  Writer Agent → Reviewer Agent → Polisher Agent
      ↑                  ↓
      └── 分数 < 阈值 ──→ 返修 ──→ [HITL: 每章可选审核]

阶段 5: 综合润色
  Polisher Agent → Citation Manager → Plagiarism Checker → [HITL: 终审]

阶段 6: 格式输出
  Chart Formatter → Citation Formatter → LaTeX / Word / PDF / Markdown
```

### Harness 质量保障

| 组件 | 功能 | 说明 |
|------|------|------|
| **Evaluator** | 7 维度质量评分（结构/逻辑/原创/语言/引用/完整/格式） | LLM-as-Judge + 规则引擎 |
| **CheckpointManager** | 检查点保存/恢复/回退 | 借鉴 LangGraph Checkpointer + Restate Journal |
| **CircuitBreaker** | 熔断保护（错误率>30%、连续失败5次、超时5min、费用>$5） | 防止级联失败 |
| **HITL Manager** | 5 个中断点 + Diff 审批视图 | 借鉴 PaperDebugger Diff 补丁 |
| **AuditTrail** | 完整操作溯源 + 状态转换日志 | 分布式系统 Journal 模式 |

### Agent Loop 模式

| 模式 | 说明 | 来源 |
|------|------|------|
| **ReAct** | Observe → Think → Act 基础循环 | Yao et al. 2023 |
| **Plan-Execute-Reflect** | 引入元认知层 | WriteHERE / SciSage |
| **Generator-Critic** | 生成→批判→返修 质量循环 | PaperDebugger |
| **多层 Reflector** | 大纲级→章节级→文档级 反思 | SciSage |
| **递归规划** | 任务分解→类型标注→DAG 调度 | WriteHERE (EMNLP Oral) |
| **DSPy 编译优化** | 声明式签名+自动优化器 | Stanford NLP |

---

## API 端点

### 论文管理

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/papers` | GET | 论文列表 |
| `/api/papers` | POST | 创建论文 |
| `/api/papers/{id}` | GET | 论文详情 |
| `/api/papers/{id}` | PUT | 更新论文 |
| `/api/papers/{id}` | DELETE | 删除论文 |
| `/api/papers/upload` | POST | 上传论文文件 |
| `/api/papers/{id}/outline` | GET | 获取大纲 |
| `/api/papers/{id}/outline/generate` | POST | AI 生成大纲 |
| `/api/papers/{id}/sections/{sid}/generate` | POST | 生成章节内容 |
| `/api/papers/{id}/sections/{sid}/format` | POST | 修正章节格式 |

### 文献与知识图谱

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/literature/search` | POST | 文献搜索 |
| `/api/literature/{id}` | GET | 文献详情 |
| `/api/papers/{pid}/literature` | POST | 添加文献到论文 |
| `/api/knowledge-graph/generate` | POST | 生成知识图谱 |
| `/api/knowledge-graph/query` | POST | GraphRAG 问答 |
| `/api/knowledge-graph/communities` | GET | 社区检测 |

### 聊天与报告

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/papers/{pid}/chat` | POST | 论文对话 |
| `/api/papers/{pid}/chat/history` | GET | 对话历史 |
| `/api/reports` | GET | 资讯列表 |
| `/api/reports/daily` | GET | 日报 |
| `/api/reports/weekly` | GET | 周报 |
| `/api/reports/monthly` | GET | 月报 |
| `/api/workflow/execute` | POST | 执行工作流 |

### 系统

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/settings` | GET/PUT | 用户设置 |
| `/api/models` | GET | 可用模型列表 |
| `/ws/status` | WS | 状态推送 |

认证方式：请求头 `X-API-Key`

---

## 项目结构

```
project-root/
├── src/agents_v2/               # 后端 Agent 系统
│   ├── api_server.py            # aiohttp HTTP 服务入口
│   ├── base_agent.py            # Agent 基类 (BaseAgent, LLMConfig)
│   ├── config.py                # YAML 配置 + 16 模型注册表
│   ├── api/                     # RESTful API 路由模块
│   │   ├── paper_api.py         # 论文/文献/聊天 API
│   │   ├── reports_api.py       # 报告/资讯 API
│   │   └── knowledge_graph_api.py # 知识图谱 API
│   ├── unified/                 # 统一编排框架
│   │   └── master_supervisor.py # MasterSupervisor 多阶段编排
│   ├── paper_agents/            # 论文流水线 Agent
│   │   ├── thesis_agent.py      # 选题 Agent
│   │   ├── outline_agent.py     # 大纲 Agent
│   │   ├── draft_writer.py      # 初稿 Agent
│   │   ├── editor_agent.py      # 编辑 Agent
│   │   └── reviewer_agent.py    # 审稿 Agent
│   ├── writing/                 # 写作 Agent
│   │   ├── outline_generator.py # 大纲生成
│   │   ├── draft_generator.py   # 初稿撰写
│   │   ├── smart_reviser.py     # 智能修订 + 语言润色
│   │   ├── report_refiner.py    # 多轮精炼
│   │   └── literature_review.py # 文献综述
│   ├── problem_oriented/        # 问题诊断 Agent
│   │   ├── language_polisher.py # 语言润色
│   │   └── plagiarism_checker.py # 查重检测
│   ├── qa/                      # 问答与报告 Agent
│   │   ├── paper_search.py      # 多源论文搜索
│   │   ├── daily_watcher.py     # 每日监控
│   │   ├── weekly_report.py     # 周报生成
│   │   └── monthly_report.py    # 月报生成
│   ├── search/                  # 学术搜索引擎适配器
│   │   ├── arxiv_search.py      # arXiv API
│   │   ├── pubmed_search.py     # PubMed API
│   │   └── semantic_scholar.py  # Semantic Scholar API
│   ├── knowledge_graph/         # 知识图谱系统
│   │   ├── entity_extractor.py  # 实体提取
│   │   ├── graphrag.py          # GraphRAG 问答
│   │   └── community_detection.py # 社区检测
│   ├── memory/                  # 记忆系统 (短期/长期/情景)
│   ├── retrieval/               # RAG 检索增强管线
│   ├── tools/                   # 工具系统 (PDF 解析/引文提取/图表)
│   └── langgraph_workflow/      # LangGraph 工作流定义
├── frontend/                    # 前端 React 应用
│   └── src/
│       ├── pages/               # 9 个页面组件
│       │   ├── WritingPage.jsx  # 写作工作台
│       │   ├── LiteraturePage.jsx # 文献浏览器
│       │   ├── AIAssistantPage.jsx # AI 对话
│       │   └── ...
│       ├── components/          # 通用组件
│       ├── store/               # Zustand 状态管理
│       └── services/api.js      # Axios API 客户端
├── docs/                        # 中文文档
│   ├── 开发文档/
│   │   ├── 框架审查与修正报告.md
│   │   ├── 论文Agent前沿开发报告.md
│   │   └── 错误与解决方案.md
│   └── 01_项目概述/
├── tests/                       # 单元/集成测试
├── docker-compose.yml           # 7 服务完整栈
├── Dockerfile                   # 3 构建目标 (runtime/gpu/light)
├── config.yaml                  # YAML 配置文件
├── requirements.txt             # Python 依赖
└── CLAUDE.md                    # 项目指令 + 错误码文档
```

---

## 开发路线图

### Phase 1: 核心写作流水线 (MVP)

- [x] 统一 Agent 基类 + LLMConfig
- [x] 多源搜索 Agent（arXiv / PubMed / Semantic Scholar）
- [x] 大纲生成 + 初稿撰写 Agent
- [x] 语言润色 + 智能修订 Agent
- [x] aiohttp API 服务 + 前端写作工作台
- [ ] SSE 流式聊天端点

### Phase 2: 质量保障体系

- [x] CircuitBreaker 熔断保护
- [ ] Reviewer Agent 结构化评审
- [ ] QualityEvaluator 7 维度评分
- [ ] Generator-Critic 写作循环
- [ ] 完整 AuditTrail 审计

### Phase 3: 高级功能

- [ ] SciSage 式多层 Reflector 反思机制
- [ ] GPT Researcher 式树状深度文献探索
- [ ] Citation Manager 引用验证
- [ ] Methodology Advisor 方法论指导
- [ ] Plagiarism Checker 查重集成
- [ ] 知识图谱交互式可视化

### Phase 4: 产品化

- [ ] 编辑器内嵌（Overleaf / VS Code 插件）
- [ ] 版本管理 + Diff 视图
- [ ] 多人协作编辑
- [ ] 多模型 LLM Router 优化
- [ ] 流式 SSE 响应全端点
- [ ] Docker Compose 生产部署
- [ ] 用户偏好学习 + 风格自适应

---

## 支持的 LLM 提供商

| 提供商 | 模型数 | 说明 |
|--------|:------:|------|
| **OpenAI** | 4 | GPT-4o, GPT-4, GPT-3.5 系列 |
| **Anthropic** | 2 | Claude Opus 4, Claude Sonnet 4 |
| **MiniMax** | 3 | MiniMax-M2.7, M1 系列 |
| **DeepSeek** | 2 | DeepSeek-R1, V3 |
| **Qwen (阿里)** | 3 | Qwen-Max, Plus, Turbo |
| **GLM (智谱)** | 2 | GLM-4, GLM-4-Flash |

---

## 前沿参考

本项目的设计与以下 2025 年学术论文 Agent 系统的最新研究成果保持一致：

| 系统 | 核心贡献 |
|------|----------|
| **PaperDebugger** (NUS) | Overleaf 内嵌多 Agent + Diff 补丁 + MCP 协议 |
| **WriteHERE** (KAUST) | 异构递归规划，EMNLP 2025 Outstanding Paper |
| **SciSage** | 三层 Reflector 边写边反思，引用 F1 提升 32% |
| **Agent Laboratory** (AMD+JHU) | 四角色自主科研流水线，成本降 84% |
| **GPT Researcher** (Columbia) | 树状递归深度研究 + 20+ 来源聚合 |
| **STORM** (Stanford) | 多专家对话模拟 + 多源信息整合写作 |

更多详细信息见 [论文Agent前沿开发报告](docs/开发文档/论文Agent前沿开发报告.md)。

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [论文Agent开发文档](docs/开发文档/论文Agent开发文档.md) | 主开发文档（需求 + 架构 + 实现 + 最佳实践） |
| [论文Agent前沿开发报告](docs/开发文档/论文Agent前沿开发报告.md) | 40+ Agent 框架调研 + Harness 设计 + 开发路线图 |
| [框架审查与修正报告](docs/开发文档/框架审查与修正报告.md) | 项目架构审计 + 8 项修正 + 改进建议 |
| [API 文档](docs/开发文档/API文档_完整版.md) | 完整 REST API 端点 + 接口对照表 |
| [错误与解决方案](docs/开发文档/错误与解决方案.md) | 错误码分类 + 调试指南 |
| [文档目录](docs/README.md) | 全部 26 份文档索引 |

---

## 许可证

MIT License

**最后更新**: 2026-05-01
