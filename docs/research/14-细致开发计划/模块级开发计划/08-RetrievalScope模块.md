# 08-RetrievalScope 模块专项开发计划

更新时间：2026-05-28

## 实现状态

R0 + R1 + R2 部分 R3 完成（2026-05-28）。R4/R5 未开始。

### R0 已完成

```text
R0.1 selected_papers 校验 paper 存在、project_id 匹配、included=True ✅
R0.2 topic_group/method_group/year_range 统一应用 included 过滤 ✅
R0.3 to_evidence_records 禁止 empty scope fallback 全项目 evidence ✅
R0.4 _filter_by_year 校验 paper project_id 和 included ✅
R0.5 graph_hops 限制 0-2 ✅
R0.6 GraphService 使用 GraphService(storage=self.storage) ✅
R0.7 resolve 返回 warnings / empty_reason / suggested_actions ✅
```

### R1 已完成

```text
R1.1 新增 build_scope_guard ✅
R1.2 新增 validate_against_scope ✅
R1.3 resolve 写入 allowed paper/evidence/graph ids ✅
R1.4 QA/Review/Innovation 计划统一调用 ScopeGuard — 待集成
R1.5 增加 scope leak 测试 ✅
```

### R2 部分完成

```text
R2.1 增加 normalize_label ✅
R2.2 topic/method 支持多值拆分 ✅
R2.3 支持同字段 OR、跨字段 AND ✅
R2.4 evidence filters — 未实现
R2.5 增加 explain ✅
```

### R3 部分完成

```text
R3.1 对接 get_subgraph related ids ✅
R3.2 graph_node_ids 校验属于当前 graph — 部分
R3.3 fallback 从 graph node properties 提取 ✅
R3.4 to_graph_context 返回 related ids ✅
R3.5 Gap 节点解析 — 待集成
```

### 新增方法

- `build_scope_guard(scope)` — 构建白名单
- `validate_against_scope(guard, refs)` — 校验引用越界
- `get_scope_filters(project_id)` — 前端可选范围
- `to_paper_cards(scope)` — 获取 scope 内卡片

### RetrievalScope 新增字段

- `metadata` — 包含 `empty_reason`、`warnings`、`suggested_actions`、`invalid_selection`、`explain`

本文档基于 `docs/research` 下的产品方案、当前开发计划、学术 QA/RAG 调研、知识图谱调研、证据表计划、Token 成本分析和当前代码实现，重新细化 Retrieval Scope 模块开发方案。

Retrieval Scope 是研究工作区的边界控制层。它负责把用户在论文库、主题、方法、年份、知识图谱节点或子图上的选择，解析成可验证、可执行、可解释的 `paper_ids`、`evidence_ids`、`graph_node_ids` 和上下文素材白名单。后续 QA、综述、创新点报告都必须先经过 Scope 解析，再在 Scope 内检索、生成和引用。

对应代码：

```text
src/agents_v3/research_workspace/scope.py
src/agents_v3/research_workspace/models.py
tests/agents_v3/research_workspace/test_retrieval_scope.py
```

上游依赖：

```text
papers
paper_cards
evidence_records
graphs / graph_{project_id}
```

下游依赖：

```text
ScopeQAService
LiteratureReviewGenerator
InnovationReportGenerator
ReportService
KnowledgeGraph 页面
```

## 1. 模块定位

### 1.1 在产品链路中的位置

产品主线：

```text
研究项目
  -> 论文库
  -> PDF 解析与分块
  -> 论文卡片
  -> 证据表
  -> 知识图谱
  -> Retrieval Scope
  -> Scope-based QA
  -> 文献综述
  -> 创新点报告
```

Retrieval Scope 处在知识组织层和生成层之间。它回答的问题不是“怎样生成答案”，而是：

```text
本次回答允许使用哪些论文？
本次回答允许引用哪些证据？
这些论文为什么被纳入范围？
哪些选择无效、为空或被过滤？
图谱子图对应哪些 paper_ids 和 evidence_ids？
下游回答是否引用了范围外来源？
当前范围是否过大，需要裁剪上下文？
```

### 1.2 一句话目标

把用户选择转换成可验证、可执行、可解释、可复用的检索范围，并为 QA、综述、创新点和报告导出提供统一边界。

### 1.3 核心原则

```text
1. project_id 是硬边界。
2. included/excluded 是硬过滤。
3. Scope 解析结果必须幂等。
4. 空范围必须有原因和建议动作。
5. 下游生成只能引用 resolved scope 内的 paper/evidence/graph。
6. Scope 既要能限制检索，也要能解释检索范围。
7. Scope 本身不编造事实，只解析已有论文、证据和图谱。
```

## 2. 本地调研结论落地

### 2.1 产品方案落地

`当前产品方案.md` 要求用户可以按以下范围进行 QA 和报告生成：

```text
全项目论文库
选中的论文
主题分组
方法分组
年份范围
知识图谱节点
知识图谱子图
创新点相关论文集合
```

因此 Scope 模块必须提供：

```text
1. 论文选择到 paper_ids。
2. 主题/方法/年份筛选到 paper_ids/evidence_ids。
3. 图谱节点/子图到 related_paper_ids/related_evidence_ids。
4. 当前范围 summary，给用户和报告记录使用。
5. guard 白名单，给 QA、综述、创新点模块做越界校验。
```

