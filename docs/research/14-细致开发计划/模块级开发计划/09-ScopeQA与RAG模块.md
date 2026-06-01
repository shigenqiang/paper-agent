# 09-Scope QA 与 RAG 模块专项开发计划

更新时间：2026-06-01

## 0. 与产品方案的关联

### 0.1 可借鉴技术

本模块可借鉴的产品与技术方案（来源：`当前产品方案.md` + `学术报告生成系统产品借鉴与技术方案调研.md`）：

| 借鉴来源 | 借鉴内容 | 落地位置 |
| --- | --- | --- |
| Anthropic Contextual Retrieval | 上下文嵌入 + BM25 混合检索，减少 67% 失败检索 | §8 检索策略 |
| LettuceDetect | Token-level 幻觉检测（ModernBERT），F1=79.22%，MIT 开源 | §12 校验与拒答 |
| PapersFlow | Critic Agent 反证检测 + Chain of Verification (CoVe) | §12 声明验证 |
| Atlas | H/V ratio 质量指标（目标 < 0.1） | §18 评估方案 |
| GPT-Researcher | Review-Revise 循环（Writer→Reviewer→Revisor） | §11 生成与结构化输出 |
| PRISMA-trAIce | AI 辅助 SR 透明报告检查清单（12 项） | §13 QA 会话与历史 |
| Consensus | Claims & Evidence Table、Consensus Meter | §8 检索策略 |
| NotebookLM | Sources + QA + Artifact 交互模式 | §16 前端交互契约 |
| RAGFlow | Parent-Child Chunking、DeepDoc 解析器 | §8 检索策略 |
| Microsoft GraphRAG | local/global 图谱检索、社区摘要 | §9 GraphRAG 集成 |

### 0.2 代码对齐状态

| 产品方案要求 | 代码现状 | 对齐状态 |
| --- | --- | --- |
| Scope 先于检索 | `answer()` 先调 `scope_service.resolve()` | ✅ 已对齐 |
| 规则意图分类 | `classify_intent()` 支持 9 种意图 | ✅ 已对齐 |
| Evidence 打分排序 | `_score_evidence()` 已实现字段打分 | ✅ 已对齐 |
| LLM JSON 结构化输出 | `invoke_json()` 已实现 | ✅ 已对齐 |
| ScopeGuard 校验 | `_validate_response()` 已实现基础校验 | ⚠️ 部分对齐 |
| 空范围拒答 | `_empty_scope_response()` 已实现 | ✅ 已对齐 |
| 证据不足拒答 | `len(evidence) < 2` 时拒答 | ✅ 已对齐 |
| QA 历史保存 | `_save_qa_history()` 已实现 | ✅ 已对齐 |
| BM25 混合检索 | 未实现，仅有字段打分 | ❌ 未对齐 |
| Contextual Retrieval | 未实现 | ❌ 未对齐 |
| 幻觉检测（LettuceDetect） | 未实现 | ❌ 未对齐 |
| Chain of Verification | 未实现 | ❌ 未对齐 |
| H/V ratio 质量指标 | 未实现 | ❌ 未对齐 |
| Review-Revise 循环 | 未实现 | ❌ 未对齐 |
| GraphRAG local/global | 未实现，仅有基础 graph_context | ❌ 未对齐 |
| 上下文压缩（大范围论文） | 未实现 | ❌ 未对齐 |
| Retrieval diagnostics | 已有基础 diagnostics | ⚠️ 部分对齐 |
| Context budget 控制 | 未实现 | ❌ 未对齐 |

本文档基于 `docs/research` 下的产品方案、当前开发计划、学术 QA/RAG 调研、RAG 与知识图谱评估调研、证据表计划、知识图谱计划、RetrievalScope 计划、Token 成本分析和当前代码实现，重新细化 Scope QA 与 RAG 模块的开发方案。

Scope QA 是用户和论文知识库交互的主入口。它不是普通聊天，而是“基于选定范围的学术证据问答”。它必须先解析 Retrieval Scope，再在 Scope 内检索 EvidenceRecord、PaperCard、GraphContext 和必要 chunk，最后生成带范围声明、证据引用、图谱路径和不确定性说明的回答。

对应代码：

```text
src/agents_v3/research_workspace/scope_qa.py
src/agents_v3/research_workspace/scope.py
src/agents_v3/research_workspace/llm/service.py
src/agents_v3/research_workspace/llm/prompts.py
src/agents_v3/research_workspace/models.py
tests/agents_v3/research_workspace/test_scope_qa.py
```

上游依赖：

```text
papers
paper_chunks
paper_cards
evidence_records
KnowledgeGraph
RetrievalScope
```

下游依赖：

```text
LiteratureReviewGenerator
InnovationReportGenerator
ReportService
QA history / evaluation
前端研究 QA 页面
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

Scope QA 位于 Scope 之后、报告生成之前，是用户反复探索论文库的核心交互层。它需要支撑这些问题：

```text
这些论文共同研究了什么？
这个主题下常用方法有哪些？
这些研究主要不足是什么？
这些文献能否支撑我的选题？
这个 gap 背后有哪些证据？
论文 A 和论文 B 为什么相关？
基于当前范围有哪些可行创新点？
当前范围能否生成文献综述？
```

### 1.2 一句话目标

实现一个范围受控、证据优先、可引用、可拒答、可评估的学术 RAG 问答服务。

### 1.3 核心原则

```text
1. Scope 先于检索。
2. EvidenceRecord 优先于 PaperCard，PaperCard 优先于全文 chunk。
3. 所有关键结论必须尽量引用 evidence_id。
4. LLM 输出的 paper_id/evidence_id 必须经过 ScopeGuard 校验。
5. 证据不足、证据低质量或范围为空时，明确拒答或说明不确定。
6. GraphRAG 路径只能解释关系，不能替代文献证据。
7. QA 输出可以保存为综述素材或创新点素材，但不能绕过证据层。
```

## 2. 本地调研结论落地

### 2.1 产品方案落地

`当前产品方案.md` 明确要求 Scope-based QA 输出：

```text
回答内容
范围声明
支撑论文
证据记录
图谱路径
不确定性说明
建议动作
```

因此 `QAResponse` 不应只是自然语言答案，还必须包含：

```text
scope_summary
supporting_papers
evidence_records
source_quotes
graph_paths
uncertainty
suggested_actions
validation_warnings
retrieval_diagnostics
```

### 2.2 RetrievalScope 计划落地

08 模块要求 Scope 输出：

```text
paper_ids
evidence_ids
graph_node_ids
graph_edge_ids
summary
empty_reason
explain
ScopeGuard
```

Scope QA 的入口必须固定为：

```text
scope_payload
  -> RetrievalScopeService.resolve()
  -> build_scope_guard()
  -> retrieve_context()
  -> generate_answer()
  -> validate_answer_against_scope()
  -> save QA history
