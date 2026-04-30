# agents_v2 — Paper Agent 后端系统

基于多 Agent 协作的智能论文调研与写作系统核心模块。

## 目录结构

```
agents_v2/
├── api_server.py            # aiohttp HTTP 服务入口（端口 8000）
│
├── core/                    # 基础层：Agent 基类、配置、类型定义
│   ├── base_agent.py        # BaseAgent, AgentInput/Output, LLMConfig, Tool
│   ├── config.py            # YAML 配置管理 + 16 模型注册表
│   ├── exceptions.py        # AgentError 异常层次结构
│   ├── streaming.py         # SSE 流式输出支持
│   ├── validators.py        # 输入验证与输出格式化
│   ├── plugins.py           # 插件系统（动态加载、沙盒）
│   ├── security.py          # 安全加固（输入清理、密钥管理）
│   ├── rbac.py              # 基于角色的访问控制
│   └── ...
│
├── api/                     # RESTful API 路由模块
│   ├── paper_api.py         # 论文/文献/聊天 API
│   ├── reports_api.py       # 报告/资讯 API
│   ├── knowledge_graph_api.py # 知识图谱 API
│   └── workflow_api.py      # 工作流 API
│
├── unified/                 # 编排层：多阶段监督与质量保障
│   ├── master_supervisor.py # MasterSupervisor 6 阶段编排
│   ├── phase_supervisor.py  # 阶段监督器
│   ├── circuit_breaker.py   # 熔断保护
│   ├── intent_router.py     # 意图路由
│   └── ...
│
├── paper_agents/            # 论文写作流水线 Agent
│   ├── topic_agent.py       # 选题 Agent
│   ├── literature_agent.py  # 文献调研 Agent
│   ├── thesis_agent.py      # Thesis 凝练 Agent
│   ├── outline_agent.py     # 大纲制定 Agent
│   ├── draft_writer.py      # 初稿撰写 Agent
│   ├── editor_agent.py      # 修订编辑 Agent
│   └── reviewer_agent.py    # 最终审核 Agent
│
├── writing/                 # 写作支持：生成、修订、润色
│   ├── draft_generator.py   # 初稿生成
│   ├── outline_generator.py # 大纲生成
│   ├── smart_reviser.py     # 智能修订 + 语言润色
│   ├── report_refiner.py    # 多轮精炼
│   ├── literature_review.py # 文献综述
│   └── ...
│
├── problem_oriented/        # 问题诊断与质量检查
│   ├── language_polisher.py # 语言润色
│   ├── plagiarism_checker.py # 查重检测
│   ├── methodology_advisor.py # 方法论指导
│   ├── chart_formatter.py   # 图表格式化
│   └── ...
│
├── qa/                      # 问答与报告 Agent
│   ├── paper_search.py      # 多源论文搜索
│   ├── daily_watcher.py     # 每日监控
│   ├── weekly_report.py     # 周报生成
│   ├── monthly_report.py    # 月报生成
│   └── query_router.py      # 查询路由
│
├── search/                  # 学术搜索引擎适配器
│   ├── arxiv_searcher.py    # arXiv API
│   ├── pubmed_searcher.py   # PubMed API
│   ├── semantic_scholar_searcher.py # Semantic Scholar
│   └── ...                  # CrossRef, OpenAlex, DBLP
│
├── retrieval/               # RAG 检索增强管线
│
├── knowledge_graph/         # 知识图谱系统（实体提取/GraphRAG/社区检测）
│
├── memory/                  # 记忆系统（短期/长期/情景记忆）
│
├── tools/                   # 工具系统（PDF解析/引文提取/图表生成）
│
├── langgraph_workflow/      # LangGraph 工作流定义
│
├── sdk/                     # Claude Agent SDK 框架（@tool 装饰器/Agent 基类）
│
├── skills/                  # Agent Skills 系统（SKILL.md 标准）
│
├── evaluation/              # 评估与测试工具
│
├── monitoring/              # 监控告警（链路追踪/日志/仪表板）
│
├── scheduler/               # 定时调度与订阅管理
│
├── intent/ / routing/       # 意图识别与路由选择
│
├── state/                   # 状态管理与检查点
│
├── multimodal/              # 多模态处理（视觉/图表/公式）
│
├── demos/                   # 演示脚本
│
└── _archive/                # 已归档未使用的模块（21 个子包，保留备查）
```

