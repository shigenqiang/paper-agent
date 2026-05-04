# Architecture 模块文档索引

> 版本：v4.0
> 更新日期：2026-05-03
> 基于：实际代码结构 `src/agents_v2/`

本文档目录用于详细说明 Paper Agent 系统中各个架构模块的具体实现细节。

## 目录结构

```
architecture/
├── README.md                      # 本文件 - 模块索引
├── architecture-diagram.md        # 系统架构图
├── execution-paths.md            # 执行路径详解
│
├── agents/                       # Agent 核心框架 (新增)
│   └── agents-framework.md       # BaseAgent + ReActLoop + 角色化Agent
│
├── api/                          # API 网关层 (新增)
│   └── api-gateway.md            # gateway + paper_api + reports_api
│
├── server/                       # HTTP 服务层 (新增)
│   └── server-module.md          # api_server + SSE + 中间件
│
├── core/                         # 核心基础层
│   └── base-agent.md            # LLMConfig + 路由
│
├── unified/                      # 编排与质量保障层
│   ├── intent-router.md         # 意图路由
│   ├── circuit-breaker.md       # 熔断保护
│   └── multi-agent.md           # MasterSupervisor + PhaseSupervisor
│
├── orchestration/                # 编排逻辑层 (新增，兼容层)
│   └── orchestration-layer.md   # 从 unified 导出
│
├── harness/                      # 质量保障层 (新增，兼容层)
│   └── harness-layer.md        # CircuitBreaker/HITL/Replay
│
├── memory/                       # 记忆系统层
│   └── memory-system.md         # UnifiedMemoryManager v4
│
├── langgraph-workflow/           # LangGraph 工作流层
│   └── langgraph-workflow.md   # 5条工作流 + 22节点
│
├── search/                       # 搜索系统层
│   └── search-system.md         # 6源学术搜索
│
├── paper_agents/                 # 论文流水线
│   └── paper-agents.md          # 5个论文Agent
│
├── paper_search/                # 论文搜索 (新增)
│   └── paper-search-module.md   # paper_search + flash + citation_manager
│
├── evaluation/                   # 质量评估
│   └── evaluation-system.md     # QualityEvaluator
│
├── retrieval/                    # 检索系统
│   └── retrieval-system.md      # HyDE + Cross-Encoder + Self-RAG
│
├── knowledge_graph/              # 知识图谱
│   └── knowledge-graph.md       # GraphRAG + 社区检测
│
├── storage/                      # 存储层
│   └── storage-layer.md         # SQLite + ChromaDB
│
├── tools/                        # 工具系统
│   └── tools-module.md          # PDF解析 + 工具注册
│
├── routing/                      # 路由系统
│   └── routing-system.md        # IntentClassifier + ConfidenceCalibrator
│
├── state/                        # 状态管理
│   └── state-management.md      # CheckpointManager + 状态持久化
│
├── monitoring/                   # 监控追踪
│   └── monitoring-system.md     # ChainTracer + LatencyTracker + Alerts
│
├── skills/                       # 技能系统
│   └── skills-system.md         # SkillLoader + SemanticMatcher
│
├── scheduler/                    # 调度系统
│   └── scheduler-system.md      # ReportScheduler + SubscriptionManager
│
├── personalization/              # 个性化系统
│   └── personalization-system.md # PreferenceLearner + UserProfileManager
│
├── multimodal/                   # 多模态系统
│   └── multimodal-system.md     # ChartAnalyzer + FormulaRecognizer
│
├── problem_oriented/             # 问题导向Agent (新增)
│   └── problem-oriented-module.md # 11个专业Agent
│
├── academic_qa/                 # 学术问答系统 (新增)
│   └── academic-qa-system.md   # 15个核心组件
│
├── intent/                     # 意图路由 (新增)
│   └── intent-router.md       # 意图识别与路由
│
├── citation/                  # 统一引用管理 (2026-05新增)
│   └── citation-module.md     # 格式化/DOI验证/提取引用/溯源
│
├── reports/                   # 统一报告生成 (2026-05新增)
│   └── reports-module.md      # 日报/周报/月报生成
│
├── search/                    # 统一搜索编排 (2026-05新增)
│   └── search-module.md      # 多源搜索/结果合并
│
├── security/                     # 安全模块 (新增)
│   └── security-module.md       # RBAC + 输入验证
│
├── validation/                   # 验证模块 (新增)
│   └── validation-module.md     # PydanticValidator
│
├── plugins/                      # 插件系统 (新增)
│   └── plugins-module.md       # 插件注册与加载
│
├── sdk/                          # SDK 层 (新增)
│   └── sdk-module.md           # Agent SDK + Context + Tool
│
├── config/                       # 配置层 (新增)
│   └── config-module.md        # 配置管理
│
└── workflow/                     # 工作流引擎 (新增)
    └── workflow-module.md       # graph/ + runners/
```

