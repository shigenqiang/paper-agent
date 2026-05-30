# PDF 解析边缘问题与解决方案调研报告

**调研时间**：2026-05-30
**调研主题**：学术 PDF 解析中的常见边缘问题及解决方案

---

## 1. 跨页表格

### 问题

表格跨两页时，解析器将其识别为两个独立表格，数据断裂。

### 检测启发式

- 逐页提取表格
- 比较第 N 页最后一个表格与第 N+1 页第一个表格
- 匹配条件：列数相同、列 x 坐标对齐（容差 ±3pt）、表格 bbox 紧邻页底/页顶
- 如果第 N+1 页首行与第 N 页表头重复 → 跳过重复表头

### 合并算法

```
for 每对相邻页 (p1, p2):
    t1 = p1 最后一个表格
    t2 = p2 第一个表格
    if 列数相同 and x 坐标对齐(容差 3pt):
        if t2 首行匹配 t1 表头:
            跳过 t2 首行
        合并 = pd.concat([t1, t2])
```

### 工具支持

| 工具 | 跨页合并 |
|------|---------|
| Camelot | 仅逐页，需手动后处理 |
| tabula-py | `multiple_tables=False` 尝试合并 |
| pdfplumber | 逐页提取，需自定义合并 |
| PyMuPDF | `page.find_tables()` 逐页，需手动合并 |
| MinerU | 上下文感知缝合算法，99.2% 准确率 |

---

## 2. 脚注混入正文

### 问题

脚注位于页面底部，字体较小，但文本提取后与正文交织。

### 检测方法

1. **字体大小启发式**：脚注通常比正文小 1-2pt
2. **上标标记检测**：脚注常以上标数字开头
3. **位置聚类**：y 坐标在页面底部 15-20% 区域

### PyMuPDF 实现

```python
import fitz

doc = fitz.open("paper.pdf")
for page in doc:
    blocks = page.get_text("dict")["blocks"]
    page_height = page.rect.height
    for b in blocks:
        if b["bbox"][1] > page_height * 0.80:
            # 底部 20% → 可能是脚注
            footnote_text = extract_text(b)
```

### 工具对比

| 工具 | 脚注处理 |
|------|---------|
| GROBID | 最佳，40+ CRF 模型自动分离 |
| PyMuPDF | 需自定义位置过滤 |
| pdfplumber | `page.chars` 逐字符元数据可过滤 |

---

## 3. 公式与文本混排

### 问题

数学公式在 PDF 中的三种渲染方式：
- 实际文本 + 特殊字体（少见）
- 嵌入图片（LaTeX 生成的 PDF 常见）
- 不可读的 glyph 流

行内公式打断文本提取，产生乱码或空白。

### 解决方案

| 工具 | 公式处理 |
|------|---------|
| Nougat | ViT 端到端，输出 LaTeX，最佳但需 GPU |
| Marker | 布局检测 + Texify 公式识别 |
| Pix2Text | OCR + LaTeX 识别，Mathpix 开源替代 |
| LaTeX-OCR | ViT 专门公式识别 |
| Docling | 内置公式检测 |

### 推荐管线

```
1. PyMuPDF / Marker 检测文本块 vs 公式区域
2. 文本块 → 直接提取
3. 公式区域 → 渲染为图像 → Nougat/Pix2Text 识别 LaTeX
4. 行内公式 → 检测文本流中的小图片或 glyph 异常
```

---

## 4. 页眉页脚去除

### 问题

学术论文每页重复页眉（期刊名、标题缩写、作者名）和页脚（页码、版权），混入提取文本。

### 检测策略

1. **重复检测**：同一 y 位置在 3+ 页出现的文本 → 几乎确定是页眉/页脚
2. **位置区域**：顶部 10-15% 为页眉区，底部 10-15% 为页脚区
3. **页码模式**：正则 `^\d+$`、`^\- \d+ \-$`、`^Page \d+`

### 实现

```python
from collections import Counter
import pdfplumber

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

---

## 5. 连字符断行 (Hyphenation)

### 问题

行尾断词（如 "computa-\ntion"）被提取为两个带连字符的 token，破坏 NLP 处理。

### 解决方案

```python
import re

def fix_hyphenation(text):
    """合并断行连字符"""
    return re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
```

**注意**：有些连字符是真正的复合词（如 "well-known"），可用字典验证。`pyphen` 库可辅助判断。

---

## 6. 合字 (Ligatures)

### 问题

PDF 字体使用合字 glyph（fi, fl, ff, ffi, ffl），编码为单个 Unicode 码点（U+FB00-U+FB04），提取后不是预期的两个/三个字符。

### 解决方案

```python
LIGATURE_MAP = {
    'ﬀ': 'ff',  # U+FB00
    'ﬁ': 'fi',  # U+FB01
    'ﬂ': 'fl',  # U+FB02
    'ﬃ': 'ffi', # U+FB03
    'ﬄ': 'ffl', # U+FB04
    'ﬅ': 'st',  # U+FB05
    'ﬆ': 'st',  # U+FB06
}

