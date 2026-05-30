# 搜索质量对比测试报告

**测试时间**: 2026-05-31 02:49
**测试查询**: `sparse functional data for deep learning`
**数据源**: OpenAlex, arXiv, Semantic Scholar
**返回数量上限**: 50

## 搜索耗时

| 阶段 | 耗时 |
|------|------|
| 搜索（短语匹配+去重+排序） | 10.84s |
| LLM相关性过滤 | 133.22s |
| **总计** | **144.05s** |

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
| 场景1: 短语匹配 + 排序（10.84s） | 10.84s | 49 | 22 | 27 | 45% |
| 场景2: 排序 + min_score≥0.85（10.84 | 10.84s | 43 | 22 | 21 | 51% |
| 场景3: 短语匹配 + 排序 + LLM过滤（144.05s | 144.05s | 49 | 22 | 27 | 45% |
| 场景4: 短语匹配 + 排序 + min_score≥0.8 | 44.62s | 10 | 8 | 2 | 80% |

## 详细结果

### 场景1: 短语匹配 + 排序（10.84s）

- 耗时: 10.84s
- 精准率: 45% (22/49)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | N | 1.401 | Embracing Change: Continual Learning in Deep Neural Networks |
| 2 | N | 1.034 | XGBoost |
| 3 | N | 1.025 | A survey on Image Data Augmentation for Deep Learning |
| 4 | N | 1.024 | AI-Assisted Pipeline for Dynamic Generation of Trustworthy H |
| 5 | N | 0.972 | Array programming with NumPy |
| 6 | N | 0.932 | The STRING database in 2023: protein–protein association net |
| 7 | N | 0.926 | Review of deep learning: concepts, CNN architectures, challe |
| 8 | Y | 0.924 | A Novel Transfer Learning Approach to Enhance Deep Neural Ne |
| 9 | N | 0.923 | Internet of Things (IoT): A vision, architectural elements,  |
| 10 | N | 0.922 | SCANPY: large-scale single-cell gene expression data analysi |
| 11 | N | 0.920 | Explainable Artificial Intelligence (XAI): Concepts, taxonom |
| 12 | N | 0.914 | A survey of transfer learning |
| 13 | N | 0.911 | Dynamic Graph CNN for Learning on Point Clouds |
| 14 | N | 0.911 | Physics-informed machine learning |
| 15 | N | 0.907 | A Survey of Convolutional Neural Networks: Analysis, Applica |
| 16 | N | 0.906 | Dictionary learning for integrative, multimodal and scalable |
| 17 | Y | 0.902 | Modeling Hierarchical Brain Networks via Volumetric Sparse D |
| 18 | N | 0.901 | Advances and Open Problems in Federated Learning |
| 19 | N | 0.900 | Ultrasensitive fluorescent proteins for imaging neuronal act |
| 20 | N | 0.889 | A hybrid deep learning framework for gene regulatory network |
| 21 | Y | 0.889 | Training deep learning models for cell image segmentation wi |
| 22 | Y | 0.887 | Multi-label classification of Alzheimer's disease stages fro |
| 23 | Y | 0.881 | Four-Dimensional Modeling of fMRI Data via Spatio–Temporal C |
| 24 | Y | 0.880 | Unsupervised Deep Learning CAD Scheme for the Detection of M |
| 25 | Y | 0.879 | Automatic Recognition of fMRI-Derived Functional Networks Us |
| 26 | N | 0.879 | Gradient boosting machines, a tutorial |
| 27 | Y | 0.875 | A Hybrid Deep Network Framework for Android Malware Detectio |
| 28 | Y | 0.874 | Deep Learning via Stacked Sparse Autoencoders for Automated  |
| 29 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 30 | Y | 0.872 | Modeling Task fMRI Data Via Deep Convolutional Autoencoder |
| 31 | Y | 0.872 | forgeNet: a graph deep neural network model using tree-based |
| 32 | N | 0.870 | Spiking Neural Networks and Their Applications: A Review |
| 33 | Y | 0.869 | Exploring Neuromorphic Computing Based on Spiking Neural Net |
| 34 | Y | 0.869 | CayleyNets: Graph Convolutional Neural Networks With Complex |
| 35 | Y | 0.868 | DeepSim: deep learning code functional similarity |
| 36 | Y | 0.867 | Multimodal Autism Spectrum Disorder Diagnosis Method Based o |
| 37 | Y | 0.866 | Sequence-to-function deep learning frameworks for engineered |
| 38 | Y | 0.864 | A Deep Learning-Based Model That Reduces Speed of Sound Aber |
| 39 | Y | 0.864 | Deep Variational Autoencoder for Mapping Functional Brain Ne |
| 40 | Y | 0.863 | Deep Learning Meets Sparse Regularization: A signal processi |
| 41 | Y | 0.858 | Adsorption Enthalpies for Catalysis Modeling through Machine |
| 42 | N | 0.857 | Localization Free Super-Resolution Microbubble Velocimetry U |
| 43 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |
| 44 | N | 0.848 | Differentiable biology: using deep learning for biophysics-b |
| 45 | N | 0.847 | The topology of fMRI-based networks defines the performance  |
| 46 | N | 0.844 | Accelerating Materials Development via Automation, Machine L |
| 47 | N | 0.841 | Deep neural network with weight sparsity control and pre-tra |
| 48 | N | 0.840 | Molecular Representation: Going Long on Fingerprints |
| 49 | N | 0.829 | Constructing fine-granularity functional brain network atlas |

