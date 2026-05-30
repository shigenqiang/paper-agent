# 论文数据中间态结构设计

> 调研日期: 2026-05-30
> 定位: 论文解析后的**中间态数据结构**
> 用途: ① 存入数据库 ② 构建知识图谱

---

## 一、这个中间态在系统中的位置

```
PDF论文
  ↓ 解析 (parser_service)
中间态 ← ← ← 本报告设计的结构
  ↓ 存储                    ↓ 转换
PostgreSQL               知识图谱
(论文库/证据表)          (节点+边)
```

中间态需要满足两个下游消费者：
1. **数据库**: 关系型存储，支持查询、过滤、排序
2. **知识图谱**: 图结构存储，支持实体-关系遍历

---

## 二、设计原则

### 2.1 从学术标准提炼的实体类型

综合三个权威框架：

| 来源 | 实体类型 | 我们采纳 |
|------|---------|---------|
| **SciERC** | Task, Method, Metric, Material | ✅ 全部采纳 |
| **NLP-AKG** | Problem, Innovation, Model, Result | ✅ 全部采纳 |
| **ORKG** | ResearchProblem, Approach, Baselines, ExperimentalSetup | ✅ 部分采纳 |

**最终实体类型** (10种):

| 实体类型 | 英文 | 说明 | 示例 |
|---------|------|------|------|
| **研究问题** | Problem | 论文要解决什么问题 | "如何提升NER的跨域泛化能力" |
| **创新点** | Innovation | 论文的核心创新 | "引入对比学习的NER预训练" |
| **方法** | Method | 提出的方法/技术 | "contrastive pre-training" |
| **模型** | Model | 具体模型/架构名称 | "CL-NER" |
| **任务** | Task | 应用任务 | "Named Entity Recognition" |
| **数据集** | Dataset | 实验数据集 | "CoNLL-2003", "OntoNotes" |
| **指标** | Metric | 评估指标 | "F1", "Precision", "Recall" |
| **基线** | Baseline | 对比基线方法 | "BERT-CRF", "BiLSTM-CRF" |
| **结果** | Result | 实验结果 | "F1=95.2%" |
| **概念** | Concept | 核心科技术语 | "attention mechanism", "transfer learning" |

### 2.2 关系类型 (8种)

| 关系 | 谓词 | 说明 | 示例 |
|------|------|------|------|
| 解决 | SOLVES | 论文→问题 | Paper SOLVES Problem |
| 提出 | PROPOSES | 论文→方法/模型 | Paper PROPOSES Method |
| 应用于 | APPLIES_TO | 方法→任务 | Method APPLIES_TO Task |
| 使用 | USES | 方法→数据集 | Method USES Dataset |
| 评估 | EVALUATED_BY | 方法→指标 | Method EVALUATED_BY Metric |
| 对比 | COMPARES_WITH | 方法→基线 | Method COMPARES_WITH Baseline |
| 实现 | ACHIEVES | 方法→结果 | Method ACHIEVES Result |
| 属于 | IS_A | 概念→概念 | CNN IS_A DeepLearning |

---

## 三、中间态数据结构

### 3.1 整体结构

```python
from pydantic import BaseModel, Field
from typing import Optional


class PaperIntermediate(BaseModel):
    """论文数据中间态 — 同时服务于数据库存储和知识图谱构建"""

    # ── 唯一标识 ──────────────────────────────────
    paper_id: str

    # ── 第一层: 解析内容 (来自parser_service) ─────
    parsed_content: ParsedContent

    # ── 第二层: 提取的实体 (来自LLM提取) ─────────
    entities: ExtractedEntities

    # ── 第三层: 提取的关系 (来自LLM提取) ─────────
    relations: list[ExtractedRelation]

    # ── 元信息 ──────────────────────────────────
    extraction_meta: ExtractionMeta
```

### 3.2 第一层: 解析内容

这是parser_service的输出，已经是当前系统已有的。

```python
class ParsedContent(BaseModel):
    """解析后的论文原始内容 — 已有，不需要改"""

    title: str = ""
    abstract: str = ""
    full_text: str = ""
    language: str = ""

    # 结构化章节
    sections: list[Section] = []

    # 图表
    figures: list[FigureInfo] = []
    tables: list[TableInfo] = []

    # 参考文献
    references: list[ReferenceInfo] = []
```

### 3.3 第二层: 提取的实体

**这是核心新增部分**。从论文全文中提取的语义实体。

