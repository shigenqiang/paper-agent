# PaperAgent 智能学术论文研究助手

## 项目概述

PaperAgent 是一个基于多 Agent 协作架构的智能学术论文研究助手，采用 Python aiohttp 后端 + React + Vite 前端架构，旨在解决学术研究中的三大痛点：

1. **信息过载** - 日增数千篇论文难以筛选
2. **报告耗时** - 2-4 小时整理文献
3. **写作门槛高** - 选题缺乏评估、修改迭代效率低

---

## 技术架构

### 后端 (Python aiohttp)
- **位置**: `src/agents_v2/`
- **核心框架**: asyncio + aiohttp
- **Agent 数量**: 40+ 个专业 Agent
- **Python 文件**: 311 个
- **存储**: SQLite + ChromaDB (论文), SQLite (记忆系统)
- **认证方式**: API Key

### 前端 (React + Vite + Ant Design)
- **位置**: `frontend/src/`
- **页面数量**: 9 个
- **状态管理**: Zustand (9 个 Store)
- **路由**: React Router
- **UI 组件**: Ant Design + G6 图可视化

---

## Agent 系统详解

### Agent 总数: 40+ 个

### 1. 基础基类 (5个)

| 基类 | 文件 | 用途 |
|-----|------|-----|
| `BaseAgent` | `src/agents_v2/base_agent.py` | 核心 Agent 接口，能力注册 |
| `PaperAgentBase` | `src/agents_v2/paper_agents/base_paper_agent.py` | 论文写作流程 Agent 基类 |
| `WritingAgentBase` | `src/agents_v2/writing/base_writing_agent.py` | 完整论文写作 Agent 基类 |
| `ProblemAgentBase` | `src/agents_v2/problem_oriented/base_problem_agent.py` | 问题诊断 Agent 基类 |
| `BaseQAAgent` | `src/agents_v2/paper_search/base_qa_agent.py` | 问答 Agent 基类 |

---

### 2. Pipeline Agent (流水线 Agent - 9个)

按顺序执行论文写作全流程：

| Agent | 文件 | 功能 | 关键特性 |
|-------|------|-----|---------|
| `TopicAgent` | `paper_agents/topic_agent.py` | 选题与细化 | 生成候选主题，可行性评估，领域分析 |
| `LiteratureAgent` | `paper_agents/literature_agent.py` | 文献检索与综述 | 多源搜索(arXiv/PubMed)，质量排序，gap识别 |
| `ThesisAgent` | `paper_agents/thesis_agent.py` | 论点凝练 | 分析现有研究，定义动机与范围 |
| `OutlineAgent` | `paper_agents/outline_agent.py` | 大纲设计 | 章节规划，关键论点识别 |
| `DraftWriterAgent` | `paper_agents/draft_writer.py` | 初稿撰写 | 并行章节写作，内容连贯性 |
| `EditorAgent` | `paper_agents/editor_agent.py` | 内容修订 | 内容修改，语言润色，格式调整 |
| `ReviewerAgent` | `paper_agents/reviewer_agent.py` | 最终评审 | 多视角批判，质量评分 |
| `DigestAgent` | `paper_agents/digest_agent.py` | 论文摘要 | 快速摘要提取，论文对比 |

---

### 3. Problem-Oriented Agent (问题导向 Agent - 10个)

针对特定论文问题进行诊断与修复：

