# Paper Agent 完整系统架构图

> 基于 `src/agents_v2/` 代码库的实际结构，实时同步代码变更

---

## 一、整体架构概览

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React 18)                                     │
│   HomePage | WritingPage | LiteraturePage | ReportsPage | SettingsPage            │
│   Axios Client + Zustand State Management                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                              HTTP/REST + SSE Streaming
                              X-API-Key: <key>
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (aiohttp)                                      │
│  端口: 8000 | 中间件: request_logging + api_key_auth + error_handle               │
│  ┌───────────────────────────────────────────────────────────────────────────┐    │
│  │ /health      - 健康检查                                                   │    │
│  │ /api/papers  - 论文CRUD                                                   │    │
│  │ /api/reports - 报告生成                                                   │    │
│  │ /api/route   - 意图路由                                                   │    │
│  │ /api/workflow- 工作流执行                                                 │    │
│  │ /api/kg      - 知识图谱                                                   │    │
│  └───────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
        ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
        │   API Routes      │  │  Server Routes    │  │   LangGraph       │
        │   (api/ 模块)      │  │  (server/)        │  │  (langgraph_workflow/) │
        └───────────────────┘  └───────────────────┘  └───────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │  MasterSupervisor (unified/master_supervisor.py)                            │  │
│  │  - 6阶段流水线: diagnostic→topic→literature→methodology→writing→polish     │  │
│  │  - 状态管理: PaperState                                                     │  │
│  │  - 错误处理: CircuitBreaker + FallbackHandler                              │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │  IntentRouter (unified/intent_router.py)                                    │  │
│  │  - 11种意图类型识别                                                         │  │
│  │  - 关键词匹配 + LLM辅助 + 置信度校准                                        │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │  LangGraph Workflow (langgraph_workflow/)                                  │  │
│  │  - unified_workflow.py (主工作流)                                           │  │
│  │  - state.py (PaperAgentState)                                              │  │
│  │  - nodes/ (22个节点) + edges.py                                            │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    │                    │                    │
          ┌─────────▼──────┐  ┌────────▼───────┐  ┌────────▼───────┐
          │   Agents       │  │   Memory       │  │   Observability│
          │   (agents/)    │  │   (memory/)   │  │  (monitoring/) │
          └────────────────┘  └────────────────┘  └────────────────┘
```

---

## 二、代码结构详解 (src/agents_v2/)

### 2.1 server/ — HTTP服务器

```
server/
├── __init__.py
├── api_server.py         # aiohttp HTTP服务入口
├── logging_config.py    # Loguru日志配置
└── migrate_logging.py   # 日志迁移工具
```

### 2.2 agents/ — 新版Agent框架

```
agents/
├── __init__.py
├── base/                 # Agent基类
│   ├── __init__.py
│   └── base_agent.py    # BaseAgent (361行)
├── loops/               # 执行循环
│   ├── __init__.py
│   └── react_loop.py    # ReAct执行器 (546行)
└── roles/              # Agent角色
    ├── __init__.py
    ├── planner/         # 规划Agent
    ├── polisher/       # 润色Agent
    ├── reviewer/       # 评审Agent
    ├── searcher/       # 搜索Agent
    ├── specialist/     # 专家Agent
    └── writer/         # 写作Agent
```

### 2.3 api/ — RESTful API路由

```
api/
├── __init__.py
├── gateway.py              # API网关抽象
├── paper_api.py           # 论文CRUD + 聊天
├── reports_api.py         # 报告/资讯生成
├── knowledge_graph_api.py # 知识图谱API
├── workflow_api.py        # 工作流API
└── sse_helper.py           # SSE流式辅助
```

### 2.4 unified/ — 编排层 (向后兼容)

```
unified/
├── __init__.py
├── master_supervisor.py     # MasterSupervisor (6阶段流水线编排)
├── phase_supervisor.py      # 阶段监督器
├── intent_router.py         # 意图路由 (11种意图类型)
├── circuit_breaker.py      # 熔断保护
├── state_model.py           # 状态模型定义
├── error_handler.py         # 错误处理与回退
├── error_recovery.py        # 错误恢复
├── translation.py           # 翻译包装器
├── cache.py                # 结果缓存
├── monitoring.py           # 指标收集
├── execution_replay.py     # 执行回放
├── hitl_manager.py         # Human-in-the-Loop管理器
├── agent_loop.py          # Agent循环抽象
├── flow_monitoring.py      # 流程监控
├── input_security.py       # 输入安全
├── output_manager.py       # 输出管理
├── pydantic_validator.py   # Pydantic验证
└── phase_supervisor.py     # 阶段监督
```

### 2.5 orchestration/ — 编排层 (新版兼容)

```
orchestration/
├── __init__.py             # 导出 unified/ 组件 (兼容层)
└── router/                 # 路由子模块
    └── __init__.py