```python
class ExtractedEntities(BaseModel):
    """从论文中提取的语义实体 — 可直接映射为KG节点"""

    # ── 问题与创新 ──────────────────────────────
    research_problem: str = ""
    """论文要解决的核心问题（一句话）"""

    innovation_points: list[str] = Field(default_factory=list)
    """创新点列表（每个创新点一句话）"""

    contribution_type: str = ""
    """贡献类型: method / dataset / theory / analysis / survey / benchmark"""

    # ── 方法 ────────────────────────────────────
    proposed_method: str = ""
    """提出的方法概述（一句话）"""

    proposed_model: str = ""
    """具体模型/架构名称，如 'BERT', 'Transformer'"""

    core_technique: str = ""
    """核心技术，如 'attention', 'contrastive learning', 'GAN'"""

    method_type: str = ""
    """方法类型: novel / improvement / hybrid / application"""

    # ── 实验 ────────────────────────────────────
    tasks: list[str] = Field(default_factory=list)
    """应用任务列表，如 ['NER', 'RE', 'QA']"""

    datasets: list[str] = Field(default_factory=list)
    """实验数据集，如 ['CoNLL-2003', 'OntoNotes']"""

    metrics: list[str] = Field(default_factory=list)
    """评估指标，如 ['F1', 'Precision', 'Recall', 'BLEU']"""

    baselines: list[str] = Field(default_factory=list)
    """对比基线方法，如 ['BERT-CRF', 'BiLSTM-CRF']"""

    # ── 结果 ────────────────────────────────────
    key_results: list[QuantitativeResult] = Field(default_factory=list)
    """结构化的量化结果"""

    main_finding: str = ""
    """主要发现（一句话总结）"""

    # ── 分析 ────────────────────────────────────
    limitations: list[str] = Field(default_factory=list)
    """局限性"""

    future_work: list[str] = Field(default_factory=list)
    """未来工作方向"""

    research_gaps: list[str] = Field(default_factory=list)
    """发现的研究空白"""

    # ── 概念术语 ────────────────────────────────
    key_concepts: list[str] = Field(default_factory=list)
    """核心科技术语（用于KG概念节点）"""

    # ── 可复现性 ────────────────────────────────
    code_url: str = ""
    """代码链接"""
```

### 3.4 第三层: 提取的关系

**直接可转换为KG三元组**。

```python
class ExtractedRelation(BaseModel):
    """提取的关系 — 直接映射为KG边"""

    subject: str
    """主语实体名称"""

    subject_type: str
    """主语实体类型: Paper / Method / Model / Task / Dataset / Metric / Baseline / Concept"""

    predicate: str
    """谓词: SOLVES / PROPOSES / APPLIES_TO / USES / EVALUATED_BY / COMPARES_WITH / ACHIEVES / IS_A"""

    object: str
    """宾语实体名称"""

    object_type: str
    """宾语实体类型"""

    confidence: float = 0.0
    """置信度"""

    source_quote: str = ""
    """原文引用（用于溯源）"""

    source_section: str = ""
    """来源章节: abstract / introduction / method / result / discussion"""
```

### 3.5 辅助模型

```python
class QuantitativeResult(BaseModel):
    """结构化量化结果"""

    metric: str
    """指标名，如 'F1'"""

    value: str
    """指标值，如 '95.2'"""

    dataset: str = ""
    """在哪个数据集上"""

    baseline_comparison: str = ""
    """对比基线结果，如 'BERT-CRF: 93.5'"""

    improvement: str = ""
    """提升幅度，如 '+1.7%'"""


class Section(BaseModel):
    """论文章节"""

    title: str = ""
    section_type: str = ""
    """introduction / method / result / discussion / conclusion"""

    text: str = ""


class FigureInfo(BaseModel):
    """图表信息"""

    figure_id: str = ""
    caption: str = ""
    section: str = ""


class TableInfo(BaseModel):
    """表格信息"""

    table_id: str = ""
    caption: str = ""
    section: str = ""
    content: str = ""
    """表格内容（简化文本表示）"""


class ReferenceInfo(BaseModel):
    """参考文献"""

    ref_id: str = ""
    raw_text: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str = ""


class ExtractionMeta(BaseModel):
    """抽取元信息"""

    extraction_method: str = "llm"
    model_name: str = ""
    prompt_version: str = ""
    confidence: float = 0.0
    extraction_time: str = ""
    source_chunks: list[str] = Field(default_factory=list)
```

---

## 四、数据库存储方案

### 4.1 关系型存储 (PostgreSQL)

