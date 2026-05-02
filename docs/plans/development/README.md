# Paper Agent 开发计划总览

> 规划日期：2026-05-02 | 版本：v2.0
> 融合：未来框架设计 v2.1 + 各模块开发计划 + 论文Agent开发文档 v8.1

---

## 一、项目愿景

**目标**：将 Paper Agent 从「单路径写作工具」升级为「企业级多Agent协作写作平台」

**核心演进方向**：
- 从 5 条独立工作流 → **统一编排的多Agent协作系统**（已实现 LangGraph 5 工作流）
- 从 JSON 文件存储 → **PostgreSQL + Qdrant + Neo4j 融合存储**
- 从 40+ 分散 Agent → **Harness 驱动的专业分工 Agent 体系**
- 从单点追踪 → **全链路可观测性 + 质量保障**

---

## 二、技术栈

### 2.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主语言 |
| **aiohttp** | >=3.8.0 | 异步 HTTP 服务器（端口 8000） |
| **LangGraph** | StateGraph | Agent 编排，有向无环图 + Checkpoint + HITL |
| **LangChain** | langchain-core >=0.1.0 | LLM 抽象层 |
| **Pydantic** | >=2.0.0 | 数据验证与模型定义 |

### 2.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | ^18.2.0 | UI 框架 |
| **Vite** | ^5.0.8 | 构建工具 |
| **Ant Design** | ^5.12.0 | UI 组件库 |
| **Zustand** | ^4.4.7 | 状态管理 |

### 2.3 支持的 LLM 模型（17 个，6 个提供商）

| 提供商 | 模型 | 推荐用途 |
|--------|------|---------|
| **MiniMax** | minimax-m2, minimax-m2.7 | 默认模型，性价比高 |
| **OpenAI** | gpt-4o, gpt-4o-mini, o3-mini | 通用推理 |
| **Anthropic** | claude-sonnet-4-6, claude-opus-4-7, claude-haiku-4-5 | 长文本写作、深度分析 |
| **Qwen（阿里）** | qwen-max, qwen-plus | 中文内容处理 |
| **DeepSeek** | deepseek-chat, deepseek-reasoner | 数学推理、低成本 |
| **GLM（智谱）** | glm-4, glm-4-plus | 中文通用 |

### 2.4 存储

| 存储类型 | 说明 |
|---------|------|
| **PostgreSQL** | 关系型数据（会话、用户数据） |
| **Qdrant** | 向量存储（论文向量检索） |
| **Neo4j** | 图数据库（知识图谱） |
| **Redis** | 缓存层 |

---

## 三、系统架构

### 3.1 三层架构范式

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

### 3.3 Agent 协议生态（2026 标准）

| 协议 | 解决的问题 | 本系统应用 |
|------|-----------|-----------|
| **MCP** (Anthropic) | Agent ↔ 工具/数据源 标准化连接 | Arxiv/PubMed/Semantic Scholar MCP Server |
| **A2A** (Google/Linux基金会) | Agent ↔ Agent 标准通信 | 搜索Agent→分析Agent→写作Agent 任务分发 |
| **Agent Skills** (Anthropic) | 能力模块化封装与复用 | paper-search/paper-analysis/report-generation |
| **AG-UI** (CopilotKit) | Agent ↔ 前端 实时交互 | 流式展示搜索进度、生成进度 |

---

## 四、模块总览

| 序号 | 模块 | 优先级 | 状态 | 开发周期 | 目录 |
|------|------|--------|------|----------|------|
| 1 | MCP/A2A/Agent Skills 协议集成 | P0 | 待开始 | 2-3周 | unified/ |
| 2 | 记忆系统 v4.0 升级 | P0 | 待开始 | 3-4周 | memory/ |
| 3 | 意图路由三级级联升级 | P1 | 待开始 | 2-3周 | routing/ |
| 4 | Evaluator/Harness 质量保障体系 | P1 | 部分实现 | 3-4周 | evaluation/ |
| 5 | PDF 解析系统升级 | P1 | 待开始 | 2-3周 | tools/ |
| 6 | 可观测性架构升级 | P2 | 待开始 | 2-3周 | monitoring/ |
| 7 | 前端 AG-UI 集成 | P2 | 待开始 | 2-3周 | state/ |
| 8 | Skill 体系重构 | P2 | 待开始 | 2-3周 | skills/ |

### 辅助模块

