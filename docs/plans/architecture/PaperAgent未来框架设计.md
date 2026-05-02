# Paper Agent 未来框架设计方案

> 更新时间：2026-05-02 | 版本：v2.0（基于research全面更新）
> 基准：当前实现（docs/implemented/）+ 技术调研（docs/research/）+ 开发计划（docs/plans/）

---

## 一、框架愿景

**目标**：将 Paper Agent 从「单路径写作工具」升级为「企业级多Agent协作写作平台」

**核心演进方向**：
- 从 5 条独立工作流 → **统一编排的多Agent协作系统**
- 从 JSON 文件存储 → **PostgreSQL + Qdrant + Neo4j 融合存储**
- 从 40+ 分散 Agent → **Harness 驱动的专业分工 Agent 体系**
- 从单点追踪 → **全链路可观测性 + 质量保障**

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

## 五、记忆系统 v3.0（融合Hermes/Hindsight/Obsidian）

### 5.1 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                    UnifiedMemoryManager                       │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ShortTerm│ │ Session │ │LongTerm │ │Episodic │ │UserProf│ │
│  │(内存)  │ │(PG JSONB)│ │(Qdrant) │ │(PG)    │ │(PG)    │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
├──────────────────────────────────────────────────────────────┤
│  服务层: MemoryExtractor / RetrievalEngine / ForgettingCtrl │
├──────────────────────────────────────────────────────────────┤
│  存储层: PostgreSQL + Qdrant(向量) + Neo4j(图)               │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 记忆系统对比（基于调研）

| 系统 | 架构特点 | 核心创新 | Paper Agent参考 |
|------|---------|---------|----------------|
| **MemGPT** | 虚拟内存管理 | 操作系统级分层 | 三层记忆架构 |
| **Generative Agents** | 记忆流+反思 | 重要性评分检索 | 反思机制 |
| **Hermes** | 三层记忆+技能沉淀 | 学习循环(Tracker→Evaluator→Reflector→Crystallizer) | 自动Skill生成 |
| **Hindsight** | 四网络图谱 | TEMPR时序检索+CARA自适应推理 | 图谱记忆 |
| **Obsidian** | 双链笔记 | 双向链接+Dataview查询 | 文档管理 |

### 5.3 重要性等级与保留策略

| 等级 | 分数 | S参数（秒）| 保留时间 |
|------|------|-----------|---------|
| **CRITICAL** | 1.0 | ∞ | 永不 |
| **HIGH** | 0.8 | 604,800 (7天) | 7天 |
| **MEDIUM** | 0.5 | 86,400 (1天) | 1天 |
| **LOW** | 0.3 | 3,600 (1小时) | 1小时 |
| **FORGOTTEN** | <0.1 | <3,600 | - |

**核心公式**: `retention = importance × e^(-t/S)`

### 5.4 记忆流转机制

| 阶段 | 触发条件 | 操作 |
|------|---------|------|
| STG→SESSION | 消息数≥30 OR 任务结束 | 批量存储到PG |
| STG→LONG_TERM | 重要性≥0.7 OR 用户标记 | 存入Qdrant+Neo4j |
| LONG_TERM→FORGOTTEN | retention<0.1 | 删除 |
| 任意→COMPRESS | token超限 | LLM生成摘要 |

### 5.5 长程任务处理（基于Agent长程任务处理调研报告）

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

### 9.3 Eval指标

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
| docs/research/ | AI_Agent_记忆系统调研报告.md | Hermes/Hindsight/Obsidian |

---

## 十三、框架自动更新机制

### 13.1 自动化目标

将"研究文档变化 → 框架文档更新"这一行为自动化，实现：

| 目标 | 说明 |
|------|------|
| **变更监测** | 自动检测 `docs/research/` 目录下文档的增删改 |
| **影响分析** | 分析变更的研究文档影响框架的哪些部分 |
| **智能更新** | 基于变更内容自动更新 `PaperAgent未来框架设计.md` |
| **版本控制** | 记录每次更新的差异，保持可追溯 |