```sql
-- 核心表: 论文实体
CREATE TABLE paper_entities (
    id              SERIAL PRIMARY KEY,
    paper_id        VARCHAR(64) NOT NULL,
    entity_type     VARCHAR(32) NOT NULL,
    -- problem / innovation / method / model / task / dataset / metric / baseline / concept
    entity_value    TEXT NOT NULL,
    confidence      REAL DEFAULT 0.0,
    source_quote    TEXT,
    source_section  VARCHAR(32),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 核心表: 论文关系
CREATE TABLE paper_relations (
    id              SERIAL PRIMARY KEY,
    paper_id        VARCHAR(64) NOT NULL,
    subject         TEXT NOT NULL,
    subject_type    VARCHAR(32),
    predicate       VARCHAR(32) NOT NULL,
    -- SOLVES / PROPOSES / APPLIES_TO / USES / EVALUATED_BY / COMPARES_WITH / ACHIEVES / IS_A
    object          TEXT NOT NULL,
    object_type     VARCHAR(32),
    confidence      REAL DEFAULT 0.0,
    source_quote    TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 量化结果表
CREATE TABLE paper_results (
    id              SERIAL PRIMARY KEY,
    paper_id        VARCHAR(64) NOT NULL,
    metric          VARCHAR(64) NOT NULL,
    value           VARCHAR(32) NOT NULL,
    dataset         VARCHAR(128),
    baseline        VARCHAR(128),
    improvement     VARCHAR(32),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_entities_paper ON paper_entities(paper_id);
CREATE INDEX idx_entities_type ON paper_entities(entity_type);
CREATE INDEX idx_relations_paper ON paper_relations(paper_id);
CREATE INDEX idx_relations_predicate ON paper_relations(predicate);
CREATE INDEX idx_results_paper ON paper_results(paper_id);
```

### 4.2 查询示例

```sql
-- 查找所有使用CoNLL-2003数据集的论文
SELECT DISTINCT paper_id FROM paper_entities
WHERE entity_type = 'dataset' AND entity_value = 'CoNLL-2003';

-- 查找某论文的所有创新点
SELECT entity_value FROM paper_entities
WHERE paper_id = 'xxx' AND entity_type = 'innovation';

-- 查找F1 > 95的结果
SELECT * FROM paper_results
WHERE metric = 'F1' AND CAST(value AS FLOAT) > 95;

-- 查找所有对比BERT-CRF的关系
SELECT * FROM paper_relations
WHERE predicate = 'COMPARES_WITH' AND object = 'BERT-CRF';
```

---

## 五、知识图谱构建方案

### 5.1 转换规则

```python
def to_kg_triples(paper: PaperIntermediate) -> list[dict]:
    """将中间态转换为KG三元组"""
    triples = []

    # 1. 论文节点
    paper_node = {"id": paper.paper_id, "type": "Paper"}

    # 2. 实体 → 节点
    entities = paper.entities

    # Problem节点
    if entities.research_problem:
        triples.append({
            "s": paper.paper_id, "s_type": "Paper",
            "p": "SOLVES",
            "o": entities.research_problem, "o_type": "Problem"
        })

    # Method节点
    if entities.proposed_method:
        triples.append({
            "s": paper.paper_id, "s_type": "Paper",
            "p": "PROPOSES",
            "o": entities.proposed_method, "o_type": "Method"
        })

    # Model节点
    if entities.proposed_model:
        triples.append({
            "s": paper.paper_id, "s_type": "Paper",
            "p": "PROPOSES",
            "o": entities.proposed_model, "o_type": "Model"
        })

    # Innovation节点
    for innovation in entities.innovation_points:
        triples.append({
            "s": paper.paper_id, "s_type": "Paper",
            "p": "HAS_INNOVATION",
            "o": innovation, "o_type": "Innovation"
        })

    # Method → Task
    for task in entities.tasks:
        triples.append({
            "s": entities.proposed_method or entities.proposed_model,
            "s_type": "Method",
            "p": "APPLIES_TO",
            "o": task, "o_type": "Task"
        })

    # Method → Dataset
    for ds in entities.datasets:
        triples.append({
            "s": entities.proposed_method or entities.proposed_model,
            "s_type": "Method",
            "p": "USES",
            "o": ds, "o_type": "Dataset"
        })

    # Method → Metric
    for metric in entities.metrics:
        triples.append({
            "s": entities.proposed_method or entities.proposed_model,
            "s_type": "Method",
            "p": "EVALUATED_BY",
            "o": metric, "o_type": "Metric"
        })

    # Method → Baseline
    for bl in entities.baselines:
        triples.append({
            "s": entities.proposed_method or entities.proposed_model,
            "s_type": "Method",
            "p": "COMPARES_WITH",
            "o": bl, "o_type": "Baseline"
        })

    # Method → Result (from quantitative results)
    for qr in entities.key_results:
        triples.append({
            "s": entities.proposed_method or entities.proposed_model,
            "s_type": "Method",
            "p": "ACHIEVES",
            "o": f"{qr.metric}={qr.value}", "o_type": "Result"
        })

    # 3. LLM提取的额外关系（直接使用）
    for rel in paper.relations:
        triples.append({
            "s": rel.subject, "s_type": rel.subject_type,
            "p": rel.predicate,
            "o": rel.object, "o_type": rel.object_type
        })

    return triples
```

