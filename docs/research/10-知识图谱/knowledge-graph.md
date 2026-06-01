# 学术论文知识图谱构建方法调研报告

> 调研时间：2026-05-31
> 调研范围：实体抽取方法、图谱构建架构、图数据库选型、GraphRAG应用

---

## 1. 实体类型体系

### 1.1 三层实体设计

| 层级 | 实体类型 | 说明 | 来源 |
|------|---------|------|------|
| **元数据层** | Paper | 论文 | PDF解析/GROBID |
| | Author | 作者 | GROBID/metadata |
| | Institution | 机构 | GROBID/metadata |
| | Venue | 期刊/会议 | metadata |
| **科学实体层** | Method | 方法/算法 | NER/LLM抽取 |
| | Model | 模型架构 | NER/LLM抽取 |
| | Dataset | 数据集 | NER/LLM抽取 |
| | Task | 研究任务 | NER/LLM抽取 |
| | Metric | 评价指标 | NER/LLM抽取 |
| | Theory | 理论/概念 | NER/LLM抽取 |
| **分析层** | Finding | 发现/结论 | LLM抽取 |
| | Limitation | 局限性 | LLM抽取 |
| | ResearchGap | 研究空白 | LLM推理 |
| | InnovationPoint | 创新点 | LLM推理 |

### 1.2 关系类型

| 关系 | 源节点 | 目标节点 | 说明 |
|------|--------|---------|------|
| authored_by | Paper | Author | 作者关系 |
| affiliated_with | Author | Institution | 隶属关系 |
| published_at | Paper | Venue | 发表位置 |
| cites | Paper | Paper | 引用关系 |
| uses_method | Paper | Method | 使用方法 |
| uses_dataset | Paper | Dataset | 使用数据集 |
| addresses_task | Paper | Task | 解决任务 |
| reports_metric | Paper | Metric | 报告指标 |
| extends | Method | Method | 方法扩展 |
| outperforms | Method | Method | 性能超越 |
| similar_to | Paper | Paper | 内容相似 |
| co_occurs | Method | Method | 共现关系 |
| has_gap | Paper | ResearchGap | 存在空白 |
| contributes | Paper | InnovationPoint | 贡献创新点 |

---

## 2. 实体抽取方法

### 2.1 方法对比

| 方法 | F1 Score | 成本 | 适用场景 |
|------|---------|------|---------|
| CRF | 55-62% | 极低 | 基线/大规模处理 |
| BiLSTM-CRF | 67-72% | 低 | 大规模生产 |
| SciBERT-NER | 65-67% | 中 | 科学文档专用 |
| BERT+BiLSTM+CRF | 67-69% | 中 | 平衡方案 |
| **LLM Few-Shot (GPT-4o)** | **70-78%** | 高 | 高质量小批量 |
| LLM Few-Shot (Claude) | 68-73% | 高 | 高质量小批量 |
| **LLM + 规则混合** | **~80%** | 中 | **推荐生产方案** |

### 2.2 推荐方案：LLM + 规则混合

```
论文文本
    │
    ▼
┌─────────────────────────┐
│ 规则预抽取（高精度）       │
│ - 正则匹配数据集名         │
│ - GROBID元数据（作者/机构） │
│ - 引用格式解析             │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│ LLM抽取（高召回）         │
│ - Method/Task/Theory等   │
│ - Few-shot prompt        │
│ - JSON结构化输出          │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│ 后处理融合                │
│ - 实体去重/归一化          │
│ - 类型校验               │
│ - 置信度过滤              │
└─────────────────────────┘
```

### 2.3 LLM抽取Prompt模板

```python
prompt = """从以下学术论文文本中抽取实体，返回JSON格式。

实体类型：
- Method: 方法、算法、技术
- Model: 模型架构
- Task: 研究任务、问题
- Dataset: 数据集名称
- Metric: 评价指标
- Theory: 理论、概念
- Finding: 关键发现
- Limitation: 局限性

文本：
{text}

输出JSON：
{{"entities": [{{"name": "实体名", "type": "类型", "description": "一句话描述"}}]}}
"""
```

### 2.4 关系抽取方法

