# 论文知识库 QA 与综述创新点 Agent 产品方案

> 日期：2026-05-27（更新：2026-06-01）
> 目标：基于当前项目已有能力，设计一个聚焦于”论文库 + 知识图谱 QA + 文献综述 + 创新点报告”的学术 Agent 产品。
> 核心边界：不做完整论文代写、不做全文修改润色、不做降重排版，聚焦研究分析与成果输出。
> 代码落地目录：`src/agents_v3/research_workspace/`

---

## 1. 核心定位

建议将产品定位为：

## 论文知识库分析 Agent

一句话介绍：

> 用户上传或检索一批论文后，系统自动解析论文、构建项目论文库和知识图谱；用户可以选择论文、主题或图谱子图进行 QA 问答，并基于选定范围生成“文献综述”和“创新点报告”。

产品主线不是“论文写作”，而是：

```text
论文库
  -> 论文解析
  -> 证据表
  -> 知识图谱
  -> 范围选择 QA
  -> 文献综述
  -> 创新点报告
```

这个定位的关键是：

1. QA 不是普通聊天，而是基于用户选择的论文集合或知识图谱子图进行回答。
2. 文献综述和创新点不是每次问答都自动生成，而是用户基于某个范围主动生成的正式成果物。
3. 文献综述和创新点共享同一个底层证据来源：项目论文库、证据表、知识图谱。

---

## 2. 产品边界

### 2.1 要做的功能

| 功能 | 说明 |
|---|---|
| 项目论文库 | 每个研究主题对应一个论文库，支持上传、检索、导入 |
| 论文上传与存储 | 上传 PDF，保存原文、元数据、解析文本、切片 |
| 论文解析 | 抽取标题、作者、摘要、章节、方法、数据、结论、局限 |
| 证据表 | 将论文转成结构化研究证据 |
| 知识图谱 | 构建 Paper-Method-Task-Dataset-Finding-Limitation-Gap 关系 |
| 选择范围 QA | 用户选择论文、主题、方法或知识图谱子图后提问 |
| 文献综述生成 | 基于选定论文集合和证据表生成综述 |
| 创新点报告生成 | 基于知识图谱空白、证据不足和研究趋势生成创新点 |
| 证据追溯 | 回答、综述、创新点都能追溯到论文和图谱关系 |

### 2.2 不做的功能

第一阶段明确不做：

| 不做 | 原因 |
|---|---|
| 全文论文代写 | 容易变成大而全论文工具，合规风险高 |
| 论文正文修改 | 会把产品拖向写作编辑器，与当前主线分散 |
| 降重/AIGC 规避 | 低壁垒且风险较高 |
| 格式排版 | 与研究分析主线弱相关 |
| 答辩 PPT | 可作为后续扩展，不属于 MVP |
| 多人协同审稿 | 复杂度高，先不做 |

当前阶段的产品边界应保持为：

```text
论文知识库 -> 研究分析 QA -> 文献综述 / 创新点报告
```

---

## 3. 用户流程

### 3.1 创建研究项目

用户创建一个项目，例如：

```text
项目名称：大语言模型对大学生自主学习能力的影响研究
学科：教育技术学
学历层次：本科 / 硕士
研究目标：生成文献综述和创新点
```

### 3.2 构建论文库

系统支持三种来源：

```text
1. 上传 PDF
2. 按关键词检索论文
3. 导入 BibTeX / RIS / DOI 列表
```

入库后，系统做：

```text
PDF 文件存储
  -> 元数据解析
  -> 全文解析
  -> 文本分块
  -> embedding
  -> 证据字段抽取
  -> 知识图谱构建
```

### 3.3 选择回答范围

用户不是只能问整个项目，而是可以先选择范围：

```text
全项目论文库
我选中的 8 篇论文
某个主题分组
某个方法分组
某个年份范围
某个知识图谱子图
某个创新点相关论文集合
```

这个范围称为：

## Retrieval Scope

示例：

```json
{
  "project_id": "proj_001",
  "selected_paper_ids": ["p1", "p2", "p3"],
  "selected_topic_ids": ["topic_llm_feedback"],
  "selected_graph_node_ids": ["method_rag", "dataset_moodle_log"],
  "include_neighbors": true,
  "graph_hops": 2,
  "time_range": ["2021", "2026"]
}
```

