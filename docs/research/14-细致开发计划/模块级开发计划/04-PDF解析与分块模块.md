# PDF 解析与分块模块专项开发计划

更新时间：2026-06-01

本文依据：

- `docs/research/05-学术搜索与解析/pdf-parsing/学术PDF解析综合技术报告.md`
- `docs/research/05-学术搜索与解析/pdf-parsing/端到端学术PDF解析方案深度调研报告.md`
- `docs/research/05-学术搜索与解析/pdf-parsing/PDF解析技术调研总报告.md`
- `docs/research/11-产品方案与开发/当前产品方案.md`
- `docs/research/11-产品方案与开发/当前开发计划.md`
- `docs/research/00-综合调研报告/学术报告生成系统产品借鉴与技术方案调研.md`
- 当前代码：`src/agents_v3/research_workspace/parser_service.py`
- 当前模型：`src/agents_v3/research_workspace/models.py`

## 0. 与产品方案的关联

PDF 解析模块是产品主线的第二环：

```text
论文入库（搜索/上传/导入）
  -> 论文解析（PDF 分块）← 本模块
  -> 论文卡片
  -> 证据表
  -> 知识图谱
  -> Scope QA
  -> 文献综述
  -> 创新点报告
```

解析模块的质量直接影响下游所有环节。借鉴产品方案中的以下技术：

| 借鉴来源 | 在解析模块的应用 |
| --- | --- |
| Anthropic Contextual Retrieval | 每个 chunk 携带论文标题、作者、章节上下文摘要，减少 67% 失败检索 |
| RAGFlow Parent-Child Chunking | 检索命中 child chunk，返回 parent chunk 给 LLM，确保上下文完整 |
| GROBID | 学术论文元数据提取事实标准，参考文献解析 F1 90%+ |
| Literature Mapper | 参考文献结构化提取 → 识别 ghost papers（被引用但不在库中的论文） |
| PRISMA-trAIce | 解析诊断数据应可追溯（哪个解析器、什么质量标记、什么覆盖率） |
| LettuceDetect | 解析质量影响幻觉检测：低质量 chunk → 高幻觉风险 |

### 当前代码与产品方案的对齐状态

| 产品方案要求 | 当前代码状态 | 差距 |
| --- | --- | --- |
| Parent-Child Chunking | ✅ `_create_parent_chunks` 已实现 | 无 |
| Contextual Retrieval | ⚠️ `_make_chunk` 未添加上下文前缀 | 需实现 |
| 多解析器 fallback | ✅ `_extract_with_fallback` 已实现 5 个适配器（pymupdf4llm 优先） | 无 |
| 文本后处理 | ✅ `TextPostProcessor` 已实现 | 无 |
| 分块去重 | ✅ `ChunkDeduplicator` 三层去重已实现 | 无 |
| 分块质量评分 | ✅ `ChunkQualityScorer` 5 维评分已实现 | 无 |
| 冗余过滤 | ✅ `ChunkRedundancyFilter` BM25 已实现 | 无 |
| 版面感知阅读顺序 | ✅ pymupdf4llm GNN 版面分析（T4.18+ 已实现） | 无 |
| PaddleOCR fallback | ⚠️ `_try_ocr_fallback` 只标记未实现 | 需实现 |
| 公式检测 | ❌ 未实现 | 需实现 |
| 表格提取 | ❌ 未实现 | 需实现 |
| GROBID 适配器 | ❌ 未实现 | 需实现 |

---

## 实现状态

P0 全部完成。P1 部分完成。P2/P3 未开始。

### 已完成

```text
T4.1  parse_paper 开始时写 PARSING ✅
T4.2  PaperChunk 模型补齐 page_start/page_end/chunk_index/section_type/chunk_type/parser_name ✅
T4.3  不再生成 stub chunk ✅
T4.4  _save_chunks 改写到 paper_chunks 集合，兼容旧 chunks_{paper_id} ✅
T4.5  增加 ParseResult 存储 ✅
T4.6  References 章节单独标记，不进入默认正文 ✅
T4.7  chunk_id 和 chunk_index 稳定化 ✅
T4.8  增强 section detector：编号标题、中文标题 ✅
T4.9  增加 section_type 归一 ✅
T4.10 增加 overlap 分块（80 token 尾部重叠）✅
T4.11 增加质量标记和 text coverage 计算 ✅
T4.12 ParserAdapter 协议 + PyMuPDF4LLMAdapter + PdfPlumberAdapter + PyMuPDFAdapter + PdfMinerAdapter + DoclingAdapter ✅
T4.13 中文乱码检测 (_detect_garbled_text) ✅
T4.14 水印检测 (_detect_watermark) ✅
T4.15 双栏布局检测 + 重排 (PyMuPDFAdapter._find_column_boundary + _reorder_columns) ✅
T4.16 Reference 模型 + 参考文献结构化提取 ✅
T4.17 增强质量报告 (quality_flags + diagnostics) ✅
T4.18 版面感知：双栏检测+重排（基础版）✅
T4.18+ 版面感知升级：pymupdf4llm GNN 版面分析（已集成，首选解析器）✅
T4.19 文本后处理管线：TextPostProcessor（合字/连字符/引用标记/页码/页眉页脚/CID/单词间距）✅
T4.22 pdfminer.six 第三解析器：PdfMinerAdapter ✅
T4.27 分块后去重：ChunkDeduplicator（SHA256 + MinHash + BM25 三层去重）✅
T4.28 分块质量评分与过滤：ChunkQualityScorer（5维评分 + 低质量过滤）✅
T4.29 Chunk 冗余检测与剔除：ChunkRedundancyFilter（BM25 + 动态阈值）✅
Parent-Child 分块：_create_parent_chunks（~2000 token 父块聚合）✅
单词间距修复：TextPostProcessor.fix_word_spacing ✅
CID 伪影移除：TextPostProcessor.fix_cid_artifacts ✅
单词间距质量检测：_detect_poor_spacing ✅
pymupdf4llm 适配器：PyMuPDF4LLMAdapter（GNN 版面分析，首选解析器）✅
Docling 适配器：DoclingAdapter（降级为兜底）✅
扫描件预检测：_detect_scanned_pdf ✅
embed_paper 向量化入库 ✅
search_chunks 检索（含 parent context 返回）✅
```

### 未完成

```text
T4.18+ XY-Cut++ 纯算法备选（pymupdf4llm 已集成，此为低优先级备选）
T4.20 PaddleOCR fallback（中文 PDF 乱码的唯一可靠方案，当前 _try_ocr_fallback 只标记）
T4.21 扫描件 OCR fallback（当前扫描件检测后只标记不处理）
T4.23 GROBID Docker 适配器（参考文献解析精度最高 F1 90%+）
T4.24 公式区域检测 + LaTeX 识别
T4.25 表格结构化提取
T4.26 Contextual Retrieval（chunk 上下文增强：论文标题+作者+章节前缀）
```

对应代码：

```text
src/agents_v3/research_workspace/parser_service.py          # 2231 行，核心解析服务
src/agents_v3/research_workspace/models.py                  # PaperChunk, ParseResult, Reference 等模型
tests/agents_v3/research_workspace/test_parser_service.py   # 解析服务测试
src/agents_v3/research_workspace/embedding_service.py       # 向量化服务（embed_paper 调用）
src/agents_v3/research_workspace/vector_storage.py          # 向量存储（search_chunks 调用）
```

相关研究文档：

```text
docs/research/05-学术搜索与解析/pdf-parsing/学术PDF解析综合技术报告.md
docs/pdf-parsing.md
```

---

## 1. 当前架构与代码分析

### 1.1 现有 ParserAdapter 协议

```python
# parser_service.py:26-37
class ParserAdapter(Protocol):
    name: str
    def can_parse(self, pdf_path: str) -> bool: ...
    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]: ...
```

5 个内置适配器：`PyMuPDF4LLMAdapter`（首选）、`PdfPlumberAdapter`、`PyMuPDFAdapter`、`PdfMinerAdapter`、`DoclingAdapter`（兜底）。fallback 链路在 `_extract_with_fallback` 中遍历。

### 1.2 当前 fallback 逻辑

```python
# parser_service.py:668-703
def _extract_with_fallback(self, pdf_path):
    for adapter in self._adapters:
        pages_text, flags = adapter.extract_pages(pdf_path)
        if pages_text and any(t.strip() for _, t in pages_text):
            full_text = "\n".join(t for _, t in pages_text)
            if self._detect_garbled_text(full_text):
                quality_flags.append("garbled_text_detected")
                continue  # 尝试下一个解析器
            return pages_text, adapter.name, quality_flags
    quality_flags.append("scanned_pdf_suspected")
    return [], "none", quality_flags
```

