# 08-RetrievalScope 模块专项开发计划

更新时间：2026-06-01

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
R1.4 QA/Review/Innovation 统一调用 ScopeGuard ✅（已集成：scope_qa.py、review_generator.py、innovation_generator.py 均在生成后调用 validate_against_scope）
R1.5 增加 scope leak 测试 ✅
```

### R2 部分完成

```text
R2.1 增加 normalize_label ✅
R2.2 topic/method 支持多值拆分 ✅（_split_multi 支持逗号/分号/顿号/斜杠）
R2.3 支持同字段 OR、跨字段 AND ✅
R2.4 evidence filters — ❌ 未实现（EvidenceRecord 缺少 evidence_type/review_status 字段）
R2.5 增加 explain ✅
```

### R3 部分完成

```text
R3.1 对接 get_subgraph related ids ✅
R3.2 graph_node_ids 校验属于当前 graph — ⚠️ 部分（node IDs 未校验归属当前 project graph）
R3.3 fallback 从 graph node properties 提取 ✅
R3.4 to_graph_context 返回 related ids ✅
R3.5 Gap 节点解析 — ❌ 待实现（_find_papers_by_graph_nodes 未处理 Gap.supporting_evidence_ids）
```

### 当前代码规模

```text
scope.py                              ~580 行  RetrievalScopeService（9 个公共方法 + 12 个内部方法）
models.py                             740 行  RetrievalScope / ScopeType / ScopeGuard 相关模型
test_retrieval_scope.py               ~300 行  1 个测试类、22 个测试方法
api/app.py                            路由：POST scope/resolve + GET scope/filters
api/models.py                         ScopeResolveRequest DTO
api/deps.py                           get_scope_service() 依赖注入
```

### 新增方法

- `build_scope_guard(scope)` — 构建白名单
- `validate_against_scope(guard, refs)` — 校验引用越界
- `get_scope_filters(project_id)` — 前端可选范围
- `to_paper_cards(scope)` — 获取 scope 内卡片

### RetrievalScope 新增字段

- `metadata` — 包含 `empty_reason`、`warnings`、`suggested_actions`、`invalid_selection`、`explain`

### 当前已知缺陷

| 缺陷 | 影响 | 修复优先级 |
| --- | --- | --- |
| R2.4 evidence filters 未实现 | 无法按 evidence_type/review_status/strength 过滤证据 | P1（依赖 EvidenceRecord 模型扩展） |
| R3.2 graph_node_ids 未校验归属 | 用户传入其他项目的 node_id 可能泄漏数据 | P1 |
| R3.5 Gap 节点 supporting_evidence 未解析 | 选择 Gap 节点时丢失支撑证据 | P1 |
| 无 scope_id | 报告 scope 快照无法精确复现 | P1 |
| context_budget 未实现 | 大范围无 token 预估，QA/综述可能超上下文窗口 | P1 |
| 无 method_group 图谱优先查找 | method_group 只从 evidence 查，不走图谱 Method 节点 | P1 |
| 测试覆盖不足 | 22 个测试缺 method_group、graph_subgraph 实际数据、to_graph_context、evidence violation | P1 |
| ScopeResolveRequest 缺 filters/options 字段 | API 层无法传入 evidence filters 和 max_papers/max_evidence | P1 |

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

Retrieval Scope 处在知识组织层和生成层之间。它回答的问题不是"怎样生成答案"，而是：

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
resolve(project_id, scope_payload)           # 主入口，按 scope_type 分派
to_paper_ids(scope)                          # 直接返回 scope.paper_ids
to_evidence_records(scope)                   # 获取 scope 内证据，禁止空范围 fallback
to_paper_cards(scope, max_cards=50)          # 获取 scope 内 active 卡片
to_graph_context(scope, hops=1)              # 获取图谱上下文
build_scope_guard(scope)                     # 构建 allowed IDs 白名单
validate_against_scope(guard, refs)          # 校验引用越界
get_scope_filters(project_id)                # 前端可选范围
summarize(scope)                             # 生成中文摘要
```

