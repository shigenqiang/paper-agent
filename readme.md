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

### 配置 API Key

```bash
cp .env.example .env
# 编辑 .env 填入以下配置
```

**LLM 配置 (.env)**：
```bash
LLM_PROVIDER=openai
LLM_MODEL=minimax-m2.7
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

OPENAI_API_KEY=sk-cp-xxxxx
ANTHROPIC_API_KEY=sk-cp-xxxxx
```

**Embedding 配置**：`src/agents_v2/embedding/`
- 本地模型：`Qwen3-Embedding-0.6B`
- 当云 API 不可用时，自动回退到本地模型

---

### 后端启动

```bash
# 安装依赖
pip install -r requirements.txt

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
阶段 1: 选题诊断 (Diagnostic)
  问题导向Agent诊断 → LiteratureMapperAgent (串行，先完成获取论文)
                    → TopicRefinerAgent + MethodologyAdvisorAgent (并行)
                    → [HITL: 选题问题严重度 ≥ 0.7 时人工确认]

阶段 2: 选题 (Topic)
  TopicAgent → [HITL: 人工选择课题]

阶段 3: 文献综述 (Literature)
  LiteratureAgent (并行多源搜索: arXiv/PubMed/Semantic Scholar/CrossRef/OpenAlex)
                → Embedding相关性排序 (超时使用原始论文列表)
                → [HITL: 审核综述]

阶段 4: 大纲规划 (Outline)
  OutlineAgent (EnglishFirstMixin) → [HITL: 确认大纲]

阶段 5: 逐章写作 (Writing, Generator-Critic 循环)
  Writer Agent (6章节并行asyncio.gather) → Reviewer Agent → Evaluator
      ↑                                          ↓
      └── 分数无提升(<0.1) 或 迭代≥max ──→ 返修 ──→ [HITL: 每章可选审核]

阶段 6: 综合润色 (Polish)
  Polisher Agent → Citation Manager → Plagiarism Checker → [HITL: 终审]
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
│   ├── api_server.py            # aiohttp HTTP 服务入口 (端口 8000)
│   ├── logging_config.py        # Loguru 日志配置
│   ├── main.py                  # 入口: python -m src.main
│   │
│   ├── core/                    # 核心基础层
│   │   ├── base_agent.py        # BaseAgent 基类
│   │   ├── config.py            # YAML 配置 + 16 模型注册表
│   │   ├── llm_fallback.py      # LLM 降级策略
│   │   ├── react_executor.py    # ReAct 执行器
│   │   └── streaming.py         # SSE 流式输出
│   │
│   ├── citation/                # 统一引用管理 (2026-05 新增)
│   │   ├── formatter.py        # 格式化引用（APA/MLA/GB7714等）
│   │   ├── verifier.py         # DOI 验证和元数据获取
│   │   ├── extractor.py        # 从文本提取引用标记
│   │   ├── tracker.py          # 答案溯源追踪
│   │   └── styles.py           # 引用样式枚举
│   │
│   ├── reports/                 # 统一报告生成 (2026-05 新增)
│   │   ├── base.py            # 基础生成器
│   │   ├── daily.py           # 日报生成
│   │   ├── weekly.py          # 周报生成
│   │   └── monthly.py         # 月报生成
│   │
│   ├── search/                  # 统一搜索编排 (2026-05 新增)
│   │   ├── arxiv_searcher.py  # arXiv 搜索
│   │   ├── pubmed_searcher.py # PubMed 搜索
│   │   ├── semantic_scholar_searcher.py # Semantic Scholar
│   │   ├── openalex_searcher.py # OpenAlex 搜索
│   │   ├── search_orchestrator.py # 搜索编排器
│   │   └── search_result_merger.py # 结果合并去重
│   │
│   ├── qa_service.py           # QA 系统服务 (2026-05 新增)
│   │
│   ├── monitoring/              # 监控与自动优化 (2026-05 新增)
│   │   └── auto_improver.py   # 自动改进器
│   │
│   ├── api/                     # RESTful API 路由模块
│   ├── unified/                 # 统一编排框架
│   ├── paper_agents/            # 论文流水线 Agent
│   ├── paper_search/            # 论文搜索 Agent
│   ├── problem_oriented/        # 问题诊断 Agent
│   ├── writing/                 # 写作 Agent
│   ├── knowledge_graph/         # 知识图谱系统
│   ├── memory/                  # 记忆系统 v4
│   ├── retrieval/               # RAG 检索增强管线
│   ├── langgraph_workflow/      # LangGraph 工作流
│   ├── storage/                 # 存储层
│   ├── routing/                 # 路由选择
│   ├── evaluation/              # 评估与测试
│   ├── monitoring/              # 监控告警
│   ├── scheduler/               # 定时调度
│   ├── sdk/                     # Claude Agent SDK
│   ├── skills/                  # Agent Skills 系统
│   ├── tools/                   # 工具系统
│   └── multimodal/             # 多模态处理
│
├── frontend/                    # 前端 React 应用
│   └── src/
│       ├── pages/               # 页面组件
│       │   ├── HomePage.jsx     # 工作台/仪表盘
│       │   ├── WritingPage.jsx  # 写作工作区
│       │   ├── LiteraturePage.jsx # 文献浏览器
│       │   ├── AIAssistantPage.jsx # AI 对话
│       │   ├── ReportsPage.jsx  # 学术报告
│       │   ├── KnowledgeGraphPage.jsx # 知识图谱
│       │   ├── OutlinePage.jsx  # AI 大纲生成
│       │   ├── FeaturesPage.jsx # 功能导航
│       │   └── SettingsPage.jsx # 设置中心
│       ├── components/          # 通用组件
│       ├── store/               # Zustand 状态管理
│       └── services/api.js      # Axios API 客户端
│
├── docs/                        # 文档
│   ├── implemented/             # 已实现架构
│   ├── plans/                  # 开发计划
│   └── research/                # 技术调研
│
├── tests/                       # 单元/集成测试
├── data/                        # 数据存储目录
├── docker-compose.yml           # 7 服务完整栈
├── Dockerfile                   # 3 构建目标
├── config.yaml                  # YAML 配置文件
├── requirements.txt             # Python 依赖
├── CLAUDE.md                    # 项目指令
└── .env                         # 环境变量配置
```