### 2.2 当前开发计划落地

`当前开发计划.md` 将知识图谱与 Retrieval Scope 放在 Phase 3，并要求：

```text
能生成图谱节点和边
能查询节点和子图
能解析 RetrievalScope
Scope summary 能清楚说明当前范围
```

本模块的 P0 目标不是做复杂检索，而是先保证：

```text
1. 范围解析准确。
2. 项目边界安全。
3. excluded 论文不进入结果。
4. evidence_ids 与 paper_ids 一致。
5. 下游生成模块可以拿到 ScopeGuard。
```

### 2.3 学术 QA/RAG 调研落地

学术 QA 调研强调：

```text
答案必须有引用来源。
生成后需要引用校验。
检索相关性低、置信度低、文档不足或超出范围时应拒答或说明不确定。
RAG 评估关注 Context Precision、Context Recall、Faithfulness、Answer Relevance。
```

Scope 模块对应提供：

```text
1. allowed_paper_ids / allowed_evidence_ids 白名单。
2. retrieved docs < 2 等空/弱范围诊断。
3. generated citation 是否属于当前范围的校验入口。
4. retrieval_diagnostics 和 scope_diagnostics，支撑 RAG 评估。
```

### 2.4 证据表调研落地

证据表模块计划强调：

```text
EvidenceRecord 是事实层。
证据需要 review_status、evidence_type、source_quote、source_chunk_id。
QA 和报告应优先使用 accepted 或 traceable evidence。
```

Scope 模块需要支持 evidence 级过滤：

```text
evidence_type
review_status
evidence_strength
topic
method
year
source availability
```

当前 `EvidenceRecord` 还没有 `evidence_type`、`review_status` 等字段，因此实现应：

```text
1. 兼容当前字段。
2. 通过 filters 预留扩展字段。
3. 字段不存在时不报错，按默认策略处理。
```

### 2.5 知识图谱调研落地

知识图谱模块计划要求 `get_subgraph` 返回：

```text
nodes
edges
related_paper_ids
related_evidence_ids
related_chunk_ids
summary
warnings
```

Retrieval Scope 对图谱的依赖是：

```text
graph_node_ids / graph_edge_ids
  -> GraphService.get_subgraph()
  -> related_paper_ids / related_evidence_ids
  -> included/project/evidence filters
  -> resolved scope
```

### 2.6 Token 成本调研落地

Token 调研建议使用分层内容：

| 层级 | 内容 | Scope 模块中的作用 |
| --- | --- | --- |
| L0 | 元数据 | 列表、筛选、summary |
| L1 | 摘要 | 大范围概览 |
| L2 | PaperCard | QA、综述、报告生成 |
| L3 | EvidenceTable | 证据型回答、创新点 |
| L4 | 相关 chunks | 深度 QA 和引用定位 |
| L5 | 全文 | 单篇深度分析，默认不进入 |

Scope 模块要提供上下文预算判断：

```text
小范围：直接返回 paper_cards + evidence_records。
中范围：返回 paper_cards + top evidence。
大范围：返回 summary + 分批上下文或交给 RAG 检索。
```

## 3. 当前实现分析

### 3.1 已有能力

当前 `RetrievalScopeService` 已实现：

```text
resolve(project_id, scope_payload)
to_paper_ids(scope)
to_evidence_records(scope)
to_graph_context(scope)
summarize(scope)
_find_papers_by_topics(project_id, topic_ids)
_find_papers_by_methods(project_id, method_ids)
_find_papers_by_graph_nodes(project_id, node_ids, hops)
_find_papers_by_year_range(project_id, time_range)
_filter_by_year(paper_ids, time_range)
_get_evidence_ids(project_id, paper_ids, topic_ids)
```

当前支持的 Scope 类型：

```text
all_project
selected_papers
topic_group
method_group
graph_subgraph
year_range
```

当前优点：

| 能力 | 状态 |
| --- | --- |
| 基础 Scope 类型 | 已支持 |
| all_project included 过滤 | 已支持 |
| 按 topic/method/year 找 paper_ids | 已支持雏形 |
| evidence_ids 解析 | 已支持雏形 |
| graph context | 已支持基础节点/边 |
| summary | 已支持基础描述 |
| storage 注入 | 构造函数已支持 |

### 3.2 当前关键问题

