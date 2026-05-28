# 论文知识库分析 Agent 项目模块拆解

> 日期：2026-05-27  
> 目标：把当前产品目标拆解为可开发的项目模块，明确每个模块做什么、不做什么、输入输出是什么。  
> 产品定位：论文知识库分析 Agent。核心输出为“文献综述”和“创新点报告”。

---

## 1. 项目总目标

本项目要做的是：

> 用户创建研究项目，上传或检索一批论文，系统解析论文、构建论文知识库和知识图谱；用户可以选择论文、主题或图谱子图进行 QA 问答，并基于选定范围生成文献综述和创新点报告。

核心流程：

```text
研究项目
  -> 论文上传 / 检索 / 导入
  -> 论文解析与存储
  -> 论文卡片
  -> 证据表
  -> 知识图谱
  -> 选择范围 QA
  -> 文献综述
  -> 创新点报告
```

当前阶段不做：

```text
全文论文写作
论文润色修改
降重
格式排版
答辩 PPT
多人协作
编辑器插件
```

---

## 2. 产品页面拆解

建议前端只保留四个核心页面。

## 2.1 项目论文库页面

### 目标

管理一个研究项目下的全部论文。

### 用户能做什么

```text
创建研究项目
上传 PDF
按关键词检索论文
导入 DOI / BibTeX / RIS
查看论文解析状态
查看论文卡片
筛选论文
标记纳入 / 排除
选择论文进入 QA 或报告生成
```

### 页面主要区域

```text
项目信息区
  - 项目名称
  - 研究方向
  - 学科
  - 当前论文数量
  - 解析完成率

论文操作区
  - 上传 PDF
  - 搜索论文
  - 导入引用文件

论文列表区
  - 标题
  - 作者
  - 年份
  - 来源
  - 解析状态
  - 纳入状态
  - 主题标签
  - 操作按钮

论文详情区
  - 摘要
  - 论文卡片
  - 证据字段
  - 关联节点
```

### 关键操作

```text
[上传论文]
[检索论文]
[生成论文卡片]
[加入当前 QA 范围]
[基于选中论文生成综述]
[基于选中论文生成创新点]
```

---

## 2.2 知识图谱页面

### 目标

展示项目论文库中的学术关系，并支持用户选择子图作为 QA 或报告生成范围。

### 用户能做什么

```text
查看论文、主题、方法、数据集、发现、局限之间的关系
选择某个节点
选择某个子图
查看节点证据来源
基于子图提问
基于子图生成创新点
```

### 图谱节点

```text
Paper
Author
Topic
Task
Method
Dataset
Finding
Limitation
Gap
InnovationPoint
```

### 图谱关系

```text
Paper -> BELONGS_TO_TOPIC -> Topic
Paper -> STUDIES_TASK -> Task
Paper -> USES_METHOD -> Method
Paper -> USES_DATASET -> Dataset
Paper -> REPORTS_FINDING -> Finding
Paper -> HAS_LIMITATION -> Limitation
Limitation -> SUGGESTS_GAP -> Gap
Gap -> SUPPORTS_INNOVATION -> InnovationPoint
Paper -> CITES -> Paper
```

### 页面主要区域

```text
图谱画布
  - 节点
  - 边
  - 缩放
  - 拖拽
  - 子图选择

筛选面板
  - 节点类型
  - 年份
  - 主题
  - 方法
  - 证据强度

节点详情面板
  - 节点名称
  - 类型
  - 关联论文
  - 证据片段
  - 可执行动作
```

### 关键操作

```text
[基于该节点提问]
[选择 1 跳邻居]
[选择 2 跳邻居]
[基于当前子图生成创新点]
[基于当前子图生成综述小节]
```

---

## 2.3 研究 QA 页面

### 目标

让用户基于选定范围进行问答。QA 是研究分析入口，不是普通聊天。

### 用户能做什么

```text
选择 QA 范围
向论文库提问
查看答案依据
把答案保存为综述素材
把答案保存为创新点素材
扩大或缩小回答范围
```

### QA 范围

```text
全项目论文库
选中的论文
主题分组
方法分组
年份范围
知识图谱节点
知识图谱子图
创新点相关证据集
```

### 页面主要区域

```text
范围选择区
  - 当前 Scope
  - 论文数量
  - 图谱节点数量
  - 是否包含邻居节点

聊天区
  - 用户问题
  - 系统回答
  - 证据来源
  - 范围声明

证据区
  - 支撑论文
  - 证据片段
  - 图谱路径
  - 不确定性说明

动作区
  - 加入文献综述
  - 加入创新点报告
  - 生成完整综述
  - 生成创新点报告
```

