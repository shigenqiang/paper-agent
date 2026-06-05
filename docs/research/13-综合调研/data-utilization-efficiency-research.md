# 生产级 RAG 系统数据利用率与存储架构调研报告

> 调研日期: 2026-05-30
> 搜索次数: 22次
> 核心问题: 关系数据库 + 向量数据库 + 知识图谱的三库架构是否存在数据冗余？数据利用率是否太低？

---

## 一、核心结论

**你的三库架构不是数据冗余，而是业界标准做法。**

生产系统的共识是：

```
PostgreSQL（关系数据库）= 数据源真相（Source of Truth）
向量数据库               = 派生索引（Derived Index）
知识图谱                 = 派生索引（Derived Index）
```

**向量和图谱本质上是 PostgreSQL 数据的"索引"，不是"副本"。** 就像书的目录不是书的重复，而是帮你快速定位内容的工具。

---

## 二、生产系统实际做法

### 2.1 MangoApps（2026年5月）— 向量不需要备份

MangoApps 工程团队在 2026 年 5 月明确表态：

> "Every embedding was computed from text we still have. The fingerprint is derived from the source the way a thumbnail is derived from a photo. You don't carefully back up thumbnails. If you lose one, you regenerate it from the photo."

**向量是派生数据**。每个 embedding 都是从原文计算出来的，原文还在 PostgreSQL 里。向量数据库挂了？从 PostgreSQL 重新生成即可。

来源: https://www.mangoapps.com/articles/dont-back-up-your-vector-database

### 2.2 Encore Blog — pgvector 消除同步问题

> "With a dedicated vector database, you store documents in Postgres and embeddings in a separate service. When you add a document, you write to both. When you delete one, you delete from both. If one write fails, you have either a document with no embedding or an orphaned vector. Keeping them in sync requires careful error handling or a background reconciliation job. With pgvector, it's a single INSERT statement."

**独立向量数据库需要同步**，pgvector 消除了这个问题。

来源: https://encore.dev/blog/you-probably-dont-need-a-vector-database

### 2.3 DBA Perspective（2025）— PostgreSQL 赢在 90% 场景

传统向量数据库架构需要 10 步：
```
1. 用户数据进入 PostgreSQL
2. 应用提取文本用于 embedding
3. 通过 API 生成 embedding
4. 写入向量数据库
5. 写入 PostgreSQL 元数据
6. 维护两者同步
7. 处理一致性问题
8. 监控两套系统
9. 备份两套系统
10. 独立扩展两套系统
```

PostgreSQL + pgvector 架构只需 3 步：
```
1. 用户数据进入 PostgreSQL
2. 通过 API 生成 embedding
3. 存入同一数据库。完成。
```

来源: https://dbadataverse.com/tech/postgresql/2025/12/postgresql-beat-vector-databases-dba-perspective

### 2.4 腾讯云/53AI（2025）— 中国企业的混合架构

> "企业级RAG的最佳方案是混合架构：向量数据库处理模糊语义查询，知识图谱处理结构化关系查询。"

数据存储层采用三库分离：
```
数据存储层
├── 文献数据库（关系型）
├── 图数据库（Neo4j）
└── 向量数据库（Milvus）
```

来源: https://cloud.tencent.com/developer/article/2590342

### 2.5 Elicit — 结构化提取 + 表格

Elicit 的数据流：
```
PDF → 解析 → 结构化表格（每列一个 prompt）
     → 交互式表格（带引用）
     → 研究报告生成
```

**没有使用知识图谱**，而是用表格 + 引用来组织数据。向量用于语义搜索，关系表用于结构化提取。

来源: https://elicit.com/blog/living-documents-ai-ux

### 2.6 Scopus AI — RAG + 重排

> "Scopus AI uses custom RAG architecture including models and prompts on abstracts in Scopus; it consists of a search module, reranking and a large language model module for text generation."

**只在摘要上做 RAG**，不做全文向量化。元数据存在关系库，向量存在搜索模块。

来源: https://scholarlykitchen.sspnet.org/2024/07/25/interview-with-maxim-khan-about-scopus-ai

### 2.7 Paper Circle（ACL 2026）— 多源聚合 + KG

```
Discovery Pipeline: arXiv + Semantic Scholar + OpenAlex + DBLP → 并行查询 → 去重 → 评分
Analysis Pipeline:  PDF → PyMuPDF解析 → 知识图谱构建 → 图感知QA
```

