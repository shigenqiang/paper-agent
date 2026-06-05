# Consensus Meter 多论文结论聚合方法调研报告

> **调研日期**: 2026-06-03
> **调研主题**: 如何统计多篇论文对同一 claim 的支持/反对/不确定
> **调研目的**: 为知识图谱系统实现类似 Consensus Meter 的多论文结论聚合功能提供技术方案

---

## 1. 核心概念与定义

### 1.1 Consensus Meter 定义

Consensus Meter 是 Consensus.app 产品的核心功能，用于从多篇科学论文中提取和聚合对同一科学主张（claim）的结论方向，以百分比形式展示科学共识程度（例如："75% 的研究支持、15% 不确定、10% 反对"）。

### 1.2 核心术语

| 术语 | 定义 |
|------|------|
| **Claim（科学主张）** | 一篇论文中提出的可验证的结论性陈述，如"运动改善睡眠质量" |
| **Stance（立场）** | 一篇论文的证据对某个 claim 的态度方向：支持(Support)/反对(Refute)/不确定(NEI) |
| **Evidence（证据）** | 论文中用于支持或反驳 claim 的具体句子或段落 |
| **Rationale（理由）** | 从论文中提取的作为证据的关键句子 |
| **Consensus Score（共识分数）** | 量化多篇论文一致程度的数值指标 |
| **Claim Normalization（主张归一化）** | 将不同表述的 finding 映射到同一 canonical claim 的过程 |

### 1.3 任务形式化定义

给定一个 claim $c$ 和一个论文集合 $D = \{d_1, d_2, ..., d_n\}$，系统需要：

1. **证据检索**: 从每篇论文 $d_i$ 中检索与 $c$ 相关的证据句子集合 $E_i$
2. **立场分类**: 对每篇论文判定 stance $s_i \in \{Support, Refute, NEI\}$
3. **聚合计算**: 计算共识分数 $S(c) = f(s_1, s_2, ..., s_n)$

---

## 2. 技术原理深度解析

### 2.1 Consensus.app 的工作原理

Consensus.app 是一款 AI 驱动的学术搜索引擎，索引了超过 2 亿篇科学论文。其 Consensus Meter 的技术架构包含以下关键环节：

#### 2.1.1 论文检索阶段

- **语义搜索**: 使用向量嵌入（如 Sentence-BERT 或类似模型）将用户查询转化为密集向量表示
- **近似最近邻搜索**: 在大规模论文索引上使用 ANN 算法进行语义匹配
- **排序**: 基于语义相关性而非仅关键词匹配来排序论文

#### 2.1.2 Claim 提取阶段

- 从论文的**摘要(Abstract)**、**结论(Conclusion)**、**讨论(Discussion)** 等章节中提取关键主张
- 使用基于 Transformer 的 NLP 模型（可能微调于科学文本）进行 claim 识别

#### 2.1.3 立场分类阶段

- 对每篇相关论文的发现进行分类：**Yes（支持）** / **No（反对）** / **Possibly（不确定）**
- 使用 LLM（GPT 系列模型）分析论文摘要和结论的立场方向

#### 2.1.4 聚合展示阶段

- 将分类结果汇总为百分比分布
- 附加质量标签：如"Highly Cited"、"RCT"等

### 2.2 Claim 归一化方法

Claim 归一化是实现多论文聚合的核心难题——如何判断不同论文的 finding 指向同一 claim。

#### 2.2.1 语义相似度方法

使用科学文本专用的嵌入模型计算 claim 之间的语义相似度：

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| **SPECTER** (Cohan et al., 2020) | 基于引用图的论文级嵌入，使用 SciBERT 微调 | 论文级相似度 |
| **SciBERT** (Beltagy et al., 2019) | 在科学语料上预训练的 BERT | 句子级科学文本 |
| **Sentence-BERT** | 通用句子嵌入，可微调于科学领域 | 通用句对匹配 |
| **SciNCL** | 基于引用的对比学习科学嵌入 | 引用感知相似度 |
| **PubMedBERT** | 在 PubMed 上预训练的 BERT | 生物医学领域 |

**实现步骤**:
1. 从每篇论文中提取 finding/claim 句子
2. 使用科学嵌入模型编码为向量
3. 计算余弦相似度，阈值以上判定为同一 claim
4. 使用聚类算法（如层次聚类）将语义等价的 claim 归为一组

#### 2.2.2 改写检测方法

