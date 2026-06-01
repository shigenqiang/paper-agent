# 细致开发计划

本目录根据 `docs/research` 下已有调研文档、`11-产品方案与开发` 中的当前产品方案和当前开发计划，以及当前代码基线 `src/agents_v3/research_workspace` 生成。

更新时间：2026-06-01

目标不是重复调研结论，而是把“论文知识库分析 Agent”拆成可以直接进入开发、测试和验收的执行计划。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `当前代码功能清单.md` | 按模块结构记录当前代码已实现的全部功能（59 源文件 / 15,621 行 / 38 个 API 端点）。 |
| `论文知识库分析Agent细致开发计划.md` | 主开发计划，包含阶段路线、模块任务、接口、测试与验收标准。 |
| `当前项目模块深化开发计划.md` | 按当前工作区代码状态补充的执行总控，重点对齐存储后端、搜索 API、证据质量、ScopeGuard、API/评估落地。 |
| `开发任务验收清单.md` | 按 P0/P1/P2 拆分的任务清单（104 已完成 / 129 待做），可用于 issue、迭代看板或开发自检。 |
| `模块级开发计划/` | 对每个核心模块逐一分析，包含当前实现、调研依据、开发任务、测试计划和验收标准。其中 05/08/10/12 已完成深度代码对齐。 |

## 当前实施基线

当前落地目录：

```text
src/agents_v3/research_workspace/
tests/agents_v3/research_workspace/
```

当前已有的最小闭环雏形包括：

```text
ProjectService
PaperLibraryService
ParserService
PaperCardGenerator
EvidenceTableService
GraphService
RetrievalScopeService
ScopeQAService
LiteratureReviewGenerator
InnovationReportGenerator
ReportService
LLMService
JSONStorage
StorageBackend
PostgresStorage
VectorStorage
FastAPI /api/rw
TaskService
SearchOrchestrator
SearchCache
RateManager
LLMService 子包
Evaluation 子包
```

后续开发应在这套 v3 模块上收敛存储后端一致性、搜索 API 可解释性、解析/证据质量、ScopeGuard、API 前端联调、评估和监控，不再从旧版目录重新开始。

## 当前深化入口

如果要根据当前项目继续开发，优先阅读：

```text
开发任务验收清单.md                          # 已按代码实现更新，104 项已完成 / 129 项待做
模块级开发计划/00-模块总览与依赖关系.md       # 全局依赖关系
模块级开发计划/README.md                     # 已更新深化状态和共享缺陷
当前项目模块深化开发计划.md
```

### 已完成深度代码对齐的模块（2026-06-01）

以下 4 个模块已完成第二轮深度对齐，包含实现状态、已知缺陷、下游集成映射、API 定义、增强测试计划和优先级下一步：

| 模块 | 代码 | 缺陷 | 测试 | 关键差距 |
| --- | --- | --- | --- | --- |
| 05-论文卡片生成 | 637 行 / 22 方法 | 7 | 21→~50 | invoke_structured 未使用、PromptRegistry 未接入 |
| 08-RetrievalScope | ~580 行 / 21 方法 | 8 | 22→~47 | Gap 节点解析不完整、context_budget 未实现 |
| 10-综述生成 | 569 行 / 12 方法 | 10 | 12→~37 | graph_context 未使用、无 Review-Revise、绕过 ReportService |
| 12-报告版本与导出 | 388 行 / 14 方法 | 10 | 22→~79 | PG schema 不完整、export 写副作用、生成模块绕过 |

4 个模块共享的基础设施缺陷：

```text
1. PromptRegistry 存在但未接入任何 generator
2. invoke_structured 未使用，LLM 输出无 schema 校验
3. FakeLLMService._responses 存入但 invoke 不读取
4. 生成模块直接 storage.upsert_item 绕过 ReportService
```

### 当前最优先的开发主线

```text
1. 生成模块接入 ReportService：review_generator / innovation_generator 改用 save_report
2. 结构化输出迁移：所有 generator 从 invoke_json 迁移到 invoke_structured
3. 存储后端收敛：PostgreSQL schema 补全 reports/report_versions 表缺失列
4. 搜索链路产品化：API 复用 SearchOrchestrator，暴露 source_stats/errors/cache_hit
5. 证据质量硬化：Parser/Card/Evidence 都输出可追溯质量信号
6. Scope 与报告可信度：QA/Review/Innovation/Report 保存前通过 ScopeGuard
7. API 与评估闭环：task progress、OpenAPI examples、quality gates
```

### 测试结果归档

各模块测试结果已按模块归档到：

```text
docs/test_results/01-核心模型与存储/  …  15-评估日志监控/
```

## 模块级计划

模块级计划位于：

```text
docs/research/14-细致开发计划/模块级开发计划/
```

建议从 `00-模块总览与依赖关系.md` 开始阅读，再按实现顺序推进。

## 调研依据

主要参考来源：

- `docs/research/01-Agent协议与架构`
- `docs/research/02-提示词工程`
- `docs/research/03-Agent能力评估`
- `docs/research/05-学术搜索与解析`
- `docs/research/07-记忆系统`
- `docs/research/08-日志与监控`
- `docs/research/10-学术QA系统`
- `docs/research/10-知识图谱`
- `docs/research/11-产品方案与开发`
- `docs/research/12-优化方案`