```

### 2.6 harness/ — 质量保障 (新版兼容)

```
harness/
└── __init__.py             # 导出 unified/ 组件 (兼容层)
```

### 2.7 langgraph_workflow/ — LangGraph工作流

```
langgraph_workflow/
├── __init__.py
├── unified_workflow.py     # 统一工作流 (20KB)
├── workflow.py            # 基础工作流 (9KB)
├── state.py               # PaperAgentState定义 (5KB)
├── edges.py               # 条件边定义
├── runner.py              # 运行入口
├── nodes/                 # 节点实现 (22个文件)
│   ├── __init__.py
│   ├── router.py          # 路由节点 (3KB)
│   ├── crawler.py         # 爬虫节点 (13KB)
│   ├── selector.py        # 筛选节点
│   ├── outline.py         # 大纲节点
│   ├── writer.py          # 写作节点
│   ├── reviewer.py        # 评审节点
│   ├── evaluator.py       # 评估节点
│   ├── memory.py          # 记忆节点
│   ├── multimodal.py      # 多模态节点
│   ├── knowledge_graph.py # 知识图谱节点
│   ├── qa_search.py       # 问答搜索节点
│   ├── qa_synthesize.py   # 问答综合节点
│   ├── qa_answer.py       # 问答回答节点
│   ├── report_crawl.py   # 报告爬取节点
│   ├── report_analyze.py # 报告分析节点
│   ├── report_gen.py      # 报告生成节点
│   ├── revise.py          # 修订节点
│   ├── refine.py          # 精炼节点
│   └── polish.py          # 润色节点
└── observability/
    └── tracer.py          # 链路追踪器
```

### 2.8 workflow/ — 预留工作流 (空目录)

```
workflow/
├── __init__.py            # 空
├── graph/                 # 图结构 (空)
│   ├── __init__.py
│   └── nodes/
│       └── __init__.py
└── runners/               # 运行器 (空)
    └── __init__.py
```

### 2.9 core/ — Agent基础层

| 文件 | 说明 |
|------|------|
| `base_agent.py` | Agent基类，execute/plan/reflect |
| `enhanced_base.py` | 增强版Agent |
| `react_executor.py` | ReAct执行器 |
| `config.py` | YAML配置 + 16模型注册表 |
| `config_manager.py` | 配置管理器 |
| `context_injector.py` | 上下文注入器 |
| `llm_fallback.py` | LLM降级策略 |
| `streaming.py` | SSE流式输出 |
| `agent_roles.py` | Agent角色定义 |
| `builtin_plugins.py` | 内置插件 |
| `plugins.py` | 插件系统 |
| `security.py` | 安全加固 |
| `error_recovery.py` | 错误恢复 |
| `validators.py` | 输入验证 |
| `exceptions.py` | 异常层次结构 |
| `rbac.py` | 基于角色的访问控制 |
| `user_manager.py` | 用户管理 |

### 2.10 paper_agents/ — 论文流水线Agent

```
paper_agents/
├── __init__.py            # 导出5个Agent
├── base_paper_agent.py    # PaperAgent基类 (11KB)
├── topic_agent.py         # 选题Agent (19KB)
├── literature_agent.py    # 文献调研Agent (12KB)
├── outline_agent.py       # 大纲制定Agent (11KB)
├── draft_writer.py        # 初稿撰写Agent (12KB)
├── digest_agent.py        # 论文摘要Agent (20KB)
└── deprecated/
    ├── annotations.py
    ├── editor_agent.py
    ├── reviewer_agent.py
    ├── thesis_agent.py
    ├── versioning.py
    └── writing_pipeline.py