### QA 输出格式

每个回答建议包含：

```text
回答正文
回答范围
支撑证据
相关论文
图谱路径
不确定性
下一步建议
```

### 示例问题

```text
这些论文主要研究了哪些问题？
这些论文共同不足是什么？
哪些方法被反复使用？
这个方法还可以迁移到哪些任务？
这个方向有哪些可行创新点？
基于当前范围生成一篇文献综述。
基于当前子图生成 3 个创新点。
```

---

## 2.4 成果报告页面

### 目标

展示和管理两个正式成果：

```text
文献综述
创新点报告
```

### 用户能做什么

```text
生成报告
查看报告版本
查看报告依据
更新报告
导出 Markdown / Word
查看引用来源
```

### 页面主要区域

```text
报告类型切换
  - 文献综述
  - 创新点报告

报告正文区
  - 标题
  - 章节
  - 引用
  - 证据标记

来源追溯区
  - 使用论文数量
  - 使用 Scope
  - 证据表记录
  - 图谱路径

版本区
  - v1
  - v2
  - 更新时间
  - 变更原因
```

### 关键操作

```text
[生成第一版]
[基于新增论文更新]
[基于当前 QA 素材更新]
[导出 Markdown]
[导出 Word]
[查看证据来源]
```

---

## 3. 后端模块拆解

建议新增一个聚合目录：

```text
src/agents_v2/research_workspace/
```

内部模块如下。

## 3.1 Project Service

### 职责

管理研究项目。

### 功能

```text
创建项目
更新项目信息
列出项目
获取项目详情
删除项目
统计项目状态
```

### 数据

```text
project_id
name
description
discipline
education_level
research_goal
created_at
updated_at
```

---

## 3.2 Paper Library Service

### 职责

管理项目下的论文。

### 功能

```text
上传 PDF
检索论文
导入 DOI / BibTeX / RIS
保存论文元数据
保存 PDF 文件路径
管理纳入 / 排除状态
管理标签和主题
```

### 数据

```text
paper_id
project_id
title
authors
year
venue
doi
abstract
pdf_path
source
status
included
exclude_reason
created_at
```

---

## 3.3 Paper Parser

### 职责

解析 PDF 和论文元数据。

### 功能

```text
PDF 文本抽取
章节识别
参考文献抽取
图表文本抽取
摘要抽取
正文分块
```

### 输出

```text
full_text
sections
references
chunks
metadata
```

---

## 3.4 Paper Card Generator

### 职责

把单篇论文转成结构化论文卡片。

### 输入

```text
论文元数据
摘要
正文片段
章节内容
```

### 输出

```text
title
research_question
method
data_or_sample
key_findings
limitations
future_work
topics
possible_gaps
```

### 质量要求

```text
不能编造论文中没有的内容
找不到字段时应标记 unknown
每个关键字段尽量附带来源片段
```

---

## 3.5 Evidence Table Service

### 职责

将论文卡片聚合成项目级证据表。

### 功能

```text
生成 evidence record
更新 evidence record
按主题查询
按方法查询
按论文查询
按 Scope 查询
```

### 字段

```text
evidence_id
paper_id
project_id
research_question
method
data_or_sample
finding
limitation
future_work
topic
evidence_strength
citation_context
source_section
```

---

## 3.6 Knowledge Graph Service

### 职责

构建和查询项目知识图谱。

### 功能

```text
从论文卡片生成节点
从证据表生成关系
查询邻居节点
查询子图
查询图谱路径
按 Scope 返回相关图谱上下文
发现潜在 Gap
```

### 输出

```text
nodes
edges
subgraph
paths
graph_context
```

---

## 3.7 Retrieval Scope Service

### 职责

管理用户当前选择的回答范围。

### Scope 类型

```text
project_scope
selected_papers_scope
topic_scope
method_scope
year_scope
graph_node_scope
graph_subgraph_scope
innovation_scope
```

### Scope 数据结构

```python
class RetrievalScope:
    project_id: str
    selected_paper_ids: list[str]
    selected_topic_ids: list[str]
    selected_method_ids: list[str]
    selected_graph_node_ids: list[str]
    selected_graph_edge_ids: list[str]
    include_neighbors: bool
    graph_hops: int
    time_range: tuple[str, str] | None
```

