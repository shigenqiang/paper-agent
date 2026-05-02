# Query Rewrite Comparison Test Report

**测试日期**: 2026-05-02 07:52:35
**测试查询数**: 5

## 汇总统计

| 指标 | 值 |
|------|-----|
| 总测试查询数 | 5 |
| 平均原始得分 | 7.93 |
| 平均改写后得分 | 7.67 |
| 整体相关性变化 | -3.3% |
| 查询改写启用率 | 60.0% |

## 详细测试结果

## 测试查询: "attention is all you need"

### 查询改写信息

| 项目 | 值 |
|------|-----|
| 原始查询 | attention is all you need |
| 改写后查询 | transformer self-attention 注意力 is all you need |
| 改写类型 | expansion |
| 置信度 | 0.80 |
| 改写原因 | 添加同义词: attention → ['transformer', 'self-attention', '注意力'] |

### 搜索结果对比

| 指标 | 原始查询 | 改写后查询 | 变化 |
|------|---------|-----------|------|
| 结果数量 | 20 | 11 | -9 |
| 平均相关性得分 | 8.53 | 9.95 | +16.8% |
| 搜索耗时 | 2.89s | 3.35s | +0.46s |
| 结果重叠率 | - | 18.2% | - |
| 新增结果数 | - | 9 | - |

### Top 5 结果对比

**原始查询结果：**
1. "All You Need" is Not All You Need for a Paper Title: On the... (得分: 18.0)
2. Grounding is All You Need? Dual Temporal Grounding for Video... (得分: 16.0)
3. Correction to: Attention is all you need: utilizing attentio... (得分: 16.0)
4. Do You Even Need Attention? A Stack of Feed-Forward Layers D... (得分: 15.0)
5. GAN Vocoder: Multi-Resolution Discriminator Is All You Need... (得分: 14.0)

**改写后查询结果：**
1. "All You Need" is Not All You Need for a Paper Title: On the... (得分: 18.0)
2. Attention Guided CAM: Visual Explanations of Vision Transfor... (得分: 14.0)
3. Self-Attention as Distributional Projection: A Unified Inter... (得分: 14.0)
4. Attention is all you need (in the brain): semantic contextua... (得分: 13.0)
5. Understanding Self-Attention of Self-Supervised Audio Transf... (得分: 12.0)

---

## 测试查询: "BERT pre-training"

### 查询改写信息

| 项目 | 值 |
|------|-----|
| 原始查询 | BERT pre-training |
| 改写后查询 | BERT pre-training |
| 改写类型 | decomposition |
| 置信度 | 0.50 |
| 改写原因 | 无法分解，使用原查询 |

### 搜索结果对比

| 指标 | 原始查询 | 改写后查询 | 变化 |
|------|---------|-----------|------|
| 结果数量 | 12 | 12 | +0 |
| 平均相关性得分 | 5.12 | 5.12 | +0.0% |
| 搜索耗时 | 1.94s | 2.58s | +0.64s |
| 结果重叠率 | - | 100.0% | - |
| 新增结果数 | - | 0 | - |

### Top 5 结果对比

**原始查询结果：**
1. BEiT: BERT Pre-Training of Image Transformers... (得分: 8.0)
2. Kaleido-BERT: Vision-Language Pre-training on Fashion Domain... (得分: 8.0)
3. Pre-training technique to localize medical BERT and enhance ... (得分: 8.0)
4. Integrating BERT pre-training with graph common neighbours f... (得分: 7.0)
5. LV-BERT: Exploiting Layer Variety for BERT... (得分: 5.0)

**改写后查询结果：**
1. BEiT: BERT Pre-Training of Image Transformers... (得分: 8.0)
2. Kaleido-BERT: Vision-Language Pre-training on Fashion Domain... (得分: 8.0)
3. Pre-training technique to localize medical BERT and enhance ... (得分: 8.0)
4. Integrating BERT pre-training with graph common neighbours f... (得分: 7.0)
5. LV-BERT: Exploiting Layer Variety for BERT... (得分: 5.0)

---

## 测试查询: "GPT-3 language model"

### 查询改写信息

| 项目 | 值 |
|------|-----|
| 原始查询 | GPT-3 language model |
| 改写后查询 | GPT-3 language model |
| 改写类型 | decomposition |
| 置信度 | 0.50 |
| 改写原因 | 无法分解，使用原查询 |

### 搜索结果对比

| 指标 | 原始查询 | 改写后查询 | 变化 |
|------|---------|-----------|------|
| 结果数量 | 10 | 10 | +0 |
| 平均相关性得分 | 8.80 | 8.80 | +0.0% |
| 搜索耗时 | 1.84s | 1.87s | +0.04s |
| 结果重叠率 | - | 100.0% | - |
| 新增结果数 | - | 0 | - |

### Top 5 结果对比

**原始查询结果：**
1. Improving accuracy of GPT-3/4 results on biomedical data usi... (得分: 12.5)
2. A Survey of GPT-3 Family Large Language Models Including Cha... (得分: 12.5)
3. How do language models learn facts? Dynamics, curricula and ... (得分: 9.0)
4. GPT-NeoX-20B: An Open-Source Autoregressive Language Model... (得分: 9.0)
5. Language Models as Few-Shot Learner for Task-Oriented Dialog... (得分: 9.0)

