# 论文知识库分析 Agent 统一开发计划

更新日期：2026-06-03

本文档是项目唯一的开发计划总控，融合了原「模块深化开发计划」和「细致开发计划」，基于当前代码实际状态编写。

## 1. 产品定义

目标产品：

```text
论文知识库分析 Agent
```

核心闭环：

```text
研究项目
  -> 论文库（论文搜索 / 上传 / 导入）
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
11. 关键链路有 [timing] 计时日志，能快速定位慢请求瓶颈。
12. LLM 和 Embedding 调用有延迟、token、失败率指标。
```

## 2. 当前代码基线

### 2.1 代码规模

```text
src/agents_v3/research_workspace/   — 76 个 Python 文件
tests/                              — HTTP API 集成测试（搜索 + 解析）
config.yaml                         — 统一配置
```

### 2.2 模块总览

| 子包 | 文件数 | 核心类 | 代码行数（约） | 状态 |
|------|--------|--------|--------------|------|
| `models/` | 7 | Paper, PaperChunk, GraphNode, EvidenceRecord, Report | 1200+ | 完整 |
| `storage/` | 7 | PostgresStorage, VectorStorage, EmbeddingProvider | 2000+ | 完整 |
| `search/` | 14 | 4 adapters, SearchOrchestrator, HybridRanker, Merger | 2500+ | 完整 |
| `parser/` | 5 | ParserService, 5 adapters, SectionExtractor | 2200+ | 完整 |
| `services/` | 11 | 11 个业务 Service | 6500+ | 完整 |
| `llm/` | 6 | LLMService, PromptRegistry, JSON repair | 800+ | 完整 |
| `evaluation/` | 5 | 7 evaluator, quality gates, metrics | 600+ | 完整 |
| `api/` | 14 | FastAPI app, 7 route modules, 28 endpoints | 1200+ | 完整 |
| 根目录 | 3 | config, utils, __init__ | 300+ | 完整 |

### 2.3 已实现的完整链路

```text
ProjectService                    — 项目 CRUD + 删除级联 + 统计
  → PaperLibraryService           — 论文池、多源搜索、DOI/BibTeX 导入、主题评分
  → ParserService                 — 5 解析器 fallback、章节分块、参考文献、自动向量化
  → PaperCardGenerator            — LLM 结构化抽取、来源验证、质量评分
  → EvidenceTableService          — 证据记录构建、scope 查询
  → GraphService                  — 类型化节点、别名归一、gap 聚合
  → RetrievalScopeService         — 6 种 scope 类型、越界防护
  → ScopeQAService                — 9 种意图、证据评分、LLM 回答
  → LiteratureReviewGenerator     — 证据矩阵、LLM 分节生成、Markdown 渲染
  → InnovationReportGenerator     — 信号收集、LLM 候选、多维评分、泛化过滤
  → ReportService                 — 报告 CRUD、版本管理、Markdown/JSON 导出
  → HierarchicalRetriever         — L0→L1→L2 三层渐进检索
  → FastAPI /api/rw               — 28 个端点、7 个路由模块
  → evaluation                    — 7 个评估函数、质量门禁、golden cases
```

### 2.4 存储架构

```text
PostgreSQL（主存储）:
  20 张表：projects, papers_pool, papers, paper_chunks, paper_cards,
  evidence_records, parse_results, graphs, reports, report_versions,
  tasks, qa_history, paper_references, citation_contexts, paper_sections,
  kg_nodes, kg_edges, queries, topic_scores, search_sessions, session_papers

Qdrant（向量存储）:
  5 个集合：paper_chunks, paper_profiles, search_queries,
  citation_contexts, paper_sections
  支持 dense (384维) + sparse (BM25) 混合检索
  支持本地 sentence-transformers 和云端 inference 两种模式

EmbeddingProvider（统一 embedding 接口）:
  LocalEmbeddingProvider  — 本地 sentence-transformers
  CloudEmbeddingProvider  — Qdrant Cloud inference API
  通过 config.yaml embedding.mode 切换
```