| 问题 | 当前表现 | 影响 | 优先级 |
| --- | --- | --- | --- |
| selected_papers 不校验项目 | 直接使用输入 ID | 可引用其他项目论文 | P0 |
| selected_papers 不过滤 included | excluded paper 可能进入范围 | 用户排除决策失效 | P0 |
| topic/method 不过滤 included | 从 evidence 找 paper_ids 后未验证论文状态 | excluded paper 可进入范围 | P0 |
| year_range 不过滤 included | 查项目论文但不筛 included | excluded paper 可进入范围 | P0 |
| graph_subgraph 新建 GraphService | `GraphService()` 未复用当前 storage | 测试和多存储环境可能读错数据 | P0 |
| graph_hops 无上限 | payload 传多少用多少 | 子图扩散破坏 Scope 边界 | P0 |
| 图谱解析信息少 | 只从 paper 节点提取 paper_ids | 无法利用 related_evidence_ids | P0 |
| 空范围无诊断 | 只返回空列表 | 前端和 QA 不知道原因 | P0 |
| evidence fallback 风险 | `to_evidence_records` 在 evidence_ids 为空时回退全项目 | 空 Scope 可能变成全项目 evidence | P0 |
| topic/method 精确匹配 | 直接 `e.get("topic") in topic_ids` | 大小写、逗号多值、别名无法匹配 | P1 |
| 组合过滤弱 | 仅部分支持 time_range | 不支持 topic + method + year 交集 | P1 |
| ScopeGuard 缺失 | 无 allowed ids 校验器 | QA/报告无法证明不越界 | P0 |
| explain 缺失 | 不记录论文纳入原因 | 用户无法理解范围 | P1 |
| 保存 Scope 缺失 | 常用范围不能复用 | 前端体验弱 | P2 |

## 4. 主流做法与借鉴

| 来源 | 做法 | 本项目落地 |
| --- | --- | --- |
| RAG metadata filter | 检索前用 metadata 限定 corpus | Scope 先解析，再检索，不允许先全库检索后过滤 |
| LangChain/LlamaIndex Retriever | retriever 接收 filters/top_k | Scope 输出标准 filters 和 allowed ids |
| GraphRAG | local search 从实体子图开始，global search 从社区摘要开始 | graph_subgraph scope 输出 related ids 和 graph context |
| Rayyan/Covidence | 文献筛选围绕 include/exclude、标签、理由 | included/excluded 是硬过滤，invalid_selection 要记录 |
| Notion/数据库视图 | 过滤、分组、排序可保存为视图 | P2 保存常用 Scope / Scope View |
| 学术 QA 系统 | 生成后做引用校验 | ScopeGuard 校验 paper/evidence/graph 是否越界 |

本项目的三层 Scope 设计：

```text
ScopePayload
  用户或前端传入的原始选择。

ResolvedScope
  解析后的 paper_ids、evidence_ids、graph ids、summary、empty_reason、explain。

ScopeGuard
  下游生成和报告保存前使用的白名单校验器。
```

## 5. 目标架构

### 5.1 服务职责拆分

当前可以继续放在 `scope.py`，但职责上应拆成这些组件：

```text
RetrievalScopeService
  对外门面，负责 resolve/to_context/summarize。

ScopeResolver
  按 all_project/selected/topic/method/graph/year 解析基础范围。

ScopeFilterEngine
  处理 included、year、topic、method、evidence_type、review_status、strength 过滤。

ScopeGuard
  校验下游引用是否越界。

ScopeExplainer
  记录每篇论文、每条证据为什么被纳入。

ScopeContextBuilder
  将 resolved scope 转成 evidence/cards/graph/context budget。
```

P0 不一定拆文件，但 `scope.py` 内部应按这些职责组织，避免继续堆逻辑。

### 5.2 解析数据流

```text
scope_payload
  |
  v
normalize payload
  |
  v
load project papers + included paper index
  |
  v
resolve base scope
  |
  v
apply filters as intersection
  |
  v
resolve evidence ids
  |
  v
resolve graph context
  |
  v
build explain + diagnostics + summary
  |
  v
ResolvedScope + ScopeGuard
```

### 5.3 对外方法

建议 `RetrievalScopeService` 保留并扩展：

```python
class RetrievalScopeService:
    def resolve(self, project_id: str, scope_payload: dict[str, Any]) -> RetrievalScope: ...
    def build_scope_guard(self, scope: RetrievalScope) -> dict[str, Any]: ...
    def validate_against_scope(self, scope: RetrievalScope, refs: dict[str, list[str]]) -> dict[str, Any]: ...
    def to_paper_ids(self, scope: RetrievalScope) -> list[str]: ...
    def to_evidence_records(self, scope: RetrievalScope) -> list[EvidenceRecord]: ...
    def to_paper_cards(self, scope: RetrievalScope) -> list[dict[str, Any]]: ...
    def to_graph_context(self, scope: RetrievalScope, hops: int | None = None) -> dict[str, Any]: ...
    def get_scope_filters(self, project_id: str) -> dict[str, Any]: ...
    def summarize(self, scope: RetrievalScope) -> str: ...
```

## 6. 数据模型设计

### 6.1 当前 RetrievalScope 基线

当前模型已有：

```text
scope_type
project_id
paper_ids
evidence_ids
graph_node_ids
graph_edge_ids
topic_ids
method_ids
time_range
summary
```

### 6.2 RetrievalScope 建议增强

P0 可先通过 `metadata` 或 dict 返回扩展字段；P1 再正式改模型。

建议字段：

```text
scope_id
scope_type
project_id
paper_ids
evidence_ids
graph_node_ids
graph_edge_ids
topic_ids
method_ids
time_range
filters
resolved
empty_reason
invalid_selection
warnings
suggested_actions
explain
context_budget
created_at
updated_at
```

### 6.3 ScopePayload 输入规范

统一前端输入：

