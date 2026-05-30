# 学术 PDF 解析综合技术报告

**编制时间**：2026-05-30
**综合来源**：7 份 PDF 解析调研报告 + 当前代码实现分析
**目标**：为 PaperAgent 项目提供完整的 PDF 解析技术蓝图与优化路线

---

## 1. 问题全景

### 1.1 PDF 的本质

PDF 是**基于坐标的绘图指令格式**，本质上是"数字纸张"，而非语义结构化数据。一个"段落"在 PDF 内部可能由数十条独立的文本绘制指令拼凑而成，没有"段落"、"章节"、"表格"等语义标签。

这意味着：**PDF 解析永远是信息有损的近似还原**。

### 1.2 学术 PDF 的特殊挑战

| 挑战维度 | 具体表现 | 影响 |
|---------|---------|------|
| 多栏布局 | 双栏/三栏排版，阅读顺序复杂 | 文本交叉混杂，NLP 不可用 |
| 数学公式 | 行内公式、块级公式、嵌套结构 | 打断文本流，产生乱码或空白 |
| 表格 | 有线表/无线表/跨页表/合并单元格 | 结构丢失，数据断裂 |
| 参考文献 | 多种引用格式、编号/作者-年份混合 | 结构化提取困难 |
| 页眉页脚 | 期刊信息、页码、脚注 | 混入正文，污染语料 |
| 中文 PDF | CID 字体编码、PUA 映射、水印 | 提取文本完全不可用 |
| 扫描件 | 无文本层，纯图像 | 需要 OCR，精度受限 |

### 1.3 技术演进四代

| 世代 | 时期 | 技术特征 | 代表方案 | 适用场景 |
|-----|------|---------|---------|---------|
| 第一代 | 1990s-2000s | 字符坐标抓取 | PyMuPDF, PDFMiner | 原生文本 PDF |
| 第二代 | 2010s | OCR 流水线 | PaddleOCR + YOLO | 扫描件 |
| 第三代 | 2020s | CV+NLP 语义重构 | LayoutLMv3, TableFormer | 复杂布局 |
| 第四代 | 2024- | VLM 端到端 | Dolphin, Nougat, ColPali | 高精度需求 |

---

## 2. 当前实现分析

### 2.1 现有架构

```
PDF 文件输入
    │
    ▼
ParserService.parse_paper()
    │
    ├── ParserAdapter 链（fallback）
    │   ├── PdfPlumberAdapter（默认）
    │   └── PyMuPDFAdapter（fallback）
    │
    ├── 乱码检测 (_detect_garbled_text)
    ├── 水印检测 (_detect_watermark)
    ├── 双栏检测 (_detect_dual_column)
    │
    ├── 章节分块 (_chunk_by_sections)
    │   └── 500-900 tokens/块，80 token overlap
    │
    ├── 参考文献提取 (_extract_references)
    │
    └── 质量标记 (quality_flags + diagnostics)
```

### 2.2 当前能力评估

| 能力 | 状态 | 评级 | 说明 |
|------|------|------|------|
| 文本提取 | 已实现 | 3/5 | pdfplumber + PyMuPDF fallback |
| 章节检测 | 已实现 | 3/5 | 正则匹配中英文标题 |
| 分块策略 | 已实现 | 3/5 | Section-Based + overlap |
| 乱码检测 | 已实现 | 3/5 | 控制字符/替换字符/PUA |
| 水印检测 | 已实现 | 2/5 | 关键词 + 重复短文本 |
| 双栏检测 | 已实现 | 2/5 | 仅检测标记，不重排文本 |
| 参考文献 | 已实现 | 2/5 | 正则分割，启发式提取 |
| 布局分析 | 未实现 | 1/5 | 无 DLA 能力 |
| 表格提取 | 未实现 | 1/5 | 无结构化表格提取 |
| 公式识别 | 未实现 | 0/5 | 无公式处理 |
| OCR fallback | 未实现 | 0/5 | 扫描件直接失败 |
| 阅读顺序 | 未实现 | 1/5 | 双栏文本仍然交叉 |

### 2.3 关键瓶颈

