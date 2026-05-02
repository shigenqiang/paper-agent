# 论文Agent开发文档

> 智能论文调研与写作系统 — Harness驱动的多Agent编排系统
> 融合：实际代码库状态 + 前沿技术调研 + Agent Harness设计范式

版本: 8.2
更新日期: 2026-05-03
状态: ✅ 与代码库一致

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [系统架构：Harness驱动的多Agent编排](#3-系统架构harness驱动的多agent编排)
4. [Agent Loop 设计模式](#4-agent-loop-设计模式)
5. [后端源码结构](#5-后端源码结构)
6. [LangGraph 工作流](#6-langgraph-工作流)
7. [API 接口文档](#7-api-接口文档)
8. [前端架构](#8-前端架构)
9. [论文写作 Pipeline](#9-论文写作-pipeline)
10. [论文搜索与RAG检索](#10-论文搜索与rag检索)
11. [定时报告](#11-定时报告)
12. [知识图谱](#12-知识图谱)
13. [记忆系统](#13-记忆系统)
14. [配置系统](#14-配置系统)
15. [部署架构](#15-部署架构)
16. [测试覆盖](#16-测试覆盖)
17. [开发路线图](#17-开发路线图)
18. [前沿技术参考](#18-前沿技术参考)

---

## 1. 项目概述

### 1.1 目标

构建一个 **Harness驱动的多Agent论文调研与写作系统**，为高校学生提供从选题诊断、文献调研、大纲规划、逐章写作、修订润色到格式输出的全流程 AI 辅助。

系统以 LangGraph StateGraph 为编排核心，借鉴 2025-2026 年前沿论文 Agent 系统（SciSage 的多层反思、WriteHERE 的异构递归规划、PaperDebugger 的 Diff 补丁机制、Agent Laboratory 的自主科研流水线）的设计理念，通过 **Evaluator + Checkpoint + CircuitBreaker + HITL** 四层 Harness 保障输出质量。

### 1.2 核心功能

| 功能 | 说明 | 状态 |
|------|------|------|
| 论文搜索 | 6+ 学术数据源并行搜索、去重排序 | ✅ |
| 论文写作 | 选题→大纲→初稿→修订→润色→评审 Pipeline | ✅ |
| 论文修改 | 智能改稿、多轮精炼、语言润色 | ✅ |
| 定时报告 | 每日/每周/每月学术报告自动生成 | ✅ |
| 对话问答 | 基于论文的智能问答与比较分析 | ✅ |
| 知识图谱 | 论文关系网络可视化、GraphRAG 问答 | ✅ |
| 记忆系统 | 短期/长期/情景记忆，遗忘曲线+偏好学习 | ✅ |
| 多模态 | 图表分析、公式识别、图文联合检索 | ✅ |
| RAG 检索 | Self-RAG、HyDE、Cross-Encoder 重排序 | ✅ |

### 1.3 设计原则

| 原则 | 说明 | 借鉴来源 |
|------|------|---------|
| Harness 驱动 | Evaluator + Checkpoint + CircuitBreaker + HITL 四层质量保障 | Agent Harness 范式 |
| 模块化架构 | 每个功能独立 Agent，便于扩展 | Anthropic Building Effective Agents |
| 包装而非重写 | 将现有 Agent 包装为 LangGraph 节点 | 本项目实践 |
| 异步优先 | 使用 async/await 处理 IO 密集任务 | aiohttp 架构 |
| 降级策略 | JSON 解析失败时提供降级输出 | 容错设计 |
| Human-in-the-Loop | 关键节点支持人工审核介入 | PaperDebugger Diff 补丁 |

### 1.4 与现有工具的核心差异

| 维度 | 现有论文工具 | Paper Agent |
|------|-------------|-------------|
| Agent 模式 | 单一 LLM 调用 | **多 Agent 协作 + Harness 质量保障** |
| 写作范式 | "一次生成" | **Generator-Critic 循环 + 多层反思** |
| 人机协作 | 文本编辑器 | **Diff 补丁 + 阶段性审批 (HITL)** |
| 容错能力 | 无 | **CircuitBreaker + Checkpoint 恢复** |
| 可追溯性 | 无 | **完整 AuditTrail + Journal 日志** |
| 个性化 | 无 | **用户偏好学习 + 风格自适应** |

### 1.5 大学生论文痛点与系统映射

基于麦可思研究院 2025 年调查（3145 份有效答卷），本系统针对性解决以下核心痛点：

| 痛点 | 数据 | 系统解决方案 |
|------|------|-------------|
| 选题困难 | 找到"创新+可行+有价值"的选题极难 | TopicAgent + ResearchGapAnalyzer |
| 文献综述效率低 | 需要阅读大量论文 | 多源搜索引擎 + 自动综述生成 |
| 结构化写作难 | "大白话"难以达标 | 多层大纲 + Generator-Critic循环 |
| AI检测焦虑 | 同一文章不同平台检测结果相差46% | 风格多样化 + 人工化润色 |
| 导师指导盲区 | 导师身在国外或跨校区 | AI Agent 全程陪伴式指导 |
| 格式规范繁琐 | 参考文献格式、排版、查重 | 自动格式化 + 引用验证 |

---

## 2. 技术栈

### 2.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主语言 |
| **aiohttp** | >=3.8.0 | 异步 HTTP 服务器（端口 8000） |
| **LangGraph** | StateGraph | Agent 编排，有向无环图 + Checkpoint + HITL |
| **LangChain** | langchain-core >=0.1.0 | LLM 抽象层 |
| **langchain-openai** | >=0.0.5 | OpenAI 兼容 LLM 连接器 |
| **openai** | >=1.0.0 | OpenAI SDK（直接调用） |
| **Pydantic** | >=2.0.0 | 数据验证与模型定义 |
| **orjson** | >=3.8.0 | 高性能 JSON 处理 |
| **pdfplumber** | >=0.10.0 | PDF 解析 |
| **arxiv** | >=1.4.0 | arXiv API 客户端 |
| **biopython** | >=1.81 | PubMed API 客户端 |
| **requests** | >=2.28.0 | 同步 HTTP 请求 |
| **pyyaml** | >=6.0 | YAML 配置解析 |
| **python-dotenv** | >=1.0.0 | .env 环境变量加载 |

### 2.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | ^18.2.0 | UI 框架 |
| **Vite** | ^5.0.8 | 构建工具 |
| **Ant Design** | ^5.12.0 | UI 组件库 |
| **Zustand** | ^4.4.7 | 状态管理 |
| **React Router** | ^6.20.0 | 客户端路由 |
| **Axios** | ^1.6.2 | HTTP 客户端 |
| **Tailwind CSS** | ^3.3.6 | 工具类 CSS |
| **@uiw/react-md-editor** | ^4.1.0 | Markdown 编辑器 |
| **react-markdown** | ^10.1.0 | Markdown 渲染 |
| **katex** | ^0.16.45 | 数学公式渲染 |
| **@ant-design/graphs** | ^2.1.1 | 图谱可视化 |
| **@antv/g6** | ^5.1.0 | 图可视化引擎 |

### 2.3 支持的 LLM 模型（17 个，6 个提供商）

| 提供商 | 模型 | 推荐用途 |
|--------|------|---------|
| **MiniMax** | minimax-m2, minimax-m2.7 | 默认模型，性价比高 |
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o3-mini | 通用推理 |
| **Anthropic** | claude-sonnet-4-6, claude-opus-4-7, claude-haiku-4-5 | 长文本写作、深度分析 |
| **Qwen（阿里）** | qwen-max, qwen-plus, qwen-turbo | 中文内容处理 |
| **DeepSeek** | deepseek-chat, deepseek-reasoner | 数学推理、低成本 |
| **GLM（智谱）** | glm-4, glm-4-plus | 中文通用 |

**模型选择矩阵**（基于前沿调研）：

| 任务类型 | 推荐模型 | 选择理由 |
|---------|---------|---------|
| 问题路由/分类 | DeepSeek-V3 / Haiku 4.5 | 低成本、低延迟 |
| 论文搜索/查询 | Claude Sonnet 4.6 | 平衡质量与成本 |
| 论文深度分析 | Claude Opus 4.7 | 最强推理，200K上下文 |
| 论文初稿写作 | Claude Opus 4.7 | 长文本质量最高 |
| 数学推理 | DeepSeek-R1 | R1 强化推理 |
| 中文内容处理 | Qwen 3.5-Max | 中文能力顶级 |
| 论文润色/格式检查 | DeepSeek-V3 / Haiku 4.5 | 简单任务低成本 |

### 2.4 存储

| 存储类型 | 说明 | 状态 |
|---------|------|------|
| **JSON 文件持久化** | 论文/文献数据存储到 `data/papers_storage.json` | ✅ |
| **内存缓存** | LRU 缓存，TTL 3600s | ✅ |
| **PostgreSQL** | 关系型数据库（可选） | ✅ |
| **Redis** | 缓存层（可选） | ✅ |
| **Neo4j** | 图数据库（可选，知识图谱） | ✅ |

### 2.5 基础设施

| 组件 | 用途 | 状态 |
|------|------|------|
| **Docker** | 多阶段构建（runtime / runtime-gpu / runtime-light） | ✅ |
| **Docker Compose** | 7 个服务编排 | ✅ |
| **Kubernetes** | K8s 部署清单 | ✅ |
| **Nginx** | 前端静态文件服务 + 反向代理 | ✅ |
| **PostgreSQL 15** | 关系型数据库（可选） | ✅ |
| **Redis 7** | 缓存层（可选） | ✅ |
| **Neo4j 5** | 图数据库（可选，知识图谱） | ✅ |
| **Prometheus + Grafana** | 监控（可选，monitoring profile） | ✅ |

---

## 3. 系统架构：Harness驱动的多Agent编排

### 3.1 三层架构范式

本系统遵循 2025 年 Agent 系统设计的核心范式 — **Framework → Runtime → Harness**：

```
┌──────────────────────────────────────────────────────┐
│              HARNESS (评估 & 质量保障)                 │
│  Evaluator (7维评分) | CheckpointManager | CircuitBreaker
│  HITL (人工审核) | AuditTrail (审计溯源)              │
├──────────────────────────────────────────────────────┤
│              RUNTIME (执行引擎)                        │
│  LangGraph StateGraph | 状态管理 | 重试/降级          │
│  并行调度 | Checkpoint持久化 | 流式SSE                │
├──────────────────────────────────────────────────────┤
│              FRAMEWORK (构建层)                        │
│  Prompt | 工具(31文件) | 记忆(26文件) | 流程控制      │
│  Agent组合 | 搜索引擎(6源) | 知识图谱 | RAG管道       │
└──────────────────────────────────────────────────────┘
```

### 3.2 分层架构详图

```
┌─────────────────────────────────────────────────────────────────┐
│  前端层 (React 18 + Vite, 端口 3000/5173)                        │
│  9 个页面 + 9 个 Zustand Store + Axios API 客户端                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  API 网关层 (aiohttp, 端口 8000)                                  │
│  REST API (49 端点) + X-API-Key 认证 + 速率限制                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  编排层 (LangGraph StateGraph)                                   │
│  UnifiedWorkflow: 5 条自动路由路径                                 │
│  MasterSupervisor → PhaseSupervisor                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  专业 Agent 层  │ │  Harness 层    │ │  基础设施层     │
│  20 个节点      │ │  Evaluator     │ │  记忆系统       │
│  搜索/写作/报告 │ │  CircuitBreaker│ │  搜索引擎       │
│  QA/修订       │ │  Checkpoint    │ │  知识图谱       │
│                │ │  HITL          │ │  LLM Router     │
│                │ │  AuditTrail    │ │                 │
└────────────────┘ └────────────────┘ └────────────────┘
```

### 3.3 五条工作流路径

系统通过意图分类自动路由到 5 条工作流：

| 路径 | 节点序列 | 说明 |
|------|---------|------|
| **Search** | router → crawler → selector → END | 论文搜索筛选 |
| **Writing** | router → memory → crawler → selector → multimodal → kg → outline → write → review → evaluator → END | 完整写作流程 |
| **Report** | router → report_crawl → report_analyze → report_gen → END | 定时报告生成 |
| **QA** | router → qa_search → qa_synthesize → qa_answer → END | 智能问答 |
| **Revision** | router → revise → refine → polish → END | 论文修订润色 |

### 3.4 Agent 协议生态

本系统基于 2026 年四大开放协议标准构建：

| 协议 | 解决的问题 | 本系统应用 |
|------|-----------|-----------|
| **MCP** (Anthropic) | Agent ↔ 工具/数据源 标准化连接 | Arxiv/PubMed/Semantic Scholar MCP Server |
| **A2A** (Google/Linux基金会) | Agent ↔ Agent 标准通信 | 搜索Agent→分析Agent→写作Agent 任务分发 |
| **Agent Skills** (Anthropic) | 能力模块化封装与复用 | paper-search/paper-analysis/report-generation |
| **AG-UI** (CopilotKit) | Agent ↔ 前端 实时交互 | 流式展示搜索进度、生成进度 |

---

## 4. Agent Loop 设计模式

本系统融合了 2025-2026 年前沿论文 Agent 的核心设计模式：

### 4.1 ReAct（Reason + Act）— 基础循环

```
Observe → Think → Act → Observe → Think → Act → ...
```

最基础的 Agent 循环，用于搜索、问答等单步任务。实现在 `unified/agent_loop.py`。

### 4.2 Plan-Execute-Reflect — 升级循环

```
Plan (制定计划) → Execute (执行步骤) → Reflect (反思结果) → Replan (调整计划) → ...
```

引入元认知层，借鉴 SciSage 和 WriteHERE 的核心机制。用于论文写作全流程。

### 4.3 Generator-Critic 循环

```
Generator (生成草稿) → Critic (批判评估)
    ├── PASS → 输出
    └── FAIL → 反馈 → Generator (修改)
```

PaperDebugger 的 Reviewer + Enhancer 配对模式。用于逐章写作阶段。

### 4.4 多层 Reflector（SciSage 范式）

```
Outline-Level Reflector → Section-Level Reflector → Document-Level Reflector
```

不同粒度层次的反思机制，从宏观结构到微观表达。实现在 `writing/reflection_engine.py`。

### 4.5 异构递归规划（WriteHERE 范式）

```
Task Analysis → Type Tagging (检索/推理/写作) → Recursive Decomposition → DAG Schedule
```

根据任务类型动态分解为原子任务，用 DAG 管理依赖关系。实现在 `langgraph_workflow/unified_workflow.py` 的条件路由。

### 4.6 树状递归研究（GPT Researcher 范式）

```
Root Topic → Generate Sub-Questions (广度)
  → For each Sub-Q: Search & Extract (深度)
    → If depth > 1: Recursive Decompose (更深层)
  → Aggregate → Filter → Synthesize → Final Report
```

用于文献综述模块的深度研究模式。

### 4.7 Harness 介入模式

```
Agent执行 → Checkpoint保存 → 质量评估 → [HITL中断] → 人工审核 → 恢复执行
                                    │
                                    └── 质量不达标 → CircuitBreaker → 降级/重试
```

---

## 5. 后端源码结构

### 5.1 顶层目录

```
src/agents_v2/
├── api/                    # REST API 路由（5 个文件，49 个端点）
├── base/                   # 基础 Agent 框架
├── core/                   # 核心基础设施（11 个文件）
├── evaluation/             # Agent 评估框架
├── intent/                 # 意图分类系统
├── knowledge_graph/        # 知识图谱系统（10 个文件）
├── langgraph_workflow/     # LangGraph 工作流（核心）
│   ├── nodes/              # 20 个工作流节点
│   ├── observability/      # 可观测性
│   ├── unified_workflow.py # 统一工作流入口
│   ├── workflow.py         # 工作流构建器
│   ├── state.py            # 状态定义
│   ├── edges.py            # 条件路由
│   └── runner.py           # CLI 运行入口
├── memory/                 # 记忆系统（26 个文件）
├── multimodal/             # 多模态处理
├── monitoring/             # 系统监控
├── paper_agents/           # 论文 Pipeline Agent
├── performance/            # 性能优化
├── problem_oriented/       # 问题导向 Agent（9 个）
├── qa/                     # QA 系统
├── retrieval/              # RAG 检索管道（24 个文件）
├── routing/                # 意图路由
├── scheduler/              # 任务调度
├── sdk/                    # Claude Agent SDK 框架
├── search/                 # 学术搜索引擎
├── skills/                 # Agent Skills（SKILL.md 标准）
├── state/                  # 状态管理
├── tools/                  # 工具系统（31 个文件）
├── unified/                # 统一编排层（16 个文件）
└── writing/                # 写作 Agent（18 个文件）
```

### 5.2 核心模块详解

#### API 层 (`api/`)

| 文件 | 端点数 | 说明 |
|------|--------|------|
| `paper_api.py` | 20 | 论文 CRUD、大纲生成、内容生成、文献管理、聊天 |
| `reports_api.py` | 8 | 报告 CRUD + 按类型筛选 |
| `knowledge_graph_api.py` | 9 | 知识图谱生成、查询、社区发现、路径分析 |
| `workflow_api.py` | 4 | 统一工作流执行入口 |
| `gateway.py` | 8 | Agent/Memory/Skill/Audit 管理（/v1/ 前缀） |

#### 核心基础设施 (`core/`)

| 文件 | 说明 |
|------|------|
| `base_agent.py` | Agent 基类 |
| `config.py` | YAML 配置加载、验证、模型注册表（17 个模型） |
| `config_manager.py` | 配置管理器 |
| `exceptions.py` | 自定义异常 |
| `plugins.py` | 插件系统 |
| `rbac.py` | 基于角色的访问控制 |
| `security.py` | 安全工具 |
| `streaming.py` | 流式响应支持 |
| `user_manager.py` | 用户管理 |
| `validators.py` | 输入验证器 |

#### 统一编排层 (`unified/`)

| 文件 | 说明 | Harness 角色 |
|------|------|-------------|
| `master_supervisor.py` | 全局协调器 | 编排层 |
| `phase_supervisor.py` | 阶段协调器（parallel/sequential/adaptive） | 编排层 |
| `state_model.py` | 全局状态模型（PaperState） | Runtime |
| `intent_router.py` | 意图路由 | 编排层 |
| `agent_loop.py` | Agent 循环（ReAct 模式） | Runtime |
| `circuit_breaker.py` | 熔断器模式 | **Harness** |
| `cache.py` | 缓存管理 | Runtime |
| `error_handler.py` | 错误处理 | Runtime |
| `error_recovery.py` | 错误恢复策略 | **Harness** |
| `execution_replay.py` | 执行重放 | Runtime |
| `flow_monitoring.py` | 流程监控 | **Harness** |
| `input_security.py` | 输入安全 | Harness |
| `monitoring.py` | 监控 | **Harness** |
| `output_manager.py` | 输出管理 | Runtime |
| `translation.py` | 翻译 | 工具 |

#### 工作流节点 (`langgraph_workflow/nodes/`)

| 节点 | 文件 | 工作流 |
|------|------|--------|
| RouteNode | `router.py` | 入口路由 |
| CrawlerAgent | `crawler.py` | Search, Writing |
| SelectorAgent | `selector.py` | Search, Writing |
| MemoryNode | `memory.py` | Writing（召回/存储） |
| MultimodalNode | `multimodal.py` | Writing（可选） |
| KnowledgeGraphNode | `knowledge_graph.py` | Writing（可选） |
| OutlineAgent | `outline.py` | Writing |
| WriterAgent | `writer.py` | Writing |
| ReviewerAgent | `reviewer.py` | Writing |
| EvaluatorNode | `evaluator.py` | Writing（可选） |
| ReportCrawlNode | `report_crawl.py` | Report |
| ReportAnalyzeNode | `report_analyze.py` | Report |
| ReportGenNode | `report_gen.py` | Report |
| QASearchNode | `qa_search.py` | QA |
| QASynthesizeNode | `qa_synthesize.py` | QA |
| QAAnswerNode | `qa_answer.py` | QA |
| ReviseNode | `revise.py` | Revision |
| RefineNode | `refine.py` | Revision |
| PolishNode | `polish.py` | Revision |

---

## 6. LangGraph 工作流

### 6.1 统一工作流入口

**文件**: `src/agents_v2/langgraph_workflow/unified_workflow.py`

`UnifiedWorkflow` 类基于 LangGraph `StateGraph` 构建，通过单一入口自动路由到 5 条工作流路径。

### 6.2 工作流状态

```python
class PaperAgentState(TypedDict):
    query: str                          # 用户查询
    intent: str                         # 意图分类结果
    papers: list                        # 搜索到的论文
    selected_papers: list               # 筛选后的论文
    outline: dict                       # 生成的大纲
    draft: str                          # 撰写的草稿
    review_result: dict                 # 审查结果
    quality_score: float                # 质量评分
    memory_context: list                # 记忆上下文
    multimodal_data: dict               # 多模态数据
    kg_data: dict                       # 知识图谱数据
    report: dict                        # 报告结果
    answer: str                         # QA 答案
    revised_text: str                   # 修订文本
    final_output: str                   # 最终输出
```

### 6.3 工作流图

```
                    ┌──────────┐
                    │  Router  │
                    └────┬─────┘
         ┌───────┬───────┼───────┬───────┐
         ▼       ▼       ▼       ▼       ▼
      Search   Writing  Report    QA   Revision
         │       │       │       │       │
         ▼       ▼       ▼       ▼       ▼
      crawler  memory  crawl   search   revise
         │       │       │       │       │
         ▼       ▼       ▼       ▼       ▼
      selector crawler analyze synthesize refine
         │       │       │       │       │
         ▼       ▼       ▼       ▼       ▼
       [END]  selector  gen    answer   polish
                 │       │       │       │
                 ▼       ▼       ▼       ▼
              outline   [END]   [END]   [END]
                 │
                 ▼
              writing
                 │
                 ▼
              review ──(loop)──▶ writing
                 │
                 ▼
              [END]
```

### 6.4 特性开关

| 开关 | 说明 | 默认 |
|------|------|------|
| `enable_memory` | 启用记忆召回/存储 | True |
| `enable_multimodal` | 启用多模态分析 | False |
| `enable_kg` | 启用知识图谱构建 | False |
| `enable_evaluation` | 启用质量评估 | False |

### 6.5 使用方式

```python
from agents_v2.langgraph_workflow import create_workflow

# 基础使用（无 LLM）
workflow = create_workflow(
    llm=None,
    sources=["arxiv", "semantic_scholar"],
    top_k=20,
    max_iterations=3,
)
result = workflow.run(query="deep learning in medical imaging")

# 高级使用（LLM + 增强检索 + 记忆）
from langchain_openai import ChatOpenAI
workflow = create_workflow(
    llm=ChatOpenAI(model="gpt-4"),
    enable_enhanced_retrieval=True,
    enable_memory=True,
    enable_kg=True,
)
result = workflow.run(query="transformer architecture")
```

### 6.6 性能指标

| 操作 | 耗时 |
|------|------|
| 筛选 100 篇论文 | < 2 秒 |
| 生成大纲（20 篇论文） | < 1 秒 |
| 端到端（10 篇→5 篇→6 节大纲→草稿） | < 3 秒（无 LLM） |

---

## 7. API 接口文档

### 7.1 论文管理 (`paper_api.py`)

#### 论文 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/papers` | 获取论文列表（分页、按状态筛选） |
| POST | `/api/papers` | 创建新论文 |
| GET | `/api/papers/{id}` | 获取论文详情 |
| PUT | `/api/papers/{id}` | 更新论文 |
| DELETE | `/api/papers/{id}` | 删除论文 |
| POST | `/api/papers/upload` | 上传论文文件（md/txt/pdf/docx） |

#### 大纲与内容生成

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/papers/{id}/outline` | 获取论文大纲 |
| POST | `/api/papers/{id}/outline/generate` | AI 生成大纲 |
| POST | `/api/papers/{id}/sections/{sectionId}/generate` | AI 生成章节内容 |
| POST | `/api/papers/{id}/sections/{sectionId}/format` | AI 修正格式/润色 |

#### 文献管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/literature/search` | 搜索文献 |
| GET | `/api/literature/{id}` | 获取文献详情 |
| POST | `/api/papers/{paperId}/literature` | 添加文献到论文 |
| GET | `/api/literature/{id}/citation` | 获取引用格式（APA/MLA/IEEE） |
| POST | `/api/literature/upload` | 上传文献文件并提取元数据 |

#### 聊天

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/papers/{paperId}/chat` | 论文上下文聊天（会话管理） |
| GET | `/api/papers/{paperId}/chat/history` | 获取聊天历史 |

#### 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取用户设置 |
| PUT | `/api/settings` | 更新用户设置 |
| GET | `/api/models` | 获取可用 LLM 模型列表 |

### 7.2 报告管理 (`reports_api.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/reports` | 获取报告列表（按类型和状态筛选） |
| POST | `/api/reports` | 创建报告（异步生成：daily/weekly/monthly） |
| GET | `/api/reports/{id}` | 获取报告详情 |
| PUT | `/api/reports/{id}` | 更新/重新生成报告 |
| DELETE | `/api/reports/{id}` | 删除报告 |
| GET | `/api/reports/daily` | 获取每日报告列表 |
| GET | `/api/reports/weekly` | 获取每周报告列表 |
| GET | `/api/reports/monthly` | 获取每月报告列表 |

### 7.3 知识图谱 (`knowledge_graph_api.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge-graph/literature` | 获取文献知识图谱 |
| POST | `/api/knowledge-graph/generate` | 生成知识图谱 |
| GET | `/api/knowledge-graph/entity/{entityId}` | 获取实体关系 |
| POST | `/api/knowledge-graph/query` | GraphRAG 问答 |
| GET | `/api/knowledge-graph/communities` | 社区发现（leiden/louvain/label_propagation） |
| GET | `/api/knowledge-graph/communities/{communityId}/papers` | 获取社区内论文 |
| GET | `/api/knowledge-graph/centrality` | 节点中心性分析（degree/betweenness） |
| GET | `/api/knowledge-graph/paths` | 路径查找（source → target） |
| GET | `/api/knowledge-graph/entity/{entityId}/neighbors` | 邻域分析（BFS） |

### 7.4 工作流 (`workflow_api.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workflow/execute` | 执行统一工作流（自动路由） |
| POST | `/api/workflow/search` | 搜索工作流 |
| POST | `/api/workflow/report` | 报告工作流 |
| GET | `/api/workflow/status` | 获取工作流状态和特性开关 |

### 7.5 网关 (`gateway.py`)

> 注意：这些端点使用 `/v1/` 前缀，独立于 aiohttp 路由系统。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/agents` | 创建 Agent |
| GET | `/v1/agents/{id}` | 获取 Agent |
| POST | `/v1/agents/{id}/execute` | 执行 Agent 任务 |
| GET | `/v1/memories` | 获取记忆列表 |
| POST | `/v1/memories` | 创建记忆 |
| GET | `/v1/skills` | 获取 Skills 列表 |
| POST | `/v1/skills` | 创建 Skill |
| GET | `/v1/audit` | 获取审计日志 |

### 7.6 系统端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| WS | `/ws/status` | WebSocket 状态推送 |

### 7.7 认证

所有 `/api/` 端点通过 `X-API-Key` 请求头认证。API Key 在 `.env` 文件中配置。

---

## 8. 前端架构

### 8.1 页面结构（9 个页面）

| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | `HomePage.jsx` | 工作台/仪表盘 |
| `/writing` | `WritingPage.jsx` | 写作工作区（34KB，最大页面） |
| `/outline` | `OutlinePage.jsx` | AI 大纲生成 |
| `/literature` | `LiteraturePage.jsx` | 文献浏览器 |
| `/ai-assistant` | `AIAssistantPage.jsx` | AI 对话助手 |
| `/reports` | `ReportsPage.jsx` | 学术报告 |
| `/features` | `FeaturesPage.jsx` | 功能导航 |
| `/knowledge-graph` | `KnowledgeGraphPage.jsx` | 知识图谱可视化（31KB） |
| `/settings` | `SettingsPage.jsx` | 设置中心 |

### 8.2 状态管理（Zustand Store）

| Store | 文件 | 说明 |
|-------|------|------|
| `paperStore` | `paperStore.js` | 论文数据管理 |
| `writingStore` | `writingStore.js` | 写作状态 |
| `literatureStore` | `literatureStore.js` | 文献数据 |
| `chatStore` | `chatStore.js` | 聊天状态 |
| `reportsStore` | `reportsStore.js` | 报告数据 |
| `kgStore` | `kgStore.js` | 知识图谱数据 |
| `assistantStore` | `assistantStore.js` | AI 助手状态 |
| `projectStore` | `projectStore.js` | 项目状态 |
| `uiStore` | `uiStore.js` | UI 状态（主题等） |

### 8.3 组件结构

```
frontend/src/components/
├── layout/           # 布局组件（侧边栏、顶栏）
├── common/           # 通用组件
├── knowledge-graph/  # 知识图谱组件
├── literature/       # 文献组件
└── writing/          # 写作组件
```

---

## 9. 论文写作 Pipeline

### 9.1 Pipeline Agent 列表

| Agent | 文件 | 职责 | 优先级 |
|-------|------|------|--------|
| TopicAgent | `paper_agents/thesis_agent.py` | 选题与研究问题凝练 | P0 |
| OutlineGeneratorAgent | `writing/outline_generator.py` | 大纲生成 | P0 |
| DraftGeneratorAgent | `writing/draft_generator.py` | 初稿撰写 | P0 |
| LiteratureReviewAgent | `writing/literature_review.py` | 文献综述 | P1 |
| ProposalGeneratorAgent | `writing/proposal_generator.py` | 开题报告 | P1 |
| SmartReviserAgent | `writing/smart_reviser.py` | 智能改稿 | P0 |
| ReportRefinerAgent | `writing/report_refiner.py` | 多轮精炼 | P0 |
| LanguagePolisherAgent | `writing/smart_reviser.py` | 语言润色 | P1 |
| ReviewerAgent | `writing/report_refiner.py` | 质量评审 | P1 |

### 9.2 问题导向 Agent（借鉴 PaperDebugger + SciSage）

| Agent | 文件 | 说明 |
|-------|------|------|
| LanguagePolisherAgent | `problem_oriented/language_polisher.py` | 语言润色 |
| PlagiarismCheckerAgent | `problem_oriented/plagiarism_checker.py` | 查重检测 |
| MethodologyAdvisorAgent | `problem_oriented/methodology_advisor.py` | 方法论指导 |
| ResearchGapAnalyzer | `problem_oriented/research_gap_analyzer.py` | 研究空白分析 |
| DiscussionDeepenerAgent | `problem_oriented/discussion_deepener.py` | 讨论深化 |
| LiteratureMapperAgent | `problem_oriented/literature_mapper.py` | 文献图谱 |
| ChartFormatterAgent | `problem_oriented/chart_formatter.py` | 图表格式化 |
| SectionDifferentiatorAgent | `problem_oriented/section_differentiator.py` | 章节差异化 |
| TopicRefinerAgent | `problem_oriented/topic_refiner.py` | 主题精炼 |

### 9.3 写作工具

| 工具 | 文件 | 说明 |
|------|------|------|
| ReflectionEngine | `writing/reflection_engine.py` | 反思引擎（SciSage 多层反思） |
| AnswerQualityChecker | `writing/answer_quality_checker.py` | 答案质量检查 |
| StreamingGenerator | `writing/streaming_generator.py` | 流式生成 |
| GenerationOptimizer | `writing/generation_optimizer.py` | 批量生成优化 |
| CitationGenerator | `writing/citation_generator.py` | 多格式引用生成 |
| SelfRAGWriter | `writing/self_rag_writer.py` | Self-RAG 写作 |
| LogicCoherenceChecker | `writing/logic_coherence_checker.py` | 逻辑连贯性检查 |

### 9.4 6 阶段写作流水线 + Harness 介入点

```
阶段1: 选题诊断
  ├── TopicAgent: 研究空白分析
  ├── TopicRefinerAgent: 选题精炼
  └── [HITL 介入点] ← 人工确认选题

阶段2: 文献综述
  ├── CrawlerAgent: 多源深度检索
  ├── LiteratureReviewAgent: 综述生成
  └── [HITL 介入点] ← 人工审核综述

阶段3: 大纲规划
  ├── OutlineGeneratorAgent: 层级化大纲生成
  ├── MethodologyAdvisorAgent: 方法论匹配
  └── [HITL 介入点] ← 人工确认大纲

阶段4: 逐章写作 (Generator-Critic循环)
  ├── DraftGeneratorAgent: 章节草稿生成
  ├── ReviewerAgent: 结构化审稿
  ├── LanguagePolisherAgent: 语言润色
  └── [HITL 介入点] ← 每章可选审核

阶段5: 综合润色
  ├── LanguagePolisherAgent: 全局语言一致性
  ├── CitationGenerator: 引用验证+格式
  ├── PlagiarismCheckerAgent: 查重+AIGC检测
  └── [HITL 介入点] ← 人工终审

阶段6: 格式输出
  ├── ChartFormatterAgent: 图表规范化
  └── 输出: LaTeX / Word / PDF / Markdown
```

### 9.5 Harness 层设计

#### Evaluator（质量评估器）

```python
class QualityEvaluator:
    dimensions = {
        "structure":   0.20,  # 结构合理性
        "logic":       0.20,  # 逻辑连贯性
        "originality": 0.15,  # 原创性
        "language":    0.15,  # 学术语言
        "citation":    0.15,  # 引用准确性
        "completeness":0.10,  # 内容完整性
        "format":      0.05,  # 格式规范性
    }
```

#### CircuitBreaker（熔断器）

```python
thresholds = {
    "llm_error_rate": 0.3,       # LLM调用错误率 >30% → 熔断
    "consecutive_failures": 5,   # 连续失败5次 → 熔断
    "timeout_seconds": 300,      # 单步超过5分钟 → 熔断
    "cost_limit": 5.0,           # 单次会话超过$5 → 熔断
}
states = ["CLOSED", "OPEN", "HALF_OPEN"]
```

#### HITL Manager（人机协作管理器）

```python
interrupt_points = {
    "after_outline":    "大纲完成后需人工确认",
    "after_literature": "文献综述完成后需审核",
    "after_section":    "每章节完成后可选审核",
    "before_final":     "终稿前需全面审核",
    "on_low_quality":   "质量评分<阈值时强制中断",
}
```

### 9.6 质量门控

```python
QUALITY_GATES = {
    "topic_agent": {"min_candidates": 3, "min_feasibility_score": 0.6},
    "literature_agent": {"min_papers": 10, "min_relevance_threshold": 0.5},
    "thesis_agent": {"min_objectives": 3, "coherence_score_threshold": 0.7},
    "outline_agent": {"min_chapters": 5},
    "writer_agent": {"min_word_count": 500, "required_citations": 3},
}
```

---

## 10. 论文搜索与RAG检索

### 10.1 支持的数据源

| 数据源 | API | 类型 | 优先级 |
|--------|-----|------|--------|
| **arXiv** | export.arxiv.org | 预印本 | P0 |
| **PubMed** | eutils.ncbi.nlm.nih.gov | 学术数据库 | P0 |
| **Semantic Scholar** | api.semanticscholar.org | 学术搜索 | P1 |
| **CrossRef** | api.crossref.org | 元数据 | P1 |
| **DBLP** | api.dblp.org | 计算机文献 | P1 |
| **OpenAlex** | api.openalex.org | 学术知识库 | P1 |

### 10.2 搜索模块结构

```
src/agents_v2/search/
├── base_searcher.py              # 搜索基类、数据结构
├── arxiv_searcher.py             # ArXiv 搜索
├── pubmed_searcher.py            # PubMed 搜索
├── semantic_scholar_searcher.py  # Semantic Scholar 搜索
├── crossref_searcher.py          # CrossRef 搜索
├── dblp_searcher.py              # DBLP 搜索
├── openalex_searcher.py          # OpenAlex 搜索
├── search_factory.py             # 搜索器工厂
├── query_parser.py               # 查询解析器
└── result_merger.py              # 结果合并去重
```

### 10.3 RAG 检索管道

```
src/agents_v2/retrieval/
├── enhanced_retrieval.py         # 增强检索
├── hyde.py                       # HyDE（假设性文档嵌入）
├── self_rag.py                   # Self-RAG
├── iterative_retriever.py        # 迭代检索
├── cross_encoder_reranker.py     # Cross-Encoder 重排序
├── query_expander.py             # 查询扩展
├── query_rewriter.py             # 查询改写
├── query_classifier.py           # 查询分类
├── deduplication.py              # 去重
└── ...                           # 共 24 个文件
```

---

## 11. 定时报告

### 11.1 报告类型

| 类型 | Agent | 文件 | 时间范围 | 优先级 |
|------|-------|------|---------|--------|
| 每日报告 | DailyWatcher | `qa/daily_watcher.py` | 30 天 | P0 |
| 每周报告 | WeeklyReportGenerator | `qa/weekly_report.py` | 7 天 | P0 |
| 每月报告 | MonthlyReportGenerator | `qa/monthly_report.py` | 30 天 | P0 |
| 论文快讯 | PaperFlash | `qa/paper_flash.py` | 实时 | P1 |

### 11.2 报告对比

| 特性 | 每日报告 | 每周报告 | 每月报告 | 论文快讯 |
|------|---------|---------|---------|---------|
| 时间范围 | 30 天 | 7 天 | 30 天 | 当天 |
| 论文处理量 | 20-50 篇 | 50-200 篇 | 100-500 篇 | 5-10 篇 |
| 分析深度 | 浅 | 中 | 深 | 浅 |
| 生成速度 | <60s | <180s | <300s | <30s |

---

## 12. 知识图谱

### 12.1 模块结构

```
src/agents_v2/knowledge_graph/
├── kg_service.py          # 知识图谱服务入口
├── kg_graphrag.py         # GraphRAG 实现
├── kg_schema.py           # 图谱 Schema 定义
├── kg_extractors.py       # 实体/关系抽取
├── kg_community.py        # 社区发现（Leiden/Louvain）
├── kg_embeddings.py       # 图嵌入
├── kg_hybrid_retriever.py # 混合检索
├── kg_summarizer.py       # 图谱摘要
├── kg_vector_store.py     # 向量存储
└── kg_batch_operations.py # 批量操作
```

### 12.2 功能

| 功能 | API 端点 | 说明 |
|------|---------|------|
| 图谱生成 | POST `/api/knowledge-graph/generate` | 从论文/文献生成知识图谱 |
| GraphRAG 问答 | POST `/api/knowledge-graph/query` | 基于图谱的问答 |
| 社区发现 | GET `/api/knowledge-graph/communities` | Leiden/Louvain/Label Propagation |
| 中心性分析 | GET `/api/knowledge-graph/centrality` | Degree/Betweenness 中心性 |
| 路径查找 | GET `/api/knowledge-graph/paths` | 两节点间路径 |
| 邻域分析 | GET `/api/knowledge-graph/entity/{id}/neighbors` | BFS 邻域探索 |

### 12.3 数据模型

```cypher
// 节点
(:Paper {title, abstract, year, citations, embedding, summary})
(:Author {name, affiliation, h_index})
(:Method {name, category, paper_count})
(:Dataset {name, task, size})
(:Community {level, size, summary, keywords})

// 关系
(:Paper)-[:AUTHORED_BY {role}]->(:Author)
(:Paper)-[:CITES]->(:Paper)
(:Paper)-[:USES_METHOD]->(:Method)
(:Paper)-[:USES_DATASET]->(:Dataset)
(:Author)-[:COLLABORATES_WITH {weight}]->(:Author)
(:Entity)-[:BELONGS_TO {level}]->(:Community)
```

---

## 13. 记忆系统

### 13.1 模块结构

```
src/agents_v2/memory/
├── unified.py           # 统一记忆管理器
├── short_term.py          # 短期记忆
├── long_term.py           # 长期记忆
├── episodic.py            # 情景记忆
├── session.py             # 会话管理
├── compression.py         # 记忆压缩
├── embeddings.py          # 记忆嵌入
├── relational.py          # 关系记忆
├── distributed.py         # 分布式记忆
├── hierarchical.py        # 层次记忆
├── mcp_protocol.py        # MCP 协议支持
├── store_postgres.py      # PostgreSQL 存储
├── store_redis.py         # Redis 存储
├── store_neo4j.py         # Neo4j 存储
└── ...                    # 共 26 个文件
```

### 13.2 记忆类型

| 类型 | 说明 | 存储 |
|------|------|------|
| 短期记忆 | 当前会话上下文 | 内存 |
| 会话记忆 | 任务内跨Agent交互 | PostgreSQL JSONB分区 |
| 长期记忆 | 跨任务知识持久化 | Qdrant (向量) + Neo4j (图) |
| 情景记忆 | 具体交互事件 | PostgreSQL |
| 层次记忆 | 按抽象层次组织 | Neo4j |
| 关系记忆 | 实体间关系 | Neo4j |
| 用户画像 | 用户偏好与习惯 | PostgreSQL |

### 13.3 重要性等级

| 等级 | 分数 | S参数(秒) | 保留时间 |
|------|------|-----------|---------|
| **CRITICAL** | 1.0 | ∞ | 永不 |
| **HIGH** | 0.8 | 604,800 (7天) | 7天 |
| **MEDIUM** | 0.5 | 86,400 (1天) | 1天 |
| **LOW** | 0.3 | 3,600 (1小时) | 1小时 |

**保留公式**: `retention = importance × e^(-t/S)`

### 13.4 记忆流转机制

| 阶段 | 触发条件 | 操作 |
|------|---------|------|
| STG→SESSION | 消息数≥30 OR 任务结束 | 批量存储到PG |
| STG→LONG_TERM | 重要性≥0.7 OR 用户标记 | 存入Qdrant+Neo4j |
| LONG_TERM→FORGOTTEN | retention<0.1 | 删除 |

### 13.5 工作流集成

在 Writing 工作流中：
- **memory_recall**: 检索前从历史记忆召回相关知识
- **memory_remember**: 筛选后将高质量论文存入记忆（遗忘曲线 + 偏好学习）

---

## 14. 配置系统

### 14.1 配置文件

| 文件 | 说明 |
|------|------|
| `config.yaml` | 主配置文件 |
| `.env` | 环境变量（API Key、代理等） |
| `.env.example` | 环境变量模板 |

### 14.2 配置加载优先级

```
环境变量 > config.yaml > 默认值
```

### 14.3 config.yaml 结构

```yaml
llm:
  provider: openai
  model: minimax-m2.7
  temperature: 0.7
  max_tokens: 4096
  timeout: 180

cache:
  ttl: 3600
  max_size: 1000

rate_limit:
  requests: 100
  window: 60

security:
  input_sanitization: true
  max_input_length: 10000

agent:
  max_concurrent: 10
  timeout: 300
  max_retries: 3
```

---

## 15. 部署架构

### 15.1 Docker 多阶段构建

**文件**: `Dockerfile`

3 个构建目标：
- `runtime`: 完整运行时
- `runtime-gpu`: GPU 支持（CLIP、Cross-Encoder）
- `runtime-light`: 轻量运行时

### 15.2 Docker Compose 服务

**文件**: `docker-compose.yml`

| 服务 | 端口 | 说明 |
|------|------|------|
| `frontend` | 3000 | React 前端（Nginx） |
| `paper-agent` | 8000 | Python 后端 |
| `postgres` | 5432 | PostgreSQL 数据库 |
| `redis` | 6379 | Redis 缓存 |
| `neo4j` | 7474/7687 | Neo4j 图数据库 |
| `prometheus` | 9090 | 监控（可选） |
| `grafana` | 3001 | 监控面板（可选） |

### 15.3 快速启动

```bash
# 开发环境 - 后端
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY 等
python -m src.main
# 服务运行在 http://localhost:8000，健康检查：/health

# 开发环境 - 前端
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173

# Docker 部署（完整栈：API + 前端 + 数据库）
docker-compose up -d

# 仅 API 服务
docker-compose up -d paper-agent

# GPU 版本
docker build -f Dockerfile --target runtime-gpu -t paper-agent:gpu .

# 带监控的部署
docker-compose --profile monitoring up -d
```

---

## 16. 测试覆盖

### 16.1 测试目录

```
tests/
├── test_langgraph_workflow.py      # 工作流测试（29 个）
├── test_unified_workflow.py        # 集成测试
├── test_e2e_langgraph.py           # 端到端测试（8 个）
├── test_enhanced_retrieval_pipeline.py
├── test_base/                      # 基础框架测试
├── test_cache/                     # 缓存测试
├── test_evaluation/                # 评估测试
├── test_intent/                    # 意图分类测试
├── test_knowledge_graph/           # 知识图谱测试
├── test_memory/                    # 记忆系统测试
├── test_multimodal/                # 多模态测试
├── test_retrieval/                 # 检索测试
├── test_routing/                   # 路由测试
├── test_security/                  # 安全测试
├── test_tools/                     # 工具测试
├── test_writing/                   # 写作测试
└── ...                             # 共 30+ 测试目录
```

### 16.2 测试覆盖总汇

| 模块 | 测试数 |
|------|--------|
| Search（搜索） | 40+ |
| Retrieval（检索） | 350+ |
| PDF 解析 | 60+ |
| LangGraph 工作流 | 29 |
| E2E 测试 | 8 |
| 其他模块 | 350+ |
| **总计** | **840+** |

---

## 17. 开发路线图

### Phase 1: 核心写作流水线 (MVP) ✅

- [x] 统一 Agent 基类 + LLMConfig
- [x] 多源搜索 Agent（arXiv / PubMed / Semantic Scholar）
- [x] 大纲生成 + 初稿撰写 Agent
- [x] 语言润色 + 智能修订 Agent
- [x] aiohttp API 服务 + 前端写作工作台
- [ ] SSE 流式聊天端点

### Phase 2: 质量保障体系 🚧

- [x] CircuitBreaker 熔断保护
- [ ] Reviewer Agent 结构化评审
- [ ] QualityEvaluator 7 维度评分
- [ ] Generator-Critic 写作循环
- [ ] 完整 AuditTrail 审计

### Phase 3: 高级功能 🚧

- [ ] SciSage 式多层 Reflector 反思机制
- [ ] GPT Researcher 式树状深度文献探索
- [ ] Citation Manager 引用验证
- [ ] Methodology Advisor 方法论指导
- [ ] Plagiarism Checker 查重集成
- [ ] 知识图谱交互式可视化

### Phase 4: 产品化 📋

- [ ] 编辑器内嵌（Overleaf / VS Code 插件）
- [ ] 版本管理 + Diff 视图
- [ ] 多人协作编辑
- [ ] 多模型 LLM Router 优化
- [ ] 流式 SSE 响应全端点
- [ ] Docker Compose 生产部署
- [ ] 用户偏好学习 + 风格自适应

### 已完成的 LangGraph 工作流阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | LangGraph 基础架构（6 节点图） | ✅ |
| Phase 2 | 混合记忆 + 偏好学习 | ✅ |
| Phase 3 | 多模态 + 知识图谱 | ✅ |
| Phase 4 | 统一路由入口（5 条工作流路径） | ✅ |
| Phase 5 | 报告/问答/修改工作流接入 | ✅ |
| Phase 6 | 扩展节点 + API 集成 | ✅ |

### 下一步计划

#### Phase 7：Harness 层完善（计划中）

```
目标: 完善质量保障体系

关键交付:
├── Evaluator 7维评分系统完善
├── CircuitBreaker 生产级实现
├── HITL Manager（PaperDebugger式Diff补丁）
├── AuditTrail 完整审计日志
└── Checkpoint 恢复与 Time Travel
```

#### Phase 8：前沿技术融合（计划中）

```
目标: 借鉴前沿论文Agent系统

关键交付:
├── SciSage式多层Reflector（Outline/Section/Document级）
├── WriteHERE式异构递归规划（DAG调度）
├── GPT Researcher式树状深度研究
├── STORM式多专家对话
└── DSPy式自动Prompt优化
```

#### Phase 9：产品化（计划中）

```
目标: 编辑器内嵌、协作功能

关键交付:
├── Overleaf/VS Code插件（PaperDebugger模式）
├── 多人协作编辑
├── 版本管理+Diff视图
├── 流式SSE响应完善
├── Docker Compose生产部署
└── 用户偏好学习
```

---

## 18. 前沿技术参考

### 18.1 2025年核心论文Agent系统

| 系统 | 核心创新 | 本系统借鉴 |
|------|---------|-----------|
| **PaperDebugger** | Overleaf内嵌多Agent + Diff补丁 + MCP协议 | HITL介入点设计 |
| **SciSage** | 三层Reflector边写边反思，引用F1提升32% | 多层反思机制 |
| **WriteHERE** | 异构递归规划，EMNLP 2025 Outstanding Paper | DAG任务调度 |
| **Agent Laboratory** | 四大Agent角色+自主科研，成本降84% | Pipeline角色分工 |
| **STORM/Co-STORM** | 斯坦福多源信息整合+协作探索 | 多专家对话 |
| **GPT Researcher** | 树状递归深度研究，聚合20+来源 | 文献综述深度研究 |

### 18.2 全球Agent框架格局

| 框架 | 核心范式 | 适用场景 |
|------|---------|---------|
| **LangGraph** | 有向图状态机 | 复杂有状态工作流（本系统选用） |
| **CrewAI** | 角色组队 | 快速多Agent原型 |
| **AutoGen/MAF** | 对话/事件驱动 | 代码生成、迭代推理 |
| **Claude Agent SDK** | Subagent+Tool+Skill | Claude生态Agent |

### 18.3 Agent Harness 设计范式

本系统的 Harness 层遵循 2025 年 Agent 系统设计的核心范式：

```
Harness = ⟨Evaluator, CheckpointManager, CircuitBreaker, HITL, AuditTrail⟩
```

关键设计原则：
1. **显式状态存储**（非运行时栈）
2. **Journal/Event Log**：每步操作追加到结构化消息数组
3. **幂等设计**：重试不重复工作
4. **数据库支持的Checkpointer**

### 18.4 参考资源

- Anthropic: [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- LangGraph: [Documentation](https://langchain.dev/langgraph)
- MCP: [Model Context Protocol](https://modelcontextprotocol.io/)
- A2A: [Agent-to-Agent Protocol](https://github.com/google/A2A)
- Agent Skills: [agentskills.io](https://agentskills.io/)
- Microsoft: [GraphRAG](https://github.com/microsoft/graphrag)
- DSPy: [Stanford NLP](https://github.com/stanfordnlp/dspy)

---

## 附录：文档索引

| 文档 | 说明 |
|------|------|
| [论文Agent开发文档](论文Agent开发文档.md) | 本文档 — 主开发文档 |
| [论文Agent前沿开发报告](论文Agent前沿开发报告.md) | 40+ Agent 框架调研 + Harness 设计 + 开发路线图 |
| [框架审查与修正报告](框架审查与修正报告.md) | 项目架构审计 + 8 项修正 + 改进建议 |
| [API文档完整版](API文档_完整版.md) | 完整 REST API 端点 + 接口对照表 |
| [错误与解决方案](错误与解决方案.md) | 错误码分类 + 调试指南 |

---

*最后更新: 2026-05-01*
