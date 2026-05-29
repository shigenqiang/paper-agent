# 模块级开发计划

更新时间：2026-05-29

本目录是 `paper-agent` 论文知识库分析 Agent 的模块级专项开发计划入口，覆盖 `src/agents_v3/research_workspace` 已有模块和后续必须收敛的 API、任务、存储后端、评估、日志、监控能力。

这些文档的用途不是泛泛描述产品，而是把“论文搜索、PDF 解析、论文卡片、证据表、知识图谱、Scope QA、综述、创新点报告、导出、前端联调、质量门禁”拆成可开发、可测试、可验收的工程任务。

## 1. 目录定位

本目录服务于三个目标：

```text
1. 统一开发路线：明确每个模块的职责、依赖、数据契约和开发顺序。
2. 降低实现偏差：每个模块都有目标架构、核心流程、接口建议、测试计划和验收标准。
3. 建立质量闭环：所有 QA、报告、创新点都必须可追溯、可评估、可回归。
```

当前主实现目录：

```text
src/agents_v3/research_workspace/
```

当前测试目录：

```text
tests/agents_v3/research_workspace/
```

后续建议新增：

```text
scripts/evaluate_research_workspace.py
tests/fixtures/research_workspace/
src/agents_v3/research_workspace/evaluation/
```

当前已经存在：

```text
src/agents_v3/research_workspace/api/
src/agents_v3/research_workspace/llm/
src/agents_v3/research_workspace/evaluation/
src/agents_v3/research_workspace/storage_backend.py
src/agents_v3/research_workspace/postgres_storage.py
src/agents_v3/research_workspace/vector_storage.py
```

## 当前代码对齐深化（2026-05-29）

本目录下 `00-15` 每个模块文件都已补充同名章节，用于把 2026-05-29 的真实代码状态、下一步深化任务、验收证据和风险收束到模块级开发计划中。后续开发时优先阅读各模块末尾的“当前代码对齐深化（2026-05-29）”，再回看前文的原始设计。

当前深化的统一方向：

```text
1. 存储后端收敛：JSONStorage、StorageBackend、PostgresStorage、VectorStorage 的边界和测试契约统一。
2. 搜索产品化：SearchField、SearchOrchestrator、papers_pool、搜索诊断、排序质量信号进入 API 和前端契约。
3. 证据可信链：PaperChunk、SourceSpan、PaperCard、EvidenceRecord、Graph、Report source_index 全链路可追踪。
4. 生成质量门禁：QA、综述、创新点报告统一接入 ScopeGuard、citation coverage、traceability 和 specificity 检查。
5. API/任务联调：/api/rw、TaskService、统一错误码、长任务 progress/events 成为前端主集成面。
6. 评估可观测：evaluation/ 子包的 metrics、golden、gates、logging_utils 写回任务和报告 validation_result。
```

本轮深化的总控入口：

```text
docs/research/14-细致开发计划/当前项目模块深化开发计划.md
```

## 2. 编写依据

本目录综合依据：

```text
当前 src/agents_v3/research_workspace 代码实现
当前 tests/agents_v3/research_workspace 测试覆盖
docs/research 下的搜索、PDF、QA/RAG、知识图谱、提示词、评估、日志、上下文优化调研
docs/research/11-产品方案与开发/当前产品方案.md
docs/research/11-产品方案与开发/当前开发计划.md
docs/research/14-细致开发计划/论文知识库分析Agent细致开发计划.md
docs/development/项目规范.md
docs/development/代码规范.md
docs/getting-started/frontend-overview.md
```

参考的主流产品和方法包括：

```text
Elicit
Consensus
scite
Rayyan
Covidence
DistillerSR
PRISMA
Cochrane / GRADE
GraphRAG
RAGAS 风格评估
OpenTelemetry / LangSmith 风格可观测性
FastAPI / Pydantic 契约化接口
```

## 3. 阅读顺序

建议按下面顺序阅读和开发。`00` 是总览，`01-15` 是模块专项计划。