### 3.4 基于选择范围 QA

用户可以问：

```text
这些论文主要研究了什么？
这些论文共同不足是什么？
这些论文之间有什么关系？
基于这些论文生成一篇文献综述。
基于这个知识图谱子图找 3 个创新点。
这些论文能不能支撑我的选题？
这个创新点有什么证据和风险？
```

回答必须声明范围：

```text
以下回答仅基于你当前选择的 8 篇论文和 2 跳知识图谱关系。
```

这样可以降低幻觉，也让用户明确知道系统回答的边界。

### 3.5 生成正式成果

系统固定生成两种正式成果：

```text
1. 文献综述
2. 创新点报告
```

触发方式不是固定自动生成，而是按需触发：

| 触发方式 | 说明 |
|---|---|
| 用户点击生成 | 最主要方式 |
| 用户在 QA 中明确要求 | 如“基于这些论文生成综述” |
| 论文库达到条件后提示 | 如已解析 20 篇论文 |
| 新增论文后提示更新 | 增量更新已有报告 |
| 用户保存 QA 回答为素材 | 将回答沉淀进综述或创新点报告 |

---

## 4. 文献综述如何生成

### 4.1 生成输入

文献综述不是直接从 PDF 全文生成，而是从结构化材料生成：

```text
选定论文集合
+ 论文元数据
+ 论文卡片
+ 证据表
+ 主题聚类
+ 知识图谱关系
+ 用户研究目标
```

### 4.2 论文卡片

每篇论文入库后生成一张论文卡片：

```text
标题
年份
作者
研究问题
研究方法
数据/样本
核心发现
局限
未来工作
可支持的主题
可支持的创新点
```

### 4.3 证据表

证据表是文献综述的核心中间层：

| 字段 | 说明 |
|---|---|
| paper_id | 论文 ID |
| research_question | 研究问题 |
| method | 研究方法 |
| data_or_sample | 数据或样本 |
| finding | 核心发现 |
| limitation | 局限 |
| future_work | 未来工作 |
| topic | 所属主题 |
| evidence_strength | 证据强度 |
| citation_context | 可引用片段 |

### 4.4 综述输出结构

建议默认生成：

```text
1. 研究背景
2. 研究主题划分
3. 代表性文献和研究脉络
4. 主要研究方法
5. 主要研究结论
6. 现有研究不足
7. 未来研究趋势
8. 参考文献
```

文献综述的本质是：

```text
对选定论文集合的结构化综合
```

而不是：

```text
LLM 根据题目凭空写一段综述
```

---

## 5. 创新点如何生成

### 5.1 创新点来源

创新点不是“灵感列表”，而是从知识图谱和证据表中推导：

```text
1. 图谱中的稀疏关系
2. 多篇论文共同提到的局限
3. 研究方法迁移空间
4. 数据集或场景空白
5. 时间趋势中的新方向
6. 支持/反对证据不充分的争议点
7. 现有论文 future work 的聚合
```

### 5.2 创新点报告结构

每个创新点建议固定输出：

```text
创新点名称
创新点描述
为什么是创新
已有研究基础
现有研究空白
支撑文献
限制或反对证据
实现可行性
风险
可转化论文题目
```

### 5.3 创新点评分

建议给每个创新点打分：

| 维度 | 说明 |
|---|---|
| Novelty | 是否有明显空白 |
| Evidence | 是否有足够文献基础 |
| Feasibility | 数据、方法、时间是否可行 |
| Risk | 风险是否可控 |
| Fit | 是否匹配用户学科和学历层次 |

示例输出：

```text
创新点 1：将学习行为日志与 LLM 交互数据结合，用于评估自主学习能力变化

为什么是创新：
当前论文库中多数研究关注问卷或访谈，较少使用行为日志与 LLM 交互数据进行联合分析。

支撑文献：
- Paper A：证明学习日志可用于学习过程分析
- Paper B：讨论 LLM 反馈对学习策略的影响

研究空白：
缺少将行为日志、LLM 反馈记录和自主学习能力量表结合的实证研究。

可行性：
中等。需要获取学习平台日志或构造实验任务。

风险：
数据获取难度较高，隐私合规要求较高。
```