## 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (server/)                             │
│                    api_server.py + SSE + 中间件                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           API Layer (api/)                                  │
│         gateway.py + paper_api.py + knowledge_graph_api + reports_api       │
├─────────────────────────────────────────────────────────────────────────────┤
│                      Orchestration Layer (orchestration/)                   │
│                   从 unified 导出，编排逻辑兼容层                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                      Harness Layer (harness/)                              │
│              CircuitBreaker + HITLManager + ExecutionReplay                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Agent Layer (agents/)                                    │
│           BaseAgent + ReActLoop + 角色化Agent (Searcher/Writer/Reviewer)    │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Unified Layer (unified/)                                │
│        MasterSupervisor + CircuitBreaker + IntentRouter + HITLManager      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   memory/   │  │   search/   │  │  retrieval/ │  │knowledge_graph/ │   │
│  │ Memory v4   │  │  6源搜索     │  │  HyDE+RAG   │  │   GraphRAG       │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   tools/    │  │  evaluation/│  │   paper_    │  │     state/      │   │
│  │  PDF解析    │  │  质量评估    │  │   agents/   │  │  Checkpoint     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   routing/  │  │ monitoring/ │  │   skills/   │  │   scheduler/    │   │
│  │  意图分类    │  │  链路追踪    │  │  Skill加载   │  │   报告调度      │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                    LangGraph Workflow (langgraph_workflow/)                  │
│                         5条工作流 + 22节点                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Storage Layer (storage/)                                  │
│                      SQLite + ChromaDB                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 模块说明

### agents/ — Agent 核心框架 (新增)

Agent 执行框架，提供 BaseAgent 基类和 ReActLoop 执行器。

| 文档 | 位置 | 说明 |
|------|------|------|
| agents-framework.md | agents/agents-framework.md | BaseAgent + ReActLoop + 角色化Agent |

### server/ — HTTP 服务层 (新增)

提供 HTTP API 服务，包含请求中间件和 SSE 流式响应。

| 文档 | 位置 | 说明 |
|------|------|------|
| server-module.md | server/server-module.md | api_server + 认证 + 限流 |

### api/ — API 网关层 (新增)

统一的 API 入口，分发到各个业务模块。

| 文档 | 位置 | 说明 |
|------|------|------|
| api-gateway.md | api/api-gateway.md | gateway + 各业务API |

### orchestration/ — 编排逻辑层 (新增)

从 unified 导出的兼容层，提供编排功能。

| 文档 | 位置 | 说明 |
|------|------|------|
| orchestration-layer.md | orchestration/orchestration-layer.md | MasterSupervisor兼容导出 |

### harness/ — 质量保障层 (新增)

从 unified 导出的兼容层，提供质量保障机制。

| 文档 | 位置 | 说明 |
|------|------|------|
| harness-layer.md | harness/harness-layer.md | CircuitBreaker/HITL/Replay |

### core/ — 核心基础层

所有 Agent 的基类，定义了 Agent 的标准执行流程。

| 文档 | 位置 | 说明 |
|------|------|------|
| base-agent.md | core/base-agent.md | LLMConfig + 意图路由 |

### unified/ — 编排与质量保障层

负责任务编排、路由和质量保障。

| 文档 | 位置 | 说明 |
|------|------|------|
| intent-router.md | unified/intent-router.md | 11 种意图识别，三级级联路由 |
| circuit-breaker.md | unified/circuit-breaker.md | 熔断保护，3 状态机，多级熔断器 |
| multi-agent.md | unified/multi-agent.md | MasterSupervisor + PhaseSupervisor |

### memory/ — 记忆系统层

管理短期、会话、长期和情景记忆。

| 文档 | 位置 | 说明 |
|------|------|------|
| memory-system.md | memory/memory-system.md | 4 层记忆结构，智能触发 + 遗忘曲线 |

### langgraph-workflow/ — 工作流层

定义 LangGraph 状态图和节点实现。

| 文档 | 位置 | 说明 |
|------|------|------|
| langgraph-workflow.md | langgraph-workflow/langgraph-workflow.md | 5 条工作流路径，22 个节点，状态定义 |