### 场景2: 排序 + min_score≥0.85（10.84s）

- 耗时: 10.84s
- 精准率: 51% (22/43)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | N | 1.401 | Embracing Change: Continual Learning in Deep Neural Networks |
| 2 | N | 1.034 | XGBoost |
| 3 | N | 1.025 | A survey on Image Data Augmentation for Deep Learning |
| 4 | N | 1.024 | AI-Assisted Pipeline for Dynamic Generation of Trustworthy H |
| 5 | N | 0.972 | Array programming with NumPy |
| 6 | N | 0.932 | The STRING database in 2023: protein–protein association net |
| 7 | N | 0.926 | Review of deep learning: concepts, CNN architectures, challe |
| 8 | Y | 0.924 | A Novel Transfer Learning Approach to Enhance Deep Neural Ne |
| 9 | N | 0.923 | Internet of Things (IoT): A vision, architectural elements,  |
| 10 | N | 0.922 | SCANPY: large-scale single-cell gene expression data analysi |
| 11 | N | 0.920 | Explainable Artificial Intelligence (XAI): Concepts, taxonom |
| 12 | N | 0.914 | A survey of transfer learning |
| 13 | N | 0.911 | Dynamic Graph CNN for Learning on Point Clouds |
| 14 | N | 0.911 | Physics-informed machine learning |
| 15 | N | 0.907 | A Survey of Convolutional Neural Networks: Analysis, Applica |
| 16 | N | 0.906 | Dictionary learning for integrative, multimodal and scalable |
| 17 | Y | 0.902 | Modeling Hierarchical Brain Networks via Volumetric Sparse D |
| 18 | N | 0.901 | Advances and Open Problems in Federated Learning |
| 19 | N | 0.900 | Ultrasensitive fluorescent proteins for imaging neuronal act |
| 20 | N | 0.889 | A hybrid deep learning framework for gene regulatory network |
| 21 | Y | 0.889 | Training deep learning models for cell image segmentation wi |
| 22 | Y | 0.887 | Multi-label classification of Alzheimer's disease stages fro |
| 23 | Y | 0.881 | Four-Dimensional Modeling of fMRI Data via Spatio–Temporal C |
| 24 | Y | 0.880 | Unsupervised Deep Learning CAD Scheme for the Detection of M |
| 25 | Y | 0.879 | Automatic Recognition of fMRI-Derived Functional Networks Us |
| 26 | N | 0.879 | Gradient boosting machines, a tutorial |
| 27 | Y | 0.875 | A Hybrid Deep Network Framework for Android Malware Detectio |
| 28 | Y | 0.874 | Deep Learning via Stacked Sparse Autoencoders for Automated  |
| 29 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 30 | Y | 0.872 | Modeling Task fMRI Data Via Deep Convolutional Autoencoder |
| 31 | Y | 0.872 | forgeNet: a graph deep neural network model using tree-based |
| 32 | N | 0.870 | Spiking Neural Networks and Their Applications: A Review |
| 33 | Y | 0.869 | Exploring Neuromorphic Computing Based on Spiking Neural Net |
| 34 | Y | 0.869 | CayleyNets: Graph Convolutional Neural Networks With Complex |
| 35 | Y | 0.868 | DeepSim: deep learning code functional similarity |
| 36 | Y | 0.867 | Multimodal Autism Spectrum Disorder Diagnosis Method Based o |
| 37 | Y | 0.866 | Sequence-to-function deep learning frameworks for engineered |
| 38 | Y | 0.864 | A Deep Learning-Based Model That Reduces Speed of Sound Aber |
| 39 | Y | 0.864 | Deep Variational Autoencoder for Mapping Functional Brain Ne |
| 40 | Y | 0.863 | Deep Learning Meets Sparse Regularization: A signal processi |
| 41 | Y | 0.858 | Adsorption Enthalpies for Catalysis Modeling through Machine |
| 42 | N | 0.857 | Localization Free Super-Resolution Microbubble Velocimetry U |
| 43 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |

### 场景3: 短语匹配 + 排序 + LLM过滤（144.05s = 搜索10.84s + LLM133

- 耗时: 144.05s
- 精准率: 45% (22/49)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | N | 1.401 | Embracing Change: Continual Learning in Deep Neural Networks |
| 2 | N | 1.034 | XGBoost |
| 3 | N | 1.025 | A survey on Image Data Augmentation for Deep Learning |
| 4 | N | 1.024 | AI-Assisted Pipeline for Dynamic Generation of Trustworthy H |
| 5 | N | 0.972 | Array programming with NumPy |
| 6 | N | 0.932 | The STRING database in 2023: protein–protein association net |
| 7 | N | 0.926 | Review of deep learning: concepts, CNN architectures, challe |
| 8 | Y | 0.924 | A Novel Transfer Learning Approach to Enhance Deep Neural Ne |
| 9 | N | 0.923 | Internet of Things (IoT): A vision, architectural elements,  |
| 10 | N | 0.922 | SCANPY: large-scale single-cell gene expression data analysi |
| 11 | N | 0.920 | Explainable Artificial Intelligence (XAI): Concepts, taxonom |
| 12 | N | 0.914 | A survey of transfer learning |
| 13 | N | 0.911 | Dynamic Graph CNN for Learning on Point Clouds |
| 14 | N | 0.911 | Physics-informed machine learning |
| 15 | N | 0.907 | A Survey of Convolutional Neural Networks: Analysis, Applica |
| 16 | N | 0.906 | Dictionary learning for integrative, multimodal and scalable |
| 17 | Y | 0.902 | Modeling Hierarchical Brain Networks via Volumetric Sparse D |
| 18 | N | 0.901 | Advances and Open Problems in Federated Learning |
| 19 | N | 0.900 | Ultrasensitive fluorescent proteins for imaging neuronal act |
| 20 | N | 0.889 | A hybrid deep learning framework for gene regulatory network |
| 21 | Y | 0.889 | Training deep learning models for cell image segmentation wi |
| 22 | Y | 0.887 | Multi-label classification of Alzheimer's disease stages fro |
| 23 | Y | 0.881 | Four-Dimensional Modeling of fMRI Data via Spatio–Temporal C |
| 24 | Y | 0.880 | Unsupervised Deep Learning CAD Scheme for the Detection of M |
| 25 | Y | 0.879 | Automatic Recognition of fMRI-Derived Functional Networks Us |
| 26 | N | 0.879 | Gradient boosting machines, a tutorial |
| 27 | Y | 0.875 | A Hybrid Deep Network Framework for Android Malware Detectio |
| 28 | Y | 0.874 | Deep Learning via Stacked Sparse Autoencoders for Automated  |
| 29 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 30 | Y | 0.872 | Modeling Task fMRI Data Via Deep Convolutional Autoencoder |
| 31 | Y | 0.872 | forgeNet: a graph deep neural network model using tree-based |
| 32 | N | 0.870 | Spiking Neural Networks and Their Applications: A Review |
| 33 | Y | 0.869 | Exploring Neuromorphic Computing Based on Spiking Neural Net |
| 34 | Y | 0.869 | CayleyNets: Graph Convolutional Neural Networks With Complex |
| 35 | Y | 0.868 | DeepSim: deep learning code functional similarity |
| 36 | Y | 0.867 | Multimodal Autism Spectrum Disorder Diagnosis Method Based o |
| 37 | Y | 0.866 | Sequence-to-function deep learning frameworks for engineered |
| 38 | Y | 0.864 | A Deep Learning-Based Model That Reduces Speed of Sound Aber |
| 39 | Y | 0.864 | Deep Variational Autoencoder for Mapping Functional Brain Ne |
| 40 | Y | 0.863 | Deep Learning Meets Sparse Regularization: A signal processi |
| 41 | Y | 0.858 | Adsorption Enthalpies for Catalysis Modeling through Machine |
| 42 | N | 0.857 | Localization Free Super-Resolution Microbubble Velocimetry U |
| 43 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |
| 44 | N | 0.848 | Differentiable biology: using deep learning for biophysics-b |
| 45 | N | 0.847 | The topology of fMRI-based networks defines the performance  |
| 46 | N | 0.844 | Accelerating Materials Development via Automation, Machine L |
| 47 | N | 0.841 | Deep neural network with weight sparsity control and pre-tra |
| 48 | N | 0.840 | Molecular Representation: Going Long on Fingerprints |
| 49 | N | 0.829 | Constructing fine-granularity functional brain network atlas |