```

### 2.3 证据表计划落地

06 证据表模块要求 EvidenceRecord 成为事实层，并逐步增强：

```text
evidence_type
claim
review_status
source_quote
source_chunk_id
evidence_strength
```

Scope QA 实现必须兼容当前旧字段：

```text
finding
limitation
future_work
method
data_or_sample
topic
source_quote
source_chunk_id
```

同时为新字段预留：

```text
claim
evidence_type
review_status
evidence_relation
confidence
```

### 2.4 知识图谱计划落地

07 知识图谱模块要求 GraphRAG 支持：

```text
local graph search
global graph summary
path explanation
related_paper_ids
related_evidence_ids
```

Scope QA 对图谱的使用规则：

```text
1. graph_subgraph scope 优先使用 Scope 中已解析的 graph context。
2. 普通问题可通过 question 匹配 graph node label 做 local graph search。
3. path explanation 只作为解释关系的辅助上下文。
4. 回答的事实依据仍必须来自 EvidenceRecord 或 source_quote。
```

### 2.5 学术 QA/RAG 调研落地

调研文档给出的主流 RAG 流程：

```text
query
  -> retriever
  -> reranker
  -> context assembly
  -> LLM generation
  -> citation validation
```

本项目 MVP 先不强依赖向量数据库，但要实现可解释的证据检索：

```text
question + resolved_scope
  -> intent classification
  -> rule/BM25-like evidence scoring
  -> graph context expansion
  -> top-k evidence + paper cards
  -> strict JSON answer
  -> ScopeGuard + citation validation
```

高级 RAG 能力的落地顺序：

| 技术 | 本项目策略 |
| --- | --- |
| Query Decomposition | P1 用于复杂比较、多跳、综述类问题 |
| CRAG | P1/P2 用 retrieval_quality 判断是否拒答、补检索或扩大范围 |
| Self-RAG | P2 做检索充分性和答案支撑性自检 |
| Step-back | P2 用于方法论、趋势、理论框架问题 |
| HyDE | 暂缓，学术场景可能引入假设性幻觉，只有向量检索成熟后谨慎使用 |
| BM25 + Vector + Rerank | P1/P2 逐步接入，MVP 先做关键词/字段打分 |

### 2.6 评估调研落地

RAG 评估建议指标：

```text
Context Precision >= 0.75
Context Recall >= 0.80
Faithfulness >= 0.80
Answer Relevance >= 0.80
```

Scope QA 模块自身质量门槛：

```text
scope_violation_rate == 0
empty_scope_refusal_rate == 1.0
out_of_scope_citation_count == 0
answer_citation_coverage >= 0.8
top_k_deterministic == true
```

### 2.7 Token 成本调研落地

Token 调研建议使用分层内容：

| 层级 | 内容 | QA 用途 |
| --- | --- | --- |
| L0 | 论文元数据 | 范围说明、参考文献展示 |
| L1 | 摘要 | 大范围概览 |
| L2 | PaperCard | 主题、方法、发现、局限的综合 |
| L3 | EvidenceRecord | 精确证据问答和引用 |
| L4 | 相关 chunks/source_quote | 深度 QA 和来源定位 |
| L5 | 全文 | 单篇深度分析，默认不进入多篇 QA |

QA 上下文默认使用 L2-L3，必要时追加 L4，不直接塞全文。

## 3. 当前实现分析

### 3.1 已有能力

当前 `ScopeQAService` 已实现：

```text
answer(project_id, question, scope_payload)
classify_intent(question)
retrieve_context(question, scope)
generate_answer(question, context, scope, intent)
_build_evidence_summary(context)
_fallback_answer(question, context, intent)
_build_suggested_actions(intent)
```

当前已有优点：

| 能力 | 状态 |
| --- | --- |
| Scope 入口 | 已使用 `RetrievalScopeService.resolve()` |
| 规则意图分类 | 已支持 summary、method、limitation、comparison、trend、evidence、review、innovation |
| 上下文聚合 | 已收集 evidence_records、paper_cards、graph nodes/edges |
| 空论文/空证据处理 | 已有基础降级 |
| LLM JSON 调用 | 使用 `llm.invoke_json()` |
| fallback | LLM 失败时可用规则回答 |
| QAResponse | 已包含 answer、intent、scope_summary、supporting_papers、evidence_records、graph_paths、uncertainty、suggested_actions |

### 3.2 当前关键问题

| 问题 | 当前表现 | 影响 | 优先级 |
| --- | --- | --- | --- |
| 检索无排序 | `retrieve_context` 取 Scope 内全部 evidence | 噪声大，Context Precision 低 | P0 |
| top-k 不可控 | `_build_evidence_summary` 固定前 20 条 | 重要证据可能被截断 | P0 |
| 没有 ScopeGuard | 生成后不校验引用 | 可能输出 scope 外来源 | P0 |
| LLM 输出 schema 弱 | prompt 只要求 answer/key_points/uncertainty | 无 evidence_id、paper_id、source_quote | P0 |
| 回答引用粗糙 | supporting_papers/evidence_records 直接取上下文前 10 | 不是模型实际使用的证据 | P0 |
| graph_paths 为空 | 未调用 GraphService.find_paths | 多跳解释缺失 | P1 |
| 证据质量无过滤 | rejected/low/无来源证据不降权 | 低质量证据会进入答案 | P0 |
| 空范围处理依赖旧 Scope | selected_papers 非法时可能被 Scope fallback 影响 | QA 可能基于错误范围回答 | P0 |
| 无 QA history | 不保存问题、范围、上下文、答案 | 无法复盘和评估 | P1 |
| 无 retrieval diagnostics | 无评分、命中原因、候选数 | 无法调参 | P0 |
| 无 context budget | 大范围直接放入证据 | 超 token 或 Lost in the Middle | P1 |
| 测试可能触发真实 LLM | `ScopeQAService()` 默认创建真实 LLM | 测试不稳定，依赖环境变量 | P0 |

## 4. 主流做法与本项目选择

| 主流做法 | 本项目落地 |
| --- | --- |
| metadata filter 先限定 corpus | RetrievalScope 必须先 resolve，检索只在 Scope 内做 |
| BM25 + vector + reranker | P0 规则/字段打分，P1 BM25，P2 vector/reranker |
| structured citations | LLM 输出 `supporting_evidence_ids` 和 `supporting_paper_ids` |
| citation validation | ScopeGuard + evidence existence validation |
| CRAG quality check | P1 增加 retrieval_quality 判断拒答/补检索 |
| GraphRAG local/global | P1 local graph search，P2 topic/gap summary |
| RAGAS metrics | 先做 golden case 的轻量评估，后续接 RAGAS 风格指标 |

MVP 选择：

```text
不用先上向量库。
不用先做复杂 agent workflow。
先把 Scope、证据排序、引用、拒答和校验打牢。
```

## 5. 目标架构

### 5.1 服务职责拆分

当前可以继续放在 `scope_qa.py`，但职责要清晰：

```text
ScopeQAService
  编排入口：resolve scope、检索、生成、校验、保存。

QAIntentClassifier
  问题意图分类和检索策略选择。

EvidenceRetriever
  在 Scope 内对 EvidenceRecord 打分、排序和过滤。

GraphContextRetriever
  调用 GraphService 进行节点匹配、子图和路径解释。

QAContextBuilder
  组装 evidence/cards/graph/source_quote，并控制 token budget。

AnswerGenerator
  构建 prompt，调用 LLM，解析结构化输出。

AnswerValidator
  ScopeGuard、citation、schema 和 grounding 校验。

QAHistoryService
  保存问题、scope、retrieval diagnostics、response。
