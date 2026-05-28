# 论文知识库分析 Agent 细致开发计划

更新日期：2026-05-28

本文档基于 `docs/research` 调研结果和当前 `src/agents_v3/research_workspace` 实现状态生成，用于指导下一阶段开发。本文只规划“开发计划中必须落地的部分”，不扩展到论文代写、润色降重、复杂协作、重型图数据库等非 MVP 能力。

## 1. 产品闭环

目标产品：

```text
论文知识库分析 Agent
```

核心闭环：

```text
研究项目
  -> 论文库
  -> 论文搜索 / 上传 / 导入
  -> PDF 解析和分块
  -> 论文卡片
  -> 证据表
  -> 轻量知识图谱
  -> 范围选择 Scope
  -> Scope-based QA
  -> 文献综述
  -> 创新点报告
  -> Markdown 导出和来源追踪
```

MVP 成功标准：

- 用户能创建研究项目并构建 20 到 30 篇论文的项目论文库。
- 系统能把论文转成可追踪的 `PaperCard`、`EvidenceRecord` 和 `KnowledgeGraph`。
- 用户能基于论文、主题、方法、年份或图谱子图选择回答范围。
- QA、综述、创新点报告都必须声明范围，并返回论文、证据记录或图谱节点来源。
- 当证据不足时，系统必须明确说明不确定性，不能编造结论。

## 2. 当前代码基线

当前实现目录：

```text
src/agents_v3/research_workspace/
tests/agents_v3/research_workspace/
```

当前已有模块：

| 模块 | 当前状态 | 后续重点 |
| --- | --- | --- |
| `models.py` | 已有核心 Pydantic 模型 | 补充任务状态、搜索源、引用、评估字段。 |
| `storage.py` | 已有 JSON 文件存储 | 修正全局 singleton 注入问题，补齐并发写保护和集合命名规范。 |
| `project_service.py` | 已有项目 CRUD 和统计 | 补齐删除级联、项目状态、演示项目初始化。 |
| `paper_library.py` | 已有上传、元数据导入、BibTeX 初版 | 补齐真实搜索源、去重、导入解析、上传校验。 |
| `parser_service.py` | 已有 pdfplumber 解析和简单分块 | 补齐章节识别、参考文献、元数据、失败重试。 |
| `paper_card.py` | 已有 LLM + fallback 卡片生成 | 补齐 JSON schema 校验、来源片段覆盖率、质量评分。 |
| `evidence_table.py` | 已有卡片转证据 | 补齐证据强度、过滤、排序和来源一致性检查。 |
| `graph_service.py` | 已有轻量图谱构建和子图查询 | 补齐实体归一化、gap 检测、图谱来源追踪。 |
| `scope.py` | 已有 Scope 解析 | 补齐越界防护、范围摘要、UI 所需过滤器。 |
| `scope_qa.py` | 已有意图分类、上下文检索、回答生成 | 补齐混合检索、拒答逻辑、证据覆盖率评估。 |
| `review_generator.py` | 已有综述生成和校验 | 补齐批处理、引用格式、结构完整性检查。 |
| `innovation_generator.py` | 已有 gap 信号、候选创新点和评分 | 补齐反证、可行性约束、泛化建议过滤。 |
| `report_service.py` | 已有保存、版本、Markdown 导出 | 补齐报告版本差异、导出元数据和来源索引。 |
| `llm_service.py` | 已有 LLM 调用和 JSON 调用 | 补齐重试、超时、模型配置、token 统计和日志脱敏。 |

当前最大缺口：

```text
1. 缺少真实多源学术搜索接入。
2. PDF 解析仍偏简化，章节、参考文献和来源定位不够稳定。
3. QA 和报告生成已有雏形，但检索、证据约束和质量门禁还不够严格。
4. API 和前端联调尚未形成完整演示闭环。
5. 监控、评估、任务状态和长任务进度还缺少统一机制。
```

## 3. 开发原则

### 3.1 MVP 优先级

P0 必须只服务一个目标：

```text
把一批论文变成可问、可查、可追溯的综述和创新点报告。
```

P0 不做：