```

### 2.11 writing/ — 写作支持

```
writing/
├── __init__.py
├── outline_generator.py     # 大纲生成
├── draft_generator.py      # 初稿生成
├── smart_reviser.py        # 智能修订 + 语言润色
├── report_refiner.py       # 多轮精炼
├── literature_review.py    # 文献综述
├── generation_optimizer.py  # 生成优化
├── streaming_generator.py  # 流式生成
├── answer_quality_checker.py # 答案质量检查
├── base_writing_agent.py   # 写作Agent基类
├── citation_generator.py   # 引用生成
├── logic_coherence.py      # 逻辑一致性
├── proposal_generator.py   # 提案生成
├── reference_processor.py   # 参考文献处理
├── reflection_engine.py    # 反思引擎
└── diff_manager.py         # Diff管理
```

### 2.12 problem_oriented/ — 问题诊断与质量检查

```
problem_oriented/
├── __init__.py
├── topic_refiner.py        # 选题精炼
├── literature_mapper.py    # 文献映射
├── methodology_advisor.py # 方法论指导
├── argument_builder.py     # 论点构建
├── research_gap.py        # 研究空白识别
├── language_polisher.py   # 语言润色
└── plagiarism_checker.py   # 查重检测
```

### 2.13 search/ — 学术搜索引擎

```
search/
├── __init__.py
├── base_searcher.py        # 搜索基类
├── base_advanced_searcher.py # 高级搜索基类
├── arxiv_searcher.py       # arXiv API
├── pubmed_searcher.py     # PubMed API
├── semantic_scholar_searcher.py # Semantic Scholar
├── openalex_searcher.py   # OpenAlex API
├── crossref_searcher.py   # CrossRef API
├── paper_search.py        # 多源聚合搜索
├── paper_flash.py         # 快速搜索
├── query_parser.py        # 查询解析
├── search_factory.py      # 搜索工厂
├── search_result_merger.py # 结果合并
├── search_orchestrator.py # 搜索编排
├── cache_manager.py       # 缓存管理
├── rate_manager.py        # 限流管理
└── strategies.py          # 搜索策略
```

### 2.14 retrieval/ — RAG检索增强

```
retrieval/
├── __init__.py
├── adaptive_retrieval.py   # 自适应检索
├── hyde_retriever.py       # HyDE检索
├── cross_encoder_reranker.py # Cross-Encoder重排
├── self_rag_controller.py  # Self-RAG控制
├── confidence_calculator.py # 置信度计算
├── deduplicator.py         # 去重
├── document_evaluator.py   # 文档评估
├── priority_matcher.py     # 优先级匹配
├── query_classifier.py     # 查询分类
├── result_fuser.py         # 结果融合
├── retrieval_chain.py      # 检索链
├── rewrite_validator.py    # 重写验证
├── score_parser.py         # 分数解析
└── keyword_sets.py         # 关键词集合
```

### 2.15 knowledge_graph/ — 知识图谱

```
knowledge_graph/
├── __init__.py
├── kg_service.py           # KG服务
├── kg_graphrag.py          # GraphRAG问答
├── kg_embeddings.py        # 向量嵌入
├── kg_community.py         # 社区检测
├── kg_batch_operations.py # 批量操作
├── kg_extractors.py       # 实体提取
├── kg_hybrid_retriever.py # 混合检索
├── kg_schema.py            # 图谱Schema
├── kg_summarizer.py        # 摘要生成
├── kg_vector_store.py     # 向量存储
└── deprecated/
    └── legacy_generator.py