**问题**：pdfplumber 和 PyMuPDF 对知网 PUA 映射都无效，两个都失败后直接标记扫描件放弃。

### 1.3 当前双栏检测

```python
# parser_service.py:992-1013
def _detect_dual_column(self, pages_text):
    # 基于行长度分布启发式
    # 连续两行都 < 40 字符且长度相似 → 双栏特征
    # 只标记不修正
```

**问题**：检测到双栏后只添加 `dual_column_detected` 标记，文本仍然是交叉的。

**产品调研结论（2026-05-30）**：没有产品单独做"双栏检测"。所有产品（MinerU、Marker、Docling）都是先检测每个文本区域的位置和类型，再确定阅读顺序。推荐方案：pymupdf4llm（GNN 版面分析，CPU 可用）+ XY-Cut++ 备选。

### 1.4 当前分块逻辑

```python
# parser_service.py:466-529
def _chunk_by_sections(self, pages_text, paper_id):
    # 逐行扫描，正则检测章节标题
    # 非标题行累积到 current_text
    # token >= 800 时 flush
    # _flush_buffer 按 500-900 token 拆分，带 80 token overlap
```

**问题**：按行扫描丢失了文本块的空间信息，无法处理双栏、脚注、页眉页脚。

---

## 2. T4.18：版面感知与阅读顺序（原"双栏文本重排"）

### 2.0 当前实现基线

当前 `PyMuPDFAdapter` 已实现基础版双栏检测+重排：

```text
_find_column_boundary()  # 通过空白谷检测找列分界线
_reorder_columns()       # 按分栏边界重排：全宽 → 左栏 → 右栏
```

**局限**：
- 只处理标准双栏，不支持三栏及以上
- 基于启发式规则，对复杂版面（嵌套表格、图文混排）效果差
- 没有 GNN 版面分析能力

### 2.1 产品调研结论（2026-05-30）

调研 MinerU、Marker/Surya、Docling、Unstructured、GROBID、ByteDance Dolphin、XY-Cut++ 等产品后，核心发现：

**没有产品单独做"双栏检测"。** 所有产品的做法是：先检测每个文本区域的位置和类型，再确定阅读顺序——这天然解决了多栏问题。

#### 三种技术路线

| 路线 | 代表 | 原理 | GPU | 精度 |
|------|------|------|-----|------|
| ML 版面检测 + ML 阅读顺序 | MinerU 1.x, Marker/Surya | DocLayout-YOLO 检测 → LayoutReader 排序 | 需要 | 最高 |
| ML 版面检测 + 规则排序 | Docling, Unstructured | RT-DETR/Detectron2 检测 → 算法排序 | 需要 | 中等 |
| 确定性算法 | XY-Cut++ (2025) | 投影轮廓 + 密度驱动分割 | 无 | 中等 |
| GNN 版面分析 | PyMuPDF Layout (pymupdf4llm) | 图神经网络版面分析 | 无 | 较好 |

#### 各产品实现细节

**MinerU**（最成熟）：
- v1.x：DocLayout-YOLO（YOLO-v10 + GL-CRM）检测区域 → LayoutReader（LayoutLMv3，BLEU 98.0）排序
- v2.5：统一多任务模型，一次推理同时输出位置、类别、旋转角、阅读顺序
- 特色：截断段落合并——在阅读顺序已知后，判断相邻区域是否应合并

**Marker/Surya**：
- SegFormer 检测布局 → 专用阅读顺序模型排序
- 输出每个 block 的 `reading_order` 字段
- 支持多栏和从右到左排版
- 性能：A10 上 0.273s/page 布局 + 0.109s/page 检测

**Docling**（CPU 可用）：
- RT-DETR 检测布局 → 后处理阶段算法排序
- **已知问题**：GitHub #2201 报告双栏 PDF 阅读顺序错误
- Granite-Docling（258M VLM）用 DocTags 编码阅读顺序

**XY-Cut++（2025）**（无需 GPU）：
1. 跨栏检测：识别全宽元素（标题、页眉页脚），beta=1.3 自适应阈值
2. 初步分割：标准 XY-Cut 投影轮廓分割
3. 密度驱动细化：根据内容密度动态选择分割轴

**ByteDance Dolphin**（ACL 2025）：
- Swin Transformer 编码 → mBart 解码，用"Parse the reading order"提示词
- 21 种元素类型，一次推理同时输出布局和阅读顺序

### 2.2 推荐方案：pymupdf4llm + XY-Cut++ 增强

> **2026-06-01 更新**：pymupdf4llm 已集成为首选解析器（PyMuPDF4LLMAdapter），测试结果全面优于 Docling（速度 3x、内容量 3x、章节识别 2.3x）。详见 `docs/test_results/04-PDF解析与分块/pymupdf4llm-test-report.md`。

根据调研，最适合本项目的方案是 **pymupdf4llm**（PyMuPDF Layout），原因：
- 无需 GPU，pip install 即用
- 内置 GNN 版面分析 + Markdown 输出
- 自动处理多栏阅读顺序
- 已被 PyMuPDF 官方集成

```bash
pip install pymupdf4llm
```

```python
import pymupdf4llm

# 方式 1：直接获取 Markdown（自动处理版面和阅读顺序）
md_text = pymupdf4llm.to_markdown(pdf_path)

# 方式 2：获取每页的结构化数据
page_data = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
# 每页包含: text, images, tables, metadata

# 方式 3：获取详细布局信息
from pymupdf4llm import LlamaMarkdownReader
reader = LlamaMarkdownReader()
docs = reader.load_data(pdf_path)
```

### 2.3 备选方案：XY-Cut++ 纯算法

当 pymupdf4llm 不可用或效果不佳时，使用 XY-Cut++ 算法：

```python
class XYCutReadingOrder:
    """XY-Cut++ 阅读顺序算法（2025）

    三阶段处理：
    1. 跨栏检测：识别全宽元素（标题、页眉页脚）
    2. 初步分割：标准 XY-Cut 投影轮廓分割
    3. 密度驱动细化：根据内容密度动态选择分割轴
    """

    def __init__(self, beta: float = 1.3, density_threshold: float = 0.9,
                 min_gap: float = 5.0):
        self.beta = beta  # 跨栏检测缩放因子
        self.density_threshold = density_threshold
        self.min_gap = min_gap

    def reorder(self, blocks: list[tuple], page_width: float) -> list[tuple]:
        """对文本块重排为正确阅读顺序

        Args:
            blocks: [(x0, y0, x1, y1, text, block_no, block_type), ...]
            page_width: 页面宽度

        Returns:
            重排后的 blocks 列表
        """
        if len(blocks) <= 1:
            return blocks

        # 阶段 1：分离全宽元素（标题、页眉页脚）
        full_width, column_blocks = self._split_full_width(blocks, page_width)

        # 阶段 2+3：对列内元素做 XY-Cut++ 排序
        ordered_columns = self._xy_cut_plus(column_blocks, page_width)

        # 拼接：全宽元素按 y 排序 + 列内元素
        full_width.sort(key=lambda b: b[1])
        return full_width + ordered_columns

    def _split_full_width(self, blocks, page_width):
        """分离全宽元素和列内元素"""
        threshold = page_width * 0.6  # 宽度 > 60% 页面 → 全宽
        full_width = []
        column_blocks = []
        for b in blocks:
            x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
            if (x1 - x0) > threshold:
                full_width.append(b)
            else:
                column_blocks.append(b)
        return full_width, column_blocks

    def _xy_cut_plus(self, blocks, page_width):
        """XY-Cut++ 递归分割"""
        if len(blocks) <= 1:
            return blocks

        # 计算投影轮廓，找最佳分割轴
        x_vals = sorted([b[0] for b in blocks] + [b[2] for b in blocks])
        y_vals = sorted([b[1] for b in blocks] + [b[3] for b in blocks])

        # 找最大空白谷
        x_gap = self._find_largest_gap(x_vals, self.min_gap)
        y_gap = self._find_largest_gap(y_vals, self.min_gap)

        # 根据密度选择分割轴
        if x_gap and y_gap:
            # 优先在更宽的间隙处分割
            if x_gap[1] > y_gap[1]:
                return self._split_vertical(blocks, x_gap[0], page_width)
            else:
                return self._split_horizontal(blocks, y_gap[0])
        elif x_gap:
            return self._split_vertical(blocks, x_gap[0], page_width)
        elif y_gap:
            return self._split_horizontal(blocks, y_gap[0])
        else:
            # 无法分割，按 y 坐标排序
            return sorted(blocks, key=lambda b: (b[1], b[0]))

    def _find_largest_gap(self, values, min_gap):
        """在有序坐标值中找最大间隙"""
        if len(values) < 2:
            return None
        best = None
        for i in range(len(values) - 1):
            gap = values[i + 1] - values[i]
            if gap >= min_gap:
                center = (values[i] + values[i + 1]) / 2
                if best is None or gap > best[1]:
                    best = (center, gap)
        return best

    def _split_vertical(self, blocks, x_split, page_width):
        """垂直分割（分栏）"""
        left = [b for b in blocks if b[2] <= x_split + 5]
        right = [b for b in blocks if b[0] >= x_split - 5]
        middle = [b for b in blocks if b not in left and b not in right]
        # 递归处理每侧
        result = self._xy_cut_plus(left + middle, page_width)
        result += self._xy_cut_plus(right, page_width)
        return result

    def _split_horizontal(self, blocks, y_split):
        """水平分割（段落）"""
        top = [b for b in blocks if b[3] <= y_split + 5]
        bottom = [b for b in blocks if b[1] >= y_split - 5]
        middle = [b for b in blocks if b not in top and b not in bottom]
        result = sorted(top + middle, key=lambda b: (b[1], b[0]))
        result += sorted(bottom, key=lambda b: (b[1], b[0]))
        return result
```