### 13.2 自动化架构

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          框架自动更新系统                                         │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│   │   文件监测    │ →  │   变更分析    │ →  │   LLM更新    │                  │
│   │  (Watcher)   │    │ (Analyzer)   │    │ (Updater)    │                  │
│   └──────────────┘    └──────────────┘    └──────────────┘                  │
│          │                  │                  │                            │
│          ▼                  ▼                  ▼                            │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│   │  git hooks   │    │  diff解析    │    │ 结构化Prompt │                  │
│   │  inotifywait │    │  关键词提取   │    │  Markdown生成│                  │
│   └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                            │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                          更新流程                                       │  │
│   │                                                                       │  │
│   │   1. [触发] 研究文档变更 (git commit/filewatch)                        │  │
│   │   2. [分析] 提取变更内容关键词、章节、要点的摘要                        │  │
│   │   3. [匹配] 建立 research → framework 映射关系                         │  │
│   │   4. [更新] LLM生成更新内容，合并到框架文档                            │  │
│   │   5. [记录] 输出diff记录，提交更新                                     │  │
│   │                                                                       │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 13.3 核心组件

#### 13.3.1 文件监测器 (FileWatcher)

```python
class ResearchDocWatcher:
    """监测研究文档变更"""

    def __init__(self, research_dir: str, framework_file: str):
        self.research_dir = research_dir
        self.framework_file = framework_file
        self.last_mtime = {}

    def get_changed_files(self) -> list[dict]:
        """获取变更的文件列表"""
        changed = []
        for root, dirs, files in os.walk(self.research_dir):
            for f in files:
                if f.endswith('.md'):
                    path = os.path.join(root, f)
                    mtime = os.path.getmtime(path)
                    if path not in self.last_mtime:
                        self.last_mtime[path] = mtime
                    elif mtime > self.last_mtime[path]:
                        changed.append({
                            'path': path,
                            'mtime': mtime,
                            'rel_path': os.path.relpath(path, self.research_dir)
                        })
                    self.last_mtime[path] = mtime
        return changed
```

#### 13.3.2 变更分析器 (ChangeAnalyzer)

```python
class ChangeAnalyzer:
    """分析变更内容，提取关键信息"""

    # 研究文档 → 框架章节 映射
    MAPPING = {
        "Agent协议生态调研报告.md": ["二、2.2四大协议层", "三、Agent体系设计"],
        "Agent提示词工程指南.md": ["三、3.3Agent Loop模式", "五、提示词规范"],
        "COMPLETE_AGENT_EVALUATION_GUIDE.md": ["四、Harness质量保障体系"],
        "Agent长程任务处理调研报告.md": ["五、5.5长程任务处理"],
        "PaperAgent_Skill_调研报告.md": ["三、3.4Skill体系重构"],
        "AI_Agent_记忆系统调研报告.md": ["五、记忆系统v3.0"],
        "意图识别技术调研报告.md": ["六、意图路由系统"],
        "PDF解析技术调研报告.md": ["八、PDF解析系统"],
        "日志系统调研报告.md": ["九、可观测性架构"],
    }

    def analyze(self, changed_file: str, content: str) -> dict:
        """分析变更内容"""
        rel_path = os.path.relpath(changed_file, "docs/research")

        # 1. 提取文档标题和关键章节
        sections = self._extract_sections(content)

        # 2. 提取关键要点（结论性语句）
        key_points = self._extract_key_points(content)

        # 3. 确定影响的框架章节
        impacted = self.MAPPING.get(rel_path, [])
        if not impacted:
            impacted = self._fuzzy_match(rel_path)

        return {
            'source': rel_path,
            'sections': sections,
            'key_points': key_points,
            'impacted_framework_sections': impacted,
            'change_type': self._classify_change(content)
        }
```