## 执行路径

### 启动路径

```
python -m src.main
  → src/main.py: main()
    → src.agents_v2.api_server: main()
      → create_app()
        → 注册中间件 (API Key 认证)
        → 注册内置路由 (/api/topic, /api/search, /api/paper ...)
        → 注册前端路由 (paper_api, reports_api, knowledge_graph_api, workflow_api)
        → web.run_app(app, port=8000)
```

### 前端 API 路径（主要使用）

```
React 前端 (port 5173)
  → Axios (X-API-Key 认证)
    → aiohttp (port 8000)
      → api_key_auth_middleware (验证 API Key)
        → api/paper_api.py 路由
```

| 前端操作 | API 端点 | 处理函数 | 调用的 Agent |
|---------|---------|---------|-------------|
| 创建论文 | `POST /api/papers` | `create_paper()` | 无（纯 CRUD，JSON 持久化） |
| AI 生成大纲 | `POST /api/papers/{id}/outline/generate` | `generate_outline()` | `OutlineAgent` (paper_agents) |
| 生成章节内容 | `POST /api/papers/{id}/sections/{sid}/generate` | `generate_content()` | `DraftWriterAgent` (paper_agents) |
| 修正章节格式 | `POST /api/papers/{id}/sections/{sid}/format` | `format_content()` | `LanguagePolisherAgent` (writing) |
| 搜索文献 | `POST /api/literature/search` | `search_literature()` | `PaperSearchAgent` (qa) |
| 论文对话 | `POST /api/papers/{id}/chat` | `chat()` | LLM 直接调用 |
| 知识图谱 | `POST /api/knowledge-graph/generate` | knowledge_graph_api | `KnowledgeGraphGenerator` |
| 日报/周报/月报 | `GET /api/reports/*` | reports_api | `DailyWatcher` / `WeeklyReport` / `MonthlyReport` |
| 执行工作流 | `POST /api/workflow/execute` | workflow_api | `langgraph_workflow/` |

### 内置 API 路径（api_server.py 直接注册）

```
POST /api/topic       → handle_topic()      → TopicAgent (paper_agents)
POST /api/search      → handle_search()     → PaperSearchAgent (qa)
POST /api/route       → handle_route()      → IntentRouter (unified)
POST /api/literature  → handle_literature() → LiteratureReviewAgent (writing)
POST /api/proposal    → handle_proposal()   → ProposalGeneratorAgent (writing)
POST /api/paper       → handle_full_paper() → MasterSupervisor.run("full_paper")
POST /api/draft       → handle_draft()      → DraftGeneratorAgent (writing)
POST /api/revise      → handle_revise()     → SmartReviserAgent (writing)
POST /api/batch       → handle_batch()      → 批量执行上述 Agent
WS   /ws/status       → handle_websocket()  → 实时状态推送
```

### MasterSupervisor 全流程执行

```
MasterSupervisor.run("full_paper")
  │
  ├─ Phase 1: diagnostic (并行)
  │   └─ 运行诊断 Agent，识别问题类型
  │
  ├─ Phase 2: topic (顺序)
  │   └─ TopicAgent → [HITL: 人工确认选题]
  │
  ├─ Phase 3: literature (顺序)
  │   └─ LiteratureAgent → ReviewerAgent → [HITL: 审核综述]
  │
  ├─ Phase 4: methodology (自适应)
  │   └─ MethodologyAdvisor + ArgumentBuilder → ReviewerAgent
  │
  ├─ Phase 5: writing (自适应)
  │   └─ ThesisAgent → OutlineAgent → DraftWriterAgent
  │       └─ EditorAgent → ReviewerAgent
  │           └─ 分数 < 阈值 → 返修循环 (max 3 iterations)
  │
  └─ Phase 6: polish (自适应)
      └─ ChartFormatter → LanguagePolisher → PlagiarismChecker
          └─ [HITL: 终审]
```

