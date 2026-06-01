# agents_v3 开发完成报告

日期：2026-05-28

## 1. 开发计划执行概览

根据 `docs/research/11-产品方案与开发/论文知识库分析Agent详细开发执行计划.md`，已完成 Phase 0 至 Phase 5 的全部后端开发。

| 阶段 | 目标 | 状态 | 测试数 |
|------|------|------|--------|
| Phase 0 | 项目骨架与数据模型 | ✅ 完成 | 34 |
| Phase 1 | 项目论文库与论文入库 | ✅ 完成 | 22 |
| Phase 2 | 论文解析、论文卡片、证据表 | ✅ 完成 | 22 |
| Phase 3 | 知识图谱与 Retrieval Scope | ✅ 完成 | 19 |
| Phase 4 | Scope-based QA | ✅ 完成 | 12 |
| Phase 5 | 文献综述与创新点报告 | ✅ 完成 | 22 |
| Phase 6 | 前端整合与演示闭环 | 🚧 进行中 | 27 文件 |

**总计: 130 个测试，全部通过**

## 2. 模块架构

```
src/agents_v3/research_workspace/
├── __init__.py              # 模块导出
├── models.py                # Pydantic 数据模型 (19 个模型)
├── storage.py               # JSON 文件持久化层
├── project_service.py       # 项目 CRUD
├── paper_library.py         # 论文库管理
├── parser_service.py        # PDF 解析与分块
├── paper_card.py            # 论文卡片生成
├── evidence_table.py        # 证据表构建
├── graph_service.py         # 知识图谱构建与查询
├── scope.py                 # Retrieval Scope 解析
├── scope_qa.py              # 基于 Scope 的 QA
├── review_generator.py      # 文献综述生成
├── innovation_generator.py  # 创新点报告生成
└── report_service.py        # 报告管理与版本控制
```

## 3. 数据模型 (19 个)

| 模型 | 用途 |
|------|------|
| Project | 研究项目 |
| Paper | 论文元数据 |
| PaperChunk | 论文分块 |
| PaperCard | 论文结构化卡片 |
| SourceSpan | 来源引用 |
| EvidenceRecord | 证据记录 |
| GraphNode | 图节点 |
| GraphEdge | 图边 |
| KnowledgeGraph | 知识图谱 |
| RetrievalScope | 检索范围 |
| QARequest | QA 请求 |
| QAResponse | QA 响应 |
| InnovationPoint | 创新点 |
| Report | 报告 |
| ReportVersion | 报告版本 |
| PaperStatus | 论文状态枚举 |
| ReportType | 报告类型枚举 |
| ScopeType | 范围类型枚举 |
| NodeType / EdgeType | 图节点/边类型枚举 |

## 4. 核心功能

### 4.1 项目管理 (ProjectService)
- 创建、查询、更新、删除研究项目
- 项目统计（论文数、卡片数、证据数、报告数）

### 4.2 论文库管理 (PaperLibraryService)
- 上传 PDF 文件
- 添加论文元数据
- 批量导入搜索结果
- 导入 DOI 列表和 BibTeX
- 论文纳入/排除管理

### 4.3 论文解析 (ParserService)
- PDF 文本提取（依赖 pdfplumber）
- 按段落分块
- 批量解析项目论文
- 解析状态管理

### 4.4 论文卡片生成 (PaperCardGenerator)
- 从 chunks 提取结构化信息
- 研究问题、方法、发现、局限、未来工作
- 来源引用追踪
- 批量生成

### 4.5 证据表 (EvidenceTableService)
- 从论文卡片生成证据记录
- 按项目/论文/主题/方法查询
- 按 Scope 过滤证据
- 主题规范化合并

### 4.6 知识图谱 (GraphService)
- 从证据记录构建图谱
- 节点类型：Paper、Topic、Method、Finding、Limitation
- 边类型：BELONGS_TO_TOPIC、USES_METHOD、REPORTS_FINDING、HAS_LIMITATION
- 邻居查询、子图提取、路径查找

### 4.7 Scope 解析 (RetrievalScopeService)
- 支持 6 种范围类型：全项目、选中论文、主题组、方法组、图子图、年份范围
- 范围转论文 ID、证据记录、图上下文
- 范围摘要生成