- **ParaSCI** 数据集：科学论文改写数据集，可用于训练改写检测模型
- 使用 NLI 模型判断两个 claim 是否蕴含/矛盾/无关

#### 2.2.3 基于查询的归一化

Consensus.app 采用的方法——用户输入自然语言问题作为"canonical claim"，系统检索所有相关论文并直接判断它们对该问题的立场。这种方式避免了显式的 claim 归一化，将问题转化为**检索+立场分类**的管道。

### 2.3 结论方向判断方法

#### 2.3.1 NLI-based 方法

将 claim verification 建模为三路分类问题（蕴含/矛盾/中性），这是学术界最主流的方法。

**核心数据集**:

| 数据集 | 发布年份 | 规模 | 领域 | 标签 |
|--------|----------|------|------|------|
| **SciFact** (Wadden et al., 2020) | 2020 | ~1,400 claims, ~5,000 abstracts | 生物医学 | Support/Refute/NEI |
| **HealthVer** (Sarrouti & El Asri, 2021) | 2021 | COVID-19 健康声明 | 医学 | Support/Refute/NEI |
| **SciTail** (Khot et al., 2018) | 2018 | 科学领域 NLI | 多学科 | Entailment/Neutral |
| **SciNLI** (Sadat et al., 2022) | 2022 | 科学文本 NLI | 多学科 | Entailment/Contradiction |
| **Climate-FEVER** | 2020 | 1,535 气候声明 | 气候科学 | Support/Refute/NEI |
| **SciTab** (Lu et al., 2023) | 2023 | 表格数据验证 | 多学科 | Support/Refute/NEI |

**模型架构**:

SciFact 的典型两阶段管道：

```
Stage 1: Retrieval (检索)
  Query: claim → BM25/Dense Retrieval → Top-K abstracts

Stage 2: Verification (验证)
  Input: [CLS] claim [SEP] abstract [SEP]
  Model: Longformer Encoder
  Output: Support/Refute/NEI + Rationale sentences
```

#### 2.3.2 LLM-based 方法

使用大语言模型（GPT-4、Claude 等）直接进行立场分类，这是 2023-2025 年的主流趋势。

**优势**:
- 无需微训练，zero-shot 即可使用
- 能处理复杂的科学语言和隐含推理
- 可以输出推理过程（Chain-of-Thought）

**劣势**:
- 成本较高（API 调用费用）
- 存在幻觉风险
- 结果可能不完全可复现

#### 2.3.3 Rule-based 方法

基于线索短语（cue phrases）的规则匹配：

- 支持线索: "consistent with", "in agreement", "confirms", "supports"
- 反对线索: "contradicts", "in contrast", "however", "failed to show"
- 不确定线索: "inconclusive", "mixed results", "further research needed"

这种方法简单但召回率低，适合作为辅助特征。

#### 2.3.4 Citation Stance Detection

分析引用上下文来判断引用者对被引论文的态度：

| 数据集 | 作者 | 年份 | 标签体系 |
|--------|------|------|----------|
| **SciCite** (Cohan et al., 2019) | Cohan et al. | 2019 | Background/Method/Result |
| **ACL-ARC** | Abu-Jbara et al. | 2013 | 多类引用功能 |
| **TAC 2014** | - | 2014 | Support/Contradict/Mention |

### 2.4 Confidence Score 计算方法

#### 2.4.1 简单投票计数（Vote Counting）

最基础的方法：统计支持/反对/不确定的论文数量，计算百分比。

```
consensus_score = count(support) / total_papers
```

**局限性**:
- 不考虑论文质量/样本量/研究设计
- 不区分强证据和弱证据
- 统计学上被认为过时（Hedges & Olkin, 1980）

#### 2.4.2 加权投票（Weighted Voting）

根据论文质量指标进行加权：

```
weighted_score = sum(weight_i * stance_i) / sum(weight_i)
```

权重因子可包括：
- 样本量（sample size）
- 研究设计类型（RCT > Cohort > Case Study）
- 引用次数（citation count）
- 期刊影响因子
- 发表时间（更新的研究权重更高）
- 偏倚风险评估（risk of bias）

#### 2.4.3 概率融合方法

使用贝叶斯方法融合多源证据：

```
P(claim | evidence_1, ..., evidence_n) ∝ P(claim) * ∏ P(evidence_i | claim)
```

每篇论文的证据被视为对 claim 真伪的一次"观测"，通过贝叶斯更新得到后验概率。

#### 2.4.4 基于 LLM 的置信度评估

