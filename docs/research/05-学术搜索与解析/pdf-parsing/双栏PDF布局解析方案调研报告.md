# 双栏 PDF 布局解析方案调研报告

**调研时间**：2026-05-30
**调研主题**：双栏学术 PDF 文本提取与阅读顺序重排

---

## 1. 问题本质

pdfplumber 和 PyMuPDF 的 `extract_text()` 按 PDF 内部内容流顺序返回文本。双栏 PDF 的内容流通常是左右栏交替写入，导致提取的文本左右交叉混杂，对下游 NLP 任务（章节检测、分块、QA）完全不可用。

---

## 2. pdfplumber / PyMuPDF 的局限

### pdfplumber

- `page.extract_text()` — 按字符流式顺序拼接，双栏文本交叉
- `page.extract_words()` — 返回带坐标的单词列表，可手动分栏
- `page.within_bbox((x0, y0, x1, y1))` — 可提取指定矩形区域，是分栏提取的关键
- **无内置分栏检测或阅读顺序校正**

### PyMuPDF (fitz)

- `page.get_text("text")` — 纯文本，无空间感知
- `page.get_text("blocks")` — 返回 `(x0, y0, x1, y1, text, block_no, block_type)` 带坐标的文本块，**最有用**
- `page.get_text("dict")` — 结构化数据，含 block/line/span 坐标
- `page.get_text("rawdict")` — 逐字符坐标，最高精度
- **无内置阅读顺序校正**

---

## 3. 业界标准检测算法

### 3.1 投影剖面法 (Projection Profile)

最经典的分栏检测算法（Nagy & Seth, 1984）：

1. 统计页面每一列的前景像素总和 → 垂直投影剖面
2. 峰值对应文本列，谷值（接近零）对应列间距
3. 中间 1/3 区域存在一个深谷 → 双栏；无谷 → 单栏；多个谷 → 多栏

### 3.2 空白谷检测法 (Whitespace Valley)

投影剖面的改进版：

1. 计算垂直投影剖面
2. 高斯平滑降噪
3. 找所有局部最小值（谷）
4. 按深度和宽度排序
5. 最深最宽的谷即为列分界线
6. 最小间隙阈值（如 300 DPI 下 20 像素）区分列边界与词间距

### 3.3 XY-Cut 递归切割算法

经典自顶向下页面分割（Nagy & Seth, 1984）：

1. 水平投影 → 找最宽空白带 → Y 切割
2. 对每个子区域做垂直投影 → X 切割
3. 递归交替，直到区域过小或无显著空白谷
4. 输出 XY 树，叶节点为文本块

**局限**：对倾斜文本、非曼哈顿布局、重叠区域敏感。

### 3.4 GROBID 的做法

GROBID 用 CRF 序列标注模型做页面分割，特征包括：

- 字体大小、字体名、粗体/斜体
- 页面绝对位置（归一化坐标）
- 行间距
- 字符级特征：大写比例、数字比例、标点密度
- 词汇特征：是否以数字开头、是否含 "Abstract"/"References"
- 滑动窗口上下文（前后 3-5 行）

检测到双栏后，按左栏从上到下、右栏从上到下的顺序重建阅读顺序。

---

## 4. 可行方案分档

| 方案 | 速度 | 精度 | 依赖 | 适合场景 |
|------|------|------|------|---------|
| PyMuPDF `get_text("blocks")` + 坐标聚类 | 快 | 中 | 无 | **当前阶段首选** |
| pdfplumber `within_bbox` 手动切栏 | 快 | 中 | 无 | 简单双栏 |
| GROBID (Docker) | 中 | 高 | Java/Docker | 学术论文金标准 |
| Marker (pip install) | 慢 | 高 | PyTorch CPU | 高精度 Markdown |
| Docling / MinerU | 慢 | 很高 | GPU 更佳 | 生产环境 |

### 不推荐 CPU 环境的方案