def fix_ligatures(text):
    for lig, replacement in LIGATURE_MAP.items():
        text = text.replace(lig, replacement)
    return text
```

**注意**：PyMuPDF 通常自动处理合字，pdfplumber/pdfminer 可能需要显式修复。

---

## 7. 上标/下标（引用标记）

### 问题

`[1]`、`[2]` 等引用标记被提取为：与前一个词合并、或成为独立小文本块、或乱码。

### 检测方法

1. **字体大小比**：上标字体约为正文 60-70%
2. **基线偏移**：上标 y 坐标高于基线
3. **模式匹配**：检测孤立的数字紧邻单词

### 后处理修复

```python
import re

def fix_citation_markers(text):
    # 重连分离的引用标记
    # "word [1]" → "word[1]"
    text = re.sub(r'(\w)\s+\[(\d+(?:,\s*\d+)*)\]', r'\1[\2]', text)
    return text
```

---

## 8. 加密/DRM PDF

### 问题

部分学术 PDF 有复制/打印限制（非完全加密），阻止文本提取。

### 解决方案

| 工具 | 方法 |
|------|------|
| pikepdf | `pikepdf.Pdf.open("file.pdf", password="")` 解除限制 |
| pypdf | `reader.decrypt(password)` |
| qpdf CLI | `qpdf --decrypt input.pdf output.pdf` |
| Ghostscript | `gs -o output.pdf -sDEVICE=pdfwrite input.pdf` |

### 两种密码类型

| 类型 | 说明 |
|------|------|
| User password | 打开 PDF 必需，强加密，无法绕过 |
| Owner password | 限制复制/打印/编辑，通常可移除 |

---

## 9. 大 PDF 内存优化

### 问题

100+ 页 PDF 同时处理可能消耗数 GB 内存。

### 优化策略

1. **逐页流式处理**：不同时加载所有页
2. **内存映射 I/O**：PyMuPDF 默认使用 mmap
3. **生成器模式**：用 yield 代替 list 累积
4. **分批处理**：每次处理 N 页
5. **显式垃圾回收**：`gc.collect()`

### 库内存行为对比

| 库 | 内存行为 |
|-----|---------|
| PyMuPDF | 最佳，mmap 按需加载 |
| pikepdf | 好，懒加载页面 |
| pypdf | 中等，结构加载但页面懒加载 |
| pdfplumber | 较高，构建完整页面对象 |
| pdfminer.six | 较高，全文档布局分析 |

### 生成器实现

```python
import fitz

def extract_pages_streaming(pdf_path):
    doc = fitz.open(pdf_path)
    for page in doc:
        yield page.get_text()
    doc.close()

for text in extract_pages_streaming("large.pdf"):
    process(text)
```

---

## 10. 综合：问题-方案速查表

| 问题 | 方案 | 工具 |
|------|------|------|
| 跨页表格 | 表头重复检测 + 列坐标对齐合并 | tabula-py, MinerU |
| 脚注混入正文 | 字体大小 + y 坐标位置过滤 | GROBID, PyMuPDF |
| 公式与文本混排 | 布局检测 + LaTeX 识别 | Nougat, Marker, Pix2Text |
| 页眉页脚 | 重复检测 + 位置区域 | GROBID, pdfplumber |
| 连字符断行 | 正则 `(\w)-\n(\w)` 合并 | 自定义后处理 |
| 合字 | Unicode 替换 `ﬁ→fi` | PyMuPDF 内置，pdfplumber 需手动 |
| 上标引用 | 字体大小比 + 正则重连 | GROBID, 自定义后处理 |
| 加密/DRM | pikepdf/qpdf 解除限制 | pikepdf, qpdf |
| 大 PDF 内存 | 逐页流式 + mmap | PyMuPDF |
| 中文乱码 | OCR fallback | PaddleOCR |
| 双栏混排 | 坐标聚类 + 分栏重排 | PyMuPDF blocks |

---

## 参考资料

1. Anthropic Contextual Retrieval (2024)
2. Jina AI Late Chunking (2024)
3. PyMuPDF: https://pymupdf.readthedocs.io/
4. GROBID: https://github.com/kermitt2/grobid
5. MinerU: https://github.com/opendatalab/MinerU
6. Marker: https://github.com/VikParuchuri/marker
7. pikepdf: https://github.com/pikepdf/pikepdf