```

### 2.16 memory/ — 记忆系统v4

```
memory/
├── __init__.py
├── unified.py              # 统一记忆管理器
├── short_term.py          # 短期记忆 (内存LRU)
├── long_term.py            # 长期记忆
├── episodic.py             # 情景记忆
├── session.py              # 会话记忆
├── flow_controller.py      # 流转控制器
├── embeddings.py           # 向量嵌入
├── compression.py          # 记忆压缩
├── retrieval.py            # 检索引擎
├── config.py              # 内存配置
└── deprecated/            # 已废弃模块 (18个)
```

### 2.17 storage/ — 存储层

```
storage/
├── __init__.py
└── paper_db.py            # SQLite + ChromaDB双存储
```

### 2.18 evaluation/ — 评估体系

```
evaluation/
├── __init__.py
├── agent_evaluator.py     # Agent评估器
├── module_evaluator.py    # 模块评估器
├── quality_evaluator.py   # 质量评估器
├── rag_evaluator.py       # RAG评估器
├── evaluation_runner.py   # 评估运行器
├── benchmark.py           # 基准测试
├── feedback_collector.py  # 反馈收集
├── output_formatter.py   # 输出格式化
├── output_validator.py    # 输出验证
├── report_generator.py   # 报告生成
├── chain_integrator.py   # 链式集成
├── chaos_tester.py       # 混沌测试
├── e2e_test_suite.py     # 端到端测试
├── performance_benchmark.py # 性能基准
├── release_checker.py    # 发布检查
└── benchmarks/
    ├── __init__.py
    ├── ab_testing.py
    ├── agent_bench.py
    ├── gaia.py
    └── paper_writing.py
```

### 2.19 monitoring/ — 可观测性

```
monitoring/
├── __init__.py
├── alerts.py              # 告警系统 (24KB)
├── chain_debugger.py      # 链路调试 (9KB)
├── chain_monitor.py       # 链路监控 (7KB)
├── chain_tracer.py       # 链路追踪 (21KB)
├── chain_tracer_mixin.py # 追踪混入 (8KB)
├── dashboard.py          # 监控仪表盘 (45KB)
├── docs_monitor.py       # 文档监控 (10KB)
├── latency_tracker.py    # 延迟追踪 (6KB)
├── optimizer.py          # 性能优化 (10KB)
├── quality_tracker.py    # 质量追踪 (14KB)
└── structured_logging.py # 结构化日志 (16KB)
```

### 2.20 routing/ — 意图路由

```
routing/
├── __init__.py
├── intent_classifier.py     # 意图分类器
├── intent_confidence.py    # 置信度计算
├── llm_intent_classifier.py # LLM意图分类
├── multi_intent.py         # 多意图处理
├── semantic_expander.py    # 语义扩展
├── agent_selector.py        # Agent选择器
├── fallback_router.py      # 降级路由
└── routing_optimizer.py    # 路由优化
```

### 2.21 其他模块

| 模块 | 文件 | 说明 |
|------|------|------|
| `tools/` | 30+ | 文本分块、引用提取、图表分类、PDF解析等 |
| `state/` | 4 | 状态模型、检查点管理、持久化、验证 |
| `skills/` | 3+ | Skill加载器、语义匹配器 |
| `multimodal/` | 6 | 图表分析、公式识别、视觉编码 |
| `scheduler/` | 3 | 报告调度、订阅管理、依赖调度 |
| `personalization/` | 2 | 偏好学习、用户画像 |
| `sdk/` | 3 | Claude Agent SDK |
| `paper_search/` | 5+ | 论文搜索独立模块 |
| `security/` | 2 | 安全 (RBAC) |
| `validation/` | 1 | 验证 |
| `plugins/` | 1 | 插件系统 |
| `config/` | 1 | 配置 |
| `demos/` | 1+ | 性能测试demo |

---

## 三、启动与执行路径

### 3.1 启动路径

```
python -m src.main
  → src/main.py: main()
    → src.agents_v2.server.api_server: main()
      → create_app()
        → 注册中间件 (request_logging, api_key_auth)
        → 注册路由
        → web.run_app(app, port=8000)
```

### 3.2 请求处理路径

```
前端 (port 5173)
  → Axios (X-API-Key认证)
    → aiohttp (port 8000)
      → api_key_auth_middleware
        → api/paper_api.py / api/workflow_api.py
          → MasterSupervisor.run() / LangGraph Workflow
            → Agent.execute()
              → LLM调用链
