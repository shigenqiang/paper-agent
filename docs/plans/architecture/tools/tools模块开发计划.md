# tools 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/tools/tools-module.md` + `docs/research/PDF解析技术调研报告.md`
> 现状：PDF解析/引文提取/图表分类/元数据解析 基础已实现

---

## 一、模块概述

### 1.1 现有架构

```
tools/
├── text_chunker.py         # 文本分块 ✅
├── citation_extractor.py  # 引文提取 ✅
├── chart_classifier.py    # 图表分类 ✅
├── metadata_parser.py      # 元数据解析 ✅
└── ...                    # 更多工具
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **PDF解析** | pdfplumber | Marker + PDF-Extract-Kit |
| **公式识别** | 基础 | LaTeX/MathML |
| **中文支持** | 弱 | 专项优化 |
| **工具注册** | 分散 | MCP 统一管理 |

---

## 二、任务清单

### 2.1 PDF 解析升级（P0）

**目标**：Marker + PDF-Extract-Kit

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Marker 集成 | P0 | 主解析引擎 | `src/agents_v2/tools/marker_parser.py` |
| PDF-Extract-Kit 集成 | P1 | 中文/公式 | `src/agents_v2/tools/pdf_extract_kit.py` |
| 自动路由 | P1 | 智能选择引擎 | `src/agents_v2/tools/smart_pdf_router.py` |
| 公式提取 | P1 | LaTeX/MathML | `src/agents_v2/tools/formula_extractor.py` |

### 2.2 MCP 工具注册（P0）

**目标**：统一工具管理

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| ToolRegistry | P0 | 工具注册表 | `src/agents_v2/tools/tool_registry.py` |
| MCP Tool Wrapper | P0 | MCP 封装 | `src/agents_v2/tools/mcp_wrapper.py` |
| 工具发现 | P1 | 自动发现 | `src/agents_v2/tools/tool_discovery.py` |

---

## 三、实施计划

```
Week 1:
  - Marker 集成
  - PDF-Extract-Kit 集成

Week 2:
  - 自动路由实现
  - 公式提取

Week 3:
  - MCP 工具注册
  - 工具发现
```

---

## 四、验收标准

- [ ] Marker 解析英文论文正常
- [ ] PDF-Extract-Kit 解析中文论文正常
- [ ] 公式提取 LaTeX 正常
- [ ] MCP 工具注册正常

---

**版本**：v1.0
**规划日期**：2026-05-02
