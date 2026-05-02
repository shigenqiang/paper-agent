# Paper Agent 未来框架设计方案

> 更新时间：2026-05-02 | 版本：v2.1（基于 research 全面更新）
> 基准：当前实现（docs/implemented/）+ 技术调研（docs/research/）+ 开发计划（docs/plans/）
> 状态：已整合 17 份调研报告、已实现架构文档、长期记忆改进方案

---

## 一、框架愿景

**目标**：将 Paper Agent 从「单路径写作工具」升级为「企业级多Agent协作写作平台」

**核心演进方向**：
- 从 5 条独立工作流 → **统一编排的多Agent协作系统**（已实现 LangGraph 5 工作流）
- 从 JSON 文件存储 → **PostgreSQL + Qdrant + Neo4j 融合存储**（已实现 SQLite + ChromaDB）
- 从 40+ 分散 Agent → **Harness 驱动的专业分工 Agent 体系**（已实现 UnifiedMemoryManager v4）
- 从单点追踪 → **全链路可观测性 + 质量保障**（已实现 Evaluator + CircuitBreaker + HITL）

**新增整合内容（v2.1）**：
- Agent 协议生态：MCP + A2A + Skills + AG-UI 四大协议标准
- 记忆系统 v4：Hermes/Hindsight/Obsidian 三系统整合方案
- 意图路由升级：三级级联混合路由（关键词→语义向量→LLM）
- 长期记忆优化：智能触发 + 遗忘曲线 + 重要性阈值过滤
- 评估体系：AgentBench/SWE-bench/PaperBench 完整基准

**对标系统**：GPT-Researcher、Agent Laboratory、PaperDebugger、SciSage、WriteHERE

---

## 二、系统架构总览

### 2.1 分层架构图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React 18 + AG-UI协议)                          │
│   写作工作台 | 文献浏览器 | 大纲编辑器 | AI对话 | 知识图谱 | 版本Diff                 │
│   AG-UI 16种事件类型：TEXT_MESSAGE/TOOL_CALL/STATE_SNAPSHOT/STEP_STARTED等           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              API GATEWAY                                              │
│   REST + SSE Streaming | X-API-Key | Rate Limit | A2A路由分发                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              ORCHESTRATOR (LangGraph + A2A Protocol)                 │
│   ┌────────────────────────────────────────────────────────────────────────────┐   │
│   │                         Master Supervisor + Phase Supervisors               │   │
│   │   Phase 1(选题) → Phase 2(综述) → Phase 3(大纲) → Phase 4(写作) → Phase 5(终审)│   │
│   │        ↓              ↓              ↓              ↓              ↓         │   │
│   │   [Checkpoint]   [Checkpoint]   [Checkpoint]   [Checkpoint]   [Checkpoint]  │   │
│   └────────────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              AGENT LAYER (MCP + A2A + Skills)                        │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐            │
│   │ Searcher  │ │  Planner  │ │  Writer   │ │ Reviewer  │ │ Polisher  │            │
│   │   Agent   │ │   Agent   │ │   Agent   │ │   Agent   │ │   Agent   │            │
│   │  MCP Server│ │           │ │           │ │           │ │           │            │
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘            │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐                         │
│   │  Method   │ │ Citation  │ │   Chart   │ │  Plag     │   AgentCard暴露能力     │
│   │  Advisor  │ │  Manager  │ │ Formatter  │ │  Checker  │   /.well-known/agent.json│
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              HARNESS LAYER                                           │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
│   │  Evaluator │ │ Checkpoint │ │Circuit    │ │    HITL    │ │  AuditTrail    │  │
│   │ (质量评分)  │ │  Manager   │ │ Breaker    │ │  Manager   │ │   (审计溯源)   │  │
│   └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              INFRASTRUCTURE                                          │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│   │   Memory   │ │   Search   │ │    KG      │ │   Tools    │ │  LLM       │      │
│   │   System   │ │   Engine   │ │            │ │  Registry  │ │  Router    │      │
│   │ (PostgreSQL│ │ (多源搜索)  │ │  (Neo4j+   │ │   (MCP)    │ │ (多模型)   │      │
│   │  +Qdrant)  │ │            │ │  Qdrant)   │ │            │ │            │      │
│   └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘      │
│                                                                                     │
│   长程任务处理：MemGPT三层记忆 | Generative Agents反思 | Voyager技能库 | LATS树搜索  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 四大协议层（2026 Agent 基础设施标准）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Agent 协议生态 (2026)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │   MCP 协议    │    │  A2A 协议    │    │  AG-UI 协议   │          │
│   │  (Anthropic)  │    │   (Google)   │    │ (CopilotKit)  │          │
│   │              │    │              │    │              │          │
│   │ Agent ↔ Tool │    │ Agent ↔ Agent│    │ Agent ↔ User  │          │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│          │                   │                   │                   │
│          │      ┌────────────┴────────────┐      │                   │
│          └──────┤    Agent Skills 标准     ├──────┘                   │
│                 │      (Anthropic)         │                          │
│                 │   能力模块化封装与复用     │                          │
│                 └─────────────────────────┘                          │
│                                                                     │
│   核心关系: MCP=手(工具) | A2A=口(协作) | Skills=脑(知识) | AG-UI=脸(交互)│
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 技术栈演进