- 全文论文代写。
- 润色、降重、答辩 PPT。
- 重型 Neo4j 或复杂 GraphRAG。
- 多用户协作和权限系统。
- 完整插件市场。

### 3.2 技术路线

| 方向 | MVP 方案 | 后续增强 |
| --- | --- | --- |
| Agent 协议 | 本地 service + prompt 模板 | MCP 工具边界，A2A 后置。 |
| 学术搜索 | 多源 adapter 接口，先接 arXiv/OpenAlex/CrossRef 中 1 到 2 个 | Semantic Scholar、PubMed、镜像源和队列调度。 |
| PDF 解析 | pdfplumber + 章节规则 + chunk | GROBID、PyMuPDF、多解析器 fallback。 |
| 检索 | Evidence + PaperCard + 图谱上下文 | BM25 + vector + rerank。 |
| 图谱 | JSON 轻量图谱 | Neo4j 或 GraphRAG。 |
| 记忆 | 项目状态、报告版本、任务 checkpoint | 用户长期偏好记忆。 |
| 前端进度 | 任务状态轮询或 SSE | AG-UI 事件流。 |
| 评估 | 本地 golden case + 结构校验 | RAGAS、自动回归评估和仪表盘。 |

## 4. 阶段路线图

| 阶段 | 名称 | 目标 | 建议周期 |
| --- | --- | --- | --- |
| Phase 0 | 工程稳定化 | 固化 v3 模块、测试隔离、日志规范。 | 1 到 2 天 |
| Phase 1 | 论文入库和搜索 | 支持上传、导入、搜索、去重和论文状态管理。 | 3 到 5 天 |
| Phase 2 | 解析、卡片和证据 | 生成可追踪的 chunks、cards、evidence。 | 4 到 6 天 |
| Phase 3 | 图谱和 Scope | 构建轻量知识图谱，支持范围选择和越界防护。 | 3 到 5 天 |
| Phase 4 | Scope QA | 基于范围回答问题，返回证据和不确定性。 | 4 到 6 天 |
| Phase 5 | 综述和创新点报告 | 生成正式成果物，支持版本和 Markdown 导出。 | 4 到 6 天 |
| Phase 6 | API 和前端闭环 | 四个主页面联调，跑通演示项目。 | 5 到 7 天 |
| Phase 7 | 评估、监控和优化 | 建立质量门禁、日志、token 和性能控制。 | 2 到 4 天 |

## 5. Phase 0：工程稳定化

目标：

```text
确保 research_workspace 可以作为后续开发主线，测试不污染真实 data，服务可注入、可观测、可回归。
```

需要改动：

| 文件 | 任务 |
| --- | --- |
| `storage.py` | 让 `get_storage(data_dir)` 在测试中可重置或移除全局污染。 |
| `project_service.py` | 支持注入 `JSONStorage`，补齐删除项目时相关数据清理策略。 |
| 所有 service | 构造函数支持 `storage: JSONStorage | None = None`，便于测试和 API 层复用。 |
| `__init__.py` | 明确导出稳定服务和模型。 |
| `tests/agents_v3/research_workspace` | 增加 fixture，统一临时目录和测试数据。 |

具体任务：

```text
T0.1 为所有 service 增加 storage 注入参数。
T0.2 增加 tests fixture：tmp_storage、sample_project、sample_paper、sample_card。
T0.3 清理测试中对真实 data/research_workspace 的依赖。
T0.4 增加端到端 smoke test：project -> paper -> card -> evidence -> graph -> qa -> report。
T0.5 增加 README 或模块说明，说明 v3 是当前开发主线。
```

验收标准：

```text
pytest tests/agents_v3/research_workspace 通过。
测试不会写入真实 data/research_workspace。
所有 service 可以在临时 storage 上运行。
research_workspace 模块可稳定 import。
```

## 6. Phase 1：论文入库、搜索和去重

调研依据：

- 学术搜索应支持多来源，至少覆盖 arXiv、OpenAlex、Semantic Scholar、CrossRef、PubMed 的可扩展接口。
- 搜索必须有 rate limit、retry/backoff、缓存和去重。
- 去重优先级：DOI > arXiv ID > 标准化标题 + 年份 + 作者。
- arXiv 需要保守请求节奏、尊重 `Retry-After`、缓存结果和失败 fallback。