---

## 开发路线图

### Phase 1: 核心写作流水线 (MVP)
- [x] 统一 Agent 基类 + LLMConfig
- [x] 多源搜索 Agent（arXiv / PubMed / Semantic Scholar / OpenAlex / CrossRef）
- [x] 大纲生成 + 初稿撰写 Agent
- [x] 语言润色 + 智能修订 Agent
- [x] aiohttp API 服务 + 前端写作工作台
- [x] SSE 流式聊天端点

### Phase 2: 质量保障体系
- [x] CircuitBreaker 熔断保护
- [x] Reviewer Agent 结构化评审
- [x] QualityEvaluator 7 维度评分
- [x] Generator-Critic 写作循环
- [x] 完整 AuditTrail 审计
- [x] CheckpointManager 检查点管理

### Phase 3: 高级功能
- [x] 多层 Reflector 反思机制
- [x] GPT Researcher 式树状深度文献探索
- [x] Citation Manager 引用验证
- [x] Methodology Advisor 方法论指导
- [x] Plagiarism Checker 查重集成
- [x] 知识图谱交互式可视化
- [x] 统一记忆系统 v4 (短期/长期/情景)

### Phase 4: 产品化
- [x] 版本管理 + Diff 视图
- [ ] 多人协作编辑
- [ ] 编辑器内嵌（Overleaf / VS Code 插件）
- [x] 多模型 LLM Router 优化
- [x] 流式 SSE 响应全端点
- [ ] Docker Compose 生产部署
- [x] 用户偏好学习 + 风格自适应
- [x] 定时报告 (日报/周报/月报)

## 模块化架构 (2026-05)

项目已重构为模块化架构，提供统一的 API 接口：