```

### 5.2 数据流

```text
question + scope_payload
  |
  v
RetrievalScopeService.resolve()
  |
  v
ScopeGuard
  |
  v
Intent classification + query analysis
  |
  v
Evidence retrieval within scope
  |
  +--> GraphRAG context
  +--> PaperCard context
  +--> source_quote/chunk context
  |
  v
Context assembly with token budget
  |
  v
LLM structured answer
  |
  v
Answer validation
  |
  v
QAResponse + QAHistory
```

### 5.3 对外接口

建议保留当前入口，并逐步扩展：

```python
class ScopeQAService:
    def answer(self, project_id: str, question: str, scope_payload: dict[str, Any]) -> QAResponse: ...
    def classify_intent(self, question: str) -> str: ...
    def retrieve_context(self, question: str, scope: RetrievalScope, options: dict | None = None) -> dict[str, Any]: ...
    def generate_answer(self, question: str, context: dict[str, Any], scope: RetrievalScope, intent: str) -> QAResponse: ...
    def validate_answer(self, response: QAResponse, context: dict[str, Any], scope: RetrievalScope) -> dict[str, Any]: ...
    def save_history(self, project_id: str, question: str, scope: RetrievalScope, context: dict[str, Any], response: QAResponse) -> dict[str, Any]: ...
```

依赖注入：

```python
def __init__(
    self,
    storage: JSONStorage | None = None,
    llm_service: LLMService | None = None,
    scope_service: RetrievalScopeService | None = None,
    graph_service: GraphService | None = None,
):
    ...
```

这样测试可以传入 fake LLM，避免真实 API 调用。

## 6. 数据模型设计

### 6.1 当前 QARequest / QAResponse 基线

当前 `QARequest`：

```text
question
scope
```

当前 `QAResponse`：

```text
answer
intent
scope_summary
supporting_papers
evidence_records
graph_paths
uncertainty
suggested_actions
```

### 6.2 QARequest 建议增强

```text
question
scope
session_id
options
top_k
include_quotes
include_graph
include_cards
answer_format
save_history
```

示例：

```json
{
  "question": "这些论文的共同局限是什么？",
  "scope": {"type": "topic_group", "selected_topic_ids": ["llm feedback"]},
  "session_id": "qa_session_001",
  "top_k": 12,
  "include_quotes": true,
  "include_graph": true,
  "options": {
    "min_evidence": 2,
    "max_context_tokens": 12000,
    "strict_citations": true
  }
}
```

### 6.3 QAResponse 建议增强

```text
answer
intent
scope_summary
supporting_papers
evidence_records
source_quotes
graph_paths
uncertainty
suggested_actions
retrieval_diagnostics
validation_warnings
refusal_reason
confidence
saved_as_material_id
```

### 6.4 ScoredEvidence

内部结构：

```python
class ScoredEvidence(BaseModel):
    evidence_id: str
    paper_id: str
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    matched_fields: list[str] = Field(default_factory=list)
    evidence_type: str = ""
    claim: str = ""
    source_quote: str = ""
    evidence_strength: str = "medium"
    review_status: str = "pending"
```

### 6.5 QAContext

内部结构：

```python
class QAContext(BaseModel):
    scope_summary: str
    paper_count: int = 0
    evidence_count: int = 0
    selected_evidence: list[dict[str, Any]] = Field(default_factory=list)
    selected_cards: list[dict[str, Any]] = Field(default_factory=list)
    graph_context: dict[str, Any] = Field(default_factory=dict)
    source_quotes: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    token_estimate: int = 0
```

### 6.6 QAHistoryItem

建议新增 collection：

```text
qa_history
qa_sessions
```

结构：

```python
class QAHistoryItem(BaseModel):
    qa_id: str
    project_id: str
    session_id: str = ""
    question: str
    scope: dict[str, Any] = Field(default_factory=dict)
    intent: str = "summary"
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    retrieved_paper_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    response: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    validation_warnings: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
```

## 7. 意图分类

### 7.1 P0 规则意图

先用规则分类，保证可测试：

```text
summary
method_analysis
method_compare
finding_summary
limitation_analysis
gap_analysis
evidence_check
trend_analysis
paper_compare
scope_feasibility
review_material
innovation_seed
review_generation
innovation_generation
```

### 7.2 意图识别规则

| 关键词/特征 | intent |
| --- | --- |
| 不足、局限、limitation、缺陷 | limitation_analysis |
| 方法、method、模型、实验设计 | method_analysis |
| 比较、对比、区别、优劣 | method_compare / paper_compare |
| 发现、结论、结果、finding | finding_summary |
| gap、空白、未来工作、创新机会 | gap_analysis / innovation_seed |
| 支撑、证据、是否能证明 | evidence_check / scope_feasibility |
| 趋势、演进、年份、近年来 | trend_analysis |
| 综述、文献综述、研究现状 | review_material / review_generation |
| 创新点、选题、论文题目 | innovation_seed / innovation_generation |

### 7.3 意图到检索字段

| intent | 优先字段 | 次级字段 | 图谱辅助 |
| --- | --- | --- | --- |
| summary | topic、finding | method、limitation | Topic |
| method_analysis | method、data_or_sample | finding、limitation | Method、Dataset |
| method_compare | method、finding、limitation | data_or_sample | Method path |
| finding_summary | finding | topic、method | Topic |
| limitation_analysis | limitation | future_work | Limitation、Gap |
| gap_analysis | future_work、limitation | finding | Gap |
| evidence_check | source_quote、citation_context | finding、limitation | Evidence path |
| trend_analysis | year、topic、finding | method | Topic by year |
| paper_compare | finding、method、limitation | topic | Paper path |
| innovation_seed | gap、future_work、limitation | method、dataset | Gap |

### 7.4 P1 查询分解

复杂问题触发 Query Decomposition：

```text
包含“比较 + 局限 + 方法”等多意图。
要求跨主题/跨方法综合。
要求“为什么”“如何”“哪些证据支持”。
```

输出：

```json
{
  "sub_questions": [
    {"question": "这些论文使用了哪些方法？", "intent": "method_analysis"},
    {"question": "这些方法各自有什么局限？", "intent": "limitation_analysis"}
  ],
  "combine_strategy": "synthesize"
}
```

P0 不实现 LLM 分解，先预留接口。

## 8. 检索策略

### 8.1 Scope 内检索原则

```text
1. 只检索 scope.evidence_ids。
2. 如果 scope.evidence_ids 为空，不允许 fallback 全项目。
3. rejected evidence 默认排除。
4. low evidence 降权。
5. 有 source_quote/source_chunk_id 的证据加权。
6. 检索结果必须稳定排序。
```

### 8.2 Evidence 文本标准化

为当前旧 EvidenceRecord 生成检索文本：

```text
claim_text =
  finding
  + limitation
  + future_work
  + method
  + data_or_sample
  + research_question
  + topic
  + citation_context
  + source_quote