| 层级 | 当前实现 | 目标实现 | 驱动因素 |
|------|---------|---------|---------|
| **编排框架** | LangGraph StateGraph | LangGraph + A2A Protocol | Agent间标准化通信 |
| **Agent协议** | 直接调用 | MCP + Agent Skills + A2A | 工具调用标准化、能力模块化 |
| **前端交互** | REST轮询 | SSE + AG-UI | 实时流式交互 |
| **记忆存储** | JSON文件 + Redis | PostgreSQL + Qdrant + Neo4j | 记忆系统 v3.0 升级 |
| **可观测性** | WorkflowTracer | LangSmith + OpenTelemetry | 全链路 LLM 追踪 |
| **质量保障** | 基础评分 | Checkpoint + Evaluator + CircuitBreaker | 企业级可靠性 |
| **意图路由** | LLM直接分类 | 三级级联混合路由 (关键词→语义向量→LLM) | 成本+延迟优化 |
| **PDF解析** | pdfplumber基础 | Marker + PDF-Extract-Kit + Nougat | 学术论文公式识别 |
| **长程任务** | 无专门处理 | MemGPT三层记忆 + Voyager技能库 | 防止目标漂移 |

---

## 三、Agent 体系设计

### 3.1 核心 Agent 角色（8个专业Agent）

| Agent | 职责 | 触发阶段 | 工具能力 |
|-------|------|---------|---------|
| **Searcher Agent** | 多源文献检索（arXiv/PubMed/Semantic Scholar/OpenAlex） | 选题、综述 | MCP Search Tools |
| **Planner Agent** | 大纲设计、任务分解、研究空白分析 | 大纲规划 | 大纲生成器、结构验证器 |
| **Writer Agent** | 逐章节撰写、上下文感知、引用标注 | 写作阶段 | 草稿生成器、内容生成器 |
| **Reviewer Agent** | 结构化审稿（清晰度/逻辑/贡献/原创性） | 每章后 | 质量评分、逻辑校验 |
| **Polisher Agent** | 学术语言润色、格式规范化 | 润色阶段 | 语言润色、格式检查 |
| **Methodology Advisor** | 研究方法建议、统计分析指导 | 方法论设计 | 统计工具、方法论知识库 |
| **Citation Manager** | 引用格式管理、参考文献验证 | 全流程 | DOI解析、引用生成 |
| **Plagiarism Checker** | 查重检测、AIGC率评估 | 终审阶段 | 查重引擎、AI检测 |

### 3.2 Agent 通信协议

| 协议 | 用途 | 核心特性 |
|------|------|---------|
| **MCP** | Agent ↔ 工具/数据源 | Tools/Resources/Prompts，stdio/HTTP+SSE传输 |
| **A2A** | Agent ↔ Agent | AgentCard发现，tasks/sendSubscribe流式任务，Task生命周期 |
| **Agent Skills** | 能力模块化封装 | SKILL.md三层渐进式披露，Tool Wrapper/Generator/Reviewer/Inversion/Pipeline |
| **AG-UI** | Agent ↔ 用户界面 | 16种事件类型，SSE实时推送 |

### 3.3 Agent Loop 模式（8种）

基于调研文档中的 Agent Loop 模式：

