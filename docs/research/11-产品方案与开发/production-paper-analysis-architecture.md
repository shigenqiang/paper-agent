# 已上线论文分析产品架构调研报告

> 调研日期: 2026-05-30
> 搜索次数: 31次
> 覆盖产品: Elicit, Consensus AI, Scite, Semantic Scholar, ORKG, Connected Papers, ResearchRabbit, Iris.ai, Scopus AI, Dimensions, Paper Circle, Corvus
> 覆盖技术: GraphRAG, LightRAG, LazyGraphRAG, pgvector, Neo4j, RRF混合检索, TreeRAG, GROBID

---

## 一、已上线产品的架构分析

### 1.1 Elicit — 结构化数据提取标杆

**产品定位**: AI驱动的系统性文献综述工具，支持1.25亿+论文

**核心架构**:
```
用户查询 → 语义搜索(125M论文库) → 结果列表
                                    ↓
                            用户选择论文集
                                    ↓
                            结构化数据提取(LLM)
                            每个"列"=一个prompt
                            支持用户自定义列
                                    ↓
                            交互式表格(带引用)
                                    ↓
                            研究报告生成(最多80篇)
```

**关键技术点**:
- **列式提取**: 用户定义要提取的字段（如"样本量"、"方法"、"F1值"），Elicit用LLM从每篇论文中提取，每列一个独立prompt
- **Pilot机制**: 先在10篇论文上测试提取效果，用户验证后再批量运行
- **句子级引用**: 每个提取的数据点都链接回原文句子，支持溯源
- **抗幻觉策略**: process supervision + prompt engineering + 多模型集成 + 自定义评估

**数据流**: PDF → 解析 → 结构化表格 → 报告生成。**没有使用知识图谱**，而是用表格+引用来组织数据。

**参考来源**: support.elicit.com, intuitionlabs.ai/pdfs/elicit-ai-data-extraction-guide

### 1.2 Consensus AI — RAG+向量检索典范

**产品定位**: 基于2亿+同行评审论文的AI搜索引擎

**核心架构**:
```
用户自然语言查询
        ↓
语义搜索(Elasticsearch + ELSER稀疏向量)
        ↓
RAG生成(基于检索结果)
        ↓
Consensus Meter(科学共识度量)
        ↓
带引用的综合答案
```

**关键技术点**:
- **Elastic ELSER**: 使用Elastic Learned Sparse EncodeR进行语义检索，不需要微调
- **RAG流程**: Elastic检索结果 → ChatGPT生成摘要，高置信度搜索质量减少幻觉
- **Google Cloud部署**: Elastic与GCP深度集成
- **Consensus Meter**: 可视化科学共识程度（支持/中立/反对的比例）

**数据流**: 论文索引 → ELSER向量化 → Elastic检索 → LLM生成。**没有使用知识图谱**，纯向量RAG方案。

**参考来源**: elastic.co/customers/consensus, pmc.ncbi.nlm.nih.gov

### 1.3 Scite AI — 引用上下文分析

**产品定位**: 14亿+ Smart Citations数据库，分类引用为支持/对比/提及

**核心架构**:
```
论文全文索引 → 引用上下文提取 → 分类(支持/对比/提及)
                                    ↓
                            Scite Assistant(LLM + 引用数据库)
                                    ↓
                            带引用证据的回答
```

**关键技术点**:
- **Smart Citations**: 不仅记录谁引用了谁，还提取引用上下文并分类
- **MCP协议**: 提供MCP接口，可被Claude/ChatGPT等外部AI调用
- **Table Mode**: 类似Elicit的表格提取功能

**参考来源**: scite.ai, library guides

### 1.4 Semantic Scholar — 学术图谱基础设施

**产品定位**: AI驱动的免费学术搜索，2亿+论文

**核心架构**:
```
多来源数据聚合(CrossRef, arXiv, PubMed, ...)
        ↓
S2ORC统一数据平台(81M论文全文)
        ↓
├── 元数据提取(GROBID + 自研pipeline)
├── SPECTER2嵌入(论文级向量表示)
├── 引用图谱(引用+被引+上下文)
├── TLDR自动生成(SciTLDR模型)
└── 推荐系统(用户标注 + FAISS KNN)
```