#### 13.3.3 LLM更新器 (FrameworkUpdater)

```python
class FrameworkUpdater:
    """基于LLM自动更新框架文档"""

    SYSTEM_PROMPT = """你是一个专业的技术文档工程师。
任务是分析研究文档的变更内容，自动更新框架设计文档。

工作流程：
1. 读取变更的研究文档内容
2. 理解变更的核心要点（新技术、新方案、修改点）
3. 根据映射关系，确定需要更新的框架章节
4. 生成更新内容，保持文档风格一致
5. 输出一致的Markdown格式

注意事项：
- 保持现有框架结构的完整性
- 新增内容放在合适的位置
- 修改内容保持上下文连贯
- 保留关键的技术细节和参数"""

    UPDATE_PROMPT = """## 任务：更新框架文档

### 变更的研究文档
文件: {changed_file}
类型: {change_type}

### 研究文档核心内容
{content_summary}

### 需要更新的框架章节
{impacted_sections}

### 当前框架文档相关内容
{fw_excerpt}

### 要求
1. 提取研究文档中最关键的3-5个更新点
2. 将其融入框架文档的对应章节
3. 保持框架文档的整体结构和风格
4. 用中文输出更新后的框架章节内容"""

    def update(self, analysis: dict, framework_content: str) -> str:
        """执行更新"""
        prompt = self.UPDATE_PROMPT.format(
            changed_file=analysis['source'],
            change_type=analysis['change_type'],
            content_summary=self._summarize(analysis['key_points']),
            impacted_sections=', '.join(analysis['impacted_framework_sections']),
            fw_excerpt=self._get_fw_excerpt(framework_content, analysis['impacted_framework_sections'])
        )
        # 调用LLM更新
        return llm_call(prompt, system=self.SYSTEM_PROMPT)
```

### 13.4 触发机制

| 触发方式 | 实现 | 适用场景 |
|----------|------|---------|
| **Git Hook** | `post-commit` 钩子 | 提交研究文档后自动触发 |
| **文件监听** | `watchdog` 库 | 开发过程中实时更新 |
| **定时任务** | `cron` / APScheduler | 定期全量审查 |
| **API调用** | REST endpoint | 手动触发/CI集成 |

#### Git Hook 实现

```bash
#!/bin/bash
# .git/hooks/post-commit

# 获取本次提交变更的研究文档
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD | grep "docs/research/")

if [ -n "$CHANGED_FILES" ]; then
    echo "检测到研究文档变更，开始更新框架文档..."
    python scripts/update_framework.py
    git add docs/plans/architecture/PaperAgent未来框架设计.md
    git commit --amend --no-edit
fi
```

### 13.5 完整脚本实现