**KG 是从解析数据中提取构建的**，不是直接存 PDF。

来源: https://arxiv.org/html/2604.06170v1

### 2.8 LightRAG（EMNLP 2025）— 图 + 向量双索引

LightRAG 的实体存储结构：
```json
{
  "_id": "ent-8b14c7...",
  "entity_name": "Alex",
  "entity_type": "person",
  "content": "Alex is a character who is highly observant...",
  "source_id": "chunk-123|||chunk-456",
  "vector": [0.015, -0.782, 0.431, ...]
}
```

**每个实体/关系都有向量表示**，用于语义搜索。图结构用于关系遍历。两者并行。

来源: https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction

---

## 三、数据流向全景图

### 3.1 你的架构（正确）

```
PDF 论文
  │
  ▼
parser_service 解析
  │
  ▼
┌─────────────────────────────────────────────────┐
│            PostgreSQL（数据源真相）                │
│                                                   │
│  papers        ← 论文元数据                       │
│  paper_chunks  ← 解析后的文本分块                  │
│  paper_cards   ← 论文卡片                         │
│  paper_entities ← 提取的实体                      │
│  paper_relations ← 提取的关系                     │
│  paper_results  ← 量化结果                        │
│                                                   │
│  ⭐ 这是唯一的 Source of Truth                     │
│  ⭐ 其他两个库的数据都可以从这里重新生成             │
└────────────────┬────────────────────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  向量库       │    │  知识图谱     │
│  (pgvector/  │    │  (Neo4j)     │
│   Qdrant)    │    │              │
│              │    │              │
│ chunk 向量   │    │ 实体节点      │
│ 摘要向量     │    │ 关系边        │
│              │    │              │
│ ⭐ 派生索引   │    │ ⭐ 派生索引   │
│ 可重新生成    │    │ 可重新提取    │
└──────────────┘    └──────────────┘
```

### 3.2 数据不是存了三份

| 层次 | 存什么 | 数据量 | 来源 |
|------|--------|--------|------|
| PostgreSQL | 原文 chunks + 元数据 + 实体 + 关系 | 最大 | parser + LLM 提取 |
| 向量库 | 向量浮点数 + 精简 metadata | 中等 | 从 PostgreSQL 计算 |
| 知识图谱 | 节点名 + 关系名 + 属性 | 最小 | 从 PostgreSQL 提取 |

**举例**：一篇 CL-NER 论文

| 存储 | 存的内容 | 数据量 |
|------|---------|--------|
| PostgreSQL | 8000 tokens 全文 + 元数据 + 实体表 + 关系表 | ~32KB |
| 向量库 | 10 个 768 维向量 + chunk_id + section_type | ~30KB |
| 知识图谱 | 5 个节点 + 8 条边 | ~2KB |

向量库存的是**数字数组**，不是原文。知识图谱存的是**实体名称和关系**，不是全文。

---

## 四、为什么不能只用一个数据库？

### 4.1 查询场景对比

| 查询 | PostgreSQL | 向量库 | 知识图谱 |
|------|-----------|--------|---------|
| "找到 2024 年以后发表的论文" | 最佳 | 不适合 | 不适合 |
| "找到语义上关于 NER 的文本" | 不适合 | 最佳 | 不适合 |
| "哪些论文用了 BERT 作为基线？" | 可以（LIKE） | 不适合 | 最佳 |
| "对比这 5 篇论文的 F1 值" | 最佳 | 不适合 | 可以 |
| "找到关于对比学习的相关文本" | 不适合 | 最佳 | 不适合 |
| "BERT 被哪些方法改进了？" | 不适合 | 不适合 | 最佳 |
| "统计每个数据集被使用了多少次" | 最佳 | 不适合 | 可以 |

### 4.2 每个库不可替代的原因

**PostgreSQL 不可替代**：
- 精确查询（WHERE, JOIN, GROUP BY）
- 事务一致性（ACID）
- 元数据过滤和排序
- 统计分析

**向量库不可替代**：
- 语义相似度搜索（"找到关于 NER 的文本"不等于 `LIKE '%NER%'`）
- 模糊匹配（"contrastive learning" 能匹配到 "对比学习"）
- 大规模近似最近邻搜索

**知识图谱不可替代**：
- 多跳关系推理（"哪些方法改进了 BERT 并应用于 NER？"）
- 路径发现（"A 和 B 之间有什么关系？"）
- 社区发现（"这个领域的主要研究方向有哪些？"）