直接让 LLM 评估证据的一致性程度：

```
Prompt: Given {N} studies about claim "{claim}":
- {n1} studies support it
- {n2} studies refute it
- {n3} are inconclusive
Rate the confidence level (0-100) and explain why.
```

#### 2.4.5 一致性度量

| 度量方法 | 计算方式 | 适用场景 |
|----------|----------|----------|
| **简单比例** | support / total | 快速概览 |
| **Cohen's Kappa** | 校正随机一致的概率 | 多标注者一致性 |
| **Fleiss' Kappa** | 扩展到多标注者 | 多论文一致性 |
| **Krippendorff's Alpha** | 支持多种数据类型 | 灵活的一致性度量 |
| **信息熵** | -sum(p * log(p)) | 分布不确定性 |

---

## 3. 主流技术方案对比

### 3.1 方案总览

| 方案 | 方法类型 | 代表系统/论文 | 精度 | 可扩展性 | 成本 | 实现复杂度 |
|------|----------|---------------|------|----------|------|------------|
| **NLI Fine-tuned** | 传统 NLP | SciFact, MultiVerS | 高 | 中 | 低 | 中 |
| **LLM Zero-shot** | 大语言模型 | GPT-4, Claude | 中-高 | 高 | 高 | 低 |
| **LLM Few-shot** | 大语言模型 | GPT-4 + examples | 高 | 高 | 高 | 低 |
| **Hybrid Pipeline** | 混合 | 检索+NLI+LLM | 最高 | 中 | 中 | 高 |
| **Rule-based** | 规则匹配 | 线索短语 | 低 | 高 | 最低 | 低 |
| **Citation Stance** | 引用分析 | SciCite-based | 中 | 高 | 低 | 中 |

### 3.2 详细对比

#### 3.2.1 NLI Fine-tuned 模型方案

**代表工作**: SciFact (Wadden et al., EMNLP 2020), MultiVerS (Wadden et al., 2021)

**架构**:
```
Claim → Retrieval (BM25/DPR) → Top-K Abstracts → Longformer Encoder → Support/Refute/NEI
```

**优点**:
- 在 SciFact 基准上达到最优性能
- 可提取 rationale sentences（证据句子）
- 推理速度快，成本低

**缺点**:
- 需要领域内标注数据进行微调
- 泛化到新领域需要额外训练
- 对复杂推理能力有限

**GitHub 资源**:
- `allenai/scifact` (261 stars) - SciFact 数据集和模型
- `dwadden/multivers` (54 stars) - MultiVerS 多证据验证模型
- `allenai/scientific-claim-generation` (32 stars) - 零样本 claim 生成

#### 3.2.2 LLM Zero-shot 方案

**代表系统**: Consensus.app, Elicit

**架构**:
```
Claim + Abstract → LLM Prompt → Support/Refute/NEI + Reasoning
```

**优点**:
- 无需训练数据
- 能处理复杂科学语言
- 支持 Chain-of-Thought 推理
- 快速部署

**缺点**:
- API 成本高（大规模处理时）
- 幻觉风险
- 结果不完全可复现
- 需要仔细设计 prompt

#### 3.2.3 Hybrid Pipeline 方案

**架构**:
```
Claim → BM25 Retrieval → Dense Re-ranking → NLI Filter → LLM Verification → Aggregation
```

**优点**:
- 结合各方法优势
- 精度最高
- 可控制成本（只对候选使用 LLM）

**缺点**:
- 系统复杂度高
- 需要维护多个组件
- 调试困难

---

## 4. 最新发展动态（2024-2026）

### 4.1 学术研究进展

#### 4.1.1 SciFact 系列的演进

- **SciFact** (2020): 奠基性工作，定义了科学 claim verification 任务
- **MultiVerS** (2021): 统一的多证据验证模型
- **SciFact-Open** (2022): 开放域设定，从大规模语料库中检索证据
- **SciTab** (2023): 将验证扩展到科学表格数据
- **MSVEC** (2024): 多领域科学 claim 验证评估语料

#### 4.1.2 LLM 在 Claim Verification 中的应用

- **Explainable Biomedical Claim Verification with LLMs** (2025): 将 LLM 与可解释性结合
- **DeepVerify** (xiongsiheng/DeepVerify, 36 stars): 基于证据的专家级科学 claim 验证
- **ClaimeAI** (BharathxD/ClaimeAI, 101 stars, 2025): 基于 LangGraph 的事实核查系统