| 模式 | 适用场景 | 实现 |
|------|---------|------|
| **ReAct** | 基础单步推理 | 当前实现 |
| **Plan-Execute-Reflect** | 复杂多步任务 | Writer Agent 写作循环 |
| **Generator-Critic** | 质量敏感生成 | Writer + Reviewer 配对 |
| **多层Reflector** | 层次化反思 | SciSage式Outline/Section/Document三层 |
| **异构递归规划** | 多类型任务分解 | WriteHERE式检索/推理/写作分离 |
| **DSPy Compiler** | 自动Prompt优化 | 质量评分驱动自动调优 |
| **Tree-of-Research** | 深度研究探索 | GPT Researcher式树状检索 |
| **多专家对话** | 多角度分析 | STORM式模拟专家辩论 |

### 3.4 Skill体系重构（Agent Skills标准）

将现有Skill框架按Agent Skills标准重构：

```
skills/
├── paper-search/                    # 论文搜索Skill
│   ├── SKILL.md                    # 元数据 + 核心指令
│   ├── scripts/
│   │   └── search_helpers.py
│   ├── references/
│   │   └── search_conventions.md
│   └── assets/
│       └── search-template.md
├── paper-analysis/                 # 论文分析Skill
│   └── SKILL.md
├── report-generation/              # 报告生成Skill
│   └── SKILL.md
└── citation-format/                # 引用格式Skill
    └── SKILL.md
```

**渐进式披露机制**：
- 第一层：Metadata触发层（常驻上下文，~50 token/skill）
- 第二层：Core Instructions核心指令层（激活时加载，500-2000 token/skill）
- 第三层：Reference Materials参考资源层（深度需要时加载）

---

## 四、Harness 质量保障体系

### 4.1 核心组件

```
Harness = ⟨Evaluator, CheckpointManager, CircuitBreaker, HITLManager, AuditTrail⟩
```

#### 4.1.1 Evaluator（质量评估器）

基于COMPLETE_AGENT_EVALUATION_GUIDE.md的五大维度：

| 维度 | 权重 | 核心指标 |
|------|------|---------|
| **学术规范性** | 20% | 引用格式、术语使用、结构规范 |
| **研究质量** | 25% | 创新性、严谨性、贡献度 |
| **内容完整性** | 20% | 文献覆盖、论证完整、局限承认 |
| **表达质量** | 15% | 清晰度、连贯性、语法风格 |
| **逻辑严谨性** | 20% | 因果推理、论据质量、结论推导 |

#### 4.1.2 CheckpointManager（检查点管理器）

- LangGraph SqliteSaver/PostgresSaver持久化
- 支持暂停/恢复/时间旅行调试
- 状态快照包含完整上下文

#### 4.1.3 CircuitBreaker（熔断器）

```python
thresholds = {
    "llm_error_rate": 0.3,       # LLM调用错误率 >30% → 熔断
    "consecutive_failures": 5,   # 连续失败5次 → 熔断
    "timeout_seconds": 300,      # 单步超过5分钟 → 熔断
    "cost_limit": 5.0,          # 单次会话超过$5 → 熔断
}
states = ["CLOSED", "OPEN", "HALF_OPEN"]
```

#### 4.1.4 HITL Manager（人机协作）

| 介入点 | 说明 |
|--------|------|
| `after_outline` | 大纲完成后需人工确认 |
| `after_literature` | 文献综述完成后需审核 |
| `after_section` | 每章节完成后可选审核 |
| `before_final` | 终稿前需全面审核 |
| `on_low_quality` | 质量评分<阈值时强制中断 |

#### 4.1.5 AuditTrail（审计溯源）

- 记录每次Agent操作（agent, action, input, output, latency）
- 记录每次状态转换（from_state, to_state, trigger）
- 记录每次人机交互（user, action, content, timestamp）
- 支持评估基准测试：AgentBench/SWE-bench/PaperBench

---

## 五、记忆系统 v4.0（融合Hermes/Hindsight/Obsidian + 智能触发优化）