### 2.5 API 端点清单（28 个）

```text
健康检查:
  GET  /api/health

项目管理（6 个）:
  POST   /api/rw/projects
  GET    /api/rw/projects
  GET    /api/rw/projects/{project_ref}
  PATCH  /api/rw/projects/{project_ref}
  DELETE /api/rw/projects/{project_ref}
  GET    /api/rw/projects/{project_ref}/stats

论文管理（8 个）:
  GET    /api/rw/projects/{project_ref}/papers
  POST   /api/rw/projects/{project_ref}/papers/import/doi
  POST   /api/rw/projects/{project_ref}/papers/import/bibtex
  GET    /api/rw/projects/{project_ref}/papers/{paper_id}
  PATCH  /api/rw/projects/{project_ref}/papers/{paper_id}
  POST   /api/rw/projects/{project_ref}/papers/{paper_id}/include
  POST   /api/rw/projects/{project_ref}/papers/{paper_id}/exclude
  POST   /api/rw/projects/{project_ref}/papers/search

解析（4 个）:
  POST   /api/rw/projects/{project_ref}/papers/download
  POST   /api/rw/projects/{project_ref}/papers/{paper_id}/download
  POST   /api/rw/projects/{project_ref}/papers/{paper_id}/parse
  POST   /api/rw/projects/{project_ref}/papers/parse

知识提取（5 个）:
  POST   /api/rw/projects/{project_ref}/cards
  POST   /api/rw/projects/{project_ref}/evidence/build
  POST   /api/rw/projects/{project_ref}/kg/build
  GET    /api/rw/projects/{project_ref}/kg
  GET    /api/rw/projects/{project_ref}/kg/stats
  POST   /api/rw/projects/{project_ref}/kg/subgraph
  GET    /api/rw/projects/{project_ref}/kg/gaps

Scope 与 QA（3 个）:
  POST   /api/rw/projects/{project_ref}/scope/resolve
  GET    /api/rw/projects/{project_ref}/scope/filters
  POST   /api/rw/projects/{project_ref}/qa

报告（5 个）:
  GET    /api/rw/projects/{project_ref}/reports
  GET    /api/rw/projects/{project_ref}/reports/{report_id}
  POST   /api/rw/projects/{project_ref}/reports/literature-review
  POST   /api/rw/projects/{project_ref}/reports/innovation
  GET    /api/rw/projects/{project_ref}/reports/{report_id}/export/markdown
  GET    /api/rw/projects/{project_ref}/reports/{report_id}/export/json

任务（2 个）:
  GET    /api/rw/tasks/{task_id}
  GET    /api/rw/tasks
```

### 2.6 当前最大缺口

```text
1. 测试覆盖不足：tests/ 下只有搜索和解析的 HTTP 集成测试，缺少单元测试。
2. 搜索性能：外部 API + HybridRanker 云端 embedding 搜索耗时过长（>10 分钟）。
3. 性能监控缺失：关键链路无系统化计时，排查慢请求只能手动加 time.time()。
4. LLM 调用无指标：无延迟、token、失败率的结构化采集。
5. 前端未开始：只有后端 API，无前端页面。
```

## 3. 开发原则

### 3.1 MVP 优先级

P0 必须只服务一个目标：

```text
把一批论文变成可问、可查、可追溯的综述和创新点报告。
```

P0 不做：

```text
- 全文论文代写。
- 润色、降重、答辩 PPT。
- 重型 Neo4j 或复杂 GraphRAG。
- 多用户协作和权限系统。
- 完整插件市场。
```

### 3.2 技术路线