```json
{
  "type": "graph_subgraph",
  "selected_paper_ids": [],
  "selected_topic_ids": [],
  "selected_method_ids": [],
  "selected_graph_node_ids": [],
  "selected_graph_edge_ids": [],
  "selected_evidence_ids": [],
  "graph_hops": 1,
  "include_neighbors": true,
  "time_range": ["2021", "2026"],
  "filters": {
    "evidence_type": ["finding", "limitation"],
    "review_status": ["accepted", "pending"],
    "evidence_strength": ["high", "medium"],
    "has_source_quote": true
  },
  "options": {
    "allow_empty": false,
    "max_papers": 80,
    "max_evidence": 200
  }
}
```

### 6.4 ResolvedScope 输出规范

```json
{
  "scope_id": "scope_xxx",
  "project_id": "proj_001",
  "scope_type": "graph_subgraph",
  "paper_ids": ["p1", "p2"],
  "evidence_ids": ["ev1", "ev2"],
  "graph_node_ids": ["topic:abc"],
  "graph_edge_ids": ["edge:xyz"],
  "topic_ids": [],
  "method_ids": [],
  "time_range": ["2021", "2026"],
  "summary": "当前范围：图谱子图，包含 2 篇论文、2 条证据",
  "empty_reason": "",
  "warnings": [],
  "suggested_actions": [],
  "explain": {}
}
```

### 6.5 ScopeGuard

建议用 dict 或 Pydantic 模型：

```python
class ScopeGuard(BaseModel):
    project_id: str
    scope_id: str = ""
    allowed_paper_ids: set[str] = Field(default_factory=set)
    allowed_evidence_ids: set[str] = Field(default_factory=set)
    allowed_graph_node_ids: set[str] = Field(default_factory=set)
    allowed_graph_edge_ids: set[str] = Field(default_factory=set)
    allow_empty: bool = False
```

校验方法：

```text
validate_papers(paper_ids)
validate_evidence(evidence_ids)
validate_graph_nodes(node_ids)
validate_graph_edges(edge_ids)
filter_to_scope(items)
validate_response_references(response)
```

返回：

```json
{
  "valid": false,
  "violations": [
    {"type": "paper_out_of_scope", "id": "p99"},
    {"type": "evidence_out_of_scope", "id": "ev99"}
  ],
  "filtered_refs": {
    "paper_ids": ["p1"],
    "evidence_ids": ["ev1"]
  }
}
```

## 7. Scope 类型解析规则

### 7.1 all_project

规则：

```text
1. 查询 project_id 下 papers。
2. 只保留 included=True 的论文。
3. 应用 time_range、topic、method、evidence filters。
4. 如果没有 included 论文，empty_reason=no_included_papers。
```

验收：

```text
excluded 论文永远不进入 all_project。
```

### 7.2 selected_papers

规则：

```text
1. 输入 paper_ids 去重并保持稳定排序。
2. 每个 paper_id 必须存在。
3. 每个 paper_id 必须属于 project_id。
4. 每个 paper_id 必须 included=True。
5. 无效 ID 进入 invalid_selection。
6. 全部被过滤时 empty_reason=no_valid_selected_papers。
```

invalid_selection 示例：

```json
[
  {"id": "p99", "reason": "not_found"},
  {"id": "p_other", "reason": "project_mismatch"},
  {"id": "p3", "reason": "excluded"}
]
```

### 7.3 topic_group

规则：

```text
1. topic_ids 先 normalize。
2. 优先从知识图谱 Topic 节点解析 related paper/evidence。
3. 如果图谱不存在，fallback 到 evidence_records.topic。
4. 支持 evidence.topic 逗号、分号、顿号多值拆分。
5. 再应用 included、method、year、evidence filters。
6. explain 记录每篇论文命中的 topic 和 evidence_ids。
```

### 7.4 method_group

规则：

```text
1. method_ids 先 normalize。
2. 优先从知识图谱 Method 节点解析。
3. fallback 到 evidence_records.method。
4. 支持多方法拆分和大小写归一化。
5. 再应用 included、topic、year、evidence filters。
```

### 7.5 graph_subgraph

规则：

```text
1. graph_node_ids / graph_edge_ids 必须属于当前 project graph。
2. graph_hops 默认 1，最大 2。
3. include_neighbors=false 时 hops=0。
4. 必须复用 RetrievalScopeService 注入的 storage 创建 GraphService(storage=self.storage)。
5. 优先读取 GraphService.get_subgraph 的 related_paper_ids / related_evidence_ids。
6. 如果旧 GraphService 未返回 related ids，则 fallback 从 Paper 节点和 properties.paper_ids/evidence_ids 提取。
7. 再应用 included 和 evidence filters。
```

graph_hops 规则：

```text
payload graph_hops < 0 -> 0
payload graph_hops missing -> 1
payload graph_hops > 2 -> 2，并写入 warning
```

### 7.6 year_range

规则：

```text
1. time_range 必须能解析为两个年份。
2. start_year > end_year 时固定策略：自动交换，并写 warning。
3. 年份非法时 empty_reason=invalid_time_range。
4. 只查询 project_id 下 included=True 论文。
5. 缺失 year 的论文默认不进入 year_range。
```

### 7.7 selected_evidence