---

## 五、业界共识：向量是索引，不是数据

### 5.1 LinkedIn 讨论（Pavan Belagatti）

> "Vector databases are not meant to be the Source of Truth. Embeddings are inherently transient—tied to embedding models and input data—which means updates to models or data often require regenerating the entire vector store."

> "From a task-oriented perspective, vector DBs are more like indexes with extra capabilities, than traditional data stores."

来源: LinkedIn discussion on vector database selection

### 5.2 Pinecone 官方文档

> "First, we use the embedding model to create vector embeddings for the content we want to index. The vector embedding is inserted into the vector database, with some reference to the original content the embedding was created from."

**向量数据库存的是"指向原文的引用 + 数学表示"，不是原文本身。**

来源: https://www.pinecone.io/learn/vector-database

### 5.3 Digital Applied（2026）— 三表规范

生产级 RAG 的规范 schema 是三张表：
```sql
-- 1. Documents — 每个源文档一行（Source of Truth）
CREATE TABLE documents (...);

-- 2. Chunks — 每个文档的多个分块
CREATE TABLE chunks (
    document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
    content text NOT NULL,
    ...
);

-- 3. Embeddings — 每个 chunk 的向量
CREATE TABLE embeddings (
    chunk_id uuid REFERENCES chunks(id) ON DELETE CASCADE,
    vector vector(1536) NOT NULL,
    ...
);
```

**明确分离 documents（真相）→ chunks（检索单元）→ embeddings（向量索引）**。

来源: https://www.digitalapplied.com/blog/build-self-hosted-rag-postgres-pgvector-tutorial-2026

---

## 六、你的架构是否高效？

### 6.1 数据流分析

```
100 篇论文 PDF
  │
  ▼ parser_service（一次性）
PostgreSQL: 100 papers + ~1000 chunks + 元数据
  │
  ├──▶ 压缩摘要（一次性，LLM）→ 向量库: ~1000 个向量
  │
  └──▶ 实体提取（一次性，LLM）→ 知识图谱: ~500 节点 + ~1000 边
```

**每个处理步骤只做一次**，结果永久存储。之后每次查询都是直接读取，不需要重新处理。

### 6.2 与"只用一个库"的对比

| 方案 | 优势 | 劣势 |
|------|------|------|
| 只用 PostgreSQL | 简单、无同步、事务一致 | 语义搜索能力弱，无法做图遍历 |
| 只用向量库 | 语义搜索强 | 无法精确查询、无法统计、无法 JOIN |
| 只用图库 | 关系推理强 | 全文检索弱、聚合统计弱 |
| **三库混合** | **所有查询场景都能覆盖** | **架构复杂度高** |

### 6.3 真正的效率衡量标准

数据利用率不是"存了几份"，而是"每份是否在被查询时发挥了不可替代的作用"。

| 指标 | 你的架构 | 说明 |
|------|---------|------|
| 数据源唯一性 | PostgreSQL 是唯一真相 | 向量和图谱可从 PostgreSQL 重建 |
| 查询场景覆盖 | 3/3（精确 + 语义 + 关系） | 每种查询都有最优路径 |
| 重复存储 | 无（向量存数字，图谱存名称） | 不是原文存三份 |
| 处理次数 | 每篇论文只处理一次 | 结果持久化 |
| 可恢复性 | 向量/图谱丢失可重建 | 原文在 PostgreSQL |

---

## 七、优化建议

### 7.1 推荐：PostgreSQL + pgvector（合并前两层）

```
PostgreSQL
├── papers          ← 论文元数据
├── paper_chunks    ← 解析后的文本分块
│   └── embedding   ← vector(768) 列（pgvector）
├── paper_entities  ← 提取的实体
├── paper_relations ← 提取的关系
└── paper_results   ← 量化结果
```

**优势**：
- 一个数据库，无同步问题
- 事务一致性（写入 chunk 和 embedding 是原子操作）
- SQL 可以同时查询结构化数据和向量
- 减少运维复杂度

### 7.2 知识图谱：按需引入

知识图谱是三者中构建成本最高的（需要 LLM 提取实体 + 消歧）。建议：

```
Phase 1: PostgreSQL + pgvector（当前）
  - 先跑通向量检索 + 结构化查询
  - 实体/关系存 PostgreSQL 表

Phase 2: 按需引入 Neo4j（如果图查询需求明确）
  - 从 PostgreSQL 的 paper_entities/paper_relations 导入
  - 不是替换 PostgreSQL，是补充图遍历能力
```

