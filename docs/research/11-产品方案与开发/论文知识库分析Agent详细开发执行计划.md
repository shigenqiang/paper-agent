# 论文知识库分析 Agent 详细开发执行计划

> 日期：2026-05-27  
> 用途：把“论文知识库分析 Agent”拆成可执行开发任务。  
> 产品边界：只做论文库、证据表、知识图谱、Scope QA、文献综述、创新点报告；不做全文写作、润色、降重、答辩 PPT。

---

## 0. 总体开发原则

### 0.1 一条主线

所有开发都必须服务于这条主线：

```text
论文入库
  -> 论文结构化
  -> 证据表
  -> 知识图谱
  -> 选择范围 QA
  -> 文献综述
  -> 创新点报告
```

### 0.2 三个核心中间层

系统不要直接从 PDF 生成报告。必须经过三个中间层：

```text
Paper Card
Evidence Record
Knowledge Graph
```

### 0.3 两个正式输出

正式输出只有：

```text
Literature Review
Innovation Report
```

QA 是分析入口，不是最终产物。

---

## 1. Phase 0：项目骨架与现有能力盘点

### 1.1 阶段目标

建立新产品方向的代码骨架，确认已有模块能复用，避免后续散乱开发。

### 1.2 预计时间

2-3 天。

### 1.3 具体任务

#### T0.1 创建模块目录

新增目录：

```text
src/agents_v2/research_workspace/
tests/research_workspace/
```

新增文件：

```text
src/agents_v2/research_workspace/__init__.py
src/agents_v2/research_workspace/models.py
src/agents_v2/research_workspace/storage.py
src/agents_v2/research_workspace/project_service.py
src/agents_v2/research_workspace/paper_library.py
src/agents_v2/research_workspace/parser_service.py
src/agents_v2/research_workspace/paper_card.py
src/agents_v2/research_workspace/evidence_table.py
src/agents_v2/research_workspace/graph_service.py
src/agents_v2/research_workspace/scope.py
src/agents_v2/research_workspace/scope_qa.py
src/agents_v2/research_workspace/review_generator.py
src/agents_v2/research_workspace/innovation_generator.py
src/agents_v2/research_workspace/report_service.py
src/agents_v2/research_workspace/api.py
```

#### T0.2 定义统一数据模型

在 `models.py` 中先定义 Pydantic/dataclass 模型。

必须包含：

```python
Project
Paper
PaperChunk
PaperCard
EvidenceRecord
GraphNode
GraphEdge
RetrievalScope
QARequest
QAResponse
Report
ReportVersion
InnovationPoint
```

#### T0.3 实现最小持久化层

在 `storage.py` 中实现 JSON 文件存储，先不强依赖数据库。

建议路径：

```text
data/research_workspace/
  projects.json
  papers.json
  paper_cards.json
  evidence_records.json
  reports.json
  files/
  graphs/
  chunks/
```

接口：

```python
load_collection(name: str) -> list[dict]
save_collection(name: str, items: list[dict]) -> None
upsert_item(name: str, item_id: str, item: dict) -> None
get_item(name: str, item_id: str) -> dict | None
delete_item(name: str, item_id: str) -> bool
```

#### T0.4 现有模块复用检查

写一份简短代码注释或内部文档，确认：

```text
搜索模块入口
PDF 解析入口
chunker 入口
知识图谱模块可复用入口
QA/RAG 模块可复用入口
文献综述生成模块可复用入口
引用校验模块入口
```

### 1.4 测试

新增：

```text
tests/research_workspace/test_models.py
tests/research_workspace/test_storage.py
```

测试内容：

```text
模型可实例化
JSON 存储能读写
upsert 能覆盖
delete 能删除
空集合能返回 []
```

### 1.5 验收标准

```text
research_workspace 模块可 import
基础模型通过测试
JSON 存储通过测试
不影响现有 API 和测试
```

### 1.6 风险

