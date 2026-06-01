# 搜索引擎技术文档

> 融合自：search-module.md、学术论文搜索开发报告.md、搜索性能优化报告.md、arxiv_rate_limit_solutions.md
> 更新时间：2026-05-31

---

## 1. 搜索模块概述

### 1.1 搜索源

| 来源 | 免费 | 字段搜索 | 说明 |
|------|------|---------|------|
| OpenAlex | 是 | title | 主力全学科搜索，覆盖最广 |
| arXiv | 是 | title/author/abstract | CS/物理/数学预印本 |
| Semantic Scholar | 是 | 仅全文 | AI/CS 引用网络，TLDR |

### 1.2 搜索模式

| 模式 | OpenAlex | arXiv | S2 |
|------|----------|-------|-----|
| `all` | 支持 | 支持 | 支持 |
| `title` | 支持 | 支持 | 降级为all |
| `author` | 降级为all | 支持 | 降级为all |
| `abstract` | 降级为all | 支持 | 降级为all |

### 1.3 API 端点

```
POST /api/rw/projects/{project_id}/papers/search
```

---

## 2. 排序算法

### 2.1 相关性：TF + 查询词覆盖率

```
relevance = weighted_tf × coverage
```

| 字段 | 权重 | 说明 |
|------|------|------|
| title | 3.0 | 标题最能反映论文主题 |
| keywords | 2.5 | 关键词高度相关 |
| abstract | 1.5 | 摘要是核心内容 |
| concepts | 1.0 | OpenAlex 概念标签 |
| venue | 0.5 | 期刊/会议名 |

### 2.2 最终分数

```
final_score = 0.55 × relevance + 0.25 × quality + 0.20 × source_priority
```

### 2.3 质量分

```
quality_score = 0.75 × citation + 0.10 × velocity + 0.15 × recency
```

- 引用归一化：平方根归一化（区分度优于 log）
- 新近性衰减：`recency = e^(-0.08 × age)`

### 2.4 过滤策略（推荐）

实际测试表明三阶段过滤优于 final_score 单阈值：

| 阶段 | 阈值 | 效果 |
|------|------|------|
| 相关性过滤 | relevance ≥ 0.8 | 精准率 45% → 100% |
| 质量过滤 | quality ≥ 0.12 | 进一步收窄 |
| LLM过滤 | 大模型判断 | 精准率最高，但耗时+27s |

> **为什么不使用 final_score？** quality_score（75%权重来自引用数）被高引论文拉偏，导致绝大多数论文 final_score 被压到 0.55~0.75，阈值失效。

---

## 3. 去重合并

### 3.1 去重优先级

1. DOI 精确匹配
2. arXiv ID 匹配（忽略版本号）
3. OpenAlex/S2/PubMed ID 匹配
4. 标题 Jaccard 相似度 ≥ 0.85

### 3.2 合并策略

标题相同时，优先保留：来源优先级更高 → 年份更新 → 引用数更高

### 3.3 RRF 融合排序

多源结果合并使用 Reciprocal Rank Fusion：

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

k 通常取 60。

---

## 4. 性能优化

### 4.1 已完成优化

| 优化项 | 优化前 | 优化后 | 效果 |
|--------|--------|--------|------|
| ArXiv 批量搜索 | O(n×T) 串行 | O(T) asyncio.gather | 1.6x 加速 |
| 多源并发 | 3个源并行 | 5个源并行 | 67% 提升 |
| 熔断机制 | 无 | 60s窗口 | 故障隔离 |
| CrossRef限流 | 无控制 | RateManager | 避免429 |

### 4.2 后续优化方向

- 结果合并算法：O(n²) 标题相似度 → SimHash 优化
- 缓存预热：高频查询主动预填充
- 语义缓存：Embedding 相似度命中

---

## 5. arXiv 限流处理

### 5.1 官方限制

| 限制类型 | 数值 |
|---------|------|
| 请求间隔 | ≥ 3 秒/次 |
| 每小时上限 | ~4000 次 |
| 单次最大结果 | 2000 条 |
| 每日建议 | < 5000 次 |

### 5.2 应对策略

| 策略 | 说明 |
|------|------|
| 请求间隔 | 所有请求间加 3s sleep |
| 指数退避 | 429 响应时 2^n 秒重试 |
| 批量控制 | `max_results_per_query` 限制单次返回 |
| 缓存 | arXiv 查询 TTL 6 小时 |
| 熔断 | 连续失败 3 次后跳过 60s |
| 备选源 | OpenAlex 覆盖 arXiv 大部分论文 |

### 5.3 已知问题

- Windows 环境下 SSL 证书验证失败
- arXiv API 对同一论文多版本返回多条记录（已去重）

---

## 6. 缓存策略

| 查询类型 | TTL |
|---------|-----|
| 普通关键词 | 24 小时 |
| DOI 查询 | 7 天 |
| arXiv 查询 | 6 小时 |

缓存 key：query + sources + limit + offset + year_from + year_to + field

---

## 7. 已知限制

| 问题 | 说明 |
|------|------|
| Semantic Scholar 限流 | 无 API key 时 429，已有自动重试 |
| OpenAlex 作者搜索 | `author.display_name.search` 不可靠，降级为全文 |
| 同一论文多版本 | 去重已生效，但同一本书不同年份可能保留最新版 |
