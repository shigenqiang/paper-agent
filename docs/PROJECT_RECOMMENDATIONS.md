# Paper-Agent 项目整体建议

> 参考范围：`docs/career/`、`docs/implemented/README.md`、`docs/implemented/execution-paths.md`  
> 目标：让 Paper-Agent 从“功能很全的论文写作助手”收敛为“可解释、可评测、可面试的大模型应用工程项目”。

## 零、一眼看懂 Paper-Agent

当前 Paper-Agent 最大的传播问题是：读者第一眼看不出它到底是“论文写作工具”“Agent 框架”“RAG 系统”“知识图谱系统”还是“全栈应用”。因此建议先给项目建立一个清晰的第一印象。

### 1. 推荐一句话定位

**Paper-Agent 是一个面向学术调研场景的文献检索增强与证据溯源系统：它把一个研究问题拆解为可检索的子问题，从多源学术数据库召回论文，完成去重、排序、引用校验和 GraphRAG 问答，最后生成带证据来源的调研报告。**

这句话要放在 README、简历项目描述和 Demo 首页的第一屏。它比“智能论文写作助手”更清楚，也更适合大模型应用开发岗位。

### 2. 项目核心卖点

建议只突出 4 个卖点，避免一上来讲 20 个模块。

| 卖点 | 说明 | 对应能力 |
|---|---|---|
| 多源文献检索 | 同时接入 OpenAlex、arXiv、Semantic Scholar、CrossRef、PubMed，解决单一来源覆盖不足 | 搜索编排、异步并发、API 集成 |
| 文献去重与排序 | 对跨源结果做 DOI 去重、标题相似度去重、综合排序和 Cross-Encoder 重排 | 检索质量、排序策略、数据融合 |
| 证据溯源与引用校验 | 回答和报告中的结论绑定文献片段、引用编号和 DOI 元数据 | RAG 可信度、引用验证、幻觉控制 |
| GraphRAG 文献关系分析 | 抽取论文实体、方法、任务和引用关系，支持基于子图的问答和图谱展示 | 知识图谱、GraphRAG、可视化 |

### 3. 推荐 README 第一屏结构

README 首页不要先展示大量架构模块。建议先按下面结构写：

```markdown
# Paper-Agent

面向学术调研的多源文献检索增强与证据溯源系统。

输入一个研究问题，系统会自动完成：

1. 查询改写与子问题拆解
2. 多源学术数据库并行检索
3. DOI / 标题相似度去重与 Cross-Encoder 重排序
4. 文献实体关系抽取与 GraphRAG 问答
5. 生成带引用和证据来源的调研报告

核心价值：不是“自动写论文”，而是帮助用户更快构建可信的文献证据链。
```

### 4. 推荐项目标题

按不同场景可以使用不同标题：

| 场景 | 推荐标题 |
|---|---|
| README / 开源项目 | Paper-Agent: Multi-source Academic Research Agent |
| 中文简历 | 基于多源检索与 GraphRAG 的学术文献研究系统 |
| 英文简历 | Multi-source Academic Literature Research System with GraphRAG |
| Demo 页面 | 从研究问题到可溯源文献报告 |

不推荐的标题：

- 智能学术论文研究与写作助手
- 学术论文智能写作与定期报告生成系统
- AI 论文助手
- 多 Agent 自动写论文系统

这些标题都容易让人误解为“生成论文的小工具”，项目的工程重点会被淹没。

### 5. 推荐 Demo 文案

Demo 首页可以直接写：

```text
输入研究问题：
GraphRAG 在学术问答中的应用和局限是什么？

系统输出：
1. 多源召回的候选论文
2. 去重排序后的 Top-K 文献
3. 每个结论对应的证据片段和引用
4. 文献关系图谱与 GraphRAG 问答
5. 可导出的调研报告
```

这样用户一眼就知道项目做什么，不需要先理解 Agent、LangGraph、Harness、Memory 等内部概念。

### 6. 项目应该优先讲什么

建议对外讲项目时使用下面顺序：

```text
先讲用户问题：学术调研时检索分散、筛选困难、引用难校验
再讲核心方案：多源检索 + 去重排序 + 证据溯源 + GraphRAG
再讲技术实现：SearchOrchestrator、ResultMerger、Reranker、CitationVerifier、GraphRAG
最后讲工程保障：LangGraph、Checkpoint、CircuitBreaker、HITL、测试与日志
```

不要一开始就讲“多 Agent 工作流”“20 个节点”“5 条工作流”“记忆系统 v4.0”。这些是实现细节，不是项目第一卖点。