```

推断 evidence_type：

```text
finding 非空 -> finding
limitation 非空 -> limitation
future_work 非空 -> future_work
method 非空 -> method
data_or_sample 非空 -> dataset
```

### 8.3 P0 字段打分

对 Scope 内 evidence 打分：

```text
score = 0
+ 4 intent 对应字段命中
+ 3 claim/finding/limitation/future_work 命中关键词
+ 2 topic/method/data_or_sample 命中关键词
+ 2 source_quote/citation_context 命中关键词
+ 2 evidence_type 与 intent 匹配
+ 2 review_status == accepted
+ 1 evidence_strength == high
+ 1 has_source_quote
+ 1 graph_related_evidence
- 3 review_status == rejected
- 1 evidence_strength == low
```

排序：

```text
score desc
evidence_strength desc
has_source_quote desc
paper_id asc
evidence_id asc
```

### 8.4 P0 检索返回

默认：

```text
top_k_evidence = 12
max_candidate_evidence = 50
top_cards = 8
max_graph_nodes = 20
max_source_quotes = 10
```

返回 diagnostics：

```json
{
  "candidate_evidence_count": 42,
  "selected_evidence_count": 12,
  "top_score": 8.5,
  "min_selected_score": 2.0,
  "low_quality_count": 3,
  "matched_fields": {
    "finding": 8,
    "limitation": 2
  }
}
```

### 8.5 P1 BM25 / keyword retrieval

P1 可实现轻量 BM25，不必立即引入向量库：

```text
语料：Scope 内 EvidenceRecord claim_text + PaperCard fields。
查询：question + intent keywords。
输出：BM25 score。
融合：field_score + BM25 score + quality score。
```

### 8.6 P2 Hybrid Retrieval

后续：

```text
BM25 候选 50
vector 候选 50
RRF 融合
cross-encoder rerank top 20
graph proximity 加权
```

接口预留：

```python
class EvidenceRetriever:
    def retrieve(self, question: str, scope: RetrievalScope, intent: str, top_k: int) -> list[ScoredEvidence]:
        ...
```

## 9. GraphRAG 集成

### 9.1 P0 graph context

如果 Scope 是 `graph_subgraph`：

```text
直接使用 scope_service.to_graph_context(scope)。
提取 graph nodes/edges。
提取 related_evidence_ids 并加入 evidence candidates。
```

如果 Scope 不是 graph_subgraph：

```text
根据 question 关键词简单匹配 graph node label。
命中节点后取 1-hop 子图。
从子图 related_evidence_ids 加权。
```

### 9.2 P1 local graph search

适用：

```text
这个 gap 的证据是什么？
这个方法连接了哪些论文？
论文 A 和论文 B 有什么关系？
```

流程：

```text
search_nodes(question)
  -> get_subgraph(hops=1)
  -> collect related evidence
  -> build graph relation summary
```

### 9.3 P1 path explanation

调用：

```python
GraphService.find_paths(project_id, source_id, target_id, max_hops=3)
```

目标 path 输出：

```json
{
  "node_ids": ["paper:p1", "topic:abc", "paper:p2"],
  "edge_ids": ["edge:1", "edge:2"],
  "related_evidence_ids": ["ev1", "ev2"],
  "explanation": "两篇论文都属于主题 LLM feedback"
}
```

QA 使用规则：

```text
路径用于解释关系。
事实结论仍必须引用 EvidenceRecord。
路径上的 evidence_id 进入检索候选并加权。
```

### 9.4 P2 global graph search

适用：

```text
整个项目的研究脉络是什么？
这个领域的主要主题和空白是什么？
```

依赖 07 模块：

```text
Topic summary
Gap summary
Method summary
graph community / cluster summary
```

## 10. 上下文组装

### 10.1 上下文组成

```text
Scope summary
Intent and query diagnostics
Selected evidence records
Selected paper cards
Graph relations / paths
Source quotes
Instructions and output schema
```

### 10.2 Prompt context 格式

```text
[Scope]
{scope_summary}
Allowed papers: p1, p2
Allowed evidence: ev1, ev2

[Question]
...

[Evidence]
ev1 | paper:p1 | type:finding | strength:high
claim: ...
quote: ...

[Paper Cards]
p1 | title | method | key_findings | limitations

[Graph Context]
paper:p1 --USES_METHOD--> method:...
path: ...
```

### 10.3 Token budget

默认预算：

```text
system prompt: 800-1200 tokens
scope summary: 200-500
evidence records: 3000-6000
paper cards: 2000-5000
graph context: 500-1500
source quotes/chunks: 1000-3000
output reserve: 1500-3000
```

策略：

```text
evidence_count <= 12：全部放入。
12 < evidence_count <= 50：top_k + paper cards。
evidence_count > 50：top_k evidence + topic/method summaries。
paper_count > 50：不放全部 card，只放相关 card 或 summary。
```

### 10.4 Lost in the Middle 处理

```text
1. 最重要证据放在 Evidence 开头。
2. scope guard 和输出 schema 放在 prompt 开头和结尾。
3. source quote 不做长列表堆叠。
4. 对长 scope 先分组摘要再回答。
```

## 11. 生成与结构化输出

### 11.1 System prompt 要求

必须包含：

```text
你只能基于给定 Scope 和 Evidence 回答。
不得引用输入中不存在的 paper_id/evidence_id。
如果证据不足，必须说明不确定性或拒答。
每个关键结论尽量绑定 evidence_id。
不要把图谱路径当作事实来源，路径只解释关系。
输出必须是 JSON。
```

### 11.2 LLM 输出 schema

```json
{
  "answer": "回答正文",
  "key_points": [
    {
      "text": "要点",
      "evidence_ids": ["ev1"],
      "paper_ids": ["p1"]
    }
  ],
  "supporting_evidence_ids": ["ev1"],
  "supporting_paper_ids": ["p1"],
  "source_quotes": [
    {"evidence_id": "ev1", "quote": "..."}
  ],
  "graph_paths": [],
  "uncertainty": "不确定性说明",
  "confidence": 0.75,
  "suggested_actions": ["generate_literature_review"]
}
```

### 11.3 JSON 解析失败处理

如果 `invoke_json()` 返回 `raw_response` 或解析失败：

```text
1. 尝试从 raw_response 提取 answer。
2. 不信任其中的 citations。
3. supporting_evidence_ids 使用检索 top evidence。
4. validation_warnings 写 json_parse_failed。
5. uncertainty 提高。
```

### 11.4 fallback 回答

LLM 失败时仍要遵守 Scope：

```text
limitation_analysis -> 输出 top limitation evidence。
method_analysis -> 输出 top method evidence。
finding_summary -> 输出 top finding evidence。
gap_analysis -> 输出 future_work/limitation/gap evidence。
summary -> 输出 topic + finding 的简短总结。
```

fallback 不得编造，只能使用 context 中的 evidence。

## 12. 校验与拒答

### 12.1 ScopeGuard 校验

回答后检查：

```text
supporting_paper_ids 全部属于 allowed_paper_ids。
supporting_evidence_ids 全部属于 allowed_evidence_ids。
source_quotes 对应 evidence_id 存在于 context。
graph_paths 对应 graph ids 属于 graph context。
```

越界处理：

```text
1. 删除越界引用。
2. 写入 validation_warnings。
3. 如果删除后无有效证据，转为拒答/不确定回答。
```

### 12.2 Citation 校验

检查：

```text
evidence_id 是否存在。
evidence_id 是否在 retrieved_evidence_ids。
paper_id 是否与 evidence.paper_id 一致。
source_quote 是否来自 evidence.source_quote 或 chunk。
```

### 12.3 Grounding 轻量校验

P0 规则：

```text
回答中出现的 evidence_id 必须在上下文。
每个 key_point 至少有一个 evidence_id，除非是范围说明或不确定性。
如果 answer 很长但 evidence_ids 很少，警告 low_citation_coverage。
```

### 12.3.1 幻觉检测（借鉴 LettuceDetect）

产品方案要求 QA 回答使用 LettuceDetect 进行 token-level 幻觉检测。

LettuceDetect 技术参数：

```text
模型：ModernBERT-based（17-68M 参数 tiny variants）
训练数据：RAGTruth 数据集
精度：F1=79.22%（token-level）
许可证：MIT 开源
支持长度：8192 tokens
多语言：EuroBERT 版本支持
```

集成方案：

```text
输入：
  - context: 检索到的 evidence 文本（拼接）
  - response: LLM 生成的回答文本