### 6.1 模块设计

新增或改造文件：

```text
src/agents_v3/research_workspace/search/
  __init__.py
  base.py
  arxiv_client.py
  openalex_client.py
  crossref_client.py
  dedup.py
  rate_limit.py
  cache.py

src/agents_v3/research_workspace/paper_library.py
```

核心对象：

```python
class SearchQuery:
    query: str
    year_from: int | None
    year_to: int | None
    sources: list[str]
    limit: int

class SearchResult:
    title: str
    authors: list[str]
    year: int | None
    abstract: str
    doi: str
    arxiv_id: str
    url: str
    pdf_url: str
    source: str
```

### 6.2 需要补齐的能力

| 能力 | P0 任务 | P1 增强 |
| --- | --- | --- |
| 上传 PDF | 校验 PDF、保存路径、生成 paper 记录 | 文件 hash 去重、原文件名保留。 |
| DOI 导入 | DOI 标准化、创建占位记录 | CrossRef 拉取元数据。 |
| BibTeX/RIS 导入 | 稳定解析 title、author、year、doi、venue | 支持更多字段和异常报告。 |
| 关键词搜索 | 先接 arXiv 或 OpenAlex 一个真实源 | 多源并行搜索、融合排序。 |
| 去重 | DOI、arXiv ID、标题归一化 | 作者相似度、年份容错。 |
| 缓存 | 以 query + source 作为缓存 key | 过期时间和手动刷新。 |
| 速率控制 | 每个 source 独立限速 | 失败退避、Retry-After。 |

### 6.3 API 计划

```text
POST /api/rw/projects/{project_id}/papers/upload
POST /api/rw/projects/{project_id}/papers/import/doi
POST /api/rw/projects/{project_id}/papers/import/bibtex
POST /api/rw/projects/{project_id}/papers/search
POST /api/rw/projects/{project_id}/papers/search/commit
GET  /api/rw/projects/{project_id}/papers
GET  /api/rw/papers/{paper_id}
PATCH /api/rw/papers/{paper_id}
POST /api/rw/papers/{paper_id}/include
POST /api/rw/papers/{paper_id}/exclude
```

### 6.4 测试计划

```text
test_paper_library.py
test_search_dedup.py
test_search_cache.py
test_arxiv_client.py
test_reference_import.py
```

验收标准：

```text
能上传 PDF 并保存 paper 记录。
能导入 DOI 列表和 BibTeX。
能调用至少一个真实搜索源或 mock 搜索 adapter。
同一 DOI / arXiv ID / 标题不重复入库。
搜索失败不会中断项目，返回可读错误。
```

## 7. Phase 2：PDF 解析、论文卡片和证据表

调研依据：

- PDF 解析应抽取元数据、章节、参考文献和 chunks。
- 不应直接把整篇 PDF 塞给模型生成综述。
- PaperCard 是 600 到 800 token 左右的单篇论文结构化摘要。
- EvidenceRecord 是 QA、综述和创新点的核心证据中间层。
- 结构化 LLM 输出必须用 Pydantic 校验，字段缺失时用 `unknown`，不能编造。

### 7.1 ParserService

需要改造：

| 文件 | 任务 |
| --- | --- |
| `parser_service.py` | 从简单段落分块升级为章节感知分块。 |
| `models.py` | 可选增加 `Reference`、`ParseResult`、`TaskStatus`。 |
| `storage.py` | 规范 chunks 集合命名，例如 `chunks_{paper_id}` 或统一 `paper_chunks`。 |

P0 解析字段：

```text
paper_id
title
authors
abstract
sections
references
chunks
page_number
section_title
start_char
end_char
token_count
```

分块规则：

```text
1. 优先按章节切分。
2. 每个 chunk 控制在 500 到 900 tokens。
3. 保留 page_number、section_title 和字符位置。
4. 摘要、方法、实验、结果、讨论、局限章节要尽量保留标题。
5. 解析失败时更新 paper.status=FAILED，并记录 error_message。
```