### search/ — 搜索系统层

聚合多源学术搜索。

| 文档 | 位置 | 说明 |
|------|------|------|
| search-system.md | search/search-system.md | 5 个搜索器，结果合并，速率限制 |

### paper_agents/ — 论文流水线

论文生成流水线中的专业 Agent。

| 文档 | 位置 | 说明 |
|------|------|------|
| paper-agents.md | paper_agents/paper-agents.md | 5个论文Agent：topic/literature/outline/thesis/report |

### paper_search/ — 论文搜索 (新增)

论文搜索相关功能。

| 文档 | 位置 | 说明 |
|------|------|------|
| paper-search-module.md | paper_search/paper-search-module.md | paper_flash + citation_manager + query_router |

### evaluation/ — 质量评估

多维度质量评估。

| 文档 | 位置 | 说明 |
|------|------|------|
| evaluation-system.md | evaluation/evaluation-system.md | Agent/module/quality/RAG Evaluator |

### retrieval/ — 检索系统

RAG 检索增强。

| 文档 | 位置 | 说明 |
|------|------|------|
| retrieval-system.md | retrieval/retrieval-system.md | HyDE + Cross-Encoder + Self-RAG |

### knowledge_graph/ — 知识图谱

GraphRAG 知识图谱增强。

| 文档 | 位置 | 说明 |
|------|------|------|
| knowledge-graph.md | knowledge_graph/knowledge-graph.md | GraphRAG + 社区检测 + 混合检索 |

### storage/ — 存储层

数据持久化存储。

| 文档 | 位置 | 说明 |
|------|------|------|
| storage-layer.md | storage/storage-layer.md | SQLite + ChromaDB 双存储 |

### tools/ — 工具系统

工具注册与调用。

| 文档 | 位置 | 说明 |
|------|------|------|
| tools-module.md | tools/tools-module.md | PDF解析 + 工具注册表 |

### problem_oriented/ — 问题导向Agent (新增)

专业领域的问题导向 Agent。

| 文档 | 位置 | 说明 |
|------|------|------|
| problem-oriented-module.md | problem_oriented/problem-oriented-module.md | 11个专业Agent |

### academic_qa/ — 学术问答系统 (新增)

基于论文的智能问答系统，支持多跳推理、混合检索、RAGAS 评估等。

| 文档 | 位置 | 说明 |
|------|------|------|
| academic-qa-system.md | academic_qa/academic-qa-system.md | 15个核心组件 |

### intent/ — 意图路由 (新增)

用户意图识别与路由模块。

| 文档 | 位置 | 说明 |
|------|------|------|
| intent-router.md | intent/intent-router.md | 意图识别与路由 |

## 核心概念

### Agent 执行流程

```
execute(user_input)
  ├─ _init_llm()              # 初始化 LLM
  ├─ _build_messages()        # 构建消息
  ├─ _llm_call()              # 调用 LLM
  ├─ _clean_thinking_blocks() # 清洗输出
  └─ _parse_response()       # 解析结果
```

### 意图路由流程（三级级联）

```
用户输入
  → Layer 1: 关键词快速匹配（<1ms, acc 60-75%）
    → 置信度不足 ↓
  → Layer 2: 语义向量路由（10-50ms, acc 80-92%）
    → 置信度不足 ↓
  → Layer 3: LLM深度分类（500ms-2s, acc 90-96%）
```

### 熔断状态机

```
CLOSED ←────────────────────────┐
  │                             │
  │ error_rate > 30%            │ success
  ▼                             │ in HALF_OPEN
OPEN ──────────────────────────►│
  │                             │
  │ 冷却 60s                    │
  ▼                             │
HALF_OPEN ──────────────────────┘
  │                   ▲
  │ failure           │ success
  └───────────────────┘
```

### 记忆系统 v4 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      分层记忆系统 v4                             │
├─────────────────────────────────────────────────────────────────┤
│  短期记忆 (ShortTerm) → 会话记忆 (Session) → 长期记忆 (LongTerm) │
│         ↓                   ↓                   ↓               │
│       内存                  文件               SQLite+向量库     │
│     500条TTL              500条TTL            持久化           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │   情景记忆       │
                    │  (Episodic)     │
                    │   SQLite存储    │
                    └─────────────────┘
```

---

**版本**：v4.0
**更新日期**：2026-05-03
**维护者**：Paper Agent Team