## 一、总体判断

当前项目最大的问题不是功能少，而是功能边界过宽：多 Agent、论文写作、定期报告、记忆系统、GraphRAG、MCP/A2A、前端工作台、质量评估等能力都在文档里出现，容易给人一种“什么都做了一点”的感觉。简历和面试中如果直接按现有 `career` 文档表达，会显得偏玩具化，甚至有夸大风险。

建议把项目重新定位为：

**基于多源检索与 GraphRAG 的学术文献研究系统**

核心主线应收敛为：

```text
研究问题
→ 查询改写 / 子问题拆解
→ 多源学术检索
→ 去重融合与重排序
→ 证据片段抽取
→ 引用校验与溯源
→ GraphRAG 问答 / 调研报告生成
```

“自动写论文”可以保留为报告生成能力，但不应作为项目核心卖点。更专业的表述是“证据驱动的调研报告生成”“引用约束摘要”“可溯源综述草稿”。

## 二、对 `docs/career/` 的建议

### 1. 降低过度包装风险

`docs/career/resume-project-final.md` 和 `简历项目描述-迭代优化版.md` 中存在较多强量化表达，例如：

- `搜索时间从 30-60 min 降至 3-5 s`
- `360x speedup`
- `F1=0.87`
- `写作质量从 6.3 提升至 7.9`
- `服务 200+ 研究人员`
- `827+ 测试用例，80%+ 覆盖率`
- `LLM 成本降低 40%`

如果这些数据没有严格 benchmark、日志或真实用户使用记录支撑，建议不要写进正式简历。否则面试官追问“怎么测的、数据集是什么、基线是什么、是否可复现”时会比较危险。

建议将 `career` 下的简历材料拆成三类：

| 文档 | 建议定位 |
|---|---|
| `resume-project-final.md` | 改成“保守可信版”，只写能用代码解释的能力 |
| `简历项目描述-迭代优化版.md` | 改成“候选素材池”，所有量化数据标注来源和验证状态 |
| `AI工程师简历写作指南.md` | 保留方法论，但增加“不得凭空量化”的提醒 |

### 2. 推荐简历表达方向

推荐项目标题：

```text
基于多源检索与 GraphRAG 的学术文献研究系统
```

推荐项目描述：

```text
针对学术调研中跨平台检索、文献去重筛选、证据来源追踪和引用一致性校验成本高的问题，
设计 PaperAgent 文献研究流水线。系统以检索增强和证据链管理为核心，
支持研究问题拆解、文献集合构建、相关性排序、溯源问答和调研报告生成。
```

推荐保留的能力点：

- 多源学术检索：OpenAlex、arXiv、Semantic Scholar、CrossRef、PubMed
- 检索编排：并行调度、缓存、限流、熔断、部分结果返回
- 结果融合：DOI 去重、标题相似度去重、跨源合并、综合排序
- 检索增强：query rewrite、query expansion、Cross-Encoder rerank、Self-RAG
- 证据链：引用格式化、DOI 验证、答案溯源、文献片段绑定
- GraphRAG：实体关系抽取、引用关系追踪、社区检测、图谱问答
- LangGraph：长链路工作流编排、状态管理、Checkpoint、HITL

建议弱化或删除的表达：

- “自动写完整论文”
- “服务 200+ 研究人员”
- “搜索效率提升 360 倍”
- “写作质量提升 25%”
- “2026 四大协议集成”
- “全流程无需人工干预”
- “独立负责整个系统架构设计与开发实现”，除非这是事实且能说明具体范围

## 三、对 `docs/implemented/README.md` 的建议

### 1. 当前问题

`implemented/README.md` 现在像一个“模块大地图”，模块很多，但读者很难判断：

- 哪些是核心已实现模块
- 哪些是兼容层
- 哪些是实验性模块
- 哪些只是规划或文档先行
- 哪些模块已经被主链路调用
- 哪些模块有测试覆盖

这会让项目显得庞大但不聚焦。对面试和开源展示而言，模块越多不一定越强，关键是主链路是否清楚、核心模块是否扎实。

### 2. 建议重构 README 的结构

建议将 `implemented/README.md` 改成以下结构：

```text
1. 项目定位
2. 核心主链路
3. 核心模块表
4. 已实现能力与证据路径
5. 实验性模块 / Roadmap
6. 如何运行核心 Demo
7. 如何复现实验指标
```

核心模块表建议增加“成熟度”字段：