| 方向 | 当前方案 | 后续增强 |
|------|---------|---------|
| 存储 | PostgreSQL + Qdrant Cloud | 分库分表、读写分离 |
| 搜索 | 4 源并行（arXiv/OpenAlex/S2/EuropePMC） | CrossRef、PubMed、镜像源 |
| 解析 | 5 解析器 fallback + 章节分块 | GROBID、OCR 增强 |
| 检索 | L0→L1→L2 三层 + dense/sparse RRF | rerank、图谱增强检索 |
| Embedding | Qdrant Cloud inference / 本地 sentence-transformers | 更大模型、多语言 |
| 图谱 | JSON 轻量图谱（PostgreSQL 存储） | Neo4j 或 GraphRAG |
| LLM | LangChain + JSON repair pipeline | 多模型路由、流式输出 |
| 评估 | 7 evaluator + quality gates + golden cases | RAGAS、自动回归评估 |
| 监控 | 计划中（@timed 装饰器 + perf_report） | Sentry、Prometheus |

## 4. Sprint 路线图

| Sprint | 名称 | 目标 | 建议周期 |
|--------|------|------|---------|
| A | 测试体系建设 | 补齐单元测试，建立 CI 回归基础 | 3-5 天 |
| B | 搜索性能优化 | 解决搜索超时，优化 embedding 链路 | 2-3 天 |
| C | 解析与证据质量硬化 | 保证材料可追溯、有质量标签 | 3-5 天 |
| D | Scope、QA、报告可信度 | 证据不足时拒答，结果可追溯 | 3-5 天 |
| E | 性能监控与可观测性 | 系统化计时、LLM/Embedding 指标 | 2-3 天 |
| F | API 产品化与前端联调 | 长任务、错误诊断、前端四页 | 5-7 天 |
| G | 评估门禁与演示闭环 | E2E smoke、质量门禁、演示项目 | 3-5 天 |

## 5. Sprint A：测试体系建设

目标：

```text
补齐单元测试，建立 CI 回归基础。当前 tests/ 只有搜索和解析的 HTTP 集成测试。
```

任务：

```text
A1. 建立 tests/agents_v3/research_workspace/ 目录结构
A2. 为每个 service 编写单元测试（使用 FakeLLMService + 临时 PostgreSQL）
    - test_project_service.py
    - test_paper_library.py
    - test_parser_service.py
    - test_paper_card_generator.py
    - test_evidence_table_service.py
    - test_graph_service.py
    - test_retrieval_scope.py
    - test_scope_qa.py
    - test_review_generator.py
    - test_innovation_generator.py
    - test_report_service.py
A3. 为 storage 层编写测试
    - test_postgres_storage.py
    - test_vector_storage.py
    - test_embedding_provider.py
A4. 为 search 层编写测试
    - test_merger.py
    - test_dedup.py
    - test_hybrid_ranker.py
    - test_quality_filter.py
A5. 为 evaluation 层编写测试
    - test_evaluator.py
    - test_quality_gates.py
A6. 建立端到端 smoke test
    - test_e2e_smoke.py: project → paper → parse → card → evidence → graph → qa → report
A7. 配置 CI：pytest 自动运行所有测试
```

验收：

```text
pytest tests/ 通过（不含需要外部 API 的集成测试）。
每个 service 至少有 3 个测试用例（正常路径、异常路径、边界条件）。
E2E smoke test 覆盖完整闭环。
```

阻塞条件：

```text
FakeLLMService 不能覆盖所有 LLM 调用场景。
PostgreSQL 测试环境搭建困难。
```

## 6. Sprint B：搜索性能优化

目标：

```text
解决搜索超时问题。当前外部 API + HybridRanker 云端 embedding 搜索耗时 >10 分钟。
```

问题诊断：

```text
1. 外部 API 搜索（4 源并行）：单个源可能超时 30-60s
2. HybridRanker 云端 embedding：每次 embed_query/embed_texts 需要 2-4s（临时集合创建/upsert/scroll/删除）
3. HybridRanker 需要 6 次 embedding 调用：query dense, query sparse, papers dense, papers sparse × 2
4. 总 embedding 耗时：约 20-30s
5. 外部 API + embedding 叠加：可能超过 5 分钟
```

任务：