#### 4.1.3 Claim 分解与原子验证

- **FActScore** (Min et al., ICLR 2023/EMNLP 2023): 将长文本分解为原子事实并逐一验证
- **ClaimDecomposition**: 将复合 claim 分解为可独立验证的子 claim
- **ClaimBuster**: 自动检测值得核查的 claim

### 4.2 工具产品发展

| 产品 | 功能特点 | 最新动态 |
|------|----------|----------|
| **Consensus.app** | Consensus Meter, 200M+ 论文索引 | 持续扩展 LLM 能力 |
| **Elicit** | 结构化数据提取, 论文对比表 | 200M 论文库, AI 辅助综述 |
| **Semantic Scholar** | 学术搜索引擎, 论文关系图 | SPECTER 嵌入, TLDR 功能 |
| **SciSpace** | AI 辅助论文阅读 | 表格/图表理解能力 |
| **Rayyan** | AI 辅助系统性综述筛选 | ML 分类器集成 |

### 4.3 LLM-based Claim Verification 工具（2025-2026）

| 项目 | Stars | 创建时间 | 描述 |
|------|-------|----------|------|
| **ClaimeAI** | 101 | 2025-05 | 基于 LangGraph 的 AI 事实核查系统 |
| **AgentClaimGuard** | 51 | 2026-05 | LLM agent 声明验证门控 |
| **Dokis** | 36 | 2026-03 | RAG 来源中间件，验证 LLM 回答中的声明 |
| **LongTracer** | 34 | 2026-04 | 检测 LLM 幻觉，混合 STS+NLI 验证 |
| **Clarity Gate** | 30 | 2025-12 | LLM 文档验证协议 |

---

## 5. 开源工具与资源汇总

### 5.1 数据集

| 数据集 | GitHub Stars | 任务 | 领域 | 标签 |
|--------|-------------|------|------|------|
| **SciFact** | 261 | Claim Verification | 生物医学 | Support/Refute/NEI |
| **FEVER** | 129 (baseline) | Fact Verification | Wikipedia | Supported/Refuted/NEI |
| **FEVEROUS** | 76 | 结构化+非结构化验证 | Wikipedia | Supported/Refuted/NEI |
| **SciCite** | 130 | Citation Intent | CS | Background/Method/Result |
| **SciNLI** | 29 | 科学 NLI | 多学科 | Entailment/Contradiction |
| **Climate-FEVER** | - | 气候声明验证 | 气候科学 | Support/Refute/NEI |
| **HealthVer** | - | 健康声明验证 | COVID-19 | Support/Refute/NEI |
| **SciTab** | 23 | 表格声明验证 | 多学科 | Support/Refute/NEI |
| **EX-FEVER** | 12 | 多跳可解释验证 | Wikipedia | Supported/Refuted/NEI |
| **CFEVER** | 8 | 中文事实验证 | 中文 | Supported/Refuted/NEI |
| **MSVEC** | 4 | 多领域科学验证 | 多学科 | Support/Refute/NEI |

### 5.2 模型与框架

| 项目 | GitHub Stars | 功能 | 链接 |
|------|-------------|------|------|
| **FActScore** | 439 | 原子事实精度评估 | `github.com/shmsw25/FActScore` |
| **MultiVerS** | 54 | 多证据科学验证模型 | `github.com/dwadden/multivers` |
| **DeepVerify** | 36 | 专家级科学 claim 验证 | `github.com/xiongsiheng/DeepVerify` |
| **scientific-claim-generation** | 32 | 零样本 claim 生成 | `github.com/allenai/scientific-claim-generation` |
| **Fin-Fact** | 27 | 多模态科学事实核查 | `github.com/IIT-DM/Fin-Fact` |
| **SPECTER** | - | 科学论文嵌入 | AllenAI |

### 5.3 自动化综述工具

| 项目 | GitHub Stars | 功能 | 链接 |
|------|-------------|------|------|
| **ASReview** | 915 | AI 辅助系统性综述筛选 | `github.com/asreview/asreview` |
| **RobotReviewer** | 175 | 自动偏倚风险评估 | `github.com/ijmarshall/robotreviewer` |

### 5.4 LLM Claim 验证工具