### 场景4: 短语匹配 + 排序 + min_score≥0.85 + LLM过滤（44.62s）

- 耗时: 44.62s
- 精准率: 80% (8/10)

| # | 相关 | 分数 | 标题 |
|---|------|------|------|
| 1 | Y | 0.924 | A Novel Transfer Learning Approach to Enhance Deep Neural Ne |
| 2 | N | 0.906 | Dictionary learning for integrative, multimodal and scalable |
| 3 | Y | 0.902 | Modeling Hierarchical Brain Networks via Volumetric Sparse D |
| 4 | N | 0.889 | A hybrid deep learning framework for gene regulatory network |
| 5 | Y | 0.889 | Training deep learning models for cell image segmentation wi |
| 6 | Y | 0.874 | Deep Learning via Stacked Sparse Autoencoders for Automated  |
| 7 | Y | 0.873 | Deep-fUS: A Deep Learning Platform for Functional Ultrasound |
| 8 | Y | 0.872 | forgeNet: a graph deep neural network model using tree-based |
| 9 | Y | 0.863 | Deep Learning Meets Sparse Regularization: A signal processi |
| 10 | Y | 0.856 | Deep-fUS: Functional ultrasound imaging of the brain using d |

## 分析

### 相关性判断标准
- 论文标题或摘要必须同时包含 `sparse` 和 `functional`
- 仅包含 `deep learning`、`data` 等泛词的论文判定为不相关

### Token 消耗

- LLM过滤消耗约 **1次 API 调用**，输入约 2500 tokens（50篇论文标题+摘要），输出约 100 tokens
- LLM过滤耗时 **133.2s**

### 建议

- 最佳精准率: **场景4: 短语匹配 + 排序 + min_score≥0.85 + LLM过滤（** (80%)
- 最快方案: **场景1: 短语匹配 + 排序（10.84s）** (10.8s)

全方案（场景4）相比基线（场景1）精准率提升 **35%**，额外耗时 33.8s。