---

## 6. QA 与文献综述/创新点的关系

QA 不是独立聊天功能，而是研究分析入口。

### 6.1 QA 的三类输出

| QA 输出类型 | 说明 | 后续动作 |
|---|---|---|
| 探索型回答 | 回答用户关于论文库的问题 | 可继续追问 |
| 综述素材 | 适合沉淀为综述某一节 | 加入文献综述 |
| 创新点素材 | 适合沉淀为创新点 | 加入创新点报告 |

### 6.2 QA 回答后的按钮

每次 QA 回答后可以提供：

```text
[加入文献综述]
[加入创新点报告]
[基于当前范围生成完整综述]
[基于当前范围生成创新点]
[扩大到全项目论文库再分析]
[查看证据来源]
```

### 6.3 QA 检索流程

```text
用户问题
  -> 识别 Retrieval Scope
  -> 子图检索相关实体和关系
  -> 向量检索相关正文片段
  -> 从证据表召回结构化记录
  -> 融合排序
  -> 生成回答
  -> 附带来源和范围声明
```

---

## 7. 对《论文Agent前沿开发报告.md》的继承与收敛

本方案并不是从零设计，而是对 `docs/research/论文Agent前沿开发报告.md` 中已有调研结论的进一步收敛。原报告覆盖了完整论文 Agent 的前沿系统、Agent Harness、文献综述、知识图谱、QA、写作流水线和产品化路线。本方案选择其中与当前目标最相关的部分，收敛为一个更小、更清晰的产品闭环：

```text
论文库
  -> 证据表
  -> 知识图谱
  -> 选择范围 QA
  -> 文献综述
  -> 创新点报告
```

### 7.1 从原报告继承的关键判断

| 原报告内容 | 本方案如何继承 |
|---|---|
| GPT Researcher 的规划-执行-聚合模式 | 用于论文检索、主题拆解、递归补充文献 |
| SciSage 的多层 Reflector | 用于综述生成后的结构、章节、证据反思 |
| STORM / Co-STORM 的多视角知识整合 | 用于按主题、方法、时间、争议多视角组织文献综述 |
| PaperDebugger 的可追溯和审批思想 | 不做编辑器插件，但保留“来源追溯、版本记录、用户确认更新” |
| Harness 质量保障层 | 用 Evaluator、Citation Verifier、Checkpoint、AuditTrail 控制输出质量 |
| 知识图谱和 GraphRAG | 作为 QA 和创新点发现的核心底座 |
| 文献综述是 P0 需求 | 将“文献综述”作为两个正式成果之一 |
| 现有代码应复用而非重写 | 复用搜索、PDF 解析、QA、知识图谱、写作、引用和工作流模块 |

### 7.2 对原报告能力的产品收敛

原报告提出的是完整论文 Agent，包含选题、文献综述、大纲、写作、修改、润色、格式、答辩、知识图谱、版本管理等能力。当前方案不建议一次性做全，而是先收敛为：

```text
上传/检索论文
  -> 构建项目论文库
  -> 抽取论文卡片和证据表
  -> 构建知识图谱
  -> 基于选定范围 QA
  -> 生成文献综述
  -> 生成创新点报告
```

暂不纳入 MVP：

```text
全文论文写作
论文修改润色
降重
格式排版
答辩 PPT
Overleaf / VS Code 插件
多人协作
```

这样做的原因是：原报告中的全生命周期论文 Agent 技术上很完整，但作为第一阶段产品容易过大；而“论文库 QA + 文献综述 + 创新点报告”可以充分复用已有能力，同时产品价值更集中。

### 7.3 从 Harness 设计中保留的质量控制

原报告强调 Harness = Evaluator + CheckpointManager + CircuitBreaker + HITL + AuditTrail。本方案建议保留其中与研究分析最相关的部分：

| Harness 能力 | 在本方案中的作用 |
|---|---|
| Evaluator | 检查综述结构、引用覆盖、创新点可行性 |
| Citation Verifier | 防止虚假引用，验证 DOI、标题、年份 |
| Checkpoint | 保存论文库解析、证据表、图谱和报告版本 |
| HITL | 用户确认生成、更新、纳入报告 |
| AuditTrail | 记录报告基于哪些论文、哪些范围、哪些版本生成 |
| CircuitBreaker | 防止大批 PDF 解析、检索或 LLM 调用失败造成级联错误 |