| 项目 | GitHub Stars | 创建时间 | 功能 | 链接 |
|------|-------------|----------|------|------|
| **ClaimeAI** | 101 | 2025-05 | LangGraph 事实核查 | `github.com/BharathxD/ClaimeAI` |
| **AgentClaimGuard** | 51 | 2026-05 | Agent 声明验证 | `github.com/konoeph/AgentClaimGuard` |
| **Dokis** | 36 | 2026-03 | RAG 来源验证 | `github.com/Vbj1808/Dokis` |
| **LongTracer** | 34 | 2026-04 | 幻觉检测 STS+NLI | `github.com/ENDEVSOLS/LongTracer` |
| **Clarity Gate** | 30 | 2025-12 | 文档验证协议 | `github.com/frmoretto/clarity-gate` |
| **Verity** | 1 | 2026-03 | 科学 NLI 引擎 | `github.com/AryanAngiras31/Verity` |

---

## 6. 实际应用案例

### 6.1 案例一：Consensus.app 的 Consensus Meter

**场景**: 用户搜索"Does intermittent fasting improve metabolic health?"

**流程**:
1. 语义搜索 200M+ 论文库，找到数百篇相关论文
2. 从每篇论文的摘要/结论中提取 finding
3. LLM 判断每篇论文的立场方向
4. 聚合为百分比：如 75% Yes / 15% Possibly / 10% No
5. 附加质量标签（RCT、Highly Cited 等）

**技术实现要点**:
- 使用 GPT 系列模型进行立场分类
- 基于 Semantic Scholar 数据库
- 用户查询本身作为 canonical claim，避免了显式的 claim 归一化

### 6.2 案例二：SciFact 学术基准

**场景**: 验证生物医学领域的科学声明

**流程**:
1. 专家编写 1,400+ 科学 claim
2. 从 S2ORC 语料库中检索相关摘要
3. 模型预测 Support/Refute/NEI
4. 同时提取 rationale sentences（证据句子）

**模型架构** (MultiVerS):
- 使用 Longformer 编码器处理长文本
- 联合训练：rationale extraction + label prediction
- 在 SciFact leaderboard 上达到最优性能

### 6.3 案例三：FActScore 原子事实验证

**场景**: 评估 LLM 生成的长文本的事实准确性

**流程**:
1. 将 LLM 生成的文本分解为原子事实（atomic facts）
2. 对每个原子事实，从知识源（如 Wikipedia）中检索支持证据
3. 判断每个原子事实是否被支持
4. FActScore = 被支持的原子事实比例

**启示**: 这种"分解-验证-聚合"的范式可以直接应用于多论文 claim 聚合。

### 6.4 案例四：Climate-FEVER 气候共识

**场景**: 验证气候科学领域的声明

**数据**: 1,535 个气候相关 claim，每个 claim 标注为支持/反驳/信息不足

**应用**: 用于对抗气候错误信息，展示科学共识

### 6.5 案例五：COVID-19 健康声明验证 (HealthVer)

**场景**: 验证 COVID-19 相关的健康声明

**流程**:
1. 收集 COVID-19 相关声明
2. 从 CORD-19 数据集中检索科学证据
3. 使用 NLI 模型判断声明与证据的关系
4. 聚合多篇论文的判断结果

---

## 7. 技术难点与解决方案

### 7.1 Claim 归一化难题

**问题**: 不同论文可能用不同方式表述同一发现，如何判断它们指向同一 claim？

**解决方案**:
1. **查询驱动**: 用户输入自然语言问题作为锚点（Consensus.app 方法）
2. **嵌入聚类**: 使用科学文本嵌入（SPECTER/SciBERT）计算相似度后聚类
3. **NLI 判定**: 使用 NLI 模型判断两个 claim 是否等价
4. **知识图谱辅助**: 在 KG 中通过实体和关系连接等价 claim

**推荐方案**: 对于我们的系统，建议采用**查询驱动 + 嵌入聚类**的混合方法：
- 用户选择一个 claim 节点
- 系统使用 SPECTER 嵌入找到语义相似的 finding
- 使用 NLI 模型确认是否真的等价

### 7.2 隐含立场识别

**问题**: 很多论文不会直接说"支持"或"反对"，而是通过实验结果间接表明立场。

**解决方案**:
1. **Chain-of-Thought 推理**: 让 LLM 先分析实验结果，再推断立场
2. **多步验证**: 先提取 finding，再判断 finding 与 claim 的关系
3. **领域知识注入**: 在 prompt 中提供领域背景知识

### 7.3 证据质量差异

**问题**: 不同论文的证据质量差异很大（RCT vs. 个案报告），简单投票不合理。