| 模块 | 职责 | 主路径是否使用 | 测试状态 | 成熟度 |
|---|---|---:|---:|---|
| `search/` | 多源检索与搜索编排 | 是 | 待补充 | 核心 |
| `retrieval/` | 查询改写、扩展、重排序、Self-RAG | 是 | 待补充 | 核心 |
| `citation/` | DOI 验证、引用格式化、引用追踪 | 是 | 待补充 | 核心 |
| `knowledge_graph/` | GraphRAG、实体关系、社区检测 | 是 | 待补充 | 核心 |
| `langgraph_workflow/` | 长链路工作流编排 | 是 | 待补充 | 核心 |
| `writing/` | 证据驱动报告生成 | 部分 | 待补充 | 支撑 |
| `memory/` | 个性化记忆 | 视主链路而定 | 待补充 | 可选 |
| `multimodal/` | 图表/公式解析 | 否 | 待补充 | 实验 |
| `skills/`、`plugins/`、`sdk/` | 扩展机制 | 否 | 待补充 | Roadmap |

### 3. 建议建立“主链路优先级”

建议把系统分为三层，不要所有模块同权展示：

**P0 核心链路**

- `SearchOrchestrator`
- `SearchResultMerger`
- `EnhancedRetrievalPipeline`
- `CrossEncoderReranker`
- `CitationVerifier`
- `GraphRAG`
- `LangGraph Workflow`

**P1 支撑能力**

- API server
- 前端检索/图谱页面
- Checkpoint
- CircuitBreaker
- HITL
- Monitoring

**P2 实验/扩展能力**

- 完整论文生成
- 记忆系统
- 多模态解析
- MCP/A2A/Agent Skills
- 插件系统

项目展示时优先讲 P0，P1 用来体现工程可靠性，P2 只作为后续规划或探索，不要抢主线。

## 四、对 `docs/implemented/execution-paths.md` 的建议

### 1. 当前问题

`execution-paths.md` 写得很全，但包含过多入口和流程：搜索请求、FULL_PAPER、ReAct Loop、LangGraph、意图路由、记忆、存储、熔断等。作为内部文档可以，但作为项目展示会显得路线复杂。

建议减少“完整论文写作流程”的权重，突出与项目新定位一致的四条路径：

1. 文献检索路径
2. 检索增强路径
3. 证据溯源问答路径
4. GraphRAG 路径

### 2. 推荐重写的核心执行路径

#### 路径一：多源文献检索

```text
User Query
→ Query Normalize
→ SearchOrchestrator
→ OpenAlex / arXiv / Semantic Scholar / CrossRef / PubMed
→ SearchResultMerger
→ DOI Dedup + Title Similarity Dedup
→ Source-aware Ranking
→ Paper List
```

需要说明的点：

- 并行调度如何做
- 某个源失败时如何返回部分结果
- 缓存命中时如何减少外部请求
- 去重和排序规则是什么

#### 路径二：增强检索与重排序

```text
User Query
→ QueryRewriter
→ QueryExpander
→ Multi-query Retrieve
→ Cross-Encoder Rerank
→ Self-RAG Filter
→ Top-K Evidence Candidates
```

需要说明的点：

- 原始 query 和改写 query 如何共存
- 多 query 的结果如何合并
- rerank 前后如何评估
- Self-RAG 过滤的阈值和失败回退

#### 路径三：证据溯源问答

```text
Question
→ Retrieve Evidence
→ Answer Generation
→ Citation Extraction
→ DOI / Metadata Verification
→ Source Trace
→ Answer with Evidence
```

需要说明的点：

- 每个答案句子是否能绑定到文献片段
- 引用编号如何生成
- DOI 无法验证时如何标记
- 如何避免“看起来像引用但实际无来源”的内容

#### 路径四：GraphRAG

```text
Paper Collection
→ Entity Extraction
→ Relation Extraction
→ Citation Network
→ Community Detection
→ Subgraph Retrieval
→ GraphRAG Answer
```

需要说明的点：

- 图谱节点和边的 schema
- citation relation、method relation、task relation 如何区分
- 查询时如何选择子图
- 图谱答案和普通 RAG 答案如何互补

### 3. 建议补充失败路径

一个严肃工程项目要能解释失败场景。建议在执行路径中增加：

- 单个搜索源超时：返回其他源结果并记录 warning
- DOI 验证失败：引用标记为 unverified，不直接删除
- Cross-Encoder 不可用：回退到基础相关性排序
- LLM 输出无法解析：触发结构化清洗或返回可诊断错误
- GraphRAG 图谱为空：回退到普通 RAG