**关键技术点**:
- **SPECTER2**: 专门为学术论文设计的嵌入模型，输入title+abstract，训练目标是让有引用关系的论文向量更近
- **S2ORC**: 最大的开放学术全文数据集，统一了多种来源的论文
- **引用意图分类**: 区分influential citation和普通引用
- **API提供预计算嵌入**: 可直接查询论文的SPECTER2向量

**参考来源**: semanticscholar.org/product/api, arxiv.org/html/2301.10140v2

### 1.5 ORKG — 结构化知识图谱

**产品定位**: Open Research Knowledge Graph，将论文贡献结构化为机器可读格式

**核心架构**:
```
论文 → 人工/自动填写模板(ResearchProblem/Approach/Results/...)
        ↓
结构化描述(Structured Description)
        ↓
知识图谱(RDF三元组)
        ↓
ORKG Ask(Vector Search + LLM + KG)
        ↓
论文比较视图 + 综述生成
```

**关键技术点**:
- **模板驱动**: 预定义的论文贡献模板（ResearchProblem, Approach, Results, Baselines等）
- **NLPContributionGraph**: SemEval-2021 Task 11，标准化论文贡献三元组提取
- **人机协作**: 自动提取 + 人工验证，蓝色警告框标识自动提取数据
- **Observatory**: 按领域组织的贡献视图

**参考来源**: orkg.org, ncg-task.github.io, leidenmadtrics.nl

### 1.6 Connected Papers — 引用图谱可视化

**核心架构**: 基于co-citation和bibliographic coupling计算论文相似度，生成Force Directed Graph

**关键技术点**:
- 不是引用树，而是相似度图
- 两篇论文即使不直接引用对方，也可以因为共同被引而紧密关联
- 节点大小=引用数，颜色=年份

### 1.7 Corvus — 生产级论文Agent

**核心架构** (开源项目):
```
用户添加论文 → Redis队列 → Celery Worker
                              ↓
                    检查是否已索引(共享向量库)
                              ↓
                    arXiv抓取 → GROBID解析(章节感知分块)
                              ↓
                    嵌入 → Qdrant向量库
                              ↓
                    QA Agent(LangGraph)
                    ├── Parent indexing(小块检索+大块上下文)
                    ├── Batched LLM filter(后过滤)
                    └── Retrieve → Evaluate → Refine循环
```

**技术栈**: LangGraph · FastAPI · Celery · Redis · Qdrant · GROBID · React

**关键经验**:
- **章节感知分块**: 用GROBID做section-aware chunking，而不是naive sliding window
- **共享向量库**: 多用户共享已索引的论文，避免重复处理
- **Parent indexing**: 小块用于精确检索，大块用于提供LLM更丰富的上下文

**参考来源**: LinkedIn post by Corvus developer

### 1.8 Paper Circle — 多Agent论文分析框架

**核心架构** (开源, ACL 2026 Oral):
```
Discovery Pipeline:
  arXiv + Semantic Scholar + OpenAlex + DBLP → 并行查询
  → 去重(DOI + 标题) → 多准则评分 → 多样性排序

Analysis Pipeline:
  PDF → PyMuPDF解析(元数据/章节/图表/公式)
  → 知识图谱构建(概念/方法/实验/图表节点)
  → 图感知QA + 覆盖度验证
```

**关键技术点**:
- **多源聚合**: 4个学术API并行查询，两阶段去重
- **KG Schema**: Paper → has_concept/has_method/has_experiment/has_figure
- **同步多格式输出**: JSON, CSV, BibTeX, Markdown, HTML

**参考来源**: arxiv.org/html/2604.06170v1

---

## 二、向量数据库与知识图谱的关系

### 2.1 业界共识：两者存储不同表示，服务于不同目的

调研31个来源后，**所有生产级系统的共识是**：

