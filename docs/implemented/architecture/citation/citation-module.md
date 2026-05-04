# Citation 模块

> 版本：v1.0
> 更新日期：2026-05-04
> 状态：**已实现**

## 概述

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

## 核心功能

### CitationFormatter

参考文献格式化，支持多种引用样式：

| 样式 | 说明 |
|------|------|
| APA | 美国心理学会格式 |
| MLA | 现代语言协会格式 |
| Chicago | 芝加哥格式 |
| IEEE | 电气电子工程师学会格式 |
| GB7714 | 中国国家标准格式 |
| Nature | Nature期刊格式 |

### DOIVerifier

DOI格式验证和元数据获取（CrossRef API）：

```python
from src.agents_v2.citation import DOIVerifier

verifier = DOIVerifier()
result = verifier.verify("10.48550/arXiv.1706.03762")
# Output: {'valid': True, 'doi': '10.48550/arXiv.1706.03762', 'title': 'Attention Is All You Need', ...}
```

### CitationExtractor

从文本提取引用标记：

- `[1]`, `[2,3]` - 数字引用
- `(Smith, 2020)` - 作者年引用

### CitationTracker

答案溯源追踪，记录答案中每个声明的来源。

## 使用示例

```python
from src.agents_v2.citation import CitationFormatter, DOIVerifier, CitationExtractor, CitationTracker

# 格式化引用
formatter = CitationFormatter()
paper = {
    "title": "Attention Is All You Need",
    "authors": ["Vaswani", "Shazeer"],
    "year": "2017",
    "journal": "NeurIPS",
}
formatted = formatter.format(paper, style='apa')
```

## 与旧模块对应

| 旧模块 | 替代模块 | 状态 |
|--------|----------|------|
| `paper_search/citation_manager` | `citation/CitationFormatter` | 保留 |
| `writing/citation_generator` | `citation/CitationFormatter` | 保留 |
| `academic_qa/citation_tracker` | `citation/CitationTracker` | 保留 |

---

**版本**：v1.0
**更新日期**：2026-05-04