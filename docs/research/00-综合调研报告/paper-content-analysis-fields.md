# 论文内容分析字段调研报告

> 调研日期: 2026-05-30
> 聚焦方向: **论文内容语义字段**（用于知识图谱构建、文献综述、创新点发现）
> 核心参考: ORKG, SciERC, NLP-AKG, NLPContributionGraph

---

## 一、核心问题

当前 `PaperCard` 模型有8个内容字段：

```
research_question, method, data_or_sample, key_findings,
limitations, future_work, topics, possible_gaps
```

**问题**: 这些字段不足以支撑以下产品核心场景：
1. 论文间的**方法对比**（缺少baseline、实验设置、评估指标）
2. **创新点发现**（缺少创新点描述、与prior work的区别）
3. 知识图谱的**细粒度关系**（缺少Task、Model、Metric等实体）
4. 证据表的**结构化比较**（缺少量化结果）

---

## 二、学术界的内容分析框架

### 2.1 ORKG (Open Research Knowledge Graph) — 最权威

ORKG将论文贡献结构化为以下信息单元：

| 信息单元 | 说明 | 必选/可选 |
|---------|------|----------|
| **ResearchProblem** | 论文要解决的问题 | 必选 |
| **Approach** | 提出的方法/方案 | 必选 |
| **Results** | 实验结果 | 必选 |
| **Model** | 具体模型名称 | 可选 |
| **Code** | 代码链接 | 可选 |
| **Dataset** | 使用的数据集 | 可选 |
| **ExperimentalSetup** | 实验设置 | 可选 |
| **Hyperparameters** | 超参数 | 可选 |
| **Baselines** | 对比基线方法 | 可选 |
| **Tasks** | 应用任务 | 可选 |
| **Experiments** | 具体实验描述 | 可选 |
| **AblationAnalysis** | 消融实验分析 | 可选 |

### 2.2 SciERC — NLP领域标准

6种科学实体类型 + 7种关系类型：

**实体类型**:
| 实体 | 说明 | 示例 |
|------|------|------|
| **Task** | 研究任务 | "sentiment analysis", "machine translation" |
| **Method** | 方法/技术 | "BERT", "attention mechanism" |
| **Metric** | 评估指标 | "F1", "BLEU", "accuracy" |
| **Material** | 数据/资源 | "ImageNet", "Penn Treebank" |
| **OtherScientificTerm** | 其他科技术语 | "word embeddings" |
| **Generic** | 泛指术语 | "model", "approach" |

**关系类型**:
| 关系 | 说明 | 示例 |
|------|------|------|
| **Used-for** | X被用于Y | "BERT Used-for NER" |
| **Evaluate-for** | X评估Y | "F1 Evaluate-for NER" |
| **Feature-of** | X是Y的特征 | "attention Feature-of Transformer" |
| **Hyponym-of** | X是Y的下位词 | "CNN Hyponym-of deep learning" |
| **Part-of** | X是Y的一部分 | "encoder Part-of seq2seq" |
| **Compare** | X与Y比较 | "BERT Compare GPT" |
| **Conjunction** | X与Y并列 | "precision Conjunction recall" |

### 2.3 NLP-AKG — 15种实体类型

| 实体类型 | 说明 | 提取自 |
|---------|------|--------|
| **Problem** | 论文主要解决的问题 | 摘要+引言 |
| **Innovation** | 主要创新点 | 摘要+引言 |
| **Method** | 提出的方法 | 全文 |
| **Model** | 具体模型名称 | 全文 |
| **Task** | 应用任务 | 摘要 |
| **Dataset** | 实验数据集 | 实验部分 |
| **Metric** | 评估指标 | 实验部分 |
| **Result** | 实验结果 | 实验部分 |
| Field | 研究领域 | 元数据 |
| Keywords | 关键词 | 元数据 |
| Title | 标题 | 元数据 |
| Author | 作者 | 元数据 |
| Institution | 机构 | 元数据 |
| Conference | 会议/期刊 | 元数据 |
| Date | 日期 | 元数据 |

### 2.4 NLPContributionGraph — 贡献三元组

将论文贡献分解为**主体-谓词-客体**三元组：

```
(BERT, UsedFor, NamedEntityRecognition)
(F1, EvaluateFor, BERT)
(BERT, Outperform, BiLSTM-CRF)
(AttentionMechanism, PartOf, Transformer)
```

---

## 三、当前PaperCard与学术框架的差距分析

### 3.1 已有字段映射