### 7.2 PaperCardGenerator

结构化输出：

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

质量规则：

```text
1. 每个核心字段至少有一个 source_span 或明确 unknown。
2. key_findings、limitations、future_work 必须能追溯到 chunk。
3. LLM JSON 输出必须通过 Pydantic 校验。
4. fallback 只作为开发和测试兜底，不作为最终质量来源。
5. confidence 不能固定写死，应由字段完整度和来源覆盖率计算。
```

### 7.3 EvidenceTableService

EvidenceRecord 生成规则：

```text
1. 每个 finding 生成一条 evidence。
2. 每个 limitation 生成一条 evidence。
3. future_work 和 possible_gaps 可以生成 gap seed evidence。
4. evidence 必须包含 paper_id、project_id、source_chunk_id 或 source_quote。
5. evidence_strength 默认 medium，但应允许根据来源章节和置信度调整。
```

### 7.4 测试计划

```text
test_parser_service.py
test_parser_sections.py
test_paper_card_generator.py
test_paper_card_schema.py
test_evidence_table_service.py
test_evidence_traceability.py
```

验收标准：

```text
能从 PDF 生成 chunks。
能从 chunks 生成 PaperCard。
能从 PaperCard 生成 EvidenceRecord。
每条 EvidenceRecord 可回到 paper_id 和 chunk 或 quote。
字段缺失时显示 unknown，不出现伪造内容。
```

## 8. Phase 3：知识图谱和 Retrieval Scope

调研依据：

- MVP 图谱用 JSON 轻量实现即可。
- 核心节点：Paper、Author、Topic、Task、Method、Dataset、Finding、Limitation、Gap、InnovationPoint。
- 核心关系：BELONGS_TO_TOPIC、USES_METHOD、USES_DATASET、REPORTS_FINDING、HAS_LIMITATION、SUGGESTS_GAP、SUPPORTS_INNOVATION、CITES。
- Scope 是 QA 和报告的范围控制边界。

### 8.1 GraphService

需要补齐：

```text
1. 实体归一化：同义 topic/method/dataset 合并。
2. 节点来源：每个非 Paper 节点记录 evidence_ids 和 paper_ids。
3. Gap 节点：从 limitation、future_work、possible_gaps 聚合生成。
4. 子图查询：支持 node_ids + hops，并返回节点、边和相关 papers。
5. 图谱统计：节点类型数量、边类型数量、孤立节点、gap 数量。
```

图谱构建规则：

```text
Paper -> BELONGS_TO_TOPIC -> Topic
Paper -> USES_METHOD -> Method
Paper -> USES_DATASET -> Dataset
Paper -> REPORTS_FINDING -> Finding
Paper -> HAS_LIMITATION -> Limitation
Limitation -> SUGGESTS_GAP -> Gap
Gap -> SUPPORTS_INNOVATION -> InnovationPoint
Paper -> CITES -> Paper
```

### 8.2 RetrievalScopeService

Scope 类型：

```text
all_project
selected_papers
topic_group
method_group
year_range
graph_subgraph
innovation_related
```

需要补齐：

```text
1. resolve 后必须得到 paper_ids、evidence_ids、graph_node_ids、summary。
2. 所有后续 QA 和报告只能使用 resolved scope 内的数据。
3. 如果 scope 为空，应返回明确错误或空范围说明。
4. year_range、topic_ids、method_ids 可以组合过滤。
5. graph_subgraph 支持 hops，但默认最多 2 跳。
```

### 8.3 API 计划

```text
POST /api/rw/projects/{project_id}/kg/build
GET  /api/rw/projects/{project_id}/kg
GET  /api/rw/projects/{project_id}/kg/stats
POST /api/rw/projects/{project_id}/kg/subgraph
POST /api/rw/projects/{project_id}/scope/resolve
GET  /api/rw/projects/{project_id}/scope/filters
```

### 8.4 测试计划

```text
test_graph_service.py
test_graph_entity_normalization.py
test_graph_gap_detection.py
test_retrieval_scope.py
test_scope_guard.py
```

