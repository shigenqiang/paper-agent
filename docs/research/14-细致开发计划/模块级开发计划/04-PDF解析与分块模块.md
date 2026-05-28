# PDF 解析与分块模块专项开发计划

更新时间：2026-05-28

## 实现状态

P0 全部完成（2026-05-28）。P1 部分完成。P2 未开始。

### P0 已完成

```text
T4.1 parse_paper 开始时写 PARSING ✅
T4.2 PaperChunk 模型补齐 page_start/page_end/chunk_index/section_type/chunk_type/parser_name ✅
T4.3 不再生成 "[PDF parsing requires pdfplumber]" stub chunk ✅
T4.4 _save_chunks 改写到 paper_chunks 集合，兼容旧 chunks_{paper_id} ✅
T4.5 增加 ParseResult 存储 ✅
T4.6 References 章节单独标记，不进入默认正文 ✅
T4.7 chunk_id 和 chunk_index 稳定化 ✅
```

### P1 已完成

```text
T4.8 增强 section detector：编号标题、中文标题 ✅
T4.9 增加 section_type 归一 ✅
T4.10 增加 overlap 分块（80 token 尾部重叠）✅
T4.11 增加质量标记和 text coverage 计算 ✅
```

### P1 未完成

```text
T4.12 增加 PyMuPDF fallback
T4.13 增加扫描件检测（只有标记，无自动 OCR）
```

### 下游适配

- `PaperCardGenerator` 已适配：从 `paper_chunks` 读取，排除 reference/table/figure_caption
- `PaperChunk` 新字段：`chunk_index`, `section_type`, `chunk_type`, `page_start`, `page_end`, `parser_name`, `quality_flags`, `metadata`
- 旧格式 `chunks_{paper_id}` 自动迁移到 `paper_chunks`

本计划聚焦 PDF 解析、章节识别、分块、参考文献分离和来源定位。这个模块是证据追溯的地基：后续论文卡片、证据表、QA、知识图谱和报告生成，都必须能从 `PaperChunk` 回到具体论文、章节、页码和原文 quote。

对应代码：

```text
src/agents_v3/research_workspace/parser_service.py
src/agents_v3/research_workspace/models.py
tests/agents_v3/research_workspace/test_parser_service.py
```

相关研究文档：

```text
docs/research/05-学术搜索与解析/PDF解析技术调研报告.md
docs/research/12-优化方案/文献综述Token消耗与上下文容量分析报告.md
docs/research/14-细致开发计划/模块级开发计划/01-核心模型与存储模块.md
docs/research/14-细致开发计划/模块级开发计划/05-论文卡片生成模块.md
docs/research/14-细致开发计划/模块级开发计划/06-证据表模块.md
```

## 1. 当前实现分析

### 1.1 当前已有能力

`ParserService` 已有方法：

```text
parse_paper(paper_id)
parse_project_papers(project_id, only_unparsed=True)
get_chunks(paper_id)
_extract_chunks(pdf_path, paper_id)
_detect_section(line)
_estimate_tokens(text)
_chunk_by_sections(pages_text, paper_id)
_flush_buffer(...)
_save_chunks(paper_id, chunks)
_update_status(...)
```

当前实现已经不只是空行切段，具备：

| 能力 | 当前状态 |
| --- | --- |
| pdfplumber 解析 | 已使用 |
| 每页抽取 | 已按 page 遍历 |
| 章节标题识别 | 已有中英文常见标题正则 |
| token 估算 | 已有粗略估算 |
| 长文本拆块 | 已按 900 token 上限拆分 |
| 批量解析 | 单篇失败不影响整体统计 |
| 状态更新 | 成功写 `PARSED`，失败写 `FAILED` |

### 1.2 当前主要缺口