这能让文献综述和创新点报告更可信，而不是普通 LLM 生成文本。

### 7.4 从知识图谱计划中保留的能力

原报告后半部分已经规划了知识图谱、混合检索、社区检测、GraphRAG、MMR 和子图摘要。本方案最需要的是其中四项：

```text
1. Paper-Method-Dataset-Task-Finding-Limitation-Gap 图谱
2. 向量检索 + 图遍历的混合检索
3. 基于选中节点/子图的 Scope-based QA
4. 子图摘要，用于生成综述小节和创新点依据
```

可以暂缓：

```text
复杂图嵌入
大规模社区检测
多层社区摘要
企业级 Neo4j 性能优化
```

MVP 中用轻量知识图谱即可，重点是打通：

```text
选中文件/子图 -> 图谱检索 -> QA 回答 -> 综述/创新点生成
```

### 7.5 与原报告功能矩阵的对应关系

| 原报告功能矩阵 | 本方案状态 |
|---|---|
| 智能选题 | 不作为主功能，但创新点报告可输出可转化题目 |
| 文献综述 | 核心正式成果 |
| 大纲规划 | 暂不做 |
| 逐章写作 | 暂不做 |
| 语言润色 | 暂不做 |
| 格式排版 | 暂不做 |
| 查重降重 | 不做 |
| 答辩辅助 | 暂不做 |
| 知识图谱 | 核心底座 |
| 版本管理 | 只做报告版本和证据追溯，不做全文 Git 式编辑 |

因此，本方案可以看作原报告的一个聚焦 MVP：

> 从“全生命周期论文 Agent”收敛为“论文知识库分析 Agent”。

---

## 8. 参考和借鉴的前沿产品

### 8.1 Elicit：系统综述和证据表工作流

Elicit 的重要启发是：

```text
研究问题
  -> 检索
  -> 筛选
  -> 数据抽取
  -> 表格化分析
  -> 报告生成
```

可借鉴点：

| Elicit 能力 | 对本产品的借鉴 |
|---|---|
| Systematic Review workflow | 本产品也应采用“先证据表，后报告”的流程 |
| Data extraction | 从每篇论文抽取方法、样本、结论、局限 |
| Supporting quotes | 综述和创新点必须可追溯到论文证据 |
| Research reports | 文献综述和创新点是正式 artifact |

不直接照搬：

```text
不做完整严肃系统综述平台，而做轻量级项目论文库分析 Agent。
```

### 8.2 NotebookLM：Sources + QA + Artifact

NotebookLM 的产品结构很适合借鉴：

```text
用户上传 sources
  -> 基于 sources 问答
  -> 在 Studio 中生成成果物
```

可借鉴点：

| NotebookLM 模式 | 对本产品的借鉴 |
|---|---|
| Sources | 项目论文库 |
| Query sources | 基于论文库 QA |
| Studio artifact | 文献综述和创新点报告 |
| 用户主动生成成果物 | 不自动每次 QA 都生成报告 |

本产品可以采用类似结构：

```text
论文库 = Sources
研究 QA = Query
文献综述 / 创新点 = Artifact
```

### 8.3 Consensus：多论文结论聚合

Consensus 的核心价值是对多个研究结果进行综合判断，而不只是返回论文列表。

可借鉴点：

| Consensus 能力 | 对本产品的借鉴 |
|---|---|
| Research Database | 构建项目级论文数据库 |
| Consensus Meter | 对研究问题做支持/反对/不确定判断 |
| Grounded analysis | 回答要基于论文全文或可验证来源 |

本产品可做：

```text
创新点或综述观点的证据倾向：
- 支持文献
- 反对文献
- 仅相关文献
- 证据不足
```

### 8.4 Scite：Smart Citations 和引用立场

Scite 的重要启发是：

```text
引用不是只有“被引用”，还要区分 supporting / contrasting / mentioning。
```

可借鉴点：

| Scite 能力 | 对本产品的借鉴 |
|---|---|
| Supporting citations | 哪些论文支持某个观点 |
| Contrasting citations | 哪些论文限制或反驳某个观点 |
| Mentioning citations | 哪些只是相关但不构成支持 |
| Citation context | 证据必须带上下文 |