| 顺序 | 文件 | 模块 | 主要对象 |
| --- | --- | --- | --- |
| 00 | `00-模块总览与依赖关系.md` | 全局总览 | 主链路、依赖关系、全局门禁 |
| 01 | `01-核心模型与存储模块.md` | 核心模型与存储 | `models.py`、`storage.py` |
| 02 | `02-项目服务模块.md` | 项目服务 | `project_service.py` |
| 03 | `03-论文库搜索导入模块.md` | 搜索、导入、论文库 | `paper_library.py`、`search/` |
| 04 | `04-PDF解析与分块模块.md` | PDF 解析与分块 | `parser_service.py` |
| 05 | `05-论文卡片生成模块.md` | 论文卡片 | `paper_card.py` |
| 06 | `06-证据表模块.md` | 证据表 | `evidence_table.py` |
| 07 | `07-知识图谱模块.md` | 知识图谱 | `graph_service.py` |
| 08 | `08-RetrievalScope模块.md` | 检索范围 | `scope.py` |
| 09 | `09-ScopeQA与RAG模块.md` | Scope QA 与 RAG | `scope_qa.py` |
| 10 | `10-综述生成模块.md` | 文献综述 | `review_generator.py` |
| 11 | `11-创新点报告模块.md` | 创新点报告 | `innovation_generator.py` |
| 12 | `12-报告版本与导出模块.md` | 报告版本与导出 | `report_service.py` |
| 13 | `13-LLM提示词与结构化输出模块.md` | LLM、提示词、结构化输出 | `llm/`、prompt schema |
| 14 | `14-API任务与前端联调模块.md` | API、任务、前端联调 | `api/`、TaskService、frontend contract |
| 15 | `15-评估日志监控模块.md` | 评估、日志、监控 | `evaluation/`、quality gates |

## 4. 模块分层

### 4.1 基础层

| 模块 | 作用 |
| --- | --- |
| 01 核心模型与存储 | 统一数据契约、持久化、迁移和安全写入 |
| 02 项目服务 | 提供项目入口、状态、统计、配置和健康检查 |
| 13 LLM 提示词与结构化输出 | 提供模型调用、schema 校验、repair、prompt version 和 token 指标 |
| 15 评估日志监控 | 提供结构化日志、评估函数、golden fixtures 和质量门禁 |

### 4.2 文献资料层

| 模块 | 作用 |
| --- | --- |
| 03 论文库搜索导入 | 多源搜索、缓存、限流、去重、融合排序和入库 |
| 04 PDF 解析与分块 | 从 PDF 得到章节、chunk、引用分离和解析质量报告 |
| 05 论文卡片生成 | 把单篇论文转成结构化研究问题、方法、发现、不足、未来工作 |

### 4.3 证据与知识层

| 模块 | 作用 |
| --- | --- |
| 06 证据表 | 从卡片和 chunk 构建可审核、可追溯的证据记录 |
| 07 知识图谱 | 组织论文、主题、方法、发现、不足、gap 的关系网络 |
| 08 RetrievalScope | 把用户选择、主题、论文集合解析成受控检索范围 |

### 4.4 智能生成层

| 模块 | 作用 |
| --- | --- |
| 09 ScopeQA 与 RAG | 在 scope 内基于证据回答问题，支持拒答和引用校验 |
| 10 综述生成 | 基于证据矩阵生成有章节、有来源、有质量校验的综述 |
| 11 创新点报告 | 基于 gap、限制证据和图谱生成具体、可执行、可追溯的创新方向 |
| 12 报告版本与导出 | 保存版本、导出 Markdown/JSON、维护来源索引和 traceability |

### 4.5 产品联调层

| 模块 | 作用 |
| --- | --- |
| 14 API 任务与前端联调 | 提供前后端接口、长任务进度、错误状态和演示链路 |
| 15 评估日志监控 | 给 API、任务、LLM 和生成结果提供可观测与回归门禁 |

## 5. MVP 主链路

最小可用产品主链路：

```text
1. 创建项目。
2. 搜索或导入论文。
3. 解析 PDF 并生成 chunks。
4. 生成 PaperCard。
5. 构建 EvidenceTable。
6. 构建 KnowledgeGraph。
7. 解析 RetrievalScope。
8. 基于 Scope 做 QA。
9. 基于 Scope 生成文献综述。
10. 基于 gap 和 evidence 生成创新点报告。
11. 保存报告版本并导出 Markdown/JSON。
12. 通过评估脚本检查 scope、来源、日志和质量门禁。
13. 接入 API、任务进度和前端页面。
```