### 5.2 KG Schema (Neo4j)

```
节点类型:
  - Paper        {paper_id, title, year}
  - Problem      {description}
  - Innovation   {description}
  - Method       {name, type}
  - Model        {name}
  - Task         {name}
  - Dataset      {name}
  - Metric       {name}
  - Baseline     {name}
  - Result       {metric, value}
  - Concept      {name}

关系类型:
  - (Paper)-[:SOLVES]->(Problem)
  - (Paper)-[:PROPOSES]->(Method)
  - (Paper)-[:PROPOSES]->(Model)
  - (Paper)-[:HAS_INNOVATION]->(Innovation)
  - (Method)-[:APPLIES_TO]->(Task)
  - (Method)-[:USES]->(Dataset)
  - (Method)-[:EVALUATED_BY]->(Metric)
  - (Method)-[:COMPARES_WITH]->(Baseline)
  - (Method)-[:ACHIEVES]->(Result)
  - (Concept)-[:IS_A]->(Concept)
```

---

## 六、提取策略

### 6.1 两阶段提取

```
阶段1: 结构化字段提取 (确定性高)
  输入: title + abstract + sections
  输出: research_problem, proposed_method, proposed_model,
        tasks, datasets, metrics, baselines
  方式: LLM + 结构化prompt

阶段2: 关系三元组提取 (需要推理)
  输入: 全文
  输出: relations[] (subject-predicate-object)
  方式: LLM + few-shot
```

### 6.2 与现有系统的集成

```
当前流程:
  PDF → parser → PaperChunk[] → PaperCard

新流程:
  PDF → parser → PaperChunk[] → PaperIntermediate → 存DB
                                                ↓
                                          KG构建 → Neo4j

PaperIntermediate 是 PaperCard 的**超集**:
  - PaperCard 的所有字段都能从 PaperIntermediate 推导
  - PaperIntermediate 额外包含 relations[], key_results, baselines 等
```

---

## 七、与当前PaperCard的关系

```python
# PaperIntermediate → PaperCard 的转换
def to_paper_card(pi: PaperIntermediate) -> PaperCard:
    return PaperCard(
        paper_id=pi.paper_id,
        research_question=pi.entities.research_problem,
        method=pi.entities.proposed_method,
        data_or_sample=", ".join(pi.entities.datasets),
        key_findings=[r.metric + "=" + r.value for r in pi.entities.key_results]
                      or [pi.entities.main_finding],
        limitations=pi.entities.limitations,
        future_work=pi.entities.future_work,
        topics=pi.entities.tasks + pi.entities.key_concepts[:3],
        possible_gaps=pi.entities.research_gaps,
        # 新增字段
        proposed_model=pi.entities.proposed_model,
        baselines=pi.entities.baselines,
        evaluation_metrics=pi.entities.metrics,
        innovation_points=pi.entities.innovation_points,
        contribution_type=pi.entities.contribution_type,
        quantitative_results=[r.metric + "=" + r.value for r in pi.entities.key_results],
    )
```

---

## 八、参考资料

### 学术框架
1. ORKG - https://orkg.org — 论文贡献结构化 (ResearchProblem/Approach/Results)
2. NLPContributionGraph - SemEval-2021 Task 11 — 贡献三元组提取
3. SciERC - Luan et al. EMNLP 2018 — 6种实体+7种关系
4. NLP-AKG - arXiv:2502.14192 — 15种论文实体类型

### 中间态数据集
5. S2ORC - Lo et al. ACL 2020 — 8.1M论文结构化全文
6. S2ORC CS Enriched - HuggingFace — 14个enrichment字段
7. SciREX - Jain et al. 2020 — Task/Dataset/Method/Metric四实体

### KG构建Pipeline
8. KG Construction from Unstructured Text - arXiv:2507.03226 — 多模型pipeline
9. Information Extraction Pipelines for KG - PMC — 实体/关系链接
10. LangChain KG Construction - blog — OpenAI functions提取KG