**解决方案**:
1. **研究设计加权**: RCT > Cohort > Case-Control > Case Report
2. **样本量加权**: 按 log(sample_size) 加权
3. **引用次数加权**: 高引用论文权重更高
4. **偏倚风险评估**: 使用 RobotReviewer 等工具评估偏倚风险
5. **时间衰减**: 更新的研究权重更高

### 7.4 领域适应性

**问题**: 在一个领域训练的模型在另一个领域表现下降。

**解决方案**:
1. **Zero-shot LLM**: 使用 LLM 的 zero-shot 能力，无需领域训练
2. **Domain-adaptive pre-training**: 在目标领域语料上继续预训练
3. **Few-shot 提供领域示例**: 在 prompt 中提供目标领域的标注示例
4. **多领域数据集**: 使用 MSVEC 等多领域数据集训练通用模型

### 7.5 规模与成本

**问题**: 大规模论文处理时 LLM API 成本过高。

**解决方案**:
1. **分层过滤**: 先用 BM25/嵌入粗筛，再用 NLI 中筛，最后用 LLM 精筛
2. **缓存机制**: 缓存已分类的 claim-evidence 对
3. **小模型替代**: 使用微调的小模型（如 SciBERT）替代 LLM
4. **批处理**: 批量处理以降低 API 调用开销

### 7.6 中文科学文本处理

**问题**: 中文学术文本的 claim verification 研究相对较少。

**已知资源**:
- **CFEVER** (IKMLab/CFEVER-data, 8 stars): 中文事实提取和验证数据集 (AAAI 2024)
- 可使用中文 LLM（如 ChatGLM、Qwen）进行中文 claim 的立场分类

---

## 8. 未来发展趋势

### 8.1 LLM 原生的 Claim Verification

2024-2026 年的趋势是将 claim verification 完全构建在 LLM 之上：
- 使用 LLM 进行 claim 提取、立场分类、证据聚合的全链路
- Agent-based 架构：多个 specialized agents 协作完成验证任务
- 如 ClaimeAI (LangGraph)、AgentClaimGuard 等项目所示

### 8.2 实时科学共识追踪

- 从静态的论文库索引走向实时的论文流处理
- Living systematic reviews 的自动化
- 新论文发表时自动更新共识分数

### 8.3 多模态证据聚合

- 不仅考虑文本，还考虑图表、表格中的数据
- SciTab 等工作已开始探索表格数据验证
- 未来可能扩展到实验数据、代码、补充材料

### 8.4 可解释的共识报告

- 不仅给出百分比，还解释为什么得出这个共识
- 提供证据链路：哪些论文、哪些句子支持了这个结论
- 与知识图谱结合，可视化证据网络

### 8.5 与知识图谱的深度融合

- Claim 节点与论文节点、Finding 节点、Evidence 节点形成图结构
- 支持基于图的推理：如"哪些论文的发现相互矛盾"
- 图上的共识传播：通过图结构传播置信度

### 8.6 从 binary 到 nuanced 的立场分类

- 从简单的三路分类（支持/反对/不确定）发展到更细粒度的立场谱系
- 包含：部分支持、有条件支持、方法论质疑、样本量不足等
- 更好地反映科学讨论的复杂性

---

## 9. 参考资料

### 9.1 核心论文

1. **Wadden, D., Lin, S., Lo, K., Wang, L.L., van Zuylen, M., Cohan, A., & Hajishirzi, H.** (2020). "Fact or Fiction: Verifying Scientific Claims." *Proceedings of EMNLP 2020*. — SciFact 数据集和任务定义

2. **Wadden, D., Lo, K., Wang, L.L., & Hajishirzi, H.** (2021). "MultiVerS: Improving Scientific Claim Verification with Weak Supervision and Full-Document Context." — 多证据验证模型

3. **Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P.W., Iyyer, M., Zettlemoyer, L., & Hajishirzi, H.** (2023). "FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation." *ICLR/EMNLP 2023*. — 原子事实评估方法

4. **Cohan, A., Ammar, M., van Zuylen, M., & Cady, F.** (2019). "Structural Scaffolds for Citation Intent Classification in Scientific Papers." *ACL 2019*. — SciCite 引用意图分类

5. **Cohan, A., Feldman, S., Beltagy, I., Downey, D., & Weld, D.S.** (2020). "SPECTER: Document-level Representation Learning using Citation-informed Transformers." *ACL 2020*. — 科学论文嵌入模型