### 2.4 集成方案

> **2026-06-01 更新**：已实现为独立的 `PyMuPDF4LLMAdapter`，作为首选解析器集成到 fallback 链路。

```python
class PyMuPDF4LLMAdapter:
    """pymupdf4llm 解析器适配器（GNN 版面分析 + 全文档 Markdown 输出）"""
    name = "pymupdf4llm"

    def can_parse(self, pdf_path: str) -> bool:
        try:
            import pymupdf4llm  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        flags: list[str] = []
        try:
            import pymupdf4llm
        except ImportError:
            flags.append("pymupdf4llm_not_available")
            return [], flags

        try:
            page_data = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
            pages_text = [(i + 1, p.get("text", "")) for i, p in enumerate(page_data)]
            flags.append("pymupdf4llm_used")
            return pages_text, flags
        except Exception as e:
            flags.append("pymupdf4llm_exception")
            return [], flags
```

Fallback 链路：`pymupdf4llm → PdfPlumber → PyMuPDF → PdfMiner → Docling`

原方案中的 XY-Cut++ 备选保留为低优先级（T4.18+），当前 pymupdf4llm 已满足需求。
        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            xy_cut = XYCutReadingOrder()
            pages_text = []

            for i in range(len(doc)):
                page = doc[i]
                blocks = page.get_text("blocks")
                text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

                if not text_blocks:
                    pages_text.append((i + 1, ""))
                    continue

                # XY-Cut++ 重排
                ordered = xy_cut.reorder(text_blocks, page.rect.width)
                text = "\n".join(b[4].strip() for b in ordered)
                pages_text.append((i + 1, text))

            doc.close()
            flags.append("xycut_used")
            return pages_text, flags
        except Exception as e:
            logger.error(f"PyMuPDF failed: {e}")
            flags.append("pymupdf_exception")
            return [], flags
```

### 2.5 边界情况处理

| 情况 | 处理方式 |
|------|---------|
| 全宽元素（标题、摘要） | 宽度 > 页面 60% → 分离，放在列内容之前 |
| 脚注 | 字体大小 + y 坐标（底部 15-20% 区域）过滤 |
| 公式 | 可能全宽或列宽，宽度检测处理大多数情况 |
| 跨栏段落 | XY-Cut++ 密度驱动细化自动处理 |
| 参考文献区 | 通常仍是双栏，短行多，XY-Cut 可处理 |
| 三栏及以上 | XY-Cut 递归分割支持任意栏数 |

---

## 3. T4.19：文本后处理管线

### 3.1 设计

在文本提取后、分块前，添加统一的后处理步骤。每一步都是纯函数，输入 text 输出 text，便于独立测试。

```python
class TextPostProcessor:
    """文本后处理管线"""

    # 合字映射表
    LIGATURE_MAP = {
        'ﬀ': 'ff',  # ﬀ
        'ﬁ': 'fi',  # ﬁ
        'ﬂ': 'fl',  # ﬂ
        'ﬃ': 'ffi', # ﬃ
        'ﬄ': 'ffl', # ﬄ
        'ﬅ': 'st',  # ﬅ
        'ﬆ': 'st',  # ﬆ
    }

    # 页码模式
    PAGE_NUM_RE = re.compile(r'^\s*(?:\-?\s*\d+\s*\-?|Page\s+\d+|第\s*\d+\s*页)\s*$')

    def process(self, text: str) -> str:
        """完整后处理管线"""
        text = self.fix_ligatures(text)
        text = self.fix_hyphenation(text)
        text = self.fix_citation_markers(text)
        text = self.remove_page_numbers(text)
        return text

    def fix_ligatures(self, text: str) -> str:
        """合字修复：ﬁ → fi"""
        for lig, replacement in self.LIGATURE_MAP.items():
            text = text.replace(lig, replacement)
        return text

    def fix_hyphenation(self, text: str) -> str:
        """连字符断行修复：computa-\\ntion → computation"""
        return re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)

    def fix_citation_markers(self, text: str) -> str:
        """引用标记重连：word [1] → word[1]"""
        return re.sub(r'(\w)\s+\[(\d+(?:,\s*\d+)*)\]', r'\1[\2]', text)

    def remove_page_numbers(self, text: str) -> str:
        """移除独立的页码行"""
        lines = text.split('\n')
        cleaned = [l for l in lines if not self.PAGE_NUM_RE.match(l.strip())]
        return '\n'.join(cleaned)
```

### 3.2 页眉页脚去除

```python
def remove_headers_footers(self, pages_text: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """基于重复检测去除页眉页脚

    原理：同一 y 位置在 3+ 页出现的短文本 → 几乎确定是页眉/页脚

    实现方式：统计每行文本在多少页中出现，超过 80% 页面的短行移除。
    """
    from collections import Counter

    if len(pages_text) < 3:
        return pages_text

    # 统计每行出现在多少页
    line_page_count: Counter[str] = Counter()
    for _, text in pages_text:
        seen_lines = set()
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped and len(stripped) < 50:
                if stripped not in seen_lines:
                    line_page_count[stripped] += 1
                    seen_lines.add(stripped)

    # 超过 80% 页面出现的短行 → 页眉/页脚
    threshold = len(pages_text) * 0.8
    headers_footers = {line for line, count in line_page_count.items()
                       if count >= threshold and len(line) < 50}

    if not headers_footers:
        return pages_text

    # 从每页中移除
    result = []
    for page_num, text in pages_text:
        lines = text.split('\n')
        cleaned = [l for l in lines if l.strip() not in headers_footers]
        result.append((page_num, '\n'.join(cleaned)))

    return result
```

### 3.3 集成位置

在 `_extract_with_fallback` 返回 `pages_text` 后、`_chunk_by_sections` 之前：

```python
def parse_paper(self, paper_id: str) -> dict[str, Any]:
    # ... 现有代码 ...

    pages_text, parser_name, quality_flags = self._extract_with_fallback(paper.pdf_path)

    # 新增：文本后处理
    post_processor = TextPostProcessor()
    pages_text = [(pn, post_processor.process(t)) for pn, t in pages_text]
    pages_text = post_processor.remove_headers_footers(pages_text)

    # ... 继续分块 ...
```

---

## 4. T4.20：PaddleOCR Fallback

### 4.1 问题

知网/万方 PDF 将字符映射到 Unicode PUA 区（U+E000-U+F8FF），pdfplumber 和 PyMuPDF 都无法正确提取。OCR 是唯一可靠方案，因为它操作的是页面渲染后的图像，完全绕过字体编码。

### 4.2 PaddleOCR 适配器实现

```python
class PaddleOCRAdapter:
    """PaddleOCR 解析器适配器（中文 PDF 最终 fallback）"""
    name = "paddleocr"

    def can_parse(self, pdf_path: str) -> bool:
        try:
            from paddleocr import PaddleOCR  # noqa: F401
            from pdf2image import convert_from_path  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        flags = []
        try:
            from paddleocr import PaddleOCR
            from pdf2image import convert_from_path
            import tempfile
            import os

            # 初始化 OCR 引擎（首次加载模型较慢）
            ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)

            # PDF → 图像
            images = convert_from_path(pdf_path, dpi=300)
            pages_text = []

            for i, img in enumerate(images):
                # 保存为临时文件（PaddleOCR 需要文件路径）
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name)
                    tmp_path = tmp.name

                try:
                    result = ocr.ocr(tmp_path, cls=True)
                    if result and result[0]:
                        lines = []
                        for line in result[1]:
                            text = line[1][0]  # (bbox, (text, confidence))
                            lines.append(text)
                        page_text = "\n".join(lines)
                    else:
                        page_text = ""
                finally:
                    os.unlink(tmp_path)

                pages_text.append((i + 1, page_text))

            flags.append("ocr_extracted")
            return pages_text, flags

        except Exception as e:
            logger.error(f"PaddleOCR failed: {e}")
            flags.append("paddleocr_exception")
            return [], flags