| 风险 | 对策 |
|---|---|
| 一开始接数据库导致复杂 | MVP 先用 JSON，本地稳定后再迁移 |
| 模型字段过多难维护 | 先保留核心字段，非核心字段放 metadata |

---

## 2. Phase 1：项目论文库与论文入库

### 2.1 阶段目标

完成研究项目和论文库管理。用户可以创建项目、上传 PDF、检索论文、导入论文元数据，并形成项目论文库。

### 2.2 预计时间

1 周。

### 2.3 后端任务

#### T1.1 ProjectService

文件：

```text
src/agents_v2/research_workspace/project_service.py
```

实现：

```python
class ProjectService:
    def create_project(self, name, description="", discipline="", education_level="", research_goal="") -> Project
    def list_projects(self) -> list[Project]
    def get_project(self, project_id: str) -> Project | None
    def update_project(self, project_id: str, **updates) -> Project
    def delete_project(self, project_id: str) -> bool
    def get_project_stats(self, project_id: str) -> dict
```

项目统计字段：

```text
paper_count
parsed_count
card_count
evidence_count
graph_node_count
report_count
```

#### T1.2 PaperLibraryService

文件：

```text
src/agents_v2/research_workspace/paper_library.py
```

实现：

```python
class PaperLibraryService:
    def add_uploaded_paper(self, project_id: str, file_path: str, metadata: dict | None = None) -> Paper
    def add_paper_metadata(self, project_id: str, metadata: dict, source: str) -> Paper
    def add_search_results(self, project_id: str, results: list[dict]) -> list[Paper]
    def list_papers(self, project_id: str, filters: dict | None = None) -> list[Paper]
    def get_paper(self, paper_id: str) -> Paper | None
    def update_paper(self, paper_id: str, **updates) -> Paper
    def mark_included(self, paper_id: str) -> Paper
    def mark_excluded(self, paper_id: str, reason: str) -> Paper
```

论文状态：

```text
imported
uploaded
parsing
parsed
card_ready
evidence_ready
failed
```

#### T1.3 文件上传保存

上传文件保存到：

```text
data/research_workspace/files/{project_id}/{paper_id}.pdf
```

要求：

```text
保留原始文件名
生成 paper_id
记录 pdf_path
文件不存在时返回明确错误
```

#### T1.4 搜索接入

先复用现有 `search` 模块。

包装接口：

```python
def search_and_add_papers(project_id: str, query: str, limit: int = 20, sources: list[str] | None = None) -> list[Paper]
```

输出统一元数据：

```text
title
authors
year
venue
doi
abstract
url
source
```

#### T1.5 导入 DOI / BibTeX / RIS

MVP 可先做 DOI 列表和简化 BibTeX。

接口：

```python
def import_doi_list(project_id: str, doi_list: list[str]) -> list[Paper]
def import_bibtex(project_id: str, bibtex_text: str) -> list[Paper]
```

没有联网元数据时，也要先创建占位 Paper。

### 2.4 API 任务

文件：

```text
src/agents_v2/research_workspace/api.py
```

先实现 aiohttp route 注册函数：

```python
def setup_research_workspace_routes(app): ...
```

接口：

```text
POST /api/rw/projects
GET  /api/rw/projects
GET  /api/rw/projects/{project_id}
PUT  /api/rw/projects/{project_id}
DELETE /api/rw/projects/{project_id}

POST /api/rw/projects/{project_id}/papers/upload
POST /api/rw/projects/{project_id}/papers/search
POST /api/rw/projects/{project_id}/papers/import
GET  /api/rw/projects/{project_id}/papers
GET  /api/rw/papers/{paper_id}
PUT  /api/rw/papers/{paper_id}
POST /api/rw/papers/{paper_id}/include
POST /api/rw/papers/{paper_id}/exclude
```

搜索请求：

```json
{
  "query": "large language models self-regulated learning",
  "limit": 20,
  "sources": ["openalex", "semantic_scholar", "arxiv"]
}
```

排除请求：

```json
{
  "reason": "topic_not_relevant"
}
```

### 2.5 前端任务

页面：