---

## 3.8 Scope-based QA Service

### 职责

基于用户选择的 Scope 回答问题。

### 流程

```text
用户问题
  -> 读取 Retrieval Scope
  -> 图谱检索
  -> 向量检索
  -> 证据表检索
  -> 融合排序
  -> LLM 生成回答
  -> 返回证据来源和范围声明
```

### 输出

```text
answer
scope_summary
supporting_papers
evidence_records
graph_paths
uncertainty
suggested_actions
```

---

## 3.9 Literature Review Generator

### 职责

基于选定 Scope 生成文献综述。

### 输入

```text
Retrieval Scope
paper cards
evidence records
topic clusters
graph context
user research goal
```

### 输出结构

```text
研究背景
主题划分
代表性文献
研究方法
主要发现
研究不足
未来趋势
参考文献
```

### 质量要求

```text
每个主要观点应有论文支撑
不能引用 Scope 之外的论文
必须说明生成范围
应包含证据不足说明
```

---

## 3.10 Innovation Report Generator

### 职责

基于知识图谱和证据表生成创新点报告。

### 创新点来源

```text
图谱空白关系
共同 limitation
future work 聚合
方法迁移空间
数据集或场景空白
争议和证据不足
近年趋势
```

### 输出结构

```text
创新点名称
创新点描述
为什么是创新
已有研究基础
研究空白
支撑文献
限制证据
可行性
风险
可转化论文题目
```

---

## 3.11 Report Version Service

### 职责

管理文献综述和创新点报告版本。

### 功能

```text
保存报告版本
记录生成 Scope
记录使用论文
记录使用证据
记录更新时间
对比版本变化
```

---

## 4. Agent 工作流拆解

## 4.1 论文入库工作流

```text
Upload / Search / Import
  -> Metadata Normalize
  -> PDF Parse
  -> Chunk
  -> Embedding
  -> Store
  -> Paper Card Generate
  -> Evidence Extract
  -> KG Update
```

### 关键 Agent / Node

```text
PaperIngestionAgent
MetadataParser
PDFParser
ChunkingAgent
PaperCardAgent
EvidenceExtractorAgent
KnowledgeGraphBuilder
```

---

## 4.2 Scope-based QA 工作流

```text
Question + RetrievalScope
  -> Intent Classify
  -> Scope Resolve
  -> Graph Retrieve
  -> Vector Retrieve
  -> Evidence Retrieve
  -> Context Fusion
  -> Answer Generate
  -> Evidence Attach
```

### QA 意图

```text
summary
comparison
method_analysis
limitation_analysis
innovation_explanation
evidence_check
review_generation
innovation_generation
```

---

## 4.3 文献综述生成工作流

```text
Scope
  -> Collect Papers
  -> Collect Evidence
  -> Topic Cluster
  -> Build Outline
  -> Generate Sections
  -> Citation Check
  -> Quality Evaluate
  -> Save Report Version
```

---

## 4.4 创新点生成工作流

```text
Scope
  -> Collect Graph Context
  -> Detect Gaps
  -> Aggregate Limitations
  -> Analyze Method Transfer
  -> Generate Candidate Innovations
  -> Score Innovations
  -> Attach Evidence
  -> Save Report Version
```

---

## 5. 数据存储拆解

## 5.1 文件存储

存：

```text
PDF 原文件
导出的 Markdown / Word
解析中间文件
```

可选：

```text
本地 data/files
MinIO
S3
```

---

## 5.2 关系型数据

存：

```text
projects
papers
paper_cards
evidence_records
qa_sessions
qa_messages
reports
report_versions
```

MVP 可用 SQLite / JSON，本地产品化可用 PostgreSQL。

---

## 5.3 向量库

存：

```text
paper chunks
chunk embeddings
paper card embeddings
evidence embeddings
```

可选：

```text
FAISS
Chroma
Qdrant
```

---

## 5.4 图数据库

存：

```text
Paper
Topic
Method
Dataset
Finding
Limitation
Gap
InnovationPoint
```

MVP 可用 NetworkX / JSON graph。  
后续可接 Neo4j。

---

## 6. API 拆解

## 6.1 项目 API

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{project_id}
PUT    /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

## 6.2 论文库 API

```text
POST /api/projects/{project_id}/papers/upload
POST /api/projects/{project_id}/papers/search
POST /api/projects/{project_id}/papers/import
GET  /api/projects/{project_id}/papers
GET  /api/projects/{project_id}/papers/{paper_id}
PUT  /api/projects/{project_id}/papers/{paper_id}/status
```

