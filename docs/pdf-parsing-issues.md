# PDF 解析已知问题清单

更新时间：2026-05-30

本文档记录 PDF 解析模块的已知问题、影响范围和待解决方案。
基于 `paper_186aaf9d`（48 页英文论文，含大量公式和图表）的实际解析结果分析。

---

## 1. 公式处理（P1）

### 1.1 问题描述

PDF 中的数学公式被提取为纯文本符号混杂在正文中，无法区分公式和普通文字。

**实际表现：**

```
# chunk 4 (method, p5-6) - 公式和正文混在一起
where ϵijk are random noises so that the longitudinal outcome Yijk is a proxy ob...
βj (Φi ξ + Ψi ζij ), and xij = (x⊤ i1, · · · , x⊤ iJ )⊤
```

```
# chunk 6 (method, p8-9) - 上下标丢失，变成平文本
be shown that for J ≥ 2, βj and C0(·, ·) can be uniquely determined by (2) using...
```

### 1.2 影响

- 公式被当作正文分块，浪费 token（~20% 的 method chunk 是公式噪声）
- 上下标丢失：`Y_ijk` 变成 `Yijk`，`x^⊤` 变成 `x⊤`
- 分数、积分、矩阵等复杂结构完全丢失语义
- LLM 处理这些"乱码公式"会产生错误理解

### 1.3 公式类型统计

| 公式类型 | 出现频率 | 示例 |
|----------|----------|------|
| 希腊字母 | 20 个 chunk 涉及 | α β γ δ ε ζ η θ ξ π σ φ ψ |
| 上下标 | 普遍 | Yijk, βj, Θ⊤, IL0×L0 |
| 矩阵/向量转置 | 高频 | x⊤, Θ⊤ 0 Θ0 |
| 分布记号 | 中频 | ∼ N(0, D) |
| 求和/积分 | 低频 | Σ, ∫ |
| 特殊符号 | 中频 | ∈, ⊂, ⊥, ∀, ∃ |

### 1.4 解决方案

**短期（P1）：** 公式检测 + 标记

```python
def _detect_formula_regions(text: str) -> list[tuple[int, int]]:
    """检测公式区域，返回 (start, end) 位置列表

    策略：
    1. 连续数学符号（希腊字母、上下标、运算符）密度 > 30% 的行
    2. 独立成行的短文本 + 高数学符号密度 → 公式行
    3. 标记为 formula_block，分块时单独处理
    """
```

**中期（P2）：** 接入公式识别

- **LaTeX-OCR / pix2tex**：图片公式 → LaTeX
- **Nougat**：端到端 PDF → Markdown（保留公式结构）
- **Marker**：PDF → Markdown + 公式保留

**长期（P3）：** 公式语义理解

- LaTeX 解析为结构化表示
- 公式与正文关联（引用关系）
- 公式变量与上下文绑定

---

## 2. 图片处理（P1）

### 2.1 问题描述

PDF 中的图片（Figure 1-18）在文本提取时完全丢失，但正文中大量引用图片。

**实际表现：**

```
# chunk 2 (introduction, p2-3) - 引用了 Figure 1 但图片内容丢失
Subject A has a more acute cognitive decline compared to Subject B...
Figure 1: Five observed longitudinal biomarkers of two subjects.
```

**引用统计：** 27 个 chunk 中有 15 个引用了图片（Figure 1-18），但没有任何图片被提取。

### 2.2 影响

- 论文核心结论依赖图表（如 Figure 1 展示了两个受试者的纵向生物标志物趋势）
- LLM 无法理解"如图所示"、"见 Figure 1"等引用
- 表格数据完全丢失（Table 1-7）

### 2.3 解决方案

**短期（P1）：** 图片位置标记

```python
def _detect_figure_regions(pdf_path: str) -> list[dict]:
    """检测图片/表格区域

    返回: [{"page": 1, "type": "figure", "caption": "Figure 1: ...", "bbox": (...)}]
    """
    # 1. 提取图片 caption（正则匹配 "Figure N:" / "Table N:"）
    # 2. 检测页面中的图片区域（PyMuPDF get_images()）
    # 3. 关联 caption 和图片位置
```