内部方法：

```text
_validate_selected_papers(paper_ids, project_id)    # 校验存在/归属/included
_find_papers_by_topics(project_id, topic_ids)       # 图谱优先→evidence fallback
_find_papers_from_graph_topics(graph, topic_ids)    # 从图谱 Topic 节点匹配
_find_papers_by_methods(project_id, method_ids)     # evidence 方法匹配
_find_papers_by_graph_nodes(project_id, node_ids, hops)  # GraphService.get_subgraph
_find_papers_by_year_range(project_id, time_range)  # 按 paper.dates.year 过滤
_filter_papers_by_topics(paper_ids, topic_ids, project_id)  # 交集过滤
_filter_papers_by_methods(paper_ids, method_ids, project_id)  # 交集过滤
_filter_by_year(paper_ids, time_range, project_id)  # 交集过滤
_get_evidence_ids(project_id, paper_ids)            # 收集 evidence IDs
_clamp_hops(hops, warnings)                         # 限制 0-2
_explain_paper_inclusion(paper, scope, graph_context)  # 构建纳入原因
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
| 基础 Scope 类型 | 6 种全部支持 |
| all_project included 过滤 | 已支持 |
| 按 topic/method/year 找 paper_ids | 已支持（topic 图谱优先） |
| evidence_ids 解析 | 已支持 |
| graph context | 已支持（GraphService.get_subgraph） |
| summary | 已支持中文摘要 |
| storage 注入 | 构造函数已支持 |
| ScopeGuard | 已支持（build + validate） |
| explain | 已支持（papers 级纳入原因） |
| normalize_label | 已支持（大小写/下划线/连字符归一化） |
| _split_multi | 已支持（逗号/分号/顿号/斜杠多值拆分） |
| 跨字段 AND 过滤 | 已支持（topic + method + year 交集） |

### 3.2 当前关键问题

| 问题 | 当前表现 | 影响 | 优先级 |
| --- | --- | --- | --- |
| evidence filters 未实现 | 无法按 evidence_type/review_status/strength 过滤 | 无法筛选高质量证据给 QA/综述 | P1（依赖 EvidenceRecord 扩展） |
| graph_node_ids 未校验归属 | 直接使用输入 node_ids，不校验是否属于当前 project graph | 可引用其他项目图谱节点 | P1 |
| Gap 节点 supporting_evidence 未解析 | `_find_papers_by_graph_nodes` 不区分节点类型 | Gap 节点丢失支撑证据 | P1 |
| 无 scope_id | 报告 scope 快照是 dict，无唯一标识 | 无法精确复现生成范围 | P1 |
| context_budget 未实现 | 无 token 预估和策略建议 | 大范围可能超 LLM 上下文窗口 | P1 |
| method_group 不走图谱 | `_find_papers_by_methods` 只查 evidence | 图谱中 Method 节点的 related papers 被忽略 | P1 |
| ScopeResolveRequest 缺 filters/options | API DTO 只有 type/ids/hops/time_range | 前端无法传入 evidence filters 和 max 限制 | P1 |
| 测试覆盖不足 | 22 个测试缺多个场景 | method_group、graph_subgraph 实际数据、to_graph_context、evidence violation 无覆盖 | P1 |

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
metadata          # 包含 empty_reason/warnings/suggested_actions/invalid_selection/explain
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
2. 优先从知识图谱 Method 节点解析。    ← 当前未实现，只走 evidence
3. fallback 到 evidence_records.method。
4. 支持多方法拆分和大小写归一化。
5. 再应用 included、topic、year、evidence filters。
```

### 7.5 graph_subgraph

规则：

