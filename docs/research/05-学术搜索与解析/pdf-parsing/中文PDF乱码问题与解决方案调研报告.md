# 中文 PDF 乱码问题与解决方案调研报告

**调研时间**：2026-05-30
**调研主题**：知网/万方 PDF CID 字体编码乱码的根本原因与解决方案

---

## 1. 根本原因：CID 字体编码机制

知网/万方 PDF 使用 CID-keyed 字体，字符编码链路为：

```
PDF 内容流字节序列
    → CID (Character ID)         ← Encoding CMap (如 GBK-EUC-H)
    → Glyph Index                ← CIDMap
    → Unicode 码点               ← ToUnicode CMap  ← 这一环在知网 PDF 中损坏/缺失
```

知网 PDF 的三种常见问题：

| 问题 | 表现 |
|------|------|
| ToUnicode CMap 完全缺失 | 提取结果为空或乱码 |
| ToUnicode CMap 被故意映射到 PUA 区 | 提取结果为 `U+E000-U+F8FF` 私用区字符 |
| ToUnicode CMap 不完整 | 部分字符正确，部分乱码 |

**关键事实**：知网故意将字符映射到 Unicode PUA（Private Use Area），这是版权保护手段，不是 bug。

---

## 2. 乱码检测策略

### 2.1 检测方法

```python
def detect_garbled_text(text):
    """检测中文 PDF 乱码"""
    # 1. 控制字符
    control_chars = sum(1 for c in text if ord(c) < 0x20 and c not in '\n\r\t')
    if control_chars > len(text) * 0.05:
        return True

    # 2. 替换字符
    replacement_chars = sum(1 for c in text if c in '□■◆◇○●')
    if replacement_chars > len(text) * 0.02:
        return True

    # 3. CJK 扩展区罕见字符（连续 3+ 个）
    import re
    if re.search(r'[\U00020000-\U0002A6DF]{3,}', text):
        return True

    # 4. 高比例非 CJK 非 ASCII 字符
    total = len(text)
    abnormal = 0
    for c in text:
        cp = ord(c)
        if cp < 0x80:
            continue
        if 0x4E00 <= cp <= 0x9FFF:  # CJK 基本区
            continue
        if 0x3400 <= cp <= 0x4DBF:  # CJK 扩展 A
            continue
        if 0xFF00 <= cp <= 0xFFEF:  # 全角字符
            continue
        if 0x3000 <= cp <= 0x303F:  # CJK 符号标点
            continue
        if c in '\n\r\t ':
            continue
        abnormal += 1
    if total > 100 and abnormal / total > 0.3:
        return True

    return False
```

### 2.2 PUA 字符检测

```python
def detect_pua_chars(text):
    """检测 Unicode 私用区字符（知网特征）"""
    pua_count = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)
    return pua_count > len(text) * 0.1
```

---

## 3. 解决方案

### 方案 A：多库尝试（快速尝试）

不同库对 CID 字体的处理能力不同：

```python
# 1. PyMuPDF — 通常对 CID 字体支持最好
import fitz
doc = fitz.open("paper.pdf")
text = "\n".join(page.get_text() for page in doc)

# 2. pdfminer.six — 内置 CMap 数据库（Adobe-GB1 等）
from pdfminer.high_level import extract_text
text = extract_text("paper.pdf", codec='utf-8')

# 3. pypdf — 近版改进了 CID 字体处理
from pypdf import PdfReader
reader = PdfReader("paper.pdf")
text = "\n".join(page.extract_text() for page in reader.pages)
```

**成功率**：对 ToUnicode 缺失（非故意篡改）的 PDF 有效，对知网 PUA 映射无效。

### 方案 B：ToUnicode CMap 诊断与修复

```python
import pikepdf

def diagnose_cmap(pdf_path):
    """诊断 CID 字体编码问题"""
    pdf = pikepdf.open(pdf_path)
    for page_num, page in enumerate(pdf.pages):
        resources = page.get("/Resources", {})
        font_dict = resources.get("/Font", {})
        if font_dict is None:
            continue
        for font_name, font_ref in font_dict.items():
            font = font_ref
            font_type = font.get("/Subtype")
            encoding = font.get("/Encoding")
            has_tounicode = "/ToUnicode" in font
            print(f"Page {page_num}, {font_name}: type={font_type}, "
                  f"encoding={encoding}, ToUnicode={has_tounicode}")
```