### Agent 调用链（单次 LLM 请求）

```
Agent.execute(user_input)
  → base_paper_agent.py: PaperAgentBase._init_llm()
    → langchain_openai.ChatOpenAI  (或 Anthropic/其他)
      → OpenAI-compatible API (通过 OPENAI_BASE_URL)
        → 实际 LLM 提供商 (MiniMax/DeepSeek/Qwen/GLM/OpenAI/Claude)
  → Agent._execute_core()  (各 Agent 子类实现)
  → AgentOutput (success, result, quality_score, next_actions)
```

### LangGraph 工作流路径（实验性）

```
POST /api/workflow/execute
  → api/workflow_api.py
    → langgraph_workflow/runner.py
      → StateGraph (crawler → selector → outline → writer → reviewer → evaluator → ...)
        → 条件边 (分数判断)
        → checkpoint 存取
```

## 意图识别 → Agent 路由

系统通过 `IntentRouter` 实现请求的自动识别和路由分发。

### 路由流程

```
用户输入 "帮我写一篇关于深度学习的论文"
  → POST /api/route {user_request: "..."}
    → IntentRouter.route()
      ├─ Step 1: 关键词匹配 (快速路径)
      │   └─ INTENT_KEYWORDS 字典匹配
      │
      ├─ Step 2: LLM 辅助识别 (复杂意图 + 多意图)
      │   └─ langchain ChatOpenAI 分析用户意图
      │
      ├─ Step 3: 合并结果, 按优先级排序
      │
      ├─ Step 4: 置信度校准 (keyword + LLM 双重验证)
      │
      ├─ Step 5: 意图冲突检测
      │
      └─ Step 6: 输出路由结果
          → {intent, confidence, suggested_agents, mode}
```

### 意图 → Agent 映射表

| 意图类型 | 意图值 | 映射 Agent | 模式 |
|---------|--------|-----------|------|
| 搜索论文 | `literature_search` | → `PaperSearchAgent` (qa) | single |
| 文献综述 | `literature_review` | → `LiteratureReviewAgent` (writing) | single |
| 文献追踪 | `literature_tracking` | → `LiteratureReviewAgent` (writing) | single |
| 论文对比 | `literature_summary` | → `LiteratureReviewAgent` (writing) | single |
| 选题 | `topic_select` | → `TopicAgent` (paper_agents) | single |
| Thesis 凝练 | `thesis_formulate` | → `ThesisAgent` (paper_agents) | single |
| 大纲生成 | `outline_generate` | → `OutlineAgent` (paper_agents) | single |
| 初稿撰写 | `draft_write` | → `DraftWriterAgent` (paper_agents) | single |
| 报告精炼 | `report_refine` | → `ReportRefinerAgent` (writing) | single |
| 智能改稿 | `paper_revision` | → `SmartReviserAgent` (writing) | single |
| 开题报告 | `proposal_generate` | → `ProposalGeneratorAgent` (writing) | single |
| 语言润色 | `language_polish` | → `LanguagePolisherAgent` (writing) | single |
| 参考文献 | `reference_format` | → `ReferenceProcessor` (writing) | single |
| 完整论文 | `full_paper` | → **5 Agent 协作** | pipeline |
| 诊断 | `diagnostic` | → **3 Agent 协作** | collaboration |

### 多 Agent 协作意图

```
full_paper (完整论文流水线):
  topic → literature → thesis → outline_generator → draft_generator

diagnostic (诊断):
  topic_refiner → literature_mapper → methodology_advisor
```

### 当前限制

`POST /api/route` 端点仅返回路由建议（JSON），不会自动执行 Agent。
自动识别 + 执行需要通过 `MasterSupervisor.run()` 全流程编排，或前端根据 `suggested_agents` 结果自主调用对应端点。

---

## 用户输入 → 全链路执行图

以下展示用户输入一句话后，系统端到端的完整执行链路。

