# Paper Agent — 论文知识库分析 Agent

> 将论文集合转化为可追溯的研究理解，生成文献综述和创新点报告

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 项目简介

Paper Agent 是一个**论文知识库分析 Agent**，帮助研究者将项目级论文集合转化为结构化知识，并生成两个核心产出：

1. **文献综述** — 基于选定论文范围的结构化综述
2. **创新点报告** — 基于知识图谱 Gap 和共同局限的创新方向分析

### 核心工作流

```
论文入库 → 论文结构化 → 证据表 → 知识图谱 → 选择范围 QA → 文献综述 / 创新点报告
```

### 与现有工具的差异

| 维度 | 现有工具 | Paper Agent |
|------|----------|-------------|
| 输入 | 单篇论文或关键词 | **项目级论文集合** |
| 分析 | 通用 QA | **Scope-based QA（选中论文/主题/子图）** |
| 产出 | 通用摘要 | **文献综述 + 创新点报告** |
| 可追溯 | 无 | **每条结论追溯到证据和图谱** |
| 知识结构 | 扁平 | **知识图谱（Paper-Topic-Method-Finding-Limitation-Gap）** |

---

## 核心功能

| 功能 | 说明 |
|------|------|
| **论文入库** | PDF 上传、搜索导入、DOI/BibTeX 导入 |
| **论文卡片** | 结构化提取：研究问题、方法、发现、局限、未来工作 |
| **证据表** | 从论文卡片生成证据记录，支持按主题/方法/范围查询 |
| **知识图谱** | 自动构建 Paper → Topic → Method → Finding → Limitation → Gap 图谱 |
| **Scope QA** | 基于选中论文/主题/方法/子图的范围限定问答 |
| **文献综述** | 基于选定 Scope 生成结构化综述，含研究背景、主题划分、方法分析、不足和趋势 |
| **创新点报告** | 基于图谱 Gap 和共同局限分析创新方向，含证据支撑和可行性评估 |

---

## 快速开始

### 安装

```bash
pip install -e .
# 或
pip install pydantic loguru pdfplumber
```

### 运行测试

```bash
python -m pytest tests/agents_v3/research_workspace/ -v
```

### 使用示例

```python
from src.agents_v3.research_workspace import *

# 1. 创建项目
ps = ProjectService()
project = ps.create_project("大语言模型与自主学习")

# 2. 添加论文
pls = PaperLibraryService()
papers = pls.add_search_results(project.project_id, [
    {"title": "LLM Feedback Study", "authors": ["A"], "year": 2024},
    {"title": "AI Tutoring System", "authors": ["B"], "year": 2023},
    {"title": "Self-Regulated Learning with AI", "authors": ["C"], "year": 2024},
])

# 3. 构建证据表和知识图谱
EvidenceTableService().build_for_project(project.project_id)
graph = GraphService().build_project_graph(project.project_id)

# 4. Scope QA
qa = ScopeQAService()
answer = qa.answer(project.project_id, "这些研究有什么不足？", {"type": "all_project"})
print(answer.answer)

# 5. 生成文献综述
review = LiteratureReviewGenerator().generate(project.project_id, {"type": "all_project"})

# 6. 生成创新点报告
innovation = InnovationReportGenerator().generate(project.project_id, {"type": "all_project"})
```

---

## 项目结构

```
src/agents_v3/research_workspace/
├── models.py                # 数据模型（Project, Paper, PaperCard, EvidenceRecord, Graph...）
├── storage.py               # JSON 文件持久化
├── project_service.py       # 项目管理
├── paper_library.py         # 论文库管理
├── parser_service.py        # PDF 解析
├── paper_card.py            # 论文卡片生成
├── evidence_table.py        # 证据表构建
├── graph_service.py         # 知识图谱
├── scope.py                 # Scope 解析
├── scope_qa.py              # Scope QA
├── review_generator.py      # 文献综述生成
├── innovation_generator.py  # 创新点报告生成
└── report_service.py        # 报告管理
```

---

## 创新之处

### 1. 三个中间层

系统不直接从 PDF 生成报告，而是经过三个结构化中间层：

```
Paper Card → Evidence Record → Knowledge Graph
```

这保证了产出的可追溯性和可验证性。

### 2. Scope-based QA

QA 不是通用聊天，而是基于用户选定的范围：

- 选中论文
- 主题组
- 方法组
- 图谱子图
- 年份范围

每条回答都声明范围，并列出支撑证据。

### 3. 知识图谱驱动

图谱不是装饰，而是驱动核心功能：

- **QA**: 基于图谱邻居扩展上下文
- **创新点**: 发现图谱中的 Gap（缺失边、低连接组合）
- **综述**: 按图谱结构组织内容

### 4. 创新点反泛化

创新点报告内置反泛化检查，拒绝无证据的泛化短语（如"使用深度学习"、"扩展样本"），必须绑定具体证据。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| 数据模型 | Pydantic v2 |
| 存储 | JSON 文件 |
| PDF 解析 | pdfplumber |
| 日志 | Loguru |
| 测试 | pytest |

---

## 许可证

MIT License