**修复成功率**：对真正缺失 CMap 的 PDF 有效，对知网故意 PUA 映射无效。

### 方案 C：OCR 方案（最可靠）

OCR 完全绕过字体编码问题，因为它操作的是页面渲染后的图像：

```
PDF 页面 → 光栅化为图像 → 文本区域检测 → 字符视觉识别
```

#### PaddleOCR（中文最优）

```python
from paddleocr import PaddleOCR
from pdf2image import convert_from_path

ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False)
images = convert_from_path("paper.pdf", dpi=300)

all_text = []
for img in images:
    img.save("/tmp/temp_page.png")
    result = ocr.ocr("/tmp/temp_page.png", cls=True)
    page_text = "\n".join(line[1][0] for line in result[0])
    all_text.append(page_text)

full_text = "\n\n".join(all_text)
```

**优势**：中文识别准确率 99%+，PP-StructureV2 支持复杂学术版面。

#### PyMuPDF 内置 OCR

```python
import fitz
doc = fitz.open("paper.pdf")
for page in doc:
    tp = page.get_textpage_ocr(language="chi_sim", dpi=300)
    text = page.get_text(textpage=tp)
```

#### Tesseract OCR

```python
from pdf2image import convert_from_path
import pytesseract

images = convert_from_path("paper.pdf", dpi=300)
for img in images:
    text = pytesseract.image_to_string(img, lang='chi_sim+eng')
```

### 方案 D：Ghostscript 字体重嵌入

```bash
gs -o fixed.pdf -sDEVICE=pdfwrite -dEmbedAllFonts=true broken.pdf
```

修复 ToUnicode 映射表，对部分 PDF 有效。

---

## 4. OCR 方案对比

| 工具 | 中文精度 | CPU 速度 | 安装 | 特点 |
|------|---------|---------|------|------|
| PaddleOCR | 最优 | 中 | pip | 中文优化最好，PP-Structure 支持版面 |
| Surya | 良好 | 慢 | pip | 90+ 语言统一模型 |
| Tesseract | 一般 | 快 | 系统包 | 老牌稳定 |
| PyMuPDF OCR | 一般 | 快 | 需 Tesseract | 内置集成 |

---

## 5. 水印去除

知网 PDF 常见水印形式：低透明度文字叠加、矢量图形、半透明背景。

### 文字搜索遮盖法

```python
import fitz

def remove_cnki_watermark(input_pdf, output_pdf):
    doc = fitz.open(input_pdf)
    watermark_texts = ["知网", "CNKI", "学位论文", "数字出版", "中国学术期刊",
                       "请用CNKI原文下载", "仅用于个人学习", "中国知网"]

    for page in doc:
        for text in watermark_texts:
            areas = page.search_for(text)
            for area in areas:
                page.add_redact_annot(area, fill=(1, 1, 1))
        page.apply_redactions()

    doc.save(output_pdf)
    doc.close()
```

### 低透明度检测法

```python
import fitz

def remove_low_opacity_watermark(input_pdf, output_pdf):
    doc = fitz.open(input_pdf)
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span.get("opacity", 1.0) < 0.3:
                            rect = fitz.Rect(span["bbox"])
                            page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions()
    doc.save(output_pdf)
```

---

## 6. 推荐策略

```
PDF 输入
    │
    ▼
[1] PyMuPDF 提取文本
    │
    ▼
[2] 乱码检测 (_detect_garbled_text)
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
            └── 失败 → 标记 failed，quality_flags 含 garbled_text_detected
```

---

## 7. 关键结论

1. **非 OCR 方案对知网 PDF 成功率很低**：知网故意将字符映射到 PUA 区，不是简单的 CMap 缺失
2. **OCR 是唯一可靠的方案**：PaddleOCR 中文识别准确率 99%+，完全绕过编码问题
3. **MinerU 的混合策略是最佳实践**：先尝试文本提取，检测到乱码后自动切 OCR
4. **水印不影响 OCR**：渲染为图像后，低透明度水印对 OCR 引擎影响很小

---

## 参考资料

1. PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR (78K stars)
2. Surya: https://github.com/VikParuchuri/surya (19K stars)
3. pikepdf: https://github.com/pikepdf/pikepdf
4. pdfminer.six: https://github.com/pdfminer/pdfminer.six
5. MinerU: https://github.com/opendatalab/MinerU (65K stars)