| 领域 | 当前状态 | 问题 |
| --- | --- | --- |
| 解析状态 | 未在解析开始时写 `PARSING` | 前端和任务系统无法显示进行中 |
| chunk 模型 | `PaperChunk` 没有 `page_number/page_start/page_end/chunk_index/parser_name` | 写入的页码读取时可能丢失 |
| 存储集合 | 写入 `chunks_{paper_id}` | 不利于统一查询和跨论文检索 |
| 页码范围 | `_flush_buffer` 只记录单页 `page_number` | 跨页 chunk 无法定位范围 |
| 章节规范化 | section title 是标题文本 | 缺少 `section_type`，不利于 Evidence 规则 |
| References | 识别到 references 但没有单独分离 | 参考文献可能进入卡片和证据 |
| 表格/图注 | 未提取 | 方法、结果、数据集常在表格中 |
| OCR | 无扫描件检测 | 扫描 PDF 会被误判为空文本 |
| fallback | pdfplumber 缺失时生成 stub chunk | 可能污染卡片和证据 |
| 解析报告 | 只返回 chunk_count | 缺少 page_count、section_count、quality flags |
| 多解析器 | 只有 pdfplumber | 对复杂版式、双栏、表格、公式不稳 |

### 1.3 必须立即修正的行为

当前 `ImportError` 时返回：

```text
"[PDF parsing requires pdfplumber]"
```

这类 stub chunk 不能进入下游生成。应改为：

```text
1. parse_paper 返回 success=false。
2. paper.status=failed。
3. error_message="pdfplumber not installed"。
4. 不写入正文 chunk。
```

## 2. 主流解析工具做法

### 2.1 调研参考

| 工具/系统 | 可借鉴做法 |
| --- | --- |
| GROBID | 专门面向学术 PDF；输出 TEI XML；支持 header、fulltext、references、坐标、参考文献 consolidation |
| Unstructured | 将文档 partition 成 Title、NarrativeText、ListItem、Table 等元素；PDF 支持 fast/hi_res/ocr_only 策略和表格/OCR 选项 |
| PyMuPDF | 快速页面文本、blocks、words、坐标抽取；适合 fallback 和定位 |
| Marker | 将 PDF 转 Markdown/JSON，关注表格、公式、图片、OCR、多格式输出 |
| LangChain/LlamaIndex RAG 实践 | chunk 应保留 metadata：source、page、section、chunk index，并针对问答做 token 窗口和 overlap |

### 2.2 对本项目的落地结论

第一阶段不需要直接引入所有解析器，但架构必须按多解析器设计：

```text
PDFParserAdapter
  -> PdfPlumberParser
  -> PyMuPDFParser
  -> GrobidParser(optional)
  -> UnstructuredParser(optional)
  -> MarkerParser(optional)
```

解析输出统一为：

```text
ParseResult
  paper metadata patch
  sections
  chunks
  references
  tables
  figures
  quality flags
```

主流做法对本项目最关键的要求：

```text
1. 不只抽全文，还要抽结构。
2. chunk 必须有页码、章节、parser、chunk_index。
3. references/table/figure_caption 要和正文区分。
4. 扫描件和低质量解析要显式标记。
5. 解析失败不能生成可被 LLM 当作正文的占位文本。
```

## 3. 模块目标

### 3.1 一句话目标

把 PDF 稳定转换为带页码、章节、类型、质量标记的 `PaperChunk`，并把参考文献、表格、图注和解析报告作为后续可扩展产物。

### 3.2 MVP 成功标准

```text
1. parse_paper 开始时写 PARSING，成功写 PARSED，失败写 FAILED。
2. 每个 chunk 有 paper_id、chunk_id、chunk_index、section_title、section_type、chunk_type、page_start/page_end、token_count。
3. References 章节不进入默认正文 chunk。
4. 空文本、扫描件、解析器缺失不会生成 stub 正文。
5. get_chunks(paper_id) 能读取统一 `paper_chunks` 集合，同时兼容旧 `chunks_{paper_id}`。
6. ParseResult 记录 page_count、chunk_count、section_count、reference_count、quality_flags、error。
7. 批量解析单篇失败不阻断其他论文。
8. 论文卡片生成只消费 body/abstract/method/result/discussion/conclusion 等可用 chunk。
```

### 3.3 暂不做

```text
1. 第一阶段不强制部署 GROBID 服务。
2. 第一阶段不实现完整公式识别。
3. 第一阶段不做复杂表格结构还原。
4. 第一阶段不做引用网络解析的完整闭环。
5. 第一阶段不做自动 OCR，只检测并提示。
```