| Agent | 文件 | 目标问题 | 工作流程 |
|-------|------|---------|---------|
| `TopicRefinerAgent` | `topic_refiner.py` | 选题太宽泛/缺乏创新 | 分析范围，评估可行性/新颖性，生成细化选题 |
| `ResearchGapAgent` | `research_gap.py` | 无法识别研究空白 | 全面搜索，分类整理，gap分析 |
| `LiteratureMapperAgent` | `literature_mapper.py` | 文献不足 | 多角度搜索，论文分类，gap识别 |
| `MethodologyAdvisorAgent` | `methodology_advisor.py` | 研究方法问题 | 方法推荐，检查严谨性，识别问题 |
| `ArgumentBuilderAgent` | `argument_builder.py` | 论点薄弱 | 构建论点框架，检查连贯性，识别gap |
| `SectionDifferentiatorAgent` | `section_differentiator.py` | 摘要/结论重复 | 检查差异化，识别重复内容 |
| `DiscussionDeepenerAgent` | `discussion_deepener.py` | 讨论浅薄 | 评估深度，指导对比，建议未来方向 |
| `ChartFormatterAgent` | `chart_formatter.py` | 图表不规范 | 检查图表规范，优化信息展示 |
| `PlagiarismCheckerAgent` | `plagiarism_checker.py` | 抄袭风险 | 识别高风险段落，建议改写 |
| `LanguagePolisherAgent` | `language_polisher.py` | 语言质量问题 | Trinka API 语法检查，术语规范化 |

---

### 4. Writing Agent (写作 Agent - 9个)

专注独立写作能力：

| Agent | 文件 | 功能 | 关键特性 |
|-------|------|-----|---------|
| `LiteratureReviewAgent` | `literature_review.py` | 文献综述生成 | 多模式(full_review/tracking/summary)，多源搜索 |
| `OutlineGeneratorAgent` | `outline_generator.py` | 完整大纲生成 | 章节结构设计，内容规划，质量评估 |
| `DraftGeneratorAgent` | `draft_generator.py` | 完整草稿生成 | 逻辑连贯检查，自我修订，并行章节生成 |
| `ReportRefinerAgent` | `report_refiner.py` | 多轮迭代精炼 | review-refine循环，质量阈值驱动迭代 |
| `ReviewerAgent` | `report_refiner.py` | 单轮质量评审 | 结构/逻辑/论点/引用/语言评分 |
| `ProposalGeneratorAgent` | `proposal_generator.py` | 开题报告生成 | 任务书+提案生成 |
| `ReferenceProcessorAgent` | `reference_processor.py` | 参考文献管理 | 格式化(APA/MLA/Chicago/IEEE)，验证，完整性检查 |
| `SmartReviserAgent` | `smart_reviser.py` | 智能修订 | 反馈解析，分类修订，修订报告生成 |
| `LanguagePolisherAgent` | `smart_reviser.py` | 语言润色 | Trinka API集成，多级润色(轻/中/重) |

---

### 5. QA/Paper Search Agent (问答与论文搜索 - 7个)

专注搜索与报告生成：

| Agent | 文件 | 功能 | 关键特性 |
|-------|------|-----|---------|
| `PaperSearchAgent` | `paper_search/paper_search.py` | 学术论文搜索 | arXiv/PubMed/Semantic Scholar/OpenAlex 并行搜索 |
| `QueryRouter` | `paper_search/query_router.py` | 问题类型路由 | BASIC_QUERY/PROFESSIONAL/FRONTIER/APPLICATION 分类 |
| `CitationManager` | `paper_search/citation_manager.py` | 引用管理 | 多格式支持(APA/MLA/Chicago/IEEE/Nature) |
| `ReportGenerator` | `paper_search/report_generator.py` | 报告生成 | 论文分析，对比，结构化Markdown报告 |
| `DailyWatcher` | `paper_search/daily_watcher.py` | 日报监控 | 关键词跟踪，趋势识别，日度总结 |
| `WeeklyReportGenerator` | `paper_search/weekly_report.py` | 周报生成 | 多关键词聚合，方法分类，新兴趋势 |
| `MonthlyReportGenerator` | `paper_search/monthly_report.py` | 月报生成 | 周度分解，作者统计，研究gap分析 |

---

### 6. Supervisor/Orchestrator (编排器 - 3个)

负责全局协调：