本产品可用于：

```text
创新点报告中的“支撑证据 / 限制证据”
文献综述中的“已有共识 / 争议 / 证据不足”
```

### 8.5 ResearchRabbit / Connected Papers / Litmaps：文献图谱和扩展

这些产品的共同点是：

```text
从一篇或一组论文出发，发现相关论文、前置研究、后续研究和研究地图。
```

可借鉴点：

| 产品 | 可借鉴能力 |
|---|---|
| ResearchRabbit | Collection、similar work、earlier/later work |
| Connected Papers | 从种子论文构建强连接论文图 |
| Litmaps | Seed map、Discover、Monitor |

本产品可做：

```text
项目论文库
  -> 研究脉络图
  -> 主题聚类
  -> 推荐补充文献
  -> 新论文增量提醒
```

### 8.6 Rayyan / Covidence / DistillerSR / ASReview：筛选和证据管理

这些系统综述工具说明：

```text
论文处理不是“读一下 PDF”，而是筛选、纳入、排除、抽取和审计。
```

可借鉴点：

| 能力 | 对本产品的借鉴 |
|---|---|
| 文献导入和去重 | 项目论文库需要管理纳入/排除 |
| 筛选状态 | 标记 included / excluded / undecided |
| 排除理由 | 生成报告时说明论文选择依据 |
| 数据抽取 | 形成证据表 |
| 审计记录 | 记录报告生成和更新版本 |

本产品可做轻量版：

```text
纳入论文：28 篇
排除论文：12 篇
排除理由：
- 主题不相关：5 篇
- 非实证研究：3 篇
- 年份过早：2 篇
- 无全文：2 篇
```

### 8.7 Scholarcy / SciSpace / Humata：PDF 解析与论文卡片

这些产品擅长把单篇 PDF 转成可读材料：

```text
PDF
  -> 摘要
  -> 重点
  -> 问答
  -> 引用定位
```

可借鉴点：

| 能力 | 对本产品的借鉴 |
|---|---|
| 单篇论文摘要 | 入库后生成论文卡片 |
| Chat with PDF | 单篇或多篇论文范围 QA |
| 关键点提取 | 抽取研究问题、方法、结论、局限 |
| 引用定位 | 回答和报告需定位来源 |

本产品不应停留在 PDF QA，而要进一步沉淀为：

```text
论文卡片 -> 证据表 -> 知识图谱 -> 综述/创新点
```

### 8.8 GPT-Researcher：多 Agent 研究工作流

GPT-Researcher（GitHub 21.1k stars）的核心启发是多角色协作的研究流程。

可借鉴点：

| GPT-Researcher 能力 | 对本产品的借鉴 |
|---|---|
| Review-Revise 循环（Writer→Reviewer→Revisor） | 综述和创新点生成后增加审查-修订环节 |
| 树状图谱探索（递归遍历 knowledge graph） | 创新点发现时递归探索图谱找 gap |
| 上下文压缩（按主题分组摘要后再生成） | 大范围论文综述时分组压缩避免超长 |
| 7 个 Agent 角色分工 | 不照搬角色数，但借鉴"规划→检索→分析→写作→审查"流程 |

本产品可做：

```text
综述生成：WriterAgent -> ReviewReviewerAgent -> ReviewRevisorAgent
创新点报告：InnovationWriterAgent -> InnovationReviewerAgent
图谱探索：_explore_graph_recursive() 递归找 gap
```

### 8.9 PapersFlow：反证检测与多 Agent 协作

PapersFlow（474M+ 论文）的核心启发是自动寻找反证。

可借鉴点：

| PapersFlow 能力 | 对本产品的借鉴 |
|---|---|
| 反证检测（自动寻找支持/反对论文） | 创新点报告中增加"反对证据"信号 |
| 多 Agent 协作 | 综述生成中的 Writer-Reviewer 分工 |
| 结构化证据提取 | 强化 EvidenceRecord 的字段完整性 |

本产品可做：

```text
创新点信号类型增加：findings_contradictions（反证信号）
每个创新点必须列出：supporting_evidence + limiting_evidence
```