6. **Beltagy, I., Lo, K., & Cohan, A.** (2019). "SciBERT: A Pretrained Language Model for Scientific Text." *EMNLP 2019*. — 科学文本预训练模型

7. **Beltagy, I., Peters, M.E., & Cohan, A.** (2020). "Longformer: The Long-Document Transformer." — 长文本编码器

8. **Khot, T., Sabharwal, A., & Clark, P.** (2018). "SciTail: A Textual Entailment Dataset from Science Question Answering." *AAAI 2018*. — 科学领域 NLI 数据集

9. **Sarrouti, M. & El Asri, L.** (2021). "HealthVer: Health Claim Verification Using Evidence from Medical Research." — 健康声明验证

10. **Sadat, M., et al.** (2022). "SciNLI: A Corpus for Natural Language Inference on Scientific Text." *ACL 2022*. — 科学 NLI 数据集

11. **Lu, X., et al.** (2023). "SCITAB: A Challenging Benchmark for Compositional Reasoning and Claim Verification on Scientific Tables." — 科学表格验证

12. **Hedges, L.V. & Olkin, I.** (1980). "Vote-counting methods in research synthesis." *Psychological Bulletin*. — 投票计数法的经典批评

### 9.2 GitHub 仓库

13. **allenai/scifact** — SciFact 数据集和模型 (261 stars)
    `https://github.com/allenai/scifact`

14. **shmsw25/FActScore** — 原子事实精度评估 (439 stars)
    `https://github.com/shmsw25/FActScore`

15. **sheffieldnlp/naacl2018-fever** — FEVER 基线系统 (129 stars)
    `https://github.com/sheffieldnlp/naacl2018-fever`

16. **awslabs/fever** — FEVER 标注平台 (126 stars)
    `https://github.com/awslabs/fever`

17. **allenai/scicite** — 引用意图分类 (130 stars)
    `https://github.com/allenai/scicite`

18. **asreview/asreview** — AI 辅助系统性综述 (915 stars)
    `https://github.com/asreview/asreview`

19. **ijmarshall/robotreviewer** — 自动偏倚风险评估 (175 stars)
    `https://github.com/ijmarshall/robotreviewer`

20. **dwadden/multivers** — MultiVerS 多证据验证 (54 stars)
    `https://github.com/dwadden/multivers`

21. **BharathxD/ClaimeAI** — LangGraph 事实核查 (101 stars)
    `https://github.com/BharathxD/ClaimeAI`

22. **Raldir/FEVEROUS** — 结构化+非结构化验证 (76 stars)
    `https://github.com/Raldir/FEVEROUS`

23. **msadat3/SciNLI** — 科学 NLI 数据集 (29 stars)
    `https://github.com/msadat3/SciNLI`

### 9.3 产品与平台

24. **Consensus.app** — AI 学术搜索引擎，Consensus Meter 功能
    `https://consensus.app`

25. **Elicit** — AI 研究助手，论文综合与数据提取
    `https://elicit.com`

26. **Semantic Scholar** — AI 学术搜索引擎
    `https://www.semanticscholar.org`

---

## 附录 A：实现建议

### 对于我们的知识图谱系统

基于以上调研，建议分三个阶段实现 Consensus Meter 功能：

#### Phase 1: 基础版本（MVP）

1. **Claim 节点扩展**: 在知识图谱中为 Claim 节点添加 `support_count`, `refute_count`, `nei_count` 字段
2. **LLM 立场分类**: 使用 LLM 对每篇关联论文的 finding 判断其对 claim 的立场
3. **简单聚合**: 计算百分比并存储在 claim 节点上

**Prompt 设计参考**:
```
You are a scientific evidence classifier. Given a claim and a paper's
finding, classify the finding's stance toward the claim.

Claim: {claim_text}
Paper Finding: {finding_text}
Paper Title: {paper_title}

Classify as one of:
- SUPPORT: The finding provides evidence supporting the claim
- REFUTE: The finding provides evidence contradicting the claim
- NEI: The finding is inconclusive, irrelevant, or insufficient

Output JSON: {"stance": "SUPPORT|REFUTE|NEI", "confidence": 0.0-1.0,
"rationale": "brief explanation"}
```

#### Phase 2: 质量加权版本

1. **研究设计权重**: 为不同研究类型分配权重
2. **时间衰减**: 较新的研究权重更高
3. **引用权重**: 高引用论文权重更高
4. **加权共识分数**: 计算加权后的共识百分比

#### Phase 3: 高级版本

