# Citation 模块开发计划

> 版本：v1.0
> 更新日期：2026-05-04
> 状态：**已实现**

## 模块概述

统一引用管理模块，提供参考文献格式化、DOI验证、引用提取引源追踪等功能。

## 目录结构

```
citation/
├── __init__.py       # 统一导出
├── formatter.py      # 格式化引用（APA/MLA/GB7714等）
├── verifier.py        # DOI验证和元数据获取
├── extractor.py       # 从文本提取引用标记
├── tracker.py         # 答案溯源追踪
└── styles.py         # 引用样式枚举
```

## 实现状态

| 功能 | 状态 | 说明 |
|------|------|------|
| CitationFormatter | ✅ 已实现 | 支持 APA/MLA/Chicago/IEEE/GB7714/Nature |
| DOIVerifier | ✅ 已实现 | CrossRef API 验证 |
| CitationExtractor | ✅ 已实现 | 提取引用标记 |
| CitationTracker | ✅ 已实现 | 答案溯源 |
| CitationStyle 枚举 | ✅ 已实现 | 样式定义 |

## 核心功能

### 1. CitationFormatter

参考文献格式化，支持多种引用样式：

```python
from src.agents_v2.citation import CitationFormatter

formatter = CitationFormatter()
paper = {
    "title": "Attention Is All You Need",
    "authors": ["Vaswani", "Shazeer"],
    "year": "2017",
    "journal": "NeurIPS",
}
formatted = formatter.format(paper, style='apa')
```

### 2. DOIVerifier

DOI格式验证和元数据获取：

```python
from src.agents_v2.citation import DOIVerifier

verifier = DOIVerifier()
result = verifier.verify("10.48550/arXiv.1706.03762")
```

### 3. CitationExtractor

从文本提取引用标记：
- `[1]`, `[2,3]` - 数字引用
- `(Smith, 2020)` - 作者年引用

### 4. CitationTracker

答案溯源追踪，记录答案中每个声明的来源。

## 向后兼容

| 旧模块 | 替代模块 | 状态 |
|--------|----------|------|
| `paper_search/citation_manager` | `citation/CitationFormatter` | 保留 |
| `writing/citation_generator` | `citation/CitationFormatter` | 保留 |
| `academic_qa/citation_tracker` | `citation/CitationTracker` | 保留 |

## 使用示例

```python
from src.agents_v2.citation import (
    CitationFormatter,   # 格式化引用（APA/MLA/GB7714等）
    DOIVerifier,         # DOI验证和元数据获取
    CitationExtractor,   # 从文本提取引用标记
    CitationTracker,     # 答案溯源追踪
    CitationStyle,       # 引用样式枚举
    format_citation,     # 便捷函数
)
```

---

**版本**：v1.0
**更新日期**：2026-05-04