步骤：
  1. 将 context 和 response 拼接为 LettuceDetect 输入格式
  2. 模型对 response 中每个 token 标注：SUPPORTED / NOT_SUPPORTED / UNKNOWN
  3. 统计 NOT_SUPPORTED token 占比

输出：
  - hallucination_tokens: list[int] — 幻觉 token 位置
  - hallucination_ratio: float — 幻觉 token 占比
  - supported_ratio: float — 有支撑 token 占比
  - h_v_ratio: float — 幻觉断言数 / 总断言数（目标 < 0.1）

集成位置：
  - generate_answer() 返回前调用
  - 结果写入 QAResponse.validation_warnings
  - h_v_ratio > 0.3 时标记 high_hallucination_risk
  - h_v_ratio > 0.5 时触发拒答或强制 uncertainty 提升
```

MVP 降级方案：

```text
如果 LettuceDetect 模型未部署：
  1. 使用规则检查：answer 中未被 evidence_id 引用的关键断言
  2. 计算 citation_coverage = 有引用的断言数 / 总断言数
  3. citation_coverage < 0.5 视为等效 hallucination_ratio > 0.3
```

### 12.3.2 Chain of Verification（借鉴 PapersFlow）

产品方案要求 QA 和报告使用 Chain of Verification 确保断言有文献支撑。

实现方案：

```text
步骤：
  1. 从 answer 中提取关键声明（key_points）
  2. 对每个声明，检查是否有对应的 evidence_id
  3. 对有 evidence_id 的声明，验证 evidence 是否支持该声明
  4. 对无 evidence_id 的声明，标记为 unverified

验证状态：
  - supported: 有 evidence_id 且 evidence 支持
  - partially_supported: 有 evidence_id 但 evidence 部分支持
  - unverified: 无 evidence_id
  - contradicted: evidence 与声明矛盾（需要 CONTRADICTS 边）

输出：
  - verification_results: list[dict] — 每个 key_point 的验证状态
  - unverified_claims: list[str] — 未验证的声明
  - verification_score: float — 已验证声明占比
```

P2 增强：

```text
1. 使用 LLM 做 claim-level 证据匹配（而非仅靠 evidence_id 存在性）
2. 自动搜索反证：在 Scope 内搜索与声明矛盾的 evidence
3. 反证结果写入 QAResponse.counter_evidence
```

### 12.3.3 H/V Ratio 质量指标（借鉴 Atlas）

Atlas 在 200 篇论文语料库上测试，H/V ratio = 0.05（最低）。本产品应将此作为 QA 质量指标。

```text
H/V ratio = 幻觉断言数 / 总断言数

计算：
  1. 总断言数 = len(key_points)
  2. 幻觉断言数 = len(unverified_claims) + len(contradicted_claims)
  3. H/V ratio = 幻觉断言数 / 总断言数

目标：
  - H/V ratio < 0.1（优秀）
  - H/V ratio < 0.2（可接受）
  - H/V ratio >= 0.3（需要 Review-Revise）

写入：
  - QAResponse.metadata.h_v_ratio
  - QA history 记录
  - 评估方案统计