```text
frontend/src/pages/ResearchWorkspacePage.jsx
```

组件建议：

```text
ProjectList
ProjectHeader
PaperUploadPanel
PaperSearchPanel
PaperTable
PaperDetailDrawer
PaperStatusTag
```

最小 UI：

```text
左侧项目列表
右侧论文库
顶部上传/搜索
表格显示论文
点击查看详情
```

### 2.6 测试

新增：

```text
tests/research_workspace/test_project_service.py
tests/research_workspace/test_paper_library.py
tests/research_workspace/test_research_workspace_api.py
```

测试用例：

```text
创建项目成功
重复项目名允许或返回明确规则
上传论文创建 Paper
搜索结果写入项目
论文列表按 project_id 隔离
include/exclude 状态更新
缺失 project_id 返回 404
```

### 2.7 验收标准

```text
能创建项目
能上传 PDF
能搜索并加入论文
能查看项目论文列表
能标记纳入/排除
前端能完成项目和论文基本操作
```

---

## 3. Phase 2：论文解析、论文卡片、证据表

### 3.1 阶段目标

将论文库中的论文转为结构化知识：解析文本、生成论文卡片、抽取证据表。

### 3.2 预计时间

1-1.5 周。

### 3.3 后端任务

#### T2.1 ParserService

文件：

```text
src/agents_v2/research_workspace/parser_service.py
```

实现：

```python
class ParserService:
    def parse_paper(self, paper_id: str) -> dict
    def parse_project_papers(self, project_id: str, only_unparsed: bool = True) -> dict
    def get_chunks(self, paper_id: str) -> list[PaperChunk]
```

解析输出保存到：

```text
data/research_workspace/chunks/{paper_id}.json
```

chunk 字段：

```text
chunk_id
paper_id
section_title
text
start_char
end_char
token_count
```

解析失败要记录：

```text
status = failed
error_message
```

#### T2.2 PaperCardGenerator

文件：

```text
src/agents_v2/research_workspace/paper_card.py
```

实现：

```python
class PaperCardGenerator:
    def generate(self, paper_id: str) -> PaperCard
    def batch_generate(self, project_id: str, only_missing: bool = True) -> list[PaperCard]
```

Prompt 输出必须 JSON 化：

```json
{
  "research_question": "...",
  "method": "...",
  "data_or_sample": "...",
  "key_findings": ["..."],
  "limitations": ["..."],
  "future_work": ["..."],
  "topics": ["..."],
  "possible_gaps": ["..."],
  "source_spans": [
    {
      "field": "key_findings",
      "chunk_id": "chunk_x",
      "quote": "..."
    }
  ],
  "confidence": 0.76
}
```

兜底规则：

```text
字段无依据时填 unknown 或 []
禁止编造 DOI、作者、年份
source_spans 不足时 confidence 降低
```

#### T2.3 EvidenceTableService

文件：

```text
src/agents_v2/research_workspace/evidence_table.py
```

实现：

```python
class EvidenceTableService:
    def build_for_project(self, project_id: str) -> list[EvidenceRecord]
    def build_for_paper(self, paper_id: str) -> list[EvidenceRecord]
    def query(self, project_id: str, filters: dict | None = None) -> list[EvidenceRecord]
    def query_by_scope(self, scope: RetrievalScope) -> list[EvidenceRecord]
```

EvidenceRecord 字段：

```text
evidence_id
project_id
paper_id
topic
research_question
method
data_or_sample
finding
limitation
future_work
evidence_strength
citation_context
source_chunk_id
source_quote
```

#### T2.4 主题规范化

实现简单 topic normalize：

```python
normalize_topics(cards: list[PaperCard]) -> dict[str, list[str]]
```

先用规则 + LLM 合并近似主题：

```text
LLM feedback
AI feedback
automatic feedback
-> feedback mechanism
```

### 3.4 API 任务