```text
B1. 搜索链路计时（已部分实现）
    - search_papers 方法已加 [timing] 日志
    - 需要重启服务验证实际耗时分布

B2. HybridRanker 优化
    - 云端模式下合并 dense+sparse 为单次 hybrid 调用（减少临时集合创建次数）
    - 考虑批量 embedding 缓存：相同文本不重复编码
    - 考虑云端模式跳过 fit_sparse（已是 no-op）和本地 TF-IDF 逻辑

B3. 外部 API 超时控制
    - 每个 adapter 设置独立超时（默认 15s）
    - 超时的 adapter 返回空结果 + 错误信息，不阻塞其他 adapter
    - 搜索响应包含 source_stats 和 errors

B4. 搜索结果缓存
    - 相同 query + sources 的结果缓存 1 小时
    - 缓存命中时跳过 HybridRanker（已有排序结果）

B5. 云端 embedding 性能优化
    - 评估是否可以用 Qdrant Cloud 的 query_points + Document 直接查询（避免临时集合）
    - 批量 embedding 合并：多条文本放入同一个临时集合
```

验收：

```text
搜索 "BERT pre-training" limit=5 耗时 < 60s。
搜索超时时返回部分结果 + 错误信息。
HybridRanker 云端模式 embedding 调用次数减少 50%。
```

## 7. Sprint C：解析与证据质量硬化

目标：

```text
保证进入 QA/综述/创新点的材料都有可追溯来源和质量标签。
```

任务：

```text
C1. ParserService 质量固化
    - ParseResult.status 更新规则：success / failed / partial
    - quality_flags 持久化到 parse_results 表
    - 低质量解析（乱码率 > 阈值）标记为 failed

C2. PaperCard 质量门禁
    - quality_report 持久化到 paper_cards 表 metadata
    - source_spans 校验：每个核心字段至少一个 source_span 或明确 unknown
    - confidence 由字段完整度和来源覆盖率计算，不能写死

C3. EvidenceRecord 增强
    - metadata 记录 evidence_type / review_status / confidence
    - EvidenceTableService 不接受 excluded paper 的 evidence
    - 证据构建后输出项目级统计

C4. 图谱来源追踪
    - 每个非 Paper 节点记录 evidence_ids 和 paper_ids
    - Gap 节点必须绑定支撑的 limitation 节点
```

验收：

```text
解析失败的论文 status = failed，不进入后续流程。
PaperCard 每个核心字段有来源或标记 unknown。
EvidenceRecord 全部有 paper_id 和 project_id。
图谱节点可追溯到 evidence。
```

## 8. Sprint D：Scope、QA、报告可信度

目标：

```text
让所有生成结果都能说明"基于哪些论文/证据/图谱范围"，证据不足时明确拒答或降级。
```

任务：

```text
D1. RetrievalScopeService 增强
    - 输出 empty_reason、scope_summary、filter_diagnostics
    - scope 为空时返回明确错误

D2. ScopeGuard 贯穿
    - QA、Review、Innovation、Report 保存前都调用 ScopeGuard
    - scope 外论文不允许进入回答或报告

D3. QA 拒答逻辑
    - evidence 少于阈值时说明不足，不编造答案
    - supporting_papers/evidence_records 必须在 scope 内

D4. 综述来源覆盖
    - section_sources 覆盖主体章节
    - 每段关键观点关联 evidence_ids

D5. 创新点约束
    - 每个候选绑定 gap / supporting_papers / limiting_evidence
    - 过滤"提高效率""优化模型"等空泛建议

D6. 报告可追溯
    - 保存时写入 scope_snapshot、source_snapshot、validation_result
    - Markdown 导出包含 scope、paper list、evidence index、warnings
```

验收：

```text
选中 3 篇论文时，QA 不引用第 4 篇。
证据为空时，QA 不编造答案。
综述和创新点报告有来源索引。
```

## 9. Sprint E：性能监控与可观测性

目标：

```text
在单服务架构下，建立轻量级性能监控体系，能快速定位慢请求和瓶颈步骤。
```

新增文件：