```

### 4.3 集成到 fallback 链路

```python
def __init__(self, storage=None):
    self.storage = storage or get_storage()
    self._adapters: list[ParserAdapter] = [
        PyMuPDF4LLMAdapter(),  # 首选：GNN 版面分析
        PdfPlumberAdapter(),
        PyMuPDFAdapter(),
        PdfMinerAdapter(),
        PaddleOCRAdapter(),   # OCR fallback
        DoclingAdapter(),     # 最终兜底
    ]
```

`_extract_with_fallback` 的逻辑不需要改——它已经按顺序遍历适配器列表，前面的失败了自动尝试下一个。

### 4.4 触发条件

PaddleOCR 只在以下情况触发：
1. pdfplumber 和 PyMuPDF 都提取到乱码（`garbled_text_detected`）
2. pdfplumber 和 PyMuPDF 都提取为空文本（扫描件）

正常 PDF 不会触发 OCR，避免不必要的性能开销。

---

## 5. T4.21：扫描件 OCR

### 5.1 扫描件检测增强

当前 `_detect_scanned_pdf` 已存在但未集成到 fallback 链路。增强版本：

```python
def _detect_scanned_pdf(self, pdf_path: str) -> dict[str, Any]:
    """检测 PDF 是否为扫描件

    Returns:
        {"is_scanned": bool, "confidence": float, "image_pages": int, "text_pages": int}
    """
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return {"is_scanned": False, "confidence": 0, "image_pages": 0, "text_pages": 0}

        image_pages = 0
        text_pages = 0

        for i in range(total_pages):
            page = doc[i]
            text = page.get_text("text").strip()
            images = page.get_images()

            # 判据：文本少于 50 字符且有图片 → 图片页
            if len(text) < 50 and len(images) > 0:
                image_pages += 1
            elif len(text) >= 50:
                text_pages += 1

        doc.close()

        # 超过 70% 的页面是图片页且文本页很少 → 扫描件
        if total_pages > 0:
            image_ratio = image_pages / total_pages
            if image_ratio > 0.7 and text_pages < total_pages * 0.3:
                return {
                    "is_scanned": True,
                    "confidence": image_ratio,
                    "image_pages": image_pages,
                    "text_pages": text_pages,
                }

        return {"is_scanned": False, "confidence": 0, "image_pages": image_pages, "text_pages": text_pages}
    except Exception:
        return {"is_scanned": False, "confidence": 0, "image_pages": 0, "text_pages": 0}
```

### 5.2 集成到 fallback

```python
def _extract_with_fallback(self, pdf_path):
    quality_flags = []

    # 先检测扫描件
    scan_result = self._detect_scanned_pdf(pdf_path)
    if scan_result["is_scanned"]:
        quality_flags.append("scanned_pdf_suspected")
        # 扫描件直接走 OCR
        if PaddleOCRAdapter().can_parse(pdf_path):
            pages_text, ocr_flags = PaddleOCRAdapter().extract_pages(pdf_path)
            quality_flags.extend(ocr_flags)
            if pages_text:
                return pages_text, "paddleocr", quality_flags
        return [], "none", quality_flags

    # 正常 fallback 链路
    for adapter in self._adapters:
        # ... 现有逻辑 ...
```

---

## 6. T4.22：pdfminer.six 第三解析器

### 6.1 适配器实现

```python
class PdfMinerAdapter:
    """pdfminer.six 解析器适配器（内置 CMap 数据库）"""
    name = "pdfminer"

    def can_parse(self, pdf_path: str) -> bool:
        try:
            from pdfminer.high_level import extract_text  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        flags = []
        try:
            from pdfminer.high_level import extract_text
            from pdfminer.pdfpage import PDFPage

            # 获取页数
            with open(pdf_path, 'rb') as f:
                page_count = sum(1 for _ in PDFPage.get_pages(f))

            pages_text = []
            for i in range(page_count):
                # 按页提取（page_numbers 参数从 0 开始）
                text = extract_text(pdf_path, page_numbers=[i], codec='utf-8')
                pages_text.append((i + 1, text or ""))

            return pages_text, flags
        except Exception as e:
            logger.error(f"pdfminer failed: {e}")
            flags.append("pdfminer_exception")
            return [], flags