**改写后查询结果：**
1. Improving accuracy of GPT-3/4 results on biomedical data usi... (得分: 12.5)
2. A Survey of GPT-3 Family Large Language Models Including Cha... (得分: 12.5)
3. How do language models learn facts? Dynamics, curricula and ... (得分: 9.0)
4. GPT-NeoX-20B: An Open-Source Autoregressive Language Model... (得分: 9.0)
5. Language Models as Few-Shot Learner for Task-Oriented Dialog... (得分: 9.0)

---

## 测试查询: "neural network machine learning"

### 查询改写信息

| 项目 | 值 |
|------|-----|
| 原始查询 | neural network machine learning |
| 改写后查询 | neural network 深度学习 deep learning neural network 神经网络 machine machine learning deep learning 机器学习 深度学习 |
| 改写类型 | expansion |
| 置信度 | 0.80 |
| 改写原因 | 添加同义词: neural → ['neural network', '深度学习', 'deep learning'], 添加同义词: network → ['neural network', '神经网络'], 添加同义词: learning → ['machine learning', 'deep learning', '机器学习', '深度学习'] |

### 搜索结果对比

| 指标 | 原始查询 | 改写后查询 | 变化 |
|------|---------|-----------|------|
| 结果数量 | 20 | 20 | +0 |
| 平均相关性得分 | 9.12 | 6.33 | -30.7% |
| 搜索耗时 | 2.02s | 3.92s | +1.90s |
| 结果重叠率 | - | 35.0% | - |
| 新增结果数 | - | 13 | - |

### Top 5 结果对比

**原始查询结果：**
1. Fourier Learning Machines: Nonharmonic Fourier-Based Neural ... (得分: 17.0)
2. Thermal analysis of flat plate solar air heater system with ... (得分: 13.0)
3. Predicting concentration levels of air pollutants by transfe... (得分: 13.0)
4. TapNet: Neural Network Augmented with Task-Adaptive Projecti... (得分: 13.0)
5. ReSet: Learning Recurrent Dynamic Routing in ResNet-like Neu... (得分: 13.0)

**改写后查询结果：**
1. Fourier Learning Machines: Nonharmonic Fourier-Based Neural ... (得分: 17.0)
2. Predicting concentration levels of air pollutants by transfe... (得分: 13.0)
3. TapNet: Neural Network Augmented with Task-Adaptive Projecti... (得分: 13.0)
4. Enhancing credit card fraud detection with a hybrid approach... (得分: 10.0)
5. The Modern Mathematics of Deep Learning... (得分: 10.0)

---

## 测试查询: "deep learning for computer vision"

### 查询改写信息

| 项目 | 值 |
|------|-----|
| 原始查询 | deep learning for computer vision |
| 改写后查询 | deep machine learning deep learning 机器学习 深度学习 for computer computer vision 图像 CV |
| 改写类型 | expansion |
| 置信度 | 0.80 |
| 改写原因 | 添加同义词: learning → ['machine learning', 'deep learning', '机器学习', '深度学习'], 添加同义词: vision → ['computer vision', '图像', 'CV'] |

### 搜索结果对比

| 指标 | 原始查询 | 改写后查询 | 变化 |
|------|---------|-----------|------|
| 结果数量 | 20 | 20 | +0 |
| 平均相关性得分 | 8.07 | 8.15 | +0.9% |
| 搜索耗时 | 2.05s | 4.07s | +2.02s |
| 结果重叠率 | - | 30.0% | - |
| 新增结果数 | - | 14 | - |

### Top 5 结果对比

**原始查询结果：**
1. Deep Learning vs. Traditional Computer Vision... (得分: 17.0)
2. FedCV: A Federated Learning Framework for Diverse Computer V... (得分: 16.0)
3. Development of an automated fruit classification system by u... (得分: 13.0)
4. Spatial Monitoring and Insect Behavioural Analysis Using Com... (得分: 12.0)
5. Predicting Thrombectomy Recanalization from CT Imaging Using... (得分: 10.5)

**改写后查询结果：**
1. PePR: Performance Per Resource Unit as a Metric to Promote S... (得分: 13.0)
2. Automated measurement of horizontal strabismus in children's... (得分: 13.0)
3. Changing Data Sources in the Age of Machine Learning for Off... (得分: 12.5)
4. A multitask deep learning model for real-time deployment in ... (得分: 14.0)
5. Predicting Thrombectomy Recanalization from CT Imaging Using... (得分: 12.5)

---

## 结论与分析

### 改写类型分布

- expansion: 3 次
- decomposition: 2 次

### 分析

1. **查询改写效果**：
   - 查询改写后整体相关性下降了 **3.3%**
   - 部分改写可能过于激进或方向不正确，需要调整改写策略

2. **结果重叠率分析**：
   - 平均结果重叠率: **56.6%**
   - 重叠率适中，改写带来了一部分新结果

3. **新增结果分析**：
   - 总新增结果数: **36** 篇
   - 平均每查询新增: **7.2** 篇

### 建议

1. 对于**短查询**（<10字符），建议启用查询扩展以获得更多结果
2. 对于**复杂查询**（多主题），建议启用查询分解
3. 对于**中英混合查询**，建议启用语言统一功能
4. 可以通过环境变量 `ENABLE_QUERY_REWRITE` 控制是否启用查询改写