**中期（P2）：** 图片提取 + OCR

- PyMuPDF `extract_image()` 提取图片
- 多模态 LLM（GPT-4V / Claude Vision）理解图片内容
- 表格结构还原（Camelot / pdfplumber tables）

**长期（P3）：** 图文关联

- 图片内容与正文描述对齐
- 表格数据结构化存储
- 图表自动生成文字描述

---

## 3. 表格处理（P1）

### 3.1 问题描述

论文中有 7 个表格（Table 1-7），包含模型比较、AIC/BIC 指标等关键数据。当前表格被当作普通文本提取，结构完全丢失。

**实际表现：**

```
# chunk 11 (method, p14-15) - 表格数据变成平文本
AIC 75754.60 75906.83 76116.50 79590.03 94657.54
BIC 76242.19 76394.42 76604.09 79951.03 95272.71
```

无法知道哪些数字属于哪个模型、哪个指标。

### 3.2 解决方案

**短期（P1）：** 表格检测 + 标记

```python
def _detect_table_regions(pages_text: list[tuple[int, str]]) -> list[dict]:
    """检测表格区域

    策略：
    1. 连续多行具有相似的列对齐模式
    2. 包含数字密集的行
    3. 前后有 "Table N:" caption
    """
```

**中期（P2）：** 表格结构还原

- **Camelot**：专门的 PDF 表格提取库
- **pdfplumber**：`page.extract_tables()` 方法
- 输出结构化 JSON：`{"headers": [...], "rows": [[...], ...]}`

---

## 4. 文本碎片化（P2）

### 4.1 问题描述

分块时在章节边界处产生过小的碎片 chunk。

**实际表现：**

```
chunk  9 [method] p13-12 |  90 tok | i γz + Ei (η⊤ i γη) o + Z Ti In particular...
chunk  0 [title ] p1-1   | 100 tok | Joint Model for Survival and Multivariate Sparse...
chunk 24 [discuss] p45-44 | 180 tok | Discussion). Statistical Science 11(2), 89–121...
```

### 4.2 影响

- 碎片 chunk 浪费 embedding 存储和检索配额
- 90 token 的 chunk 缺乏上下文，检索质量差
- chunk 24 把 discussion 尾部和 references 混在一起

### 4.3 解决方案

```python
def _merge_fragments(chunks: list[dict], min_tokens: int = 200) -> list[dict]:
    """合并过小的碎片 chunk

    规则：
    1. < min_tokens 的 chunk 与相邻 chunk 合并
    2. 合并后不超过 max_tokens (1200)
    3. 保持 section_type 一致（不同 section 的碎片不合并）
    """
```

---

## 5. 单词间距丢失（P2 - 部分解决）

### 5.1 问题描述

pdfplumber 提取某些 PDF 时丢失单词间的空格。

**实际表现：**

```
Alzheimer'sdisease(AD)isthemostprevalentneurodegenerativedisorder,canoftenbe
```

### 5.2 当前解决状态

已实现 **质量检测 + 自动 fallback**：
- `_detect_poor_spacing()` 检测到间距问题
- 自动 fallback 到 PyMuPDF（间距保留更好）

**残留问题：** PyMuPDF 的双栏重排偶尔也会丢失少量间距。

### 5.3 待改进

- TextPostProcessor 的 `fix_word_spacing()` 对无分隔符的粘连词无效
- 需要更智能的断词策略（词典匹配或语言模型辅助）

---

## 6. CID 伪影（已解决）

### 6.1 问题描述

pdfplumber 无法解析某些 CID 字体时输出 `(cid:48)` `(cid:62)` 等占位符。

**实际表现：**

```
x = β (Φ ξ + Ψ ζ ), and (cid:48) (cid:62)
```

### 6.2 解决状态

已在 `TextPostProcessor.fix_cid_artifacts()` 中清理：
- 正则 `\(\d+\)` 匹配并移除所有 `(cid:N)` 模式
- 解析后 CID 残留：0 个

---

## 7. 合字与断行（已解决）

### 7.1 问题描述

PDF 提取中的常见文本问题：
- 合字：`ﬁ` (fi ligature) → 应为 `fi`
- 连字符断行：`computa-\ntion` → 应为 `computation`
- 引用标记：`word [1]` → 应为 `word[1]`