```
向量数据库 ≠ 知识图谱的数据副本
向量数据库 = 文本的语义表示（"这段话和哪段话相似？"）
知识图谱   = 文本的结构化表示（"哪些论文用了同一个方法？"）
```

**它们是同一份源数据的两种并行表示，不是串联关系。**

### 2.2 三种主流架构模式

#### 模式A: 纯向量RAG（Consensus AI, Elicit）

```
文本 → 分块 → 嵌入 → 向量库 → 语义检索 → LLM生成
```

**适用场景**: 查询主要是"找关于X的文档"，不需要关系推理
**代表产品**: Consensus AI, Elicit
**优势**: 简单、快速、成本低
**劣势**: 无法回答多跳推理问题（"哪些论文的方法对比了BERT？"）

#### 模式B: 纯知识图谱RAG（ORKG）

```
文本 → 实体/关系提取 → 知识图谱 → 图遍历 → LLM生成
```

**适用场景**: 数据有强结构化需求，需要精确关系查询
**代表产品**: ORKG
**优势**: 精确关系推理、可解释性强
**劣势**: 构建成本高、实体消歧困难

#### 模式C: 混合架构（主流生产选择，2025-2026）

```
文本 ──┬──→ 分块+嵌入 → 向量库（语义检索）
       │
       └──→ 实体/关系提取 → 知识图谱（关系推理）
                                │
                    查询路由器 ←─┘
                        │
                ┌───────┼───────┐
                ▼       ▼       ▼
            向量检索  图遍历  BM25
                │       │       │
                └───┬───┘───────┘
                    ▼
              RRF融合排序
                    ▼
              Cross-encoder重排
                    ▼
              LLM生成
```

**代表系统**:
- Neo4j + Qdrant/ChromaDB (混合检索)
- Microsoft GraphRAG (社区摘要+向量)
- FalkorDB GraphRAG SDK
- Corvus (GROBID + Qdrant + LangGraph)

**关键数据** (来自FalkorDB 2025基准测试):
- 纯向量RAG在高实体查询(10+实体)上准确率降至0%
- GraphRAG在同场景下保持86%+准确率
- 混合架构综合准确率提升3.4倍

### 2.3 数据流关系图

```
                    PaperChunks (parser输出)
                         │
            ┌────────────┼────────────┐
            ▼                         ▼
      向量化存储                  结构化提取
      (Branch A)                (Branch B)
            │                         │
    ┌───────▼───────┐         ┌───────▼───────┐
    │   嵌入模型     │         │   LLM提取     │
    │  (SPECTER2/   │         │  (实体+关系)  │
    │   BGE/etc)    │         │               │
    └───────┬───────┘         └───────┬───────┘
            │                         │
    ┌───────▼───────┐         ┌───────▼───────┐
    │  向量数据库    │         │  PostgreSQL    │
    │  (pgvector/   │         │  + Neo4j      │
    │   Qdrant)     │         │               │
    │               │         │ paper_entities │
    │ chunk_id      │         │ paper_relations│
    │ embedding     │         │ KG nodes/edges │
    │ text          │         │               │
    └───────┬───────┘         └───────┬───────┘
            │                         │
            └────────┬────────────────┘
                     │
              ┌──────▼──────┐
              │  查询路由器  │
              │  (判断用哪种 │
              │   检索方式)  │
              └──────┬──────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
      语义检索    图遍历     BM25
          │          │          │
          └────┬─────┘──────────┘
               ▼
         RRF融合 + Rerank
               ▼
          LLM生成回答
```

### 2.4 关键结论

**向量数据库和知识图谱存的是不同维度的信息**:

| 维度 | 向量数据库 | 知识图谱 |
|------|-----------|---------|
| **存什么** | 文本块 + 语义向量 | 实体节点 + 关系边 |
| **查询方式** | "找语义相似的文本" | "找实体间的关系路径" |
| **优势** | 模糊匹配、召回率高 | 精确推理、可解释性强 |
| **典型查询** | cosine similarity | Cypher图遍历 |
| **构建成本** | 低(嵌入即可) | 高(需LLM提取+消歧) |
| **更新成本** | 低(增量嵌入) | 高(需重新提取关系) |