### 路径 A: 前端直接调用（当前主流程）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         用户输入一句话                                    │
│              "帮我写一篇关于多模态学习综述的论文"                           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     React 前端 (localhost:5173)                          │
│                                                                         │
│  用户选择操作:                                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ AI 生成大纲│ │ 生成内容  │ │ 修正格式  │ │ 搜索文献  │ │ 与论文对话    │ │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬───────┘ │
│        │             │             │             │             │          │
└────────┼─────────────┼─────────────┼─────────────┼─────────────┼──────────┘
         │             │             │             │             │
         ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Axios HTTP 请求 (X-API-Key 认证)                       │
│                                                                         │
│  POST /api/papers/{id}/outline/generate                                 │
│  POST /api/papers/{id}/sections/{sid}/generate                          │
│  POST /api/papers/{id}/sections/{sid}/format                            │
│  POST /api/literature/search                                            │
│  POST /api/papers/{id}/chat                                             │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   aiohttp HTTP Server (port 8000)                        │
│                                                                         │
│  api_key_auth_middleware → 验证 X-API-Key                                │
│         │                                                               │
│         ├─→ api/paper_api.py  (前端 REST 路由)                           │
│         └─→ api_server.py     (内置直达路由)                              │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Agent 实例化 & 执行                                 │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ paper_api.py 路由处理函数                                         │   │
│  │                                                                   │   │
│  │ generate_outline():                                                │   │
│  │   1. 获取/验证 LLMConfig (从环境变量)                              │   │
│  │   2. agent = OutlineAgent(llm_config)  ← paper_agents/             │   │
│  │   3. result = await agent.execute(user_input)                      │   │
│  │                                                                   │   │
│  │ generate_content():                                                │   │
│  │   agent = DraftWriterAgent(llm_config) ← paper_agents/             │   │
│  │                                                                   │   │
│  │ format_content():                                                  │   │
│  │   agent = LanguagePolisherAgent(llm_config) ← writing/             │   │
│  │                                                                   │   │
│  │ search_literature():                                               │   │
│  │   agent = PaperSearchAgent(llm_config) ← qa/                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent.execute() 内部调用链                             │
│                                                                         │
│  Agent.execute(user_input)                                               │
│    │                                                                    │
│    ├─ 1. _init_llm()                                                     │
│    │    └─ langchain_openai.ChatOpenAI(                                  │
│    │         model=model_name,      # MiniMax-M2.7 / DeepSeek-V3 / ...  │
│    │         base_url=base_url,     # https://api.minimax.chat/v1        │
│    │         api_key=api_key,                                            │
│    │         temperature=0.7                                             │
│    │       )                                                             │
│    │                                                                    │
│    ├─ 2. _build_messages(user_input)                                     │
│    │    └─ [SystemMessage(system_prompt), HumanMessage(user_input)]      │
│    │                                                                    │
│    ├─ 3. llm.ainvoke(messages)                                           │
│    │    └─ HTTP POST → OpenAI-compatible API                             │
│    │         → 实际 LLM 提供商 (MiniMax / DeepSeek / Qwen / GLM / ...)   │
│    │                                                                    │
│    └─ 4. _parse_response(response)                                       │
│         └─ AgentOutput(success, result, quality_score, next_actions)     │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         JSON 响应返回                                    │
│                                                                         │
│  {                                                                       │
│    "success": true,                                                      │
│    "data": { "outline": [...], "sections": [...] },                      │
│    "message": "大纲生成成功"                                              │
│  }                                                                       │
│         │                                                               │
│         └─→ 前端接收 → 更新 State → 重新渲染 UI                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 路径 B: 意图路由识别

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    用户输入一句话                                         │
│              "帮我找几篇关于transformer注意力机制的论文"                    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│           POST /api/route  {user_request: "..."}                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    IntentRouter.route()                                  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 1: 关键词匹配 (快速路径, 无 LLM 调用)                        │  │
│  │                                                                   │  │
│  │ 扫描 INTENT_KEYWORDS 字典 (16 种意图 × N 个关键词)                  │  │
│  │                                                                   │  │
│  │ 用户输入: "帮我找几篇关于transformer注意力机制的论文"               │  │
│  │           ↓                                                       │  │
│  │ 命中关键词: "找"  →  "搜索论文"  →  IntentType.LITERATURE_SEARCH   │  │
│  │            "论文" →  "搜索论文"  →  IntentType.LITERATURE_SEARCH   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 2: LLM 辅助识别 (处理复杂/多意图情况)                        │  │
│  │                                                                   │  │
│  │ langchain ChatOpenAI.ainvoke([                                    │  │
│  │   SystemMessage("你是一个意图识别专家..."),                         │  │
│  │   HumanMessage("分析以下用户请求的所有意图: 帮我找几篇...")         │  │
│  │ ])                                                                │  │
│  │   ↓                                                               │  │
│  │ LLM 返回 JSON:                                                     │  │
│  │ {                                                                  │  │
│  │   "intents": [                                                     │  │
│  │     {"intent": "literature_search", "confidence": 0.92},           │  │
│  │     {"intent": "literature_summary", "confidence": 0.45}           │  │
│  │   ],                                                               │  │
│  │   "reasoning": "用户明确要求搜索论文...次要意图可能包含对比总结"     │  │
│  │ }                                                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 3: 合并结果 + 按优先级排序                                    │  │
│  │                                                                   │  │
│  │ 关键词: [LITERATURE_SEARCH]                                       │  │
│  │ LLM:    [LITERATURE_SEARCH, LITERATURE_SUMMARY]                   │  │
│  │          ↓ 合并去重                                                │  │
│  │ 主意图:   LITERATURE_SEARCH (priority=60)                          │  │
│  │ 次要意图: LITERATURE_SUMMARY (priority=60)                         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 4: 置信度校准                                                │  │
│  │                                                                   │  │
│  │ keyword_match=True + llm_match=True  →  +0.15                      │  │
│  │ base_confidence=0.92  →  calibrated=1.0 (cap)                      │  │
│  │ confidence_level = HIGH (≥0.8)                                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 5: 意图冲突检测                                              │  │
│  │                                                                   │  │
│  │ 检查 LITERATURE_SEARCH ↔ LITERATURE_SUMMARY 是否有冲突             │  │
│  │ 不在冲突对列表中 → 无冲突                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 6: 查 intent_agent_map → 输出路由结果                        │  │
│  │                                                                   │  │
│  │ LITERATURE_SEARCH → agent="literature"          (PaperSearchAgent) │  │
│  │ LITERATURE_SUMMARY → agent="literature_review"  (LiteratureReview) │  │
│  │                                                                   │  │
│  │ mode = "collaboration" (有次要意图 → 协作模式)                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    路由结果 JSON 返回 (仅建议)                            │
│                                                                         │
│  {                                                                       │
│    "primary_intent": "literature_search",                                 │
│    "confidence": 1.0,                                                    │
│    "confidence_level": "high",                                           │
│    "is_multi_intent": true,                                              │
│    "secondary_intents": ["literature_summary"],                           │
│    "suggested_agents": ["literature", "literature_review"],               │
│    "mode": "collaboration",                                              │
│    "requires_collaboration": true                                        │
│  }                                                                       │
│         │                                                               │
│         └─→ 前端读取 suggested_agents                                     │
│             → 调用对应端点执行 (路径 A)                                    │
│             → 或交给 MasterSupervisor 全流程编排 (路径 C)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 路径 C: MasterSupervisor 全流程编排

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    用户输入 "我要写一篇完整的论文"                          │
│                    或前端选择 "全流程生成" 按钮                            │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│          POST /api/paper  {user_request: "...", task_type: "full_paper"} │
│                    或前端调用 MasterSupervisor.run()                      │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              MasterSupervisor.run("full_paper", input_data)              │
│                                                                         │
│  初始化 PaperState(user_request="...")                                    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Phase 1: diagnostic (并行)                        阈值 ≥ 6.0     │   │
│  │                                                                   │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │   │
│  │ │topic_refiner│ │literature   │ │methodology  │                  │   │
│  │ │             │ │_mapper      │ │_advisor     │                  │   │
│  │ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                  │   │
│  │        └───────────────┼───────────────┘                         │   │
│  │                        ▼                                         │   │
│  │            DiagnosticResult {                                     │   │
│  │              problems_found: [TOPIC_VAGUE, ...],                  │   │
│  │              severity: {...},                                     │   │
│  │              recommendations: [...]                               │   │
│  │            }                                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Phase 2: topic (顺序)                              阈值 ≥ 7.0    │   │
│  │                                                                   │   │
│  │ TopicAgent.execute(user_request)                                   │   │
│  │   → {title, description, innovation, feasibility}                  │   │
│  │   → [HITL: 人工确认选题]                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Phase 3: literature (顺序)                         阈值 ≥ 7.0    │   │
│  │                                                                   │   │
│  │ LiteratureAgent.execute(topic)                                     │   │
│  │   → 搜索 + 筛选 + 综述                                            │   │
│  │   → ReviewerAgent 审核                                            │   │
│  │   → [HITL: 人工审核综述]                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Phase 4: methodology (自适应)                      阈值 ≥ 7.0    │   │
│  │                                                                   │   │
│  │ MethodologyAdvisor + ArgumentBuilder                               │   │
│  │   → ReviewerAgent 质量检查                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Phase 5: writing (自适应)                          阈值 ≥ 7.0    │   │
│  │                                                                   │   │
│  │ ThesisAgent → OutlineAgent → DraftWriterAgent                     │   │
│  │   → EditorAgent → ReviewerAgent                                   │   │
│  │   → 分数 < 7.0 → 返修循环 (最多 3 轮)                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Phase 6: polish (自适应)                           阈值 ≥ 8.0    │   │
│  │                                                                   │   │
│  │ ChartFormatter → LanguagePolisher → PlagiarismChecker              │   │
│  │   → [HITL: 终审确认]                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 编译最终结果                                                      │   │
│  │                                                                   │   │
│  │ {                                                                  │   │
│  │   "success": true,                                                 │   │
│  │   "phases_completed": ["diagnostic","topic",...,"polish"],         │   │
│  │   "final_paper": "<完整论文文本>",                                  │   │
│  │   "quality_history": [{score:7.5,...}, ...],                       │   │
│  │   "final_quality": 8.2,                                            │   │
│  │   "iterations": 2                                                  │   │
│  │ }                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 三条路径对比