| 当前字段 | 对应ORKG | 对应SciERC | 覆盖度 |
|---------|----------|-----------|--------|
| `research_question` | ResearchProblem | - | ✅ 覆盖 |
| `method` | Approach | Method | ⚠️ 粗粒度 |
| `data_or_sample` | Dataset | Material | ⚠️ 粗粒度 |
| `key_findings` | Results | - | ⚠️ 非结构化 |
| `limitations` | - | - | ✅ 覆盖 |
| `future_work` | - | - | ✅ 覆盖 |
| `topics` | - | Task | ⚠️ 混合 |
| `possible_gaps` | - | - | ✅ 覆盖 |

### 3.2 缺失的关键字段

| 缺失字段 | 来源 | 对产品场景的价值 |
|---------|------|-----------------|
| **proposed_model** | NLP-AKG/ORKG | 论文提出了什么具体模型/架构？ |
| **baselines** | ORKG | 与哪些方法对比？ |
| **evaluation_metrics** | SciERC/ORKG | 用什么指标评估？ |
| **quantitative_results** | ORKG | 具体数值结果（F1=0.95等） |
| **experimental_setup** | ORKG | 实验环境、超参数 |
| **innovation_points** | NLP-AKG | 创新点是什么？与prior work的区别？ |
| **contribution_type** | NLPContributionGraph | 贡献类型（新方法/新数据集/新理论） |
| **tasks** | SciERC/ORKG | 应用于什么任务？ |
| **code_url** | ORKG | 代码链接 |
| **ablation_analysis** | ORKG | 消融实验结论 |

---

## 四、建议的完整论文内容分析字段

### 4.1 一级字段（论文卡片核心）

用于**快速理解一篇论文的核心贡献**：

```python
class PaperContentAnalysis(BaseModel):
    """论文内容分析 - 一级字段"""

    # 问题定义
    research_problem: str = ""          # 研究问题（一句话）
    background_context: str = ""        # 研究背景（为什么重要）

    # 方法
    proposed_method: str = ""           # 提出的方法（一句话）
    proposed_model: str = ""            # 具体模型/架构名称
    method_type: str = ""               # 方法类型：novel/improvement/hybrid/application
    core_technique: str = ""            # 核心技术（如attention, GAN, RL等）

    # 实验
    datasets: list[str] = []            # 实验数据集
    baselines: list[str] = []           # 对比基线方法
    evaluation_metrics: list[str] = []  # 评估指标
    key_results: list[str] = []         # 关键结果（含数值）

    # 创新与贡献
    innovation_points: list[str] = []   # 创新点列表
    contribution_type: str = ""         # 贡献类型：method/dataset/theory/analysis/survey
    advantages: list[str] = []          # 方法优势

    # 局限与展望
    limitations: list[str] = []         # 局限性
    future_work: list[str] = []         # 未来工作
    research_gaps: list[str] = []       # 发现的研究空白
```

### 4.2 二级字段（知识图谱实体）

用于**构建论文间的关系网络**：

```python
class PaperEntities(BaseModel):
    """论文实体提取 - 二级字段"""

    # SciERC标准实体
    tasks: list[str] = []               # 应用任务
    methods: list[str] = []             # 方法/技术（多个）
    metrics: list[str] = []             # 评估指标（多个）
    materials: list[str] = []           # 数据/资源

    # NLP-AKG扩展实体
    models: list[str] = []              # 具体模型名称
    concepts: list[str] = []            # 核心概念
    datasets_used: list[str] = []       # 使用的数据集

    # 关系三元组（用于知识图谱）
    relations: list[dict] = []          # [{subject, predicate, object}]
    # 例: {"subject": "BERT", "predicate": "UsedFor", "object": "NER"}
    # 例: {"subject": "F1", "predicate": "EvaluateFor", "object": "BERT"}
```

### 4.3 三级字段（深度分析）

用于**文献综述和创新点报告**：

```python
class PaperDeepAnalysis(BaseModel):
    """论文深度分析 - 三级字段"""

    # 研究设计
    research_design: str = ""           # 研究设计类型
    sample_description: str = ""        # 样本/数据描述
    experimental_setup: str = ""        # 实验设置

    # 量化结果
    main_results: list[dict] = []       # [{metric, value, dataset, baseline_comparison}]
    # 例: {"metric": "F1", "value": "95.2", "dataset": "CoNLL-2003", "baseline": "BiLSTM-CRF (93.5)"}

    # 消融分析
    ablation_results: list[dict] = []   # 消融实验结论
    # 例: {"component": "attention", "effect": "+2.3% F1"}

    # 与prior work对比
    prior_work_comparison: list[dict] = []  # 与已有工作的对比
    # 例: {"prior": "BERT", "improvement": "+1.5% accuracy", "reason": "better pre-training"}

    # 理论贡献
    theoretical_contribution: str = ""  # 理论贡献
    practical_implication: str = ""     # 实践意义

    # 可复现性
    code_url: str = ""                  # 代码链接
    reproducibility_notes: str = ""     # 可复现性说明
```

