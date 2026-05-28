# 论文知识库分析 Agent 开发计划

> 日期：2026-05-27  
> 产品目标：构建“论文知识库分析 Agent”，支持论文上传/检索、论文解析、证据表、知识图谱、选择范围 QA，并生成文献综述和创新点报告。  
> 开发原则：先打通最小闭环，再增强质量和体验；不做全文论文写作、润色、降重、排版、答辩 PPT。

---

## 1. MVP 总体范围

MVP 必须打通这条链路：

```text
创建项目
  -> 上传/检索论文
  -> 解析论文
  -> 生成论文卡片
  -> 抽取证据表
  -> 构建简单知识图谱
  -> 选择论文/主题/子图进行 QA
  -> 生成文献综述
  -> 生成创新点报告
  -> 追溯来源
```

MVP 不做：

```text
全文论文生成
论文修改润色
降重
复杂 Word 排版
答辩 PPT
多人协作
复杂插件
```

---

## 2. 建议开发周期

建议分 6 个阶段，总计约 6-8 周。

| 阶段 | 时间 | 核心目标 |
|---|---:|---|
| Phase 0 | 2-3 天 | 梳理现有代码并建立目标目录 |
| Phase 1 | 1 周 | 项目论文库与论文入库 |
| Phase 2 | 1-1.5 周 | 论文解析、论文卡片、证据表 |
| Phase 3 | 1-1.5 周 | 简单知识图谱与 Scope 选择 |
| Phase 4 | 1-1.5 周 | Scope-based QA |
| Phase 5 | 1-1.5 周 | 文献综述与创新点报告 |
| Phase 6 | 1 周 | 前端整合、质量控制、演示闭环 |

---

## 3. Phase 0：代码梳理与目录准备

### 目标

明确复用现有模块，新增聚合模块，避免散乱开发。

### 主要任务

1. 确认现有可复用模块：

```text
src/agents_v2/search/
src/agents_v2/tools/pdf_parser.py
src/agents_v2/tools/enhanced_pdf_parser.py
src/agents_v2/academic_qa/
src/agents_v2/retrieval/
src/agents_v2/knowledge_graph/
src/agents_v2/writing/literature_review.py
src/agents_v2/citation/
src/agents_v2/langgraph_workflow/
```

2. 新增聚合目录：

```text
src/agents_v2/research_workspace/
```

3. 新增基础文件：

```text
src/agents_v2/research_workspace/__init__.py
src/agents_v2/research_workspace/models.py
src/agents_v2/research_workspace/project_service.py
src/agents_v2/research_workspace/paper_library.py
src/agents_v2/research_workspace/paper_card.py
src/agents_v2/research_workspace/evidence_table.py
src/agents_v2/research_workspace/scope.py
src/agents_v2/research_workspace/scope_qa.py
src/agents_v2/research_workspace/review_generator.py
src/agents_v2/research_workspace/innovation_generator.py
src/agents_v2/research_workspace/report_service.py
```

4. 新增测试目录：

```text
tests/research_workspace/
```

### 验收标准

```text
新增目录结构清晰
基础模型可 import
不破坏现有测试
```

---

## 4. Phase 1：项目论文库与论文入库

### 目标

用户可以创建研究项目，上传/检索/导入论文，并形成项目论文库。

### 后端任务

#### 4.1 数据模型

在 `models.py` 中定义：

```python
Project
Paper
PaperStatus
PaperSource
ImportResult
```

建议字段：

```text
Project:
  project_id
  name
  description
  discipline
  education_level
  research_goal
  created_at
  updated_at

Paper:
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

#### 4.2 Project Service

实现：

```python
create_project()
list_projects()
get_project()
update_project()
delete_project()
get_project_stats()
```

#### 4.3 Paper Library Service

实现：

```python
add_uploaded_paper()
add_search_results()
import_references()
list_papers()
get_paper()
update_paper_status()
mark_included()
mark_excluded()
```

#### 4.4 搜索集成

复用：

```text
src/agents_v2/search/search_orchestrator.py
src/agents_v2/search/search_result_merger.py
src/agents_v2/search/arxiv_searcher.py
src/agents_v2/search/openalex_searcher.py
src/agents_v2/search/semantic_scholar_searcher.py
```

搜索结果必须能写入项目论文库。

#### 4.5 API

新增或扩展：

```text
POST /api/projects
GET  /api/projects
GET  /api/projects/{project_id}
PUT  /api/projects/{project_id}