其中 `01-03` 是当前优先推进搜索模块时的基础依赖；`15` 是搜索之后所有生成模块都需要持续接入的质量底座。

## 6. 推荐开发批次

### Batch A：搜索 MVP

目标：先把论文搜索、结果融合、缓存、去重、入库做扎实。

建议阅读：

```text
00-模块总览与依赖关系.md
01-核心模型与存储模块.md
02-项目服务模块.md
03-论文库搜索导入模块.md
15-评估日志监控模块.md
```

验收重点：

```text
搜索 session 可保存。
OpenAlex/arXiv/CrossRef provider 可 mock 测试。
缓存、限流、错误降级可测试。
结果去重和融合排序稳定。
搜索结果可 commit 到 paper library。
```

### Batch B：解析、卡片、证据

目标：让搜索或导入的论文进入可追溯证据层。

建议阅读：

```text
04-PDF解析与分块模块.md
05-论文卡片生成模块.md
06-证据表模块.md
13-LLM提示词与结构化输出模块.md
15-评估日志监控模块.md
```

验收重点：

```text
PDF 解析失败有状态和原因。
chunk 带 paper_id、section、页码或位置元数据。
PaperCard 字段完整，有 source_spans。
EvidenceRecord 可追溯到 paper/card/chunk。
```

### Batch C：Scope、QA、综述

目标：实现范围受控的问答和综述生成。

建议阅读：

```text
07-知识图谱模块.md
08-RetrievalScope模块.md
09-ScopeQA与RAG模块.md
10-综述生成模块.md
15-评估日志监控模块.md
```

验收重点：

```text
所有 QA 和综述都先 resolve scope。
scope 外 paper/evidence 不进入答案。
证据不足时能拒答或表达不确定。
综述主体章节有来源覆盖。
```

### Batch D：创新点、报告、产品联调

目标：形成可交付成果并接入前端。

建议阅读：

```text
11-创新点报告模块.md
12-报告版本与导出模块.md
14-API任务与前端联调模块.md
15-评估日志监控模块.md
```

验收重点：

```text
创新点有 gap、证据、风险和可行性。
报告版本可保存、比较、导出。
长任务有 task_id、进度、错误类型。
前端可完成项目、搜索、分析、报告四类核心页面联调。
```

## 7. 当前深化状态

截至 2026-05-29，本目录中 `00` 到 `15` 均已有专项开发计划；当前新增 `../当前项目模块深化开发计划.md` 作为按现有代码状态推进下一轮开发的执行入口。

| 文件 | 状态 |
| --- | --- |
| `00-模块总览与依赖关系.md` | 已完成，全局入口 |
| `01-核心模型与存储模块.md` | 已完成 |
| `02-项目服务模块.md` | 已完成 |
| `03-论文库搜索导入模块.md` | 已完成，并已按当前搜索实现和平台选型深化 |
| `04-PDF解析与分块模块.md` | 已完成 |
| `05-论文卡片生成模块.md` | 已完成 |
| `06-证据表模块.md` | 已完成 |
| `07-知识图谱模块.md` | 已完成 |
| `08-RetrievalScope模块.md` | 已完成 |
| `09-ScopeQA与RAG模块.md` | 已完成 |
| `10-综述生成模块.md` | 已完成 |
| `11-创新点报告模块.md` | 已完成 |
| `12-报告版本与导出模块.md` | 已完成 |
| `13-LLM提示词与结构化输出模块.md` | 已完成，需以后续代码为准维护 `llm/` 子包路径 |
| `14-API任务与前端联调模块.md` | 已完成，需以后续代码为准维护 `api/` 子包路径 |
| `15-评估日志监控模块.md` | 已完成，需以后续代码为准维护 `evaluation/` 子包路径 |

## 8. 全局工程原则

实现时遵循：