**2026年生产系统的默认选择**: 混合架构，向量检索为默认路径，查询路由器根据问题类型决定是否使用图遍历。

---

## 三、分段感知摘要策略

### 3.1 业界做法

**Corvus (生产级开源)**:
- 使用GROBID做**章节感知分块** (section-aware chunking)，而不是naive sliding window
- GROBID将PDF解析为结构化TEI-XML，保留章节层级

**RAGFlow TreeRAG (2025)**:
- 离线阶段用LLM构建**多层级树状目录摘要**: Chapter → Section → Subsection → Key Paragraph Summary
- 每个节点可附加语义增强: 摘要、关键词、实体、潜在问题、元数据
- 核心思想: "先精确定位，再扩展阅读"

**Iris.ai**:
- **抽取式+生成式结合**: 先提取关键数据点，再用abstractive summarization生成摘要
- 不同文档类型使用不同策略

### 3.2 分段压缩比建议

基于调研，推荐的分段策略:

| 章节 | 压缩比 | 理由 | 产品验证 |
|------|--------|------|---------|
| **Abstract** | 0.10 | 已经很短，几乎不压缩 | 所有产品保留原文 |
| **Introduction** | 0.35 | 保留研究背景、动机、gap | TreeRAG保留完整层级 |
| **Related Work** | 0.45 | 论文间关系核心来源 | Elicit列式提取 |
| **Method** | 0.55 | 技术细节对综述价值低 | Elicit只提取关键字段 |
| **Results** | 0.55 | 保留关键数值 | Elicit结构化提取 |
| **Discussion** | 0.35 | limitations + future work | ORKG模板字段 |
| **Conclusion** | 0.35 | 主要贡献总结 | 所有产品保留 |

### 3.3 实现建议

**方案1: GROBID + 自定义压缩** (推荐)
```
PDF → GROBID解析(保留章节结构) → 按section_type分组
→ 对每个章节按压缩比用LLM生成摘要
→ 存入SectionSummaries
```

**方案2: TreeRAG方式**
```
PDF → 分块 → LLM构建层级树摘要
→ 每个节点: 标题 + 摘要 + 实体 + 关键词
→ 保留完整层级关系
```

**方案3: Elicit列式方式** (适合结构化提取)
```
PDF → 全文 → LLM按列提取(研究问题/方法/结果/...)
→ 每列独立prompt，支持用户自定义
```

---

## 四、生产级架构模式总结

### 4.1 2026年RAG架构默认配置

根据多个来源的共识:

| 层 | 2023默认 | 2026默认 |
|----|---------|---------|
| **检索** | 纯向量嵌入 | 混合(BM25 + dense) + RRF |
| **重排** | 无 | Cross-encoder reranker |
| **查询处理** | 原始查询 | HyDE/分解重写 |
| **编排** | 单次检索-生成 | Agentic loop(需要时) |
| **知识结构** | 平面chunk存储 | 混合 + 图层(全局问题) |
| **评估** | 人工抽检 | 持续groundedness + context adherence + answer relevance |

### 4.2 查询路由器设计

**生产系统不会对每次查询都执行图检索**。大多数问题不需要图遍历，延迟代价不值得。

推荐的路由方案:

```python
def route_query(question: str) -> str:
    """根据问题类型选择检索策略"""

    # 信号1: 实体密度
    entities = extract_entities(question)
    if len(entities) >= 3:
        return "graph"  # 多实体 → 图遍历

    # 信号2: 关系词检测
    relation_words = ["对比", "关系", "影响", "引用", "基于", "改进"]
    if any(w in question for w in relation_words):
        return "hybrid"  # 关系查询 → 混合

    # 信号3: 全局 vs 局部
    global_words = ["综述", "总结", "趋势", "整体", "所有"]
    if any(w in question for w in global_words):
        return "graph_global"  # 全局查询 → 图社区摘要

    # 默认
    return "vector"  # 简单查询 → 纯向量
```

### 4.3 混合检索融合: RRF

**Reciprocal Rank Fusion (RRF)** 是2026年生产系统的标准融合方法:

