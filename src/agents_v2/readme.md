# Paper-Agent — 基于多源检索与GraphRAG的学术文献研究系统

> 项目周期：2026年4月 - 2026年5月

---

## 项目概述

面向学术文献调研场景，输入研究问题后自动完成多源检索、去重排序、GraphRAG图谱构建与可溯源综述报告生成，基于LangGraph 20+节点StateGraph统一编排搜索、写作、报告、问答、修订5条工作流路径，串联从问题拆解到报告输出的完整调研流水线。

**技术栈**：Python / aiohttp / asyncio / LangGraph / LangChain / Pydantic / Cross-Encoder / GraphRAG / Neo4j / PostgreSQL / Redis / Qwen3-Embedding / React / G6

---

## 主要功能模块

### 1. 意图识别与路由

通过口语术语映射与多维查询重写消歧用户输入，再经关键词→语义向量→LLM三级级联意图路由，按意图分发至搜索、写作、报告、问答、修订5条工作流路径，支持**16种意图类型**（难负样本挖掘配合Few-shot迭代优化）。

### 2. 多源检索与问题拆解

基于GPT Researcher树状递归思路，aiohttp + asyncio**四路并发**调度arXiv、PubMed、Semantic Scholar、OpenAlex、CrossRef五个平台，实现RateManager频率管理、TTLCache缓存与熔断降级，支持**FAST/BALANCED/COMPREHENSIVE/PRECISE四种搜索策略**，响应时间**3-5秒**。

### 3. 文献融合与排序

结合BM25关键词检索与Learning to Rank排序学习，**top_k=20**候选检索经DOI/标题两级去重与跨源合并后，经Cross-Encoder语义重排序保留前5（rerank_top_k=5），基于相关性、质量、新颖性三维评分与置信度融合形成最终候选文献集合。

### 4. GraphRAG文献关系分析

通过轻量分类器路由抽取论文、方法、任务、引用等实体关系，复杂关系由大模型补全，构建知识图谱；检索时先取图谱1-hop子图缩小语义空间，再与向量检索融合排序，答案附来源ID可溯源；**Louvain/Leiden社区检测**发现子领域聚类，辅助判断检索覆盖面，Neo4j存储。

### 5. 证据溯源与引用管理

参考PaperQA证据式问答设计，维护文献片段、DOI元数据、引用格式和结论来源绑定，支持**APA/MLA/GB/T 7714/TURABIAN四种引用格式**，CrossRef API校验作者年份信息，建立从用户问题到原始文献的端到端溯源链。

### 6. Generator-Critic写作闭环

参考NUS PaperDebugger的Diff补丁机制与SciSage的Reflect-When-You-Write三层反思思路，设计Writer→Reviewer→Evaluator生成-批评循环；主题可行性采用**文献充足性、方法可行性、创新性、时间合理性、资源可获取性5维评分**，7维度加权评分驱动章节迭代，最大**3轮迭代**、改进增量<0.1早停控制。

### 7. 质量保障与评估

设计Harness评估体系，从**答案相关性、忠实度、上下文精确度、幻觉检测、置信度校准、多跳推理6个维度**自动评估输出质量；引入CheckpointManager实现工作流断点恢复，CircuitBreaker在错误率超30%或连续失败5次时自动熔断，结合RAGAS追踪生成质量。

---

## 量化指标对照表

| 指标 | 值 | 来源 |
|------|-----|------|
| 搜索响应时间 | 3-5秒 | 实测：4个API并发调用 |
| 并发度 | 4 | MAIN_SEARCH_CONCURRENCY=4 |
| 检索top_k | 20 | top_k=20候选 |
| 重排序top_k | 5 | rerank_top_k=5 |
| 搜索策略 | 4种 | FAST/BALANCED/COMPREHENSIVE/PRECISE |
| 意图类型 | 16种 | IntentType枚举（含UNKNOWN） |
| 引用格式 | 4种 | APA/MLA/GB/T 7714/TURABIAN |
| 评分维度 | 5维10分制 | literature_adequacy/method_feasibility/novelty/time_reasonableness/resource_accessibility |
| QA评估 | 6项 | Faithfulness/Answer Relevance/Context Precision等 |
| 迭代轮数 | 最大3轮 | 改进增量<0.1早停 |
| 熔断条件 | 错误率>30%或连续5次失败 | CircuitBreaker配置 |
| LLM超时 | TIME_LIMIT=120s | 环境变量配置 |

---

## 目录结构

