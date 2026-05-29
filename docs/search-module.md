# 论文搜索模块

> 更新时间: 2026-05-29

## 1. 概述

搜索模块负责从多个学术数据源检索论文，支持关键词搜索、字段级搜索、去重合并和质量排序。

## 2. 搜索源

| 来源 | 免费 | 字段搜索 | 说明 |
|------|------|---------|------|
| OpenAlex | ✅ | title | 主力全学科搜索，覆盖最广 |
| arXiv | ✅ | title/author/abstract | CS/物理/数学预印本 |
| CrossRef | ✅ | title/author | DOI 元数据补全 |
| Semantic Scholar | ✅ | 仅全文 | AI/CS 引用网络，TLDR |

## 3. 搜索模式 (SearchField)

通过 `field` 参数控制搜索范围：

| 模式 | 说明 | OpenAlex | arXiv | CrossRef | S2 |
|------|------|----------|-------|----------|-----|
| `all` | 全文搜索（默认） | ✅ | ✅ | ✅ | ✅ |
| `title` | 仅搜索标题 | ✅ | ✅ | ✅ | 降级为 all |
| `author` | 仅搜索作者 | 降级为 all | ✅ | ✅ | 降级为 all |
| `abstract` | 仅搜索摘要 | 降级为 all | ✅ | 降级为 all | 降级为 all |

**降级策略：** 不支持某字段模式的 adapter 自动降级为 `all`。

### API 用法

```json
{
  "query": "transformer attention",
  "field": "title",
  "sources": ["openalex", "arxiv"],
  "limit": 10
}
```

## 4. 排序算法

### 4.1 最终分数公式

```
final_score = 0.35 × relevance + 0.50 × quality + 0.15 × source_priority
```

| 组件 | 权重 | 说明 |
|------|------|------|
| relevance | 35% | BM25 相关性，基于查询词在标题/摘要/关键词中的匹配 |
| quality | 50% | 论文质量综合分 |
| source_priority | 15% | 来源优先级（OpenAlex 0.9, S2 0.8, arXiv 0.7） |

### 4.2 质量分 (quality_score)

```
quality_score = 0.75 × citation + 0.10 × velocity + 0.15 × recency
```

| 组件 | 权重 | 计算方式 |
|------|------|---------|
| citation | 75% | √citations / √max_citations（平方根归一化） |
| velocity | 10% | citations / age（年均引用数，log 压缩） |
| recency | 15% | e^(-0.08 × age)（指数衰减） |

### 4.3 引用数归一化

使用**平方根归一化**而非 log 归一化，以提供更好的高引用论文区分度：

```
citation_norm = √citations / √max_citations
```

**对比：**
- log 归一化：log(1+11298) / log(1+29704) = 0.906，差距 0.047
- 平方根归一化：√11298 / √29704 = 0.617，差距 0.134

平方根对高引用论文的区分度更好。

### 4.4 新近性衰减

```
recency = e^(-0.08 × age)
```

| 论文年龄 | recency 分数 |
|---------|-------------|
| 1 年 | 0.92 |
| 5 年 | 0.67 |
| 10 年 | 0.45 |
| 20 年 | 0.20 |

对经典论文更宽容（衰减率 0.08，之前为 0.15）。

## 5. 去重合并

### 5.1 去重优先级

1. DOI 精确匹配
2. arXiv ID 匹配（忽略版本号）
3. OpenAlex/S2/PubMed ID 匹配
4. 标题 Jaccard 相似度 ≥ 0.95

### 5.2 合并策略

当标题相同时，优先保留：
1. 来源优先级更高者
2. 年份更新者
3. 引用数更高者

## 6. 并行搜索

多个搜索源通过 `ThreadPoolExecutor` 并行调用，总延迟 = max(各源延迟) 而非 sum。

## 7. 缓存

| 查询类型 | TTL |
|---------|-----|
| 普通关键词 | 24 小时 |
| DOI 查询 | 7 天 |
| arXiv 查询 | 6 小时 |

缓存 key 包含：query、sources、limit、offset、year_from、year_to、field。

## 8. API 端点

```
POST /api/rw/projects/{project_id}/papers/search
```

请求参数：

```json
{
  "query": "reinforcement learning",
  "sources": ["openalex", "arxiv", "semantic_scholar"],
  "limit": 10,
  "offset": 0,
  "year_from": 2020,
  "year_to": 2026,
  "field": "all",
  "use_cache": true,
  "force_refresh": false
}
```

响应：

```json
{
  "data": {
    "session_id": "ss_xxx",
    "results": [...],
    "result_count": 10
  }
}
```

## 9. 已知限制

| 问题 | 说明 |
|------|------|
| arXiv SSL | Windows 环境下 SSL 证书验证失败 |
| Semantic Scholar 限流 | 无 API key 时被 429 限流 |
| OpenAlex 作者搜索 | `author.display_name.search` 过滤不可靠，降级为全文 |
| 同一论文多版本 | 去重已生效，但同一本书不同年份可能保留最新版 |