| 方法 | 原理 | F1 | 适用场景 |
|------|------|-----|---------|
| 远程监督 | 知识库对齐自动标注 | 60-70% | 大规模 |
| BERT-RE | 分类模型 | 70-78% | 中等规模 |
| **LLM抽取** | prompt驱动 | **75-82%** | 高质量小批量 |
| 共现统计 | 统计共现频率 | 50-60% | 粗粒度关系 |

---

## 3. 图谱数据模型

### 3.1 Neo4j Schema设计

```cypher
// 节点约束
CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE;
CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.author_id IS UNIQUE;
CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:Method) REQUIRE m.name IS UNIQUE;
CREATE CONSTRAINT task_name IF NOT EXISTS FOR (t:Task) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT dataset_name IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE;

// 全文索引（用于文本搜索）
CREATE FULLTEXT INDEX paper_fulltext IF NOT EXISTS
FOR (p:Paper) ON EACH [p.title, p.abstract];

// 向量索引（用于语义检索）
CREATE VECTOR INDEX paper_embedding IF NOT EXISTS
FOR (p:Paper) ON (p.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}};
```

### 3.2 规模估算（100篇论文项目）

| 指标 | 数量 |
|------|------|
| Paper节点 | 100 |
| Author节点 | ~400 |
| Method节点 | ~200 |
| Task节点 | ~80 |
| Dataset节点 | ~60 |
| 总节点数 | ~1,380 |
| 总边数 | ~3,500 |

---

## 4. 端到端构建流程

```
PDF文件
  │
  ▼
PDF解析 (GROBID/MinerU)
  │ 提取：标题、作者、摘要、正文、参考文献
  ▼
文本分块 (Section-Based)
  │ 按章节切分，保留结构信息
  ▼
实体抽取 (LLM + 规则)
  │ 抽取：Method, Task, Dataset, Metric, Finding...
  ▼
关系抽取 (LLM + 共现)
  │ 抽取：uses_method, addresses_task, extends...
  ▼
知识融合 (Entity Resolution)
  │ 作者消歧、方法归一化、实体链接
  ▼
图存储 (Neo4j)
  │ MERGE语义写入，避免重复
  ▼
知识图谱
```

---

## 5. 知识融合

### 5.1 作者消歧

| 方法 | 准确率 | 说明 |
|------|-------|------|
| 规则匹配 | 85-90% | 姓名+机构精确匹配 |
| 聚类 | 90-93% | 姓名相似度+共同作者 |
| **混合方案** | **93-97%** | 规则+聚类+图关系 |

作者指纹算法：
```python
def author_fingerprint(name: str, institution: str) -> str:
    normalized = unidecode(name).lower().strip()
    parts = normalized.split()
    # 标准化为 "last, first_initial"
    if len(parts) >= 2:
        key = f"{parts[-1]}, {parts[0][0]}"
    else:
        key = normalized
    if institution:
        key += f"@{institution.lower().strip()[:20]}"
    return key
```

### 5.2 方法/数据集归一化

- 同义词映射表：`BERT → bert, BERT-base, bert-base-uncased`
- 标准化：小写、去版本号、去括号
- 嵌入相似度：余弦 > 0.9 视为同一实体

### 5.3 实体链接（外部数据源）

| 数据源 | 覆盖 | 用途 |
|--------|------|------|
| OpenAlex | 2.5亿+作品 | 论文/作者ID |
| DBLP | CS论文 | 作者/会议 |
| ORCID | 研究者 | 作者唯一ID |
| Wikidata | 通用知识 | 实体归一化 |

---

## 6. 图数据库选型

| 数据库 | Stars | 易用性 | 性能 | 扩展性 | 推荐度 |
|--------|-------|--------|------|--------|--------|
| **Neo4j** | 13K+ | 最高 | 高 | 中 | 首选 |
| NebulaGraph | 10K+ | 中 | 高 | 高 | 大规模备选 |
| ArangoDB | 13K+ | 高 | 高 | 高 | 多模型需求 |
| TigerGraph | — | 中 | 最高 | 高 | 实时分析 |
| JanusGraph | 2K+ | 低 | 中 | 高 | 不推荐 |

**推荐：Neo4j Community Edition**
- Cypher查询语言，学习曲线最低
- APOC插件生态丰富
- 与LangChain/LlamaIndex原生集成
- 社区版免费，支持数亿节点