POST /api/projects/{project_id}/papers/upload
POST /api/projects/{project_id}/papers/search
POST /api/projects/{project_id}/papers/import
GET  /api/projects/{project_id}/papers
GET  /api/projects/{project_id}/papers/{paper_id}
PUT  /api/projects/{project_id}/papers/{paper_id}/status
```

### 前端任务

新增或改造一个页面：

```text
frontend/src/pages/ResearchProjectPage.jsx
```

或在现有 `LiteraturePage.jsx` 上收敛为项目论文库页面。

页面包含：

```text
项目创建
论文上传
论文搜索
论文列表
论文状态
论文详情
```

### 测试

```text
tests/research_workspace/test_project_service.py
tests/research_workspace/test_paper_library.py
```

### 验收标准

```text
能创建项目
能上传 PDF 并保存文件路径
能检索论文并加入项目
能列出项目论文
能标记 included / excluded
```

---

## 5. Phase 2：论文解析、论文卡片、证据表

### 目标

把论文从“文件/元数据”转成“可分析结构”。

### 后端任务

#### 5.1 论文解析

复用现有解析工具：

```text
src/agents_v2/tools/pdf_parser.py
src/agents_v2/tools/enhanced_pdf_parser.py
src/agents_v2/tools/section_parser.py
src/agents_v2/tools/reference_parser.py
src/agents_v2/academic_qa/chunker.py
```

实现：

```python
parse_paper(paper_id)
extract_sections(paper_id)
chunk_paper(paper_id)
store_chunks(paper_id)
```

输出：

```text
full_text
sections
references
chunks
parse_status
```

#### 5.2 论文卡片

在 `paper_card.py` 实现：

```python
generate_paper_card(paper_id)
batch_generate_paper_cards(project_id)
get_paper_card(paper_id)
```

论文卡片字段：

```text
research_question
method
data_or_sample
key_findings
limitations
future_work
topics
possible_gaps
source_spans
confidence
```

如果找不到字段，必须输出：

```text
unknown
```

不能编造。

#### 5.3 证据表

在 `evidence_table.py` 实现：

```python
build_evidence_table(project_id)
extract_evidence_from_card(paper_card)
query_evidence_by_scope(scope)
query_evidence_by_topic(topic_id)
query_evidence_by_method(method_id)
```

证据记录字段：

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

#### 5.4 API

```text
POST /api/projects/{project_id}/papers/{paper_id}/parse
POST /api/projects/{project_id}/papers/{paper_id}/card
POST /api/projects/{project_id}/papers/cards/batch
POST /api/projects/{project_id}/evidence/build
GET  /api/projects/{project_id}/evidence
```

### 前端任务

项目论文库页面增加：

```text
解析状态
论文卡片抽屉/详情
证据表视图
批量生成按钮
```

### 测试

```text
tests/research_workspace/test_paper_parser.py
tests/research_workspace/test_paper_card.py
tests/research_workspace/test_evidence_table.py
```

### 验收标准

```text
能解析 PDF
能生成论文卡片
论文卡片有来源片段或 unknown
能生成项目级证据表
能按论文/主题/方法查询证据
```

---

## 6. Phase 3：简单知识图谱与 Scope 选择

### 目标

基于论文卡片和证据表构建轻量知识图谱，并支持选择论文、主题、方法、子图作为检索范围。

### 后端任务

#### 6.1 知识图谱构建

优先用轻量实现：

```text
NetworkX / JSON graph / 现有 knowledge_graph 服务包装
```

节点：

```text
Paper
Topic
Task
Method
Dataset
Finding
Limitation
Gap
InnovationPoint
```

关系：

```text
Paper -> BELONGS_TO_TOPIC -> Topic
Paper -> STUDIES_TASK -> Task
Paper -> USES_METHOD -> Method
Paper -> USES_DATASET -> Dataset
Paper -> REPORTS_FINDING -> Finding
Paper -> HAS_LIMITATION -> Limitation
Limitation -> SUGGESTS_GAP -> Gap
Gap -> SUPPORTS_INNOVATION -> InnovationPoint
```

实现：

```python
build_project_graph(project_id)
get_graph(project_id)
get_node(node_id)
get_neighbors(node_id, hops=1)
get_subgraph(node_ids, hops=1)
find_paths(source_id, target_id)
```

#### 6.2 Retrieval Scope

在 `scope.py` 实现：

```python
RetrievalScope
resolve_scope()
scope_to_paper_ids()
scope_to_graph_context()
scope_summary()
```

Scope 类型：

```text
all_project
selected_papers
topic
method
year_range
graph_node
graph_subgraph
innovation
```

#### 6.3 API

```text
POST /api/projects/{project_id}/kg/build
GET  /api/projects/{project_id}/kg
GET  /api/projects/{project_id}/kg/nodes/{node_id}
POST /api/projects/{project_id}/kg/subgraph
POST /api/projects/{project_id}/scope/resolve
```

### 前端任务

知识图谱页面：

```text
展示节点和边
按节点类型筛选
点击节点显示详情
选择节点/子图
设置 hops
将当前子图设为 QA 范围
```

### 测试

```text
tests/research_workspace/test_knowledge_graph.py
tests/research_workspace/test_scope.py
```

### 验收标准

```text
能从证据表构建图谱
能查询节点和邻居
能选择子图
能将子图解析为 Retrieval Scope
Scope 能返回相关论文和证据
```

---

## 7. Phase 4：Scope-based QA

### 目标

用户可以选择论文、主题、方法或子图进行问答，系统只基于该范围回答，并给出证据来源。

### 后端任务

#### 7.1 QA Service

在 `scope_qa.py` 实现：

```python
answer_question(project_id, question, scope)
retrieve_graph_context(scope, question)
retrieve_vector_context(scope, question)
retrieve_evidence_context(scope, question)
fuse_contexts()
generate_answer()
```

#### 7.2 检索融合

上下文来源：

```text
Scope 内论文 chunks
Scope 内 evidence records
Scope 内 graph nodes / edges / paths
论文卡片
```

回答必须包含：

```text
answer
scope_summary
supporting_papers
evidence_records
graph_paths
uncertainty
suggested_actions
```

#### 7.3 QA 意图识别

先用规则 + 现有路由模块：

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

#### 7.4 API

```text
POST /api/projects/{project_id}/qa
GET  /api/projects/{project_id}/qa/sessions
GET  /api/projects/{project_id}/qa/sessions/{session_id}
```

请求体：

```json
{
  "question": "这些论文共同不足是什么？",
  "scope": {
    "selected_paper_ids": ["p1", "p2"],
    "selected_graph_node_ids": ["topic_1"],
    "include_neighbors": true,
    "graph_hops": 2
  }
}
```

### 前端任务

研究 QA 页面：

```text
显示当前 Scope
聊天输入
回答展示
证据来源
图谱路径
下一步按钮
```

下一步按钮：

```text
[加入文献综述]
[加入创新点报告]
[基于当前范围生成综述]
[基于当前范围生成创新点]
[扩大到全项目]
```

### 测试

```text
tests/research_workspace/test_scope_qa.py
```

### 验收标准

```text
QA 回答限定在 Scope 内
回答明确声明范围
回答附带论文和证据来源
回答能返回图谱路径
支持基于选中论文 QA
支持基于图谱子图 QA
```

---

## 8. Phase 5：文献综述与创新点报告

### 目标

基于选定 Scope 生成两个正式成果：

```text
文献综述
创新点报告
```

### 后端任务

#### 8.1 文献综述生成

在 `review_generator.py` 实现：

```python
generate_literature_review(project_id, scope)
collect_review_materials(scope)
cluster_topics(evidence_records)
build_review_outline()
generate_review_sections()
verify_citations()
evaluate_review_quality()
```

输出结构：

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

质量要求：

```text
每个主要观点至少绑定一个 evidence record
不能引用 Scope 外论文
必须说明报告生成范围
必须列出使用论文数量
```

#### 8.2 创新点报告生成

在 `innovation_generator.py` 实现：

```python
generate_innovation_report(project_id, scope)
detect_graph_gaps()
aggregate_limitations()
aggregate_future_work()
analyze_method_transfer()
generate_candidate_innovations()
score_innovations()
attach_evidence()
```

输出结构：

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

创新点评分：

```text
novelty
evidence_strength
feasibility
risk
fit_to_user_goal
```

#### 8.3 报告版本

在 `report_service.py` 实现：

```python
save_report_version()
list_reports()
get_report()
update_report()
export_report_markdown()
```

#### 8.4 API

```text
POST /api/projects/{project_id}/reports/literature-review
POST /api/projects/{project_id}/reports/innovation
GET  /api/projects/{project_id}/reports
GET  /api/projects/{project_id}/reports/{report_id}
POST /api/projects/{project_id}/reports/{report_id}/update
GET  /api/projects/{project_id}/reports/{report_id}/export
```

### 前端任务

成果报告页面：

```text
报告类型切换
生成按钮
报告正文
证据来源侧栏
版本列表
Markdown 导出
```

### 测试

```text
tests/research_workspace/test_review_generator.py
tests/research_workspace/test_innovation_generator.py
tests/research_workspace/test_report_service.py
```

### 验收标准

```text
能基于 Scope 生成文献综述
能基于 Scope 生成创新点报告
报告说明使用范围
报告说明使用论文数量
关键结论可追溯到 evidence records
创新点不是泛泛套话，必须附带图谱空白或证据依据
```

---

## 9. Phase 6：前端整合、质量控制、演示闭环

### 目标

把后端能力串成完整可演示产品。

### 前端整合

四个核心页面：

```text
项目论文库
知识图谱
研究 QA
成果报告
```

导航建议：

```text
项目 -> 论文库 -> 图谱 -> QA -> 报告
```

### 质量控制

加入检查：

```text
引用真实性检查
Scope 外引用检查
Evidence coverage 检查
创新点泛化检查
报告结构完整性检查
QA 范围声明检查
```

### 演示数据

准备一个 demo 项目：

```text
主题：大语言模型与自主学习
论文：20-30 篇
输出：
  - 论文卡片
  - 证据表
  - 知识图谱
  - Scope QA 示例
  - 文献综述
  - 创新点报告