```

### 6.2 为什么需要 pdfminer

pdfminer.six 内置 Adobe 的 CMap 数据库（Adobe-GB1 等），对部分 CID 字体编码的 PDF 有比 PyMuPDF 更好的解码能力。作为 PyMuPDF 和 PaddleOCR 之间的中间 fallback。

---

## 7. T4.23：GROBID Docker 适配器

### 7.1 为什么需要 GROBID

GROBID 是学术论文元数据提取的事实标准，核心优势：
- 参考文献解析精度最高（F1 90%+）
- 输出结构化 TEI XML
- 被 Semantic Scholar 用于处理 2 亿+ 论文

### 7.2 适配器实现

```python
class GROBIDAdapter:
    """GROBID 解析器适配器（需要 Docker 运行 GROBID 服务）"""
    name = "grobid"

    def __init__(self, base_url: str = "http://localhost:8070"):
        self.base_url = base_url

    def can_parse(self, pdf_path: str) -> bool:
        """检查 GROBID 服务是否可用"""
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.base_url}/api/isalive")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        """调用 GROBID processFulltextDocument API

        GROBID 输出 TEI XML，解析后提取：
        - 标题、作者、摘要
        - 章节结构（head/div）
        - 参考文献列表（biblStruct）
        - 正文段落（p）
        """
        flags = []
        try:
            import urllib.request
            import xml.etree.ElementTree as ET

            # 调用 GROBID API
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()

            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            body = (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="input"; filename="paper.pdf"\r\n'
                f'Content-Type: application/pdf\r\n\r\n'
            ).encode() + pdf_data + f'\r\n--{boundary}--\r\n'.encode()

            req = urllib.request.Request(
                f"{self.base_url}/api/processFulltextDocument",
                data=body,
                headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
                method='POST',
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                tei_xml = resp.read().decode('utf-8')

            # 解析 TEI XML
            pages_text = self._parse_tei_xml(tei_xml)
            flags.append("grobid_extracted")
            return pages_text, flags

        except Exception as e:
            logger.error(f"GROBID failed: {e}")
            flags.append("grobid_exception")
            return [], flags

    def _parse_tei_xml(self, tei_xml: str) -> list[tuple[int, str]]:
        """从 TEI XML 提取文本，保留章节结构"""
        import xml.etree.ElementTree as ET

        # TEI XML 命名空间
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

        try:
            root = ET.fromstring(tei_xml)
        except ET.ParseError:
            return []

        pages_text = []
        page_num = 1

        # 提取正文
        body = root.find('.//tei:body', ns)
        if body is not None:
            for div in body.findall('.//tei:div', ns):
                # 章节标题
                head = div.find('tei:head', ns)
                section_title = head.text.strip() if head is not None and head.text else ""

                # 段落文本
                paragraphs = []
                if section_title:
                    paragraphs.append(section_title)
                for p in div.findall('tei:p', ns):
                    text = ''.join(p.itertext()).strip()
                    if text:
                        paragraphs.append(text)

                if paragraphs:
                    pages_text.append((page_num, "\n".join(paragraphs)))
                    page_num += 1

        return pages_text if pages_text else [(1, "")]
```

### 7.3 GROBID 特殊用法

GROBID 不加入默认 fallback 链路（需要 Docker 服务），而是作为**可选增强**：

```python
def parse_paper_with_grobid(self, paper_id: str) -> dict[str, Any]:
    """使用 GROBID 增强解析（元数据 + 参考文献）"""
    # 1. 正常解析获取 chunks
    result = self.parse_paper(paper_id)

    # 2. 如果 GROBID 可用，用它补充元数据和参考文献
    grobid = GROBIDAdapter()
    if grobid.can_parse(paper.pdf_path):
        # GROBID 的参考文献解析精度远高于正则
        refs = self._extract_references_via_grobid(paper.pdf_path)
        if refs:
            self._save_references(paper_id, refs)
```

---

## 8. T4.24：公式区域检测

### 8.1 技术路线

公式处理分两步：
1. **检测**：区分文本块和公式区域
2. **识别**：将公式图像转为 LaTeX

当前阶段只做检测和标记，不做 LaTeX 识别（需要 GPU）。

### 8.2 基于规则的公式检测

```python
def _detect_formula_regions(self, page) -> list[tuple[float, float, float, float]]:
    """检测页面中的公式区域（规则方法）

    公式特征：
    1. 包含数学符号（∑∫∂∇αβγ...）
    2. 独立成行且居中
    3. 字体与正文不同（通常用 MathFont/Symbol）
    """
    import pymupdf

    formula_regions = []
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if "lines" not in block:
            continue

        for line in block["lines"]:
            line_text = ""
            math_font = False

            for span in line["spans"]:
                line_text += span["text"]
                font_name = span["font"].lower()
                # 数学字体特征
                if any(kw in font_name for kw in ["math", "symbol", "cmmi", "cmsy", "cmr"]):
                    math_font = True

            # 检测数学符号
            math_chars = sum(1 for c in line_text if ord(c) in range(0x2200, 0x22FF)  # 数学运算符
                             or ord(c) in range(0x0370, 0x03FF)  # 希腊字母
                             or c in '∑∫∂∇∞±×÷√≈≠≤≥∈∉⊂⊃∪∩')
            has_math = math_chars > 0 or math_font

            # 独立成行且短（< 100 字符）且包含数学符号 → 公式行
            if has_math and len(line_text.strip()) < 100 and len(line_text.strip()) > 2:
                bbox = line["bbox"]
                formula_regions.append(bbox)

    return formula_regions
```

### 8.3 后续升级路径

| 阶段 | 方案 | 工具 | 需要 |
|------|------|------|------|
| 当前 | 规则检测，标记 formula chunk | PyMuPDF | 无额外依赖 |
| P2 | 公式区域裁剪 → LaTeX 识别 | pix2tex | pip install pix2tex |
| P3 | 端到端公式+文本 | MinerU (UniMERNet) | GPU |

---

## 9. T4.25：表格结构化提取

### 9.1 PyMuPDF 内置表格提取

```python
def _extract_tables(self, page) -> list[dict]:
    """使用 PyMuPDF 内置表格提取"""
    tables = page.find_tables()

    result = []
    for table in tables:
        # table.extract() 返回二维列表
        data = table.extract()
        if not data:
            continue

        result.append({
            "bbox": table.bbox,
            "rows": len(data),
            "cols": len(data[0]) if data else 0,
            "data": data,
            "header": data[0] if data else [],
        })

    return result
```

### 9.2 pdfplumber 表格提取

```python
def _extract_tables_pdfplumber(self, pdf_path: str) -> list[dict]:
    """使用 pdfplumber 提取表格（有线表效果好）"""
    import pdfplumber

    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                all_tables.append({
                    "page": i + 1,
                    "rows": len(table),
                    "cols": len(table[0]) if table else 0,
                    "data": table,
                })

    return all_tables
```

### 9.3 跨页表格合并

```python
def _merge_cross_page_tables(self, tables: list[dict]) -> list[dict]:
    """跨页表格合并

    检测条件：
    1. 相邻页的表格
    2. 列数相同
    3. 列 x 坐标对齐（容差 ±3pt）
    4. 前一页表格在页底，后一页表格在页顶
    """
    if len(tables) < 2:
        return tables

    merged = []
    skip = set()

    for i in range(len(tables) - 1):
        if i in skip:
            continue

        t1 = tables[i]
        t2 = tables[i + 1]

        # 检查是否可合并
        if (t1.get("cols") == t2.get("cols")
            and t1.get("page", 0) + 1 == t2.get("page", 0)):
            # 检查表头是否重复
            header1 = t1["data"][0] if t1["data"] else []
            header2 = t2["data"][0] if t2["data"] else []

            if header1 == header2:
                # 跳过重复表头，合并数据
                merged_data = t1["data"] + t2["data"][1:]
            else:
                merged_data = t1["data"] + t2["data"]

            merged.append({
                "page": t1["page"],
                "rows": len(merged_data),
                "cols": t1["cols"],
                "data": merged_data,
                "cross_page": True,
            })
            skip.add(i + 1)
        else:
            merged.append(t1)

    if len(tables) - 1 not in skip:
        merged.append(tables[-1])

    return merged
```

---

## 10. T4.26：Contextual Retrieval

### 10.1 原理（Anthropic 研究数据）

Anthropic 提出的 Contextual Retrieval 是当前最先进的 RAG 检索优化方案：

**问题**：传统 RAG 将文档切块后独立编码，丢失了块与文档整体的上下文关系。

**解决方案**（三层递进）：
1. **Contextual Embeddings**：在每个 chunk 编码前，prepend 一段描述该 chunk 在文档中位置和含义的上下文摘要
2. **BM25 混合检索**：将语义向量检索与 BM25 关键词检索结合
3. **Reranking**：对混合检索结果进行重排序

**效果**（Anthropic 官方数据）：
- 仅用 Contextual Embeddings → 减少 35% 失败检索
- + BM25 混合 → 减少 49% 失败检索
- + Reranking → 减少 67% 失败检索

**对本模块的意义**：解析阶段是构建 chunk 上下文的最佳时机——此时论文元数据（标题、作者、摘要、章节结构）已知，且不影响检索时延。

### 10.2 实现

对学术论文，上下文可以是：
- 论文标题 + 作者
- 当前章节名称
- 前一个 chunk 的尾部（已有 overlap）
- 论文摘要的简短版本

```python
def _build_chunk_context(self, chunk_text: str, paper: Paper, section_type: str) -> str:
    """为 chunk 构建上下文前缀（Contextual Retrieval）

    不需要 LLM，使用结构化元数据拼接。
    这是 Anthropic Contextual Embeddings 的简化版：
    - Anthropic 方案：用 LLM 生成上下文摘要（效果最好，但有成本和时延）
    - 本方案：用结构化元数据拼接（零成本，零时延，覆盖 80% 效果）

    参考：Anthropic Contextual Retrieval
      - Contextual Embeddings 减少 35% 失败检索
      - + BM25 混合减少 49%
      - + Reranking 减少 67%
    """
    parts = []

    # 论文标识
    if paper.title:
        parts.append(f"Paper: {paper.title}")
    if paper.authors:
        author_names = ", ".join(a.name for a in paper.authors[:3])
        parts.append(f"Authors: {author_names}")

    # 章节标识
    if section_type:
        parts.append(f"Section: {section_type}")

    # 组装
    context = " | ".join(parts)
    return f"[{context}]\n\n{chunk_text}" if context else chunk_text
```

### 10.3 集成

在 `_flush_buffer` 中构建 chunk 时添加上下文：

```python
def _make_chunk(self, paper_id, chunk_index, section_type, chunk_type,
                text, char_offset, page_start, page_end):
    # 获取论文信息用于上下文
    paper_item = self.storage.get_item("papers", paper_id)
    if paper_item:
        paper = Paper(**paper_item)
        text = self._build_chunk_context(text, paper, section_type)

    return {
        "chunk_id": f"chunk_{paper_id}_{chunk_index:04d}",
        "paper_id": paper_id,
        "text": text,
        # ... 其他字段 ...
    }
```

### 10.4 与下游模块的关系

| 下游消费者 | 如何使用上下文 chunk |
| --- | --- |
| embedding_service | 上下文前缀随 chunk 文本一起编码，提升语义检索精度 |
| vector_storage | 上下文前缀存储在 chunk.text 中，检索时自动包含 |
| search_chunks | 检索命中 child chunk，返回 parent chunk（含上下文），给 LLM 更多语境 |
| 论文卡片生成 | 上下文前缀帮助 LLM 准确识别 chunk 所属论文和章节 |
| 证据表抽取 | 上下文前缀帮助 LLM 准确归因 evidence 到正确的论文和章节 |

### 10.5 升级路径

| 阶段 | 方案 | 成本 | 效果 |
| --- | --- | --- | --- |
| 当前（P1） | 结构化元数据拼接（标题+作者+章节） | 零 | 覆盖 80% 场景 |
| P2 | LLM 生成上下文摘要（Anthropic 完整方案） | ~$0.001/chunk | 覆盖 95% 场景 |
| P3 | Contextual Embeddings + BM25 + Reranking | 需要向量库支持 | 减少 67% 失败检索 |

---

## 11. T4.27：分块后去重

### 11.1 问题

当前 `ChunkCleaner.clean()` 只做噪声行过滤和碎片合并，没有去重。实际场景中存在：
- 跨页重复的页眉/水印文本被分到不同 chunk
- 同一论文中重复出现的表格标题、图注
- 跨论文的通用方法描述（如相同的实验设置段落）

### 11.2 技术方案：MinHash + 余弦双层去重

根据调研（FineWeb/Dolma/NeMo Curator），采用分层去重策略：

```python
class ChunkDeduplicator:
    """分块后去重：精确哈希 → 近似 MinHash → 余弦相似度"""

    def __init__(self, jaccard_threshold: float = 0.8, cosine_threshold: float = 0.9):
        self.jaccard_threshold = jaccard_threshold
        self.cosine_threshold = cosine_threshold

    def deduplicate(self, chunks: list[dict]) -> list[dict]:
        """三层去重管线"""
        # 第一层：精确哈希去重（SHA256）
        chunks = self._exact_dedup(chunks)
        # 第二层：MinHash 近似去重（Jaccard ≥ 0.8）
        chunks = self._minhash_dedup(chunks)
        # 第三层：余弦相似度过滤（cosine ≥ 0.9）
        chunks = self._cosine_dedup(chunks)
        return chunks

    def _exact_dedup(self, chunks: list[dict]) -> list[dict]:
        """精确哈希去重：完全相同的文本"""
        seen = set()
        result = []
        for c in chunks:
            h = hashlib.sha256(c["text"].encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                result.append(c)
        return result

    def _minhash_dedup(self, chunks: list[dict]) -> list[dict]:
        """MinHash 近似去重：Jaccard ≥ threshold 的近似重复"""
        try:
            from datasketch import MinHash, MinHashLSH
        except ImportError:
            return chunks  # datasketch 不可用时跳过

        lsh = MinHashLSH(threshold=self.jaccard_threshold, num_perm=128)
        result = []

        for i, c in enumerate(chunks):
            m = MinHash(num_perm=128)
            # 5-gram 分词
            text = c["text"].lower()
            for j in range(len(text) - 4):
                m.update(text[j:j+5].encode("utf8"))

            # 查询是否有近似重复
            duplicates = lsh.query(m)
            if not duplicates:
                lsh.insert(f"chunk_{i}", m)
                result.append(c)
            # 否则跳过（保留首次出现的 chunk）

        return result

    def _cosine_dedup(self, chunks: list[dict]) -> list[dict]:
        """TF-IDF 余弦相似度去重：≥ threshold 的语义重复

        参考 ChunkRAG 方案：对 chunk 文本做 TF-IDF 向量化，
        计算两两余弦相似度，≥ 0.9 的对中移除较短者。
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        if len(chunks) < 2:
            return chunks

        texts = [c["text"] for c in chunks]
        vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(texts)

        # 两两相似度
        sim_matrix = cosine_similarity(tfidf_matrix)
        to_remove = set()

        for i in range(len(chunks)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(chunks)):
                if j in to_remove:
                    continue
                if sim_matrix[i][j] >= self.cosine_threshold:
                    # 移除较短的 chunk
                    if len(chunks[i]["text"]) < len(chunks[j]["text"]):
                        to_remove.add(i)
                    else:
                        to_remove.add(j)

        return [c for i, c in enumerate(chunks) if i not in to_remove]