### 7.2 解决状态

已在 `TextPostProcessor` 中全部处理：
- `fix_ligatures()` — 7 种合字修复
- `fix_hyphenation()` — 连字符断行修复
- `fix_citation_markers()` — 引用标记重连
- `remove_page_numbers()` — 页码移除
- `remove_headers_footers()` — 页眉页脚去除

---

## 8. 章节检测（已解决）

### 8.1 问题描述

最初只能检测少数章节类型，大量章节被跳过。

### 8.2 解决状态

已扩展到 30+ 种中英文章节模式，支持：
- 无编号标题：`Abstract`、`Introduction`
- 编号标题：`1 Introduction`、`2.1 Methods`
- 中文标题：`摘要`、`引言`、`方法`

当前检测结果：Abstract / Introduction / Model / Model Estimation / Model Selection / Data Analysis / Simulations / Simulation Settings / Simulation Results / Discussion / References

---

## 9. 参考文献提取（部分解决）

### 9.1 问题描述

最初只能识别 `[N]` 和 `N.` 编号格式的参考文献。

### 9.2 当前状态

已支持无编号格式 `Author (Year). Title. Journal.` 的分割和提取：
- 35 条参考文献被识别
- 年份、作者提取基本正确
- 标题提取仍有部分失败（`_guess_title` 对复杂格式的启发式不够完善）

### 9.3 待改进

- 标题提取成功率约 60%，需改进启发式规则
- DOI 提取率低（大部分参考文献无 DOI 或格式不标准）
- 考虑接入 CrossRef API 根据标题反查完整元数据

---

## 10. 扫描件 OCR（P2 - 未实现）

### 10.1 问题描述

扫描件 PDF（图片页面）无法提取文本。

### 10.2 当前状态

- `_detect_scanned_pdf()` 已实现扫描件检测（基于图片页比例）
- `_try_ocr_fallback()` 仅标记 `ocr_not_implemented`
- 需要接入 PaddleOCR 或 Tesseract

### 10.3 解决方案

```python
def _try_ocr_fallback(self, pdf_path: str):
    """PaddleOCR fallback"""
    # 1. PyMuPDF 提取每页图片
    # 2. PaddleOCR 识别文本
    # 3. 保留页码信息
```

---

## 优先级总结

| 优先级 | 问题 | 影响 | 工作量 |
|--------|------|------|--------|
| **P1** | 公式处理 | 20% chunk 是公式噪声 | 中（检测+标记）/ 大（识别） |
| **P1** | 图片提取 | 核心论证信息丢失 | 中 |
| **P1** | 表格结构还原 | 关键数据无法利用 | 中 |
| **P2** | 文本碎片化 | 检索质量下降 | 小 |
| **P2** | 单词间距 | 部分文本可读性差 | 小 |
| **P2** | 参考文献标题 | 元数据不完整 | 小 |
| **P2** | 扫描件 OCR | 无法处理扫描 PDF | 中 |
| ✅ | CID 伪影 | 已解决 | — |
| ✅ | 合字/断行 | 已解决 | — |
| ✅ | 章节检测 | 已解决 | — |

---

## 技术路线图

```
当前（P0 完成）
├── pdfplumber + PyMuPDF + pdfminer 三解析器 fallback
├── TextPostProcessor（合字/断行/CID/页眉页脚）
├── 章节检测 + 分块 + overlap
├── 参考文献结构化提取
└── 质量检测 + 乱码/水印/间距检测

下一步（P1）
├── 公式区域检测 + 标记（不识别，只标记为 formula_block）
├── 图片区域检测 + caption 提取
├── 表格区域检测 + 结构化提取（Camelot/pdfplumber）
└── 文本碎片合并

中期（P2）
├── Nougat / Marker 接入（端到端 PDF → Markdown，保留公式和表格）
├── PaddleOCR 接入（扫描件）
├── 多模态 LLM 图片理解
└── CrossRef API 参考文献反查

长期（P3）
├── 公式 LaTeX 解析 + 语义理解
├── 图文关联 + 自动描述
└── 知识图谱自动构建（从公式/表格/图表中提取关系）
```