```text
POST /api/rw/papers/{paper_id}/parse
POST /api/rw/projects/{project_id}/parse
POST /api/rw/papers/{paper_id}/card
POST /api/rw/projects/{project_id}/cards
GET  /api/rw/papers/{paper_id}/card
POST /api/rw/projects/{project_id}/evidence
GET  /api/rw/projects/{project_id}/evidence
```

### 3.5 前端任务

论文库页面增加：

```text
批量解析按钮
批量生成卡片按钮
论文卡片详情
证据表 tab
解析失败提示
```

证据表列：

```text
论文
主题
方法
发现
局限
证据强度
来源片段
```

### 3.6 测试

```text
tests/research_workspace/test_parser_service.py
tests/research_workspace/test_paper_card_generator.py
tests/research_workspace/test_evidence_table_service.py
```

测试用例：

```text
无 PDF 的 paper 解析失败且错误清楚
PDF 解析后生成 chunks
论文卡片字段齐全
unknown 字段不会导致失败
证据表能从论文卡片生成
按 topic/method 查询证据
```

### 3.7 验收标准

```text
至少能解析 5 篇 PDF
每篇能生成 PaperCard
项目能生成 EvidenceTable
证据记录能追溯到 paper_id 和 chunk_id
前端能查看论文卡片和证据表
```

---

## 4. Phase 3：知识图谱与 Retrieval Scope

### 4.1 阶段目标

从证据表构建简单知识图谱，并让用户能选择论文、主题、方法、节点或子图作为 QA 范围。

### 4.2 预计时间

1-1.5 周。

### 4.3 后端任务

#### T3.1 GraphService

文件：

```text
src/agents_v2/research_workspace/graph_service.py
```

MVP 用 JSON graph 或 NetworkX，不强依赖 Neo4j。

实现：

```python
class GraphService:
    def build_project_graph(self, project_id: str) -> dict
    def get_graph(self, project_id: str) -> dict
    def get_node(self, project_id: str, node_id: str) -> GraphNode | None
    def get_neighbors(self, project_id: str, node_id: str, hops: int = 1) -> dict
    def get_subgraph(self, project_id: str, node_ids: list[str], hops: int = 1) -> dict
    def find_paths(self, project_id: str, source_id: str, target_id: str, max_hops: int = 3) -> list[list[str]]
```

图谱保存：

```text
data/research_workspace/graphs/{project_id}.json
```

节点 ID 规则：

```text
paper:{paper_id}
topic:{normalized_topic}
method:{normalized_method}
finding:{hash}
limitation:{hash}
gap:{hash}
```

#### T3.2 图谱构建规则

从 EvidenceRecord 生成：

```text
Paper -> BELONGS_TO_TOPIC -> Topic
Paper -> USES_METHOD -> Method
Paper -> REPORTS_FINDING -> Finding
Paper -> HAS_LIMITATION -> Limitation
Limitation -> SUGGESTS_GAP -> Gap
```

Gap 初版生成规则：

```text
limitation 中高频短语
future_work 中高频方向
method 与 topic 的低连接组合
```

#### T3.3 RetrievalScopeService

文件：

```text
src/agents_v2/research_workspace/scope.py
```

实现：

```python
class RetrievalScopeService:
    def resolve(self, project_id: str, scope_payload: dict) -> RetrievalScope
    def to_paper_ids(self, scope: RetrievalScope) -> list[str]
    def to_evidence_records(self, scope: RetrievalScope) -> list[EvidenceRecord]
    def to_graph_context(self, scope: RetrievalScope) -> dict
    def summarize(self, scope: RetrievalScope) -> str
```

Scope 输入：

```json
{
  "type": "graph_subgraph",
  "selected_paper_ids": [],
  "selected_topic_ids": ["topic:feedback_mechanism"],
  "selected_method_ids": [],
  "selected_graph_node_ids": ["topic:feedback_mechanism"],
  "include_neighbors": true,
  "graph_hops": 2,
  "time_range": ["2021", "2026"]
}
```

Scope 输出必须包括：

```text
paper_ids
evidence_ids
graph_node_ids
graph_edge_ids
summary
```

### 4.4 API 任务