## 6.3 论文解析 API

```text
POST /api/projects/{project_id}/papers/{paper_id}/parse
POST /api/projects/{project_id}/papers/{paper_id}/card
POST /api/projects/{project_id}/evidence/build
```

## 6.4 知识图谱 API

```text
POST /api/projects/{project_id}/kg/build
GET  /api/projects/{project_id}/kg
GET  /api/projects/{project_id}/kg/nodes/{node_id}
POST /api/projects/{project_id}/kg/subgraph
```

## 6.5 Scope QA API

```text
POST /api/projects/{project_id}/qa
POST /api/projects/{project_id}/qa/scope
GET  /api/projects/{project_id}/qa/sessions
GET  /api/projects/{project_id}/qa/sessions/{session_id}
```

## 6.6 报告 API

```text
POST /api/projects/{project_id}/reports/literature-review
POST /api/projects/{project_id}/reports/innovation
GET  /api/projects/{project_id}/reports
GET  /api/projects/{project_id}/reports/{report_id}
POST /api/projects/{project_id}/reports/{report_id}/update
GET  /api/projects/{project_id}/reports/{report_id}/export
```

---

## 7. MVP 开发顺序

## Phase 1：项目论文库

目标：

```text
可以创建项目，上传/检索论文，保存论文元数据和 PDF。
```

交付：

```text
Project Service
Paper Library Service
Upload API
Paper List UI
```

---

## Phase 2：论文解析和论文卡片

目标：

```text
每篇论文可以解析成文本、chunk 和论文卡片。
```

交付：

```text
PDF Parser
Chunker
Paper Card Generator
Paper Card UI
```

---

## Phase 3：证据表和知识图谱

目标：

```text
从论文卡片抽取 evidence records，并构建简单知识图谱。
```

交付：

```text
Evidence Table Service
Knowledge Graph Service
KG UI
```

---

## Phase 4：选择范围 QA

目标：

```text
用户可以选择论文或图谱子图提问，系统基于选择范围回答。
```

交付：

```text
Retrieval Scope Service
Scope-based QA Service
QA UI
Evidence Trace
```

---

## Phase 5：文献综述和创新点报告

目标：

```text
基于选定 Scope 生成文献综述和创新点报告。
```

交付：

```text
Literature Review Generator
Innovation Report Generator
Report Version Service
Reports UI
Markdown Export
```

---

## 8. 验收标准

MVP 完成标准：

```text
1. 能创建研究项目
2. 能上传或检索至少 20 篇论文
3. 能解析论文并生成论文卡片
4. 能生成项目级证据表
5. 能生成简单知识图谱
6. 能选择论文或子图作为 QA 范围
7. QA 回答能说明范围和来源
8. 能基于选定范围生成文献综述
9. 能基于选定范围生成创新点报告
10. 报告中的关键结论能追溯到论文或图谱关系
```

---

## 9. 最小演示路径

```text
1. 创建项目：大语言模型与自主学习
2. 上传 10 篇 PDF
3. 系统检索补充 20 篇论文
4. 解析论文，生成论文卡片
5. 生成证据表和知识图谱
6. 用户选择“实证研究”主题子图
7. 用户提问：这些研究共同不足是什么？
8. 系统基于子图回答，并展示证据来源
9. 用户点击：基于当前子图生成创新点报告
10. 用户选择全项目论文库
11. 用户点击：生成文献综述
12. 系统展示两个正式成果
```

---

## 10. 关键风险

| 风险 | 说明 | 对策 |
|---|---|---|
| 解析质量差 | PDF 格式复杂，抽取错误 | 保留原文片段，允许 unknown 字段 |
| 创新点泛泛 | LLM 容易输出套话 | 必须绑定图谱空白和证据 |
| QA 变普通聊天 | 没有使用 Scope | 每个回答必须声明范围 |
| 知识图谱无感 | 用户看不到图谱价值 | 图谱必须用于 QA、创新点和证据路径 |
| 报告不可追溯 | 输出像普通生成文本 | 每个关键结论绑定 evidence record |
| 产品膨胀 | 容易加入写作润色等功能 | 坚持只做综述和创新点两个正式成果 |

---

## 11. 最终边界

这个项目的目标不是：

```text
帮用户写完整论文
```

而是：

```text
帮用户把一批论文变成可追问、可追溯、可生成综述和创新点的研究知识库。
```