当前 `ScopeType` 还没有 selected_evidence。P1 可新增。

临时方案：

```text
scope_payload.selected_evidence_ids 可作为 filters 的一部分。
resolve 后先校验 evidence project_id，再反推出 paper_ids。
```

### 7.8 innovation_related

产品方案中提到“创新点相关论文集合”，P2 支持。

来源：

```text
InnovationPoint.supporting_papers
InnovationPoint.limiting_evidence
Gap.supporting_paper_ids
Gap.supporting_evidence_ids
```

## 8. 组合过滤规则

### 8.1 总体策略

Scope 解析采用“基础范围 + 交集过滤”：

```text
project boundary
  -> included filter
  -> base scope
  -> topic/method/year filters
  -> evidence filters
  -> graph filters
  -> max limits / context budget
```

基础范围由 `type` 决定：

```text
all_project
selected_papers
topic_group
method_group
graph_subgraph
year_range
```

其他条件作为交集过滤。

### 8.2 示例

用户选择：

```json
{
  "type": "topic_group",
  "selected_topic_ids": ["llm feedback"],
  "selected_method_ids": ["quasi experiment"],
  "time_range": ["2022", "2026"]
}
```

解析含义：

```text
项目内 included 论文
且属于 llm feedback 主题
且使用 quasi experiment 方法
且年份在 2022-2026
```

### 8.3 OR 与 AND

MVP 规则：

```text
同一字段内部是 OR：
  topic in [A, B]

不同字段之间是 AND：
  topic in [A, B] AND method in [M] AND year in range
```

P2 可扩展高级布尔表达式，但 MVP 不做。

## 9. Evidence 解析规则

### 9.1 基本规则

`scope.evidence_ids` 必须严格来自：

```text
project_id 匹配
paper_id in scope.paper_ids
通过 evidence filters
未被 review_status=rejected 排除
```

注意：如果 `scope.paper_ids` 为空且 `empty_reason` 非空，不能 fallback 到全项目 evidence。

### 9.2 Evidence filters

建议支持：

```text
topic
method
evidence_type
review_status
evidence_strength
has_source_quote
has_source_chunk
keyword
```

当前模型没有部分字段时：

```text
不存在 evidence_type -> 从 finding/limitation/future_work 等字段推断。
不存在 review_status -> 默认 pending。
不存在 claim -> 从 finding/limitation/future_work 等字段取文本。
```

### 9.3 Evidence type 推断

兼容当前字段：

```text
finding 非空 -> finding
limitation 非空 -> limitation
future_work 非空 -> future_work
method 非空 -> method
data_or_sample 非空 -> dataset
```

如果一条 EvidenceRecord 同时有多个字段，P0 可以保留整条记录，P1 应在证据表模块拆分为多条 evidence。

## 10. 空范围处理

### 10.1 empty_reason

必须明确原因：

```text
no_included_papers
no_valid_selected_papers
no_matching_topic
no_matching_method
no_matching_graph_nodes
no_matching_graph_subgraph
invalid_time_range
no_papers_after_year_filter
no_evidence_after_filters
graph_not_built
all_selected_papers_excluded
```

### 10.2 suggested_actions

示例：

```text
扩大年份范围。
清除方法筛选。
先构建知识图谱。
选择至少一篇 included 论文。
将被排除论文重新纳入后再分析。
改用全项目范围。
```

### 10.3 下游行为

```text
QA：空范围直接拒答，并展示 empty_reason。
综述：空范围不能生成报告。
创新点：空范围不能生成创新点。
前端：显示空状态和 suggested_actions。
```

## 11. Scope Explain

### 11.1 explain 输出

```json
{
  "papers": {
    "p1": {
      "included_by": ["topic:llm feedback", "year:2024"],
      "matched_evidence_ids": ["ev1", "ev2"],
      "matched_graph_node_ids": ["topic:abc"],
      "warnings": []
    }
  },
  "evidence": {
    "ev1": {
      "included_by": ["paper:p1", "topic:llm feedback"],
      "source_quote_available": true
    }
  }
}
```

### 11.2 用途

```text
1. 前端展示“为什么这些论文在范围内”。
2. QA 证据不足时提示具体缺口。
3. 测试验证 selected/topic/method/year 的交集逻辑。
4. 报告导出时记录范围来源。
```

## 12. Scope Context 构建

### 12.1 to_evidence_records

要求：

```text
1. 只返回 scope.evidence_ids 内的记录。
2. 如果 scope.evidence_ids 为空且 empty_reason 非空，返回空。
3. 禁止空 Scope fallback 到全项目 evidence。
4. 返回顺序稳定：paper_id、evidence_strength、evidence_id。
```

### 12.2 to_paper_cards

新增：

```python
to_paper_cards(scope: RetrievalScope) -> list[dict[str, Any]]
```

规则：

```text
1. 只返回 scope.paper_ids 内的 paper_cards。
2. 大范围时可限制 max_cards。
3. 默认按年份、标题或输入选择顺序稳定排序。
```

### 12.3 to_graph_context

要求：