```

### 11.3 集成位置

在 `ChunkCleaner.clean()` 末尾，碎片合并之后：

```python
def clean(self, chunks: list[dict]) -> list[dict]:
    """完整清洗管线"""
    chunks = self._filter_noise_lines(chunks)
    chunks = self._merge_fragments(chunks)
    chunks = self._deduplicate(chunks)       # 新增
    chunks = self._update_token_counts(chunks)
    return chunks
```

### 11.4 性能考虑

| 方法 | 时间复杂度 | 1000 chunks 耗时 | 适用场景 |
|------|-----------|-----------------|---------|
| SHA256 精确 | O(n) | <1ms | 必须做 |
| MinHash LSH | O(n) 插入+查询 | ~100ms (128 perm) | 推荐做 |
| TF-IDF 余弦 | O(n²) 比对 | ~500ms (5000 features) | 可选做 |

MinHash 的 `num_perm=128` 在调研中被 datasketch/NeMo Curator/FineWeb 一致推荐为标准值。

---

## 12. T4.28：分块质量评分与过滤

### 12.1 问题

当前 `ChunkCleaner` 只过滤公式行和合并碎片，没有对 chunk 整体质量打分。低质量 chunk 进入向量库后会：
- 污染检索结果（调研发现：95% 的退化案例中 LLM 被噪声 chunk 误导）
- 浪费 embedding 计算
- 降低 RAG 整体准确率

### 12.2 质量评分维度

```python
class ChunkQualityScorer:
    """分块质量评分器"""

    # 评分权重
    WEIGHTS = {
        "length_score": 0.25,
        "info_density": 0.25,
        "structure_score": 0.20,
        "language_score": 0.15,
        "noise_score": 0.15,
    }

    def score(self, chunk: dict) -> dict:
        """计算 chunk 质量分，返回 0-1 分数和各维度详情"""
        text = chunk.get("text", "")
        scores = {
            "length_score": self._score_length(text),
            "info_density": self._score_info_density(text),
            "structure_score": self._score_structure(text),
            "language_score": self._score_language(text),
            "noise_score": self._score_noise(text),
        }
        weighted = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        return {"quality_score": round(weighted, 3), "details": scores}

    def _score_length(self, text: str) -> float:
        """长度评分：过短过长都扣分"""
        tokens = len(text.split())
        if tokens < 30:
            return 0.2   # 过短
        if tokens < 50:
            return 0.5
        if tokens <= 1000:
            return 1.0   # 理想范围
        if tokens <= 1500:
            return 0.8
        return 0.5        # 过长

    def _score_info_density(self, text: str) -> float:
        """信息密度：停用词占比、实体密度、词汇多样性"""
        words = text.lower().split()
        if not words:
            return 0.0
        # 词汇多样性（unique / total）
        diversity = len(set(words)) / len(words)
        # 非停用词占比（简化版）
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on",
                     "at", "to", "for", "of", "with", "and", "or", "but", "not"}
        content_ratio = sum(1 for w in words if w not in stopwords) / len(words)
        return min(1.0, (diversity * 0.5 + content_ratio * 0.5) * 1.5)

    def _score_structure(self, text: str) -> float:
        """结构评分：是否包含有意义的句子结构"""
        has_sentence = bool(re.search(r'[.!?。！？]\s', text))
        has_paragraph = '\n\n' in text or text.count('\n') > 3
        score = 0.5
        if has_sentence:
            score += 0.3
        if has_paragraph:
            score += 0.2
        return min(1.0, score)

    def _score_language(self, text: str) -> float:
        """语言一致性评分：中英文混杂扣分"""
        if not text:
            return 0.0
        cn_chars = sum(1 for c in text if '一' <= c <= '鿿')
        en_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total = cn_chars + en_chars
        if total == 0:
            return 0.0
        # 纯中文或纯英文得高分，混杂扣分
        ratio = max(cn_chars, en_chars) / total
        return ratio

    def _score_noise(self, text: str) -> float:
        """噪声评分：噪声越少分越高（反向）"""
        lines = text.split('\n')
        noise_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # 公式行
            math_chars = sum(1 for c in stripped if c in "∑∫∂∇αβγδεζηθ∈∉⊂⊃∪∩≈≠≤≥∞±×÷")
            if len(stripped) > 0 and math_chars / len(stripped) > 0.2:
                noise_count += 1
            # 纯数字行
            elif stripped.replace(' ', '').isdigit():
                noise_count += 1
            # 过短行（< 5 字符，非标题）
            elif len(stripped) < 5 and not re.match(r'^\d+\.', stripped):
                noise_count += 1
        noise_ratio = noise_count / max(len(lines), 1)
        return max(0.0, 1.0 - noise_ratio * 3)
```

### 12.3 质量过滤阈值

```python
def filter_low_quality(self, chunks: list[dict], min_score: float = 0.3) -> list[dict]:
    """过滤低质量 chunk"""
    scorer = ChunkQualityScorer()
    result = []
    for c in chunks:
        score_result = scorer.score(c)
        c["quality_score"] = score_result["quality_score"]
        c["quality_details"] = score_result["details"]
        if c["quality_score"] >= min_score:
            result.append(c)
    return result