### 8.10 Atlas：跨论文综合与幻觉检测

Atlas 的核心启发是跨论文综合和生成质量控制。

可借鉴点：

| Atlas 能力 | 对本产品的借鉴 |
|---|---|
| 跨论文综合 | 综述不是单篇摘要拼接，而是跨论文主题聚合 |
| 幻觉-验证比率 | 对生成内容进行事实核查，确保引用准确 |
| 思维导图可视化 | 知识图谱的时间线和主题展示 |

本产品可做：

```text
综述质量指标：hallucination_ratio = 无来源断言数 / 总断言数
创新点验证：每个创新点的 evidence_coverage = 有来源支撑的要点数 / 总要点数
```

---

## 9. 产品功能架构

### 9.1 页面结构

建议只有四个主页面：

```text
1. 项目论文库
2. 知识图谱
3. 研究 QA
4. 成果报告
```

### 9.2 项目论文库

功能：

```text
上传 PDF
检索论文
导入 BibTeX / RIS / DOI
查看解析状态
查看论文卡片
标记纳入 / 排除
按主题、方法、年份筛选
```

### 9.3 知识图谱

节点：

```text
Paper
Author
Method
Dataset
Task
Finding
Limitation
Gap
Topic
```

关系：

```text
Paper -> USES_METHOD -> Method
Paper -> USES_DATASET -> Dataset
Paper -> STUDIES_TASK -> Task
Paper -> REPORTS_FINDING -> Finding
Paper -> HAS_LIMITATION -> Limitation
Limitation -> SUGGESTS_GAP -> Gap
Paper -> CITES -> Paper
Paper -> BELONGS_TO_TOPIC -> Topic
```

### 9.4 研究 QA

核心能力：

```text
选择论文回答
选择主题回答
选择图谱子图回答
基于全项目回答
回答后保存为综述素材
回答后保存为创新点素材
```

### 9.5 成果报告

固定两类：

```text
文献综述
创新点报告
```

报告应具备：

```text
版本号
生成范围
使用论文数量
证据来源
更新时间
可导出 Markdown / Word
```

---

## 10. MVP 建议

第一版只做最小闭环：

```text
1. 创建项目
2. 上传或检索 20-30 篇论文
3. 解析论文并生成论文卡片
4. 抽取证据表
5. 构建简单知识图谱
6. 支持选择文件 / 主题 / 子图 QA
7. 一键生成文献综述
8. 一键生成创新点报告
```

### 10.1 MVP 不做

```text
全文论文写作
论文修改润色
降重
复杂协作
复杂导出格式
答辩 PPT
```

### 10.2 MVP 演示路径

```text
1. 用户创建项目：大语言模型与自主学习
2. 上传 10 篇 PDF，系统检索补充 20 篇论文
3. 系统解析论文，生成论文卡片和知识图谱
4. 用户选择“实证研究”主题子图
5. 用户问：这些研究共同不足是什么？
6. 系统基于子图回答，并给出证据来源
7. 用户点击：基于当前范围生成创新点报告
8. 用户选择全项目论文库
9. 用户点击：生成文献综述
10. 系统输出文献综述和创新点报告
```

---

## 11. 为什么这个方案合理

### 11.1 它符合现有优秀产品验证过的模式

现有产品已经证明：

```text
Elicit 证明：证据表和数据抽取是研究报告的基础。
NotebookLM 证明：来源库 + QA + 成果物是自然交互模式。
Consensus 证明：用户需要多论文结论聚合。
Scite 证明：引用立场和证据上下文很重要。
ResearchRabbit / Litmaps 证明：论文关系图和扩展是刚需。
Rayyan / Covidence 证明：筛选和证据管理是严肃综述的核心。
```

本产品不是简单复制它们，而是组合成一个更适合学生和早期研究者的轻量产品：

```text
论文库 + 知识图谱 + 范围选择 QA + 文献综述 + 创新点报告
```

### 11.2 它解决了“QA 和报告割裂”的问题

QA 和文献综述/创新点不是硬拼在一起。

它们的关系是：

```text
底层数据相同：项目论文库
检索结构相同：证据表 + 知识图谱
QA 是探索入口
报告是正式成果
```

也就是说：

```text
QA 不负责每次都写报告
报告也不是凭空生成
二者都基于同一套论文知识库
```