```text
1. graph_node_ids / graph_edge_ids 必须属于当前 project graph。    ← 当前未校验
2. graph_hops 默认 1，最大 2。
3. include_neighbors=false 时 hops=0。
4. 必须复用 RetrievalScopeService 注入的 storage 创建 GraphService(storage=self.storage)。
5. 优先读取 GraphService.get_subgraph 的 related_paper_ids / related_evidence_ids。
6. 如果旧 GraphService 未返回 related ids，则 fallback 从 Paper 节点和 properties.paper_ids/evidence_ids 提取。
7. 再应用 included 和 evidence filters。
8. Gap 节点需解析 supporting_evidence_ids。    ← 当前未实现
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

产品方案中提到"创新点相关论文集合"，P2 支持。

来源：

```text
InnovationPoint.supporting_papers
InnovationPoint.limiting_evidence
Gap.supporting_paper_ids
Gap.supporting_evidence_ids
```

## 8. 组合过滤规则

### 8.1 总体策略

Scope 解析采用"基础范围 + 交集过滤"：

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
1. 前端展示"为什么这些论文在范围内"。
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

ScopeQA（已集成）：

```text
LLM 输出 supporting_papers 必须属于 allowed_paper_ids。
LLM 输出 evidence_records 必须属于 allowed_evidence_ids。
graph_paths 里的节点和边必须属于当前 graph context。
```

LiteratureReview（已集成）：

```text
报告引用论文必须属于 allowed_paper_ids。
报告 evidence_ids 必须属于 allowed_evidence_ids。
参考文献列表不能包含 scope 外论文。
```

InnovationReport（已集成）：

```text
创新点 supporting_papers 和 limiting_evidence 必须在 scope 内。
Gap 节点来源 evidence 必须在 scope 内，或者标注"来自 scope 外，未纳入本次结论"。
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

## 15. 下游对接

### 15.1 ScopeQAService 消费 Scope 的方式

```text
1. scope_service.resolve(project_id, scope_payload) → RetrievalScope
2. scope_service.build_scope_guard(scope) → guard dict
3. 检查 scope.metadata["empty_reason"] → 空则拒答
4. scope_service.to_evidence_records(scope) → 检索上下文
5. scope_service.to_paper_cards(scope) → 卡片上下文
6. scope_service.to_graph_context(scope) → 图谱上下文
7. LLM 生成答案
8. _validate_response(response, guard) → 剥离越界引用
9. 保存 scope 摘要到 QAResponse.scope_summary
```

### 15.2 LiteratureReviewGenerator 消费 Scope 的方式

```text
1. scope_service.resolve(project_id, scope_payload) → RetrievalScope
2. 检查 empty_reason → 空则返回空报告
3. collect_materials(scope):
   - to_evidence_records(scope) → evidence
   - to_paper_cards(scope) → cards
   - to_graph_context(scope) → graph
4. 检查 evidence_count < 2 → 证据不足报告
5. LLM 生成综述各节
6. _validate_review(review, scope) → 检查每节 paper_ids/evidence_ids 是否越界
7. 存储 scope 快照到 report.scope
```

### 15.3 InnovationReportGenerator 消费 Scope 的方式

```text
1. scope_service.resolve(project_id, scope_payload) → RetrievalScope
2. 检查 empty_reason → 空则返回空报告
3. collect_signals(scope):
   - to_evidence_records(scope) → evidence
   - to_paper_cards(scope) → cards
   - to_graph_context(scope) → graph
4. 检查 evidence_count < 2 → 证据不足报告
5. 构建候选创新点 → LLM 生成 → 评分 → 过滤泛化
6. _validate_candidates(candidates, scope) → 检查 supporting_papers/supporting_evidence_ids 是否越界
7. 存储 scope 快照到 report.scope
```

### 15.4 normalize_label 的下游复用

`normalize_label` 已被 `innovation_generator.py` 直接导入使用（line 19），用于 limitation/future_work 聚类和去重。该函数应保持在 `scope.py` 作为公共工具函数。

## 16. API 定义

### 16.1 当前已实现