```
agents_v2/
├── __init__.py
├── readme.md
├── logging_config.py
│
├── core/                    # 基础层：Agent 基类、配置、类型定义
│   ├── base_agent.py
│   ├── config.py            # YAML 配置管理 + 16 模型注册表
│   ├── exceptions.py
│   ├── streaming.py         # SSE 流式输出支持
│   ├── validators.py
│   ├── plugins.py
│   ├── security.py
│   ├── rbac.py
│   └── enhanced_base.py
│
├── api/                     # RESTful API 路由模块
│   ├── paper_api.py
│   ├── reports_api.py
│   ├── knowledge_graph_api.py
│   └── workflow_api.py
│
├── unified/                 # 编排层：多阶段监督与质量保障
│   ├── master_supervisor.py # MasterSupervisor 6 阶段编排
│   ├── phase_supervisor.py
│   ├── circuit_breaker.py   # 熔断保护
│   ├── intent_router.py     # 意图路由（16种意图类型）
│   └── pydantic_validator.py
│
├── paper_agents/            # 论文写作流水线 Agent
│   ├── base_paper_agent.py
│   ├── topic_agent.py       # 选题 Agent（5维可行性评分）
│   ├── literature_agent.py  # 文献调研 Agent
│   ├── thesis_agent.py
│   ├── outline_agent.py
│   ├── draft_writer.py
│   ├── editor_agent.py
│   └── reviewer_agent.py
│
├── writing/                 # 写作支持：生成、修订、润色
│   ├── draft_generator.py
│   ├── outline_generator.py
│   ├── smart_reviser.py
│   ├── report_refiner.py
│   ├── literature_review.py
│   ├── reference_processor.py
│   └── reflection_engine.py
│
├── problem_oriented/        # 问题诊断与质量检查
│   ├── base_problem_agent.py
│   ├── language_polisher.py
│   ├── methodology_advisor.py
│   └── literature_mapper.py
│
├── academic_qa/            # 学术 QA 系统（RAG 架构）
│   ├── system.py
│   ├── ragas_evaluator.py    # RAGAS 评估指标
│   ├── confidence_calibrator.py
│   ├── hybrid_retriever.py
│   ├── hallucination_detector.py
│   ├── multi_hop_reasoner.py
│   └── query_decomposer.py
│
├── paper_search/           # 学术搜索
│   ├── paper_search.py
│   └── query_router.py
│
├── search/                  # 学术搜索引擎适配器
│   ├── arxiv_searcher.py
│   ├── pubmed_searcher.py
│   ├── semantic_scholar_searcher.py
│   ├── strategies.py        # 搜索策略（FAST/BALANCED/COMPREHENSIVE/PRECISE）
│   └── search_orchestrator.py
│
├── retrieval/               # RAG 检索增强管线
│
├── knowledge_graph/         # 知识图谱系统
│   └── community_detection.py # Louvain/Leiden 社区检测
│
├── memory/                  # 记忆系统（短期/长期/情景记忆）
│
├── langgraph_workflow/     # LangGraph 工作流定义
│   ├── unified_workflow.py
│   ├── workflow.py
│   ├── edges.py
│   ├── nodes/
│   │   ├── diagnostic.py
│   │   ├── literature.py
│   │   ├── memory.py
│   │   ├── outline.py
│   │   ├── polish.py
│   │   ├── reviewer.py
│   │   ├── writer.py
│   │   └── evaluator.py
│   └── observability/
│       └── tracer.py        # OpenTelemetry 链路追踪
│
├── reports/                 # 报告生成
│   ├── base.py
│   ├── daily.py
│   ├── weekly.py
│   └── monthly.py
│
├── common/                  # 公共模块
│   ├── citation/            # 引用处理
│   │   ├── citation_formatter.py
│   │   ├── citation_parser.py
│   │   └── citation_tracker.py
│   └── llm/                # LLM 工厂
│       └── llm_factory.py
│
├── embedding/              # 向量嵌入（本地 Qwen3-Embedding）
│   ├── local_embedding.py
│   └── model.safetensors
│
├── state/                   # 状态管理与检查点
│
├── evaluation/             # 评估与测试工具
│
├── monitoring/             # 监控告警
│   └── otel_tracer.py      # OpenTelemetry 追踪
│
├── prompts/                 # Prompt 模板
│   └── coherence_prompts.py
│
├── intent/                  # 意图识别
│   └── registry.py
│
├── routing/                # 路由选择
│
├── scheduler/              # 定时调度
│
├── storage/               # 存储
│
├── multimodal/           # 多模态处理
│
├── config/               # 配置
│
├── sdk/                   # Claude Agent SDK 框架
│
├── skills/                # Agent Skills 系统
│
├── tools/                 # 工具系统
│
└── demos/                 # 演示脚本
```

---

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

### 内置 API 路径

```
POST /api/topic       → handle_topic()      → TopicAgent (paper_agents)
POST /api/search      → handle_search()     → PaperSearchAgent (academic_qa)
POST /api/route       → handle_route()      → IntentRouter (unified, 16种意图类型)
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

---

## 快速启动

```bash
# 启动 API 服务
python -m src.agents_v2.api_server

# 或使用完整论文生成
python -m demos.full_paper.runner "深度学习医学图像诊断" --paper-only
```

## 导入示例

```python
from src.agents_v2 import BaseAgent, LLMConfig          # 基础类
from src.agents_v2 import MasterSupervisor              # 编排
from src.agents_v2 import PaperSearchAgent, QueryRouter  # 搜索问答
from src.agents_v2.paper_agents import TopicAgent        # 写作 Agent
```

---

*最后更新：2026-05-23*