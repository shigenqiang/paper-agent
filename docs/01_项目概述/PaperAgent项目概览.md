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
- **Agent 数量**: 37 个专业 Agent
- **图谱存储**: Neo4j
- **认证方式**: API Key

### 前端 (React + Vite + Ant Design)
- **位置**: `frontend/src/`
- **状态管理**: Zustand (paperStore)
- **路由**: React Router
- **UI 组件**: Ant Design

---

## Agent 系统详解

### Agent 总数: 37 个

### 1. 基础基类 (5个)

| 基类 | 文件 | 用途 |
|-----|------|-----|
| `BaseAgent` | `src/agents_v2/base_agent.py` | 核心 Agent 接口，能力注册 |
| `PaperAgentBase` | `src/agents_v2/paper_agents/base_paper_agent.py` | 论文写作流程 Agent 基类 |
| `WritingAgentBase` | `src/agents_v2/writing/base_writing_agent.py` | 完整论文写作 Agent 基类 |
| `ProblemAgentBase` | `src/agents_v2/problem_oriented/base_problem_agent.py` | 问题诊断 Agent 基类 |
| `BaseQAAgent` | `src/agents_v2/qa/base_qa_agent.py` | 统计问答 Agent 基类 |

---

### 2. Pipeline Agent (流水线 Agent - 8个)

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

### 3. Problem-Oriented Agent (问题导向 Agent - 9个)

针对特定论文问题进行诊断与修复：

| Agent | 文件 | 目标问题 | 工作流程 |
|-------|------|---------|---------|
| `TopicRefinerAgent` | `topic_refiner.py` | 选题太宽泛/缺乏创新 | 分析范围，评估可行性/新颖性，生成细化选题 |
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
| `PaperSearchAgent` | `qa/paper_search.py` | 学术论文搜索 | arXiv + PubMed 并行搜索，相关性排序，去重 |
| `QueryRouter` | `qa/query_router.py` | 问题类型路由 | BASIC_QUERY/PROFESSIONAL/FRONTIER/APPLICATION 分类 |
| `CitationManager` | `qa/citation_manager.py` | 引用管理 | 多格式支持(APA/MLA/Chicago/IEEE/Nature) |
| `ReportGenerator` | `qa/report_generator.py` | 报告生成 | 论文分析，对比，结构化Markdown报告 |
| `DailyWatcher` | `qa/daily_watcher.py` | 日报监控 | 关键词跟踪，趋势识别，日度总结 |
| `WeeklyReportGenerator` | `qa/weekly_report.py` | 周报生成 | 多关键词聚合，方法分类，新兴趋势 |
| `MonthlyReportGenerator` | `qa/monthly_report.py` | 月报生成 | 周度分解，作者统计，研究gap分析 |

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
├── src/
│   └── agents_v2/
│       ├── base_agent.py              # Agent基类
│       ├── config.py                  # 配置
│       ├── config_manager.py          # 配置管理
│       ├── roles/
│       │   └── agent_roles.py         # 角色定义
│       ├── paper_agents/              # Pipeline Agents
│       │   ├── base_paper_agent.py
│       │   ├── topic_agent.py
│       │   ├── literature_agent.py
│       │   ├── thesis_agent.py
│       │   ├── outline_agent.py
│       │   ├── draft_writer.py
│       │   ├── editor_agent.py
│       │   ├── reviewer_agent.py
│       │   └── digest_agent.py
│       ├── problem_oriented/           # Problem Agents
│       │   ├── base_problem_agent.py
│       │   ├── topic_refiner.py
│       │   ├── literature_mapper.py
│       │   ├── methodology_advisor.py
│       │   ├── argument_builder.py
│       │   ├── section_differentiator.py
│       │   ├── discussion_deepener.py
│       │   ├── chart_formatter.py
│       │   ├── plagiarism_checker.py
│       │   └── language_polisher.py
│       ├── writing/                   # Writing Agents
│       │   ├── base_writing_agent.py
│       │   ├── literature_review.py
│       │   ├── outline_generator.py
│       │   ├── draft_generator.py
│       │   ├── report_refiner.py
│       │   ├── proposal_generator.py
│       │   ├── reference_processor.py
│       │   └── smart_reviser.py
│       ├── qa/                       # QA Agents
│       │   ├── base_qa_agent.py
│       │   ├── paper_search.py
│       │   ├── query_router.py
│       │   ├── citation_manager.py
│       │   ├── report_generator.py
│       │   ├── daily_watcher.py
│       │   ├── weekly_report.py
│       │   └── monthly_report.py
│       └── unified/                  # Orchestrators
│           ├── intent_router.py
│           ├── master_supervisor.py
│           └── phase_supervisor.py
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── HomePage.jsx
│       │   ├── WritingPage.jsx
│       │   ├── OutlinePage.jsx
│       │   ├── LiteraturePage.jsx
│       │   ├── ReportsPage.jsx
│       │   ├── KnowledgeGraphPage.jsx
│       │   └── SettingsPage.jsx
│       ├── services/
│       │   └── api.js                # API封装
│       └── store/
│           └── paperStore.js         # 状态管理
└── docs/
    └── 开发文档/
        ├── 前后端接口对照表.md
        └── ...
```

---

## 快速链接

- [前后端接口对照表](./开发文档/前后端接口对照表.md)
- [Agent开发最佳实践](./开发文档/Agent开发最佳实践.md)
- [论文Agent核心组件调研报告](./03_核心架构/论文Agent核心组件调研报告.md)
- [论文Agent执行链路](./03_核心架构/论文Agent执行链路.md)