```

根据调研（NAACL 2025, MAIN-RAG），建议默认阈值 0.3（宽松），实际部署时根据检索效果调优。

---

## 13. T4.29：Chunk 冗余检测与剔除

### 13.1 问题

去重（T4.27）处理的是高度相似的 chunk，但还存在"相关但冗余"的情况：
- 同一 section 的不同段落讨论相似内容
- 方法描述和实验部分有重复的方法名
- 讨论部分重复了结果部分的数据

### 13.2 ChunkRAG 方案

调研发现 ChunkRAG（arXiv 2025）的方案最适合：

```python
class ChunkRedundancyFilter:
    """Chunk 冗余过滤：TF-IDF + 动态阈值"""

    def __init__(self, redundancy_threshold: float = 0.85):
        self.threshold = redundancy_threshold

    def filter(self, chunks: list[dict]) -> list[dict]:
        """移除冗余 chunk，保留信息量更大的那个"""
        if len(chunks) < 2:
            return chunks

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        texts = [c["text"] for c in chunks]
        vectorizer = TfidfVectorizer(max_features=3000)
        tfidf = vectorizer.fit_transform(texts)
        sim = cosine_similarity(tfidf)

        to_remove = set()
        for i in range(len(chunks)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(chunks)):
                if j in to_remove:
                    continue
                if sim[i][j] >= self.threshold:
                    # 冗余对：保留更长的（信息量更大）
                    if len(chunks[i]["text"]) < len(chunks[j]["text"]):
                        to_remove.add(i)
                        break
                    else:
                        to_remove.add(j)

        return [c for i, c in enumerate(chunks) if i not in to_remove]
```

### 13.3 与去重的区别

| 维度 | T4.27 去重 | T4.29 冗余过滤 |
|------|-----------|---------------|
| 阈值 | Jaccard ≥ 0.8 / Cosine ≥ 0.9 | Cosine ≥ 0.85 |
| 目标 | 移除近似重复 | 移除语义冗余 |
| 时机 | 分块后立即做 | 可选，去重之后 |
| 策略 | 保留首次出现 | 保留信息量更大的 |
| 依赖 | datasketch + sklearn | sklearn |

### 13.4 集成到 ChunkCleaner

```python
def clean(self, chunks: list[dict]) -> list[dict]:
    """完整清洗管线"""
    chunks = self._filter_noise_lines(chunks)
    chunks = self._merge_fragments(chunks)
    chunks = self._deduplicate(chunks)            # T4.27
    chunks = self._filter_low_quality(chunks)     # T4.28
    chunks = self._filter_redundancy(chunks)      # T4.29
    chunks = self._update_token_counts(chunks)
    return chunks
```

---

## 14. 完整 fallback 链路设计

### 14.1 目标架构

```
PDF 输入
    │
    ▼
[0] 扫描件预检测
    │
    ├── 是扫描件 → PaddleOCR → 返回
    │
    └── 非扫描件
        │
        ▼
[1] PdfPlumberAdapter
    │
    ├── 成功且无乱码 → 文本后处理 → 返回
    ├── 成功但乱码 → 记录，继续
    └── 失败/空 → 记录，继续
        │
        ▼
[2] PyMuPDFAdapter（含双栏重排）
    │
    ├── 成功且无乱码 → 文本后处理 → 返回
    ├── 成功但乱码 → 记录，继续
    └── 失败/空 → 记录，继续
        │
        ▼
[3] PdfMinerAdapter
    │
    ├── 成功且无乱码 → 文本后处理 → 返回
    ├── 成功但乱码 → 记录，继续
    └── 失败/空 → 记录，继续
        │
        ▼
[4] PaddleOCRAdapter
    │
    ├── 成功 → 返回
    └── 失败 → 标记 failed
```

### 14.2 实现

```python
def _extract_with_fallback(self, pdf_path: str) -> tuple[list[tuple[int, str]], str, list[str]]:
    quality_flags: list[str] = []

    # 阶段 0：扫描件预检测
    scan_result = self._detect_scanned_pdf(pdf_path)
    if scan_result["is_scanned"]:
        quality_flags.append("scanned_pdf_suspected")
        quality_flags.append(f"scan_confidence={scan_result['confidence']:.2f}")
        # 扫描件直接走 OCR
        ocr_adapter = PaddleOCRAdapter()
        if ocr_adapter.can_parse(pdf_path):
            pages_text, ocr_flags = ocr_adapter.extract_pages(pdf_path)
            quality_flags.extend(ocr_flags)
            if pages_text and any(t.strip() for _, t in pages_text):
                return pages_text, "paddleocr", quality_flags
        quality_flags.append("ocr_failed")
        return [], "none", quality_flags

    # 阶段 1-3：文本提取器 fallback
    text_adapters = [
        PdfPlumberAdapter(),
        PyMuPDFAdapter(),
        PdfMinerAdapter(),
    ]

    for adapter in text_adapters:
        if not adapter.can_parse(pdf_path):
            quality_flags.append(f"{adapter.name}_unavailable")
            continue

        pages_text, flags = adapter.extract_pages(pdf_path)
        quality_flags.extend(flags)

        if not pages_text or not any(t.strip() for _, t in pages_text):
            quality_flags.append(f"{adapter.name}_empty")
            continue

        # 乱码检测
        full_text = "\n".join(t for _, t in pages_text)
        if self._detect_garbled_text(full_text):
            quality_flags.append(f"{adapter.name}_garbled")
            continue

        # 成功
        return pages_text, adapter.name, quality_flags

    # 阶段 4：OCR 最终 fallback
    ocr_adapter = PaddleOCRAdapter()
    if ocr_adapter.can_parse(pdf_path):
        pages_text, ocr_flags = ocr_adapter.extract_pages(pdf_path)
        quality_flags.extend(ocr_flags)
        if pages_text and any(t.strip() for _, t in pages_text):
            quality_flags.append("ocr_fallback_used")
            return pages_text, "paddleocr", quality_flags

    quality_flags.append("all_adapters_failed")
    return [], "none", quality_flags