```text
1. graph_subgraph 优先调用 GraphService.get_subgraph。
2. 非 graph scope 可按 paper_ids 返回相关 Paper 节点、Topic/Method/Gap 邻居。
3. 返回 related_paper_ids 和 related_evidence_ids。
4. 不返回 scope 外节点作为可引用证据。
```

输出：

```json
{
  "nodes": [],
  "edges": [],
  "related_paper_ids": [],
  "related_evidence_ids": [],
  "warnings": [],
  "summary": ""
}
```

### 12.4 context_budget

Scope 解析后给出预算建议：

```json
{
  "paper_count": 30,
  "evidence_count": 120,
  "estimated_card_tokens": 21000,
  "estimated_evidence_tokens": 60000,
  "recommended_strategy": "rag_top_k",
  "max_evidence_for_prompt": 30
}
```

策略：

```text
paper_count <= 10：可直接使用 card + evidence。
paper_count <= 50：使用 card + top evidence。
paper_count > 50：使用 RAG 检索、分批或摘要。
```

## 13. ScopeGuard 设计

### 13.1 构建

```python
build_scope_guard(scope: RetrievalScope) -> dict[str, Any]
```

输出：

```json
{
  "project_id": "proj_001",
  "scope_id": "scope_xxx",
  "allowed_paper_ids": ["p1", "p2"],
  "allowed_evidence_ids": ["ev1", "ev2"],
  "allowed_graph_node_ids": ["topic:abc"],
  "allowed_graph_edge_ids": ["edge:xyz"],
  "allow_empty": false
}
```

### 13.2 下游校验点

ScopeQA：

```text
LLM 输出 supporting_papers 必须属于 allowed_paper_ids。
LLM 输出 evidence_records 必须属于 allowed_evidence_ids。
graph_paths 里的节点和边必须属于当前 graph context。
```

LiteratureReview：

```text
报告引用论文必须属于 allowed_paper_ids。
报告 evidence_ids 必须属于 allowed_evidence_ids。
参考文献列表不能包含 scope 外论文。
```

InnovationReport：

```text
创新点 supporting_papers 和 limiting_evidence 必须在 scope 内。
Gap 节点来源 evidence 必须在 scope 内，或者标注“来自 scope 外，未纳入本次结论”。
```

### 13.3 校验返回

```json
{
  "valid": false,
  "scope_leak_count": 2,
  "violations": [
    {"kind": "paper", "id": "p99", "reason": "out_of_scope"},
    {"kind": "evidence", "id": "ev99", "reason": "out_of_scope"}
  ],
  "action": "remove_invalid_references"
}
```

## 14. get_scope_filters

### 14.1 目标

前端需要知道当前项目可选范围：

```python
get_scope_filters(project_id: str) -> dict[str, Any]
```

### 14.2 返回结构

```json
{
  "papers": [
    {"id": "p1", "title": "Paper A", "year": 2024, "included": true}
  ],
  "topics": [
    {"id": "topic:abc", "label": "LLM feedback", "paper_count": 12, "evidence_count": 30}
  ],
  "methods": [
    {"id": "method:def", "label": "quasi experiment", "paper_count": 5}
  ],
  "years": [
    {"year": 2024, "paper_count": 8}
  ],
  "graph_nodes": [
    {"id": "gap:xyz", "label": "lack of longitudinal evidence", "type": "Gap", "paper_count": 4}
  ],
  "evidence_types": [
    {"id": "finding", "label": "Finding", "evidence_count": 40}
  ],
  "review_statuses": [
    {"id": "accepted", "label": "Accepted", "evidence_count": 20}
  ]
}
```

### 14.3 统计规则

```text
只统计 project_id 内 included=True 的论文。
topic/method 优先来自 graph，fallback 到 evidence_records。
计数要基于过滤后的 included paper。
```

## 15. API 计划

### 15.1 Scope 解析

```text
POST /api/rw/projects/{project_id}/scope/resolve
POST /api/rw/projects/{project_id}/scope/guard/validate
GET  /api/rw/projects/{project_id}/scope/filters
```

### 15.2 Scope 上下文

```text
POST /api/rw/projects/{project_id}/scope/context/evidence
POST /api/rw/projects/{project_id}/scope/context/cards
POST /api/rw/projects/{project_id}/scope/context/graph
POST /api/rw/projects/{project_id}/scope/context/estimate
```

### 15.3 保存范围

P2：

```text
POST /api/rw/projects/{project_id}/scopes
GET  /api/rw/projects/{project_id}/scopes
GET  /api/rw/projects/{project_id}/scopes/{scope_id}
PUT  /api/rw/projects/{project_id}/scopes/{scope_id}
DELETE /api/rw/projects/{project_id}/scopes/{scope_id}
```

## 16. 前端交互契约

### 16.1 范围选择器

前端应支持：

```text
论文多选
主题筛选
方法筛选
年份范围
知识图谱节点/子图选择
证据状态/强度筛选
当前范围预览
```

### 16.2 范围预览

Scope resolve 后展示：

```text
论文数量
证据数量
图谱节点数量
主要主题
主要方法
年份跨度
空范围原因
建议动作
```

### 16.3 交互要求