1. **双栏文本交叉**：`_detect_dual_column` 只标记不修正，提取的文本左右混杂
2. **中文 PDF 乱码**：检测到乱码后 fallback 到 PyMuPDF，但两个库都无法处理 PUA 映射
3. **扫描件完全无法处理**：标记 `scanned_pdf_suspected` 后直接放弃
4. **表格/公式被当作纯文本**：结构信息完全丢失
5. **参考文献提取粗糙**：正则分割，作者/标题猜测准确率低

---

## 3. 布局检测与阅读顺序

### 3.1 问题本质

pdfplumber 和 PyMuPDF 的 `extract_text()` 按 PDF 内部内容流顺序返回文本。双栏 PDF 的内容流通常是左右栏交替写入，导致提取的文本左右交叉混杂：

```
实际提取：左栏第1行 | 右栏第1行 | 左栏第2行 | 右栏第2行 ...
期望输出：左栏全部 → 右栏全部
```

### 3.2 业界检测算法

#### 3.2.1 投影剖面法 (Projection Profile)

最经典的分栏检测算法（Nagy & Seth, 1984）：

```
1. 统计页面每一列的字符数 → 垂直投影剖面
2. 峰值对应文本列，谷值（接近零）对应列间距
3. 中间 1/3 区域存在深谷 → 双栏
```

#### 3.2.2 空白谷检测法 (Whitespace Valley)

投影剖面的改进版：
1. 计算垂直投影剖面
2. 高斯平滑降噪
3. 找所有局部最小值（谷）
4. 按深度和宽度排序
5. 最深最宽的谷即为列分界线

#### 3.2.3 XY-Cut 递归切割

经典自顶向下页面分割：
1. 水平投影 → 找最宽空白带 → Y 切割
2. 对每个子区域做垂直投影 → X 切割
3. 递归交替，直到区域过小

**局限**：对倾斜文本、非曼哈顿布局敏感。

#### 3.2.4 GROBID CRF 方法

用 CRF 序列标注模型做页面分割，特征包括：
- 字体大小、字体名、粗体/斜体
- 页面绝对位置（归一化坐标）
- 行间距
- 字符级特征：大写比例、数字比例、标点密度
- 词汇特征：是否以数字开头、是否含 "Abstract"/"References"

### 3.3 当前实现的不足与改进

**当前 `_detect_dual_column`**：基于行长度分布启发式，只能检测不能修正。

**改进方案：PyMuPDF Blocks + 空白谷检测**

```python
def extract_column_aware(pdf_path):
    """分栏感知的文本提取"""
    import fitz
    doc = fitz.open(pdf_path)
    all_pages = []

    for page in doc:
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

        if not text_blocks:
            all_pages.append("")
            continue

        page_width = page.rect.width
        boundary = find_column_boundary(text_blocks, page_width)

        if boundary is None:
            # 单栏：按 y 排序
            text_blocks.sort(key=lambda b: (b[1], b[0]))
            text = "\n".join(b[4].strip() for b in text_blocks)
            all_pages.append(text)
            continue

        # 分类：左栏、右栏、全宽
        left, right, full = [], [], []
        for b in text_blocks:
            x0, y0, x1, y1, text, *_ = b
            if x1 < boundary + 10:
                left.append(b)
            elif x0 > boundary - 10:
                right.append(b)
            else:
                full.append(b)

        # 各组按 y 排序
        left.sort(key=lambda b: (b[1], b[0]))
        right.sort(key=lambda b: (b[1], b[0]))
        full.sort(key=lambda b: b[1])

        # 合并：全宽 → 左栏 → 右栏
        ordered = full + left + right
        text = "\n".join(b[4].strip() for b in ordered)
        all_pages.append(text)

    doc.close()
    return all_pages
```

**关键改进点**：
1. 使用 `page.get_text("blocks")` 获取带坐标的文本块
2. 通过空白谷检测找列分界线
3. 全宽元素（标题、摘要）放在列内容之前
4. 各组内部按 y 坐标排序保证阅读顺序

### 3.4 ML 方案对比（用于后续升级）