```text
POST /api/rw/projects/{project_id}/kg/build
GET  /api/rw/projects/{project_id}/kg
GET  /api/rw/projects/{project_id}/kg/nodes/{node_id}
POST /api/rw/projects/{project_id}/kg/subgraph
POST /api/rw/projects/{project_id}/scope/resolve
```

### 4.5 前端任务

知识图谱页面初版可简单：

```text
节点列表 + 边列表 + 节点详情
```

如果已有 G6，可做基础图谱：

```text
节点颜色按类型
点击节点显示详情
选择节点
选择 hops
设为 QA 范围
```

范围选择组件：

```text
ScopeSelector
  - 全项目
  - 选中论文
  - 选中主题
  - 选中方法
  - 当前图谱子图
```

### 4.6 测试

```text
tests/research_workspace/test_graph_service.py
tests/research_workspace/test_retrieval_scope.py
```

测试用例：

```text
证据表能构建节点和边
topic 节点能连接多篇论文
hops=1 返回直接邻居
hops=2 返回二跳邻居
scope 能解析 selected_paper_ids
scope 能解析 selected_topic_ids
scope 不存在节点返回明确错误
```

### 4.7 验收标准

```text
项目能生成知识图谱
能选择节点和子图
Scope 能返回论文、证据、图谱上下文
前端能设置当前 QA 范围
```

---

## 5. Phase 4：Scope-based QA

### 5.1 阶段目标

实现基于选定论文/主题/子图的 QA。回答必须限定范围、给出证据来源，并可触发生成综述或创新点。

### 5.2 预计时间

1-1.5 周。

### 5.3 后端任务

#### T4.1 ScopeQAService

文件：

```text
src/agents_v2/research_workspace/scope_qa.py
```

实现：

```python
class ScopeQAService:
    def answer(self, project_id: str, question: str, scope_payload: dict) -> QAResponse
    def classify_intent(self, question: str) -> str
    def retrieve_context(self, question: str, scope: RetrievalScope) -> dict
    def generate_answer(self, question: str, context: dict, scope: RetrievalScope) -> QAResponse
```

#### T4.2 QA 意图分类

MVP 先规则实现：

```text
contains "综述" / "文献综述" -> review_generation
contains "创新" / "创新点" -> innovation_generation
contains "不足" / "局限" -> limitation_analysis
contains "方法" -> method_analysis
contains "比较" / "区别" -> comparison
else -> summary
```

后续可接现有 `routing/`。

#### T4.3 上下文检索

Context 包含：

```text
scope_summary
paper_cards
evidence_records
graph_nodes
graph_edges
graph_paths
chunks
```

MVP 检索优先级：

```text
1. evidence_records
2. paper_cards
3. graph_context
4. chunks
```

#### T4.4 回答格式

QAResponse：

```json
{
  "answer": "...",
  "intent": "limitation_analysis",
  "scope_summary": "基于当前选择的 8 篇论文和 2 跳图谱邻居",
  "supporting_papers": ["p1", "p2"],
  "evidence_records": ["e1", "e2"],
  "graph_paths": [
    ["paper:p1", "limitation:x", "gap:y"]
  ],
  "uncertainty": "该结论仅基于当前选择范围，不代表全领域。",
  "suggested_actions": [
    "generate_innovation_report",
    "expand_to_project_scope"
  ]
}
```

#### T4.5 生成型问题路由

如果 intent 是：

```text
review_generation
innovation_generation
```

可以返回：

```text
建议调用报告生成 API
```

或直接调用对应 generator。

MVP 建议：

```text
QA 返回 suggested_action，由前端按钮触发正式报告生成。
```

这样避免 QA 每次自动写报告。

### 5.4 API 任务

```text
POST /api/rw/projects/{project_id}/qa
GET  /api/rw/projects/{project_id}/qa/sessions
GET  /api/rw/projects/{project_id}/qa/sessions/{session_id}
```

请求：

```json
{
  "question": "这些论文共同不足是什么？",
  "scope": {
    "type": "selected_papers",
    "selected_paper_ids": ["p1", "p2", "p3"]
  }
}
```

