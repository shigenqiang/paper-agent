# 搜索质量与文献选取技术文档

> 融合自：学术文献选取机制调研报告.md、论文搜索去重优化方案.md、search-quality-report.md
> 更新时间：2026-05-31

---

## 1. 核心算法

### 1.1 BM25

学术文献选取的基础排序算法。

```
BM25(q,d) = Σ IDF(qi) × (f(qi,d) × (k1+1)) / (f(qi,d) + k1 × (1 - b + b × |d|/avgdl))
```

- k1 = 1.2, b = 0.75（典型参数）
- 优势：词频饱和、文档长度归一化
- 劣势：仅词袋模型，无语义理解

### 1.2 TF-IDF

经典基线，BM25 的简化版。

```
TF-IDF(t,d) = TF(t,d) × log(N/DF(t))
```

### 1.3 Learning to Rank

| 类型 | 方法 | 特点 |
|------|------|------|
| Pointwise | 回归/分类 | 独立预测每个文档分数 |
| Pairwise | RankNet, LambdaRank | 学习文档对的偏序关系 |
| Listwise | ListNet, LambdaMART | 直接优化整个排序列表 |

### 1.4 语义检索

| 方法 | 原理 | 适用场景 |
|------|------|---------|
| Dense Retrieval | Embedding 向量相似度 | 语义匹配 |
| Sparse Retrieval | BM25/TF-IDF | 关键词精确匹配 |
| Hybrid | Dense + Sparse + Reranker | 最佳综合效果 |

---

## 2. 质量评估指标

### 2.1 期刊/会议级别

| 指标 | 说明 | 局限 |
|------|------|------|
| 影响因子 (IF) | JCR 两年引用平均 | 学科不可比、受自引影响 |
| H-index | 作者/期刊产出+影响力 | 对年轻学者不公平 |
| SJR | Scopus 权威指标 | 需付费 |
| JCI | JCR 引用指标归一化 | 较新 |

### 2.2 论文级别

| 指标 | 说明 |
|------|------|
| 被引次数 | 最直接的影响力指标 |
| 引用速度 | 年均引用数 |
| Altmetric | 社交媒体关注度 |
| FWCI | 领域归一化引用 |

### 2.3 我们的质量分公式

```
quality_score = 0.75 × citation_norm + 0.10 × velocity + 0.15 × recency
```

- citation_norm = √citations / √max_citations（平方根归一化，区分度优于 log）
- velocity = log(1 + citations/age)（年均引用，log 压缩）
- recency = e^(-0.08 × age)（指数衰减，经典论文更宽容）

---

## 3. 去重技术

### 3.1 去重层级

| 层级 | 方法 | 说明 |
|------|------|------|
| 精确去重 | DOI / arXiv ID / OpenAlex ID | 最可靠 |
| 近似去重 | 标题 Jaccard ≥ 0.85 | 处理微小差异 |
| 语义去重 | Embedding 余弦相似度 ≥ 0.95 | 处理同义改写 |

### 3.2 RRF 融合排序

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

- k = 60（标准值）
- 适用于多源结果合并
- 不依赖原始分数，只依赖排名

### 3.3 缓存策略

| 策略 | 适用场景 |
|------|---------|
| LRU | 热点查询频繁重复 |
| LFU | 长期稳定的高频查询 |
| 语义缓存 | Embedding 相似度命中相似查询 |

---

## 4. 学术文献选取方法论

### 4.1 系统性综述 (PRISMA)

```
Identification → Screening → Eligibility → Included
   检索文献       初筛          全文评估       纳入分析
```

### 4.2 可视化工具

| 工具 | 特点 |
|------|------|
| Connected Papers | 引用图谱可视化 |
| Litmaps | 文献地图 |
| Research Rabbit | 论文推荐 |
| Elicit | AI 辅助文献综述 |

### 4.3 研究空白识别

- 引用网络中的结构洞（structural holes）
- 关键词共现网络的弱连接区域
- 时间维度上的研究趋势断层

---

## 5. 搜索质量测试报告

### 5.1 测试配置

- 查询：`sparse functional data for deep learning`
- 数据源：OpenAlex, arXiv, Semantic Scholar
- 返回上限：50

### 5.2 各阶段过滤效果

| 阶段 | 论文数 | 相关 | 精准率 | 召回率 | 耗时 |
|------|--------|------|--------|--------|------|
| BM25排序 | 49 | 22 | 45% | 100% | 33.7s |
| + relevance ≥ 0.8 | 9 | 9 | 100% | 41% | 33.7s |
| + quality ≥ 0.12 | 7 | 7 | 100% | 32% | 33.7s |
| + LLM过滤 | 1 | 1 | 100% | 5% | 60.8s |

### 5.3 结论

- **最佳平衡**：relevance ≥ 0.8（100% 精准率，41% 召回率，无额外耗时）
- **最高精准**：三阶段全开（100% 精准率，但召回率仅 5%，耗时 +27s）
- **建议**：生产环境用 relevance ≥ 0.8，需要精排时加 LLM 过滤