```

---

## 四、意图类型与Agent映射

| IntentType | 值 | 映射Agent | 模块 |
|-----------|---|-----------|------|
| `LITERATURE_SEARCH` | 搜索论文 | PaperSearchAgent | search |
| `LITERATURE_REVIEW` | 文献综述 | LiteratureAgent | paper_agents |
| `LITERATURE_TRACKING` | 文献追踪 | LiteratureAgent | paper_agents |
| `LITERATURE_SUMMARY` | 文献对比 | LiteratureAgent | paper_agents |
| `TOPIC_SELECT` | 选题 | TopicAgent | paper_agents |
| `THESIS_FORMULATE` | Thesis凝练 | ThesisAgent | paper_agents |
| `OUTLINE_GENERATE` | 大纲生成 | OutlineAgent | paper_agents |
| `DRAFT_WRITE` | 初稿撰写 | DraftWriterAgent | paper_agents |
| `PAPER_REVISION` | 智能改稿 | SmartReviserAgent | writing |
| `REPORT_REFINE` | 报告精炼 | ReportRefinerAgent | writing |
| `FULL_PAPER` | 完整论文 | 5 Agent协作 | pipeline |
| `DIAGNOSTIC` | 诊断 | 3 Agent协作 | collaboration |

---

## 五、LangGraph Workflow

### 5.1 五条工作流路径

| 工作流 | 节点序列 | 说明 |
|--------|----------|------|
| **search** | crawler → selector | 多源论文搜索 |
| **writing** | memory_recall → crawler → selector → [multimodal] → [kg] → outline → writer → reviewer → evaluator → memory_remember | 完整写作流程 |
| **report** | report_crawl → report_analyze → report_gen | 报告生成 |
| **qa** | qa_search → qa_synthesize → qa_answer | 问答 |
| **revise** | revise → refine → polish | 修改润色 |

### 5.2 核心节点

| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `writer` | 逐节生成内容，带引用标注 | selected_papers, outline | draft |
| `reviewer` | 质量评审，反馈改进建议 | draft | feedback, quality_score |
| `evaluator` | 多维度评分，决策通过/返修 | draft | evaluation_passed |

---

## 六、数据存储

### 6.1 存储架构

```
┌────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
├────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   SQLite        │  │   ChromaDB      │                  │
│  │   (元数据)       │  │   (向量)        │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                           │
│           ▼                    ▼                           │
│  ┌─────────────────────────────────────────────┐          │
│  │  Paper DB (data/papers.db)                   │          │
│  └─────────────────────────────────────────────┘          │
│  ┌─────────────────────────────────────────────┐          │
│  │  ChromaDB (data/chroma_db/)                   │          │
│  └─────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────┘
```

### 6.2 存储路径

```
data/
├── papers.db         # SQLite数据库
└── chroma_db/       # ChromaDB向量存储
```

---

## 七、技术栈总结

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + Vite 5 + Ant Design 5 + Zustand 4 | SPA写作工作台 |
| **后端** | Python 3.11 + aiohttp | 异步HTTP服务 |
| **Agent框架** | 新版 agents/ + 兼容 unified/ | 双轨并行 |
| **Agent编排** | LangGraph (StateGraph) | 有向图状态机 |
| **LLM支持** | OpenAI / Anthropic / MiniMax / DeepSeek / Qwen / GLM | 多模型 |
| **存储** | SQLite + ChromaDB | 元数据+向量双存储 |
| **日志** | Loguru | 结构化日志 |
| **可选** | PostgreSQL + Redis + Neo4j | 分布式部署 |

---

## 八、模块演进说明

| 模块 | 状态 | 说明 |
|------|------|------|
| `server/` | **新增** | 从 api_server.py 迁移 |
| `agents/` | **新增** | 新版Agent框架，ReAct Loop |
| `orchestration/` | **新增** | 编排兼容层 |
| `harness/` | **新增** | 质量保障兼容层 |
| `workflow/` | 预留 | 预留工作流目录（空） |
| `unified/` | 保留 | 向后兼容，继续使用 |
| `langgraph_workflow/` | 保留 | LangGraph工作流 |

---

**文档版本**: v4.0
**更新日期**: 2026-05-03
**基于代码版本**: fresh-start branch
**代码结构**: `src/agents_v2/` 目录下实际存在的文件结构