### 5.5 前端任务

研究 QA 页面：

```text
ScopeSummaryBar
QAChatPanel
EvidencePanel
SuggestedActions
```

回答中展示：

```text
范围声明
回答正文
证据论文
证据表记录
图谱路径
不确定性
下一步按钮
```

### 5.6 测试

```text
tests/research_workspace/test_scope_qa.py
```

测试用例：

```text
selected_papers QA 只返回选中论文证据
topic scope QA 返回相关论文
graph scope QA 返回图谱路径
问“创新点”时 suggested_actions 包含 generate_innovation_report
问“文献综述”时 suggested_actions 包含 generate_literature_review
无证据时回答应说明证据不足
```

### 5.7 验收标准

```text
QA 必须声明 Scope
QA 必须返回 evidence_records 或说明无证据
QA 不能引用 Scope 外论文
前端能从 QA 直接触发报告生成
```

---

## 6. Phase 5：文献综述与创新点报告

### 6.1 阶段目标

基于选定 Scope 生成两个正式成果：文献综述和创新点报告。

### 6.2 预计时间

1-1.5 周。

### 6.3 后端任务

#### T5.1 LiteratureReviewGenerator

文件：

```text
src/agents_v2/research_workspace/review_generator.py
```

实现：

```python
class LiteratureReviewGenerator:
    def generate(self, project_id: str, scope_payload: dict, options: dict | None = None) -> Report
    def collect_materials(self, scope: RetrievalScope) -> dict
    def build_outline(self, materials: dict) -> list[dict]
    def generate_sections(self, outline: list[dict], materials: dict) -> str
    def attach_citations(self, text: str, materials: dict) -> str
    def validate_review(self, report: Report) -> dict
```

options：

```json
{
  "language": "zh",
  "organization": "topic",
  "target_length": 3000,
  "include_method_analysis": true,
  "include_limitations": true
}
```

文献综述结构：

```text
标题
生成范围说明
使用论文数量
研究背景
主题划分
代表性文献和研究脉络
主要研究方法
主要发现
研究不足
未来趋势
参考文献
证据附录
```

#### T5.2 InnovationReportGenerator

文件：

```text
src/agents_v2/research_workspace/innovation_generator.py
```

实现：

```python
class InnovationReportGenerator:
    def generate(self, project_id: str, scope_payload: dict, options: dict | None = None) -> Report
    def collect_gap_signals(self, scope: RetrievalScope) -> dict
    def detect_graph_gaps(self, graph_context: dict) -> list[dict]
    def aggregate_limitations(self, evidence_records: list[EvidenceRecord]) -> list[dict]
    def generate_candidates(self, gap_signals: dict) -> list[InnovationPoint]
    def score_candidates(self, candidates: list[InnovationPoint]) -> list[InnovationPoint]
    def render_report(self, candidates: list[InnovationPoint]) -> str
```

创新点来源权重：

```text
共同 limitation：高
future_work 聚合：高
图谱缺失边：高
方法迁移空间：中
数据集空白：中
年份趋势：中
LLM 自由生成：低
```

创新点对象：

```text
innovation_id
name
description
why_innovative
research_foundation
gap
supporting_papers
limiting_evidence
feasibility
risk
possible_topic
scores
```

#### T5.3 创新点反泛化检查

实现简单规则：

如果创新点包含以下泛化短语但无具体证据，则降分或拒绝：

```text
多模态
深度学习
大模型
扩展样本
跨学科
优化算法
提高准确率
```

必须绑定至少：

```text
2 条 evidence_records
或 1 条 graph gap + 1 条 limitation
```

#### T5.4 ReportService

文件：

```text
src/agents_v2/research_workspace/report_service.py
```

实现：

```python
class ReportService:
    def save_report(self, report: Report) -> Report
    def list_reports(self, project_id: str, report_type: str | None = None) -> list[Report]
    def get_report(self, report_id: str) -> Report | None
    def create_version(self, report_id: str, content: str, reason: str) -> ReportVersion
    def export_markdown(self, report_id: str) -> str
```