```text
POST /api/rw/projects/{project_ref}/scope/resolve
  请求体：ScopeResolveRequest（type/selected_*_ids/graph_hops/time_range）
  响应：RetrievalScope 对象

GET /api/rw/projects/{project_ref}/scope/filters
  响应：papers/topics/methods/years/graph_nodes 可选列表
```

### 16.2 计划新增

```text
POST /api/rw/projects/{project_ref}/scope/guard/validate
  请求体：{ "guard": {...}, "refs": { "paper_ids": [...], "evidence_ids": [...] } }
  响应：{ "valid": bool, "violations": [...] }

POST /api/rw/projects/{project_ref}/scope/context/evidence
  请求体：ScopeResolveRequest
  响应：EvidenceRecord 列表

POST /api/rw/projects/{project_ref}/scope/context/cards
  请求体：ScopeResolveRequest
  响应：PaperCard 列表

POST /api/rw/projects/{project_ref}/scope/context/graph
  请求体：ScopeResolveRequest
  响应：{ nodes, edges, related_paper_ids, related_evidence_ids }

POST /api/rw/projects/{project_ref}/scope/context/estimate
  请求体：ScopeResolveRequest
  响应：context_budget（paper_count/evidence_count/estimated_tokens/recommended_strategy）
```

### 16.3 ScopeResolveRequest 增强

当前 DTO 缺少 filters 和 options 字段，需扩展：

```python
class ScopeResolveRequest(BaseModel):
    type: str = "all_project"
    selected_paper_ids: list[str] = Field(default_factory=list)
    selected_topic_ids: list[str] = Field(default_factory=list)
    selected_method_ids: list[str] = Field(default_factory=list)
    selected_graph_node_ids: list[str] = Field(default_factory=list)
    selected_graph_edge_ids: list[str] = Field(default_factory=list)
    graph_hops: int = 1
    time_range: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)    # 新增
    options: dict[str, Any] = Field(default_factory=dict)     # 新增
```

### 16.4 保存范围（P2）

```text
POST /api/rw/projects/{project_ref}/scopes
GET  /api/rw/projects/{project_ref}/scopes
GET  /api/rw/projects/{project_ref}/scopes/{scope_id}
PUT  /api/rw/projects/{project_ref}/scopes/{scope_id}
DELETE /api/rw/projects/{project_ref}/scopes/{scope_id}
```

## 17. 前端交互契约

### 17.1 范围选择器

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

### 17.2 范围预览

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

### 17.3 交互要求

```text
1. 用户在 QA、综述、创新点页面看到同一套范围摘要。
2. 空范围时禁用生成按钮。
3. 选择图谱节点后可以预览相关论文和证据。
4. 被排除论文不应出现在默认可选列表中，除非用户开启"显示 excluded"。
5. 每个范围可展示 explain，说明纳入原因。
```

## 18. 日志与诊断

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

## 19. 开发阶段

### R0：修复边界安全（已完成）

目标：让当前 Scope 不会越项目、不会引用 excluded 论文、不会空范围 fallback 全项目。

任务：

```text
R0.1 selected_papers 校验 paper 存在、project_id 匹配、included=True。 ✅
R0.2 topic_group/method_group/year_range 统一应用 included 过滤。 ✅
R0.3 to_evidence_records 禁止 empty scope fallback 全项目 evidence。 ✅
R0.4 _filter_by_year 校验 paper project_id 和 included。 ✅
R0.5 graph_hops 限制 0-2。 ✅
R0.6 GraphService 使用 GraphService(storage=self.storage)。 ✅
R0.7 resolve 返回 warnings / empty_reason / suggested_actions。 ✅
```

验收：

```text
其他项目论文不能进入 selected scope。
excluded 论文不能进入任何默认 scope。
空范围不会返回全项目 evidence。
graph_hops > 2 会被截断并记录 warning。
```

### R1：ResolvedScope 与 ScopeGuard（已完成）

目标：形成下游统一白名单。

任务：

