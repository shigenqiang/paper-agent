# 搜索质量对比测试报告

**测试时间**: 2026-05-31 02:38
**测试查询**: `sparse functional data for deep learning`
**数据源**: OpenAlex, arXiv, Semantic Scholar
**返回数量上限**: 20

## 搜索耗时

| 阶段 | 耗时 |
|------|------|
| 搜索（短语匹配+去重+排序） | 9.79s |
| LLM相关性过滤 | 68.72s |
| **总计** | **78.51s** |

## 测试方案说明

| 方案 | 短语匹配 | min_score | LLM过滤 | 说明 |
|------|---------|-----------|---------|------|
| 场景1 | 开 | 关 | 关 | 仅短语匹配+排序 |
| 场景2 | 开 | 0.3 | 关 | 短语匹配+排序+低分过滤 |
| 场景3 | 开 | 关 | 开 | 短语匹配+排序+LLM相关性判断 |
| 场景4 | 开 | 0.3 | 开 | 全部开启（推荐） |

## 结果汇总

| 方案 | 耗时 | 总数 | 相关 | 不相关 | 精准率 |
|------|------|------|------|--------|--------|
| 场景1: 短语匹配 + 排序（9.79s） | 9.79s | 19 | 11 | 8 | 58% |
| 场景2: 排序 + min_score≥0.85（9.79s | 9.79s | 16 | 11 | 5 | 69% |
| 场景3: 短语匹配 + 排序 + LLM过滤（78.51s  | 78.51s | 2 | 2 | 0 | 100% |
| 场景4: 短语匹配 + 排序 + min_score≥0.8 | 48.99s | 3 | 3 | 0 | 100% |

## 详细结果

### 场景1: 短语匹配 + 排序（9.79s）

- 耗时: 9.79s
- 精准率: 58% (11/19)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | N | 1.401 | Embracing Change: Continual Learning in Deep Neural Networks |
| 2 | N | 1.034 | XGBoost |
| 3 | N | 1.024 | AI-Assisted Pipeline for Dynamic Generation of Trustworthy H |
| 4 | N | 0.972 | Array programming with NumPy |
| 5 | Y | 0.924 | A Novel Transfer Learning Approach to Enhance Deep Neural Ne |
| 6 | Y | 0.887 | Multi-label classification of Alzheimer's disease stages fro |
| 7 | Y | 0.879 | Automatic Recognition of fMRI-Derived Functional Networks Us |
| 8 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 9 | Y | 0.872 | Modeling Task fMRI Data Via Deep Convolutional Autoencoder |
| 10 | N | 0.870 | Spiking Neural Networks and Their Applications: A Review |
| 11 | Y | 0.869 | Exploring Neuromorphic Computing Based on Spiking Neural Net |
| 12 | Y | 0.869 | CayleyNets: Graph Convolutional Neural Networks With Complex |
| 13 | Y | 0.868 | DeepSim: deep learning code functional similarity |
| 14 | Y | 0.866 | Sequence-to-function deep learning frameworks for engineered |
| 15 | Y | 0.864 | A Deep Learning-Based Model That Reduces Speed of Sound Aber |
| 16 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |
| 17 | N | 0.848 | Differentiable biology: using deep learning for biophysics-b |
| 18 | N | 0.847 | The topology of fMRI-based networks defines the performance  |
| 19 | N | 0.841 | Deep neural network with weight sparsity control and pre-tra |

### 场景2: 排序 + min_score≥0.85（9.79s）

- 耗时: 9.79s
- 精准率: 69% (11/16)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | N | 1.401 | Embracing Change: Continual Learning in Deep Neural Networks |
| 2 | N | 1.034 | XGBoost |
| 3 | N | 1.024 | AI-Assisted Pipeline for Dynamic Generation of Trustworthy H |
| 4 | N | 0.972 | Array programming with NumPy |
| 5 | Y | 0.924 | A Novel Transfer Learning Approach to Enhance Deep Neural Ne |
| 6 | Y | 0.887 | Multi-label classification of Alzheimer's disease stages fro |
| 7 | Y | 0.879 | Automatic Recognition of fMRI-Derived Functional Networks Us |
| 8 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 9 | Y | 0.872 | Modeling Task fMRI Data Via Deep Convolutional Autoencoder |
| 10 | N | 0.870 | Spiking Neural Networks and Their Applications: A Review |
| 11 | Y | 0.869 | Exploring Neuromorphic Computing Based on Spiking Neural Net |
| 12 | Y | 0.869 | CayleyNets: Graph Convolutional Neural Networks With Complex |
| 13 | Y | 0.868 | DeepSim: deep learning code functional similarity |
| 14 | Y | 0.866 | Sequence-to-function deep learning frameworks for engineered |
| 15 | Y | 0.864 | A Deep Learning-Based Model That Reduces Speed of Sound Aber |
| 16 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |

### 场景3: 短语匹配 + 排序 + LLM过滤（78.51s = 搜索9.79s + LLM68.72

- 耗时: 78.51s
- 精准率: 100% (2/2)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 2 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |

### 场景4: 短语匹配 + 排序 + min_score≥0.85 + LLM过滤（48.99s）

- 耗时: 48.99s
- 精准率: 100% (3/3)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | Y | 0.879 | Automatic Recognition of fMRI-Derived Functional Networks Us |
| 2 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 3 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |

## 分析

### 相关性判断标准
- 论文标题或摘要必须同时包含 `sparse` 和 `functional`
- 仅包含 `deep learning`、`data` 等泛词的论文判定为不相关

### Token 消耗

- LLM过滤消耗约 **1次 API 调用**，输入约 1000 tokens（20篇论文标题+摘要），输出约 100 tokens
- LLM过滤耗时 **68.7s**

### 建议

- 最佳精准率: **场景3: 短语匹配 + 排序 + LLM过滤（78.51s = 搜索9.79s ** (100%)
- 最快方案: **场景1: 短语匹配 + 排序（9.79s）** (9.8s)

全方案（场景4）相比基线（场景1）精准率提升 **42%**，额外耗时 39.2s。