### 4.8 Scope QA (ScopeQAService)
- 意图分类（6 种：局限性、方法、综述、创新点、比较、摘要）
- 上下文检索（证据、卡片、图谱）
- 基于意图的回答生成
- 建议操作推荐

### 4.9 文献综述生成 (LiteratureReviewGenerator)
- 材料收集（证据、卡片）
- 大纲构建（8 个标准章节）
- 章节生成
- 引用附加
- 综述验证

### 4.10 创新点报告 (InnovationReportGenerator)
- Gap 信号收集（局限性聚合、图谱缺失边）
- 候选创新点生成
- 泛化短语过滤
- 创新点评分
- 报告渲染

### 4.11 报告管理 (ReportService)
- 报告 CRUD
- 版本管理
- Markdown 导出

## 5. 开发规范遵循

根据 `docs/development/代码规范.md` 和 `docs/development/项目规范.md`：

| 规范项 | 遵循情况 |
|--------|----------|
| Python >=3.11 | ✅ 使用 `from __future__ import annotations` |
| snake_case 文件名 | ✅ 所有文件使用 snake_case |
| PascalCase 类名 | ✅ 所有类使用 PascalCase |
| 类型注解 | ✅ 所有公共接口有类型注解 |
| loguru 日志 | ✅ 使用 loguru 而非 print |
| pytest 测试 | ✅ 130 个测试 |
| v3 不依赖 v2 | ✅ 模块自包含 |
| 模块边界清晰 | ✅ 每个服务职责单一 |

## 6. 文件清单

### 源代码 (14 个文件)
- `src/agents_v3/__init__.py`
- `src/agents_v3/research_workspace/__init__.py`
- `src/agents_v3/research_workspace/models.py`
- `src/agents_v3/research_workspace/storage.py`
- `src/agents_v3/research_workspace/project_service.py`
- `src/agents_v3/research_workspace/paper_library.py`
- `src/agents_v3/research_workspace/parser_service.py`
- `src/agents_v3/research_workspace/paper_card.py`
- `src/agents_v3/research_workspace/evidence_table.py`
- `src/agents_v3/research_workspace/graph_service.py`
- `src/agents_v3/research_workspace/scope.py`
- `src/agents_v3/research_workspace/scope_qa.py`
- `src/agents_v3/research_workspace/review_generator.py`
- `src/agents_v3/research_workspace/innovation_generator.py`
- `src/agents_v3/research_workspace/report_service.py`

### 测试 (13 个文件)
- `tests/agents_v3/__init__.py`
- `tests/agents_v3/research_workspace/__init__.py`
- `tests/agents_v3/research_workspace/test_models.py`
- `tests/agents_v3/research_workspace/test_storage.py`
- `tests/agents_v3/research_workspace/test_project_service.py`
- `tests/agents_v3/research_workspace/test_paper_library.py`
- `tests/agents_v3/research_workspace/test_parser_service.py`
- `tests/agents_v3/research_workspace/test_paper_card_generator.py`
- `tests/agents_v3/research_workspace/test_evidence_table_service.py`
- `tests/agents_v3/research_workspace/test_graph_service.py`
- `tests/agents_v3/research_workspace/test_retrieval_scope.py`
- `tests/agents_v3/research_workspace/test_scope_qa.py`
- `tests/agents_v3/research_workspace/test_review_generator.py`
- `tests/agents_v3/research_workspace/test_innovation_generator.py`
- `tests/agents_v3/research_workspace/test_report_service.py`

## 7. 待办事项 (Phase 6)

- [ ] API 路由层（aiohttp routes）
- [ ] 前端页面整合
- [ ] 演示项目数据准备
- [ ] 端到端演示脚本
- [ ] 质量检查自动化

## 8. 运行方式

```bash
# 运行所有测试
python -m pytest tests/agents_v3/research_workspace/ -v

# 运行单个模块测试
python -m pytest tests/agents_v3/research_workspace/test_models.py -v

# 查看测试覆盖率
python -m pytest tests/agents_v3/research_workspace/ --cov=src/agents_v3/research_workspace
```