```text
R1.1 新增 build_scope_guard。 ✅
R1.2 新增 validate_against_scope。 ✅
R1.3 resolve 写入 allowed paper/evidence/graph ids。 ✅
R1.4 QA/Review/Innovation 计划统一调用 ScopeGuard。 ✅（已集成到三个下游服务）
R1.5 增加 scope leak 测试。 ✅
```

验收：

```text
ScopeGuard 能拦截范围外 paper_id。
ScopeGuard 能拦截范围外 evidence_id。
ScopeGuard 校验结果可被 QAResponse/report 记录。
```

### R2：组合过滤与归一化（部分完成）

目标：支持 topic + method + year + evidence filters 的交集。

任务：

```text
R2.1 增加 normalize_label。 ✅
R2.2 topic/method 支持多值拆分。 ✅
R2.3 支持同字段 OR、跨字段 AND。 ✅
R2.4 evidence filters 支持 strength、review_status、evidence_type、has_source_quote。 ❌ 待实现
R2.5 增加 explain。 ✅
```

R2.4 实现方案：

```text
1. 依赖 EvidenceRecord 模型扩展 evidence_type 和 review_status 字段（见 06-证据表模块）。
2. _get_evidence_ids 增加 filters 参数。
3. evidence_type 不存在时从 finding/limitation/future_work 推断。
4. review_status 不存在时默认 pending。
5. evidence_strength 按 confidence 映射（>=0.7 → high, >=0.4 → medium, else low）。
6. has_source_quote 检查 source_quote 非空。
```

验收：

```text
topic+method+year 返回交集。
大小写不同的 topic/method 可匹配。
explain 能说明 paper/evidence 纳入原因。
evidence filters 能按 strength/type/status 过滤。
```

### R3：图谱子图 Scope（部分完成）

目标：让图谱节点/子图稳定解析为 paper/evidence 范围。

任务：

```text
R3.1 对接 07 知识图谱模块 get_subgraph related ids。 ✅
R3.2 graph_node_ids / graph_edge_ids 校验属于当前 graph。 ⚠️ 部分
R3.3 fallback 从 graph node/edge properties 提取 paper_ids/evidence_ids。 ✅
R3.4 to_graph_context 返回 related_paper_ids/related_evidence_ids。 ✅
R3.5 支持 Gap 节点解析 supporting evidence。 ❌ 待实现
```

R3.2 完善方案：

```text
1. 在 _find_papers_by_graph_nodes 开始时加载 project graph。
2. 校验每个 node_id 存在于 graph.nodes 中。
3. 不存在的 node_id 写入 invalid_selection。
4. 全部无效时 empty_reason=no_matching_graph_nodes。
```

R3.5 实现方案：

```text
1. 在 _find_papers_by_graph_nodes 中检查节点类型。
2. 如果 node.type == "Gap"，读取 node.properties.get("supporting_evidence_ids", [])。
3. 从 supporting_evidence_ids 反推 paper_ids。
4. 合并到 scope.paper_ids 和 scope.evidence_ids。
5. explain 记录 "gap:xxx supporting evidence"。
```

验收：

```text
选择 Topic 节点可解析相关论文和证据。
选择 Gap 节点可解析 supporting evidence。
图谱子图不会泄漏 scope 外 evidence。
不存在的 node_id 被记录为 invalid_selection。
```

### R4：前端筛选与上下文预算（未开始）

目标：支持前端范围选择器和生成前预估。

任务：

```text
R4.1 get_scope_filters。 ✅（已有基础版）
R4.2 context_budget 估算。 ❌ 待实现
R4.3 to_paper_cards。 ✅（已有基础版）
R4.4 scope preview payload。 ❌ 待实现
R4.5 大范围建议 RAG top-k 或分批。 ❌ 待实现
```

R4.2 实现方案：