| 方案 | Stars | CPU 速度 | 分栏处理 | 集成难度 | 推荐场景 |
|------|-------|---------|---------|---------|---------|
| PyMuPDF blocks + 聚类 | — | 极快 | 手动 | 低 | **当前阶段首选** |
| GROBID (Docker) | 4.9K | 中 | 原生 | 中 | 元数据+参考文献 |
| Marker | 35K | 慢 | 原生 | 低 | 高精度 Markdown |
| Docling | 60K | 慢 | 原生 | 低 | 生产环境 |
| MinerU | 65K | 慢 | 原生 | 中 | 中文最佳 |
| Surya | 19K | 慢 | 原生 | 中 | 90+ 语言统一 |

---

## 4. 中文 PDF 特殊处理

### 4.1 根本原因：CID 字体编码

知网/万方 PDF 使用 CID-keyed 字体，字符编码链路：

```
PDF 内容流字节序列
    → CID (Character ID)         ← Encoding CMap (如 GBK-EUC-H)
    → Glyph Index                ← CIDMap
    → Unicode 码点               ← ToUnicode CMap  ← 这一环在知网 PDF 中损坏/缺失
```

知网故意将字符映射到 Unicode PUA（Private Use Area, U+E000-U+F8FF），这是**版权保护手段**，不是 bug。

### 4.2 三种常见问题

| 问题 | 表现 | 非 OCR 方案成功率 |
|------|------|-----------------|
| ToUnicode CMap 完全缺失 | 提取结果为空或乱码 | 中（多库尝试可能成功） |
| ToUnicode CMap 被映射到 PUA 区 | 提取结果为私用区字符 | 低（知网故意为之） |
| ToUnicode CMap 不完整 | 部分字符正确，部分乱码 | 中 |

### 4.3 当前实现的不足

当前 `_detect_garbled_text` 能检测乱码，但 fallback 策略不够：
- pdfplumber → PyMuPDF fallback 对 PUA 映射无效（两个库都无法处理）
- 缺少 OCR fallback（PaddleOCR 是唯一可靠方案）

### 4.4 推荐改进：OCR Fallback 管线

```
PDF 输入
    │
    ▼
[1] PyMuPDF 提取文本
    │
    ▼
[2] 乱码检测
    │
    ├── 无乱码 → 使用提取结果
    │
    └── 有乱码
        │
        ▼
        [3] 尝试 pdfminer.six
        │
        ├── 成功 → 使用提取结果
        │
        └── 仍乱码
            │
            ▼
            [4] PaddleOCR fallback
            │
            ├── 成功 → 使用 OCR 结果
            │
            └── 失败 → 标记 failed
```

### 4.5 OCR 方案对比

| 工具 | 中文精度 | CPU 速度 | 安装 | 推荐场景 |
|------|---------|---------|------|---------|
| PaddleOCR | 最优 (99%+) | 中 | pip | **中文 PDF 首选** |
| Surya | 良好 | 慢 | pip | 多语言统一 |
| Tesseract | 一般 | 快 | 系统包 | 老牌稳定 |
| EasyOCR | 良好 | 慢 | pip | 快速原型 |

### 4.6 水印去除

```python
def remove_cnki_watermark(input_pdf, output_pdf):
    """文字搜索遮盖法"""
    import fitz
    doc = fitz.open(input_pdf)
    watermark_texts = ["知网", "CNKI", "学位论文", "数字出版",
                       "中国学术期刊", "请用CNKI原文下载", "仅用于个人学习"]

    for page in doc:
        for text in watermark_texts:
            areas = page.search_for(text)
            for area in areas:
                page.add_redact_annot(area, fill=(1, 1, 1))
        page.apply_redactions()

    doc.save(output_pdf)
    doc.close()
```

### 4.7 PUA 字符检测增强

```python
def detect_pua_chars(text):
    """检测 Unicode 私用区字符（知网特征）"""
    pua_count = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)
    return pua_count > len(text) * 0.1
```

---

## 5. 边缘问题与解决方案

### 5.1 跨页表格

**问题**：表格跨两页时，解析器将其识别为两个独立表格。

**检测启发式**：
- 比较第 N 页最后一个表格与第 N+1 页第一个表格
- 匹配条件：列数相同、列 x 坐标对齐（容差 ±3pt）、表格 bbox 紧邻页底/页顶
- 如果第 N+1 页首行与第 N 页表头重复 → 跳过重复表头

