# Search 模块

> 版本：v1.0
> 更新日期：2026-05-04
> 状态：**已实现**

## 概述

统一搜索编排模块，聚合多源学术搜索，支持结果合并去重。

## 目录结构

```
search/
├── __init__.py                  # 统一导出
├── arxiv_searcher.py            # arXiv搜索
├── pubmed_searcher.py           # PubMed搜索
├── semantic_scholar_searcher.py # Semantic Scholar搜索
├── openalex_searcher.py        # OpenAlex搜索
├── crossref_searcher.py        # CrossRef搜索
├── search_orchestrator.py       # 搜索编排器
├── search_result_merger.py      # 结果合并去重
├── base_searcher.py            # 搜索基类
├── base_advanced_searcher.py   # 高级搜索基类
├── enhanced_base_searcher.py   # 增强搜索基类
├── paper_search.py             # 论文搜索
├── query_parser.py            # 查询解析
├── cache_manager.py           # 缓存管理
├── rate_manager.py            # 速率限制
├── search_factory.py          # 搜索工厂
└── strategies.py             # 搜索策略
```

## 核心功能

### ArxivSearcher

arXiv 学术论文搜索，支持：
- 关键词搜索
- 分类筛选
- 作者搜索
- 结果排序

### PubmedSearcher

PubMed 生物医学文献搜索，支持：
- MeSH 术语
- 期刊筛选
- 时间范围

### SemanticScholarSearcher

Semantic Scholar 搜索，支持：
- 论文引用图
- 推荐论文
- 作者信息

### OpenAlexSearcher

OpenAlex 开放学术搜索，支持：
- 跨出版社统一标识
- 机构关联
- 主题分类

### SearchOrchestrator

搜索编排器，负责任务分发和结果聚合：

```python
from src.agents_v2.search import SearchOrchestrator, SearchResultMerger

orchestrator = SearchOrchestrator()
results = orchestrator.search(
    query="transformer architecture",
    sources=["arxiv", "pubmed", "semantic_scholar"],
    max_results=20
)
```

### SearchResultMerger

结果合并去重，基于：
- DOI 去重
- 相似度去重
- 相关性评分

## 搜索策略

| 策略 | 说明 |
|------|------|
| `DIRECT` | 直接搜索 |
| `DEPTH_FIRST` | 深度优先探索 |
| `BREADTH_FIRST` | 广度优先探索 |
| `HYBRID` | 混合策略 |

## 速率限制

各搜索源有独立的速率限制器，防止请求过载。

## 与旧模块对应

| 旧模块 | 替代模块 | 状态 |
|--------|----------|------|
| 多源搜索 | `search/` 统一模块 | 重构 |

---

**版本**：v1.0
**更新日期**：2026-05-04