### 5.1 架构设计

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        分层记忆系统 (Memory System v4)                          │
└──────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│    短期记忆           │  │    会话记忆           │  │    长期记忆           │
│  (ShortTermMemory)    │  │  (SessionMemory)      │  │  (LongTermMemory)     │
│                       │  │                       │  │                       │
│  范围: 当前任务        │  │  范围: 任务内跨Agent    │  │  范围: 跨任务持久化     │
│  存储: 内存 (LRU)      │  │  存储: 内存/文件        │  │  存储: SQLite/向量库   │
│  容量: 500条目         │  │  容量: 500条目          │  │  容量: 无限制          │
│  TTL: 任务结束清除     │  │  TTL: 会话结束清除      │  │  特性: 持久化          │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │    情景记忆 (EpisodicMemory)   │
                    │                               │
                    │  范围: 执行轨迹记录             │
                    │  存储: SQLite                  │
                    │  特性: 时间线, 因果关系         │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    统一记忆管理器               │
                    │  (UnifiedMemoryManager v4)      │
                    │                               │
                    │  核心服务:                      │
                    │  - MemoryExtractor (LLM驱动)    │
                    │  - SummaryGenerator (自动摘要)  │
                    │  - EnhancedRetrievalEngine      │
                    │  - ForgettingController (遗忘曲线)│
                    └───────────────────────────────┘
```

### 5.2 智能触发机制（长期记忆优化）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      智能记忆召回流程                                       │
└─────────────────────────────────────────────────────────────────────────────┘

用户输入
  ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              _should_recall_memories()                                     │
│  检查历史关键词: ["之前", "上次", "曾经", "还记得", ...]                    │
│                              ↓                                              │
│              包含关键词? → 是 → 触发召回                                    │
│                         → 否 → 不触发（跳过，节省token）                      │
└─────────────────────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│           _prioritize_memories() + 遗忘曲线时间衰减                         │
│                                                                            │
│  1. 重要性阈值过滤 (< 0.3 丢弃)                                            │
│  2. 时间衰减计算: retention = importance × e^(-t/S)                          │
│     - 高重要性(≥0.8): S = 7天                                              │
│     - 中重要性(≥0.6): S = 1天                                              │
│     - 低重要性(≥0.4): S = 12小时                                           │
│     - 其他: S = 1小时                                                       │
│  3. 最终分数 = 基础分数 × 保留分数                                          │
└─────────────────────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│           Context Window (短期记忆)                                         │
│                                                                            │
│  高优先级记忆被加载进来，低重要性记忆被过滤                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**配置参数**：

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `importance_threshold` | 0.3 | 重要性阈值，低于此值的记忆被过滤 |
| `enable_time_decay` | True | 是否启用时间衰减 |
| `SYSTEM_TOKEN_RESERVE` | 2000 | 保留给系统的 token 数 |

### 5.3 记忆系统对比（基于调研）

| 系统 | 架构特点 | 核心创新 | Paper Agent参考 |
|------|---------|---------|----------------|
| **MemGPT** | 虚拟内存管理 | 操作系统级分层 | 三层记忆架构 |
| **Generative Agents** | 记忆流+反思 | 重要性评分检索 | 反思机制 |
| **Hermes** | 三层记忆+技能沉淀 | 学习循环(Tracker→Evaluator→Reflector→Crystallizer) | 自动Skill生成 |
| **Hindsight** | 四网络图谱 | TEMPR时序检索+CARA自适应推理 | 图谱记忆 |
| **Obsidian** | 双链笔记 | 双向链接+Dataview查询 | 文档管理 |

### 5.4 重要性等级与保留策略

| 等级 | 分数 | S参数（秒）| 保留时间 |
|------|------|-----------|---------|
| **CRITICAL** | 1.0 | ∞ | 永不 |
| **HIGH** | 0.8 | 604,800 (7天) | 7天 |
| **MEDIUM** | 0.5 | 86,400 (1天) | 1天 |
| **LOW** | 0.3 | 3,600 (1小时) | 1小时 |
| **FORGOTTEN** | <0.1 | <3,600 | - |

**核心公式**: `retention = importance × e^(-t/S)`

### 5.5 记忆流转机制

| 阶段 | 触发条件 | 操作 |
|------|---------|------|
| STG→SESSION | 消息数≥30 OR 任务结束 | 批量存储到PG |
| STG→LONG_TERM | 重要性≥0.7 OR 用户标记 | 存入Qdrant+Neo4j |
| LONG_TERM→FORGOTTEN | retention<0.1 | 删除 |
| 任意→COMPRESS | token超限 | LLM生成摘要 |

### 5.6 长程任务处理（基于Agent长程任务处理调研报告）

| 技术 | 原理 | 适用场景 |
|------|------|---------|
| **MemGPT三层记忆** | Main Context/Recall Memory/Archive Memory分页 | 超长上下文 |
| **Voyager技能库** | 从成功案例自动提取可复用技能 | 跨任务迁移 |
| **AdaPlanner闭环规划** | 执行→反馈→修正→重新规划 | 动态调整 |
| **LATS树搜索** | MCTS + LLM评估状态价值 | 复杂推理 |
| **Reflexion自我反思** | 自然语言反思从失败中学习 | 错误改进 |
| **ExpeL经验学习** | 成功/失败轨迹对比提取策略 | 策略积累 |

---

## 六、意图路由系统（三级级联混合路由）

### 6.1 架构设计

```
用户输入
  → Layer 1: 关键词快速匹配（<1ms, acc 60-75%）
    → 置信度不足 ↓
  → Layer 2: 语义向量路由（10-50ms, acc 80-92%）[新增]
    → 置信度不足 ↓
  → Layer 3: LLM深度分类（500ms-2s, acc 90-96%）
    → Layer 4: 降级兜底（默认意图）