验收标准：

```text
项目 evidence 能生成图谱。
图谱节点和边都有来源。
Scope 能解析出论文、证据和图谱上下文。
Scope 外论文不会进入 QA 或报告。
```

## 9. Phase 4：Scope-based QA 和 RAG

调研依据：

- QA 必须 scope-bound。
- MVP 可先用 Evidence + PaperCard + Graph context 检索，再升级 BM25 + vector + rerank。
- 回答必须包含范围声明、证据、支持论文、不确定性和建议动作。
- 证据不足时应拒答或降级回答。
- 评估指标包括 Context Precision、Context Recall、Faithfulness、Answer Relevance。

### 9.1 ScopeQAService

当前已有：

```text
classify_intent()
retrieve_context()
generate_answer()
answer()
```

需要补齐：

| 能力 | P0 | P1 |
| --- | --- | --- |
| 检索 | EvidenceRecord 关键词匹配 + topic/method 过滤 | BM25 + vector + rerank |
| 意图 | summary、method_compare、limitation_analysis、gap_analysis、evidence_check、innovation_seed、review_material | 多轮上下文和任务计划 |
| 范围防护 | 只加载 scope 内 paper/evidence | 自动检测越界引用 |
| 拒答 | evidence 少于阈值时说明不足 | 给出补充检索建议 |
| 来源 | 返回 supporting_papers、evidence_records、graph_paths | 引文定位和 quote 高亮 |

### 9.2 回答结构

`QAResponse` 必须包含：

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

回答生成规则：

```text
1. 开头说明当前回答范围。
2. 结论只能来自 scope 内 evidence 和 card。
3. 每个关键结论至少关联一条 evidence。
4. 不确定性必须写明原因，例如样本少、证据冲突、缺少实验细节。
5. suggested_actions 根据意图给出，例如生成综述、生成创新点、扩大范围、补充搜索。
```

### 9.3 测试计划

```text
test_scope_qa.py
test_scope_qa_refusal.py
test_scope_qa_citations.py
test_scope_qa_intents.py
test_rag_quality_cases.py
```

验收标准：

```text
选中 3 篇论文时，QA 不引用第 4 篇。
证据为空时，QA 不编造答案。
回答中有 scope_summary、supporting_papers、evidence_records。
至少支持 summary、method_compare、limitation_analysis、gap_analysis 四类问题。
```

## 10. Phase 5：文献综述和创新点报告

调研依据：

- 报告不能直接从全文 PDF 生成，应使用 PaperCard、EvidenceRecord 和 selected chunks。
- 30 篇论文可用卡片和证据生成综述；50 篇以上需要分批和检索。
- 创新点应来自图谱稀疏关系、共同局限、future work、方法迁移空间、数据集或场景空白、争议点。
- 每个创新点需要文献基础、研究空白、支撑证据、限制证据、可行性、风险和评分。

### 10.1 LiteratureReviewGenerator

默认结构：

```text
1. 研究背景
2. 主题划分
3. 代表性文献和研究脉络
4. 主要研究方法
5. 主要研究结论
6. 现有研究不足
7. 未来研究趋势
8. 参考文献
```

需要补齐：

```text
1. 按主题/方法/年份组织材料。
2. 每段关键观点关联 evidence_ids。
3. 生成前检查 scope 内论文数量和 evidence 数量。
4. 论文数量超过阈值时分批总结，再合并。
5. validate_review 检查结构完整性、来源覆盖率和空泛段落。
```

### 10.2 InnovationReportGenerator

创新点来源：

```text
图谱 gap 节点
多篇论文共同 limitation
future_work 聚合
方法迁移空间
数据集 / 场景空白
证据冲突或争议点
近年趋势
```

每个创新点输出：