---

## 7. 增量更新策略

```cypher
// 新论文入库 — MERGE语义避免重复
MERGE (p:Paper {paper_id: $paper_id})
ON CREATE SET p.title = $title, p.created_at = datetime()
ON MATCH SET p.updated_at = datetime()

// 作者关系 — MERGE避免重复边
MATCH (p:Paper {paper_id: $paper_id})
MERGE (a:Author {name: $author_name})
MERGE (p)-[:AUTHORED_BY {position: $pos}]->(a)

// 方法实体 — 归一化后MERGE
MERGE (m:Method {name: toLower(trim($method_name))})
ON CREATE SET m.aliases = [$method_name]
MERGE (p)-[:USES_METHOD {section: $section}]->(m)
```

---

## 8. 应用场景

### 8.1 GraphRAG（图增强RAG）

```
用户查询
  ├─ 向量检索 → 语义匹配的chunk
  ├─ 图谱检索 → 结构化关系路径
  └─ 社区摘要 → 全局视角
       ↓
  融合上下文 → LLM生成答案
```

### 8.2 创新点发现（本项目核心价值）

利用知识图谱的**结构洞（Structural Holes）**检测：

```
Method A ──uses──→ Task 1
Method B ──uses──→ Task 2
                     ↑
               [结构洞] ← Method A 未用于 Task 2？→ 创新机会
```

- **跨领域方法迁移**：Method-Task二部图中的未连接对
- **数据集空白**：Task-Dataset二部图中的稀疏区域
- **组合创新**：两个Method的共现模式异常

### 8.3 文献综述生成

图谱驱动的综述结构：
1. 按Task聚类生成大纲
2. 利用 `extends/outperforms` 关系生成方法比较段落
3. 利用Gap实体生成"未来方向"段落
4. 每个论点自动关联证据论文

### 8.4 论文推荐

基于元路径的推荐：
- `Paper → Method → Paper`：使用相同方法的论文
- `Paper → Task → Paper`：解决相同任务的论文
- `Paper → Author → Paper`：同一作者的其他论文

---

## 9. 开源工具生态

| 工具 | Stars | 定位 | 推荐度 |
|------|-------|------|--------|
| **llm-graph-builder** | 4.7K | Neo4j+LLM构建图谱 | 首选 |
| **paper2lkg** | — | 港科大，论文转知识图谱 | 学术场景首选 |
| **DeepKE** | 4.4K | 知识抽取工具包（NER+RE） | 传统方法 |
| **OpenNRE** | 4.5K | 关系抽取工具包 | 关系抽取 |
| **scispacy** | 2.0K | 科学文档NER | 生物医学 |
| **Microsoft GraphRAG** | 33K | 社区检测+层次摘要 | 全局QA |
| **LightRAG** | 36K | 轻量级GraphRAG | 快速部署 |

---

## 10. 对本项目的推荐方案

### 推荐技术栈

| 组件 | 推荐方案 | 备选 |
|------|---------|------|
| PDF解析 | GROBID + MinerU | — |
| 实体抽取 | LLM(GPT-4o) + 规则混合 | SciBERT微调 |
| 关系抽取 | LLM + 共现统计 | BERT-RE |
| 知识融合 | 混合消歧 | — |
| 图数据库 | Neo4j Community | NebulaGraph |
| 图谱构建 | llm-graph-builder | paper2lkg |
| GraphRAG | LightRAG | Microsoft GraphRAG |

### 分阶段实施

| 阶段 | 目标 | 技术 |
|------|------|------|
| **P1** | 元数据图谱 | GROBID抽取作者/机构/引用 → Neo4j |
| **P2** | 科学实体图谱 | LLM抽取Method/Task/Dataset → Neo4j |
| **P3** | 分析层图谱 | LLM推理Gap/Innovation → Neo4j |
| **P4** | GraphRAG集成 | 向量检索 + 图谱检索融合 |

---

详细子报告：
- `10-知识图谱/学术知识图谱构建架构设计调研报告.md` — 架构设计（1377行）
- `10-知识图谱/学术论文实体抽取方法深度调研报告.md` — 实体抽取方法
- `10-知识图谱/学术论文知识图谱应用场景与GraphRAG结合调研报告.md` — 应用场景（954行）