**工具支持**：

| 工具 | 跨页合并 |
|------|---------|
| MinerU | 上下文感知缝合算法，99.2% 准确率 |
| tabula-py | `multiple_tables=False` 尝试合并 |
| pdfplumber | 逐页提取，需自定义合并 |
| PyMuPDF | `page.find_tables()` 逐页，需手动合并 |

### 5.2 脚注混入正文

**检测方法**：
1. 字体大小启发式：脚注通常比正文小 1-2pt
2. 上标标记检测：脚注常以上标数字开头
3. 位置聚类：y 坐标在页面底部 15-20% 区域

```python
# PyMuPDF 实现
for page in doc:
    blocks = page.get_text("dict")["blocks"]
    page_height = page.rect.height
    for b in blocks:
        if b["bbox"][1] > page_height * 0.80:
            # 底部 20% → 可能是脚注
            footnote_text = extract_text(b)
```

### 5.3 公式与文本混排

数学公式在 PDF 中的三种渲染方式：
- 实际文本 + 特殊字体（少见）
- 嵌入图片（LaTeX 生成的 PDF 常见）
- 不可读的 glyph 流

**推荐管线**：
```
1. PyMuPDF / Marker 检测文本块 vs 公式区域
2. 文本块 → 直接提取
3. 公式区域 → 渲染为图像 → Nougat/Pix2Text 识别 LaTeX
4. 行内公式 → 检测文本流中的小图片或 glyph 异常
```

**公式识别工具**：

| 工具 | Stars | 技术 | 输出 | 推荐场景 |
|------|-------|------|------|---------|
| LaTeX-OCR (pix2tex) | 16K | ViT | LaTeX | 通用公式识别 |
| Pix2Text | 3K | 多模型 | LaTeX/MD | Mathpix 开源替代 |
| Texify | 1K | Transformer | LaTeX | 与 Marker 集成 |
| UniMERNet | 479 | 通用网络 | LaTeX | 学术论文公式 |

### 5.4 页眉页脚去除

**检测策略**：
1. **重复检测**：同一 y 位置在 3+ 页出现的文本 → 几乎确定是页眉/页脚
2. **位置区域**：顶部 10-15% 为页眉区，底部 10-15% 为页脚区
3. **页码模式**：正则 `^\d+$`、`^\- \d+ \-$`、`^Page \d+`

```python
from collections import Counter

header_candidates = Counter()
footer_candidates = Counter()

with pdfplumber.open("paper.pdf") as pdf:
    for page in pdf.pages:
        h = page.height
        for char in page.chars:
            if char["top"] < h * 0.12:
                header_candidates[char["text"]] += 1
            elif char["top"] > h * 0.88:
                footer_candidates[char["text"]] += 1

num_pages = len(pdf.pages)
headers_to_remove = {k for k, v in header_candidates.items() if v > num_pages * 0.8}
```

### 5.5 连字符断行 (Hyphenation)

```python
import re

def fix_hyphenation(text):
    """合并断行连字符"""
    return re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
```

**注意**：有些连字符是真正的复合词（如 "well-known"），可用 `pyphen` 库辅助判断。

### 5.6 合字 (Ligatures)

```python
LIGATURE_MAP = {
    'ﬀ': 'ff',  # U+FB00
    'ﬁ': 'fi',  # U+FB01
    'ﬂ': 'fl',  # U+FB02
    'ﬃ': 'ffi', # U+FB03
    'ﬄ': 'ffl', # U+FB04
}

def fix_ligatures(text):
    for lig, replacement in LIGATURE_MAP.items():
        text = text.replace(lig, replacement)
    return text
```

**注意**：PyMuPDF 通常自动处理合字，pdfplumber 可能需要显式修复。

### 5.7 上标/下标（引用标记）

```python
import re

def fix_citation_markers(text):
    # 重连分离的引用标记
    text = re.sub(r'(\w)\s+\[(\d+(?:,\s*\d+)*)\]', r'\1[\2]', text)
    return text
```

### 5.8 加密/DRM PDF