```text
1. 用户在 QA、综述、创新点页面看到同一套范围摘要。
2. 空范围时禁用生成按钮。
3. 选择图谱节点后可以预览相关论文和证据。
4. 被排除论文不应出现在默认可选列表中，除非用户开启“显示 excluded”。
5. 每个范围可展示 explain，说明纳入原因。
```

## 17. 日志与诊断

结合日志调研，Scope 解析应记录结构化日志。

事件：

```text
scope.resolve.started
scope.resolve.completed
scope.resolve.empty
scope.resolve.warning
scope.guard.violation
scope.context.built
```

字段：

```json
{
  "event": "scope.resolve.completed",
  "project_id": "proj_001",
  "scope_type": "topic_group",
  "paper_count": 12,
  "evidence_count": 45,
  "graph_node_count": 0,
  "empty_reason": "",
  "duration_ms": 42,
  "warnings_count": 1
}
```

质量指标：

```text
scope_resolve_latency_ms
scope_empty_rate
scope_invalid_selection_count
scope_leak_count
scope_guard_violation_rate
avg_papers_per_scope
avg_evidence_per_scope
```

## 18. 开发阶段

### R0：修复边界安全

目标：让当前 Scope 不会越项目、不会引用 excluded 论文、不会空范围 fallback 全项目。

任务：

```text
R0.1 selected_papers 校验 paper 存在、project_id 匹配、included=True。
R0.2 topic_group/method_group/year_range 统一应用 included 过滤。
R0.3 to_evidence_records 禁止 empty scope fallback 全项目 evidence。
R0.4 _filter_by_year 校验 paper project_id 和 included。
R0.5 graph_hops 限制 0-2。
R0.6 GraphService 使用 GraphService(storage=self.storage)。
R0.7 resolve 返回 warnings / empty_reason / suggested_actions。
```

验收：

```text
其他项目论文不能进入 selected scope。
excluded 论文不能进入任何默认 scope。
空范围不会返回全项目 evidence。
graph_hops > 2 会被截断并记录 warning。
```

### R1：ResolvedScope 与 ScopeGuard

目标：形成下游统一白名单。

任务：

```text
R1.1 新增 build_scope_guard。
R1.2 新增 validate_against_scope。
R1.3 resolve 写入 allowed paper/evidence/graph ids。
R1.4 QA/Review/Innovation 计划统一调用 ScopeGuard。
R1.5 增加 scope leak 测试。
```

验收：

```text
ScopeGuard 能拦截范围外 paper_id。
ScopeGuard 能拦截范围外 evidence_id。
ScopeGuard 校验结果可被 QAResponse/report 记录。
```

### R2：组合过滤与归一化

目标：支持 topic + method + year + evidence filters 的交集。

任务：

```text
R2.1 增加 normalize_label。
R2.2 topic/method 支持多值拆分。
R2.3 支持同字段 OR、跨字段 AND。
R2.4 evidence filters 支持 strength、review_status、evidence_type、has_source_quote。
R2.5 增加 explain。
```

验收：

```text
topic+method+year 返回交集。
大小写不同的 topic/method 可匹配。
explain 能说明 paper/evidence 纳入原因。
```

### R3：图谱子图 Scope

目标：让图谱节点/子图稳定解析为 paper/evidence 范围。

任务：

```text
R3.1 对接 07 知识图谱模块 get_subgraph related ids。
R3.2 graph_node_ids / graph_edge_ids 校验属于当前 graph。
R3.3 fallback 从 graph node/edge properties 提取 paper_ids/evidence_ids。
R3.4 to_graph_context 返回 related_paper_ids/related_evidence_ids。
R3.5 支持 Gap 节点解析 supporting evidence。
```

验收：

```text
选择 Topic 节点可解析相关论文和证据。
选择 Gap 节点可解析 supporting evidence。
图谱子图不会泄漏 scope 外 evidence。
```

### R4：前端筛选与上下文预算

目标：支持前端范围选择器和生成前预估。

任务：

```text
R4.1 get_scope_filters。
R4.2 context_budget 估算。
R4.3 to_paper_cards。
R4.4 scope preview payload。
R4.5 大范围建议 RAG top-k 或分批。
```

验收：

```text
前端能展示主题、方法、年份、图谱节点候选。
用户选择范围后能预览 paper/evidence 数量。
大范围能给出 context 策略建议。
```

### R5：保存 Scope 与高级范围

目标：提升研究工作流复用能力。

任务：

```text
R5.1 保存常用 Scope。
R5.2 Scope View 命名、描述、更新时间。
R5.3 Scope 对比。
R5.4 innovation/gap related scope。
R5.5 高级布尔过滤表达式。
```

验收：

```text
用户可以保存“实证研究主题 + 2022-2026 + high evidence”的范围。
报告记录 scope_id 后可复现生成范围。
```

## 19. 测试计划

### 19.1 测试文件

```text
tests/agents_v3/research_workspace/test_retrieval_scope.py
tests/agents_v3/research_workspace/test_scope_project_boundary.py
tests/agents_v3/research_workspace/test_scope_included_filter.py
tests/agents_v3/research_workspace/test_scope_empty.py
tests/agents_v3/research_workspace/test_scope_guard.py
tests/agents_v3/research_workspace/test_scope_filters.py
tests/agents_v3/research_workspace/test_scope_graph_context.py
tests/agents_v3/research_workspace/test_scope_explain.py
tests/agents_v3/research_workspace/test_scope_context_budget.py
```