Report 字段：

```text
report_id
project_id
type
title
content
scope
paper_ids
evidence_ids
graph_node_ids
created_at
updated_at
version
```

### 6.4 API 任务

```text
POST /api/rw/projects/{project_id}/reports/literature-review
POST /api/rw/projects/{project_id}/reports/innovation
GET  /api/rw/projects/{project_id}/reports
GET  /api/rw/reports/{report_id}
POST /api/rw/reports/{report_id}/versions
GET  /api/rw/reports/{report_id}/export/markdown
```

### 6.5 前端任务

成果报告页面：

```text
ReportTypeTabs
GenerateReportPanel
ReportViewer
EvidenceTraceSidebar
ReportVersionList
ExportButton
```

报告生成表单：

```text
Scope
报告类型
组织方式：topic / method / timeline
目标长度
是否包含方法分析
是否包含研究不足
```

### 6.6 测试

```text
tests/research_workspace/test_review_generator.py
tests/research_workspace/test_innovation_generator.py
tests/research_workspace/test_report_service.py
```

测试用例：

```text
文献综述生成包含 scope_summary
文献综述不引用 Scope 外论文
创新点至少包含 supporting_papers
泛化创新点被降分
报告能保存版本
报告能导出 Markdown
```

### 6.7 验收标准

```text
能基于全项目生成综述
能基于选中文件生成综述
能基于子图生成创新点
报告有版本和 Scope 记录
关键结论能追溯到 evidence_ids
```

---

## 7. Phase 6：前端整合与演示闭环

### 7.1 阶段目标

把模块串成完整产品体验。

### 7.2 预计时间

1 周。

### 7.3 前端页面

至少完成四个页面：

```text
ResearchWorkspacePage
PaperLibraryPage
KnowledgeGraphPage
ResearchQAPage
ResearchReportsPage
```

如果时间有限，可以合并：

```text
ResearchWorkspacePage
  - tab: 论文库
  - tab: 知识图谱
  - tab: QA
  - tab: 报告
```

### 7.4 演示项目数据

准备一个 demo：

```text
项目：大语言模型与自主学习
论文：20-30 篇
主题：LLM feedback、self-regulated learning、learning analytics
方法：survey、experiment、interview、log analysis
输出：综述 + 创新点报告
```

### 7.5 端到端演示脚本

```text
1. 创建项目
2. 搜索论文
3. 上传 PDF
4. 批量解析
5. 批量生成论文卡片
6. 生成证据表
7. 生成知识图谱
8. 选择“实证研究”主题
9. 提问：这些研究共同不足是什么？
10. 查看证据来源和图谱路径
11. 基于当前子图生成创新点报告
12. 基于全项目生成文献综述
13. 导出 Markdown
```

### 7.6 质量检查

增加自动检查：

```text
报告是否有 scope_summary
报告是否有 paper_ids
报告是否有 evidence_ids
QA 是否有范围声明
创新点是否有 supporting_papers
是否出现无来源强断言
```

### 7.7 验收标准

```text
前端能完整跑通演示脚本
后端 API 无 500 错误
报告生成后能追溯来源
QA 不会越过 Scope 引用论文
```

---

## 8. API 汇总

### 8.1 项目

```text
POST   /api/rw/projects
GET    /api/rw/projects
GET    /api/rw/projects/{project_id}
PUT    /api/rw/projects/{project_id}
DELETE /api/rw/projects/{project_id}
```

### 8.2 论文

```text
POST /api/rw/projects/{project_id}/papers/upload
POST /api/rw/projects/{project_id}/papers/search
POST /api/rw/projects/{project_id}/papers/import
GET  /api/rw/projects/{project_id}/papers
GET  /api/rw/papers/{paper_id}
PUT  /api/rw/papers/{paper_id}
POST /api/rw/papers/{paper_id}/include
POST /api/rw/papers/{paper_id}/exclude
```