| 工具 | 方法 |
|------|------|
| pikepdf | `pikepdf.Pdf.open("file.pdf", password="")` 解除限制 |
| pypdf | `reader.decrypt(password)` |
| qpdf CLI | `qpdf --decrypt input.pdf output.pdf` |
| Ghostscript | `gs -o output.pdf -sDEVICE=pdfwrite input.pdf` |

**两种密码类型**：
- User password：打开 PDF 必需，强加密，无法绕过
- Owner password：限制复制/打印/编辑，通常可移除

### 5.9 大 PDF 内存优化

| 库 | 内存行为 |
|-----|---------|
| PyMuPDF | 最佳，mmap 按需加载 |
| pikepdf | 好，懒加载页面 |
| pypdf | 中等，结构加载但页面懒加载 |
| pdfplumber | 较高，构建完整页面对象 |
| pdfminer.six | 较高，全文档布局分析 |

**生成器实现**：
```python
import fitz

def extract_pages_streaming(pdf_path):
    doc = fitz.open(pdf_path)
    for page in doc:
        yield page.get_text()
    doc.close()
```

---

## 6. 技术方案深度对比

### 6.1 端到端方案对比

| 方案 | Stars | 表格 | 公式 | 参考文献 | 中文 | 扫描件 | CPU | 推荐场景 |
|------|-------|------|------|---------|------|--------|-----|---------|
| **GROBID** | 4.9K | 2/5 | 1/5 | **5/5** | 2/5 | 2/5 | 快 | 元数据+参考文献 |
| **MinerU** | 65K | **5/5** | **5/5** | 3/5 | **5/5** | 4/5 | 慢 | 学术论文全解析 |
| **Docling** | 60K | **5/5** | 3/5 | 3/5 | 4/5 | 4/5 | 慢 | 企业级多格式 |
| **Marker** | 35K | 3/5 | 4/5 | 3/5 | 3/5 | 4/5 | 慢 | 快速 Markdown |
| **Nougat** | 9.9K | 3/5 | **5/5** | 2/5 | 2/5 | 4/5 | 极慢 | 学术研究参考 |
| **PaddleOCR** | 78K | — | — | — | **5/5** | **5/5** | 中 | OCR 引擎 |
| **Surya** | 19K | 3/5 | — | — | 4/5 | 4/5 | 慢 | 多语言统一 |

### 6.2 Python 库对比

| 库 | 底层引擎 | 速度 | 表格 | 内存 | 推荐场景 |
|-----|---------|------|------|------|---------|
| PyMuPDF | MuPDF (C++) | 最快 | 一般 | 最低 | 文本提取首选 |
| pdfplumber | pdfminer.six | 中 | 优秀 | 中 | 表格提取 |
| PDFMiner.six | 纯 Python | 慢 | 需额外 | 高 | 底层分析 |
| camelot | 规则+启发式 | 中 | 良好 | 中 | 有线表格 |
| tabula-py | Java Tabula | 中 | 良好 | 中 | 简单表格 |

### 6.3 功能维度评分矩阵

| 功能 | GROBID | MinerU | Docling | Marker | 当前实现 |
|------|--------|--------|---------|--------|---------|
| 标题提取 | 5 | 4 | 4 | 3 | 2 |
| 作者提取 | 5 | 3 | 3 | 2 | 1 |
| 摘要提取 | 5 | 4 | 4 | 3 | 3 |
| 正文分节 | 5 | 4 | 4 | 3 | 3 |
| 参考文献 | 5 | 3 | 3 | 2 | 2 |
| 公式识别 | 1 | 5 | 3 | 4 | 0 |
| 表格解析 | 2 | 5 | 5 | 3 | 1 |
| 多栏布局 | 4 | 5 | 5 | 4 | 2 |
| 中文支持 | 2 | 5 | 4 | 3 | 2 |
| 扫描件 | 2 | 4 | 4 | 4 | 0 |

---

## 7. 分块策略优化

### 7.1 策略对比

| 策略 | 检索准确率(MRR) | 相对提升 | 计算成本 |
|-----|----------------|---------|---------|
| 固定 Token（256） | 基准 | — | 低 |
| 固定 Token（512） | +3% | 低 |
| Section-Based | +8% | 低 |
| 语义分块 | +12% | 中 |
| Late Chunking | +15% | 高 |
| Contextual Retrieval | +35-50% | 中 |

