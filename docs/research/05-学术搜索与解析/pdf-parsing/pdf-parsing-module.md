# PDF 解析模块技术文档

> 融合自：pdf-parsing.md、pdf-parsing-issues.md、中文PDF乱码问题与解决方案调研报告.md、双栏PDF布局解析方案调研报告.md、PDF解析边缘问题与解决方案调研报告.md
> 更新时间：2026-05-31

---

## 1. 架构概览

```
PDF 文件输入
    │
    ▼
┌─────────────────────────────────────────┐
│  ParserService.parse_paper()            │
│  ┌─────────────────────────────────┐    │
│  │  ParserAdapter 链               │    │
│  │  1. PdfPlumberAdapter           │    │
│  │  2. PyMuPDFAdapter (fallback)   │    │
│  │  3. [future] GROBIDAdapter      │    │
│  │  4. [future] MinerUAdapter      │    │
│  └─────────────────────────────────┘    │
│              │                           │
│              ▼                           │
│  质量检查：扫描件 / 乱码 / 水印 / 双栏   │
│              │                           │
│              ▼                           │
│  章节分块 (Section-Based)                │
│  - 章节标题检测 (中英文)                  │
│  - 500-900 token/块, 80 token overlap   │
│  - 参考文献分离                          │
│              │                           │
│              ▼                           │
│  参考文献结构化提取                       │
└─────────────────────────────────────────┘
    │                │               │
    ▼                ▼               ▼
paper_chunks    references     parse_results
```

### 解析器

| 解析器 | 状态 | 说明 |
|--------|------|------|
| pdfplumber | 默认 | 文本提取质量高 |
| PyMuPDF | Fallback | 速度快，复杂PDF更稳定 |
| GROBID | 计划中 | 学术元数据提取事实标准 |
| MinerU | 计划中 | 一站式学术PDF解析（需GPU） |
| Marker | 计划中 | PDF转Markdown |

---

## 2. 分块策略

| ChunkType | 进入正文 | 说明 |
|-----------|---------|------|
| title | 否 | 论文标题 |
| abstract | 是 | 摘要 |
| body | 是 | 引言、相关工作 |
| method | 是 | 方法 |
| result | 是 | 结果 |
| discussion | 是 | 讨论 |
| conclusion | 是 | 结论 |
| reference | 否 | 参考文献 |
| table | 否 | 表格 |
| figure_caption | 否 | 图注 |
| appendix | 否 | 附录 |

---

## 3. 质量标记 (Quality Flags)

| 标记 | 说明 |
|------|------|
| `empty_pdf` | 文本内容 < 100 字符 |
| `scanned_pdf_suspected` | 疑似扫描件 |
| `garbled_text_detected` | 检测到乱码 |
| `watermark_suspected` | 疑似水印 |
| `dual_column_detected` | 双栏布局 |
| `low_section_coverage` | 章节识别覆盖率低 |
| `pdfplumber_fallback` | 使用fallback解析器 |

---

## 4. 已知问题与解决状态

### 4.1 已解决

| 问题 | 方案 |
|------|------|
| CID伪影 `(cid:48)` | `fix_cid_artifacts()` 正则清理 |
| 合字 `ﬁ` | `fix_ligatures()` 7种合字修复 |
| 连字符断行 `computa-\ntion` | `fix_hyphenation()` 自动拼接 |
| 引用标记 `word [1]` | `fix_citation_markers()` 重连 |
| 页眉页脚 | `remove_headers_footers()` |
| 页码 | `remove_page_numbers()` |
| 章节检测 | 30+种中英文章节模式 |

### 4.2 待解决 (P1)

| 问题 | 影响 | 方案 |
|------|------|------|
| **公式处理** | 20% chunk是公式噪声，上下标丢失 | 短期：公式区域检测+标记；中期：LaTeX-OCR/pix2tex |
| **图片丢失** | 核心论证信息丢失（27个chunk引用图片但无图片） | 短期：图片位置标记+caption提取；中期：多模态LLM理解 |
| **表格结构丢失** | 关键数据无法利用（AIC/BIC等指标变成平文本） | 短期：表格区域检测；中期：Camelot/pdfplumber结构还原 |

### 4.3 待解决 (P2)

| 问题 | 影响 | 方案 |
|------|------|------|
| 文本碎片化 | 90 token chunk缺乏上下文 | 合并 < 200 token 的碎片 |
| 单词间距丢失 | 部分文本可读性差 | 已有fallback，待改进断词策略 |
| 参考文献标题提取 | 成功率约60% | 改进启发式 + CrossRef API反查 |
| 扫描件OCR | 无法处理扫描PDF | 接入PaddleOCR |

---

## 5. 中文PDF特殊处理

### 5.1 乱码检测

知网/万方PDF常因CID字体编码导致乱码。检测策略：

1. 控制字符检测（`\x00-\x08`）
2. 替换字符检测（`□■◆◇○●`）
3. CJK扩展区罕见字符
4. 高比例非CJK非ASCII字符

### 5.2 水印检测

知网/万方PDF常带文字水印层：

1. 水印关键词匹配（"知网"、"CNKI"、"万方"）
2. 多页重复出现的短文本行

### 5.3 双栏布局

检测策略：基于文本块x坐标的聚类分析，识别左右两栏。

处理：分栏后按阅读顺序重排文本。

---

## 6. 技术路线图

```
当前（P0 完成）
├── pdfplumber + PyMuPDF 双解析器 fallback
├── TextPostProcessor（合字/断行/CID/页眉页脚）
├── 章节检测 + 分块 + overlap
├── 参考文献结构化提取
└── 质量检测 + 乱码/水印/间距检测

下一步（P1）
├── 公式区域检测 + 标记（formula_block）
├── 图片区域检测 + caption 提取
├── 表格区域检测 + 结构化提取
└── 文本碎片合并

中期（P2）
├── MinerU/Marker 适配器（端到端 PDF → Markdown）
├── PaddleOCR（扫描件）
├── 多模态LLM图片理解
└── CrossRef API 参考文献反查

长期（P3）
├── 公式 LaTeX 解析 + 语义理解
├── 图文关联 + 自动描述
└── 知识图谱自动构建
```