- **Nougat (Meta)**：ViT + mBART，CPU 推理极慢（每页数分钟），不实用
- **LayoutParser + Detectron2**：强烈推荐 GPU

---

## 5. 推荐实现方案：PyMuPDF Blocks + 空白谷检测

### 5.1 分栏检测

```python
def detect_column_structure(pdf_path, sample_pages=3):
    """基于文本块 x 坐标聚类的分栏检测"""
    import fitz
    doc = fitz.open(pdf_path)
    column_scores = []

    for i in range(min(sample_pages, len(doc))):
        page = doc[i]
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0 and len(b[4].strip()) > 10]

        if len(text_blocks) < 4:
            continue

        page_width = page.rect.width
        mid = page_width / 2

        left_count = sum(1 for b in text_blocks if b[2] < mid - 20)
        right_count = sum(1 for b in text_blocks if b[0] > mid + 20)

        if left_count >= 2 and right_count >= 2:
            balance = min(left_count, right_count) / max(left_count, right_count)
            if balance > 0.3:
                column_scores.append(1)
            else:
                column_scores.append(0)
        else:
            column_scores.append(0)

    doc.close()
    if not column_scores:
        return False
    return sum(column_scores) / len(column_scores) > 0.5
```

### 5.2 分栏边界定位

```python
def find_column_boundary(text_blocks, page_width):
    """通过空白谷检测找列分界线"""
    import numpy as np

    if len(text_blocks) < 4:
        return None

    mid = page_width / 2
    left = sum(1 for b in text_blocks if b[2] < mid)
    right = sum(1 for b in text_blocks if b[0] > mid)

    if left < 2 or right < 2:
        return None

    # 找 x 坐标间隙
    x_coords = sorted([b[0] for b in text_blocks])
    gaps = []
    for i in range(len(x_coords) - 1):
        gap = x_coords[i+1] - x_coords[i]
        if gap > 20:
            gaps.append((gap, (x_coords[i] + x_coords[i+1]) / 2))

    if gaps:
        gaps.sort(reverse=True)
        for gap_size, gap_center in gaps:
            if abs(gap_center - mid) < page_width * 0.2:
                return gap_center

    return mid  # 回退到中点
```

### 5.3 分栏阅读顺序重排

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
        page_height = page.rect.height
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

---

## 6. 边界情况处理

| 情况 | 处理方式 |
|------|---------|
| 全宽元素（标题、摘要） | 检测宽度 > 页面 60% 的块，放在列内容之前 |
| 脚注 | 字体大小 + y 坐标（底部 15-20% 区域）过滤 |
| 公式 | 可能全宽或列宽，宽度检测处理大多数情况 |
| 列尾连字符 | 左栏行尾 `-` 与右栏行首合并 |
| 参考文献区 | 通常仍是双栏，但短行多，需单独处理 |

---

## 7. ML 方案对比（用于后续升级）

| 工具 | Stars | CPU 速度 | 分栏处理 | 集成难度 |
|------|-------|---------|---------|---------|
| Surya | 19K | 慢 | 原生（DETR + 阅读顺序模型） | 中 |
| Marker | 35K | 慢 | 原生（Surya 布局检测） | 低 |
| Docling | 60K | 慢 | 原生（DocLayNet + 阅读顺序模型） | 低 |
| GROBID | 4.9K | 中 | 原生（CRF 分割模型） | 中（Docker） |
| DocLayout-YOLO | 2.1K | 快 | 检测布局区域，需自行排序 | 中 |

---

## 参考文献

1. Nagy and Seth (1984), "Hierarchical Representation of Optically Scanned Documents"
2. O'Gorman (1993), "The Document Spectrum for Page Layout Analysis"
3. PyMuPDF Documentation: https://pymupdf.readthedocs.io/
4. pdfplumber: https://github.com/jsvine/pdfplumber
5. GROBID: https://github.com/kermitt2/grobid
6. Marker: https://github.com/VikParuchuri/marker
7. Surya: https://github.com/VikParuchuri/surya
8. Docling: https://github.com/docling-project/docling