```
用户输入一句话
      │
      ├──→ 路径 A (主流程): 前端直接调用具体端点
      │      React → Axios → aiohttp → paper_api.py → Agent.execute() → LLM
      │      适用: 用户明确知道要做什么 (生成大纲/写内容/搜文献)
      │      响应: Agent 执行结果 JSON
      │
      ├──→ 路径 B (辅助): 意图识别路由
      │      React → Axios → /api/route → IntentRouter → 路由建议 JSON
      │      适用: 用户不确定该用哪个功能, 先分析意图
      │      响应: {intent, confidence, suggested_agents} — 仅建议, 不执行
      │
      └──→ 路径 C (全流程): MasterSupervisor 编排
             React → Axios → /api/paper → MasterSupervisor.run()
             → 6 Phase 顺序执行 → 完整论文
             适用: 用户要端到端生成完整论文
             响应: {final_paper, quality_history, phases_completed}
```

---

## 后端 → 前端：数据处理与清洗链路

LLM 原始输出包含大量前端不需要的内容（思考过程、代码块标记、参考文献、JSON 元数据等）。后端经过 **4 层清洗** 后才将干净数据返回前端。

### 数据清洗流水线全图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LLM 原始输出 (raw response)                       │
│                                                                         │
│  <think>我需要先分析用户的需求...</think>                                 │
│  ```json                                                                │
│  {                                                                       │
│    "structure": {"title": "...", "chapters": [...]},                     │
│    "chapter_plans": [...],                                               │
│    "reasoning": "选择了5章结构因为..."                                    │
│  }                                                                       │
│  ```                                                                    │
│  ## 参考文献                                                             │
│  [1] ...                                                                 │
│                                                                         │
│  混杂内容: HTML标签, UTF-8转义(\xe4\xbd\xa0), 多余空行, 控制字符         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    第 1 层: base_paper_agent.py                          │
│                    _clean_thinking_blocks()                              │
│                                                                         │
│  ① regex 移除 <think>...</think> 块                                     │
│     re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)            │
│                                                                         │
│  ② 截断参考文献部分                                                      │
│     re.sub(r'##?\s*参考文献.*$', '', text)                               │
│                                                                         │
│  ③ _remove_code_fences() — 剥除 markdown 代码块标记                      │
│     ```json  →  (移除)                                                   │
│     ```      →  (移除)                                                   │
│                                                                         │
│  ④ _fix_utf8_escapes() — 修复字节转义序列                               │
│     \xe4\xbd\xa0 → 你                                                    │
│                                                                         │
│  ⑤ 去除前导分隔线和多余空行                                               │
│     .lstrip('-\n')                                                       │
│                                                                         │
│  ⑥ HTML 检测 — 如果以 <! 或 <html 开头，抛出错误                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    第 2 层: Agent 解析层                                  │
│                    各 Agent._execute_core()                              │
│                                                                         │
│  cleaned_text = await self._llm_call(prompt)   ← 调用第1层清洗           │
│  data = json.loads(cleaned_text)               ← 解析结构化JSON          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 各 Agent 只提取自己需要的键:                                      │   │
│  │                                                                   │   │
│  │ OutlineAgent    → .get("structure", {})  丢弃 chapter_plans 等    │   │
│  │ TopicAgent      → .get("candidates", [])  丢弃 scoring_detail 等  │   │
│  │ LiteratureAgent → .get("ranked", [])      丢弃 raw_query 等       │   │
│  │ ThesisAgent     → .get("hypotheses", [])  丢弃 alternatives 等    │   │
│  │ DraftWriter     → .get("full_draft", "")  丢弃 section_meta 等    │   │
│  │ ReviewerAgent   → .get("expert_review", {}) 丢弃 draft_scores 等  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  → 包装为 AgentOutput:                                                   │
│    {success, result, agent_name, reasoning, quality_score, ...}          │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    第 3 层: paper_api.py 路由层                           │
│                    字段提取 + 二次过滤                                    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ generate_outline():                                              │   │
│  │   AgentOutput.result → result.get("outline", {})                  │   │
│  │   → {success: true, data: {structure, chapters}}                  │   │
│  │                                                                   │   │
│  │ generate_content():                                               │   │
│  │   AgentOutput.result → result.get("full_draft") || "content"      │   │
│  │   → {success: true, data: {content: "...", section_id}}           │   │
│  │                                                                   │   │
│  │ format_content():                                                 │   │
│  │   AgentOutput.result → result.get("polished_text")                │   │
│  │   丢弃: diagnosis, grammar_issues, style_issues                   │   │
│  │   → {success: true, data: {content: "...", section_id}}           │   │
│  │                                                                   │   │
│  │ search_literature():                                              │   │
│  │   AgentOutput.result → {papers, total, sources}                   │   │
│  │   → {success: true, data: {results, total, query}}                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  共同剥离的字段: reasoning, quality_score, agent_name,                   │
│                  next_actions, metadata, error                           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    第 4 层: Chat 消息过滤 (特殊)                          │
│                    paper_api.py chat() / get_chat_history()              │
│                                                                         │
│  存储的消息格式 (完整):                                                   │
│  {"role": "assistant", "content": "Hello!", "reasoning": "思考过程..."}  │
│                                                                         │
│  返回前端的格式 (精简):                                                   │
│  for m in messages_context:                                             │
│      → {"role": m["role"], "content": m["content"]}  ← reasoning 剥离   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         前端接收到的纯净 JSON                             │
│                                                                         │
│  通用格式:                                                                │
│  {                                                                       │
│    "success": true,                                                      │
│    "data": {                         ← 只有前端需要的业务数据             │
│      "outline": {...},                                                   │
│      "content": "...",                                                   │
│      "results": [...]                                                    │
│    }                                                                     │
│  }                                                                       │
│                                                                         │
│  不包含:                                                                  │
│  ✗ reasoning (思考过程)                                                  │
│  ✗ quality_score (内部评分)                                              │
│  ✗ agent_name (内部标识)                                                 │
│  ✗ next_actions (内部执行计划)                                           │
│  ✗ metadata (内部元数据)                                                 │
│  ✗ error (异常时单独返回)                                                │
│  ✗ <think> 块 (已清洗)                                                   │
│  ✗ 参考文献 (已截断)                                                     │
│  ✗ markdown 代码围栏 (已剥离)                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 流式传输 (SSE) 的数据处理

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SSE 流式传输路径 (/ws/status)                        │
│                                                                         │
│  流式层 (streaming.py) 不做任何清洗                                       │
│                                                                         │
│  async for chunk in llm.astream(prompt):                                 │
│      content = getattr(chunk, 'content', str(chunk))                    │
│      await stream.write(content)     ← 原始 chunk 直接推送               │
│                                                                         │
│  事件类型: START → TOKEN/CHUNK → COMPLETE/ERROR                           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 注意: 流式传输中, 前端会收到原始的 token 流, 包括:                │   │
│  │  • <think> 标记 (如果模型输出的话)                                │   │
│  │  • ```json 代码围栏 (如果模型输出的话)                            │   │
│  │  • 需要前端自行处理显示逻辑                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### MiniMax 特有处理

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MiniMax API 特殊适配                                   │
│                                                                         │
│  ① reasoning_split: False                                               │
│     extra_body={"reasoning_split": False}                                │
│     防止模型在响应中分离思考过程                                          │
│                                                                         │
│  ② UTF-8 字节转义修复                                                    │
│     MiniMax 有时输出 \xe4\xbd\xa0 而非实际中文字符                        │
│     _fix_utf8_escapes() 将其解码为正确的 UTF-8 字符                       │
│                                                                         │
│  ③ Content block 格式                                                    │
│     tool_call 结果需要使用特定的 content block 格式                       │
│     否则 API 返回: "Content block is not a input_json block"             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 清洗前后对比

```
┌─────────────────────────────────────────────────────────────────────────┐
│  清洗前 (Agent._llm_call 返回的原始文本)                                  │
│  ─────────────────────────────────────────────                           │
│  - <think>...</think> 思考块                                             │
│  - ```json / ``` 代码围栏标记                                            │
│  - \xHH 字节转义序列                                                     │
│  - <!--  HTML 注释 -->                                                   │
│  - ## 参考文献 及全部引用内容                                             │
│  - 前导 --- 分隔线                                                        │
│  - 多个连续空行 \n{3,}                                                    │
│  - 控制字符 [\x00-\x08]                                                  │
│  体积: ~2500 tokens (典型值)                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  清洗后 (AgentOutput.result 中的结构化数据)                               │
│  ─────────────────────────────────────────────                           │
│  - 干净的 Python dict / str                                              │
│  - 无 markdown 标记                                                      │
│  - 正确的 UTF-8 字符                                                     │
│  - 无 HTML 标签                                                          │
│  - 无参考文献                                                             │
│  - 标准化的换行                                                          │
│  体积: ~200 tokens (仅业务数据)                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  返回前端 (HTTP Response JSON body)                                      │
│  ─────────────────────────────────                                      │
│  {                                                                       │
│    "success": true,                                                      │
│    "data": {                         ← 字段名统一为 "data"               │
│      ...                              ← 内容精简为前端需要的最小集合      │
│    }                                                                     │
│  }                                                                       │
│  体积: ~150 tokens                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 写作流水线

```
选题诊断 → 文献综述 → 大纲规划 → 逐章写作 → 综合润色 → 格式输出
    ↑          ↑          ↑          ↑          ↑          ↑
TopicAgent  Literature Outline   Draft      Polisher   Chart
            Agent      Agent     Writer     Agent      Formatter
```

## 快速启动

```bash
python -m src.agents_v2.api_server
```

## 导入示例

```python
from src.agents_v2 import BaseAgent, LLMConfig          # 基础类
from src.agents_v2 import MasterSupervisor              # 编排
from src.agents_v2 import PaperSearchAgent, QueryRouter  # 搜索问答
from src.agents_v2.paper_agents import TopicAgent        # 写作 Agent
```