```text
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

评分维度：

```text
Novelty
Evidence
Feasibility
Risk
Fit
```

泛化建议过滤：

```text
过滤“提高效率”“优化模型”“加强研究”“扩大样本”等没有具体文献 gap 的空泛表达。
每个创新点必须绑定至少 2 篇支撑论文或明确说明证据不足。
```

### 10.3 ReportService

需要补齐：

```text
1. 报告保存时记录 scope、paper_ids、evidence_ids、graph_node_ids。
2. Markdown 导出增加元信息块：项目、范围、论文数量、证据数量、生成时间。
3. 支持报告版本说明和版本差异摘要。
4. 支持把 QA 回答保存为报告素材。
```

### 10.4 测试计划

```text
test_review_generator.py
test_review_traceability.py
test_innovation_generator.py
test_innovation_generic_filter.py
test_report_service.py
test_report_export_markdown.py
```

验收标准：

```text
综述包含完整结构和参考来源。
创新点报告至少输出 3 个候选创新点。
每个创新点有支撑论文、gap、可行性和风险。
报告可以导出 Markdown。
报告元数据能追溯到 scope、paper_ids 和 evidence_ids。
```

## 11. Phase 6：API 和前端演示闭环

### 11.1 API 聚合层

建议新增：

```text
src/agents_v3/research_workspace/api.py
```

或接入项目现有 API 框架，保持路径前缀：

```text
/api/rw
```

端到端任务接口：

```text
POST /api/rw/projects/{project_id}/pipeline/ingest
POST /api/rw/projects/{project_id}/pipeline/analyze
POST /api/rw/projects/{project_id}/pipeline/build-graph
POST /api/rw/projects/{project_id}/pipeline/demo
GET  /api/rw/tasks/{task_id}
```

任务状态：

```text
queued
running
succeeded
failed
cancelled
```

任务事件：

```text
paper_uploaded
paper_parsed
card_generated
evidence_generated
graph_built
qa_answered
report_generated
error
```

### 11.2 前端四页

MVP 页面：

| 页面 | 必备功能 |
| --- | --- |
| 项目论文库 | 创建项目、上传 PDF、搜索/导入、论文列表、解析状态、include/exclude。 |
| 知识图谱 | 查看节点和边、筛选类型、选中节点/子图、查看来源。 |
| 研究 QA | 选择 Scope、提问、查看答案、证据来源、不确定性和建议动作。 |
| 成果报告 | 生成综述、生成创新点报告、查看版本、导出 Markdown。 |

前端体验要求：

```text
1. 每个长任务必须展示进度和失败原因。
2. 每个 QA 答案和报告段落必须能展开来源。
3. Scope 选择必须在页面上可见，避免用户误以为是全库回答。
4. 报告生成前展示使用论文数量和证据数量。
```

### 11.3 演示项目

演示主题：

```text
大语言模型与自主学习
```

演示路径：

```text
1. 创建项目。
2. 上传 5 到 10 篇 PDF。
3. 搜索补充到 20 篇左右。
4. 解析论文并生成卡片。
5. 生成证据表。
6. 构建知识图谱。
7. 选择“实证研究”或某个方法子图。
8. 提问：这些研究共同不足是什么？
9. 基于当前 Scope 生成创新点报告。
10. 基于全项目生成文献综述。
11. 导出 Markdown，并检查来源追踪。
```

验收标准：

```text
演示路径可以稳定复现。
前端能看到每一步状态。
QA 和报告能展开来源。
失败任务有可读错误，不是静默失败。
```

## 12. Phase 7：评估、监控和质量门禁

调研依据：

- 日志需要包含 request_id、task_id、project_id、paper_id。
- 应记录 latency、token usage、model、retries、evidence count、scope summary。
- 不能记录完整私有论文内容、API key 或完整 prompt。
- 长任务需要 checkpoint 和状态字段。
- QA/RAG 评估需要 Context Precision、Context Recall、Faithfulness、Answer Relevance。

### 12.1 日志规范

使用现有 Loguru，统一字段：

```text
request_id
task_id
project_id
paper_id
service
operation
status
latency_ms
model
token_input
token_output
retry_count
evidence_count
scope_summary
error_type
```

脱敏规则：

```text
不记录 API key。
不记录完整 PDF 文本。
不记录完整 prompt。
source_quote 默认截断。
用户上传文件路径只记录相对路径或 hash。
```

### 12.2 质量门禁

P0 门禁：

```text
1. 所有 Pydantic 模型校验通过。
2. QA 不允许引用 Scope 外论文。
3. 报告必须有 paper_ids 和 evidence_ids。
4. 创新点不能全部为空泛建议。
5. LLM JSON 解析失败必须 fallback 或返回可读错误。
6. PDF 解析失败不能中断整个项目批处理。
```

评估数据：

```text
tests/fixtures/research_workspace/
  mini_project.json
  sample_papers.json
  sample_cards.json
  sample_evidence.json
  golden_qa_cases.json
  golden_report_checks.json