```

### 6.2 技术选型

| 层级 | 技术 | 工具 |
|------|------|------|
| Layer 1 | 关键词匹配 | 现有intent_classifier.py |
| Layer 2 | 语义向量路由 | Semantic Router + FastEmbed (BAAI/bge-small-zh-v1.5) |
| Layer 3 | LLM分类 | Instructor结构化输出 + Prompt Cache |
| Layer 4 | 降级兜底 | fallback_router.py |

### 6.3 预期效果

| 指标 | 当前 | 改造后 | 提升 |
|------|:---:|:---:|:---:|
| P50路由延迟 | ~800ms | ~15ms | **53x更快** |
| P95路由延迟 | ~2s | ~800ms | 2.5x更快 |
| 每万次路由成本 | $18-30 | $2-5 | **成本降低85%** |
| LLM路由占比 | 60% | 20% | 减少2/3 |

---

## 七、工作流设计

### 7.1 六阶段写作流水线

```
阶段1: 选题诊断
  ├── Searcher Agent: 文献检索相关领域
  ├── Planner Agent: 研究空白分析
  ├── Reviewer Agent: 选题可行性评估
  └── [HITL 介入点] ← 人工确认选题

阶段2: 文献综述
  ├── Searcher Agent: 多源深度检索（arXiv/PubMed/Semantic Scholar/OpenAlex）
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

### 7.2 统一工作流入口

```
                              ┌─────────────┐
                              │  用户查询    │
                              └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │  RouteNode   │
                              │  三级级联路由 │
                              └──────┬──────┘
                                     │
          ┌──────────┬───────────┬───┴───┬──────────┬──────────┐
          ▼          ▼           ▼       ▼          ▼          ▼
     ┌─────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
     │ 搜索    │ │ 报告   │ │ 写作 │ │ 修改 │ │ 问答 │ │ 记忆 │
     │ 工作流  │ │ 工作流 │ │工作流│ │工作流│ │工作流│ │ 介入 │
     └─────────┘ └────┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
                      │        │        │        │        │
                      └────────┴────────┴────────┴────────┘
                                     │
                              ┌──────▼──────┐
                              │  输出/评估   │
                              └─────────────┘
```

---

## 八、PDF解析系统

### 8.1 解析方案对比

| 工具 | 公式支持 | 表格支持 | 中文 | 速度 | 推荐度 |
|------|----------|----------|------|------|--------|
| **Marker** | ⭐⭐⭐⭐ LaTeX | ⭐⭐⭐⭐ | ⭐⭐⭐ | 快 | ⭐⭐⭐⭐⭐ |
| **Nougat** | ⭐⭐⭐⭐ MathML | ⭐⭐⭐ | ⭐⭐⭐ | 慢 | ⭐⭐⭐⭐ |
| **PDF-Extract-Kit** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 | ⭐⭐⭐⭐⭐ |
| **LlamaParse** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 快 | ⭐⭐⭐⭐⭐ (付费) |

### 8.2 推荐方案

```python
class PDFParser:
    def __init__(self):
        self.primary = "marker"           # 通用论文，快速处理
        self.fallback = "pdf_extract_kit" # 复杂公式/中文论文

    async def parse(self, pdf_path: str, mode: str = "auto") -> dict:
        if mode == "auto":
            # 自动路由：中文/公式 → PDF-Extract-Kit，其他 → Marker
            return await self._smart_route(pdf_path)
```