```text
继续以 src/agents_v3/research_workspace 作为主线。
优先补齐可追溯证据链，而不是优先做复杂 Agent 编排。
优先保证数据契约、存储、测试和错误处理，而不是只追求生成效果。
所有 QA、综述、创新点都必须先 resolve RetrievalScope。
所有正式回答和报告必须保留 paper_ids、evidence_ids、graph_node_ids。
LLM 输出必须经过结构化 schema 校验、repair 或 fallback。
长任务必须有 task_id、状态、进度、失败原因和可恢复策略。
日志不能泄露 API key、完整 prompt、完整 PDF 文本或完整 LLM response。
每个模块都必须有单元测试、关键边界测试和验收标准。
```

## 9. 全局质量门禁

模块实现完成后，至少证明：

```text
1. 从创建项目到报告导出全链路可运行。
2. 搜索失败、解析失败、LLM 失败、导出失败都有明确状态和日志。
3. 所有正式答案和报告都能追溯到 paper、evidence 或 graph node。
4. Scope 外内容不会进入 QA、综述或创新点报告。
5. EvidenceTable 不接受 unknown、伪证据或无来源强结论。
6. PaperCard 和 EvidenceRecord 有 source span 或可解释来源。
7. 综述主体章节有来源覆盖。
8. 创新点必须有 gap、证据、风险和可行性。
9. 报告导出包含范围、论文、证据、版本和来源索引。
10. 评估脚本能发现 scope 越界、报告无来源、创新点空泛和日志泄露。
```

P0 建议门禁：

```text
scope_guard_pass_rate == 1.0
out_of_scope_citation_count == 0
report_traceability_rate >= 0.80
section_source_coverage >= 0.80
innovation_specificity_rate >= 0.70
generic_filter_pass_rate >= 0.90
redaction_check_pass == true
e2e_smoke_pass == true
```

## 10. 统一测试矩阵

| 层级 | 测试重点 |
| --- | --- |
| 模型层 | Pydantic 校验、默认值、序列化、旧数据兼容 |
| 存储层 | 原子写入、collection 约束、查询、迁移、损坏文件恢复 |
| 搜索层 | provider mock、缓存、限流、去重、融合排序、commit |
| 解析层 | PDF 成功/失败、section 识别、chunk 元数据、references split |
| 卡片层 | schema 输出、source spans、fallback、字段完整度 |
| 证据层 | evidence type、traceability、review status、导出 |
| 图谱层 | stable ids、source properties、subgraph、gap/path query |
| Scope 层 | project boundary、empty scope、组合过滤、ScopeGuard |
| QA/RAG | retrieval ranking、拒答、citation validation、scope violation |
| 报告层 | section sources、traceability、version、Markdown/JSON export |
| LLM 层 | structured output、repair、token/latency metrics、脱敏 |
| API 层 | request/response contract、task progress、错误状态 |
| 评估层 | golden fixtures、quality gates、evaluate script、redaction check |

## 11. 文档维护规则

后续改动本目录时遵循：

```text
1. 新增模块时先更新 README 和 00 总览。
2. 改变开发顺序时同步更新“推荐开发批次”。
3. 改变数据模型时同步更新 01 和相关业务模块。
4. 改变 LLM 输出结构时同步更新 13 和受影响模块。
5. 改变质量指标时同步更新 15 和相关模块验收标准。
6. 文档中的文件名、类名、函数名应尽量对应真实代码。
7. 不把临时想法写成已确定任务；不确定内容标注 P1/P2 或待验证。
```

## 12. 快速入口

如果当前只做搜索模块：

```text
先读 03-论文库搜索导入模块.md
再读 01-核心模型与存储模块.md
必要时读 02-项目服务模块.md
最后对齐 15-评估日志监控模块.md 中的日志和指标要求
```

如果当前做生成质量：

```text
先读 08-RetrievalScope模块.md
再读 09-ScopeQA与RAG模块.md
然后读 10-综述生成模块.md、11-创新点报告模块.md
最后读 15-评估日志监控模块.md
```

如果当前做前端联调：

```text
先读 14-API任务与前端联调模块.md
再读 12-报告版本与导出模块.md
最后读 15-评估日志监控模块.md
```