1. **Claim 归一化**: 使用 SPECTER 嵌入聚类等价 claim
2. **证据链路**: 从共识分数追溯到具体证据句子
3. **图上推理**: 利用知识图谱结构发现矛盾和知识空白
4. **实时更新**: 新论文入库时自动更新相关 claim 的共识分数

---

## 附录 B：搜索记录

| 编号 | 搜索关键词 | 结果来源 | 关键发现 |
|------|-----------|----------|----------|
| 1 | Consensus meter scientific claims aggregation | WebSearch + 训练知识 | Consensus.app 使用 LLM 将论文结论分为 Yes/Possibly/No |
| 2 | Consensus AI search engine paper analysis | WebSearch + 训练知识 | 索引 200M+ 论文，使用 GPT 模型 |
| 3 | SciFact scientific claim verification dataset | WebSearch + GitHub API | 1,400 claims, Support/Refute/NEI, 261 stars |
| 4 | stance detection scientific citations | WebSearch + 训练知识 | SciCite(130 stars), 三路分类 Background/Method/Result |
| 5 | scientific claim verification NLP multi-document | WebSearch + Semantic Scholar | MultiVerS, DeepVerify 等多证据验证模型 |
| 6 | LLM-based claim extraction prompt engineering | WebSearch + 训练知识 | Zero-shot, Few-shot, CoT 三种 prompt 策略 |
| 7 | multi-document evidence aggregation consensus score | WebSearch + 训练知识 | 投票、加权、概率融合、注意力聚合等方法 |
| 8 | claim normalization paraphrase detection | WebSearch + 训练知识 | SPECTER, SciBERT 嵌入 + 聚类方法 |
| 9 | Consensus app startup funding | WebSearch + 训练知识 | Seed $3M (2022), Series A $10M+ (2023) |
| 10 | GitHub: scientific claim verification repos | GitHub API | 8 个相关仓库，最高 101 stars (ClaimeAI) |
| 11 | GitHub: claim stance detection repos | GitHub API | SciNLI (29 stars), Verity (1 star) |
| 12 | GitHub: FEVER fact verification repos | GitHub API | 10 个仓库，最高 129 stars |
| 13 | GitHub: NLI scientific repos | GitHub API | SciNLI (29 stars), MSciNLI |
| 14 | GitHub: claim verification LLM repos | GitHub API | ClaimeAI (101), AgentClaimGuard (51), Dokis (36) |
| 15 | GitHub: evidence aggregation scientific repos | GitHub API | 无直接匹配结果 |
| 16 | GitHub: meta-analysis NLP repos | GitHub API | 无直接匹配结果 |
| 17 | FActScore fine-grained atomic fact verification | WebSearch + GitHub API | 439 stars, EMNLP 2023, 分解-验证范式 |
| 18 | SciCite citation intent classification | WebSearch + GitHub API | 130 stars, ACL 2019, 三路引用意图 |
| 19 | claim decomposition sub-claims verification | WebSearch + 训练知识 | 分解-检索-验证-聚合管道 |
| 20 | Climate-FEVER dataset | WebSearch + 训练知识 | 1,535 气候声明, Support/Refute/NEI |
| 21 | automated systematic review LLM GPT-4 | WebSearch + 训练知识 | ASReview(915 stars), RobotReviewer(175 stars) |
| 22 | SPECTER scientific paper embeddings | WebSearch + 训练知识 | ACL 2020, 引用图训练的论文嵌入 |
| 23 | HealthVer COVID claim verification | WebSearch + 训练知识 | COVID-19 健康声明验证 |
| 24 | SciTab benchmark scientific tables | WebSearch + 训练知识 | 表格数据 claim 验证 |
| 25 | 多篇论文结论聚合 中文 | WebSearch + 训练知识 | 投票计数法、贝叶斯元分析、NLP/LLM 方法 |
| 26 | claim stance LLM prompt template | WebSearch + 训练知识 | 结构化 prompt + JSON 输出 |
| 27 | knowledge graph claim confidence aggregation | WebSearch + 训练知识 | 概率 KG, 置信度传播 |
| 28 | Elicit AI research tool | WebSearch + 训练知识 | 200M 论文, 结构化数据提取 |
| 29 | vote counting meta-analysis limitations | WebSearch + 训练知识 | Hedges & Olkin (1980) 经典批评 |
| 30 | Scientific claim verification open source 2024 | WebSearch + GitHub API | FActScore, SciFact, ClaimeAI 等 |