```

P2 可增加 LLM judge：

```text
提取 answer statements。
逐条判断是否被 evidence 支撑。
计算 faithfulness。
```

### 12.4 拒答触发条件

```text
scope.paper_ids 为空。
scope.evidence_ids 为空。
retrieved_evidence_count < min_evidence，默认 2。
top_score < min_relevance_score。
所有证据 evidence_strength=low。
所有证据缺少 source_quote 且问题要求精确证据。
ScopeGuard 删除所有引用。
问题明显超出当前范围。
```

拒答输出：

```text
说明当前范围无法回答。
说明缺少哪些证据。
给出 suggested_actions。
不生成泛化答案。
```

## 13. QA 会话与历史

### 13.1 保存内容

每次 QA 保存：

```text
question
scope_payload
resolved_scope
intent
retrieved_evidence_ids
retrieval_diagnostics
graph_context ids
response
validation_warnings
model info
created_at
```

### 13.2 collection

```text
qa_sessions
qa_history
qa_saved_materials
```

### 13.3 保存为素材

用户可以把回答保存为：

```text
review_material
innovation_material
evidence_note
```

保存时必须记录：

```text
qa_id
scope_id / scope payload
paper_ids
evidence_ids
answer excerpt
created_at
```

## 14. 与下游模块集成

| 下游模块 | 使用方式 |
| --- | --- |
| 综述生成 | QA 回答可保存为 review_material，但最终综述仍需重新基于 Scope 和 Evidence 生成 |
| 创新点报告 | gap_analysis / innovation_seed 的回答可作为候选，但创新点必须回查 Gap 和 Evidence |
| ReportService | 报告记录 QA 来源、scope、paper_ids、evidence_ids |
| KnowledgeGraph 页面 | 用户从图谱节点发起 QA，scope_payload 使用 graph_subgraph |
| 前端 QA 页面 | 展示 scope summary、证据列表、引用、图谱路径、不确定性 |

## 15. API 计划

### 15.1 QA

```text
POST /api/rw/projects/{project_id}/qa
GET  /api/rw/projects/{project_id}/qa/sessions
POST /api/rw/projects/{project_id}/qa/sessions
GET  /api/rw/projects/{project_id}/qa/sessions/{session_id}
GET  /api/rw/projects/{project_id}/qa/history
GET  /api/rw/projects/{project_id}/qa/history/{qa_id}
```

### 15.2 检索和诊断

```text
POST /api/rw/projects/{project_id}/qa/retrieve
POST /api/rw/projects/{project_id}/qa/validate
POST /api/rw/projects/{project_id}/qa/evaluate
```

### 15.3 素材保存

```text
POST /api/rw/projects/{project_id}/qa/history/{qa_id}/save-material
GET  /api/rw/projects/{project_id}/qa/materials
DELETE /api/rw/projects/{project_id}/qa/materials/{material_id}
```

## 16. 前端交互契约

### 16.1 QA 页面组成

```text
Scope selector
Question input
Answer panel
Evidence panel
Graph path panel
Uncertainty / warnings
Suggested actions
History sidebar
```

### 16.2 回答展示

必须展示：

```text
当前范围：scope_summary
支撑论文：supporting_papers
支撑证据：evidence_records
证据引用：source_quotes
图谱路径：graph_paths
不确定性：uncertainty
校验警告：validation_warnings
```

### 16.3 建议动作

按 intent 返回：

```text
generate_literature_review
generate_innovation_report
save_as_review_material
save_as_innovation_material
expand_to_project_scope
adjust_scope
build_knowledge_graph
generate_evidence_table
```

## 17. 日志与监控

结合日志监控计划，Scope QA 记录结构化事件：

```text
qa.answer.started
qa.scope.resolved
qa.retrieve.completed
qa.generate.started
qa.generate.completed
qa.validate.completed
qa.answer.refused
qa.history.saved
qa.answer.failed
```

字段：

```json
{
  "event": "qa.retrieve.completed",
  "project_id": "proj_001",
  "qa_id": "qa_001",
  "scope_type": "topic_group",
  "intent": "limitation_analysis",
  "candidate_evidence_count": 42,
  "selected_evidence_count": 12,
  "top_score": 8.5,
  "duration_ms": 37
}
```

监控指标：

```text
qa_latency_ms
retrieval_latency_ms
generation_latency_ms
scope_violation_count
refusal_rate
empty_scope_rate
avg_selected_evidence_count
answer_citation_coverage
json_parse_failure_rate
llm_failure_rate
```

## 18. 评估方案

### 18.1 Golden Cases

每个项目或 fixture 保留：

```json
{
  "case_id": "qa_limitation_001",
  "question": "这些论文的共同局限是什么？",
  "scope_payload": {"type": "selected_papers", "selected_paper_ids": ["p1", "p2"]},
  "expected_intent": "limitation_analysis",
  "expected_evidence_ids": ["ev_lim_1", "ev_lim_2"],
  "forbidden_paper_ids": ["p3"],
  "expected_answer_keywords": ["样本", "时间"],
  "should_refuse": false
}
```

### 18.2 指标

| 指标 | 含义 | MVP 目标 |
| --- | --- | --- |
| intent_accuracy | 意图分类是否正确 | >= 0.85 |
| context_precision | 检索结果相关比例 | >= 0.75 |
| context_recall | golden evidence 是否被检出 | >= 0.80 |
| faithfulness | 答案是否被证据支撑 | >= 0.80 |
| answer_relevance | 是否回答问题 | >= 0.80 |
| scope_violation_rate | 是否引用 Scope 外来源 | 0 |
| refusal_correctness | 该拒答时是否拒答 | >= 0.90 |
| citation_coverage | 关键要点有引用比例 | >= 0.80 |

### 18.3 本地评估脚本

与 15 模块衔接：

```text
scripts/evaluate_research_workspace.py --target qa
```

输出：

```text
case_count
pass_count
intent_accuracy
context_precision
context_recall
scope_violation_count
refusal_correctness
failed_cases
```

## 19. 开发阶段

### Q0：测试稳定和依赖注入

目标：让 QA 服务可测试，不依赖真实 LLM。

任务：

```text
Q0.1 ScopeQAService 支持注入 scope_service、graph_service、llm_service。
Q0.2 增加 FakeLLMService / StubLLMService 测试工具。
Q0.3 answer 流程记录 qa_id。
Q0.4 现有测试不再触发真实 API。
```

验收：

```text
test_scope_qa.py 在无 OPENAI_API_KEY 环境下稳定通过。
LLM 失败时 fallback 仍遵守 Scope。
```

### Q1：ScopeGuard 和拒答闭环

目标：先保证不越界、不乱答。

任务：

```text
Q1.1 调用 RetrievalScopeService.build_scope_guard。
Q1.2 空 scope / 空 evidence 使用 empty_reason 生成拒答。
Q1.3 实现 validate_answer_against_scope。
Q1.4 LLM 输出越界 paper/evidence 时过滤并写 warning。
Q1.5 低质量证据触发 uncertainty。
```

验收：

```text
Scope 内只有 p1 时，回答不能引用 p2。
evidence 为空时不生成泛化答案。
越界 evidence_id 被过滤并记录 validation_warnings。
```

### Q2：EvidenceRetriever 与上下文诊断

目标：从“全量塞 evidence”升级为可解释 top-k 检索。

任务：

```text
Q2.1 实现 ScoredEvidence。
Q2.2 实现 keyword/field score。
Q2.3 intent 到字段加权。
Q2.4 retrieve_context 返回 top_k evidence。
Q2.5 返回 retrieval_diagnostics。
Q2.6 _build_evidence_summary 改为基于 selected_evidence。
```

验收：

```text
limitation 问题优先命中 limitation evidence。
method 问题优先命中 method evidence。
top_k 参数生效。
检索排序稳定。
```

### Q3：结构化生成和引用校验

目标：让 LLM 输出可验证的引用。

任务：

```text
Q3.1 升级 QA_SYSTEM_PROMPT，强制输出 supporting_evidence_ids。
Q3.2 generate_answer 解析 key_points/source_quotes/confidence。
Q3.3 citation validation 校验 evidence_id/paper_id/source_quote。
Q3.4 QAResponse 写入 source_quotes/retrieval_diagnostics/validation_warnings。
Q3.5 JSON parse failure 有降级策略。
```

验收：

```text
回答包含 evidence_ids。
无效 citation 被清理。
JSON 解析失败不会导致越界引用。
```

### Q4：GraphRAG 与路径解释

目标：支持图谱节点、子图和路径型 QA。

任务：

```text
Q4.1 graph_subgraph scope 使用 graph_context。
Q4.2 question 匹配 graph node label。
Q4.3 related_evidence_ids 加入检索候选并加权。
Q4.4 对 paper_compare / gap_analysis 填充 graph_paths。
Q4.5 回答中展示路径解释和对应证据。
```

验收：

```text
基于 Topic 节点提问能检索 related evidence。
两个 Paper 之间能返回 graph path。
Graph path 不会替代 evidence citation。
```

### Q5：QA 历史、素材和评估

目标：形成可复盘、可评估的 QA 工作流。

任务：

```text
Q5.1 保存 qa_history。
Q5.2 支持 qa_sessions。
Q5.3 支持保存回答为 review_material / innovation_material。
Q5.4 增加 golden QA cases fixture。
Q5.5 增加 evaluate qa 脚本或 evaluation.py 函数。
```

验收：

```text
QA history 可按 project/session 查询。
保存素材记录 scope/evidence。
golden cases 可计算 intent/context/scope 指标。
```

### Q6：Hybrid RAG 增强

目标：提升大范围和复杂问题检索质量。

任务：

```text
Q6.1 增加 BM25。
Q6.2 预留 vector retriever。
Q6.3 预留 reranker。
Q6.4 增加 Query Decomposition。
Q6.5 增加 CRAG retrieval quality check。
Q6.6 增加 context budget 分批策略。
```

验收：

```text
大范围问题 context_precision 提升。
复杂比较问题能分子问题检索。
检索质量低时能拒答或建议调整范围。
```

## 20. 测试计划

### 20.1 测试文件

```text
tests/agents_v3/research_workspace/test_scope_qa.py
tests/agents_v3/research_workspace/test_scope_qa_intents.py
tests/agents_v3/research_workspace/test_scope_qa_refusal.py
tests/agents_v3/research_workspace/test_scope_qa_guard.py
tests/agents_v3/research_workspace/test_scope_qa_retrieval_ranking.py
tests/agents_v3/research_workspace/test_scope_qa_context_budget.py
tests/agents_v3/research_workspace/test_scope_qa_citations.py
tests/agents_v3/research_workspace/test_scope_qa_graph_paths.py
tests/agents_v3/research_workspace/test_scope_qa_history.py
tests/agents_v3/research_workspace/test_scope_qa_evaluation_cases.py
```

### 20.2 关键测试

Scope 和拒答：

```text
Scope 内只有 paper_1 时，答案不能引用 paper_2。
空 scope 返回 refusal_reason。
empty evidence 不触发全项目 fallback。
证据不足时 suggested_actions 包含 generate_evidence_table 或 adjust_scope。
```

检索：

```text
limitation 问题优先命中 limitation evidence。
method compare 问题返回 method + finding + limitation evidence。
rejected evidence 不进入默认上下文。
top_k 限制生效。
相同输入多次检索顺序稳定。
```

生成和校验：

```text
LLM 输出越界 evidence_id 时被过滤。
LLM 输出不存在 paper_id 时被过滤。
JSON 解析失败时有 fallback 和 warning。
source_quote 必须对应 evidence_id。
```

GraphRAG：

```text
graph_subgraph scope 返回 graph_context。
related_evidence_ids 被纳入候选。
paper_compare 问题返回 graph_paths。
```

历史和评估：

```text
QA history 被保存。
session_id 可复用。
golden case 计算 context_recall。
scope_violation_count 为 0。
```

## 21. 验收标准

P0/Q0-Q3 完成后：

```text
1. QA 必须先 resolve scope。
2. retrieve_context 只返回 scope 内 evidence/cards/graph。
3. evidence 检索有 score、top_k 和 diagnostics。
4. prompt 要求输出 supporting_evidence_ids/supporting_paper_ids。
5. 回答后用 ScopeGuard 校验引用。
6. 空范围、空证据、低质量证据时不编造。
7. 测试不依赖真实 LLM API。
```

P1/Q4-Q5 完成后：

```text
1. graph_subgraph QA 可用。
2. graph_paths 可填充路径和证据。
3. QA history 可保存和查询。
4. 回答可保存为综述/创新点素材。
5. golden QA cases 可本地评估。
```

P2/Q6 完成后：

```text
1. 支持 BM25 / vector / reranker 混合检索。
2. 支持复杂问题分解。
3. 支持 CRAG 风格检索质量判断。
4. RAG 评估指标进入质量门禁。
```

## 22. 最小实现顺序

推荐顺序：

```text
1. 注入 fake LLM，稳定测试。
2. 接入 ScopeGuard。
3. 修空范围和空证据拒答。
4. 实现 ScoredEvidence 和 top-k。
5. 加 retrieval_diagnostics。
6. 强化 LLM 输出 schema。
7. 加 citation validation。
8. 保存 QAHistory。
9. 接 graph_context 和 graph_paths。
10. 加 golden cases。
```

不要优先做：

```text
完整向量数据库
复杂 Agent 编排
HyDE
多用户 QA 协作
联网搜索补充回答
全文级超长上下文问答
```

这些能力会增加复杂度，但不能先解决当前最关键的风险：Scope 越界、证据不排序、引用不可校验。

## 23. 风险与应对

| 风险 | 表现 | 应对 |
| --- | --- | --- |
| Scope 越界 | LLM 输出范围外论文 | ScopeGuard 后校验 |
| 幻觉引用 | 输出不存在的 evidence_id | citation validation |
| 检索噪声 | Scope 内证据全量塞入 | EvidenceRetriever top-k |
| 低质量证据误导 | low/rejected evidence 被使用 | quality filter + 降权 |
| 空范围乱答 | 没有证据仍生成 | refusal policy |
| 测试不稳定 | 真实 LLM 调用 | FakeLLM 注入 |
| 上下文过大 | 大范围全部放入 prompt | token budget + top-k |
| 图谱误用 | 路径被当事实 | GraphRAG 只解释关系，事实需 evidence |

## 24. 参考文档

本地调研：

```text
docs/research/11-产品方案与开发/当前产品方案.md
docs/research/11-产品方案与开发/当前开发计划.md
docs/research/14-细致开发计划/模块级开发计划/06-证据表模块.md
docs/research/14-细致开发计划/模块级开发计划/07-知识图谱模块.md
docs/research/14-细致开发计划/模块级开发计划/08-RetrievalScope模块.md
docs/research/14-细致开发计划/模块级开发计划/10-综述生成模块.md
docs/research/14-细致开发计划/模块级开发计划/15-评估日志监控模块.md
docs/research/10-学术QA系统/智能问答Agent学术QA综合调研报告.md
docs/research/10-知识图谱/RAG与知识图谱检索评估标准调研报告.md
docs/research/12-优化方案/文献综述Token消耗与上下文容量分析报告.md
```

外部参考：

```text
RAGAS Metrics:
https://docs.ragas.io/