```

---

## 15. 质量评估指标

### 15.1 定义

| 指标 | 计算方式 | 目标阈值 |
|-----|---------|---------|
| 文本提取率 | 提取字符数 / 预期字符数 | > 80% |
| 乱码率 | PUA 字符数 / 总字符数 | < 5% |
| 章节覆盖率 | 检测到的 section_type 数 / 预期 section 数 | > 60% |
| 参考文献识别率 | 识别的 ref 条目数 / 实际 ref 数 | > 80% |
| 处理成功率 | 成功解析 / 总数 | > 95% |
| 单篇处理时间 | — | < 30s (CPU, 非 OCR) |

### 15.2 诊断数据

`ParseResult.diagnostics` 中记录：

```python
diagnostics = {
    "total_chars": 12345,
    "total_pages": 15,
    "garbled_text": False,
    "watermark": True,
    "dual_column": True,
    "low_section_coverage": False,
    "post_processing": {
        "ligatures_fixed": 3,
        "hyphens_fixed": 12,
        "citations_reconnected": 5,
        "headers_removed": ["Journal of XYZ"],
    },
    "adapter_used": "pymupdf",
    "fallback_chain": ["pdfplumber_empty", "pymupdf_success"],
    "processing_time_ms": 2340,
}
```

---

## 16. 开发任务清单

### P1（近期）—— 已大部分完成

| 任务 | 说明 | 状态 | 预估 |
|------|------|------|------|
| T4.18 版面感知与阅读顺序 | 双栏检测+重排（基础版） | ✅ 已完成 | — |
| T4.18+ 版面感知升级 | PyMuPDF4LLMAdapter（GNN，首选解析器） | ✅ 已完成 | — |
| T4.19 文本后处理管线 | TextPostProcessor（7 项修复） | ✅ 已完成 | — |
| T4.22 pdfminer.six 适配器 | PdfMinerAdapter 第三解析器 | ✅ 已完成 | — |
| T4.27 分块后去重 | ChunkDeduplicator（SHA256+MinHash+BM25） | ✅ 已完成 | — |
| T4.28 分块质量评分 | ChunkQualityScorer（5维评分） | ✅ 已完成 | — |
| T4.29 Chunk 冗余过滤 | ChunkRedundancyFilter（BM25+动态阈值） | ✅ 已完成 | — |
| Parent-Child 分块 | _create_parent_chunks（~2000 token 父块） | ✅ 已完成 | — |
| Docling 适配器 | DoclingAdapter（降级为兜底） | ✅ 已完成 | — |
| T4.26 Contextual Retrieval | chunk 上下文前缀（结构化元数据版） | ❌ 未开始 | 2h |

### P2（中期）

| 任务 | 说明 | 依赖 | 预估 |
|------|------|------|------|
| T4.18+ 版面感知升级 | pymupdf4llm GNN 版面分析 + XY-Cut++ 备选 | pip install pymupdf4llm | 3h |
| T4.20 PaddleOCR fallback | 中文 PDF 乱码最终方案 | pip install paddleocr pdf2image | 3h |
| T4.21 扫描件 OCR | 扫描件预检测 + OCR fallback | T4.20 | 1h |
| T4.24 公式区域检测 | 规则方法检测公式行 | 无 | 2h |
| T4.25 表格提取 | PyMuPDF + pdfplumber 表格提取 | 无 | 2h |
| 测试补充 | pymupdf4llm、OCR、公式、表格 | T4.18+-T4.25 | 3h |

### P3（远期）

| 任务 | 说明 | 依赖 | 预估 |
|------|------|------|------|
| T4.23 GROBID 适配器 | Docker 服务调用 + TEI XML 解析 | Docker | 4h |
| 公式 LaTeX 识别 | pix2tex 集成 | pip install pix2tex | 3h |
| 跨页表格合并 | 表头检测 + 列坐标对齐 | T4.25 | 2h |
| MinerU 适配器 | 一站式学术 PDF 解析 | GPU | 4h |
| LLM 上下文摘要 | Anthropic Contextual Retrieval 完整方案 | LLM API | 3h |

---

## 17. 验收标准

```text
1. 双栏 PDF 文本按正确阅读顺序排列（当前基线已达标）
2. 中文知网 PDF 乱码自动触发 OCR fallback（P2 完成后达标）
3. 合字、连字符、引用标记被正确修复（已达标）
4. 页眉页脚被自动去除（已达标）
5. 扫描件 PDF 通过 OCR 提取文本（P2 完成后达标）
6. 分块后自动去重（SHA256 + MinHash + BM25，已达标）
7. 低质量 chunk 被标记或过滤（quality_score < 0.3，已达标）
8. 冗余 chunk 被剔除（BM25 ≥ 0.85，已达标）
9. Parent-Child 分块正常工作（已达标）
10. Contextual Retrieval 前缀正确添加（P1 完成后达标）
11. 所有现有测试继续通过
12. 新增测试覆盖：pymupdf4llm、OCR fallback、公式检测、表格提取
```

---

## 18. 研究借鉴增强

### 18.1 Contextual Retrieval 准备（T4.26）

**来源**：Anthropic Contextual Retrieval 研究

解析模块是构建 chunk 上下文的最佳时机。当前 `_make_chunk` 未添加上下文前缀，需要实现：

```python
# 当前 _make_chunk 的 text 字段是纯 chunk 文本
# 需要添加上下文前缀：
# [Paper: {title} | Authors: {authors} | Section: {section_type}]
#
# 这是 Anthropic Contextual Embeddings 的简化版：
# - Anthropic 方案：用 LLM 生成上下文摘要（效果最好，但有成本和时延）
# - 本方案：用结构化元数据拼接（零成本，零时延，覆盖 80% 效果）
```

**与搜索模块的协作**：
- 解析模块生成 chunk 时添加上下文前缀
- 搜索模块的 hybrid_ranker 在检索时利用上下文前缀提升精度
- 向量存储的 embedding 包含上下文信息

### 18.2 GROBID 参考文献增强（T4.23）

**来源**：GROBID 官方文档 + Literature Mapper

GROBID 是学术论文元数据提取的事实标准：
- 参考文献解析精度最高（F1 90%+）
- 输出结构化 TEI XML
- 被 Semantic Scholar 用于处理 2 亿+ 论文

**与知识图谱的关系**：
- GROBID 解析的参考文献 → 构建 Paper CITES Paper 关系
- 识别 ghost papers（被引用但不在库中的论文）→ Literature Mapper 的 gap detection
- 参考文献列表 → 支撑引用网络分析（Inciteful 链接预测）

### 18.3 解析诊断与透明报告（PRISMA-trAIce）

**来源**：PRISMA-trAIce AI 辅助 SR 透明报告检查清单

解析诊断数据应支持可追溯性：
- 哪个解析器成功了（adapter_used）
- fallback 链路是什么（fallback_chain）
- 质量标记有哪些（quality_flags）
- 后处理修复了什么（post_processing）
- 处理耗时多少（processing_time_ms）

当前 `ParseResult.diagnostics` 已记录大部分信息，可直接用于 PRISMA-trAIce 风格的透明报告。

### 18.4 分块质量与幻觉检测的关系

**来源**：LettuceDetect + Vectara Hallucination Leaderboard

分块质量直接影响下游幻觉率：
- 低质量 chunk（噪声多、信息密度低）→ 检索结果不准确 → LLM 基于噪声生成 → 幻觉率上升
- 调研发现：95% 的退化案例中 LLM 被噪声 chunk 误导
- RAG grounding 是减少幻觉的最强单一手段（-75-90%）

**当前 ChunkQualityScorer 的 5 维评分**已覆盖：
- 长度评分（过短过长都扣分）
- 信息密度（停用词占比、词汇多样性）
- 结构评分（是否包含有意义的句子结构）
- 语言一致性（中英文混杂扣分）
- 噪声评分（公式行、纯数字行、过短行）

### 18.5 Parent-Child Chunking 与检索的关系

**来源**：RAGFlow v0.23 Parent-Child Chunking

当前 `_create_parent_chunks` 已实现 parent-child 分块：
- child chunk：~500-900 tokens，用于精确匹配
- parent chunk：~2000 tokens，用于给 LLM 提供上下文
- `search_chunks(return_parent=True)` 已支持返回 parent chunk 文本

**与 RAGFlow 的差距**：
- RAGFlow 的 parent chunk 是按语义边界（段落、章节）划分的
- 当前实现是按 section_type + token 数量聚合的
- 后续可优化：基于段落语义边界而非 token 数量

### 18.6 开发阶段更新

```text
当前阶段：P1 基础完成，P2 准备中
下一步：
  1. 实现 T4.26 Contextual Retrieval（P1 最后一项）
  2. 升级 T4.18 版面感知（pymupdf4llm）
  3. 实现 T4.20 PaddleOCR fallback
  4. 实现 T4.24 公式检测 + T4.25 表格提取
```

---

## 19. 当前代码对齐深化

### 19.1 已实现但计划中未反映的能力

| 能力 | 代码位置 | 说明 |
| --- | --- | --- |
| PyMuPDF4LLMAdapter | parser_service.py:223-258 | GNN 版面分析，首选解析器，速度 3x/内容量 3x 优于 Docling |
| DoclingAdapter | parser_service.py:261-302 | 降级为兜底解析器 |
| fix_word_spacing | TextPostProcessor:302-317 | 修复 PDF 提取中丢失的单词间距 |
| fix_cid_artifacts | TextPostProcessor:291-293 | 移除 pdfplumber 的 CID 伪影 |
| _detect_poor_spacing | parser_service.py | 单词间距质量检测，触发下一个适配器 |
| _detect_scanned_pdf | parser_service.py:1822-1860 | 扫描件预检测（图片页比例 > 70%） |
| embed_paper | parser_service.py:1235-1274 | 向量化 chunks 并存入 Qdrant |
| search_chunks | parser_service.py:1276-1328 | 向量检索 + parent context 返回 |
| _create_parent_chunks | parser_service.py:1574-1658 | Parent-Child 分块（~2000 token 父块） |
| _migrate_old_chunks | parser_service.py:1677-1699 | 旧格式 chunks 迁移 |

### 19.2 计划中描述但代码中未实现的能力

| 能力 | 计划章节 | 当前状态 | 优先级 |
| --- | --- | --- | --- |
| Contextual Retrieval 前缀 | §10 | `_make_chunk` 未添加上下文 | P1 |
| pymupdf4llm 版面分析 | §2.2 | 只有基础双栏重排 | P2 |
| XY-Cut++ 算法 | §2.3 | 未实现 | P2 |
| PaddleOCR 适配器 | §4 | `_try_ocr_fallback` 只标记 | P2 |
| 公式区域检测 | §8 | 未实现 | P2 |
| 表格结构化提取 | §9 | 未实现 | P2 |
| GROBID 适配器 | §7 | 未实现 | P3 |