```python
def rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)

def hybrid_merge(vector_results, graph_results, bm25_results, k=60):
    scores = {}
    for rank, doc in enumerate(vector_results):
        scores[doc.id] = scores.get(doc.id, 0) + rrf_score(rank, k)
    for rank, doc in enumerate(graph_results):
        scores[doc.id] = scores.get(doc.id, 0) + rrf_score(rank, k)
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] = scores.get(doc.id, 0) + rrf_score(rank, k)
    return sorted(scores.items(), key=lambda x: -x[1])
```

**k=60** 是广泛验证的默认值。更大的k使分数更均匀，更小的k给top结果更大权重。

---

## 五、实体提取的生产实践

### 5.1 LLM提取的最佳实践

**两阶段提取** (来自多个生产系统):

```
阶段1: 实体提取 (确定性高)
  输入: title + abstract + introduction
  输出: 10种实体类型
  prompt: 结构化JSON输出 + few-shot示例

阶段2: 关系提取 (需要推理)
  输入: 全文 + 已提取实体列表
  输出: subject-predicate-object三元组
  prompt: 给定实体列表，找关系 + evidence + confidence
```

### 5.2 实体消歧是最大挑战

**来自生产系统的教训** (tianpan.co):

> "构建生产级GraphRAG系统最难的部分，不是选择图数据库或编写遍历查询，而是实体消歧——确保'IBM'、'国际商业机器'、'IBM Corp'和'Big Blue'都指向同一个节点。"

**解决方案**:
1. **标准化层**: 建立实体别名表
2. **嵌入消歧**: 用实体描述的向量相似度合并近似实体
3. **LLM合并**: 用LLM判断两个实体是否相同（成本最高但最准确）
4. **跳过这一步的团队无一例外地追悔莫及**——实体碎片化的知识图谱比没有知识图谱更糟糕

### 5.3 成本考量

| 方案 | 索引成本(100篇论文) | 查询成本 |
|------|-------------------|---------|
| 纯向量RAG | $0.5-2 | $0.01-0.05 |
| Microsoft GraphRAG | $4-7 | $0.02-0.10 |
| LightRAG | $0.15 | $0.01-0.05 |
| LazyGraphRAG | $0.004-0.07 | ≈ GraphRAG |

**LazyGraphRAG** (Microsoft 2025) 将索引成本降低了1000倍，同时查询质量与完整GraphRAG相当。

---

## 六、针对你的产品的建议

### 6.1 架构选择

基于你的产品定位（论文知识库分析Agent），推荐:

```
PDF → parser_service → PaperChunks (带section_type)
    │
    ├── 向量化分支:
    │   按章节分组 → 分段感知摘要(SectionSummaries)
    │   → 嵌入(SPECTER2或BGE) → pgvector
    │
    └── 结构化提取分支:
        LLM两阶段提取 → ExtractedEntities + ExtractedRelation
        → PostgreSQL + Neo4j
```

### 6.2 中间态数据结构

```python
class PaperIntermediate(BaseModel):
    paper_id: str

    # 第一层: parser输出
    parsed_content: ParsedContent

    # 第二层: 分段摘要(用于向量存储和文献综述)
    summaries: SectionSummaries

    # 第三层: 提取实体(用于知识图谱)
    entities: ExtractedEntities

    # 第四层: 提取关系(用于知识图谱)
    relations: list[ExtractedRelation]

    # 元信息
    extraction_meta: ExtractionMeta
```

### 6.3 查询路由策略

```
用户问题 → 查询分类器
    │
    ├── "这篇论文的方法是什么？" → 向量检索(找相关chunk)
    ├── "哪些论文用了BERT？" → 图遍历(找实体关系)
    ├── "对比这5篇论文的结果" → 结构化查询(PostgreSQL)
    └── "这个领域的研究趋势？" → 图社区摘要 + 向量检索
```

### 6.4 分步实施路线