## 4. 目标架构

### 4.1 数据流

```text
Paper(pdf_path)
   |
   v
ParserService.parse_paper()
   |
   +--> ParserAdapter.extract()
   |
   +--> ParseResult
          paper_metadata_patch
          pages
          sections
          chunks
          references
          tables
          figures
          quality_flags
   |
   +--> paper_chunks storage
   +--> parse_results storage
   +--> Paper.status update
```

### 4.2 建议文件拆分

```text
src/agents_v3/research_workspace/parsing/
  __init__.py
  models.py
  service.py
  adapters/
    base.py
    pdfplumber_parser.py
    pymupdf_parser.py
    grobid_parser.py
    unstructured_parser.py
  section_detector.py
  chunker.py
  reference_splitter.py
  quality.py
```

MVP 可以先保留 `parser_service.py`，但要让内部函数逐步可独立测试。

## 5. 数据模型

### 5.1 ParseResult

```python
class ParseResult(BaseModel):
    parse_id: str
    paper_id: str
    project_id: str = ""
    parser_name: str = ""
    parser_version: str = ""
    status: ParseStatus = ParseStatus.PENDING
    page_count: int = 0
    section_count: int = 0
    chunk_count: int = 0
    reference_count: int = 0
    table_count: int = 0
    figure_count: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    error_message: str = ""
    started_at: str = ""
    finished_at: str = ""
```

### 5.2 Section

```python
class ParsedSection(BaseModel):
    section_id: str
    paper_id: str
    title: str = ""
    section_type: str = ""
    level: int = 0
    page_start: int | None = None
    page_end: int | None = None
    text: str = ""
```

### 5.3 ChunkType

```text
title
abstract
body
method
result
discussion
limitation
conclusion
reference
table
figure_caption
appendix
unknown
```

`reference` 默认不进入论文卡片和证据生成。

### 5.4 PaperChunk

按核心模型计划扩展：

```text
chunk_id
paper_id
section_title
section_type
section_level
chunk_index
chunk_type
text
start_char
end_char
page_start
page_end
token_count
parser_name
parser_version
quality_flags
metadata
```

## 6. 分块策略

### 6.1 P0 策略

```text
1. 按页抽取文本。
2. 对每页保留 page_number。
3. 用章节标题正则识别 Abstract/Introduction/Methods/Results/Discussion/Conclusion/References。
4. 将章节标题归一为 section_type。
5. References 后的内容标记为 reference，不进入正文 chunks。
6. 每个正文 chunk 目标 500-900 tokens。
7. 相邻正文 chunk overlap 50-100 tokens。
8. chunk_id 使用稳定格式：chunk_{paper_id}_{chunk_index:04d}。
9. token_count 超过 1100 的 chunk 必须继续拆分。
10. text 少于 30 字符的碎片默认丢弃，除非是标题/表格/图注。
```

### 6.2 章节权重

供后续卡片和证据使用：

| section_type | 用途 |
| --- | --- |
| abstract | 背景摘要，不作为唯一强证据 |
| introduction | 研究问题、背景、gap |
| method | 方法、样本、数据集 |
| result | 核心发现 |
| discussion | 解释、局限、未来方向 |
| limitation | 局限 |
| conclusion | 总结、未来方向 |
| reference | 引文解析，不进入主证据 |

### 6.3 质量标记

```text
empty_pdf
low_text_coverage
scanned_pdf_suspected
too_many_short_lines
references_not_detected
section_detection_low_confidence
table_heavy_pdf
parser_import_error
parser_exception
```

## 7. 多解析器策略

### 7.1 ParserAdapter 接口

```python
class ParserAdapter(Protocol):
    name: str
    def can_parse(self, pdf_path: str) -> bool: ...
    def parse(self, pdf_path: str, paper_id: str) -> ParseResult: ...
```

### 7.2 P0/P1 选型

| 阶段 | 解析器 | 作用 |
| --- | --- | --- |
| P0 | pdfplumber | 当前默认，抽页文本 |
| P1 | PyMuPDF | 快速 fallback，补 blocks/words/坐标 |
| P1 | GROBID | 学术论文结构化 TEI、参考文献 |
| P2 | Unstructured | OCR/table/element partition 增强 |
| P2 | Marker | Markdown/JSON、公式/表格/OCR 增强 |