| Supervisor | 文件 | 功能 |
|------------|------|-----|
| `IntentRouter` | `unified/intent_router.py` | 用户意图检测，多意图支持，路由到合适Agent |
| `MasterSupervisor` | `unified/master_supervisor.py` | 全文流水线全局编排，阶段协调，质量阈值管理 |
| `PhaseSupervisor` | `unified/phase_supervisor.py` | 每阶段Agent执行，并行/顺序/自适应执行模式 |

---

## Agent 架构图

```
MasterSupervisor
├── IntentRouter (路由用户请求)
├── PhaseSupervisor (6阶段: diagnostic → topic → literature → methodology → writing → polish)
│   ├── Problem-Oriented Agents (诊断/修复问题)
│   │   ├── TopicRefinerAgent
│   │   ├── LiteratureMapperAgent
│   │   ├── MethodologyAdvisorAgent
│   │   ├── ArgumentBuilderAgent
│   │   ├── SectionDifferentiatorAgent
│   │   ├── DiscussionDeepenerAgent
│   │   ├── ChartFormatterAgent
│   │   ├── PlagiarismCheckerAgent
│   │   └── LanguagePolisherAgent
│   │
│   ├── Pipeline Agents (流水线: topic → literature → thesis → outline → draft → editor → reviewer)
│   │   ├── TopicAgent
│   │   ├── LiteratureAgent
│   │   ├── ThesisAgent
│   │   ├── OutlineAgent
│   │   ├── DraftWriterAgent
│   │   ├── EditorAgent
│   │   └── ReviewerAgent
│   │
│   └── Writing Agents (独立写作能力)
│       ├── LiteratureReviewAgent
│       ├── OutlineGeneratorAgent
│       ├── DraftGeneratorAgent
│       ├── ReportRefinerAgent
│       ├── ProposalGeneratorAgent
│       ├── ReferenceProcessorAgent
│       ├── SmartReviserAgent
│       └── LanguagePolisherAgent
│
└── QA Agents (搜索与报告)
    ├── PaperSearchAgent
    ├── QueryRouter
    ├── CitationManager
    ├── ReportGenerator
    ├── DailyWatcher
    ├── WeeklyReportGenerator
    └── MonthlyReportGenerator
```

---

## 核心功能特性

### 1. 长链推理
- **ReAct 范式**: 意图识别 → 问题分解 → 多源检索 → 知识聚合 → 报告生成 → 质量评估 → 迭代优化
- **意图分类**: BASIC_QUERY / PROFESSIONAL / FRONTIER / APPLICATION 四类

### 2. 多源检索
- **平台**: arXiv、PubMed、Semantic Scholar、DBLP、OpenAlex
- **查询扩展**: 同义词库（"深度学习" → "neural network, CNN, transformer"）
- **结果融合**: 相关性0.6 + 引用数0.3 + 时效性0.1 加权评分

### 3. 知识图谱
- **存储**: Neo4j
- **功能**: 论文引用关系、作者合作网络、主题关联强度

### 4. 订阅推送
- **调度**: Cron 表达式
  - 日报: `0 9 * * *`
  - 周报: `0 9 * * 1`
  - 月报: `0 9 1 * *`
- **快讯类型**: HOT热点、TRENDING趋势、CONFERENCE顶会

---

## 前端页面

| 页面 | 文件 | 功能 |
|-----|------|-----|
| 首页/论文列表 | `pages/HomePage.jsx` | 论文列表、创建、删除 |
| 写作页面 | `pages/WritingPage.jsx` | 大纲编辑、内容生成、AI对话 |
| 大纲页面 | `pages/OutlinePage.jsx` | AI生成大纲、模板选择 |
| 文献页面 | `pages/LiteraturePage.jsx` | 文献搜索、管理 |
| 资讯页面 | `pages/ReportsPage.jsx` | 日报、周报、月报 |
| 知识图谱 | `pages/KnowledgeGraphPage.jsx` | 图谱可视化、社区检测 |
| 设置页面 | `pages/SettingsPage.jsx` | API配置、参数设置 |