```
Phase 1 (当前): 基础管道
  - parser_service → PaperChunks (已有)
  - PaperCard扩展 (新增proposed_model, baselines等字段)
  - 向量化存储 (pgvector)

Phase 2 (近期): 结构化提取
  - LLM实体/关系提取
  - PostgreSQL实体表
  - 简单图遍历

Phase 3 (中期): 知识图谱
  - Neo4j部署
  - 实体消歧
  - 查询路由器
  - RRF混合检索

Phase 4 (远期): 高级功能
  - TreeRAG层级摘要
  - Agentic RAG
  - 文献综述自动生成
  - 创新点发现
```

---

## 七、关键教训总结

| 教训 | 来源 | 说明 |
|------|------|------|
| **数据准备比预期花更多时间** | Towards Data Science | RAG不是快速原型，是大型基础设施项目 |
| **实体消歧是最难的部分** | tianpan.co | 跳过消歧的团队无一例外追悔莫及 |
| **大多数查询不需要图检索** | Medium/Quaxel | 用查询路由器按需选择，不要全部走图 |
| **LazyGraphRAG降低1000倍索引成本** | Microsoft Research | 2025年的突破性进展 |
| **章节感知分块优于滑动窗口** | Corvus/GROBID | 保留文档结构显著提升检索质量 |
| **RRF是标准融合方法** | 多个来源 | k=60是广泛验证的默认值 |
| **评估要同时测检索和生成** | FutureAGI | 只测faithfulness会漏掉检索层的问题 |
| **先跑通最简单的方案** | Medium/Quaxel | 先RAG baseline，再按需升级到GraphRAG |

---

## 八、参考资料

### 产品文档与案例
1. Elicit - https://elicit.com — AI数据提取指南
2. Consensus AI - https://consensus.app — Elastic合作案例: elastic.co/customers/consensus
3. Scite AI - https://scite.ai — Smart Citations数据库
4. Semantic Scholar API - https://api.semanticscholar.org — SPECTER2嵌入
5. ORKG - https://orkg.org — Open Research Knowledge Graph
6. Connected Papers - https://connectedpapers.com — 引用图谱可视化
7. Corvus - GitHub开源 — 生产级论文Agent架构
8. Paper Circle - arXiv:2604.06170 — ACL 2026 Oral, 多Agent论文分析
9. Iris.ai - https://iris.ai — Researcher Workspace
10. Scopus AI - Elsevier — 学术搜索AI

### 技术框架
11. Microsoft GraphRAG - arXiv:2404.16130 — 知识图谱RAG
12. LightRAG - arXiv:2410.05779 — EMNLP 2025 Best Paper
13. LazyGraphRAG - Microsoft Research 2025 — 1000倍成本降低
14. Neo4j GraphRAG Python - https://neo4j.com/blog/developer/hybrid-retrieval-graphrag-python-package
15. RAGFlow TreeRAG - https://ragflow.io — 层级摘要技术
16. GROBID - https://grobid.readthedocs.io — PDF学术解析

### 混合检索
17. RRF (Reciprocal Rank Fusion) - OpenSearch/Elasticsearch实现
18. Elastic ELSER - 稀疏向量模型
19. Neo4j HybridCypherRetriever - 混合检索+图遍历
20. FalkorDB GraphRAG SDK - 生产级GraphRAG基准

### 评估与最佳实践
21. RAG Evaluation Metrics 2026 - futureagi.com
22. Six Lessons Learned Building RAG - towardsdatascience.com
23. Production RAG Architecture - kalvad.com
24. GraphRAG落地实践 - tianpan.co — 实体消歧与成本分析
25. AI知识库搭建技术 - betteryeah.com — RAG技术选型

### 学术论文
26. NLPContributionGraph - SemEval-2021 Task 11 — 论文贡献三元组
27. SciERC - Luan et al. EMNLP 2018 — 科学实体关系
28. S2ORC - Lo et al. ACL 2020 — 81M论文全文数据集
29. SPECTER2 - Singh et al. 2023 — 论文嵌入模型
30. KG2RAG - NAACL 2025 — 知识图谱引导的RAG
31. When to Use Graphs in RAG - OpenReview 2025 — GraphRAG基准测试