### 8.3 解析和证据

```text
POST /api/rw/papers/{paper_id}/parse
POST /api/rw/projects/{project_id}/parse
POST /api/rw/papers/{paper_id}/card
POST /api/rw/projects/{project_id}/cards
POST /api/rw/projects/{project_id}/evidence
GET  /api/rw/projects/{project_id}/evidence
```

### 8.4 知识图谱和 Scope

```text
POST /api/rw/projects/{project_id}/kg/build
GET  /api/rw/projects/{project_id}/kg
GET  /api/rw/projects/{project_id}/kg/nodes/{node_id}
POST /api/rw/projects/{project_id}/kg/subgraph
POST /api/rw/projects/{project_id}/scope/resolve
```

### 8.5 QA

```text
POST /api/rw/projects/{project_id}/qa
GET  /api/rw/projects/{project_id}/qa/sessions
GET  /api/rw/projects/{project_id}/qa/sessions/{session_id}
```

### 8.6 报告

```text
POST /api/rw/projects/{project_id}/reports/literature-review
POST /api/rw/projects/{project_id}/reports/innovation
GET  /api/rw/projects/{project_id}/reports
GET  /api/rw/reports/{report_id}
POST /api/rw/reports/{report_id}/versions
GET  /api/rw/reports/{report_id}/export/markdown
```

---

## 9. 测试计划汇总

### 9.1 单元测试

```text
test_models.py
test_storage.py
test_project_service.py
test_paper_library.py
test_parser_service.py
test_paper_card_generator.py
test_evidence_table_service.py
test_graph_service.py
test_retrieval_scope.py
test_scope_qa.py
test_review_generator.py
test_innovation_generator.py
test_report_service.py
```

### 9.2 集成测试

```text
test_research_workspace_flow.py
```

覆盖：

```text
创建项目
添加论文
生成卡片
生成证据
生成图谱
Scope QA
生成综述
生成创新点
```

### 9.3 质量测试

```text
test_scope_guard.py
test_report_traceability.py
test_innovation_generic_filter.py
```

覆盖：

```text
QA 不越界引用
报告必须有 evidence_ids
创新点不能全是泛化短语
```

---

## 10. 开发依赖关系

```text
Phase 0
  -> Phase 1
      -> Phase 2
          -> Phase 3
              -> Phase 4
                  -> Phase 5
                      -> Phase 6
```

其中：

```text
Phase 4 依赖 Scope 和 EvidenceTable
Phase 5 依赖 ScopeQA 的上下文检索能力
Innovation Report 依赖 GraphService
Literature Review 依赖 EvidenceTable
```

---

## 11. 每阶段完成定义

### Phase 0 Done

```text
research_workspace 模块存在
核心模型存在
JSON storage 可用
测试通过
```

### Phase 1 Done

```text
能创建项目
能上传论文
能搜索论文
能列出项目论文
能 include/exclude
```

### Phase 2 Done

```text
能解析论文
能生成 chunks
能生成 PaperCard
能生成 EvidenceRecord
```

### Phase 3 Done

```text
能生成图谱
能选择节点/子图
能解析 RetrievalScope
```

### Phase 4 Done

```text
能基于 Scope QA
回答有范围声明
回答有证据
回答有 suggested_actions
```

### Phase 5 Done

```text
能生成文献综述
能生成创新点报告
报告有 Scope、papers、evidence
```

### Phase 6 Done

```text
前端能完整演示
报告能导出 Markdown
演示项目跑通
```

---

## 12. 最重要的实现顺序建议

如果只能先做一小段，顺序是：

```text
ProjectService
PaperLibraryService
PaperCardGenerator
EvidenceTableService
RetrievalScopeService
ScopeQAService
LiteratureReviewGenerator
InnovationReportGenerator
```

知识图谱初版可以轻量，但 Scope 和 EvidenceTable 必须先打通。

核心验证不是“图谱画得好不好”，而是：

```text
用户选一批论文
系统能基于这批论文回答
系统能基于这批论文生成综述和创新点
```