```text
src/agents_v3/research_workspace/monitoring/
  __init__.py
  timer.py            # @timed 装饰器 + TimingContext
  llm_metrics.py      # LLM 调用指标采集
  embed_metrics.py    # Embedding 调用指标采集
  request_middleware.py  # FastAPI 请求耗时 middleware

scripts/
  perf_report.py      # 日志解析 + 统计报告
```

任务：

```text
E1. @timed 装饰器
    - 自动记录函数耗时到 logger
    - 输出格式：[timing] {module}.{function}: {elapsed}s
    - 支持 async 和 sync 函数

E2. 核心链路埋点
    - search_papers: refine_query / external_search / merge / hybrid_rank / add_to_pool
    - embed_paper: L0 profile / L1 sections / L2 chunks / total
    - parse_paper: PDF下载 / 文本提取 / 分块 / 入库 / auto_embed
    - generate_card / generate_review / generate_innovation: LLM 调用耗时

E3. LLM 调用监控
    - 记录：model、prompt_name、latency_ms、token_input、token_output、success、error_type
    - 汇总：总调用次数、平均延迟、P95、失败率、token 消耗
    - 写入 monitoring/llm_metrics.py

E4. Embedding 调用监控
    - 记录：mode (local/cloud)、operation、batch_size、latency_ms
    - 云端模式额外：临时集合创建/查询/删除各阶段耗时
    - 写入 monitoring/embed_metrics.py

E5. API 请求耗时 Middleware
    - 响应 Header 返回 X-Process-Time
    - 慢请求（>10s）自动 warn 日志
    - 已有 X-Request-ID 和 X-Duration-Ms middleware，需确认是否覆盖

E6. 性能诊断脚本
    - scripts/perf_report.py：读取日志 [timing] 行，生成统计表
    - 输出：函数名 / 调用次数 / 平均耗时 / P95 / 最大值
    - 可选：集成 py-spy 生成火焰图

E7. 可选：Sentry Performance Monitoring（产品上线后）
    - 免费版每月 5000 transaction
    - 自动采集 FastAPI 请求 span
    - 错误 + 性能关联
```

技术选型对照：

```text
| 方案                  | 适用场景                | 状态 |
|----------------------|------------------------|------|
| time.time() + logger | 单服务、快速定位         | ✅ 当前使用 |
| @timed 装饰器         | 单服务、统一格式         | 📋 E1 目标 |
| cProfile / py-spy    | 单服务、函数级火焰图     | 📋 E6 可选 |
| Prometheus + Grafana | 需要长期图表监控         | ⏳ 上线后 |
| Sentry Performance   | 错误+性能关联、SaaS 告警 | ⏳ E7 可选 |
| OpenTelemetry        | 多服务、分布式追踪       | ❌ 不需要 |
```

验收：

```text
搜索 API 日志有 [timing] 各步骤耗时。
解析 API 日志有 [timing] 各步骤耗时。
LLM 调用日志包含 model、latency_ms、token_count。
慢请求（>10s）自动 warning。
perf_report.py 能从日志生成统计表。
```

## 10. Sprint F：API 产品化与前端联调

目标：

```text
前端可以只依赖 /api/rw 完成项目、搜索、解析、分析、报告四类工作流。
```

任务：

```text
F1. 长任务产品化
    - TaskService 增加 step、progress、events、error_type、retryable、result_ref
    - 下载/解析/卡片/报告建议 task 化
    - 前端可通过 SSE 或轮询获取进度

F2. 搜索响应增强
    - 暴露 source_stats、errors、cache_hit、elapsed_ms
    - 每个 adapter 的成功/失败/耗时单独返回

F3. API 错误诊断
    - error body 增加 details.error_type、details.suggested_action
    - 不同业务异常返回不同 HTTP 状态码

F4. OpenAPI 文档完善
    - examples 覆盖项目创建、搜索、解析、scope、qa、报告
    - 路径与实际路由一致

F5. 前端四页
    - 项目论文库：创建项目、上传/搜索/导入、论文列表、解析状态
    - 知识图谱：节点和边、筛选、子图、来源
    - 研究 QA：Scope 选择、提问、答案、证据来源
    - 成果报告：生成综述/创新点、版本、导出 Markdown

F6. 演示项目
    - 主题：大语言模型与自主学习
    - 路径：创建项目 → 搜索 20 篇 → 解析 → 卡片 → 证据 → 图谱 → QA → 综述 → 创新点 → 导出
```