## 五、建议补齐的评测体系

项目想从“玩具”变成“工程项目”，最关键是评测。建议新建 `docs/evaluation/benchmark_plan.md`，用小规模可复现 benchmark 支撑简历表达。

### 1. 检索评测

准备 20 个学术研究问题，每个问题人工标注 5-10 篇相关论文。

指标：

- `Recall@20`
- `Precision@10`
- `nDCG@10`
- `MRR`
- `Coverage by Source`

对比基线：

- 只用 arXiv
- 只用 Semantic Scholar
- 多源检索但不重排
- 多源检索 + Cross-Encoder 重排

### 2. 去重评测

准备跨源重复论文样本，覆盖 DOI 缺失、标题变体、作者缩写、年份不一致等情况。

指标：

- `Dedup Precision`
- `Dedup Recall`
- `False Merge Rate`
- `False Split Rate`

### 3. 引用与溯源评测

准备 30 个问答样本，要求答案必须带引用。

指标：

- `Citation Validity`
- `Evidence Support Rate`
- `Unsupported Claim Rate`
- `DOI Verification Rate`

### 4. 性能与可靠性评测

指标：

- 搜索 P50/P95 延迟
- 缓存命中率
- 单源失败时的可用结果比例
- GraphRAG 构图耗时
- 工作流失败恢复成功率

有了这些指标，简历里才可以谨慎写“相比单源检索提升 Recall@20”等明确结论。

## 六、建议的 Demo 设计

建议只做一个强 Demo，不要展示所有功能。

输入：

```text
GraphRAG 在学术问答中的应用和局限是什么？
```

输出四块：

1. 文献列表：来源、年份、引用数、相关性分数、是否去重合并
2. Top-K 证据：每条证据对应论文、段落、引用编号
3. GraphRAG 图谱：关键实体、方法、任务、引用关系
4. 调研报告：每个结论都带引用和证据来源

这个 Demo 能同时展示检索、RAG、GraphRAG、引用校验和前端可视化，比“自动生成一篇论文”更专业。

## 七、代码与模块收敛建议

建议减少“Agent 名字很多但职责重叠”的感觉。面试中更推荐围绕以下工程模块讲：

| 推荐讲法 | 对应能力 |
|---|---|
| `SearchOrchestrator` | 多源检索、并行调度、缓存、限流、熔断 |
| `SearchResultMerger` | DOI 去重、标题相似度、跨源合并、排序 |
| `EnhancedRetrievalPipeline` | query rewrite、query expansion、rerank、Self-RAG |
| `CitationVerifier / CitationTracker` | DOI 验证、引用格式化、证据追踪 |
| `GraphRAGPipeline` | 实体关系抽取、子图检索、图谱问答 |
| `WorkflowRunner` | LangGraph 状态管理、长链路编排、失败恢复 |

不建议在简历中大量堆叠 `TopicAgent`、`WriterAgent`、`ReviewerAgent`、`PolisherAgent` 等名称。它们容易让项目显得像“套 Agent 名词”，而不是扎实的检索增强系统。

## 八、建议的后续改造路线

### 第一阶段：文档收敛

- 将项目标题统一为“学术文献研究系统”方向
- 在 `career` 文档中删除未验证量化指标
- 在 `implemented/README.md` 中增加模块成熟度表
- 在 `execution-paths.md` 中突出四条核心路径

### 第二阶段：评测补齐

- 新建 benchmark 数据集
- 评测多源检索、重排序、去重、引用溯源
- 生成可复现实验报告
- 只把已验证指标写入简历

### 第三阶段：Demo 打磨

- 固定一个研究问题作为端到端 Demo
- 输出文献、证据、图谱、报告四块结果
- 前端弱化写作编辑器，强化文献表格、证据面板和图谱

### 第四阶段：工程质量

- 为 P0 模块补单元测试和集成测试
- 明确配置文件、环境变量、API Key 管理
- 增加失败回退与日志说明
- 给出最小 Docker Compose 启动路径

## 九、最终建议

Paper-Agent 最有价值的部分不是“帮用户写论文”，而是把学术研究中的证据链做清楚：

- 从哪里检索
- 为什么选这些文献
- 文献是否重复
- 排序依据是什么
- 结论来自哪篇论文的哪个片段
- 引用是否真实可验证
- 图谱关系如何支撑回答

如果项目围绕这些问题收敛，它会更像一个严肃的大模型应用工程项目；如果继续围绕“多 Agent 自动写作”发散，它会更容易被看成玩具项目或简历包装项目。