### 11.3 它避免产品过大

只保留两个正式输出：

```text
文献综述
创新点报告
```

其他功能都服务于这两个输出：

```text
上传论文是为了构建论文库
知识图谱是为了支撑 QA 和创新点
QA 是为了探索论文库
选择范围是为了控制回答依据
证据表是为了生成可靠报告
```

因此不会膨胀成论文全流程平台。

---

## 12. 当前项目可复用能力

从现有代码看，可以复用：

| 能力 | 当前模块 |
|---|---|
| 多源搜索 | `src/agents_v2/search/`, `paper_search/` |
| PDF 解析 | `src/agents_v2/tools/pdf_parser.py`, `enhanced_pdf_parser.py` |
| 文献综述 | `src/agents_v2/writing/literature_review.py` |
| QA/RAG | `src/agents_v2/academic_qa/`, `retrieval/` |
| 知识图谱 | `src/agents_v2/knowledge_graph/` |
| 引用管理 | `src/agents_v2/citation/` |
| 文本切片和检索 | `retrieval/`, `academic_qa/chunker.py` |
| 评估 | `src/agents_v2/evaluation/` |
| 工作流 | `src/agents_v2/langgraph_workflow/` |
| 前端页面基础 | `frontend/src/pages/LiteraturePage.jsx`, `KnowledgeGraphPage.jsx`, `AIAssistantPage.jsx`, `ReportsPage.jsx` |

建议新增一个聚合模块：

```text
src/agents_v2/research_workspace/
  project_library.py
  paper_card.py
  evidence_table.py
  scope.py
  scope_qa.py
  review_generator.py
  innovation_generator.py
  report_version.py
```

---

## 13. 最终产品定义

最终产品可以这样对外介绍：

> 论文知识库分析 Agent 是一个面向学生和早期研究者的学术研究分析工具。用户可以上传或检索论文，系统会自动解析论文、构建证据表和知识图谱。用户可以选择论文、主题或图谱子图进行问答，并基于选定范围生成文献综述和创新点报告。所有回答和报告都能追溯到具体论文和知识图谱关系。

一句话卖点：

> 不是帮你直接写论文，而是帮你把一批论文变成可问、可查、可追溯的文献综述和创新点。

---

## 参考来源

1. Elicit Systematic Reviews：自动搜索、筛选、数据抽取和报告生成。  
   https://pro.elicit.com/solutions/systematic-reviews

2. Elicit API Reference：提供语义搜索、系统综述和自动报告生成能力。  
   https://docs.elicit.com/

3. Consensus Research Database：强调可读取全文时生成更 grounded 的 AI analysis。  
   https://help.consensus.app/en/articles/10055108-consensus-research-database

4. Consensus Meter：将论文结果标记为 Yes / No / Possibly / Mixed。  
   https://help.consensus.app/en/articles/10069920-the-consensus-meter

5. Scite API Docs：提供 supporting、contradicting、mentioning 等 Smart Citation 统计。  
   https://api.scite.ai/docs

6. ResearchRabbit Guide：围绕 Similar Work、Earlier Work、Later Work 进行文献扩展。  
   https://www.researchrabbit.ai/help/guide

7. Connected Papers About：从 origin paper 出发分析大量论文，选择强连接论文构建图谱。  
   https://www.connectedpapers.com/about

8. Litmaps Features：Seed map、Discover、Monitor 等文献发现与追踪能力。  
   https://www.litmaps.com/features

9. Rayyan Getting Started：AI、机器学习和 NLP 支持更快筛选和结构化综述工作流。  
   https://help.rayyan.ai/hc/en-us/articles/22697630697617-2-Getting-Started-with-Rayyan-A-Quick-Start-Guide

10. Rayyan Screening：导入文献后进行 include / exclude / maybe 等筛选流程。  
    https://help.rayyan.ai/hc/en-us/articles/45703234075281-How-to-Screen-References-in-Rayyan

11. DistillerSR Systematic Review Software：AI-enabled evidence synthesis 和 evidence extraction。  
    https://www.distillersr.com/products/distillersr-systematic-review-software/

12. ASReview：用 active learning 辅助系统综述筛选。  
    https://asreview.nl/