### 8.3 升级路线图

```
Phase 1 (1-2周):
  - 集成 Marker 作为主解析引擎
  - 保留 pdfplumber 作为表格提取备选

Phase 2 (2-3周):
  - 集成 PDF-Extract-Kit 支持中文和公式
  - 添加自动路由：中文/公式 → PDF-Extract-Kit，其他 → Marker

Phase 3 (3-4周):
  - 考虑 Zerox 处理扫描版 PDF
  - 添加 PDFMathTranslate 支持论文翻译场景
```

---

## 九、可观测性架构

### 9.1 追踪体系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    可观测性系统 (OpenTelemetry标准)                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────┐  ┌────────────────────────────┐
│  WorkflowTracer (现有)                    │  │ LangfuseTracer (新增)       │
│                                           │  │                            │
│  功能:                                    │  │ 功能:                       │
│  - 节点计时                               │  │ - LLM调用级追踪             │
│  - Token估算                              │  │ - Prompt/Completion捕获     │
│  - 成本估算                               │  │ - 完整Token使用统计         │
│  - 错误率监控                             │  │ - 工具调用记录              │
│                                           │  │ - 成本精确计算              │
│                                           │  │ - Web UI可视化              │
└───────────────────────────────────────────┘  └────────────────────────────┘
         │                                    │
         └────────────────────────────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │   OpenTelemetry 统一接口        │
                │                               │
                │ start_trace(query, user_id)    │
                │ start_node(node_name)          │
                │ record_llm_call(...)          │
                │ record_tool_call(...)          │
                │ end_node(status, error)         │
                │ end_trace()                    │
                └───────────────────────────────┘
```

### 9.2 日志系统标准（基于日志系统调研报告）

| 要求 | 说明 |
|------|------|
| **多级别** | TRACE/DEBUG/INFO/WARN/ERROR/CRITICAL |
| **多目标** | 控制台、文件、远程服务器 |
| **滚动** | 按大小/时间自动滚动 |
| **异步** | 异步写入，不阻塞业务 |
| **结构化** | JSON格式，便于分析 |
| **可关联** | TraceId串联全链路日志 |
| **可告警** | 日志异常实时告警 |

### 9.3 评估基准体系

基于 COMPLETE_AGENT_EVALUATION_GUIDE.md 的完整评估体系：

| 基准名称 | 来源 | 评估重点 | 适用场景 |
|----------|------|----------|----------|
| **AgentBench** | 清华ChatGLM团队 | 8环境综合评估(OS/DB/KG/游戏/家居/购物/网页) | ICLR'24, 全面LLM-as-Agent评估 |
| **SWE-bench Verified** | OpenAI | 500精选GitHub Issue, 解决原版噪声问题 | 代码Agent核心基准 |
| **PaperBench** | OpenAI | 论文复现能力，ICML'24 Spotlight | 科研Agent核心基准 |
| **GAIA** | Meta+HuggingFace+AutoGPT | 466个真实问题,3级难度 | 通用AI助手,多步骤推理 |
| **SuperCLUE-Agent** | CLUE团队 | 中文Agent能力 | 中文论文/对话Agent |
| **DeepSearchQA** | Google | 深度搜索与研究任务多步骤评估 | 2025-12 新发布 |

**2026年评估焦点**：从"模型能力"转向"Agent系统能力"——工具使用、规划、记忆、安全构成完整评估链路。

### 9.4 Eval指标

| 维度 | 指标 |
|------|------|
| **准确性** | Eval scores on curated benchmarks |
| **事实性** | Citation coverage, hallucination detection |
| **安全性** | Guardrail violation count, PII leaks |
| **延迟** | p50 / p95 response times |
| **成本** | Token usage per task |
| **工具正确性** | Tool failure rate, correct API call rate |

---

## 十、LLM模型路由

### 10.1 模型选择策略

| 任务类型 | 推荐模型 | 理由 |
|----------|----------|------|
| 问题分类/路由 | Haiku 4.5 / DeepSeek-V3 | 低成本高吞吐 |
| 论文搜索/查询 | Sonnet 4.6 / Gemini 3.1 Flash | 平衡 |
| 论文深度分析 | Opus 4.7 / DeepSeek-R1 | 强推理 |
| 论文初稿写作 | Opus 4.7 / DeepSeek-V3 | 长文本质量 |
| 中文内容处理 | Qwen 3.5-Max / DeepSeek-V3 | 中文优先 |
| 数学推理 | DeepSeek-R1 / Qwen 3.5-Math | 数学专用 |
| 图表/图像理解 | Gemini 3.1 Pro / Claude Opus | 多模态 |
| 引用格式检查 | Haiku 4.5 / DeepSeek-V3 | 简单任务 |
| 论文润色 | Opus 4.7 / Claude Sonnet | 质量优先 |

### 10.2 成本对比

| 模型 | 输入价格 ($/1M) | 输出价格 ($/1M) | 相对GPT-4o |
|------|-----------------|-----------------|------------|
| DeepSeek-V3 | $0.27 | $1.10 | ~1/18 |
| DeepSeek-R1 | $0.55 | $2.19 | ~1/9 |
| GPT-4o | $2.50 | $10.00 | 基准 |
| Claude Opus 4 | $15.00 | $75.00 | ~6x基准 |

---

## 十一、开发路线图

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

### Phase 3：协议集成（+2-3周）

```
目标: 接入MCP + A2A + Agent Skills + AG-UI