**数据来源**：Anthropic Contextual Retrieval (2024)、LlamaIndex 基准测试

### 7.2 当前实现评估

当前使用 Section-Based + 80 token overlap：
- 优点：尊重文档结构，简单高效
- 缺点：overlap 固定、无上下文元数据、无语义边界检测

### 7.3 优化方向

#### 7.3.1 Contextual Retrieval

Anthropic 提出的方法：为每个 chunk 添加上下文摘要，检索准确率提升 35-50%。

```python
def add_context(chunk_text, full_text):
    """为 chunk 添加上下文摘要"""
    prompt = f"""Here is the full document: {full_text[:2000]}
Here is the chunk: {chunk_text}
Give a short context for this chunk (1-2 sentences):"""
    context = llm.generate(prompt)
    return f"{context}\n\n{chunk_text}"
```

#### 7.3.2 Late Chunking

Jina AI 提出：先 embedding 全文档，再分块，保留跨块上下文。

```python
def late_chunk(text, tokenizer, model, chunk_size=512):
    """先编码全文档，再按 token 边界分块"""
    tokens = tokenizer.encode(text)
    embeddings = model.encode(tokens)  # 全文档编码

    chunks = []
    for i in range(0, len(tokens), chunk_size):
        chunk_tokens = tokens[i:i+chunk_size]
        chunk_embedding = embeddings[i:i+chunk_size].mean(dim=0)
        chunks.append((chunk_tokens, chunk_embedding))

    return chunks
```

#### 7.3.3 层次化分块

```python
def hierarchical_chunk(parsed_paper):
    """层次化分块：Section → Paragraph → Sentence"""
    chunks = []
    for section in parsed_paper.sections:
        section_chunks = []
        for paragraph in section.paragraphs:
            if len_tokens(paragraph) > MAX_CHUNK:
                sub_chunks = split_by_sentences(paragraph)
                section_chunks.extend(sub_chunks)
            else:
                section_chunks.append(paragraph)

        for chunk in section_chunks:
            chunks.append({
                "text": chunk,
                "metadata": {
                    "section": section.name,
                    "heading_path": section.heading_path,
                    "page_range": chunk.page_range,
                }
            })
    return chunks
```

---

## 8. 工程化优化方案

### 8.1 多解析器 Fallback 链路增强

**当前**：PdfPlumber → PyMuPDF → scanned_pdf_suspected

**优化**：PdfPlumber → PyMuPDF → pdfminer.six → PaddleOCR → 标记失败

```python
class ParserService:
    def __init__(self):
        self._adapters: list[ParserAdapter] = [
            PdfPlumberAdapter(),
            PyMuPDFAdapter(),
            PdfMinerAdapter(),      # 新增：pdfminer.six
            PaddleOCRAdapter(),     # 新增：OCR fallback
        ]
```

### 8.2 文本后处理管线

在文本提取后、分块前，添加统一的后处理管线：

```python
def post_process_text(text: str) -> str:
    """统一文本后处理管线"""
    text = fix_ligatures(text)          # 合字修复
    text = fix_hyphenation(text)        # 连字符断行
    text = fix_citation_markers(text)   # 引用标记重连
    text = remove_headers_footers(text) # 页眉页脚去除
    return text
```

### 8.3 质量评估指标

| 指标 | 定义 | 目标阈值 |
|-----|------|---------|
| 文本提取率 | 提取字符数 / 预期字符数 | > 80% |
| 乱码率 | 乱码字符数 / 总字符数 | < 5% |
| 表格识别准确率 | 正确表格 / 总表格数 | > 90% |
| 公式识别准确率 | 正确公式 / 总公式数 | > 85% |
| 处理成功率 | 成功 / 总数 | > 95% |
| 单篇处理时间 | — | < 30s (CPU) |

### 8.4 性能基准

| 工具 | 单页时间 | 100 页时间 | 内存 |
|-----|---------|-----------|------|
| PyMuPDF | ~0.1s | ~10s | 低 |
| pdfplumber | ~0.3s | ~30s | 中 |
| MinerU (CPU) | ~2s | ~200s | 高 |
| MinerU (GPU) | ~0.5s | ~50s | 高 |
| Marker (CPU) | ~1.5s | ~150s | 中 |
| GROBID | ~0.5s | ~50s | 中 |