```

### 验收标准

```text
能按最小演示路径完整跑通
前端可以选择论文和子图
QA 能基于选择范围回答
报告能导出 Markdown
用户能追溯报告来源
```

---

## 10. 优先级排序

## P0：必须做

```text
项目论文库
论文上传/检索
论文解析
论文卡片
证据表
简单知识图谱
Retrieval Scope
Scope-based QA
文献综述生成
创新点报告生成
证据追溯
```

## P1：增强体验

```text
图谱可视化优化
报告版本对比
QA 回答保存为素材
Markdown 导出
批量解析进度
论文纳入/排除理由
```

## P2：后续再做

```text
Neo4j 深度集成
复杂 GraphRAG
社区检测
Word 导出
多用户项目
新论文监控提醒
```

## 暂不做

```text
全文论文生成
论文润色
降重
答辩 PPT
插件
复杂协作
```

---

## 11. 推荐落地顺序

如果资源有限，最短路径是：

```text
1. 复用现有搜索和 PDF 解析
2. 先实现 paper_card 和 evidence_table
3. 用 JSON/NetworkX 做轻量图谱
4. 实现 scope-based QA
5. 基于 evidence_table 生成文献综述
6. 基于 limitation/gap 生成创新点
7. 再做前端图谱和报告页
```

不要一开始就重构全局 LangGraph，也不要一开始就接复杂 Neo4j。

MVP 关键是先证明：

```text
选定一批论文/子图
  -> 系统能回答
  -> 系统能生成综述
  -> 系统能生成创新点
  -> 输出能追溯来源
```

---

## 12. 开发完成定义

本计划完成时，应能演示：

```text
1. 创建一个研究项目
2. 上传/检索论文
3. 系统解析论文并生成论文卡片
4. 系统生成证据表和知识图谱
5. 用户选择几篇论文提问
6. 系统基于这些论文回答并给出证据
7. 用户选择一个图谱子图提问
8. 系统基于子图回答并给出图谱路径
9. 用户基于当前范围生成文献综述
10. 用户基于当前范围生成创新点报告
11. 报告中的关键结论能追溯到论文和证据表
```