```

评估脚本建议：

```text
scripts/evaluate_research_workspace.py
```

指标：

```text
Scope Guard Pass Rate
Evidence Coverage
Answer Citation Coverage
Report Traceability Rate
Innovation Specificity Rate
Parse Success Rate
Search Dedup Precision
```

## 13. 立即执行的前三个迭代

### Iteration 1：稳定当前 v3 闭环

目标：

```text
让现有最小闭环在测试环境稳定运行。
```

任务：

```text
1. 所有 service 支持 storage 注入。
2. 增加统一测试 fixture。
3. 增加端到端 smoke test。
4. 修正真实 data 目录污染。
5. 补齐错误状态和日志字段。
```

交付：

```text
pytest tests/agents_v3/research_workspace 通过。
端到端 smoke test 可跑通。
```

### Iteration 2：补齐真实论文入库和解析质量

目标：

```text
让用户能把真实论文导入项目，并得到可追踪 chunks、cards、evidence。
```

任务：

```text
1. 接入至少一个真实搜索源或稳定 mock adapter。
2. 实现 DOI / arXiv ID / 标题去重。
3. 改进 PDF 章节分块。
4. PaperCard 输出增加 schema 校验和 source coverage。
5. EvidenceRecord 增加 traceability 校验。
```

交付：

```text
10 篇真实或夹具论文可以批量解析。
每篇论文至少生成 1 张卡片和多条证据。
```

### Iteration 3：Scope QA、报告和演示闭环

目标：

```text
跑通用户可见的问答、综述、创新点报告和导出路径。
```

任务：

```text
1. 强化 Scope 越界防护。
2. QA 增加证据不足拒答。
3. 综述和创新点报告增加来源索引。
4. 实现 API 聚合层。
5. 前端四页完成最小联调。
6. 准备演示项目数据。
```

交付：

```text
从创建项目到导出 Markdown 的演示路径可复现。
QA、综述、创新点报告均可追溯来源。
```

## 14. 风险和应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 多源搜索 API 不稳定 | 论文入库失败 | adapter 解耦、缓存、mock 数据、失败降级。 |
| PDF 解析质量不稳定 | 卡片和证据质量下降 | 多解析器 fallback、章节规则、人工上传元数据补充。 |
| LLM 输出 JSON 不合规 | 生成链路中断 | Pydantic 校验、repair、fallback、错误可见。 |
| QA 越界引用 | 产品可信度下降 | Scope guard 单测、回答后校验、证据 ID 白名单。 |
| 报告空泛 | 不能作为正式成果物 | evidence coverage、创新点 specificity 检查。 |
| token 成本过高 | 批量综述不可用 | PaperCard + Evidence 优先，分批总结，禁止全文直塞。 |
| 前端状态不可见 | 用户误以为卡死 | task 状态、SSE/轮询、失败原因展示。 |

## 15. 最终交付定义

当以下条件满足时，可以认为“论文知识库分析 Agent MVP”完成：

```text
1. 用户能创建项目并导入/搜索论文。
2. 系统能解析论文并生成 PaperCard、EvidenceRecord、KnowledgeGraph。
3. 用户能选择 Scope 并进行 QA。
4. QA 返回范围声明、证据、论文来源和不确定性。
5. 系统能基于 Scope 生成文献综述。
6. 系统能基于 gap 和 evidence 生成创新点报告。
7. 报告能导出 Markdown。
8. 全流程有自动化测试和演示项目。
9. 日志能定位失败原因。
10. 不出现明显越界引用和无来源编造。
```