### 8.5 批量处理优化

```python
from concurrent.futures import ThreadPoolExecutor

class BatchPDFProcessor:
    def __init__(self, parser, max_workers=4):
        self.parser = parser
        self.max_workers = max_workers

    def process_batch(self, pdf_paths):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.parser.parse, pdf) for pdf in pdf_paths]
            results = [f.result() for f in futures]
        return results
```

---

## 9. 推荐技术路线与实施计划

### 9.1 分阶段实施

#### P0（当前）— 规则引擎基础

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 双栏文本重排 | **P0** | PyMuPDF blocks + 空白谷检测，解决文本交叉 |
| 文本后处理管线 | **P0** | 合字/连字符/引用标记/页眉页脚 |
| 参考文献提取增强 | P1 | 更准确的作者/标题/年份提取 |

#### P1 — OCR Fallback

| 任务 | 优先级 | 说明 |
|------|--------|------|
| PaddleOCR 集成 | **P1** | 中文 PDF 乱码的唯一可靠方案 |
| 扫描件 OCR | P1 | 扫描件不再是死路 |
| pdfminer.six 适配器 | P1 | 第三解析器 fallback |

#### P2 — ML 增强

| 任务 | 优先级 | 说明 |
|------|--------|------|
| GROBID Docker 适配器 | P2 | 元数据+参考文献金标准 |
| Marker 适配器 | P2 | 高精度 Markdown 输出 |
| 公式识别 (pix2tex) | P2 | LaTeX 公式提取 |
| 表格结构化提取 | P2 | 有线表/无线表识别 |

#### P3 — 生产级方案

| 任务 | 优先级 | 说明 |
|------|--------|------|
| MinerU 适配器 | P3 | 中文最佳一站式解析 |
| Docling 适配器 | P3 | 企业级多格式支持 |
| VLM 端到端 | P3 | Dolphin/GPT-4o 深度解析 |
| Contextual Retrieval | P3 | chunk 上下文增强 |

### 9.2 技术选型决策树

```
PDF 输入
    │
    ├── 原生文本 PDF（非中文）
    │   └── PyMuPDF 提取 → 后处理 → 分块
    │
    ├── 中文 PDF（知网/万方）
    │   └── PyMuPDF → 乱码检测 → PaddleOCR fallback
    │
    ├── 双栏 PDF
    │   └── PyMuPDF blocks → 空白谷检测 → 分栏重排
    │
    ├── 扫描件 PDF
    │   └── PaddleOCR → 后处理 → 分块
    │
    ├── 复杂表格/公式密集
    │   └── MinerU/Docling → 结构化输出
    │
    └── 需要高精度元数据
        └── GROBID → 元数据+参考文献
```

### 9.3 架构目标

```
PDF 输入
    │
    ▼
┌─────────────────────────────────────────────┐
│  LayoutDetector（布局检测）                   │
│  - 单栏/双栏/三栏检测                         │
│  - 阅读顺序确定                               │
│  - 全宽元素识别                               │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  ParserAdapter Chain（解析器链）              │
│  1. PdfPlumberAdapter                        │
│  2. PyMuPDFAdapter                           │
│  3. PdfMinerAdapter                          │
│  4. PaddleOCRAdapter（乱码/扫描件时触发）     │
│  5. [future] GROBIDAdapter                   │
│  6. [future] MinerUAdapter                   │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  PostProcessor（后处理管线）                  │
│  - 合字修复                                   │
│  - 连字符断行修复                             │
│  - 引用标记重连                               │
│  - 页眉页脚去除                               │
│  - 脚注分离                                   │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  QualityChecker（质量检查）                   │
│  - 乱码检测                                   │
│  - 水印检测                                   │
│  - 扫描件检测                                 │
│  - 文本覆盖率                                 │
│  - 章节覆盖率                                 │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Chunker（分块器）                            │
│  - Section-Based 分块                        │
│  - 500-900 tokens/块                         │
│  - 80 token overlap                          │
│  - 层次化元数据                               │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  ReferenceExtractor（参考文献提取）           │
│  - 编号分割                                   │
│  - DOI/年份/标题/作者提取                     │
│  - 结构化存储                                 │
└─────────────────────────────────────────────┘
    │
    ▼
输出：paper_chunks + references + parse_results
```

