# search 模块开发计划

> 状态：**已实现**
> 更新日期：2026-05-04
> 与未来框架设计 v2.1 对齐

## 模块定位

search 模块是学术搜索核心，提供：
- 6源并行搜索（ArXiv/PubMed/SS/OpenAlex/CrossRef）
- MCP Server 标准化封装
- 智能速率限制
- 结果质量优化

## 实现状态

| 组件 | 状态 | 说明 |
|------|------|------|
| ArxivSearcher | ✅ 已实现 | arXiv搜索 |
| PubmedSearcher | ✅ 已实现 | PubMed搜索 |
| SemanticScholarSearcher | ✅ 已实现 | Semantic Scholar搜索 |
| OpenAlexSearcher | ✅ 已实现 | OpenAlex搜索 |
| CrossrefSearcher | ✅ 已实现 | CrossRef搜索 |
| SearchOrchestrator | ✅ 已实现 | 搜索编排器 |
| SearchResultMerger | ✅ 已实现 | 结果合并去重 |
| CacheManager | ✅ 已实现 | 缓存管理 |
| RateManager | ✅ 已实现 | 速率限制 |

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

## 使用示例

```python
from src.agents_v2.search import (
    ArxivSearcher,           # arXiv搜索
    PubmedSearcher,          # PubMed搜索
    SemanticScholarSearcher, # Semantic Scholar搜索
    OpenAlexSearcher,        # OpenAlex搜索
    SearchOrchestrator,     # 搜索编排器
    SearchResultMerger,      # 结果合并去重
)

# 多源搜索
orchestrator = SearchOrchestrator()
results = orchestrator.search(
    query="深度学习医学影像",
    sources=["arxiv", "pubmed", "openalex"],
    max_results=30
)
```

## 详细计划

见 `search模块开发计划.md`（规划增强功能）

---

**版本**：v1.1
**更新日期**：2026-05-04
