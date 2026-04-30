# 论文 Agent 前沿开发报告

> 调研日期：2026-05-01
> 基于：全网 Agent 框架调研 + 学术论文 Agent 系统调研 + 大学生论文需求调查 + 论文网站功能分析

---

## 目录

1. [全球 Agent 框架格局](#1-全球-agent-框架格局)
2. [学术论文 Agent 前沿系统](#2-学术论文-agent-前沿系统)
3. [大学生论文写作需求与痛点](#3-大学生论文写作需求与痛点)
4. [现有论文写作工具功能分析](#4-现有论文写作工具功能分析)
5. [Agent Harness 设计范式](#5-agent-harness-设计范式)
6. [论文 Agent 架构设计方案](#6-论文-agent-架构设计方案)
7. [功能矩阵设计](#7-功能矩阵设计)
8. [开发路线图](#8-开发路线图)

---

## 1. 全球 Agent 框架格局

### 1.1 三大主流框架对比（2025-2026）

| 维度 | 🕸️ LangGraph | 🚢 CrewAI | 🔁 AutoGen/MAF |
|------|:---:|:---:|:---:|
| **编排模式** | 有向图状态机 | 角色组队（Crew/Role/Task） | 对话/事件驱动 |
| **最适合** | 有状态复杂工作流、生产系统 | 快速多 Agent 原型 | 代码生成、迭代推理 |
| **学习曲线** | 高（需要图思维） | 低（类自然语言） | 中 |
| **原型速度** | 4-8周到生产 | **2-4小时** | 中等 |
| **生产成熟度** | ★★★★★ (Klarna, Uber, Elastic) | ★★★★☆ (IBM, Shopify) | ★★★★☆ |
| **可观测性** | LangSmith（内置追踪） | 第三方 | Azure Telemetry |
| **Human-in-the-Loop** | 原生支持（interrupt节点、checkpoint） | 通过Flows支持 | 原生审批检查点 |
| **Token效率** | 高（~12,400 tokens） | 高（~$0.12/次） | 较低（~24,200 avg） |
| **GitHub Stars** | ~28k | ~48k | ~56k |
| **许可证** | MIT | MIT | MIT |

### 1.2 2026年行业共识：混合使用策略

```
CrewAI 快速原型 → 验证可行性 → LangGraph 重写核心编排 → 生产部署
                                    ↑
                              AutoGen 子Agent处理代码执行
```

**关键趋势**：三个框架不是竞争者，而是同一技术栈的不同层。

### 1.3 2025-2026年全球Agent框架全景图

#### A. 企业级编排框架

| 框架 | 出品方 | Stars | 核心范式 | 特点 | 适用场景 |
|------|--------|:-----:|----------|------|----------|
| **LangGraph** | LangChain | ~28k | 有向图状态机 | 原生Checkpoint/HITL，LangSmith可观测 | 复杂有状态工作流 |
| **CrewAI** | 开源 | ~48k | 角色组队(Crew/Role/Task) | 类自然语言定义Agent，学习曲线最低 | 快速多Agent原型 |
| **AutoGen/MAF** | Microsoft | ~56k | 对话/事件驱动 | 代码生成能力强，Azure原生集成 | 代码生成、迭代推理 |
| **Semantic Kernel** | Microsoft | ~22k | 插件+规划器 | 模型无关SDK，.NET/Python双语言，企业级可靠性 | 企业应用、Microsoft生态 |
| **AgentScope** | 阿里通义 | ~12k | 消息驱动+分布式 | Python+Java双版本，SDK+Runtime+Studio三位一体 | 分布式多Agent、国内生态 |
| **CAMEL** | KAUST | ~18k | 角色扮演(Role-Playing) | 最早的ChatGPT多Agent框架，心智交互研究先驱 | 学术研究、角色扮演协作 |
| **Google ADK** | Google | ~5k | Pregel图算法 | 原生GCP集成 | Google生态 |
| **Claude Agent SDK** | Anthropic | - | Subagent+Tool+Skill | 18+内置工具、MCP原生、自动上下文压缩、权限系统 | Claude生态、企业Agent |

#### B. 2026 年 Agent 协议标准

2025-2026 年形成了四大开放协议标准，彻底改变了 Agent 基础设施格局：

| 协议 | 主导方 | 发布 | 解决的问题 | Paper Agent 关联 |
|------|--------|------|-----------|-----------------|
| **MCP** | Anthropic | 2024-11 | Agent ↔ 工具/数据源 标准化连接 | MCP Server (Arxiv, PubMed, SS) |
| **A2A** | Google → Linux基金会 | 2025-04 | Agent ↔ Agent 跨框架通信 (JSON-RPC + SSE) | 多Agent任务分发与结果同步 |
| **Agent Skills** | Anthropic | 2025-12 | 能力模块化封装 (SKILL.md + 渐进式披露) | paper-search / analysis / writing Skills |
| **AG-UI** | CopilotKit | 2025-05 | Agent ↔ 前端 实时交互 (16种事件类型) | 前端流式进度展示 |

**协议协同关系**: MCP是"手"(操作工具)，A2A是"口"(Agent通信)，Skills是"脑"(专业知识)，AG-UI是"脸"(用户交互)。互补非竞争。

#### C. 轻量/专用框架

| 框架 | 出品方 | 核心范式 | 特点 | 适用场景 |
|------|--------|----------|------|----------|
| **DSPy** | Stanford NLP | 声明式编程+自动优化 | 用Signatures替代手写Prompt，编译器自动优化提示词，MIPRO/BootstrapFewShot优化器 | LLM流水线自动优化 |
| **LlamaIndex** | 开源 | 数据索引+RAG | 专注RAG场景，丰富索引结构(Vector/Tree/Keyword/SQL)，Agent支持 | 企业级RAG、知识库问答 |
| **Haystack** | deepset | Pipeline组件化 | 端到端NLP框架，灵活的Pipeline组合，支持多种文档存储 | QA系统、语义搜索 |
| **Agno** | 开源 | 轻量Agent | 极致轻量、高并发、低延迟 | 高频推理、微服务Agent |
| **OpenAI Agents SDK** | OpenAI | Swarm编排+Handoff | 原生Tracing、Built-in Tools、Guardrails | OpenAI生态应用 |
| **Smolagents** | HuggingFace | Code Agent | 极简设计(~1000行)，Agent用代码表达行动 | 轻量Agent实验 |

#### C. 自主研究/任务型框架

| 框架 | 出品方 | 核心范式 | 特点 | 适用场景 |
|------|--------|----------|------|----------|
| **GPT Researcher** | Columbia AI | 规划-执行-聚合(Planner-Executor-Publisher) | 树状递归深度研究，聚合20+来源，单次研究~$0.4 | 自动研究报告生成 |
| **MetaGPT** | 深度赋智 | SOP编码(SOP-encoded) | 模拟软件公司角色，SOP驱动协作 | 代码生成、软件开发 |
| **TaskWeaver** | Microsoft | 代码优先(Code-First) | 将用户请求转化为可执行代码，支持复杂数据结构 | 数据分析、代码执行 |
| **AutoGPT** | 开源 | 自主任务链 | AI Agent先驱(15万Star)，任务自分解+执行循环 | 通用自主任务 |
| **BabyAGI** | 开源 | 任务驱动(Task-Driven) | 极简设计，无限循环创建/优先排序/执行任务 | AI任务管理实验 |

#### D. 可视化低代码平台

| 平台 | 出品方 | 核心范式 | 特点 | 适用场景 |
|------|--------|----------|------|----------|
| **Dify** | 开源 | 可视化工作流 | 完整的LLMOps平台，RAG Pipeline，Agent编排，对话管理 | 业务自动化、非技术人员 |
| **LangFlow** | 开源 | 拖拽式LangChain | LangChain可视化原型工具，导出Flow JSON | LangChain原型设计 |
| **Flowise** | 开源 | 拖拽式低代码 | 最简洁的LLM工作流搭建，节点式拖拽，一键API部署 | 快速搭建RAG/Agent |

### 1.4 框架选型决策矩阵

| 决策因素 | 推荐框架 |
|----------|----------|
| 快速验证多Agent创意 | CrewAI（2-4小时出原型） |
| 生产级论文写作流水线 | LangGraph（Checkpoint+HITL原生支持） |
| Claude生态Agent开发 | Claude Agent SDK（18+工具、MCP原生、Subagents） |
| LLM流水线自动优化 | DSPy（自动提示词工程） |
| 企业级RAG应用 | LlamaIndex（最全索引类型） |
| 分布式多Agent系统 | AgentScope（原生分布式支持） |
| 自动研究报告生成 | GPT Researcher（树状深度研究） |
| 微软生态企业应用 | Semantic Kernel（.NET+Azure原生） |
| Agent间通信标准化 | A2A协议（JSON-RPC + SSE + AgentCard） |
| Agent工具调用标准化 | MCP协议（Tools + Resources + Prompts） |

---

## 2. 学术论文 Agent 前沿系统

### 2.1 2025年核心论文 Agent 系统一览

#### A. PaperDebugger — 编辑器内嵌多Agent（2025.12）

| 项目 | 详情 |
|------|------|
| **团队** | 新加坡国立大学 |
| **定位** | **Overleaf内嵌**Chrome扩展的多Agent学术写作助手 |
| **GitHub** | github.com/PaperDebugger/PaperDebugger |
| **评分** | Chrome Store 4.9/5 |

**五层架构**：
```
表现层     → Chrome 扩展 + 脚本注入 (浮动UI、文本选择、Diff视图)
后端层     → Go + Kubernetes (认证、会话、gRPC流式)
Agent层    → Reviewer / Enhancer / Scorer / Researcher 四Agent
协议层     → MCP + XtraMCP (双向SSE流、模式校验)
基础设施层 → K8s集群 (水平扩展、容错)
```

**核心创新**：
- **Diff补丁机制**：像Git一样展示修改，用户一键Accept/Reject
- **两类Agent运行模式**：Prompt-template（轻量快速）+ Workflow-based（多步协调）
- **XtraMCP协议**：集成语义检索、AAAI风格多步审稿
- **用户数据**：112次安装 | 78位用户 | 158个项目 | 797次写作线程

---

#### B. SciSage — 边写边反思（2025.06）

| 项目 | 详情 |
|------|------|
| **团队** | Xiaofeng Shi 等 |
| **定位** | 高质量科学综述自动生成 |
| **范式** | **Reflect-When-You-Write** |

**三层反思架构**：
```
用户查询 → Query Interpreter Agent → Content Retrieval Agent
                                          ↓
                                   Outline-Level Reflector ←──┐
                                          ↓                   │
                                   Section-Level Reflector ───┤
                                          ↓                   │
                                   Document-Level Reflector ──┘
                                          ↓
                                   Refinement Agent → 终稿
```

**性能**：
- 连贯性得分高于基线 **+1.73**
- 引用F1分数提升 **+32%**
- 人类评估：3胜 / 7负 vs 人类撰写

---

#### C. WriteHERE — 异构递归规划（2025.03，EMNLP Oral）

| 项目 | 详情 |
|------|------|
| **团队** | Jürgen Schmidhuber 团队 (KAUST) |
| **定位** | 通用长文写作Agent，打破"先大纲后填充" |
| **GitHub** | github.com/principia-ai/WriteHERE |
| **奖项** | **EMNLP 2025 Outstanding Paper** |

**核心架构**：
```
Agent = ⟨Kernel, Memory, Environment, Workspace, IO⟩

三类原子任务：
  - 检索任务 (Retrieval)：从外部环境获取信息
  - 推理任务 (Reasoning)：逻辑校验、结构分析
  - 写作任务 (Composition)：在工作空间生成文本

状态化DAG调度：
  每个任务有 [激活/挂起/静默] 三种状态
  按依赖关系自适应执行
```

**性能**：
- 单次生成 **44,000+ 字、100+ 页**专业报告
- 8000词小说胜率超基线 **90%+**
- 技术报告信息相关性 **4.9/5**

---

#### D. Agent Laboratory — 自主科研流水线（2025.01）

| 项目 | 详情 |
|------|------|
| **团队** | AMD + 约翰斯·霍普金斯大学 |
| **GitHub** | github.com/SamuelSchmidgall/AgentLaboratory |

**三大阶段 + 四大Agent角色**：

```
阶段1: 文献综述     PhD Agent → arXiv检索 → 摘要/全文提取
阶段2: 实验         PhD + Postdoc + ML Engineer
       ├── 制定计划  PhD ↔ Postdoc 对话协作
       ├── 数据准备  ML Engineer 编写Python代码
       ├── 运行实验  ML Engineer + mle-solver自主优化
       └── 结果解释  PhD + Postdoc 提炼见解
阶段3: 报告撰写     PhD + Professor + paper-solver
       └── LaTeX初稿 → 引用检索 → 模拟审稿 → 修改完善
```

**关键数据**：
- 最佳模型：o1-preview（4.0/10总分）
- 代码能力：6/10达到高于人类中位数
- 成本降低 **84%** vs 传统自主研究
- Co-pilot模式：人类在各阶段介入，质量从 3.8→4.38

---

#### E. STORM/Co-STORM（Stanford）— AI驱动知识整合写作

| 项目 | 详情 |
|------|------|
| **团队** | 斯坦福大学 |
| **时间** | 2024推出，2025持续更新 |
| **定位** | 自动化编写维基百科式长篇文章 |
| **GitHub** | github.com/stanford-oval/storm |

**核心机制**：
```
用户输入主题 → 多源信息检索(数百个网站)
  → 多角度提问生成 → 模拟多专家对话
  → 信息综合与引用 → 结构化长文输出
```

**Co-STORM创新**：引入协作机制，支持人机交互式知识探索，解决单一AI生成的信息盲点问题。

---

#### F. 其他前沿系统

| 系统 | 时间 | 核心创新 | 来源 |
|------|------|----------|------|
| **AgRefine** | 2025.12 | Revision Planner + Language Expert + Iteration Reviewer三Agent修订 | IEEE ICA |
| **LiRA** | 2025.10 | Content Outlining → Subsection Writing → Editing → Reviewing四阶段 | arXiv |
| **Select-Read-Write** | 2025 ACL | Selector(选读) → Reader(消化) → Writer(生成) + Graph-aware阅读策略 | ACL 2025 |
| **Agentic AutoSurvey** | 2025.09 | Paper Search + Topic Mining + Survey Writer + Quality Evaluator四Agent | Lehigh Univ |
| **AIssistant** | 2025.09 | 端到端ML论文+LaTeX生成，成本<$1/篇 | arXiv |
| **TTD-DR (Google)** | 2025.09 | 扩散模型"去噪"研究草稿，74.5%胜率超OpenAI Deep Research | Google Research |
| **OmniScientist** | 2025.11 | 文献→构思→实验→写作→审稿全生命周期 | arXiv |
| **Loong** | 2025.09 | CAMEL-AI团队，通过Verifier合成大规模长链思维 | arXiv |

### 2.2 GPT Researcher 深度研究模式 — 树状递归探索

GPT Researcher（Columbia AI开源，21k+ stars）的"规划-执行-聚合"三阶段架构对论文Agent的文献综述模块有直接借鉴价值：

```
用户查询
  → Planner Agent: 生成一组研究问题（广度探索）
  → Executor Agents: 并行搜索20+在线资源（深度执行）
      ├── 每个子问题触发独立爬虫Agent
      ├── 递归深度探索（树状结构，depth>1时自动深入）
      └── 信号量控制并发（避免被限流）
  → Publisher Agent: 聚合所有发现 → 生成综合研究报告
```

**关键数据**：
- 聚合平均超过20个来源，避免单一来源偏见
- 深度研究模式单次约$0.4（使用特定模型）
- 支持本地文档 + 在线检索混合模式
- 向量数据库存储研究记忆（避免重复检索）

**对论文Agent的启示**：文献综述模块应借鉴此模式——先规划研究方向（广度），再对每个方向深入检索（深度），最后综合生成结构化综述。这与SciSage的"边写边反思"形成互补。

### 2.3 2025论文Agent系统架构共识

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator 编排层                     │
│         (任务分解 | 角色分配 | 流程控制 | 人机交互)         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ 检索Agent │  │ 规划Agent │  │ 写作Agent │  │ 评审Agent│ │
│  │(文献搜索  │  │(大纲/结构 │  │(章节撰写  │  │(质量检查 │ │
│  │论文筛选)  │  │ 任务分解) │  │ 综合合成) │  │引用验证) │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  共享基础设施层                                           │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐  │
│  │ Memory  │ │  Tools   │ │ State  │ │  Evaluator   │  │
│  │(短期/长期│ │(搜索/代码│ │(检查点 │ │(评分/验证)    │  │
│  │ 情景记忆)│ │ 执行/API)│ │ 持久化)│ │              │  │
│  └─────────┘ └──────────┘ └────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 大学生论文写作需求与痛点

### 3.1 核心数据（麦可思研究院2025年调查，3145份有效答卷）

| 数据项 | 比例 |
|--------|------|
| 教师认为学生"过度依赖AI" | **46%** |
| 学生遇难题首选AI（超咨询导师） | **65%** |
| 师生认为论文与培养目标脱节 | **80%教师 / 66%学生** |
| 支持取消本科生毕业论文 | **47%** |
| 希望用实践项目替代论文 | **75%学生** |
| 教师认为论文"临时拼凑、粗制滥造" | **75%** |

### 3.2 六大核心痛点

#### 痛点1：AI检测的混乱与不公
- 同一文章不同平台检测结果相差 **46%**
- 完全手写的"致谢"被判定为 **100% AI生成**
- 人工修改后AI率**不降反增**
- 学生仅检测费就花超200元

#### 痛点2：选题与研究方法的困难
- 找到"有创新性 + 有实际价值 + 好落实"的选题极难
- 数据收集难：问卷质量与样本量难以兼顾
- 专业语言障碍："大白话"难以达标

#### 痛点3：导师指导的盲区
- 导师年龄大、脱离一线研究
- 导师身在国外或跨校区，只能远程低频联系
- 文字沟通有歧义
- 导师任务量重，难以兼顾每位学生

#### 痛点4："防御性论证"与盲审焦虑
- 为应对外审把所有论证角度全堆上
- 论文厚度膨胀至8万字甚至10万+
- 教育部抽检不合格后果严重影响大

#### 痛点5：篇幅膨胀与"字数迷思"
- 本科论文：8000字→**2万字+**
- 硕士论文：3-5万字→**8-10万字+**
- "以页数论高下"的功利化竞争

#### 痛点6：心理压力与拖延
- 有学生因论文痛苦到"躺在床上不吃不喝"
- "很抗拒打开文档这个步骤"
- 焦虑、拖延普遍存在

### 3.3 学生核心需求映射

| 需求 | 优先级 | Agent可解决程度 |
|------|:------:|:---------------:|
| **选题指导**：找到创新+可行+有价值的选题 | ⭐⭐⭐⭐⭐ | 高 — 文献挖掘+研究空白分析 |
| **文献综述**：高效搜索、筛选、综合文献 | ⭐⭐⭐⭐⭐ | 高 — 多源搜索引擎+自动综述生成 |
| **结构化写作**：大纲生成、章节撰写、逻辑连贯 | ⭐⭐⭐⭐⭐ | 高 — 多层大纲+逐章生成+反思验证 |
| **AI检测规避**：降低AIGC率，同时保持学术质量 | ⭐⭐⭐⭐⭐ | 中 — 风格多样化+人工化润色 |
| **格式规范**：参考文献格式、排版、查重 | ⭐⭐⭐⭐ | 高 — 自动格式化+引用验证 |
| **语言润色**：专业学术语言、逻辑连贯性 | ⭐⭐⭐⭐ | 高 — 学术语言模型+审稿Agent |
| **导师协作**：版本管理、批注、Diff对比 | ⭐⭐⭐⭐ | 中 — 版本控制+审稿意见跟踪 |
| **数据/实验支持**：方法论建议、数据分析 | ⭐⭐⭐ | 中 — 代码生成+统计方法推荐 |
| **答辩准备**：PPT生成、可能问题预测 | ⭐⭐⭐ | 高 — 内容摘要+问答生成 |
| **心理健康**：缓解焦虑、分步引导 | ⭐⭐⭐ | 低 — 进度可视化+鼓励式交互 |

---

## 4. 现有论文写作工具功能分析

### 4.1 国内学术专用工具

| 工具 | 查重率 | 参考文献 | 特色功能 | 价格 | 不足 |
|------|:------:|----------|----------|------|------|
| **酷兔AI论文** | 知网~3% | 40篇知网/中科院文献 | 免费大纲、答辩PPT、降AIGC率 | 基础免费 | 高级功能付费 |
| **68爱写AI论文** | 知网~5% | 核心文献+出处 | 3万字长文无断层 | 付费 | 价格偏高 |
| **易笔AI论文** | 低 | 40篇中科院文献 | 700+学科、6种语言 | 付费 | 深度学术有限 |
| **PaperRed** | 低 | 权威数据库联动 | AIGC不限次检测、1500+格式 | 基础免费 | 高级功能49元/月 |
| **鲲鹏智写** | — | 智能索引 | 30分钟5万字、SPSS模拟 | 付费 | 质量参差 |

### 4.2 国际学术工具

| 工具 | 核心功能 | 语言 | 特色 | 价格 |
|------|----------|------|------|------|
| **Grammarly** | 语法检查+风格优化 | 英语 | 50万+应用集成 | 免费/Pro $12/月 |
| **QuillBot** | 改写+摘要+语法 | 30+语言 | Turnitin查重预检 | 免费/$8.33/月 |
| **Wordvice AI** | 学术校对+改写 | 多语言 | 百万字学术数据训练 | 免费/<$20/月 |
| **SciSpace** | PDF对话+文献检索 | 英语 | 2亿+论文库、Chat with PDF | 免费+付费 |
| **Jenni AI** | 研究写作+引用管理 | 英语 | 引用深度整合 | 免费+付费 |
| **Trinka AI** | 学术语法检查 | 英语 | 学术专用错误识别、LaTeX校对 | 免费+付费 |

### 4.3 现有工具的共性缺失

| 缺失能力 | 说明 |
|----------|------|
| **多Agent协作** | 现有工具多为单一LLM调用，缺少专业分工Agent |
| **深度论文理解** | 无法理解论文完整上下文，只能逐段处理 |
| **研究空白分析** | 缺少基于文献计量学的研究空白识别 |
| **可解释写作** | 生成内容不透明，无法追溯推理过程 |
| **版本控制集成** | 无Git式版本管理和协作审稿 |
| **全程Human-in-the-loop** | 缺少精细的人工审核介入点 |
| **学术诚信保障** | AIGC检测被动应对，缺乏主动式合规设计 |
| **个性化学习** | 无法根据用户写作风格和水平自适应 |
| **实验/数据支持** | 仅文本生成，无方法论指导和数据分析 |

---

## 5. Agent Harness 设计范式

### 5.1 三层架构：Framework → Runtime → Harness

这是2025年Agent系统设计的核心范式：

```
┌──────────────────────────────────────────────┐
│              HARNESS (评估 & 测试)             │
│  基准测试 | 回归检测 | 安全扫描 | 成本监控     │
├──────────────────────────────────────────────┤
│              RUNTIME (执行引擎)                │
│  状态管理 | 重试/降级 | 并行调度 | 持久化     │
├──────────────────────────────────────────────┤
│              FRAMEWORK (构建层)                │
│  Prompt | 工具 | 记忆 | 流程控制 | Agent组合  │
└──────────────────────────────────────────────┘
```

### 5.2 Agent Loop 核心模式

#### 模式1：ReAct（Reason + Act）— 基础循环
```
Observe → Think → Act → Observe → Think → Act → ...
```
最基础的Agent循环，2025年仍是大多数生产Agent的基础。

#### 模式2：Plan-Execute-Reflect — 升级循环
```
Plan (制定计划) → Execute (执行步骤) → Reflect (反思结果) → Replan (调整计划) → ...
```
引入元认知层，是WriteHERE和SciSage的核心机制。

#### 模式3：Generator-Critic 循环
```
Generator (生成草稿) → Critic (批判评估)
    ├── PASS → 输出
    └── FAIL → 反馈 → Generator (修改)
```
PaperDebugger的Reviewer + Enhancer配对就是此模式。

#### 模式4：多层Reflector（SciSage范式）
```
Outline-Level Reflector → Section-Level Reflector → Document-Level Reflector
```
不同粒度层次的反思机制，从宏观结构到微观表达。

#### 模式5：Heterogeneous Recursive Planning（WriteHERE范式）
```
Task Analysis → Type Tagging (检索/推理/写作) → Recursive Decomposition → DAG Schedule
```
根据任务类型动态分解为原子任务，用DAG管理依赖关系。

#### 模式6：DSPy Compiler Loop（声明式优化）
```
Define Signature → Compile with Optimizer → Evaluate Metric → Retry
    ↑                                                          ↓
    └──────────────────────────────────────────────────────────┘
                    (自动循环优化，无需人工调Prompt)
```
斯坦福NLP团队的范式创新：用Signatures替代手写Prompt，通过BootstrapFewShot、MIPRO等优化器自动调整提示词和示例。对论文Agent的启示——**将审稿评分作为优化信号**，自动提升论文生成质量。

#### 模式7：Tree-of-Recursive-Research（GPT Researcher范式）
```
Root Topic → Generate Sub-Questions (广度)
  → For each Sub-Q: Search & Extract (深度)
    → If depth > 1: Recursive Decompose (更深层)
  → Aggregate → Filter → Synthesize → Final Report
```
树状递归探索机制，以深度优先或广度优先的方式探索研究主题。对论文Agent的文献综述模块有直接借鉴价值。

#### 模式8：Multi-Perspective Expert Dialogue（STORM范式）
```
Topic → Generate Multi-Perspective Questions
  → Simulate Expert A ↔ Expert B Conversation
  → Cross-reference & Validate Claims
  → Synthesize into Structured Article
```
模拟不同领域专家对话，从多角度审视主题，减少信息盲点。适用于论文Agent的选题诊断和论点驳斥环节。

### 5.3 Harness设计关键要素

#### A. Checkpoint & Resume — 检查点与恢复

```python
# 检查点数据结构
class AgentCheckpoint:
    session_id: str
    phase: str                    # 当前阶段
    completed_steps: List[str]    # 已完成步骤
    pending_approval: bool        # 是否等待人工审批
    state_snapshot: Dict          # 完整状态快照
    message_history: List[Message] # 完整对话历史
    created_at: datetime
    updated_at: datetime
```

**2025年最佳实践**：
- **显式状态存储**（非运行时栈）：HITL事件写入Agent状态schema
- **Journal/Event Log**：每步操作追加到结构化消息数组
- **幂等设计**：重试不重复工作
- **数据库支持的Checkpointer**：LangGraph的SqliteSaver、Restate的持久化Promises

#### B. Human-in-the-Loop（HITL）

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Agent执行   │ ──→ │ 检查点暂停     │ ──→ │ 人工审核     │
│  (自动推进)  │     │ (保存状态)     │     │ (审批/修改)   │
└─────────────┘     └──────────────┘     └──────┬──────┘
      ↑                                         │
      └─────────────────────────────────────────┘
                   恢复执行
```

**中断策略**：
| 策略 | 说明 | 适用场景 |
|------|------|----------|
| Static Interrupt | 预定义节点 `interrupt_before` | 固定流程 |
| Dynamic Interrupt | 运行时状态判断 `interrupt()` | 条件触发 |
| Event-Driven HITL | 写入 `pending_hitl_event` | 前后端解耦 |

#### C. Durable Execution — 持久执行

Restate（2025年6月）提出的模式：

```
LLM调用 → [Journal写入] → 工具调用 → [Journal写入] → 下一步决策
              ↑ 失败时从此处重放 ↑
```

- 支持**无服务器挂起**：等待人工审批时关闭Agent，审批到达后恢复
- **Virtual Objects**：按session_id分片的持久化状态，并发控制

#### D. Eval-in-the-Loop — 持续评估

| 维度 | 指标 |
|------|------|
| **准确性** | Eval scores on curated benchmarks |
| **事实性** | Citation coverage, hallucination detection |
| **安全性** | Guardrail violation count, PII leaks |
| **延迟** | p50 / p95 response times |
| **成本** | Token usage per task |
| **工具正确性** | Tool failure rate, correct API call rate |

### 5.4 2025年生产化十诫

1. **从简单开始** — 单Agent+ReAct，验证可靠性后再加复杂度
2. **工具优先设计** — 工具设计在前，MCP包装在后
3. **纯函数工具** — 工具应无状态、幂等
4. **单一职责Agent** — 每个Agent只做一件事
5. **外部化Prompt管理** — 不在代码中硬编码Prompt
6. **工作流与MCP分离** — 清晰的关注点分离
7. **容器化部署** — 可扩展运维
8. **全量日志** — 工具调用、状态转换、输入/输出
9. **先加护栏再上线** — PII脱敏、语气检查、安全扫描
10. **Canary发布** — 监控指标，自动回滚

---

## 6. 论文 Agent 架构设计方案

### 6.1 总体架构：Harness驱动的多Agent编排系统

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                           │
│  写作工作台 | 文献浏览器 | 大纲编辑器 | AI对话 | 知识图谱可视化    │
├──────────────────────────────────────────────────────────────────┤
│                        API GATEWAY                                │
│  REST + SSE Streaming | 认证 | 限流 | 路由                       │
├──────────────────────────────────────────────────────────────────┤
│                     ORCHESTRATOR (LangGraph)                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  Master Supervisor                          │  │
│  │   Phase 1     →    Phase 2     →    Phase 3   →   Phase N  │  │
│  │  (文献调研)       (大纲规划)        (逐章写作)     (终审)    │  │
│  │       ↓               ↓                ↓            ↓      │  │
│  │  [Checkpoint]    [Checkpoint]     [Checkpoint] [Checkpoint] │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                     SPECIALIZED AGENTS                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │Searcher │ │ Planner │ │ Writer  │ │Reviewer │ │ Polisher  │ │
│  │Agent    │ │Agent    │ │Agent    │ │Agent    │ │Agent      │ │
│  │(文献检索)│ │(大纲规划)│ │(章节写作)│ │(质量评审)│ │(语言润色) │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────────┘ │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│  │Method   │ │Chart    │ │Citation │ │PlagCheck│              │
│  │Advisor  │ │Formatter│ │Manager  │ │er Agent │              │
│  │(方法论)  │ │(图表生成)│ │(引用管理)│ │(查重)   │              │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘              │
├──────────────────────────────────────────────────────────────────┤
│                    HARNESS (评估 & 质量保障)                       │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │Evaluator │ │Checkpoint │ │Circuit   │ │Human-in-the-Loop │  │
│  │(质量评分) │ │Manager    │ │Breaker   │ │(人工审核介入)     │  │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                                  │
│  ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────┐ ┌───────────┐      │
│  │ Memory │ │Search  │ │Knowledge│ │Tools │ │LLM Router │      │
│  │System  │ │Engine  │ │Graph    │ │Registry│ │(多模型)   │      │
│  └────────┘ └────────┘ └─────────┘ └──────┘ └───────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 核心Agent角色设计（借鉴Agent Laboratory + PaperDebugger）

| Agent | 职责 | 工具 | 触发时机 |
|-------|------|------|----------|
| **Searcher Agent** | 多源文献检索（arXiv/PubMed/Semantic Scholar/Crossref/OpenAlex） | 搜索引擎适配器、PDF解析器 | 选题/文献综述阶段 |
| **Planner Agent** | 大纲设计、章节结构规划、任务分解 | 大纲生成器、结构验证器 | 大纲规划阶段 |
| **Writer Agent** | 逐章节撰写，上下文感知 | 草稿生成器、内容生成器 | 写作阶段 |
| **Reviewer Agent** | 结构化审稿（清晰度/逻辑/贡献/原创性） | 质量评分、逻辑校验 | 每个写作阶段后 |
| **Polisher Agent** | 学术语言润色、格式规范化 | 语言润色器、格式检查器 | 润色阶段 |
| **Methodology Advisor** | 研究方法建议、统计分析指导 | 统计工具、方法论知识库 | 方法论设计阶段 |
| **Citation Manager** | 引用格式管理、参考文献验证 | 引用生成器、DOI验证 | 全流程 |
| **Plagiarism Checker** | 查重检测、AIGC率评估 | 查重引擎、AI检测器 | 终审阶段 |

### 6.3 Harness层设计（本项目核心创新）

```
Harness = ⟨Evaluator, CheckpointManager, CircuitBreaker, HITL, AuditTrail⟩
```

#### 6.3.1 Evaluator（质量评估器）

```python
class QualityEvaluator:
    """多维度质量评估"""
    dimensions = {
        "structure":  0.20,   # 结构合理性
        "logic":      0.20,   # 逻辑连贯性
        "originality": 0.15,  # 原创性
        "language":   0.15,   # 学术语言
        "citation":   0.15,   # 引用准确性
        "completeness":0.10,  # 内容完整性
        "format":     0.05,   # 格式规范性
    }

    def evaluate(draft, rubric) -> QualityReport:
        # 使用LLM-as-a-Judge + 规则引擎
        scores = {}
        for dim, weight in dimensions.items():
            scores[dim] = llm_judge(draft, rubric[dim])
        return QualityReport(scores, overall, suggestions)
```

#### 6.3.2 CheckpointManager（检查点管理器）

```python
class CheckpointManager:
    """借鉴LangGraph Checkpointer + Restate Journal设计"""

    def save_checkpoint(phase, state, messages) -> Checkpoint:
        """保存完整状态快照到持久化存储"""

    def restore_checkpoint(session_id) -> Checkpoint:
        """恢复最近检查点"""

    def rollback(session_id, step) -> Checkpoint:
        """回退到指定步骤"""

    def list_checkpoints(session_id) -> List[Checkpoint]:
        """查看所有检查点（Time Travel）"""
```

#### 6.3.3 CircuitBreaker（熔断器）

```python
class CircuitBreaker:
    """防止级联失败"""

    thresholds = {
        "llm_error_rate": 0.3,       # LLM调用错误率 >30% → 熔断
        "consecutive_failures": 5,   # 连续失败5次 → 熔断
        "timeout_seconds": 300,      # 单步超过5分钟 → 熔断
        "cost_limit": 5.0,           # 单次会话超过$5 → 熔断
    }

    states = ["CLOSED", "OPEN", "HALF_OPEN"]
    # CLOSED → 正常
    # OPEN → 拒绝请求，快速失败
    # HALF_OPEN → 允许有限请求测试恢复
```

#### 6.3.4 HITL Manager（人机协作管理器）

```python
class HITLManager:
    """借鉴PaperDebugger Diff补丁 + LangGraph Interrupt模式"""

    interrupt_points = {
        "after_outline":    "大纲完成后需人工确认",
        "after_literature": "文献综述完成后需审核",
        "after_section":    "每章节完成后可选审核",
        "before_final":     "终稿前需全面审核",
        "on_low_quality":   "质量评分<阈值时强制中断",
    }

    def request_approval(content, diff_view) -> HITLResponse:
        """请求人工审批，提供Diff视图"""

    def apply_feedback(feedback, target_section) -> Patch:
        """应用人工反馈到目标章节"""
```

#### 6.3.5 AuditTrail（审计溯源）

```python
class AuditTrail:
    """完整操作溯源，借鉴分布式系统Journal设计"""

    def log_agent_action(agent, action, input, output, latency):
        """记录每次Agent操作"""

    def log_state_transition(from_state, to_state, trigger):
        """记录每次状态转换"""

    def log_human_interaction(user, action, content, timestamp):
        """记录每次人机交互"""

    def generate_report(session_id) -> AuditReport:
        """生成完整审计报告"""
```

### 6.4 写作流水线设计（6阶段 + Harness介入点）

```
阶段1: 选题诊断
  ├── Searcher Agent: 文献检索相关领域
  ├── Planner Agent: 研究空白分析
  ├── Reviewer Agent: 选题可行性评估
  └── [HITL 介入点] ← 人工确认选题

阶段2: 文献综述
  ├── Searcher Agent: 多源深度检索
  ├── Writer Agent: 文献综述草稿
  ├── Reviewer Agent: 综述质量评估
  └── [HITL 介入点] ← 人工审核综述

阶段3: 大纲规划
  ├── Planner Agent: 层级化大纲生成
  ├── Methodology Advisor: 方法论匹配
  ├── Reviewer Agent: 结构合理性检查
  └── [HITL 介入点] ← 人工确认大纲

阶段4: 逐章写作 (Generator-Critic循环)
  ├── Writer Agent: 章节草稿生成
  ├── Reviewer Agent: 结构化审稿
  ├── Polisher Agent: 语言润色
  └── [HITL 介入点] ← 每章可选审核

阶段5: 综合润色
  ├── Polisher Agent: 全局语言一致性
  ├── Citation Manager: 引用验证+格式
  ├── Plagiarism Checker: 查重+AIGC检测
  └── [HITL 介入点] ← 人工终审

阶段6: 格式输出
  ├── Chart Formatter: 图表规范化
  ├── Citation Manager: 最终引用格式化
  └── 输出: LaTeX / Word / PDF / Markdown
```

### 6.5 多Agent通信协议设计

```
Agent之间通信方式:

1. Shared State (共享状态)
   └── 通过 Orchestrator 的 StateGraph 传递

2. Message Passing (消息传递)
   └── Agent A → Orchestrator → Agent B
   └── 结构化消息: {from, to, type, content, metadata}

3. Debate Protocol (辩论协议，借鉴AutoGen)
   └── Reviewer提出批评 → Writer逐条回应 → Arbiter最终裁决

4. MCP Protocol (工具调用，标准化)
   └── Agent → MCP Host → MCP Server → External Tool
   └── 核心原语: Tools / Resources / Prompts
   └── 传输方式: stdio (本地) / HTTP+SSE (远程)

5. A2A Protocol (Agent间通信，标准化) [2026 新增]
   └── AgentCard 服务发现 (/.well-known/agent.json)
   └── tasks/sendSubscribe (流式任务分发+SSE状态跟踪)
   └── Task生命周期: submitted → working → completed

6. Agent Skills 标准 (能力封装) [2026 新增]
   └── SKILL.md + scripts/ + references/ + assets/
   └── 渐进式披露: Metadata → Core Instructions → Reference Materials
   └── 五大设计模式: Tool Wrapper / Generator / Reviewer / Inversion / Pipeline
```

---

## 7. 功能矩阵设计

### 7.1 面向学生用户的功能矩阵

| 功能模块 | 核心功能 | 优先级 | 差异化 |
|----------|----------|:------:|--------|
| **智能选题** | 研究空白分析、热门趋势、可行性评估 | P0 | ⭐ Agent驱动的研究空白识别 |
| **文献综述** | 多源搜索、自动筛选、综述生成、引用管理 | P0 | ⭐ 多Agent分工+反思机制 |
| **大纲规划** | 层级化大纲生成、结构验证、方法论匹配 | P0 | ⭐ Planner+Reviewer协作 |
| **逐章写作** | 上下文感知写作、风格一致、逻辑连贯 | P0 | ⭐ Generator-Critic循环 |
| **语言润色** | 学术语气、逻辑连贯、专业术语 | P0 | ⭐ 学术专用模型 |
| **格式排版** | 参考文献自动格式化、多格式导出 | P1 | 1500+格式支持 |
| **查重降重** | 查重检测、AIGC检测、智能改写 | P1 | ⭐ 主动式合规 |
| **答辩辅助** | PPT生成、可能问题预测、模拟答辩 | P1 | ⭐ Agent角色扮演 |
| **知识图谱** | 文献关系可视化、研究脉络图 | P2 | ⭐ 交互式KG |
| **版本管理** | Git式版本控制、Diff对比、协作批注 | P2 | ⭐ PaperDebugger风格 |

### 7.2 技术差异化优势

与现有工具相比，本系统的核心差异化：

| 维度 | 现有工具 | 本系统 |
|------|----------|--------|
| Agent模式 | 单一LLM调用 | **多Agent协作+Harness保障** |
| 质量保障 | 无或基础评分 | **Checkerpoint+Evaluator+CircuitBreaker+HITL** |
| 写作范式 | "一次生成" | **WriteHERE式递归规划 + SciSage式反思** |
| 人机协作 | 编辑文本框 | **PaperDebugger式Diff补丁+阶段性审批** |
| 可追溯性 | 无 | **完整AuditTrail+Journal日志** |
| 容错能力 | 无 | **CircuitBreaker+Checkpoint恢复** |
| 个性化 | 无 | **用户偏好学习+风格自适应** |

---

## 8. 开发路线图

### Phase 1：核心写作流水线（MVP，4-6周）

```
目标: 跑通 选题 → 大纲 → 写作 → 润色 基础流程

关键交付:
├── 统一Agent基类 + LLMConfig统一
├── LangGraph编排器基础实现
├── Searcher Agent (arXiv + Semantic Scholar)
├── Planner Agent (大纲生成)
├── Writer Agent (单章写作)
├── Polisher Agent (语言润色)
├── 基础Checkpoint Manager
├── 基础HITL Manager
└── 前端写作工作台
```

### Phase 2：质量保障体系（+3-4周）

```
目标: 加入Reviewer、Evaluator、CircuitBreaker

关键交付:
├── Reviewer Agent (结构化评审)
├── QualityEvaluator (多维度评分)
├── CircuitBreaker (熔断保护)
├── AuditTrail (完整审计)
├── 改进的Checkpoint恢复
└── Generator-Critic写作循环
```

### Phase 3：高级功能（+4-6周）

```
目标: 献综述自动化、多Agent协作、反思机制

关键交付:
├── SciSage式多层Reflector
├── Agent Laboratory式自主科研流程
├── Citation Manager (引用验证)
├── Methodology Advisor
├── Plagiarism Checker集成
├── 知识图谱可视化
└── 答辩PPT生成
```

### Phase 4：产品化（+4-6周）

```
目标: 编辑器内嵌、协作功能、性能优化

关键交付:
├── Overleaf/VS Code插件（PaperDebugger模式）
├── 多人协作编辑
├── 版本管理+Diff视图
├── 流式SSE响应
├── 多模型LLM Router
├── Docker Compose生产部署
├── 用户偏好学习
└── 性能优化+HPA扩展
```

---

## 附录A：关键论文参考文献

| 论文/项目 | 时间 | 核心贡献 | 来源 |
|------|------|----------|------|
| Agent Laboratory | 2025.01 | 四大Agent角色+自主科研流水线，成本降84% | arxiv.org/abs/2501.04227 |
| WriteHERE | 2025.03 | 异构递归规划、EMNLP 2025 Outstanding Paper | arxiv.org/abs/2503.08275 |
| SciSage | 2025.06 | 三层Reflector边写边反思，引用F1提升32% | arxiv.org/abs/2506.12689 |
| Agentic AutoSurvey | 2025.09 | 四Agent自动综述+12维评估框架 | arxiv.org/abs/2509.18661 |
| PaperDebugger | 2025.12 | Overleaf多Agent+Diff补丁+MCP协议 | arxiv.org/abs/2512.02589 |
| GPT Researcher | 2025 | 树状递归深度研究+20+来源聚合 | github.com/assafelovic/gpt-researcher |
| STORM/Co-STORM | 2024-2025 | 斯坦福多源信息整合写作+协作探索 | github.com/stanford-oval/storm |
| DSPy | 2023-2025 | 声明式LLM编程，编译器替代手工Prompt工程 | github.com/stanfordnlp/dspy |
| AgRefine | 2025.12 | 三Agent修订流水线 | IEEE ICA 2025 |
| LiRA | 2025.10 | 四阶段文献综述Agent | arxiv.org/abs/2510.05138 |
| TTD-DR (Google) | 2025.09 | 扩散模型"去噪"研究报告，74.5%胜率超OpenAI Deep Research | Google Research |
| Loong | 2025.09 | CAMEL-AI长链思维合成(通过Verifier) | arxiv.org |
| AIssistant | 2025.09 | 端到端ML论文+LaTeX生成，成本<$1/篇 | arXiv |
| ReAct | 2023 | Reason+Act基础Agent循环模式 | Yao et al. 2023 |
| Reflexion | 2023 | 自我反思Agent模式 | Shinn et al. 2023 |
| CAMEL | 2023 | 首个基于ChatGPT的多Agent角色扮演框架 | NeurIPS 2023 |

## 附录B：技术栈选型建议

| 层级 | 推荐技术 | 备选 |
|------|----------|------|
| **编排框架** | LangGraph (StateGraph) | CrewAI（原型验证用） |
| **LLM调用** | LangChain + 原生OpenAI SDK | 直接HTTP调用 |
| **后端框架** | aiohttp（已有） | FastAPI |
| **状态持久化** | LangGraph SqliteSaver → PostgreSQL | Restate Durable Execution |
| **流式推送** | SSE (Server-Sent Events) | WebSocket |
| **前端框架** | React 18 + Vite（已有） | — |
| **图可视化** | AntV G6（已有） | D3.js |
| **容器化** | Docker + Docker Compose（已有） | K8s（已有配置） |
| **可观测性** | LangSmith / OpenTelemetry | Prometheus + Grafana（已有配置） |
| **搜索集成** | arXiv + Semantic Scholar + PubMed API | OpenAlex + Crossref |

---

## 附录C：详细开发计划 (v12.0)

**文档版本**: v12.0 Unified
**更新日期**: 2026-04-27
**对齐基准**: README.md 六大核心功能
**当前状态**: LangGraph 工作流基础已就绪，需与现有功能模块集成

---

## 现状分析

### 已完成

| 模块 | 说明 | 测试 |
|------|------|------|
| LangGraph 工作流 | 6 节点图（crawl→select→outline→write→review→eval） | 37/37 |
| 搜索模块 | arXiv, PubMed, Semantic Scholar, OpenAlex | 已有 |
| QA 模块 | 论文搜索、每日/周/月报告、查询路由 | 已有 |
| 写作模块 | 18 个文件：大纲、初稿、综述、改稿、润色等 | 已有 |
| 论文 Agent | 选题、大纲、初稿、编辑、评审 | 已有 |
| 路由模块 | 意图分类（11类）、Agent 选择、降级路由 | 已有 |
| API 层 | paper_api + reports_api + gateway | 已有 |
| 记忆模块 | 25 个文件：短期/长期/情景/压缩/Neo4j | 已有 |
| LangGraph 扩展节点 | memory/multimodal/kg（已实现但**未接入图**） | 已有 |

### 核心问题：LangGraph 与现有代码脱节

当前 LangGraph 工作流只覆盖了「写作」功能的一条线性路径。README 描述的六大功能中，大多数未接入 LangGraph：

| README 功能 | 现有代码 | LangGraph 集成状态 |
|------------|---------|-------------------|
| 论文搜索 | search/ (4搜索引擎) | 部分接入（crawler 节点） |
| 定时报告 | qa/ (daily/weekly/monthly) | **未接入** |
| 论文写作 | writing/ (18文件) + paper_agents/ (9文件) | **重复实现**（outline/writer 节点） |
| 论文修改 | smart_reviser, report_refiner | **未接入** |
| 对话问答 | query_router (4类路由) | **未接入** |
| 记忆系统 | memory/ (25文件) | **未接入**（节点已写但未连图） |

此外：
- 3 个已实现的扩展节点（memory、multimodal、kg）未接入 StateGraph
- 路由层（routing/，意图分类+Agent 选择）未与 LangGraph 对接
- API 层（api/paper_api.py, api/reports_api.py）未调用 LangGraph 工作流

---

## 开发目标

将 LangGraph 工作流从「单路径写作工具」升级为「统一入口引擎」，覆盖 README 全部六大功能。核心原则：

1. **复用现有代码** — 不重写，而是将现有 Agent 包装为 LangGraph 节点
2. **按 README 功能组织** — 每个功能对应独立的工作流路径
3. **统一入口** — 通过路由层分发到不同工作流

---

## 开发计划

### Phase 1：统一路由入口（第 1-2 周）

**目标**: 建立查询路由层，将不同类型请求分发到对应工作流路径

#### 1.1 整合路由层到 LangGraph

现有 `src/agents_v2/routing/` 已有完整的意图分类（11类）和 Agent 选择逻辑。需要将其接入 LangGraph 作为入口节点。

```
用户查询
    │
    ▼
┌─────────────┐
│ RouteNode    │  ← LLMIntentClassifier (routing/llm_intent_classifier.py)
│ 意图分类     │  → 11种意图: literature_search, topic_select, outline_generate,
└──────┬──────┘     draft_write, full_paper, question, comparison, ...
       │
       ├── literature_search → 搜索工作流
       ├── daily/weekly/monthly → 报告工作流
       ├── outline_generate → 写作工作流（大纲）
       ├── draft_write → 写作工作流（初稿）
       ├── full_paper → 写作工作流（全流程）
       ├── smart_revise → 修改工作流
       ├── polish → 修改工作流（润色）
       ├── question → 问答工作流
       ├── comparison → 问答工作流（比较）
       └── unknown → 默认搜索工作流
```

**实现要点**:
- 新建 `RouteNode`：包装 `LLMIntentClassifier`，将意图映射到工作流路径
- 修改 `workflow.py`：在 `StateGraph` 入口处添加路由节点，用 `add_conditional_edges` 分发
- 新增 `route_by_intent()` 条件边函数

**文件变更**:
- 修改: `src/agents_v2/langgraph_workflow/workflow.py` — 添加路由节点和条件边
- 修改: `src/agents_v2/langgraph_workflow/edges.py` — 添加 `route_by_intent()`
- 新建: `src/agents_v2/langgraph_workflow/nodes/router.py` — RouteNode 包装器

#### 1.2 统一工作流入口

将路由层作为所有功能的统一入口：

```python
# 目标用法
workflow = create_unified_workflow(llm=llm)
result = workflow.run(query="最近一周transformer相关论文", user_id="user1")
# → RouteNode 识别为 literature_search → 搜索工作流 → 返回论文列表

result = workflow.run(query="帮我写一篇关于因果推断的综述", user_id="user1")
# → RouteNode 识别为 full_paper → 写作工作流（全流程）→ 返回大纲+初稿
```

**验收标准**:
- [ ] RouteNode 能正确分类至少 8 种意图
- [ ] 条件路由正确分发到对应工作流路径
- [ ] 现有 37 个测试不回归

---

### Phase 2：接入报告工作流（第 3 周）

**目标**: 将定时报告功能（每日/周/月）接入 LangGraph

README 定义了 4 种报告类型，现有代码 `src/agents_v2/qa/` 已完整实现。

#### 2.1 报告工作流节点

```
RouteNode
    │ (daily_report | weekly_report | monthly_report)
    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ ReportCrawl   │───▶│ ReportAnalyze │───▶│ ReportGen    │
│ 搜索论文      │    │ 统计分析      │    │ 生成报告     │
└──────────────┘    └──────────────┘    └──────────────┘
```

**实现要点**:
- 新建 `ReportCrawlNode`: 包装 `PaperSearchAgent`（qa/paper_search.py），按报告类型搜索
- 新建 `ReportAnalyzeNode`: 包装现有报告分析逻辑（方法统计、趋势分析）
- 新建 `ReportGenNode`: 包装 `DailyWatcher`/`WeeklyReportGenerator`/`MonthlyReportGenerator`
- 在 workflow.py 中添加报告路径

**复用代码**:
- `qa/daily_watcher.py` → DailyWatcher
- `qa/weekly_report.py` → WeeklyReportGenerator
- `qa/monthly_report.py` → MonthlyReportGenerator
- `qa/report_generator.py` → 通用报告生成
- `qa/paper_search.py` → PaperSearchAgent

**文件变更**:
- 新建: `src/agents_v2/langgraph_workflow/nodes/report_crawl.py`
- 新建: `src/agents_v2/langgraph_workflow/nodes/report_analyze.py`
- 新建: `src/agents_v2/langgraph_workflow/nodes/report_gen.py`
- 修改: `workflow.py` — 添加报告路径节点和边

**验收标准**:
- [ ] 每日/周/月报告可通过 LangGraph 工作流生成
- [ ] 报告节点复用现有 qa/ 模块代码（不重写逻辑）
- [ ] 报告路径有独立测试覆盖

---

### Phase 3：接入问答工作流（第 4 周）

**目标**: 将对话问答功能接入 LangGraph

README 定义了 4 种问答模式：基础查询、比较、探索、追踪。

#### 3.1 问答工作流节点

```
RouteNode
    │ (question | comparison | frontier | application)
    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ QASearch     │───▶│ QASynthesize │───▶│ QAAnswer     │
│ 搜索相关论文  │    │ 综合/比较分析 │    │ 生成回答     │
└──────────────┘    └──────────────┘    └──────────────┘
```

**实现要点**:
- 新建 `QASearchNode`: 包装 `PaperSearchAgent`，根据问题类型选择搜索策略
- 新建 `QASynthesizeNode`: 包装比较/趋势分析逻辑
- 新建 `QAAnswerNode`: 包装答案生成，支持引用论文
- 对比类问题：并行搜索双方论文，然后综合比较

**复用代码**:
- `qa/paper_search.py` → PaperSearchAgent
- `qa/query_router.py` → QueryRouter（辅助二次路由）
- `tools/extended_search.py` → compare_papers, analyze_paper_trend

**文件变更**:
- 新建: `src/agents_v2/langgraph_workflow/nodes/qa_search.py`
- 新建: `src/agents_v2/langgraph_workflow/nodes/qa_synthesize.py`
- 新建: `src/agents_v2/langgraph_workflow/nodes/qa_answer.py`
- 修改: `workflow.py` — 添加问答路径

**验收标准**:
- [ ] 基础查询、比较分析可通过工作流完成
- [ ] 问答节点复用现有 qa/ 代码
- [ ] 问答结果包含论文引用

---

### Phase 4：接入修改工作流（第 5 周）

**目标**: 将论文修改功能接入 LangGraph

README 定义了修改流程：智能改稿 → 多轮精炼 → 语言润色 → 最终评审。

#### 4.1 修改工作流节点

```
RouteNode
    │ (smart_revise | polish | review)
    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ ReviseNode    │───▶│ RefineNode   │───▶│ PolishNode   │
│ 智能改稿      │    │ 多轮精炼     │    │ 语言润色     │
└──────────────┘    └──────────────┘    └──────────────┘
```

**实现要点**:
- 新建 `ReviseNode`: 包装 `SmartReviserAgent`（writing/smart_reviser.py）
- 新建 `RefineNode`: 包装 `ReportRefinerAgent`（writing/report_refiner.py）
- 新建 `PolishNode`: 包装 `LanguagePolisherAgent`（writing/smart_reviser.py）
- 支持单步修改（仅润色）和全流程修改

**复用代码**:
- `writing/smart_reviser.py` → SmartReviserAgent, LanguagePolisherAgent
- `writing/report_refiner.py` → ReportRefinerAgent
- `writing/answer_quality_checker.py` → 质量检查

**文件变更**:
- 新建: `src/agents_v2/langgraph_workflow/nodes/revise.py`
- 新建: `src/agents_v2/langgraph_workflow/nodes/refine.py`
- 新建: `src/agents_v2/langgraph_workflow/nodes/polish.py`
- 修改: `workflow.py` — 添加修改路径

**验收标准**:
- [ ] 智能改稿、语言润色可通过工作流完成
- [ ] 修改节点复用现有 writing/ 代码
- [ ] 修改结果包含修改报告和统计

---

### Phase 5：连接扩展节点 + API 集成（第 6-7 周）

**目标**: 将已实现但未连图的 3 个扩展节点接入，并将 API 层对接到统一工作流

#### 5.1 连接扩展节点

3 个节点已实现（`nodes/memory.py`, `nodes/multimodal.py`, `nodes/knowledge_graph.py`）但未添加到 StateGraph。

**MemoryNode 接入**:
```
RouteNode → ... → MemoryRecall → [搜索/写作节点] → MemoryRemember → [输出]
```
- 在搜索前调用 `recall_before_search()` 注入用户偏好
- 在筛选后调用 `remember_after_selection()` 记住选择
- 在输出前调用 `personalize_output()` 个性化

**MultimodalNode 接入**:
- 在写作节点前调用 `analyze_paper_figures()` 丰富论文元数据
- 输出的图表类型信息供 writer 参考生成

**KnowledgeGraphNode 接入**:
- 在选择后调用 `extract_and_build()` 构建知识图谱
- 调用 `query_related()` 发现跨论文关联
- 结果供 writer 参考生成综述

**文件变更**:
- 修改: `workflow.py` — 将 3 个节点加入图，添加相应边

#### 5.2 API 层对接

现有 API 层（`api/paper_api.py`, `api/reports_api.py`）直接调用各 Agent。需要改为调用统一工作流。

**实现要点**:
- 修改 `paper_api.py` 的路由处理函数：调用 `create_unified_workflow().run()` 而非直接调用各 Agent
- 修改 `reports_api.py`：通过工作流生成报告
- 保留现有 API 端点不变，只改内部实现
- `/api/papers/{id}/outline/generate` → 写作工作流（大纲）
- `/api/papers/{id}/sections/{sectionId}/generate` → 写作工作流（初稿）
- `/api/papers/{paperId}/chat` → 问答工作流
- `/api/literature/search` → 搜索工作流
- `/api/reports/*` → 报告工作流

**文件变更**:
- 修改: `src/agents_v2/api/paper_api.py` — 对接工作流
- 修改: `src/agents_v2/api/reports_api.py` — 对接工作流
- 修改: `src/agents_v2/api_server.py` — 健康检查增加工作流状态

**验收标准**:
- [ ] MemoryNode 在搜索前注入用户偏好
- [ ] MultimodalNode 在写作前分析图表
- [ ] KnowledgeGraphNode 在写作前构建关联
- [ ] API 端点通过工作流处理请求
- [ ] 现有 API 行为不回归

---

### Phase 6：测试、文档与优化（第 8 周）

**目标**: 完善测试覆盖、更新文档、性能优化

#### 6.1 测试补充

为每个新工作流路径补充单元测试和端到端测试：

- `tests/test_workflow_routing.py` — 路由分发测试
- `tests/test_workflow_report.py` — 报告工作流测试
- `tests/test_workflow_qa.py` — 问答工作流测试
- `tests/test_workflow_revision.py` — 修改工作流测试
- `tests/test_workflow_integration.py` — 完整集成测试

#### 6.2 文档更新

- 更新 README.md：反映统一工作流架构
- 更新 API 文档：新增工作流相关端点
- 更新使用指南：按六大功能组织使用示例

#### 6.3 性能优化

- 复用已有 `optimization/` 和 `cache/` 模块
- 为高频路径（搜索、问答）添加缓存
- 工作流编译结果缓存（避免每次请求重新编译）

**验收标准**:
- [ ] 测试覆盖率 > 85%
- [ ] 所有 API 端点有集成测试
- [ ] README 与实际代码一致
- [ ] 端到端延迟 < 5s（含 LLM）

---

## 统一工作流架构总览

完成后的工作流架构：

```
                              ┌─────────────┐
                              │  用户查询    │
                              └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │  RouteNode   │
                              │  意图分类     │
                              └──────┬──────┘
                                     │
          ┌──────────┬───────────┬───┴───┬──────────┬──────────┐
          ▼          ▼           ▼       ▼          ▼          ▼
     ┌─────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
     │ 搜索    │ │ 报告   │ │ 写作 │ │ 修改 │ │ 问答 │ │ 记忆 │
     │ 工作流  │ │ 工作流 │ │工作流│ │工作流│ │工作流│ │ 介入 │
     └────┬────┘ └───┬────┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
          │          │         │        │        │        │
          └──────────┴─────────┴────────┴────────┴────────┘
                              │
                       ┌──────▼──────┐
                       │  输出/评估   │
                       └─────────────┘

搜索工作流: crawl → select → (输出)
报告工作流: report_crawl → report_analyze → report_gen
写作工作流: memory_recall → crawl → select → kg → multimodal → outline → write → review → eval → memory_remember
修改工作流: revise → refine → polish
问答工作流: qa_search → qa_synthesize → qa_answer
```

---

## 技术原则

1. **包装而非重写** — 将现有 Agent（writing/, qa/, paper_agents/）包装为 LangGraph 节点，内部逻辑不变
2. **路径隔离** — 每个工作流路径独立，不互相影响
3. **共享基础设施** — 搜索、记忆、评估为共享节点，各路径复用
4. **渐进集成** — 每个 Phase 独立可测试，不阻塞其他 Phase

---

## 时间规划

| Phase | 内容 | 时间 | 依赖 |
|-------|------|------|------|
| Phase 1 | 统一路由入口 | 第 1-2 周 | 无 |
| Phase 2 | 报告工作流 | 第 3 周 | Phase 1 |
| Phase 3 | 问答工作流 | 第 4 周 | Phase 1 |
| Phase 4 | 修改工作流 | 第 5 周 | Phase 1 |
| Phase 5 | 扩展节点 + API | 第 6-7 周 | Phase 2-4 |
| Phase 6 | 测试文档优化 | 第 8 周 | Phase 5 |

Phase 2-4 可并行开发（都只依赖 Phase 1 的路由层）。

---

## 现有代码复用映射

| 工作流节点 | 复用的现有代码 |
|-----------|-------------|
| RouteNode | `routing/llm_intent_classifier.py` → LLMIntentClassifier |
| ReportCrawlNode | `qa/paper_search.py` → PaperSearchAgent |
| ReportGenNode | `qa/daily_watcher.py`, `qa/weekly_report.py`, `qa/monthly_report.py` |
| QASearchNode | `qa/paper_search.py` → PaperSearchAgent |
| QASynthesizeNode | `tools/extended_search.py` → compare_papers, analyze_paper_trend |
| QAAnswerNode | `qa/query_router.py` → QueryRouter |
| ReviseNode | `writing/smart_reviser.py` → SmartReviserAgent |
| RefineNode | `writing/report_refiner.py` → ReportRefinerAgent |
| PolishNode | `writing/smart_reviser.py` → LanguagePolisherAgent |
| CrawlerAgent | `search/search_factory.py` → SearchFactory（已接入） |
| MemoryNode | `memory/services.py` → UnifiedMemoryService（已实现，待接入图） |
| MultimodalNode | 自包含规则分析（已实现，待接入图） |
| KnowledgeGraphNode | `knowledge_graph/` → Neo4j 服务（已实现，待接入图） |

---

## 附录：知识图谱详细计划

**制定日期**: 2026-04-26
**目标**: 将Paper Agent知识图谱从基础实现升级为企业级架构

---

## 一、当前状态评估

### 1.1 已实现功能

| 模块 | 状态 | 说明 |
|------|------|------|
| Neo4jGraphStore | ✅ 完成 | 基础CRUD、路径查询 |
| EntityExtractor | ✅ 完成 | 基于正则的实体抽取 |
| RelationExtractor | ✅ 完成 | 基于规则的关抽取 |
| KnowledgeGraphGenerator | ✅ 完成 | 端到端生成流程 |

### 1.2 缺失功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 社区检测 | P1 | Leiden/Louvain算法 |
| 向量检索集成 | P1 | Qdrant/混合检索 |
| MMR融合 | P1 | 检索结果去重排序 |
| 批量操作优化 | P2 | APOC批量导入 |
| 图嵌入 | P2 | TransE/ComplEx |
| 子图摘要生成 | P2 | GraphRAG风格 |

---

## 二、迭代计划

### Iteration 1: 社区检测 (2-3天)

**目标**: 实现Leiden社区检测算法，支持层次化社区发现

**任务**:

1. `kg_community.py` - 新增社区检测模块
   - LeidenAlgorithm实现
   - LouvainAlgorithm备选
   - 社区层次结构管理

2. Neo4jStore扩展
   - 添加社区相关索引
   - 支持社区查询

3. 测试用例
   - 社区检测准确性测试
   - 性能基准测试

**验收标准**:
- 能够从论文网络中检测出研究社区
- 支持社区层次结构查询
- 1000节点社区检测 < 1秒

---

### Iteration 2: 混合检索 (3-4天)

**目标**: 实现向量+图遍历的混合检索

**任务**:

1. `kg_hybrid_retriever.py` - 新增混合检索器
   - 向量相似度检索
   - 图遍历扩展
   - MMR融合算法

2. Qdrant集成
   - 向量存储初始化
   - 论文embedding生成
   - 混合查询接口

3. 测试用例
   - 检索相关性测试
   - 性能基准测试

**验收标准**:
- 支持同时使用向量和图信息检索
- MMR去重率 > 30%
- Top-10检索相关性 > 0.7

---

### Iteration 3: 批量操作优化 (2-3天)

**目标**: 提升大规模数据导入性能

**任务**:

1. Neo4jStore批量操作扩展
   - APOC批量导入
   - 事务优化
   - 增量更新支持

2. 论文数据模型优化
   - 标签系统重构
   - 属性索引优化

3. 性能测试
   - 10万节点导入测试
   - 并发写入测试

**验收标准**:
- 10万节点批量导入 < 5分钟
- 增量更新延迟 < 1秒

---

### Iteration 4: 图嵌入与推理 (3-4天)

**目标**: 实现知识图谱嵌入，支持链接预测

**任务**:

1. `kg_embeddings.py` - 新增嵌入模块
   - TransE实现
   - ComplEx实现
   - 预训练模型加载

2. 链接预测API
   - 相似实体发现
   - 缺失关系预测

3. 与检索系统集成

**验收标准**:
- TransE训练收敛
- 链接预测准确率 > 0.8

---

### Iteration 5: 子图摘要与GraphRAG (4-5天)

**目标**: 实现GraphRAG风格的子图摘要

**任务**:

1. `kg_summarizer.py` - 新增摘要生成器
   - 社区摘要生成
   - LLM摘要调用
   - 摘要缓存

2. GraphRAG检索流程
   - 社区定位
   - 子图收集
   - 上下文组装

3. API端点
   - 问答接口
   - 探索接口

**验收标准**:
- 支持基于图的问答
- 上下文组装正确
- 多跳推理正确

---

## 三、技术方案详细设计

### 3.1 数据模型（优化后）

```cypher
// 节点 - 使用Label代替Type属性
(:Paper:`+paper_id+` {
  title: string,
  abstract: string,
  year: int,
  citations: int,
  embedding: list<float>,  // 向量
  summary: string,          // LLM生成的摘要
  created_at: datetime,
  updated_at: datetime
})

(:Author:`+author_id+` {
  name: string,
  affiliation: string,
  h_index: float
})

(:Method:`+method_id+` {
  name: string,
  category: string,  // cnn/transformer/gnn等
  paper_count: int
})

(:Dataset:`+dataset_id+` {
  name: string,
  task: string,
  size: string
})

(:Community:`+community_id+` {
  level: int,           // 社区层次
  size: int,            // 成员数量
  summary: string,      // 社区摘要
  keywords: list<string>
})

// 关系
(:Paper)-[:AUTHORED_BY {role: string}]->(:Author)
(:Paper)-[:CITES]->(:Paper)
(:Paper)-[:USES_METHOD]->(:Method)
(:Paper)-[:USES_DATASET]->(:Dataset)
(:Paper)-[:PUBLISHED_IN {journal: string}]->(j:Journal)
(:Author)-[:AFFILIATED_WITH]->(:Institution)
(:Author)-[:COLLABORATES_WITH {weight: float}]->(:Author)
(:Method)-[:SIMILAR_TO {score: float}]->(:Method)
(:Entity)-[:BELONGS_TO {level: int}]->(:Community)  // 社区归属
```

### 3.2 核心API设计

```python
class KnowledgeGraphService:
    """知识图谱服务"""

    # ========== 社区检测 ==========
    def detect_communities(self, algorithm: str = "leiden") -> Dict:
        """
        检测社区

        Returns:
            {
                "communities": [
                    {"id": "c1", "level": 0, "members": [...], "summary": "..."},
                    {"id": "c2", "level": 1, "members": [...], "summary": "..."}
                ],
                "hierarchy": {...}
            }
        """
        pass

    # ========== 混合检索 ==========
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict = None
    ) -> List[RetrievalResult]:
        """
        混合检索

        1. 向量相似度检索候选
        2. 图遍历扩展
        3. MMR融合
        """
        pass

    # ========== 图嵌入 ==========
    def compute_embeddings(self, model: str = "transe") -> bool:
        """计算所有实体嵌入"""
        pass

    def predict_link(self, head: str, relation: str) -> List[str]:
        """预测可能链接的尾实体"""
        pass

    # ========== GraphRAG ==========
    def query_with_graph(
        self,
        question: str,
        use_community: bool = True
    ) -> GraphRAGResult:
        """
        GraphRAG风格问答

        1. 实体链接
        2. 社区定位
        3. 子图收集
        4. 上下文组装
        5. LLM生成
        """
        pass

    # ========== 批量操作 ==========
    def batch_import_papers(self, papers: List[Dict]) -> BatchResult:
        """批量导入论文"""
        pass

    def incremental_update(self, paper_id: str, changes: Dict) -> bool:
        """增量更新"""
        pass
```

### 3.3 MMR融合实现

```python
class MMRReranker:
    """最大边际相关性重排序"""

    def __init__(self, lambda_param: float = 0.5):
        self.lambda_param = lambda_param  # 多样性权重

    def rerank(
        self,
        query_embedding: np.ndarray,
        candidates: List[Candidate],
        top_k: int,
        embeddings: Dict[str, np.ndarray]
    ) -> List[Candidate]:
        """
        MMR重排序

        MMR公式: score = λ * sim(query, doc) - (1-λ) * max(sim(doc_i, doc_j))
        """
        selected = []
        remaining = candidates.copy()

        while len(selected) < top_k and remaining:
            best_score = -float('inf')
            best_candidate = None

            for candidate in remaining:
                # 相关度分数
                relevance = self.cosine_similarity(
                    query_embedding,
                    embeddings.get(candidate.id)
                )

                # 多样性分数：与已选中文档的最大相似度
                diversity = 0
                if selected:
                    max_sim = max(
                        self.cosine_similarity(
                            embeddings.get(candidate.id),
                            embeddings.get(s.id)
                        )
                        for s in selected
                    )
                    diversity = max_sim

                # MMR分数
                mmr_score = (
                    self.lambda_param * relevance
                    - (1 - self.lambda_param) * diversity
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate

            selected.append(best_candidate)
            remaining.remove(best_candidate)

        return selected
```

### 3.4 Leiden社区检测实现

```python
class LeidenAlgorithm:
    """Leiden社区检测算法"""

    def detect(self, graph: nx.Graph, resolution: float = 1.0) -> Dict:
        """
        Leiden社区检测

        相比Louvain:
        1. 使用更快的局部移动
        2. 产生更连接紧密的社区
        3. 支持层次化结构
        """
        # 1. 初始化：每个节点独立社区
        partition = {node: node for node in graph.nodes()}

        # 2. 迭代优化
        improved = True
        while improved:
            improved = self._local_move(graph, partition, resolution)

        # 3. 细化
        refined = self._refine_partition(graph, partition)

        # 4. 构建层次
        hierarchy = self._build_hierarchy(graph, refined)

        return {
            "partition": partition,
            "hierarchy": hierarchy,
            "modularity": self._compute_modularity(graph, partition)
        }

    def _local_move(self, graph, partition, resolution):
        """局部移动优化"""
        improved = False
        for node in graph.nodes():
            current_comm = partition[node]
            current_gain = self._modularity_gain(
                graph, partition, node, current_comm, resolution
            )

            best_comm = current_comm
            best_gain = current_gain

            for neighbor_comm in self._get_neighbor_communities(
                graph, partition, node
            ):
                gain = self._modularity_gain(
                    graph, partition, node, neighbor_comm, resolution
                )
                if gain > best_gain:
                    best_gain = gain
                    best_comm = neighbor_comm

            if best_comm != current_comm:
                partition[node] = best_comm
                improved = True

        return improved
```

---

## 四、文件结构规划

```
src/agents_v2/
├── knowledge_graph/
│   ├── __init__.py
│   ├── kg_store.py              # 知识图谱存储（重构Neo4jStore）
│   ├── entity_extractor.py      # 实体抽取（保留现有）
│   ├── relation_extractor.py    # 关系抽取（保留现有）
│   ├── kg_generator.py          # 图谱生成器（保留现有）
│   ├── kg_community.py          # [NEW] 社区检测
│   ├── kg_embeddings.py         # [NEW] 图嵌入
│   ├── kg_hybrid_retriever.py   # [NEW] 混合检索
│   ├── kg_summarizer.py         # [NEW] 子图摘要
│   ├── kg_reranker.py           # [NEW] MMR重排序
│   └── kg_service.py            # [NEW] 统一服务API
```

---

## 五、依赖更新

```txt
# requirements.txt 新增
networkx>=3.1              # 图算法
python-louvain>=0.16       # Louvain算法
leidenalg>=0.9.0          # Leiden算法
cdlib>=0.2.6               # 社区检测工具
qdrant-client>=1.1.0       # 向量数据库客户端
sentence-transformers>=2.2  # 嵌入模型
torch>=2.0                 # 深度学习
torch-geometric>=2.3       # 图神经网络
```

---

## 六、里程碑

| 阶段 | 周期 | 交付物 |
|------|------|--------|
| M1 | 第1周 | 社区检测模块 + 单元测试 |
| M2 | 第2周 | 混合检索 + MMR融合 |
| M3 | 第3周 | 批量操作优化 |
| M4 | 第4周 | 图嵌入 + 链接预测 |
| M5 | 第5周 | GraphRAG问答 |
| M6 | 第6周 | 集成测试 + 性能优化 |

---

## 七、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Neo4j大规模性能 | 高 | 使用HugeGraph作为替代 |
| Leiden算法性能 | 中 | 使用python-louvain替代 |
| LLM调用成本 | 中 | 使用缓存 + 小模型 |
| 嵌入计算耗时 | 低 | 预计算 + 增量更新 |