| 模块 | 说明 |
|------|------|
| **agents/** | 8个专业Agent角色 |
| **core/** | 核心基础设施（上下文注入、Prompt缓存） |
| **diagnostic/** | 论文质量诊断 |
| **harness/** | 质量保障核心组件 |
| **knowledge_graph/** | 知识图谱服务 |
| **langgraph-workflow/** | LangGraph工作流 |
| **multimodal/** | 多模态处理 |
| **orchestration/** | 多Agent协作编排 |
| **paper_agents/** | 论文Pipeline Agent |
| **personalization/** | 用户偏好学习 |
| **retrieval/** | RAG检索管道 |
| **scheduler/** | 任务调度 |
| **search/** | 学术搜索引擎 |
| **server/** | API服务入口 |
| **storage/** | 数据持久化 |
| **topic-evaluation/** | 选题评估 |

---

## 五、六阶段写作流水线

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

---

## 六、Agent Loop 设计模式（8种）

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

---

## 七、Harness 质量保障体系

### 7.1 核心组件

```
Harness = ⟨Evaluator, CheckpointManager, CircuitBreaker, HITLManager, AuditTrail⟩
```

### 7.2 Evaluator（5维度评估）

| 维度 | 权重 | 核心指标 |
|------|------|---------|
| **学术规范性** | 20% | 引用格式、术语使用、结构规范 |
| **研究质量** | 25% | 创新性、严谨性、贡献度 |
| **内容完整性** | 20% | 文献覆盖、论证完整、局限承认 |
| **表达质量** | 15% | 清晰度、连贯性、语法风格 |
| **逻辑严谨性** | 20% | 因果推理、论据质量、结论推导 |

### 7.3 CircuitBreaker 配置

```python
thresholds = {
    "llm_error_rate": 0.3,       # LLM调用错误率 >30% → 熔断
    "consecutive_failures": 5,   # 连续失败5次 → 熔断
    "timeout_seconds": 300,      # 单步超过5分钟 → 熔断
    "cost_limit": 5.0,          # 单次会话超过$5 → 熔断
}
states = ["CLOSED", "OPEN", "HALF_OPEN"]
```

### 7.4 HITL 介入点

| 介入点 | 说明 |
|--------|------|
| `after_outline` | 大纲完成后需人工确认 |
| `after_literature` | 文献综述完成后需审核 |
| `after_section` | 每章节完成后可选审核 |
| `before_final` | 终稿前需全面审核 |
| `on_low_quality` | 质量评分<阈值时强制中断 |

---

## 八、记忆系统 v4.0

### 8.1 架构设计

```
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│    短期记忆           │  │    会话记忆           │  │    长期记忆           │
│  (ShortTermMemory)    │  │  (SessionMemory)      │  │  (LongTermMemory)     │
│  范围: 当前任务        │  │  范围: 任务内跨Agent    │  │  范围: 跨任务持久化     │
│  存储: 内存 (LRU)      │  │  存储: 内存/文件        │  │  存储: SQLite/向量库   │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

### 8.2 遗忘曲线

```
retention = importance × e^(-t/S)

重要性等级与S参数：
- CRITICAL (1.0): S = ∞ (永不遗忘)
- HIGH (0.8): S = 604,800秒 (7天)
- MEDIUM (0.5): S = 86,400秒 (1天)
- LOW (0.3): S = 3,600秒 (1小时)
```

### 8.3 智能触发机制

```
_should_recall_memories() - 历史关键词检测
  检查: ["之前", "上次", "曾经", "还记得", ...]
  包含关键词 → 触发召回 → 节省token
```

---

## 九、意图路由三级级联

### 9.1 架构设计

```
用户输入
  → Layer 1: 关键词快速匹配（<1ms, acc 60-75%）
    → 置信度不足 ↓
  → Layer 2: 语义向量路由（10-50ms, acc 80-92%）[新增]
    → 置信度不足 ↓
  → Layer 3: LLM深度分类（500ms-2s, acc 90-96%）
    → Layer 4: 降级兜底（默认意图）
```

### 9.2 预期效果

| 指标 | 当前 | 改造后 | 提升 |
|------|:---:|:---:|:---:|
| P50路由延迟 | ~800ms | ~15ms | **53x更快** |
| P95路由延迟 | ~2s | ~800ms | 2.5x更快 |
| 每万次路由成本 | $18-30 | $2-5 | **成本降低85%** |
| LLM路由占比 | 60% | 20% | 减少2/3 |

---

## 十、数据源（6个学术数据库）

| 数据源 | API | 类型 | 优先级 |
|--------|-----|------|--------|
| **arXiv** | export.arxiv.org | 预印本 | P0 |
| **PubMed** | eutils.ncbi.nlm.nih.gov | 学术数据库 | P0 |
| **Semantic Scholar** | api.semanticscholar.org | 学术搜索 | P1 |
| **CrossRef** | api.crossref.org | 元数据 | P1 |
| **DBLP** | api.dblp.org | 计算机文献 | P1 |
| **OpenAlex** | api.openalex.org | 学术知识库 | P1 |

---

## 十一、开发依赖关系

```
模块1 (MCP/A2A) ─────────┬──→ 模块8 (Skill体系重构)
                         │
模块2 (记忆系统) ─────────┼──→ 模块4 (Harness)
                         │
模块3 (意图路由) ─────────┤
                         │
模块5 (PDF解析) ──────────┼──→ 模块6 (可观测性)
                         │
模块7 (前端AG-UI) ────────┘
```

---

## 十二、五条工作流路径

| 路径 | 节点序列 | 说明 |
|------|---------|------|
| **Search** | router → crawler → selector → END | 论文搜索筛选 |
| **Writing** | router → memory → crawler → selector → multimodal → kg → outline → write → review → evaluator → END | 完整写作流程 |
| **Report** | router → report_crawl → report_analyze → report_gen → END | 定时报告生成 |
| **QA** | router → qa_search → qa_synthesize → qa_answer → END | 智能问答 |
| **Revision** | router → revise → refine → polish → END | 论文修订润色 |

---

## 十三、部署架构

### Docker Compose 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| `frontend` | 3000 | React 前端（Nginx） |
| `paper-agent` | 8000 | Python 后端 |
| `postgres` | 5432 | PostgreSQL 数据库 |
| `redis` | 6379 | Redis 缓存 |
| `neo4j` | 7474/7687 | Neo4j 图数据库 |
| `prometheus` | 9090 | 监控（可选） |
| `grafana` | 3001 | 监控面板（可选） |

### 快速启动

```bash
# 开发环境 - 后端
pip install -r requirements.txt
python -m src.main

# 开发环境 - 前端
cd frontend && npm install && npm run dev

# Docker 部署
docker-compose up -d
```

---

## 十四、测试覆盖

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

## 十五、开发阶段

### Phase 1: 核心写作流水线 (MVP) ✅

- [x] 统一 Agent 基类 + LLMConfig
- [x] 多源搜索 Agent
- [x] 大纲生成 + 初稿撰写 Agent
- [x] 语言润色 + 智能修订 Agent
- [x] aiohttp API 服务 + 前端写作工作台

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

### Phase 4: 产品化 📋

- [ ] 编辑器内嵌（Overleaf / VS Code 插件）
- [ ] 版本管理 + Diff 视图
- [ ] 多人协作编辑
- [ ] 多模型 LLM Router 优化
- [ ] 流式 SSE 响应全端点
- [ ] Docker Compose 生产部署

---

## 十六、各模块详细计划

详细开发计划见各模块目录下的 `模块开发计划.md`：

- [unified/模块开发计划.md](unified/模块开发计划.md) - MCP/A2A/Agent Skills协议集成
- [memory/模块开发计划.md](memory/模块开发计划.md) - 记忆系统v4.0升级
- [routing/模块开发计划.md](routing/模块开发计划.md) - 意图路由三级级联升级
- [evaluation/模块开发计划.md](evaluation/模块开发计划.md) - Evaluator/Harness质量保障体系
- [tools/模块开发计划.md](tools/模块开发计划.md) - PDF解析系统升级
- [monitoring/模块开发计划.md](monitoring/模块开发计划.md) - 可观测性架构升级
- [state/模块开发计划.md](state/模块开发计划.md) - 前端AG-UI集成
- [skills/模块开发计划.md](skills/模块开发计划.md) - Skill体系重构

辅助模块：
- [agents/模块开发计划.md](agents/模块开发计划.md)
- [core/模块开发计划.md](core/模块开发计划.md)
- [diagnostic/模块开发计划.md](diagnostic/模块开发计划.md)
- [harness/模块开发计划.md](harness/模块开发计划.md)
- [knowledge_graph/模块开发计划.md](knowledge_graph/模块开发计划.md)
- [langgraph-workflow/模块开发计划.md](langgraph-workflow/模块开发计划.md)
- [multimodal/模块开发计划.md](multimodal/模块开发计划.md)
- [orchestration/模块开发计划.md](orchestration/模块开发计划.md)
- [paper_agents/模块开发计划.md](paper_agents/模块开发计划.md)
- [personalization/模块开发计划.md](personalization/模块开发计划.md)
- [retrieval/模块开发计划.md](retrieval/模块开发计划.md)
- [scheduler/模块开发计划.md](scheduler/模块开发计划.md)
- [search/模块开发计划.md](search/模块开发计划.md)
- [server/模块开发计划.md](server/模块开发计划.md)
- [storage/模块开发计划.md](storage/模块开发计划.md)
- [topic-evaluation/模块开发计划.md](topic-evaluation/模块开发计划.md)

---

## 十七、参考文档

| 文档 | 说明 |
|------|------|
| `docs/plans/architecture/PaperAgent未来框架设计.md` | 未来框架设计 v2.1 |
| `docs/plans/architecture/各模块开发计划.md` | 各模块详细开发计划 |
| `docs/guides/论文Agent开发文档.md` | 论文Agent开发文档 v8.1 |
| `docs/implemented/architecture/` | 已实现架构文档 |

---

**版本**：v2.0
**规划日期**：2026-05-02
**基于**：未来框架设计 v2.1 + 17份调研报告 + 论文Agent开发文档 v8.1 + 已实现架构