Microsoft GraphRAG:
https://microsoft.github.io/graphrag/

LlamaIndex GraphRAG:
https://docs.llamaindex.ai/en/stable/examples/cookbooks/GraphRAG_v2/

Self-RAG:
https://github.com/AkariAsai/self-rag

LangChain RAG:
https://python.langchain.com/docs/tutorials/rag/
```

## 25. 研究借鉴增强

### 25.1 Contextual Retrieval 集成（借鉴 Anthropic）

Anthropic 的 Contextual Retrieval 是当前最先进的 RAG 检索优化方案：

```text
效果数据：
  - 仅 Contextual Embeddings → 减少 35% 失败检索
  - + BM25 混合检索 → 减少 49% 失败检索
  - + Reranking → 减少 67% 失败检索
```

本项目落地：

```text
P0（当前）：
  字段打分 + intent 匹配 + evidence_strength 加权

P1（BM25 集成）：
  1. 对 Scope 内 EvidenceRecord 构建 BM25 索引
  2. 查询：question + intent keywords
  3. 融合：field_score * 0.4 + BM25_score * 0.4 + quality_score * 0.2
  4. 不需要向量库，纯 Python 实现（rank_bm25 库）

P1（Contextual 增强）：
  1. EvidenceRecord 的 claim_text 生成时 prepend 上下文摘要
  2. 上下文格式：”[论文标题][章节类型][主题] {claim_text}”
  3. 与 PaperChunk 的 context 字段对齐

P2（Hybrid + Reranking）：
  1. BM25 候选 50 + Vector 候选 50
  2. RRF (Reciprocal Rank Fusion) 融合
  3. Cross-encoder rerank top 20
  4. Graph proximity 加权
```

### 25.2 幻觉检测集成（借鉴 LettuceDetect）

产品方案要求使用 LettuceDetect 进行 token-level 幻觉检测：

```text
技术选型：
  - 模型：LettuceDetect-v0.1（ModernBERT-based）
  - 精度：F1=79.22%（RAGTruth 数据集）
  - 大小：tiny variants 17-68M 参数
  - 许可：MIT 开源
  - 部署：HuggingFace 直接加载

集成位置：
  - QA 回答后、返回前
  - 综述生成后、返回前
  - 创新点报告生成后、返回前