### 统一引用管理 `src.agents_v2.citation/`

| 模块 | 功能 |
|------|------|
| `CitationFormatter` | 格式化引用（APA/MLA/GB7714等） |
| `DOIVerifier` | DOI 验证和元数据获取 |
| `CitationExtractor` | 从文本提取引用标记 |
| `CitationTracker` | 答案溯源追踪 |

### 统一报告生成 `src.agents_v2/reports/`

| 模块 | 功能 |
|------|------|
| `DailyReportGenerator` | 日报生成 |
| `WeeklyReportGenerator` | 周报生成 |
| `MonthlyReportGenerator` | 月报生成 |

### 统一搜索 `src.agents_v2/search/`

| 模块 | 功能 |
|------|------|
| `ArxivSearcher` | arXiv 搜索 |
| `PubmedSearcher` | PubMed 搜索 |
| `SemanticScholarSearcher` | Semantic Scholar 搜索 |
| `OpenAlexSearcher` | OpenAlex 搜索 |
| `SearchOrchestrator` | 搜索编排器 |
| `SearchResultMerger` | 结果合并去重 |

---

## 论文字数与上下文材料加载分析

**模型**: MiniMax-M2.7（上下文 ~32K tokens）

### 上下文窗口约束

| 内容类型 | 估算方式 |
|---------|---------|
| 中文文本 | ~1.8 tokens/字符 |
| 英文文本 | ~2.5 tokens/词 |
| 安全系数 | 80%（预留 prompt 和响应空间）→ 有效可用 ~25K tokens |

### 论文规模与材料配比

**10000字论文基准分析**

| 内容类型 | 字数/数量 | tokens | 占比 |
|---------|----------|--------|------|
| 论文正文 | 10000字 | ~18000 | 60% |
| 参考文献元数据(30篇) | ~3000字 | ~3000 | 10% |
| Prompt/系统 | - | ~4000 | 15% |
| 响应缓冲 | - | ~3000 | 10% |
| **总计** | - | **~28000** | 100% |

### 按论文字数的材料加载建议

| 论文字数 | 建议加载篇数 | 参考文献tokens | 占比 | 状态 |
|---------|-------------|---------------|------|------|
| 5000字 | 15篇 | ~1500 | 8% | ✅ |
| 8000字 | 25篇 | ~2500 | 10% | ✅ |
| 10000字 | 30篇 | ~3000 | 10% | ✅ 建议上限 |
| 15000字 | 30篇 | ~3000 | 7% | ✅ 上限 |
| 20000字 | 30篇 | ~3000 | 5% | ✅ 上限 |

### Polish阶段性能瓶颈（10000字论文，104篇文献）

| 操作 | 耗时 | 占比 | 瓶颈 |
|-----|------|------|------|
| `_run_citation_processor` | ~152秒 | 49% | 104篇文献处理超时 |
| `_run_language_polisher` | ~89秒 | 28% | JSON解析失败重试 |
| 连贯性检查 | ~73秒 | 23% | 正常 |
| **总计** | **~314秒** | 100% | 远超目标60秒 |

**根因**: 104篇引用超载，导致 ReferenceProcessorAgent 和 LLM 插入引用超时。

### 优化方案

| 方案 | 措施 | 预期效果 |
|-----|------|---------|
| A: 硬性限制引用数量 | `papers[:30]` | 引用处理 152秒→50秒 |
| B: 限制 max_tokens 上限 | `min(max_tokens, 8192)` | 避免输出截断 |
| C: 跳过长文本完整润色 | `len > 15000` 跳过 | 节省~90秒 |

### 动态加载策略

```python
def get_recommended_paper_count(paper_chars: int) -> int:
    """根据论文长度推荐参考文献数量"""
    # 每篇参考约100 tokens，预留40%空间给参考文献
    available_ref_tokens = paper_chars * 1.8 * 0.4
    recommended = int(available_ref_tokens / 100)
    return min(recommended, 30)  # 上限30篇
```

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

**最后更新**: 2026-05-04
