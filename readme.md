# Paper Agent

<p align="center">
  <strong>论文知识库分析 Agent</strong>
</p>

<p align="center">
  将论文集合转化为可追溯的研究理解，自动生成文献综述与创新点报告
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#核心功能">核心功能</a> ·
  <a href="#工作原理">工作原理</a> ·
  <a href="#api">API</a> ·
  <a href="#贡献">贡献</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/tests-130%20passed-brightgreen.svg" alt="Tests">
</p>

---

## 什么是 Paper Agent？

Paper Agent 是一个面向研究者的**论文知识库分析系统**。它不是通用的 AI 写作工具，而是专注于一个核心问题：

> **如何从一批论文中，提取结构化知识，发现研究空白，并生成有证据支撑的文献综述和创新点报告？**

### 它解决什么问题？

研究者通常需要阅读数十篇论文，手动整理笔记、绘制关系图、撰写综述。这个过程：

- **耗时**：阅读 30 篇论文可能需要数周
- **容易遗漏**：人工难以发现跨论文的共同局限和研究空白
- **难以追溯**：综述中的结论往往缺乏明确的证据来源

Paper Agent 自动化了这个过程。

### 与现有工具的区别

| | 通用 AI 助手 | 文献管理工具 | **Paper Agent** |
|---|---|---|---|
| 输入 | 单个问题 | 论文列表 | **项目级论文集合** |
| 分析方式 | 自由问答 | 标签分类 | **结构化提取 + 知识图谱** |
| 产出 | 通用回答 | 引用格式 | **文献综述 + 创新点报告** |
| 可追溯性 | 无 | 引用链接 | **结论 → 证据 → 论文 → 段落** |
| 知识结构 | 无 | 扁平标签 | **图谱：论文-主题-方法-发现-局限-空白** |

---

## 核心功能

### 论文管理
- 上传 PDF 文件
- 从学术搜索引擎导入
- 批量导入 DOI / BibTeX

### 知识提取
- **论文卡片**：自动提取研究问题、方法、数据集、关键发现、局限性
- **证据表**：从卡片生成结构化证据记录
- **知识图谱**：构建论文 → 主题 → 方法 → 发现 → 局限 → 空白的关系图

### 智能分析
- **Scope QA**：基于选中论文/主题/子图的限定范围问答
- **文献综述**：自动生成结构化综述（背景、主题、方法、发现、不足、趋势）
- **创新点报告**：基于图谱空白和共同局限，发现可行的创新方向

### 可追溯性
- 每条结论关联到具体证据
- 每条证据关联到论文和段落
- 创新点必须绑定支撑论文，拒绝无证据的泛化表述

---

## 工作原理

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   论文入库   │ ──▶ │   论文解析   │ ──▶ │   论文卡片   │
│  PDF/DOI/搜索 │     │  文本分块    │     │  结构化提取  │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  文献综述    │ ◀── │  Scope QA   │ ◀── │   证据表     │
│  结构化生成  │     │  范围限定问答 │     │  证据聚合    │
└─────────────┘     └─────────────┘     └─────────────┘
        ▲                                     │
        │           ┌─────────────┐           │
        └────────── │  知识图谱    │ ◀─────────┘
                    │  关系发现    │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  创新点报告  │
                    │  Gap 分析    │
                    └─────────────┘
```

### 三个核心中间层

系统不直接从 PDF 生成报告，而是经过三个结构化中间层：

1. **Paper Card** — 论文的结构化摘要
2. **Evidence Record** — 可查询的证据单元
3. **Knowledge Graph** — 实体关系网络

这保证了产出的可验证性。

### Scope-based QA

问答不是通用聊天，而是基于用户选定的范围：

```python
# 只基于选中的 3 篇论文回答
qa.answer(project_id, "这些研究有什么共同不足？", {
    "type": "selected_papers",
    "selected_paper_ids": ["paper_001", "paper_002", "paper_003"]
})