```text
1. 统计 scope.paper_count 和 scope.evidence_count。
2. 估算 card_tokens = paper_count * avg_card_tokens（约 700 tokens/card）。
3. 估算 evidence_tokens = evidence_count * avg_evidence_tokens（约 500 tokens/evidence）。
4. 推荐策略：
   paper_count <= 10 → "direct"（直接使用全部 card + evidence）
   paper_count <= 50 → "top_k"（card + top evidence by strength）
   paper_count > 50 → "rag"（RAG 检索，返回 top_k chunks）
5. max_evidence_for_prompt = min(evidence_count, 30)。
6. 写入 scope.metadata["context_budget"]。
```

验收：

```text
前端能展示主题、方法、年份、图谱节点候选。
用户选择范围后能预览 paper/evidence 数量。
大范围能给出 context 策略建议。
context_budget 包含 paper_count/evidence_count/estimated_tokens/recommended_strategy。
```

### R5：保存 Scope 与高级范围（未开始）

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
用户可以保存"实证研究主题 + 2022-2026 + high evidence"的范围。
报告记录 scope_id 后可复现生成范围。
```

## 20. 测试计划

### 20.1 当前测试（22 个）

```text
test_retrieval_scope.py
  TestRetrievalScopeService
    test_resolve_all_project_includes_only_included        # all_project excluded 过滤
    test_resolve_selected_papers                           # 基础 selected_papers
    test_resolve_topic_group                               # topic_group 基础
    test_resolve_year_range                                # year_range 基础
    test_selected_papers_filters_other_project             # 跨项目 paper 拒绝
    test_selected_papers_filters_excluded                  # excluded paper 拒绝
    test_selected_papers_filters_nonexistent               # 不存在 paper 拒绝
    test_empty_project_returns_empty_reason                # 空项目 empty_reason
    test_empty_scope_to_evidence_returns_empty             # 空 scope 不 fallback
    test_all_excluded_returns_empty_reason                 # 全 excluded 空范围
    test_resolve_has_empty_reason                          # 无匹配 topic empty_reason
    test_resolve_has_suggested_actions                     # suggested_actions 非空
    test_resolve_has_explain                               # explain.papers 有数据
    test_resolve_has_warnings_key                          # warnings key 存在
    test_build_scope_guard                                 # guard 有 allowed IDs
    test_validate_against_scope_passes                     # 合法引用通过
    test_validate_against_scope_fails_for_out_of_scope     # 越界引用拦截
    test_topic_and_year_intersection                       # topic + year AND 交集
    test_to_paper_cards                                    # 获取卡片
    test_get_scope_filters                                 # 前端筛选项
    test_graph_hops_clamped                                # hops 截断 + warning
    test_summarize_* (3 个)                                # 摘要文本
```

### 20.2 P1 新增测试

```text
test_retrieval_scope.py（新增）

  TestMethodGroup
    test_resolve_method_group_from_evidence
    test_resolve_method_group_normalizes_case
    test_resolve_method_group_multi_value_split
    test_resolve_method_group_no_match_returns_empty_reason

  TestGraphSubgraph
    test_resolve_graph_subgraph_returns_related_papers
    test_resolve_graph_subgraph_filters_excluded
    test_resolve_graph_subgraph_invalid_node_id_records_invalid_selection
    test_resolve_graph_subgraph_gap_node_resolves_supporting_evidence
    test_resolve_graph_subgraph_node_from_other_project_rejected

  TestEvidenceFilters
    test_evidence_filter_by_strength
    test_evidence_filter_by_evidence_type
    test_evidence_filter_by_has_source_quote
    test_evidence_filter_combines_with_paper_filter
    test_evidence_filter_missing_field_uses_default

  TestCrossFilter
    test_method_and_year_intersection
    test_topic_method_year_triple_intersection
    test_same_field_or_different_field_and

  TestToGraphContext
    test_to_graph_context_graph_scope_delegates_to_graph_service
    test_to_graph_context_non_graph_scope_returns_paper_nodes
    test_to_graph_context_excludes_out_of_scope_nodes

  TestContextBudget
    test_context_budget_small_scope_direct
    test_context_budget_medium_scope_top_k
    test_context_budget_large_scope_rag
    test_context_budget_written_to_metadata

  TestScopeGuardEdgeCases
    test_guard_evidence_violation_detected
    test_guard_all_refs_valid_returns_valid
    test_guard_empty_scope_returns_empty_allowed

  TestExplainDetail
    test_explain_records_topic_match
    test_explain_records_year_match
    test_explain_records_graph_node_match
    test_explain_evidence_source_paper
