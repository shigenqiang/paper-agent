# Multimodal 多模态处理详解

> 位置: `src/agents_v2/multimodal/`

## 一、架构概览

```
multimodal/
├── __init__.py
├── chart_analyzer.py        # 图表分析 (15KB)
├── diagram_parser.py       # 图表解析 (7KB)
├── figure_classifier.py    # 图表分类 (8KB)
├── formula_recognizer.py   # 公式识别 (8KB)
├── multimodal_retriever.py # 多模态检索 (13KB)
└── vision_encoder.py       # 视觉编码器 (10KB)
```

## 二、功能描述

### 2.1 图表分析 (ChartAnalyzer)

**功能**: 分析论文中的图表，提取数据信息和结构

**输入**: 图表图片 (PNG/JPG/SVG)

**处理流程**:
1. 图表类型识别（折线图/柱状图/饼图/热力图/散点图）
2. 数据提取（坐标轴数据、图例、标签）
3. 趋势分析（增长/下降/波动）
4. 关键发现总结

**输出**:
```python
ChartAnalysis:
    chart_type: str           # 图表类型
    title: str                # 图表标题
    data_points: List[dict]  # 提取的数据点
    trends: List[str]        # 趋势分析结果
    key_findings: List[str]  # 关键发现
    ocr_text: str            # OCR识别文字
```

### 2.2 公式识别 (FormulaRecognizer)

**功能**: 识别并转换学术公式

**支持的格式**:
- LaTeX
- MathML
- 图片 (截图/扫描)

**处理流程**:
1. 公式区域检测
2. 公式类型识别（内联/独立）
3. 公式结构解析
4. LaTeX/MathML 转换

**输出**:
```python
FormulaResult:
    latex: str               # LaTeX格式
    mathml: str              # MathML格式
    plain_text: str          # 纯文本描述
    is_inline: bool          # 是否内联公式
```

### 2.3 图表分类 (FigureClassifier)

**功能**: 对图表进行分类和标注

**分类体系**:
| 类别 | 说明 | 示例 |
|------|------|------|
| performance | 性能对比图 | 准确率/速度对比 |
| architecture | 架构图 | 网络结构/系统设计 |
| workflow | 流程图 | 算法流程/处理步骤 |
| comparison | 对比图 | 实验结果对比 |
| distribution | 分布图 | 数据分布直方图 |
| correlation | 相关图 | 相关性热力图 |
| timeline | 时序图 | 训练曲线/时间序列 |

### 2.4 视觉编码器 (VisionEncoder)

**功能**: 将图像编码为向量，支持语义检索

**模型**: 支持多种视觉模型
- CLIP
- ViT
- 专用学术图表模型

**用途**:
- 图表相似度检索
- 图表聚类
- 跨模态检索（文本↔图表）

## 三、多模态检索

### 3.1 MultimodalRetriever

**功能**: 支持文本+图表的混合检索

**检索模式**:
| 模式 | 说明 | 场景 |
|------|------|------|
| text_only | 纯文本检索 | 文字查询 |
| image_only | 纯图像检索 | 以图搜图 |
| hybrid | 文本+图像混合 | 综合查询 |

**处理流程**:
1. 解析查询（判断是否含图像）
2. 文本向量化
3. 图像向量化（可选）
4. 相似度计算
5. 结果排序返回

## 四、在论文写作中的应用

### 4.1 图表处理流程

```
论文PDF
    │
    ▼
┌─────────────────────────────────────────┐
│  PDF解析                                 │
│  - 提取文本                              │
│  - 提取图表                              │
│  - 提取表格                              │
└─────────────────────────────────────────┘
    │
    ├──► 图表分析 → 描述生成 → 引用标注
    │
    ├──► 公式识别 → LaTeX转换 → 格式规范化
    │
    └──► 表格检测 → 数据提取 → 结构化存储
```

### 4.2 写作辅助

**功能**:
- 根据文字描述推荐相关图表
- 自动生成图表说明文字
- 检测图表引用完整性
- 图表数据可视化验证

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/multimodal/`