# 基于某个主题的所有论文回答
qa.answer(project_id, "反馈机制的研究方法有哪些？", {
    "type": "topic_group",
    "selected_topic_ids": ["feedback_mechanism"]
})

# 基于知识图谱子图回答
qa.answer(project_id, "这个方向有什么创新空间？", {
    "type": "graph_subgraph",
    "selected_graph_node_ids": ["topic:feedback_mechanism"],
    "graph_hops": 2
})
```

每条回答都声明范围，并列出支撑证据。

### 创新点反泛化

创新点报告内置反泛化检查，拒绝无证据支撑的泛化表述：

```
✗ "使用深度学习"        → 无具体证据，被拒绝
✗ "扩展样本量"          → 无具体论文支撑，被拒绝
✓ "将 X 方法迁移到 Y 领域" → 有 3 篇论文支撑图谱 Gap，被接受
```

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/shigenqiang/paper-agent.git
cd paper-agent

# 安装依赖
pip install -e .

# 或仅安装核心依赖
pip install pydantic loguru pdfplumber
```

### 基本使用

```python
from src.agents_v3.research_workspace import *

# 创建项目
ps = ProjectService()
project = ps.create_project("我的研究方向")

# 添加论文
pls = PaperLibraryService()
pls.add_paper_metadata(project.project_id, {
    "title": "论文标题",
    "authors": ["作者A", "作者B"],
    "year": 2024,
})

# 后续步骤：解析 → 生成卡片 → 构建证据表 → 构建图谱 → QA → 生成报告
```

### 运行测试

```bash
python -m pytest tests/agents_v3/research_workspace/ -v
```

---

## API

### 项目管理

```python
ProjectService.create_project(name, description, ...)
ProjectService.list_projects()
ProjectService.get_project(project_id)
ProjectService.get_project_stats(project_id)
```

### 论文库

```python
PaperLibraryService.add_uploaded_paper(project_id, file_path)
PaperLibraryService.add_paper_metadata(project_id, metadata)
PaperLibraryService.add_search_results(project_id, results)
PaperLibraryService.import_doi_list(project_id, doi_list)
PaperLibraryService.import_bibtex(project_id, bibtex_text)
```

### 知识提取

```python
ParserService.parse_paper(paper_id)
PaperCardGenerator.generate(paper_id)
EvidenceTableService.build_for_project(project_id)
GraphService.build_project_graph(project_id)
```

### 分析与生成

```python
ScopeQAService.answer(project_id, question, scope)
LiteratureReviewGenerator.generate(project_id, scope)
InnovationReportGenerator.generate(project_id, scope)
ReportService.export_markdown(report_id)
```

---

## 项目结构

```
src/agents_v3/research_workspace/
├── models.py                 # 数据模型定义
├── storage.py                # JSON 持久化层
├── project_service.py        # 项目管理
├── paper_library.py          # 论文库管理
├── parser_service.py         # PDF 解析
├── paper_card.py             # 论文卡片生成
├── evidence_table.py         # 证据表构建
├── graph_service.py          # 知识图谱
├── scope.py                  # Scope 解析
├── scope_qa.py               # Scope QA
├── review_generator.py       # 文献综述生成
├── innovation_generator.py   # 创新点报告生成
└── report_service.py         # 报告管理
```

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 类型注解、现代语法 |
| 数据模型 | Pydantic v2 | 强类型、自动验证 |
| 存储 | JSON 文件 | 轻量、可读、易于调试 |
| PDF 解析 | pdfplumber | 文本提取和分块 |
| 日志 | Loguru | 结构化日志 |
| 测试 | pytest | 130 个测试用例 |
| 代码质量 | Ruff | 格式化和 lint |

---

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'Add your feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

### 开发规范

- 遵循 [代码规范](docs/development/代码规范.md)
- 遵循 [项目规范](docs/development/项目规范.md)
- 新增功能必须包含测试
- 运行 `python -m pytest tests/agents_v3/ -v` 确保测试通过

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  如果这个项目对你有帮助，请给一个 ⭐️
</p>