```

### 20.3 测试文件清单

```text
test_retrieval_scope.py              # 主测试（现有 22 + 新增约 25）
test_scope_project_boundary.py       # 项目边界专项
test_scope_included_filter.py        # included/excluded 专项
test_scope_empty.py                  # 空范围专项
test_scope_guard.py                  # ScopeGuard 专项
test_scope_filters.py                # 前端筛选专项
test_scope_graph_context.py          # 图谱上下文专项
test_scope_explain.py                # explain 专项
test_scope_context_budget.py         # context budget 专项
```

关键测试：

```text
selected_papers 包含其他项目论文时被过滤并记录 invalid_selection。     ✅
topic/method/year 不返回其他项目论文。                                  ✅
evidence_ids 不包含其他项目 evidence。                                  ✅
all_project 不包含 excluded。                                          ✅
selected_papers 选择 excluded 时被过滤。                                ✅
topic/method/year 匹配到 excluded 论文时仍过滤。                        ✅
空项目返回 no_included_papers。                                         ✅
无匹配 topic 返回 no_matching_topic。                                   ✅
非法年份返回 invalid_time_range。                                       ✅
空范围 to_evidence_records 返回空，不 fallback 全项目。                  ✅
topic + method + year 返回交集。                                        ✅
同字段多选为 OR。                                                        ✅
跨字段多选为 AND。                                                       ✅
graph_hops > 2 被截断。                                                 ✅
GraphService 使用同一个 storage。                                        ✅
graph_subgraph 返回 related_paper_ids/evidence_ids。                    ❌ 无实际图谱数据测试
无图谱时返回 graph_not_built。                                           ❌ 未测试
范围外 paper_id 被拦截。                                                 ✅
范围外 evidence_id 被拦截。                                              ❌ 未测试
QAResponse 中越界引用会生成 validation warning。                         ❌ 未测试
get_scope_filters 只统计 included 论文。                                 ✅
topics/methods/years 计数正确。                                          ✅
method_group 能解析。                                                    ❌ 未测试
Gap 节点 supporting_evidence 能解析。                                    ❌ 未测试
context_budget 写入 metadata。                                           ❌ 未测试
```

## 21. 验收标准

P0/R0-R1 完成后（当前状态）：

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
6. Gap 节点能解析 supporting_evidence_ids。
7. graph_node_ids 能校验归属当前 project。
8. method_group 能从图谱 Method 节点优先查找。
9. context_budget 能估算 token 并推荐策略。
10. 报告 scope 快照包含 scope_id 可复现。
```

P2/R5 完成后：

```text
1. 支持保存常用 Scope。
2. 报告可以通过 scope_id 复现生成范围。
3. 支持创新点/gap 相关 Scope。
4. 支持高级范围对比和模板。
```

## 22. 最小实现顺序

推荐顺序：