```python
#!/usr/bin/env python3
"""
scripts/update_framework.py
框架自动更新脚本
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
RESEARCH_DIR = PROJECT_ROOT / "docs" / "research"
FRAMEWORK_FILE = PROJECT_ROOT / "docs" / "plans" / "architecture" / "PaperAgent未来框架设计.md"
SCRIPT_DIR = Path(__file__).parent


def load_file(path: Path) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def save_file(path: Path, content: str):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def extract_frontmatter(content: str) -> tuple[dict, str]:
    """提取 Markdown frontmatter"""
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            frontmatter = content[3:end].strip()
            body = content[end+3:].strip()
            # 解析 frontmatter
            meta = {}
            for line in frontmatter.split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip()
            return meta, body
    return {}, content


def update_frontmatter(meta: dict) -> dict:
    """更新元信息"""
    meta['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    meta['auto_update'] = 'true'
    return meta


def main():
    # 1. 加载框架文档
    framework = load_file(FRAMEWORK_FILE)
    meta, body = extract_frontmatter(framework)

    # 2. 扫描研究文档目录，获取所有文档
    research_files = list(RESEARCH_DIR.rglob("*.md"))
    print(f"发现 {len(research_files)} 份研究文档")

    # 3. 分析每个文档，生成摘要
    summaries = []
    for rf in research_files:
        content = load_file(rf)
        # 提取标题（第一个 # 开头）
        lines = content.split('\n')
        title = ""
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break

        # 提取关键要点（简单的启发式规则）
        key_points = []
        for line in lines:
            if any(keyword in line for keyword in ['关键', '核心', '推荐', '重要', '最佳', '✅', '⭐']):
                key_points.append(line.strip())

        summaries.append({
            'file': rf.relative_to(PROJECT_ROOT),
            'title': title,
            'key_points': key_points[:5]  # 最多5个要点
        })

    # 4. 生成更新报告
    update_report = f"""## 自动更新报告

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 研究文档总数: {len(research_files)}

### 文档清单

"""
    for s in summaries:
        update_report += f"#### {s['title']}\n"
        update_report += f"- 文件: `{s['file']}`\n"
        if s['key_points']:
            update_report += "- 关键要点:\n"
            for kp in s['key_points']:
                update_report += f"  - {kp}\n"
        update_report += "\n"

    # 5. 更新 frontmatter
    meta = update_frontmatter(meta)

    # 6. 构建新文档
    new_frontmatter = "---\n"
    for k, v in meta.items():
        new_frontmatter += f"{k}: {v}\n"
    new_frontmatter += "---\n\n"

    new_framework = new_frontmatter + body + "\n\n" + update_report

    # 7. 保存
    backup_file = FRAMEWORK_FILE.with_suffix('.md.bak')
    save_file(backup_file, framework)  # 备份
    save_file(FRAMEWORK_FILE, new_framework)

    print(f"✅ 框架文档已更新")
    print(f"📄 备份: {backup_file}")
    print(f"📝 更新报告已追加到文档末尾")


if __name__ == "__main__":
    main()
```

### 13.6 使用流程

```
┌────────────────────────────────────────────────────────────────┐
│                    自动化使用流程                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  方式一：Git Hook（推荐）                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. 研究员提交研究文档                                     │   │
│  │  2. post-commit 钩子触发 update_framework.py             │   │
│  │  3. 自动分析变更，更新框架文档                             │   │
│  │  4. 自动提交更新（或等待人工审核）                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
│  方式二：手动触发                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  $ python scripts/update_framework.py                     │   │
│  │  发现 17 份研究文档                                         │   │
│  │  ✅ 框架文档已更新                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
│  方式三：API 调用（CI/CD 集成）                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  POST /api/framework/update                              │   │
│  │  {                                                   │   │
│  │    "research_dir": "docs/research",                    │   │
│  │    "framework_file": "docs/plans/architecture/..."    │   │
│  │  }                                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 13.7 与现有系统的集成

| 现有系统 | 集成点 | 说明 |
|----------|--------|------|
| **CLAUDE.md** | `scripts/update_framework.py` | 在代码管理规范中添加自动更新指引 |
| **Git Hooks** | `.git/hooks/post-commit` | 提交研究文档后自动触发 |
| **Memory** | `MEMORY.md` | 记录自动更新系统的配置和使用偏好 |
| **文档索引** | `docs/README.md` | 框架文档已收录，自动化可追踪版本 |

### 13.8 进一步优化方向

| 优化方向 | 说明 | 优先级 |
|----------|------|--------|
| **LLM精化更新** | 使用LLM理解语义而非关键词匹配 | P0 |
| **增量更新** | 只更新变化的部分，而非全量重写 | P1 |
| **冲突处理** | 多人同时修改时的冲突检测 | P1 |
| **审核流程** | 重大更新需人工审核后生效 | P2 |
| **Diff可视化** | Web界面展示变更前后对比 | P2 |
| **通知机制** | 更新后自动通知相关人员 | P3 |

---

**版本**：v2.0
**更新日期**：2026-05-02
**基于**：当前实现 + 技术调研（17份文档）+ 开发计划