---

## 10. 问题-方案速查表

| 问题 | 方案 | 工具 | 优先级 |
|------|------|------|--------|
| 双栏文本交叉 | PyMuPDF blocks + 空白谷检测 | PyMuPDF | P0 |
| 中文 PDF 乱码 | OCR fallback | PaddleOCR | P1 |
| 知网 PUA 映射 | OCR 完全绕过 | PaddleOCR | P1 |
| 扫描件无文本 | OCR | PaddleOCR | P1 |
| 跨页表格 | 表头重复检测 + 列坐标对齐 | MinerU | P2 |
| 脚注混入正文 | 字体大小 + y 坐标位置过滤 | PyMuPDF | P1 |
| 公式与文本混排 | 布局检测 + LaTeX 识别 | pix2tex, Marker | P2 |
| 页眉页脚 | 重复检测 + 位置区域 | 后处理 | P0 |
| 连字符断行 | 正则 `(\w)-\n(\w)` 合并 | 后处理 | P0 |
| 合字 | Unicode 替换 `ﬁ→fi` | 后处理 | P0 |
| 上标引用 | 字体大小比 + 正则重连 | 后处理 | P0 |
| 加密/DRM | pikepdf/qpdf 解除限制 | pikepdf | P1 |
| 大 PDF 内存 | 逐页流式 + mmap | PyMuPDF | P1 |
| 参考文献结构化 | GROBID / 正则+LLM | GROBID | P2 |
| 表格结构化 | TableFormer / MinerU | Docling/MinerU | P2 |

---

## 参考资料

### 核心开源项目

1. MinerU: https://github.com/opendatalab/MinerU (65K stars)
2. Docling: https://github.com/docling-project/docling (60K stars)
3. PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR (78K stars)
4. Marker: https://github.com/VikParuchuri/marker (35K stars)
5. GROBID: https://github.com/kermitt2/grobid (4.9K stars)
6. Nougat: https://github.com/facebookresearch/nougat (9.9K stars)
7. Surya: https://github.com/VikParuchuri/surya (19K stars)
8. PyMuPDF: https://pymupdf.readthedocs.io/
9. pdfplumber: https://github.com/jsvine/pdfplumber
10. pikepdf: https://github.com/pikepdf/pikepdf
11. LaTeX-OCR: https://github.com/lukas-blecher/LaTeX-OCR (16K stars)
12. Dolphin: https://github.com/bytedance/Dolphin (9K stars)
13. PDF-Extract-Kit: https://github.com/opendatalab/PDF-Extract-Kit (9.6K stars)

### 学术论文

1. Nagy and Seth (1984), "Hierarchical Representation of Optically Scanned Documents"
2. Nougat: Neural Optical Understanding for Academic Documents (NeurIPS 2023)
3. ColPali: Efficient Document Retrieval with Vision Language Models (ICLR 2025)
4. DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation (KDD 2022)
5. TableFormer: Robust Transformer Modeling for Table-Structure Recognition (ICDAR 2022)
6. Dolphin: Document Image Parsing via Heterogeneous Anchor Prompting (ACL 2025)
7. TEXOCR: Advancing Document OCR Models for Compilable Page-to-LaTeX Reconstruction (2026)
8. Anthropic Contextual Retrieval (2024)
9. Jina AI Late Chunking (2024)

### 综合报告来源

1. PDF解析技术调研报告 (2026-05-11)
2. 端到端学术PDF解析方案深度调研报告 (2026-05-29)
3. 论文PDF解析核心技术路线调研报告 (2026-05-29)
4. 论文PDF解析最佳实践与工程方案调研报告 (2026-05-29)
5. 双栏PDF布局解析方案调研报告 (2026-05-30)
6. 中文PDF乱码问题与解决方案调研报告 (2026-05-30)
7. PDF解析边缘问题与解决方案调研报告 (2026-05-30)
