# search 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/search/search-system.md` + `docs/research/arxiv_rate_limit_solutions.md`
> 现状：6源搜索（ArXiv/PubMed/Semantic Scholar/OpenAlex/CrossRef）已实现

---

## 一、模块概述

### 1.1 现有架构

```
search/
├── base_searcher.py            # 搜索器基类 ✅
├── arxiv_searcher.py          # ArXiv API ✅
├── pubmed_searcher.py         # PubMed API ✅
├── semantic_scholar_searcher.py # Semantic Scholar ✅
├── openalex_searcher.py      # OpenAlex API ✅
├── crossref_searcher.py      # CrossRef API ✅
├── paper_search.py           # 多源聚合搜索 ✅
├── paper_flash.py            # 快速搜索 ✅
├── query_parser.py           # 查询解析 ✅
├── search_factory.py        # 搜索工厂 ✅
└── search_result_merger.py  # 结果合并 ✅

paper_search/
├── paper_search.py           # 论文搜索 Agent ✅
├── paper_flash.py           # 快速搜索 ✅
├── query_router.py          # 查询路由 ✅
├── citation_manager.py      # 引用管理 ✅
└── report_generator.py      # 报告生成 ✅
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **协议层** | 直接 API 调用 | MCP Server 封装 |
| **速率限制** | 基础限流 | 智能限流 + 退避重试 |
| **结果质量** | 基础评分 | LLM 评分 + 去重 |
| **多语言** | 英文为主 | 中英文混合检索 |

---

## 二、任务清单

### 2.1 MCP Server 封装（P0）

**目标**：将学术搜索封装为标准 MCP Server

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| ArXiv MCP Server | P0 | ArXiv 搜索 MCP 工具 | `src/agents_v2/mcp/arxiv_server.py` |
| PubMed MCP Server | P0 | PubMed 搜索 MCP 工具 | `src/agents_v2/mcp/pubmed_server.py` |
| Semantic Scholar MCP Server | P0 | SS 搜索 MCP 工具 | `src/agents_v2/mcp/ss_server.py` |
| MCP 客户端集成 | P0 | 通过 MCP 调用搜索 | `src/agents_v2/core/mcp_client.py` |

### 2.2 速率限制增强（P1）

**目标**：解决 ArXiv 限流问题

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 指数退避重试 | P1 | 基础 + jitter | `src/agents_v2/search/rate_limiter.py` |
| 令牌桶算法 | P1 | 平滑限流 | `src/agents_v2/search/token_bucket.py` |
| 分布式限流 | P2 | Redis 协调 | `src/agents_v2/search/distributed_limiter.py` |
| 备源自动切换 | P1 | 限流时切换数据源 | `src/agents_v2/search/fallback_router.py` |

### 2.3 结果质量优化（P1）

**目标**：提升搜索结果相关性

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| LLM 评分筛选 | P1 | Top 20 评分 | `src/agents_v2/search/scorer.py` |
| 去重机制 | P1 | DOI/标题去重 | `src/agents_v2/search/deduplicator.py` |
| 结果融合 | P1 | RRF/MRR 融合 | `src/agents_v2/search/result_fuser.py` |
| 相关性反馈 | P2 | 用户反馈学习 | `src/agents_v2/search/relevance_feedback.py` |

### 2.4 多语言支持（P2）

**目标**：支持中英文混合检索

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 中文查询翻译 | P2 | 中→英翻译 | `src/agents_v2/search/query_translator.py` |
| 中文论文源 | P2 | CNKI/万方适配 | `src/agents_v2/search/cnki_searcher.py` |
| 多语言排序 | P2 | 语言权重调整 | `src/agents_v2/search/multilingual_ranker.py` |

---

## 三、ArXiv 限流解决方案

### 3.1 问题分析

ArXiv API 限制：
- 1秒1请求（严格）
- 2秒内最多3请求
- 8秒内最多10请求

### 3.2 解决方案

```python
class ArxivRateLimiter:
    """ArXiv 智能限流器"""

    def __init__(self):
        self.last_request_time = 0
        self.request_count = 0
        self.window_start = time.time()

    async def acquire(self):
        """获取请求许可"""
        current_time = time.time()
        elapsed = current_time - self.window_start

        # 8秒窗口重置
        if elapsed > 8:
            self.request_count = 0
            self.window_start = current_time

        # 检查限制
        if self.request_count >= 10:
            wait_time = 8 - elapsed + random.uniform(0.1, 0.5)
            await asyncio.sleep(wait_time)
            self.request_count = 0
            self.window_start = time.time()

        # 确保1秒间隔
        time_since_last = current_time - self.last_request_time
        if time_since_last < 1.0:
            await asyncio.sleep(1.0 - time_since_last)

        self.request_count += 1
        self.last_request_time = time.time()
```

### 3.3 备源自动切换

```python
async def search_with_fallback(query: str, max_results: int = 10) -> List[Paper]:
    """带自动切换的搜索"""

    sources = [
        ArxivSearcher(),
        PubMedSearcher(),
        SemanticScholarSearcher(),
    ]

    for source in sources:
        try:
            # 限流获取许可
            await source.rate_limiter.acquire()

            # 执行搜索
            return await source.search(query, max_results)

        except RateLimitError:
            # 限流时切换到下一个源
            continue

    # 所有源都失败
    raise SearchError("所有数据源均不可用")
```

---

## 四、实施计划

### Phase 1：MCP Server 封装（1周）

```
Day 1-2:
  - ArXiv MCP Server 实现
  - PubMed MCP Server 实现

Day 3-4:
  - Semantic Scholar MCP Server 实现
  - MCP 客户端集成

Day 5:
  - 测试验证
```

### Phase 2：速率限制增强（1周）

```
Day 1-2:
  - 指数退避重试实现
  - 令牌桶算法实现

Day 3-4:
  - 备源自动切换实现
  - 分布式限流（可选）

Day 5:
  - 压测验证
```

### Phase 3：结果质量优化（1周）

```
Day 1-2:
  - LLM 评分筛选实现
  - 去重机制实现

Day 3-4:
  - 结果融合实现
  - 相关性反馈（可选）

Day 5:
  - A/B 测试验证
```

---

## 五、验收标准

- [ ] ArXiv/PubMed/SS MCP Server 正常工作
- [ ] 限流情况下自动切换备源
- [ ] 搜索结果 Top 20 经 LLM 评分
- [ ] DOI 去重正常工作
- [ ] 8秒内10请求不触发限流

---

**版本**：v1.0
**规划日期**：2026-05-02