### 19.2 关键测试

项目边界：

```text
selected_papers 包含其他项目论文时被过滤并记录 invalid_selection。
topic/method/year 不返回其他项目论文。
evidence_ids 不包含其他项目 evidence。
```

included/excluded：

```text
all_project 不包含 excluded。
selected_papers 选择 excluded 时被过滤。
topic/method/year 匹配到 excluded 论文时仍过滤。
```

空范围：

```text
空项目返回 no_included_papers。
无匹配 topic 返回 no_matching_topic。
非法年份返回 invalid_time_range。
空范围 to_evidence_records 返回空，不 fallback 全项目。
```

组合过滤：

```text
topic + method + year 返回交集。
同字段多选为 OR。
跨字段多选为 AND。
```

图谱：

```text
graph_hops > 2 被截断。
GraphService 使用同一个 storage。
graph_subgraph 返回 related_paper_ids/evidence_ids。
无图谱时返回 graph_not_built。
```

ScopeGuard：

```text
范围外 paper_id 被拦截。
范围外 evidence_id 被拦截。
QAResponse 中越界引用会生成 validation warning。
```

前端筛选：

```text
get_scope_filters 只统计 included 论文。
topics/methods/years 计数正确。
```

## 20. 验收标准

P0/R0-R1 完成后：

```text
1. all_project、selected_papers、topic_group、method_group、graph_subgraph、year_range 都能解析。
2. 任何 Scope 都不会返回其他项目论文。
3. 任何默认 Scope 都不会返回 excluded 论文。
4. 空范围有 empty_reason 和 suggested_actions。
5. to_evidence_records 不会在空范围 fallback 全项目。
6. ScopeGuard 能校验 paper_ids/evidence_ids 是否越界。
7. graph_hops 默认 1，最大 2。
```

P1/R2-R4 完成后：

```text
1. 支持 topic + method + year + evidence filters 组合过滤。
2. 支持 Scope explain。
3. 支持 get_scope_filters 给前端使用。
4. graph_subgraph 能解析 related_paper_ids/related_evidence_ids。
5. Scope context 能给 QA/RAG 提供 token budget 建议。
```

P2/R5 完成后：

```text
1. 支持保存常用 Scope。
2. 报告可以通过 scope_id 复现生成范围。
3. 支持创新点/gap 相关 Scope。
4. 支持高级范围对比和模板。
```

## 21. 最小实现顺序

推荐顺序：

```text
1. 修 selected_papers 项目边界和 included 过滤。
2. 修 topic/method/year 的 included 过滤。
3. 修空范围和 to_evidence_records fallback。
4. 加 graph_hops 限制和 GraphService storage 注入。
5. 加 build_scope_guard。
6. 加 validate_against_scope。
7. 加组合过滤。
8. 加 explain。
9. 加 get_scope_filters。
10. 加 context_budget 和 to_paper_cards。
```

不要优先做：

```text
复杂布尔查询语言
多人协作 Scope 权限
保存视图的复杂 UI
向量检索本身
报告生成优化
```

这些能力依赖基础边界控制，优先级低于 P0 安全闭环。

## 22. 风险与应对

| 风险 | 表现 | 应对 |
| --- | --- | --- |
| 越项目引用 | selected_papers 直接信任前端 ID | 后端强制校验 project_id |
| excluded 失效 | topic/method/year 从 evidence 反推论文 | 所有入口统一 included filter |
| 空范围误用 | evidence_ids 为空时 fallback 全项目 | empty_reason 存在时禁止 fallback |
| 图谱扩散 | hops 太大导致全项目进入 scope | hops 最大 2，并返回 warning |
| 图谱存储不一致 | graph_{project_id} 与 graphs 并存 | GraphService 统一读取，Scope 只调用门面 |
| 前端筛选不一致 | 页面自己统计 options | get_scope_filters 后端统一输出 |
| 生成越界 | LLM 输出范围外引用 | ScopeGuard 后校验 |
| 上下文过大 | 大范围直接塞入所有证据 | context_budget + RAG top-k |

## 23. 参考文档

本地调研：

```text
docs/research/11-产品方案与开发/当前产品方案.md
docs/research/11-产品方案与开发/当前开发计划.md
docs/research/14-细致开发计划/模块级开发计划/06-证据表模块.md
docs/research/14-细致开发计划/模块级开发计划/07-知识图谱模块.md
docs/research/14-细致开发计划/模块级开发计划/09-ScopeQA与RAG模块.md
docs/research/10-学术QA系统/智能问答Agent学术QA综合调研报告.md
docs/research/10-知识图谱/RAG与知识图谱检索评估标准调研报告.md
docs/research/12-优化方案/文献综述Token消耗与上下文容量分析报告.md
docs/research/08-日志与监控/日志系统调研报告.md
```

外部参考：

```text
RAGAS Metrics:
https://docs.ragas.io/

Microsoft GraphRAG Query:
https://microsoft.github.io/graphrag/query/overview/

Rayyan:
https://help.rayyan.ai/

Covidence:
https://support.covidence.org/help
```