关键交付:
├── MCP Server标准化 (arxiv/pubmed/semantic-scholar)
├── A2A协议基础实现 (AgentCard + tasks/sendSubscribe)
├── Agent Skills重构 (SKILL.md格式)
├── AG-UI前端集成 (16种事件类型)
└── 三级级联意图路由
```

### Phase 4：高级功能（+4-6周）

```
目标: 文献综述自动化、多Agent协作、反思机制

关键交付:
├── SciSage式多层Reflector
├── Agent Laboratory式自主科研流程
├── Citation Manager (引用验证)
├── Methodology Advisor
├── Plagiarism Checker集成
├── 知识图谱可视化
├── PDF解析升级 (Marker + PDF-Extract-Kit)
└── 答辩PPT生成
```

### Phase 5：产品化（+4-6周）

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

## 十二、关键参考文档

| 来源 | 文档 | 关键内容 |
|------|------|---------|
| docs/implemented/architecture/ | architecture-diagram.md | 当前系统架构、5条工作流 |
| docs/implemented/architecture/ | memory/memory-system.md | 记忆系统 v4 架构详解 |
| docs/implemented/architecture/ | unified/intent-router.md | 意图路由 11 种意图详解 |
| docs/implemented/architecture/ | langgraph-workflow/langgraph-workflow.md | LangGraph 工作流节点详解 |
| docs/plans/architecture/ | 论文Agent前沿开发报告.md | Agent框架调研、6阶段开发路线图 |
| docs/plans/architecture/ | 记忆系统与数据存储融合方案.md | Memory v3.0 升级方案 |
| docs/research/01-Agent协议与架构/ | Agent协议生态调研报告.md | MCP/A2A/Agent Skills/AG-UI协议 |
| docs/research/02-提示词工程/ | Agent提示词工程指南.md | Prompt规范标准、Few-Shot、CoT |
| docs/research/03-Agent能力评估/ | COMPLETE_AGENT_EVALUATION_GUIDE.md | Agent评估体系 |
| docs/research/03-Agent能力评估/ | Agent长程任务处理调研报告.md | MemGPT/Voyager/LATS/Reflexion |
| docs/research/04-PaperAgent技能/ | PaperAgent_Skill_调研报告.md | Skill生态调研 |
| docs/research/05-学术搜索与解析/ | PDF解析技术调研报告.md | Marker/PDF-Extract-Kit/Nougat |
| docs/research/06-意图识别与路由/ | 意图识别技术调研报告.md | 三级级联混合路由 |
| docs/research/08-日志与监控/ | 日志系统调研报告.md | 结构化日志、EFK/Loki/Graylog |
| docs/research/ | AI_Agent_记忆系统调研报告_Hermes_Hindsight_Obsidian.md | Hermes/Hindsight/Obsidian |
| docs/research/ | 长期记忆写入短期记忆机制改进方案.md | 智能触发+遗忘曲线+阈值过滤 |

---

**版本**：v2.1
**更新日期**：2026-05-02
**基于**：当前实现 + 技术调研（17份文档）+ 开发计划 + 长期记忆改进方案