输出：
  - hallucination_ratio: 幻觉 token 占比
  - h_v_ratio: 幻觉断言 / 总断言（目标 < 0.1）
  - 标记 high_hallucination_risk 时触发 uncertainty 提升或拒答
```

### 25.3 反证检测（借鉴 PapersFlow Critic Agent）

PapersFlow 的 Critic Agent 专门寻找反对证据，避免只展示支持证据的偏见。

本项目落地：

```text
1. 在 generate_answer() 后新增 _search_counter_evidence() 步骤
2. 在 Scope 内搜索与 key_points 矛盾的 evidence
3. 搜索条件：evidence_direction == “contrasting” 或 Finding CONTRADICTS Finding 边
4. 反证结果写入 QAResponse.counter_evidence
5. 如果存在反证，uncertainty 自动提升，confidence 下调
```

### 25.4 Review-Revise 循环（借鉴 GPT-Researcher）

GPT-Researcher 的 Review-Revise 循环确保输出质量：

```text
WriterAgent 生成初稿
  -> ReviewerAgent 审查（结构完整性、证据覆盖、引用准确性、逻辑连贯性）
  -> RevisorAgent 根据审查意见修订
  -> 可配置迭代轮数（默认 1 轮）
```

本项目落地（P1）：

```text
1. generate_answer() 生成初版回答
2. _review_answer() 检查：
   - 是否所有 key_points 都有 evidence_id
   - 是否存在 scope 外引用
   - 是否存在未验证断言
   - uncertainty 是否充分
3. 如果 review 发现问题，_revise_answer() 修订
4. 最大迭代 1 轮（避免过度消耗 token）
```

### 25.5 上下文压缩（借鉴 GPT-Researcher）

大范围论文（>20 篇）的 QA 上下文可能超出 token 限制：

```text
方案：
  1. 按 topic 对 evidence 分组
  2. 每组取 top evidence（按 score）
  3. 组内低分 evidence 用摘要替代全文
  4. 总 context 控制在 max_context_tokens 以内

分层压缩策略（借鉴 Token 调研）：
  - L0 元数据：始终包含（论文标题、作者、年份）
  - L1 摘要：大范围时用摘要替代 PaperCard 全文
  - L2 PaperCard：中等范围
  - L3 EvidenceRecord：精确问答
  - L4 source_quote：深度引用
```

### 25.6 透明报告元数据（借鉴 PRISMA-trAIce）

产品方案要求 QA 和报告记录透明元数据：

```text
QA 响应元数据：
  - prompt_version: 使用的 prompt 版本
  - scope_snapshot: 范围快照（paper_ids、evidence_ids）
  - retrieval_snapshot: 检索结果快照（candidate_count、selected_count、scores）
  - model_info: LLM 模型和参数
  - validation_result: ScopeGuard 校验结果
  - hallucination_check: LettuceDetect 检测结果
  - verification_result: Chain of Verification 结果
  - h_v_ratio: 幻觉/验证比
  - generated_at: 生成时间
```

## 当前代码对齐深化（2026-06-01）

### 当前实现确认

```text
scope_qa.py（451 行）当前包含 ScopeQAService，已实现：
  - answer() — 主入口：resolve scope → classify intent → retrieve → generate → validate → save
  - classify_intent() — 9 种规则意图分类
  - retrieve_context() — Scope 内 evidence/cards/graph 聚合
  - _score_evidence() — 字段打分排序（intent 匹配 + 关键词 + strength + source_quote）
  - generate_answer() — LLM JSON 结构化输出
  - _validate_response() — ScopeGuard 基础校验
  - _save_qa_history() — QA 历史保存
  - _fallback_answer() — LLM 失败时规则降级

API 层已有 ask_question 路由。
evaluation/evaluator.py 已有 refusal_correctness_check、citation_coverage_check 等评估函数。
vector_storage.py 已存在但配置默认 vector_storage: none。
```

### 与产品方案的 Gap 分析

| 产品方案要求 | 代码现状 | Gap 严重度 |
| --- | --- | --- |
| BM25 混合检索 | 仅有字段打分，无 BM25 | 高（检索质量） |
| Contextual Retrieval | 未实现 | 高（检索质量） |
| LettuceDetect 幻觉检测 | 未实现 | 高（输出可信度） |
| Chain of Verification | 未实现 | 高（输出可信度） |
| H/V ratio 质量指标 | 未实现 | 中（质量监控） |
| Review-Revise 循环 | 未实现 | 中（输出质量） |
| 反证检测 | 未实现 | 中（避免偏见） |
| 上下文压缩 | 未实现 | 中（大范围论文） |
| Context budget 控制 | 未实现 | 中（token 控制） |
| GraphRAG local/global | 仅有基础 graph_context | 中（图谱增强） |
| 透明报告元数据 | 已有基础 diagnostics | ⚠️ 部分对齐 |
| ScopeGuard 完整校验 | 已有基础校验 | ⚠️ 部分对齐 |

### 下一步深化任务

```text
优先级 P0（阻塞 QA 质量）：
1. 增强 _score_evidence()：加入 review_status 过滤（rejected 排除）、evidence_direction 加权
2. 实现 Context budget 控制：max_context_tokens 参数，超出时按 score 截断
3. 增强 ScopeGuard：校验 source_quote 是否来自 context 中的 evidence
4. 实现 Retrieval diagnostics 增强：low_confidence_count、excluded_by_scope_count

优先级 P1（增强检索和可信度）：
5. 实现 BM25 检索：使用 rank_bm25 库对 evidence claim_text 做 BM25 打分
6. 实现 Contextual 增强：claim_text prepend 上下文摘要
7. 集成 LettuceDetect：QA 回答后 token-level 幻觉检测
8. 实现 Chain of Verification：key_points 逐条验证
9. 实现 H/V ratio 计算并写入 response metadata
10. 实现反证检测：在 Scope 内搜索 CONTRADICTS 证据

优先级 P2（高级能力）：
11. 实现 Review-Revise 循环（1 轮）
12. 实现上下文压缩（按 topic 分组截断）
13. 实现 Hybrid Retrieval（BM25 + Vector + RRF + Rerank）
14. 实现 GraphRAG local/global 上下文增强
```

### 验收证据

```text
pytest tests/agents_v3/research_workspace/test_scope_qa.py 通过。
pytest tests/agents_v3/research_workspace/test_evaluation.py 通过相关 QA 评估。
新增测试覆盖：
  - 证据不足拒答
  - 引用越界失败
  - vector_storage none 路径可用
  - BM25 检索结果正确性
  - LettuceDetect 幻觉标记
  - Chain of Verification 状态正确
  - H/V ratio 计算正确
  - 反证检测结果正确
```

### 风险与阻塞

```text
QA 最主要风险是”看似合理但不在 Scope 内”。ScopeGuard、citation coverage 和 refusal correctness 必须成为默认门禁。
向量检索启用前，不应让系统对 ChromaDB 形成硬依赖。
LettuceDetect 模型部署需要额外依赖（transformers + torch），MVP 可先用规则降级。
BM25 索引在 evidence 数量大时可能有性能问题，需要评估是否需要持久化索引。
Chain of Verification 增加 LLM 调用次数，需要控制 token 成本。
```