验收：

```text
演示路径可稳定复现。
前端能看到每一步状态。
QA 和报告能展开来源。
失败任务有可读错误。
```

## 11. Sprint G：评估门禁与演示闭环

目标：

```text
把 evaluation 子包从工具推进为每次 smoke 和报告生成后的质量门禁。
```

任务：

```text
G1. 质量门禁自动化
    - run_quality_gates 在报告保存前自动执行
    - required gate 失败时阻止保存或标记 warning

G2. 评估脚本
    - scripts/evaluate_research_workspace.py
    - 支持 --target qa|rag|report|innovation|logs|e2e|all
    - 输出 JSON/Markdown summary

G3. Golden cases 扩充
    - 从 4 个扩展到至少 10 个
    - 覆盖：QA 正常、QA 拒答、综述结构、创新点非空泛、scope 越界

G4. E2E smoke test
    - 覆盖完整闭环：project → search → parse → card → evidence → graph → scope → qa → review → innovation
    - 输出可机器读取的 summary

G5. 日志脱敏检查
    - redaction_check 覆盖 API key、Bearer、完整 prompt、raw_response
    - 每次 E2E smoke 自动运行 redaction_check
```

P0 门禁阈值：

```text
scope_guard_pass_rate == 1.0
out_of_scope_citation_count == 0
report_traceability_rate >= 0.80
innovation_specificity_rate >= 0.70
redaction_check_pass == true
e2e_smoke_pass == true
```

验收：

```text
python scripts/evaluate_research_workspace.py --target all --output-json
quality gates 在报告保存前自动执行
golden cases 全部通过
```

## 12. 优先级与依赖

```text
A（测试）→ B（搜索性能）→ C（质量硬化）→ D（可信度）→ E（监控）→ F（前端）→ G（门禁）
                            ↗
                    可并行：E 可与 C/D 并行推进
```

当前最高优先级：

```text
1. A — 测试体系建设（没有测试，后续重构无保障）
2. B — 搜索性能优化（当前搜索超时 >10 分钟，用户体验不可用）
3. E1-E2 — 关键链路计时（已部分实现，快速完成）
```

不建议当前做：

```text
1. Neo4j 或重型 GraphRAG
2. 多用户权限系统
3. 外部监控 SaaS 强依赖（Sentry 延后）
4. 自动抓取 Google Scholar
5. 大规模向量检索重构
```

## 13. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 多源搜索 API 不稳定 | 论文入库失败 | adapter 解耦、缓存、超时降级 |
| PDF 解析质量不稳定 | 卡片和证据质量下降 | 5 解析器 fallback、质量标记 |
| LLM 输出 JSON 不合规 | 生成链路中断 | Pydantic 校验、repair、fallback |
| QA 越界引用 | 产品可信度下降 | ScopeGuard + 单测 |
| 云端 embedding 慢 | 搜索超时 | 合并调用、缓存、本地 fallback |
| token 成本过高 | 批量综述不可用 | PaperCard + Evidence 优先、分批总结 |
| 前端状态不可见 | 用户误以为卡死 | TaskService + SSE/轮询 |

## 14. 模块文档同步

后续修改代码时，同步更新以下文档：

| 改动类型 | 必须同步 |
|----------|---------|
| 模型字段变化 | `models/` 相关文件、受影响 service |
| 搜索源/评分变化 | `search/` 相关文件 |
| 存储后端变化 | `storage/` 相关文件 |
| LLM schema 变化 | `llm/prompts.py`、调用方 service |
| API 路径变化 | `api/routes/` 相关文件、本文档 §2.5 |
| 质量门禁变化 | `evaluation/` 相关文件 |
| 性能监控变化 | `monitoring/` 相关文件、本文档 §9 |