---

## 五、字段与产品场景的映射

| 产品场景 | 需要的字段 | 优先级 |
|---------|-----------|--------|
| **论文卡片** | research_problem, proposed_method, innovation_points, key_results | P0 |
| **知识图谱** | tasks, methods, metrics, datasets, relations | P0 |
| **证据表** | datasets, baselines, evaluation_metrics, main_results | P0 |
| **文献综述** | research_problem, method_type, limitations, future_work, research_gaps | P0 |
| **创新点报告** | innovation_points, contribution_type, research_gaps, prior_work_comparison | P0 |
| **QA问答** | 所有一级字段 | P1 |
| **论文对比** | baselines, quantitative_results, advantages | P1 |
| **方法追踪** | core_technique, methods, baselines | P2 |

---

## 六、实施建议

### 6.1 分层实施策略

```
Phase 1 (当前): PaperCard扩展
  - 新增: proposed_model, baselines, evaluation_metrics, innovation_points
  - 改进: key_findings → structured key_results (含数值)
  - 影响: PaperCardExtractionResult + prompt更新

Phase 2 (近期): 知识图谱实体
  - 新增: tasks, methods[], metrics[], relations[]
  - 影响: GraphNode扩展 + 实体抽取pipeline

Phase 3 (远期): 深度分析
  - 新增: main_results (结构化), ablation_results, prior_work_comparison
  - 影响: 全文分析pipeline + 证据表结构
```

### 6.2 与现有模型的兼容

```python
# 建议的PaperCard扩展（向后兼容）
class PaperCard(BaseModel):
    # 现有字段保持不变
    research_question: str = "unknown"
    method: str = "unknown"
    data_or_sample: str = "unknown"
    key_findings: list[str] = []
    limitations: list[str] = []
    future_work: list[str] = []
    topics: list[str] = []
    possible_gaps: list[str] = []

    # 新增字段（Phase 1）
    proposed_model: str = ""                    # 具体模型名称
    baselines: list[str] = []                   # 对比基线
    evaluation_metrics: list[str] = []          # 评估指标
    innovation_points: list[str] = []           # 创新点
    contribution_type: str = ""                 # 贡献类型
    quantitative_results: list[str] = []        # 量化结果
    core_technique: str = ""                    # 核心技术
    tasks: list[str] = []                       # 应用任务
    code_url: str = ""                          # 代码链接
```

---

## 七、参考资料

### 学术框架
1. **ORKG** - Open Research Knowledge Graph. https://orkg.org
2. **NLPContributionGraph** - D'Souza et al., SemEval-2021 Task 11. Structuring Scholarly NLP Contributions for a Research Knowledge Graph.
3. **SciERC** - Luan et al., EMNLP 2018. Multi-Task Identification of Entities, Relations, and Coreference for Scientific Knowledge Graph Construction.
4. **SciREX** - Jain et al., 2020. SciREX: A Challenge Dataset for Document-Level Information Extraction.
5. **NLP-AKG** - arXiv:2502.14192. NLP-AKG: Few-Shot Construction of NLP Academic Knowledge Graph Based on LLM.
6. **Research Knowledge Graphs** - arXiv:2506.07285. Research Knowledge Graphs: the Shifting Paradigm of Scholarly Information Representation.

### 实体关系标准
7. **SciER** - arXiv:2410.21155. SciER: An Entity and Relation Extraction Dataset for Datasets, Methods, and Tasks.
8. **CORD-NER** - Named Entity Recognition for COVID-19 Open Research Dataset.
9. **TDMSci** - Tasks, Datasets and Evaluation Metrics extraction.

### 创新性评估
10. **NovBench** - arXiv:2604.11543. Evaluating Large Language Models on Academic Paper Novelty Assessment.
11. **RAG-Novelty** - ACL 2025. Evaluating and Enhancing LLMs for Novelty Assessment.
12. **Chain of Ideas** - arXiv:2410.13185. Revolutionizing Research in Novel Idea Development with LLM Agents.
