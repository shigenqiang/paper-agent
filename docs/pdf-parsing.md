# PDF 解析模块

## 架构概览

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
│  ┌─────────────────────────────────┐    │
│  │  质量检查                        │    │
│  │  - 扫描件检测                    │    │
│  │  - 乱码检测 (中文 PDF)           │    │
│  │  - 水印检测 (知网/万方)          │    │
│  │  - 双栏布局检测                  │    │
│  └─────────────────────────────────┘    │
│              │                           │
│              ▼                           │
│  ┌─────────────────────────────────┐    │
│  │  章节分块 (Section-Based)        │    │
│  │  - 章节标题检测 (中英文)          │    │
│  │  - 500-900 token/块             │    │
│  │  - 80 token overlap             │    │
│  │  - 参考文献分离                  │    │
│  └─────────────────────────────────┘    │
│              │                           │
│              ▼                           │
│  ┌─────────────────────────────────┐    │
│  │  参考文献结构化提取               │    │
│  │  - 按编号分割                    │    │
│  │  - DOI/年份/标题提取             │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
    │                │               │
    ▼                ▼               ▼
paper_chunks    references     parse_results
```

## 支持的解析器

| 解析器 | 状态 | 说明 |
|--------|------|------|
| pdfplumber | 默认 | 基于 pdfminer.six，文本提取质量高 |
| PyMuPDF | Fallback | 速度快，处理复杂 PDF 更稳定 |
| GROBID | 计划中 | 学术论文元数据提取事实标准 |
| MinerU | 计划中 | 一站式学术 PDF 解析（需 GPU） |
| Marker | 计划中 | PDF 转 Markdown，公式/表格支持 |

## 分块策略

采用 **Section-Based + Overlap** 混合策略：

1. 按页提取文本
2. 正则识别章节标题（支持中英文：Abstract/摘要、Introduction/引言、Methods/方法 等）
3. 章节标题归一化为 `section_type`
4. 每个 chunk 目标 500-900 tokens
5. 相邻 chunk 有 80 token 尾部重叠
6. 参考文献章节单独标记，不进入正文 chunk

### ChunkType 枚举

| 类型 | 说明 | 是否进入正文 |
|------|------|-------------|
| title | 论文标题 | 否 |
| abstract | 摘要 | 是 |
| body | 正文（引言、相关工作等） | 是 |
| method | 方法 | 是 |
| result | 结果 | 是 |
| discussion | 讨论 | 是 |
| limitation | 局限 | 是 |
| conclusion | 结论 | 是 |
| reference | 参考文献 | 否 |
| table | 表格 | 否 |
| figure_caption | 图注 | 否 |
| appendix | 附录 | 否 |

## 质量标记 (Quality Flags)

| 标记 | 说明 |
|------|------|
| `empty_pdf` | PDF 文本内容极少 (< 100 字符) |
| `low_text_coverage` | 文本覆盖低 (< 500 字符) |
| `scanned_pdf_suspected` | 疑似扫描件，无文本可提取 |
| `too_many_short_lines` | 短行过多，可能是表格或乱码 |
| `garbled_text_detected` | 检测到乱码（中文 PDF 常见） |
| `watermark_suspected` | 疑似包含水印 |
| `dual_column_detected` | 检测到双栏布局 |
| `low_section_coverage` | 章节识别覆盖率低 |
| `pdfplumber_fallback` | pdfplumber 失败，使用 fallback |
| `parser_import_error` | 解析器依赖未安装 |
| `parser_exception` | 解析器运行异常 |

## 中文 PDF 处理

### 乱码检测

知网/万方下载的 PDF 常因 CID 字体编码问题导致提取文本乱码。检测策略：

1. 控制字符检测（`\x00-\x08` 等）
2. 替换字符检测（`□■◆◇○●`）
3. CJK 扩展区罕见字符（`\U00020000-\U0002A6DF`）
4. 高比例非 CJK 非 ASCII 字符

### 水印检测

知网/万方 PDF 常带文字水印层。检测策略：

1. 水印关键词匹配（"知网"、"CNKI"、"万方" 等）
2. 多页重复出现的短文本行

## 参考文献提取

支持格式：
- `[1] Author. Title. Journal, Year.`
- `1. Author. Title. Journal, Year.`

提取字段：
- DOI（正则匹配 `10.xxxx/...`）
- 年份（四位数字）
- 标题（启发式规则）
- 作者（启发式规则）

## 后续扩展路线

### P2 阶段

- GROBID 适配器：元数据提取、参考文献结构化、引用关系
- MinerU/Docling 适配器：表格提取、公式识别、OCR
- Marker 适配器：Markdown 输出、公式/表格增强
- 完整 Reference 模型：引用上下文、引用关系图

### P3 阶段

- VLM 端到端方案（Dolphin/Nougat）
- 公式 LaTeX 识别（pix2tex/UniMERNet）
- 表格结构还原（Table Transformer）