### 7.3 数据流优化

```
PDF → parser → PostgreSQL（chunks + 元数据）
                  │
                  ├── pgvector embedding（同一数据库内）
                  │
                  └── LLM 实体提取 → PostgreSQL entities/relations 表
                                        │
                                        └── （可选）导出到 Neo4j
```

---

## 八、关键教训

| 教训 | 来源 | 说明 |
|------|------|------|
| 向量是派生数据，不需要备份 | MangoApps 2026 | 从源数据重新生成即可 |
| 向量数据库不是 Source of Truth | LinkedIn/Pinecone | 它是索引，不是数据库 |
| pgvector 消除同步问题 | Encore Blog | 一个 INSERT 搞定 |
| 三库存的是不同维度的信息 | 多个来源 | 不是同一份数据存三次 |
| 先跑通最简单的方案 | 业界共识 | PostgreSQL + pgvector 先行 |
| 知识图谱构建成本最高 | TianPan.co | 按需引入，不要过早优化 |

---

## 九、参考资料

### 官方文档与产品
1. MangoApps - "Don't Back Up Your Vector Database" - https://www.mangoapps.com/articles/dont-back-up-your-vector-database (2026.05)
2. Encore Blog - "You Probably Don't Need a Vector Database" - https://encore.dev/blog/you-probably-dont-need-a-vector-database
3. Pinecone - "What is a Vector Database" - https://www.pinecone.io/learn/vector-database
4. Elicit - "Living Documents as a UX Pattern" - https://elicit.com/blog/living-documents-ai-ux
5. Scopus AI Interview - https://scholarlykitchen.sspnet.org/2024/07/25/interview-with-maxim-khan-about-scopus-ai
6. Iris.ai Researcher Workspace - https://iris.ai/blog/introduction-to-researcher-workspace

### 技术博客与最佳实践
7. DBA Perspective - "PostgreSQL vs Vector Database: Why PostgreSQL Wins" - https://dbadataverse.com/tech/postgresql/2025/12/postgresql-beat-vector-databases-dba-perspective
8. Digital Applied - "Build Self-Hosted RAG with Postgres pgvector" - https://www.digitalapplied.com/blog/build-self-hosted-rag-postgres-pgvector-tutorial-2026
9. Applied AI - "Enterprise RAG Architecture: A Practitioner's Guide" - https://www.applied-ai.com/briefings/enterprise-rag-architecture (2025.11)
10. TianPan.co - "GraphRAG vs Vector RAG" - https://tianpan.co/zh/blog/2026-04-17-graphrag-vs-vector-rag-knowledge-graphs
11. Medium - "RAG IX — Parent Document Retriever" - https://medium.com/@danushidk507/rag-ix-parent-document-retriever
12. DEV Community - "Optimizing RAG Indexing Strategy" - https://dev.to/jamesli/optimizing-rag-indexing-strategy-multi-vector-indexing-and-parent-document-retrieval-49hf
13. Medium - "Advanced RAG 01: Small-to-Big Retrieval" - https://medium.com/data-science/advanced-rag-01-small-to-big-retrieval-172181b396d4

### 学术论文与框架
14. Paper Circle - ACL 2026 Oral - https://arxiv.org/html/2604.06170v1
15. Neo4j - "Under the Covers With LightRAG: Extraction" - https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction
16. Atlan - "What Is GraphRAG?" - https://atlan.com/know/what-is-graphrag
17. Medium - "GraphRAG on Postgres: A Builder's Guide" - https://medium.com/@duckweave/graphrag-on-postgres-a-builders-guide-1c6d2ecf2eed

### 中文资源
18. 腾讯云 - "文献综述自动化：引用追踪驱动的知识图谱构建" - https://cloud.tencent.com/developer/article/2590342
19. 53AI - "RAG知识库的数据方案：图数据库、向量数据库和知识图谱怎么选？" - https://www.53ai.com/news/knowledgegraph/2025032984091.html
20. 博客园 - "更强的RAG：向量数据库和知识图谱的结合" - https://www.cnblogs.com/hohoa/p/18456986
21. 腾讯云 - "向量存储vs知识图谱：LLM记忆系统技术选型" - https://cloud.tencent.com/developer/article/2588369
22. 53AI - "RAG彻底爆了！一文掌握其效果优化的架构设计及核心要点" - https://www.53ai.com/news/RAG/2025091519370.html