```text
 1. 补 method_group 测试 + 图谱优先查找。
 2. 补 graph_subgraph 测试（含实际图谱数据）。
 3. 补 to_graph_context 测试。
 4. 补 evidence violation 测试。
 5. 修 graph_node_ids 校验归属当前 project。
 6. 修 Gap 节点 supporting_evidence 解析。
 7. 增加 scope_id 字段。
 8. 增加 context_budget 估算。
 9. 增加 evidence filters（依赖 EvidenceRecord 扩展）。
10. 扩展 ScopeResolveRequest DTO。
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

## 23. 风险与应对

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
| scope_id 缺失 | 报告无法复现生成范围 | P1 增加 scope_id 字段 |
| 图谱节点越界 | 用户传入其他项目 node_id | P1 校验 node 归属 |

## 24. 参考文档

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

## 25. 当前代码对齐深化（2026-06-01 更新）

### 当前实现确认

```text
scope.py 当前包含 RetrievalScopeService（~580 行，9 个公共方法 + 12 个内部方法），已具备 resolve、过滤器、scope guard、empty reason、explain、summarize、get_scope_filters 等完整实现。
models.py 中 RetrievalScope 已有 scope_type/project_id/paper_ids/evidence_ids/graph_node_ids/edge_ids/topic_ids/method_ids/time_range/summary/metadata。
下游三个服务（ScopeQAService、LiteratureReviewGenerator、InnovationReportGenerator）已统一调用 resolve → build_scope_guard → validate_against_scope 流程。
API 层已有 POST scope/resolve + GET scope/filters 两个端点。
normalize_label 已被 innovation_generator.py 复用。
```

### 下一步深化任务（按优先级排序）

```text
1. [P1 高] 补 method_group 图谱优先查找
   - _find_papers_by_methods 应先从图谱 Method 节点查找 related papers
   - fallback 到 evidence method 字段
   - 与 topic_group 的图谱优先模式一致

2. [P1 高] 补 graph_node_ids 校验归属
   - 加载 project graph，校验 node_id 存在于 graph.nodes
   - 不存在的写入 invalid_selection
   - 防止跨项目图谱数据泄漏

3. [P1 高] 补 Gap 节点 supporting_evidence 解析
   - 检查 node.type == "Gap"，读取 supporting_evidence_ids
   - 反推 paper_ids 合并到 scope
   - explain 记录 gap supporting evidence 来源

4. [P1 高] 补测试覆盖
   - method_group、graph_subgraph（含实际图谱数据）、to_graph_context、evidence violation
   - 当前 22 个测试无法覆盖这些场景

5. [P1 中] 增加 scope_id
   - resolve 时生成唯一 scope_id（如 hash(project_id + scope_type + sorted ids)）
   - 写入 scope.metadata["scope_id"]
   - 下游报告 scope 快照可引用 scope_id 复现

6. [P1 中] 增加 context_budget
   - 统计 paper_count/evidence_count
   - 估算 token 消耗
   - 推荐 direct/top_k/rag 策略
   - 写入 scope.metadata["context_budget"]

7. [P1 中] 增加 evidence filters
   - 依赖 EvidenceRecord 扩展 evidence_type/review_status 字段
   - _get_evidence_ids 增加 filters 参数
   - 兼容当前字段（不存在时推断/默认）

8. [P1 低] 扩展 ScopeResolveRequest DTO
   - 增加 filters 和 options 字段
   - 前端可传入 evidence_type/review_status/strength 筛选

9. [P2] 保存 Scope + scope_id 复现
10. [P2] innovation_related scope type
```

### 验收证据

```text
pytest tests/agents_v3/research_workspace/test_retrieval_scope.py 通过。
新增测试覆盖 method_group、graph_subgraph 实际数据、to_graph_context、evidence violation、context_budget。
下游三个服务能通过 scope_service 获取完整上下文（evidence + cards + graph）。
ScopeGuard 能拦截范围外 paper_id 和 evidence_id。
API resolve_scope 返回字段可直接被 QA 和报告生成请求复用。
context_budget 能为大范围推荐合适策略。
```

### 风险与阻塞

```text
如果 Scope 只是前端过滤而非后端强约束，QA 和报告很容易引用用户未选择的论文。
Scope 快照缺失（无 scope_id）会导致报告版本无法解释"当时基于哪些论文生成"。
如果 evidence filters 不实现，QA 和综述无法区分高质量证据和低质量证据，影响输出质量。
如果 graph_node_ids 不校验归属，跨项目图谱数据可能泄漏到 scope 中。
如果 context_budget 不实现，大范围直接塞入所有证据可能超出 LLM 上下文窗口。
```