### 7.3 fallback 规则

```text
pdfplumber 成功且 text coverage 足够 -> 使用 pdfplumber。
pdfplumber 失败或空文本 -> 尝试 PyMuPDF。
仍然空文本 -> 标记 scanned_pdf_suspected，不生成正文 chunk。
GROBID/Unstructured/Marker 作为可选增强，不阻塞 MVP。
```

## 8. 状态流转

```text
IMPORTED / UPLOADED
  -> PARSING
  -> PARSED
  -> FAILED
```

规则：

```text
1. 无 pdf_path：FAILED，error_message="No PDF path"。
2. pdf_path 不存在：FAILED，error_message="PDF file not found"。
3. 解析器依赖缺失：FAILED，不写 stub chunk。
4. 空文本：FAILED 或 PARTIAL，并标记 scanned_pdf_suspected。
5. 至少一个正文 chunk 才能标记 PARSED。
6. 批量解析结果必须统计 total/success/failed/skipped。
```

## 9. 开发阶段

### P0：修正解析基础契约

```text
T4.1 parse_paper 开始时写 PARSING。
T4.2 PaperChunk 模型补齐 page_start/page_end/chunk_index/chunk_type/parser_name。
T4.3 不再生成 "[PDF parsing requires pdfplumber]" stub chunk。
T4.4 `_save_chunks` 改写到 `paper_chunks` 集合，并兼容旧 chunks_{paper_id}。
T4.5 增加 ParseResult 存储。
T4.6 References 章节单独标记，不进入默认正文。
T4.7 chunk_id 和 chunk_index 稳定化。
```

### P1：提升结构化解析

```text
T4.8 增强 section detector：编号标题、大小写、中文标题、双栏断行。
T4.9 增加 section_type 归一。
T4.10 增加 overlap 分块。
T4.11 增加质量标记和 text coverage 计算。
T4.12 增加 PyMuPDF fallback。
T4.13 增加扫描件检测。
```

### P2：学术结构增强

```text
T4.14 增加 GROBID adapter 设计和可选接入。
T4.15 增加 Reference 模型和参考文献解析。
T4.16 增加 table/figure_caption chunk。
T4.17 增加 DOI/title/author/year 元数据补全。
T4.18 增加解析质量报告 UI/API 输出。
```

## 10. 测试计划

新增或增强：

```text
test_parser_service.py
test_parser_status_flow.py
test_parser_sections.py
test_parser_chunk_size.py
test_parser_chunk_metadata.py
test_parser_references_split.py
test_parser_failure.py
test_parser_batch.py
test_parser_legacy_chunks.py
test_parser_quality_flags.py
```

关键测试：

```text
无 paper 返回 success=false。
无 pdf_path 写 FAILED。
PDF 文件缺失写 FAILED。
解析开始写 PARSING。
pdfplumber 缺失不写 stub chunk。
简单 PDF 能生成正文 chunks。
chunk 包含 page_start/page_end/chunk_index/parser_name。
References 不混入 body chunks。
chunk token_count 不超过上限。
批量解析中一篇失败，其余继续。
get_chunks 兼容旧 chunks_{paper_id}。
空文本 PDF 标记 scanned_pdf_suspected。
```

## 11. 验收标准

```text
pytest tests/agents_v3/research_workspace/test_parser_service.py 通过。
真实 PDF 可生成带章节、页码和 chunk_index 的 chunks。
解析失败不会产生可被下游误用的正文 chunk。
References 被分离或标记为 reference。
PaperCardGenerator 默认只读取可用正文 chunk。
ParseResult 能解释成功、失败、partial 和质量问题。
```

## 12. 参考来源

```text
GROBID Documentation:
https://grobid.readthedocs.io/en/latest/

Unstructured Partitioning:
https://docs.unstructured.io/open-source/core-functionality/partitioning

PyMuPDF Text Extraction:
https://pymupdf.readthedocs.io/en/latest/recipes-text.html

Marker:
https://github.com/datalab-to/marker
```