---

## 项目文件结构

```
D:\pycharmprojects\pythonProject1\
├── src/agents_v2/                  # 后端 Agent 系统 (311 Python 文件)
│   ├── api_server.py               # aiohttp HTTP 服务入口
│   ├── main.py                     # 入口: python -m src.main
│   ├── logging_config.py           # Loguru 日志配置
│   │
│   ├── core/                       # 核心基础层
│   │   ├── base_agent.py           # BaseAgent 基类
│   │   ├── config.py               # YAML 配置 + 16 模型注册
│   │   ├── llm_fallback.py         # LLM 降级策略
│   │   └── react_executor.py       # ReAct 执行器
│   │
│   ├── api/                        # RESTful API 路由
│   │   ├── paper_api.py            # 论文 CRUD
│   │   ├── reports_api.py          # 报告 API
│   │   ├── knowledge_graph_api.py  # 知识图谱 API
│   │   └── workflow_api.py         # 工作流 API
│   │
│   ├── unified/                    # 统一编排框架
│   │   ├── intent_router.py        # 意图路由 (11 种意图)
│   │   ├── master_supervisor.py    # 全局编排器
│   │   └── phase_supervisor.py     # 阶段监督器
│   │
│   ├── paper_agents/               # Pipeline Agents (9 个)
│   │   ├── topic_agent.py          # 选题与细化
│   │   ├── literature_agent.py     # 文献检索
│   │   ├── thesis_agent.py         # 论点凝练
│   │   ├── outline_agent.py        # 大纲设计
│   │   ├── draft_writer.py         # 初稿撰写
│   │   ├── editor_agent.py         # 内容修订
│   │   ├── reviewer_agent.py       # 最终评审
│   │   └── digest_agent.py         # 论文摘要
│   │
│   ├── problem_oriented/           # Problem Agents (10 个)
│   │   ├── topic_refiner.py        # 选题精炼
│   │   ├── research_gap.py         # 研究空白识别
│   │   ├── literature_mapper.py    # 文献映射
│   │   ├── methodology_advisor.py  # 方法论指导
│   │   ├── argument_builder.py     # 论点构建
│   │   └── language_polisher.py     # 语言润色
│   │
│   ├── paper_search/               # 搜索与报告 (7 个)
│   │   ├── paper_search.py         # 多源论文搜索
│   │   ├── daily_watcher.py        # 日报监控
│   │   └── monthly_report.py       # 月报生成
│   │
│   ├── writing/                    # Writing Agents (17 个)
│   │   ├── outline_generator.py    # 大纲生成
│   │   ├── draft_generator.py     # 初稿生成
│   │   ├── smart_reviser.py        # 智能修订
│   │   └── literature_review.py   # 文献综述
│   │
│   ├── memory/                     # 记忆系统 v4 (20 个)
│   │   ├── unified.py              # 统一记忆管理器
│   │   ├── short_term.py           # 短期记忆
│   │   └── long_term.py           # 长期记忆
│   │
│   ├── knowledge_graph/            # 知识图谱 (12 个)
│   ├── retrieval/                  # RAG 检索 (26 个)
│   ├── langgraph_workflow/        # LangGraph 工作流
│   └── storage/                    # 存储层 (SQLite + ChromaDB)
│
├── frontend/src/                   # 前端 React 应用
│   ├── pages/                      # 9 个页面
│   ├── components/                 # 通用组件
│   └── store/                      # Zustand 状态管理
│
├── docs/                           # 文档 (30+ 份)
├── tests/                          # 测试
└── data/                           # 数据存储
```

---

## 快速链接

- [前后端接口对照表](./开发文档/前后端接口对照表.md)
- [Agent开发最佳实践](./开发文档/Agent开发最佳实践.md)
- [论文Agent核心组件调研报告](./03_核心架构/论文Agent核心组件调研报告.md)
- [论文Agent执行链路](./03_核心架构/论文Agent执行链路.md)
