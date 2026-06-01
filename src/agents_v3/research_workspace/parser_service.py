"""论文解析服务 - 增强版"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from loguru import logger

from src.agents_v3.research_workspace.models import (
    ChunkType,
    Paper,
    PaperChunk,
    PaperStatus,
    ParseResult,
    Reference,
)
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


# ── ParserAdapter 协议 ────────────────────────────────────


class ParserAdapter(Protocol):
    """解析器适配器协议"""
    name: str

    def can_parse(self, pdf_path: str) -> bool:
        """检查是否可用"""
        ...

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        """提取每页文本，返回 (pages_text, quality_flags)"""
        ...


class PdfPlumberAdapter:
    """pdfplumber 解析器适配器"""
    name = "pdfplumber"

    def can_parse(self, pdf_path: str) -> bool:
        try:
            import pdfplumber  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        flags: list[str] = []
        try:
            import pdfplumber
        except ImportError:
            flags.append("parser_import_error")
            return [], flags

        try:
            pages_text: list[tuple[int, str]] = []
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages_text.append((i + 1, text))
            return pages_text, flags
        except Exception as e:
            logger.error(f"pdfplumber failed: {e}")
            flags.append("parser_exception")
            return [], flags


class PyMuPDFAdapter:
    """PyMuPDF 解析器适配器（fallback，支持双栏重排）"""
    name = "pymupdf"

    def can_parse(self, pdf_path: str) -> bool:
        try:
            import pymupdf  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        flags: list[str] = []
        try:
            import pymupdf
        except ImportError:
            flags.append("pymupdf_not_available")
            return [], flags

        try:
            pages_text: list[tuple[int, str]] = []
            doc = pymupdf.open(pdf_path)

            for i in range(len(doc)):
                page = doc[i]
                blocks = page.get_text("blocks")
                text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

                if not text_blocks:
                    pages_text.append((i + 1, ""))
                    continue

                page_width = page.rect.width
                boundary = self._find_column_boundary(text_blocks, page_width)

                if boundary is not None:
                    flags.append("dual_column_detected")
                    text = self._reorder_columns(text_blocks, boundary)
                else:
                    text_blocks.sort(key=lambda b: (b[1], b[0]))
                    text = "\n".join(b[4].strip() for b in text_blocks)

                pages_text.append((i + 1, text))

            doc.close()
            return pages_text, flags
        except Exception as e:
            logger.error(f"PyMuPDF failed: {e}")
            flags.append("pymupdf_exception")
            return [], flags

    @staticmethod
    def _find_column_boundary(text_blocks: list, page_width: float) -> float | None:
        """通过空白谷检测找列分界线"""
        valid = [b for b in text_blocks if b[6] == 0 and len(b[4].strip()) > 10]
        if len(valid) < 4:
            return None

        mid = page_width / 2

        # 按文本块中心 x 坐标分为左半和右半
        left_count = sum(1 for b in valid if (b[0] + b[2]) / 2 < mid)
        right_count = sum(1 for b in valid if (b[0] + b[2]) / 2 > mid)

        if left_count < 2 or right_count < 2:
            return None

        balance = min(left_count, right_count) / max(left_count, right_count)
        if balance < 0.3:
            return None

        # 找 x 坐标间隙
        x_coords = sorted(set([b[0] for b in valid]))
        gaps = []
        for j in range(len(x_coords) - 1):
            gap = x_coords[j + 1] - x_coords[j]
            if gap > 20:
                gap_center = (x_coords[j] + x_coords[j + 1]) / 2
                gaps.append((gap, gap_center))

        if not gaps:
            return mid

        gaps.sort(reverse=True)
        for _, gap_center in gaps:
            if abs(gap_center - mid) < page_width * 0.2:
                return gap_center

        return mid

    @staticmethod
    def _reorder_columns(text_blocks: list, boundary: float) -> str:
        """按分栏边界重排文本：全宽 → 左栏 → 右栏"""
        left, right, full = [], [], []
        for b in text_blocks:
            x0, y0, x1, y1, text, *_ = b
            if x1 < boundary + 10:
                left.append(b)
            elif x0 > boundary - 10:
                right.append(b)
            else:
                full.append(b)

        left.sort(key=lambda b: (b[1], b[0]))
        right.sort(key=lambda b: (b[1], b[0]))
        full.sort(key=lambda b: b[1])

        ordered = full + left + right
        return "\n".join(b[4].strip() for b in ordered)


class PdfMinerAdapter:
    """pdfminer.six 解析器适配器（内置 CMap 数据库，CID 字体支持好）"""
    name = "pdfminer"

    def can_parse(self, pdf_path: str) -> bool:
        try:
            from pdfminer.high_level import extract_text  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        flags: list[str] = []
        try:
            from pdfminer.high_level import extract_text
            from pdfminer.pdfpage import PDFPage
        except ImportError:
            flags.append("pdfminer_not_available")
            return [], flags

        try:
            with open(pdf_path, "rb") as f:
                page_count = sum(1 for _ in PDFPage.get_pages(f))

            pages_text: list[tuple[int, str]] = []
            for i in range(page_count):
                text = extract_text(pdf_path, page_numbers=[i], codec="utf-8")
                pages_text.append((i + 1, text or ""))

            return pages_text, flags
        except Exception as e:
            logger.error(f"pdfminer failed: {e}")
            flags.append("pdfminer_exception")
            return [], flags


class PyMuPDF4LLMAdapter:
    """pymupdf4llm 解析器适配器（GNN 版面分析 + 全文档 Markdown 输出）

    基于 PyMuPDF 的图神经网络版面分析，CPU 可用，自动处理多栏阅读顺序。
    测试结果：速度 3x、内容量 3x、章节识别 2.3x，全面优于 Docling。
    """
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
            # page_chunks=True 返回每页文本，保留跨页上下文
            page_data = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
            pages_text: list[tuple[int, str]] = []
            for i, page in enumerate(page_data):
                text = page.get("text", "")
                pages_text.append((i + 1, text))
            flags.append("pymupdf4llm_used")
            return pages_text, flags
        except Exception as e:
            logger.error(f"pymupdf4llm failed: {e}")
            flags.append("pymupdf4llm_exception")
            return [], flags


class DoclingAdapter:
    """Docling 解析器适配器（高质量 Markdown 输出，内置 OCR）"""
    name = "docling"

    def can_parse(self, pdf_path: str) -> bool:
        try:
            from docling.document_converter import DocumentConverter  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_pages(self, pdf_path: str) -> tuple[list[tuple[int, str]], list[str]]:
        flags: list[str] = []
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            flags.append("docling_not_available")
            return [], flags

        try:
            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            num_pages = result.document.num_pages()

            pages_text: list[tuple[int, str]] = []
            for i in range(1, num_pages + 1):
                try:
                    page_result = converter.convert(pdf_path, page_range=(i, i))
                    md = page_result.document.export_to_markdown()
                    pages_text.append((i, md))
                except Exception:
                    pages_text.append((i, ""))
                    flags.append(f"docling_page_{i}_failed")

            flags.append("docling_used")
            return pages_text, flags
        except Exception as e:
            logger.error(f"Docling failed: {e}")
            flags.append("docling_exception")
            return [], flags


class TextPostProcessor:
    """文本后处理管线：修复 PDF 提取中的常见文本问题"""

    LIGATURE_MAP = {
        "ﬀ": "ff",  # ﬀ
        "ﬁ": "fi",  # ﬁ
        "ﬂ": "fl",  # ﬂ
        "ﬃ": "ffi",  # ﬃ
        "ﬄ": "ffl",  # ﬄ
        "ﬅ": "st",  # ﬅ
        "ﬆ": "st",  # ﬆ
    }

    PAGE_NUM_RE = re.compile(r"^\s*(?:\-?\s*\d+\s*\-?|Page\s+\d+|第\s*\d+\s*页)\s*$")
    CID_RE = re.compile(r"\(cid:\d+\)")

    def process(self, text: str) -> str:
        """完整后处理管线"""
        text = self.fix_cid_artifacts(text)
        text = self.fix_ligatures(text)
        text = self.fix_word_spacing(text)
        text = self.fix_hyphenation(text)
        text = self.fix_citation_markers(text)
        text = self.remove_page_numbers(text)
        return text

    def fix_cid_artifacts(self, text: str) -> str:
        """移除 pdfplumber 的 CID 伪影：(cid:48) (cid:62) 等"""
        return self.CID_RE.sub("", text)

    def fix_ligatures(self, text: str) -> str:
        """合字修复：ﬁ → fi"""
        for lig, replacement in self.LIGATURE_MAP.items():
            text = text.replace(lig, replacement)
        return text

    @staticmethod
    def fix_word_spacing(text: str) -> str:
        """修复 PDF 提取中丢失的单词间距

        策略：在多种粘连边界处插入空格
        例：Alzheimer'sdisease → Alzheimer's disease
        注意：不处理常见连写词和缩写
        """
        # 小写字母/数字/右括号/引号后紧跟大写字母 → 插入空格
        text = re.sub(r"([a-z0-9)'\"’])([A-Z])", r"\1 \2", text)
        # 小写字母后紧跟左括号（非空格）→ 插入空格
        text = re.sub(r"([a-z])(\()", r"\1 \2", text)
        # 右括号后紧跟字母（非空格）→ 插入空格
        text = re.sub(r"(\))([a-zA-Z])", r"\1 \2", text)
        # 逗号/分号后紧跟字母（非空格）→ 插入空格
        text = re.sub(r"([,;])([a-zA-Z])", r"\1 \2", text)
        return text

    @staticmethod
    def fix_hyphenation(text: str) -> str:
        """连字符断行修复：computa-\\ntion → computation"""
        return re.sub(r"(\w+)-[ \t]*\n[ \t]*(\w+)", r"\1\2", text)

    @staticmethod
    def fix_citation_markers(text: str) -> str:
        """引用标记重连：word [1] → word[1]"""
        return re.sub(r"(\w)\s+\[(\d+(?:,\s*\d+)*)\]", r"\1[\2]", text)

    def remove_page_numbers(self, text: str) -> str:
        """移除独立的页码行"""
        lines = text.split("\n")
        cleaned = [line for line in lines if not self.PAGE_NUM_RE.match(line.strip())]
        return "\n".join(cleaned)

    @staticmethod
    def remove_headers_footers(pages_text: list[tuple[int, str]]) -> list[tuple[int, str]]:
        """基于重复检测去除页眉页脚

        同一文本在超过 80% 页面出现的短行 → 页眉/页脚
        """
        if len(pages_text) < 3:
            return pages_text

        line_page_count: Counter[str] = Counter()
        for _, text in pages_text:
            seen: set[str] = set()
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) < 50 and stripped not in seen:
                    line_page_count[stripped] += 1
                    seen.add(stripped)

        threshold = len(pages_text) * 0.8
        headers_footers = {
            line
            for line, count in line_page_count.items()
            if count >= threshold and len(line) < 50
        }

        if not headers_footers:
            return pages_text

        result = []
        for page_num, text in pages_text:
            lines = text.split("\n")
            cleaned = [line for line in lines if line.strip() not in headers_footers]
            result.append((page_num, "\n".join(cleaned)))

        return result


# ── Chunk 分块后清洗 ──────────────────────────────────


class ChunkCleaner:
    """分块后清洗：过滤噪声行、合并碎片、去重、质量评分、冗余过滤"""

    # 数学符号 Unicode 范围
    _MATH_CHARS = set(
        "αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ"
        "∑∏∫∂∇∆∈∉⊂⊃∪∩∧∨¬±×÷≈≠≤≥∞∅⊤⊥⊢⊨"
        "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹"
        "·⋯…‖|‖⟨⟩⟪⟫"
    )

    def __init__(self) -> None:
        self._deduplicator = ChunkDeduplicator()
        self._quality_scorer = ChunkQualityScorer()
        self._redundancy_filter = ChunkRedundancyFilter()

    def clean(self, chunks: list[dict]) -> list[dict]:
        """完整清洗管线"""
        chunks = self._filter_noise_lines(chunks)
        chunks = self._merge_fragments(chunks)
        chunks = self._deduplicator.deduplicate(chunks)
        chunks = self._filter_low_quality(chunks)
        chunks = self._redundancy_filter.filter(chunks)
        chunks = self._update_token_counts(chunks)
        return chunks

    def _filter_low_quality(self, chunks: list[dict], min_score: float = 0.3) -> list[dict]:
        """过滤低质量 chunk"""
        result = []
        for c in chunks:
            score_result = self._quality_scorer.score(c)
            c["quality_score"] = score_result["quality_score"]
            c["quality_details"] = score_result["details"]
            if c["quality_score"] >= min_score:
                result.append(c)
        return result

    def _filter_noise_lines(self, chunks: list[dict]) -> list[dict]:
        """过滤每个 chunk 中的噪声行"""
        for chunk in chunks:
            text = chunk.get("text", "")
            if not text:
                continue
            lines = text.split("\n")
            cleaned = self._filter_lines(lines)
            chunk["text"] = "\n".join(cleaned)
        return chunks

    def _filter_lines(self, lines: list[str]) -> list[str]:
        """过滤行列表，移除噪声行"""
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 跳过空行
            if not stripped:
                result.append(line)
                i += 1
                continue

            # 规则 1：Figure/Table caption 保留
            if re.match(r"^(Figure|Table|Fig\.)\s+\d+", stripped, re.IGNORECASE):
                result.append(line)
                i += 1
                continue

            # 规则 2：公式行检测
            if self._is_formula_line(stripped):
                i += 1
                continue

            # 规则 3：坐标轴标签块检测
            block_end = self._find_axis_label_block(lines, i)
            if block_end > i:
                # 跳过整个坐标轴标签块
                i = block_end
                continue

            result.append(line)
            i += 1

        return result

    def _is_formula_line(self, line: str) -> bool:
        """判断是否为公式行

        条件：数学符号/非字母字符占比高 且 正常单词密度低
        """
        if len(line) < 3:
            return False

        # 统计数学符号
        math_count = sum(1 for c in line if c in self._MATH_CHARS)

        # 统计正常英文单词（≥4 个字母的连续字母序列）
        normal_words = re.findall(r"[a-zA-Z]{4,}", line)
        normal_word_count = len(normal_words)

        # 统计字母占比
        alpha_count = sum(1 for c in line if c.isalpha())
        alpha_ratio = alpha_count / len(line) if line else 0

        # 规则 1：有数学符号 + 正常单词少
        if math_count >= 2 and normal_word_count < 5:
            return True
        if math_count >= 1 and normal_word_count < 2 and len(line) < 30:
            return True

        # 规则 2：数学符号占比 > 20% + 正常单词 < 3
        if len(line) > 0 and math_count / len(line) > 0.2 and normal_word_count < 3:
            return True

        # 规则 3：字母占比极低（< 20%）+ 有数学符号 → 纯公式符号行
        if alpha_ratio < 0.2 and math_count >= 1:
            return True

        return False

    def _find_axis_label_block(self, lines: list[str], start: int) -> int:
        """检测从 start 开始的坐标轴标签块

        坐标轴标签块：连续 5+ 短行（<30 字符），超过一半是纯数字/单字母/刻度标签
        返回块结束位置（不含），如果不是块则返回 start
        """
        end = start
        while end < len(lines) and end - start < 20:
            stripped = lines[end].strip()
            if not stripped:
                end += 1
                continue
            if len(stripped) > 30:
                break
            # Figure/Table caption 中断块
            if re.match(r"^(Figure|Table|Fig\.)\s+\d+", stripped, re.IGNORECASE):
                break
            end += 1

        block_size = end - start
        if block_size < 5:
            return start  # 不是块

        # 检查块内短行比例
        block_lines = [lines[j].strip() for j in range(start, end) if lines[j].strip()]
        numeric_or_single = sum(
            1 for l in block_lines
            if re.match(r"^[\d.±\-+]+$", l) or len(l) <= 2
        )

        if len(block_lines) >= 5 and numeric_or_single / len(block_lines) > 0.5:
            return end
        return start

    def _merge_fragments(self, chunks: list[dict], min_tokens: int = 200, max_tokens: int = 1000) -> list[dict]:
        """合并过小的碎片 chunk"""
        if len(chunks) <= 1:
            return chunks

        result = []
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            tokens = self._estimate_tokens(chunk.get("text", ""))

            # chunk 0（title）保持独立
            if chunk.get("chunk_index", -1) == 0 and tokens < min_tokens:
                result.append(chunk)
                i += 1
                continue

            if tokens >= min_tokens:
                result.append(chunk)
                i += 1
                continue

            # 尝试向前合并（与前一个 chunk）
            if result:
                prev = result[-1]
                if (prev.get("section_type") == chunk.get("section_type")
                        and self._estimate_tokens(prev.get("text", "")) + tokens <= max_tokens):
                    prev["text"] = prev["text"] + "\n" + chunk["text"]
                    prev["page_end"] = max(prev.get("page_end", 0), chunk.get("page_end", 0))
                    i += 1
                    continue

            # 尝试向后合并（与下一个 chunk）
            if i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                next_tokens = self._estimate_tokens(next_chunk.get("text", ""))
                if (next_chunk.get("section_type") == chunk.get("section_type")
                        and tokens + next_tokens <= max_tokens):
                    chunk["text"] = chunk["text"] + "\n" + next_chunk["text"]
                    chunk["page_end"] = max(chunk.get("page_end", 0), next_chunk.get("page_end", 0))
                    result.append(chunk)
                    i += 2  # 跳过下一个
                    continue

            # 无法合并，保留
            result.append(chunk)
            i += 1

        return result

    def _update_token_counts(self, chunks: list[dict]) -> list[dict]:
        """重新计算 token 数"""
        for chunk in chunks:
            chunk["token_count"] = self._estimate_tokens(chunk.get("text", ""))
        return chunks

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """粗略估算 token 数"""
        cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
        en_chars = len(text) - cn_chars
        return cn_chars // 2 + en_chars // 4


# ── BM25 工具函数 ─────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    """简单分词：按空白 + 标点拆分，转小写"""
    return re.findall(r"[a-zA-Z0-9一-鿿]+", text.lower())


def _bm25_pairwise_similarity(chunks: list[dict]) -> list[list[float]] | None:
    """计算 chunk 间的 BM25 两两相似度矩阵（归一化到 [0,1]）"""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.debug("rank_bm25 not installed, skipping BM25 similarity")
        return None

    texts = [c.get("text", "") for c in chunks]
    tokenized = [_tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)

    n = len(chunks)
    sim_matrix = [[0.0] * n for _ in range(n)]

    # 计算每个 chunk 对所有 chunk 的 BM25 分数
    scores_cache: list[list[float]] = []
    for i in range(n):
        scores = bm25.get_scores(tokenized[i])
        scores_cache.append(scores.tolist())

    # 归一化：sim(i,j) = avg(score(i→j)/score(i→i), score(j→i)/score(j→j))
    for i in range(n):
        sim_matrix[i][i] = 1.0
        self_score_i = scores_cache[i][i] if scores_cache[i][i] > 0 else 1.0
        for j in range(i + 1, n):
            self_score_j = scores_cache[j][j] if scores_cache[j][j] > 0 else 1.0
            norm_ij = scores_cache[i][j] / self_score_i
            norm_ji = scores_cache[j][i] / self_score_j
            sim = (norm_ij + norm_ji) / 2.0
            sim_matrix[i][j] = sim
            sim_matrix[j][i] = sim

    return sim_matrix


# ── T4.27 分块后去重 ─────────────────────────────────


class ChunkDeduplicator:
    """分块后去重：精确哈希 → 近似 MinHash → 余弦相似度"""

    def __init__(self, jaccard_threshold: float = 0.8, cosine_threshold: float = 0.9):
        self.jaccard_threshold = jaccard_threshold
        self.cosine_threshold = cosine_threshold

    def deduplicate(self, chunks: list[dict]) -> list[dict]:
        """三层去重管线"""
        chunks = self._exact_dedup(chunks)
        chunks = self._minhash_dedup(chunks)
        chunks = self._cosine_dedup(chunks)
        return chunks

    def _exact_dedup(self, chunks: list[dict]) -> list[dict]:
        """精确哈希去重：完全相同的文本"""
        seen: set[str] = set()
        result = []
        for c in chunks:
            h = hashlib.sha256(c.get("text", "").encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                result.append(c)
        return result

    def _minhash_dedup(self, chunks: list[dict]) -> list[dict]:
        """MinHash 近似去重：Jaccard ≥ threshold 的近似重复"""
        try:
            from datasketch import MinHash, MinHashLSH
        except ImportError:
            logger.debug("datasketch not installed, skipping MinHash dedup")
            return chunks

        lsh = MinHashLSH(threshold=self.jaccard_threshold, num_perm=128)
        result = []

        for i, c in enumerate(chunks):
            m = MinHash(num_perm=128)
            text = c.get("text", "").lower()
            for j in range(len(text) - 4):
                m.update(text[j : j + 5].encode("utf8"))

            duplicates = lsh.query(m)
            if not duplicates:
                lsh.insert(f"chunk_{i}", m)
                result.append(c)

        return result

    def _cosine_dedup(self, chunks: list[dict]) -> list[dict]:
        """BM25 语义相似度去重：≥ threshold 的语义重复"""
        if len(chunks) < 2:
            return chunks

        sim_matrix = _bm25_pairwise_similarity(chunks)
        if sim_matrix is None:
            return chunks

        to_remove: set[int] = set()
        for i in range(len(chunks)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(chunks)):
                if j in to_remove:
                    continue
                if sim_matrix[i][j] >= self.cosine_threshold:
                    if len(chunks[i].get("text", "")) < len(chunks[j].get("text", "")):
                        to_remove.add(i)
                    else:
                        to_remove.add(j)

        return [c for idx, c in enumerate(chunks) if idx not in to_remove]


# ── T4.28 分块质量评分 ───────────────────────────────


class ChunkQualityScorer:
    """分块质量评分器"""

    WEIGHTS = {
        "length_score": 0.25,
        "info_density": 0.25,
        "structure_score": 0.20,
        "language_score": 0.15,
        "noise_score": 0.15,
    }

    _STOPWORDS = frozenset(
        {"the", "a", "an", "is", "are", "was", "were", "in", "on",
         "at", "to", "for", "of", "with", "and", "or", "but", "not"}
    )

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

    @staticmethod
    def _score_length(text: str) -> float:
        """长度评分：过短过长都扣分"""
        tokens = len(text.split())
        if tokens < 30:
            return 0.2
        if tokens < 50:
            return 0.5
        if tokens <= 1000:
            return 1.0
        if tokens <= 1500:
            return 0.8
        return 0.5

    def _score_info_density(self, text: str) -> float:
        """信息密度：停用词占比、词汇多样性"""
        words = text.lower().split()
        if not words:
            return 0.0
        diversity = len(set(words)) / len(words)
        content_ratio = sum(1 for w in words if w not in self._STOPWORDS) / len(words)
        return min(1.0, (diversity * 0.5 + content_ratio * 0.5) * 1.5)

    @staticmethod
    def _score_structure(text: str) -> float:
        """结构评分：是否包含有意义的句子结构"""
        has_sentence = bool(re.search(r"[.!?。！？]\s", text))
        has_paragraph = "\n\n" in text or text.count("\n") > 3
        score = 0.5
        if has_sentence:
            score += 0.3
        if has_paragraph:
            score += 0.2
        return min(1.0, score)

    @staticmethod
    def _score_language(text: str) -> float:
        """语言一致性评分：中英文混杂扣分"""
        if not text:
            return 0.0
        cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
        en_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total = cn_chars + en_chars
        if total == 0:
            return 0.0
        return max(cn_chars, en_chars) / total

    @staticmethod
    def _score_noise(text: str) -> float:
        """噪声评分：噪声越少分越高（反向）"""
        lines = text.split("\n")
        noise_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            math_chars = sum(
                1 for c in stripped if c in "∑∫∂∇αβγδεζηθ∈∉⊂⊃∪∩≈≠≤≥∞±×÷"
            )
            if len(stripped) > 0 and math_chars / len(stripped) > 0.2:
                noise_count += 1
            elif stripped.replace(" ", "").isdigit():
                noise_count += 1
            elif len(stripped) < 5 and not re.match(r"^\d+\.", stripped):
                noise_count += 1
        noise_ratio = noise_count / max(len(lines), 1)
        return max(0.0, 1.0 - noise_ratio * 3)


# ── T4.29 Chunk 冗余过滤 ─────────────────────────────


class ChunkRedundancyFilter:
    """Chunk 冗余过滤：BM25 + 动态阈值"""

    def __init__(self, redundancy_threshold: float = 0.85):
        self.threshold = redundancy_threshold

    def filter(self, chunks: list[dict]) -> list[dict]:
        """移除冗余 chunk，保留信息量更大的那个"""
        if len(chunks) < 2:
            return chunks

        sim = _bm25_pairwise_similarity(chunks)
        if sim is None:
            return chunks

        to_remove: set[int] = set()
        for i in range(len(chunks)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(chunks)):
                if j in to_remove:
                    continue
                if sim[i][j] >= self.threshold:
                    if len(chunks[i].get("text", "")) < len(chunks[j].get("text", "")):
                        to_remove.add(i)
                        break
                    else:
                        to_remove.add(j)

        return [c for idx, c in enumerate(chunks) if idx not in to_remove]


# ── 章节类型归一 ──────────────────────────────────────

_SECTION_TYPE_MAP: dict[str, str] = {
    "abstract": "abstract", "摘要": "abstract",
    "introduction": "introduction", "引言": "introduction", "导言": "introduction",
    "related work": "related_work", "相关工作": "related_work", "文献综述": "related_work",
    "background": "background", "背景": "background",
    "preliminary": "background", "preliminaries": "background",
    "method": "method", "方法": "method", "methodology": "method", "方法论": "method",
    "approach": "method", "approaches": "method",
    "experiment": "method", "实验": "method", "experiments": "method",
    "model": "method", "模型": "method",
    "estimation": "method", "估计": "method",
    "simulation": "method", "仿真": "method", "simulations": "method",
    "data analysis": "method", "数据分析": "method",
    "proposed method": "method", "proposed model": "method",
    "result": "result", "结果": "result", "results": "result",
    "simulation results": "result", "simulation settings": "method",
    "model selection": "method", "模型选择": "method",
    "model estimation": "method",
    "discussion": "discussion", "讨论": "discussion",
    "conclusion": "conclusion", "结论": "conclusion", "conclusions": "conclusion",
    "limitation": "limitation", "局限": "limitation", "limitations": "limitation",
    "future work": "future_work", "未来工作": "future_work", "future direction": "future_work",
    "acknowledgment": "acknowledgment", "致谢": "acknowledgment",
    "reference": "reference", "参考文献": "reference", "references": "reference",
    "appendix": "appendix", "附录": "appendix",
}

# 正文 chunk 类型映射
_SECTION_TO_CHUNK_TYPE: dict[str, str] = {
    "abstract": ChunkType.ABSTRACT.value,
    "introduction": ChunkType.BODY.value,
    "related_work": ChunkType.BODY.value,
    "background": ChunkType.BODY.value,
    "method": ChunkType.METHOD.value,
    "result": ChunkType.RESULT.value,
    "discussion": ChunkType.DISCUSSION.value,
    "limitation": ChunkType.LIMITATION.value,
    "conclusion": ChunkType.CONCLUSION.value,
    "future_work": ChunkType.BODY.value,
    "reference": ChunkType.REFERENCE.value,
    "appendix": ChunkType.APPENDIX.value,
    "acknowledgment": ChunkType.BODY.value,
}


class ParserService:
    """PDF 解析与分块"""

    def __init__(self, storage: JSONStorage | None = None, enable_contextual_retrieval: bool = True):
        self.storage = storage or get_storage()
        self._adapters: list[ParserAdapter] = [
            PyMuPDF4LLMAdapter(),
            PdfPlumberAdapter(),
            PyMuPDFAdapter(),
            PdfMinerAdapter(),
            DoclingAdapter(),
        ]
        self._post_processor = TextPostProcessor()
        self._chunk_cleaner = ChunkCleaner()
        self._enable_contextual = enable_contextual_retrieval

    def download_pdf(self, paper_id: str) -> dict[str, Any]:
        """下载论文 PDF 到本地"""
        import urllib.request

        item = self.storage.get_item("papers", paper_id)
        if not item:
            return {"success": False, "error": "Paper not found"}

        paper = Paper(**item)
        pdf_url = paper.open_access.pdf_url if paper.open_access else ""
        if not pdf_url:
            return {"success": False, "error": "No PDF URL"}

        # 目标路径
        project_id = paper.project_id
        dest_dir = self.storage.data_dir / "files" / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{paper_id}.pdf"

        if dest_path.exists():
            # 已下载，更新路径
            self._update_pdf_path(paper_id, str(dest_path))
            self._mark_pool_pdf_downloaded(paper)
            return {"success": True, "pdf_path": str(dest_path), "skipped": True}

        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            headers = {"User-Agent": "PaperAgent/1.0 (research-tool)"}
            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(dest_path, "wb") as f:
                    f.write(resp.read())
            self._update_pdf_path(paper_id, str(dest_path))
            self._mark_pool_pdf_downloaded(paper)
            logger.info(f"Downloaded PDF: {dest_path}")
            return {"success": True, "pdf_path": str(dest_path)}
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
            return {"success": False, "error": str(e)}

    def download_all_pdfs(self, project_id: str, max_workers: int | None = None) -> dict[str, Any]:
        """下载项目中所有有 PDF URL 但没有本地文件的论文（并行下载）"""
        if max_workers is None:
            max_workers = int(os.environ.get("PARALLEL_WORKERS", "4"))

        items = self.storage.query("papers", {"project_id": project_id})
        results = {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}

        # 筛选需要下载的论文
        to_download = []
        for item in items:
            paper = Paper(**item)
            pdf_url = paper.open_access.pdf_url if paper.open_access else ""
            if not pdf_url:
                continue
            if paper.pdf_path and Path(paper.pdf_path).exists():
                results["skipped"] += 1
                continue
            to_download.append(paper.paper_id)

        results["total"] = len(to_download)
        if not to_download:
            return results

        logger.info(f"Downloading {len(to_download)} PDFs with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.download_pdf, pid): pid for pid in to_download}
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    result = future.result()
                    if result.get("success"):
                        results["downloaded"] += 1
                    else:
                        results["failed"] += 1
                        logger.warning(f"Download failed for {pid}: {result.get('error')}")
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"Download exception for {pid}: {e}")

        return results

    def _update_pdf_path(self, paper_id: str, pdf_path: str) -> None:
        """更新论文的 pdf_path"""
        item = self.storage.get_item("papers", paper_id)
        if item:
            item["pdf_path"] = pdf_path
            self.storage.upsert_item("papers", paper_id, item)

    def parse_paper(self, paper_id: str, force: bool = False) -> dict[str, Any]:
        item = self.storage.get_item("papers", paper_id)
        if not item:
            return {"success": False, "error": "Paper not found"}

        paper = Paper(**item)

        # 已解析则跳过（force=True 时强制重新解析）
        if not force and paper.status in (
            PaperStatus.PARSED, PaperStatus.CARD_READY, PaperStatus.EVIDENCE_READY,
        ):
            existing_chunks = self.storage.query("paper_chunks", {"paper_id": paper_id})
            logger.info(f"Paper {paper_id} already parsed ({len(existing_chunks)} chunks), skipping")
            return {"success": True, "skipped": True, "chunk_count": len(existing_chunks)}

        # 检查 PDF 是否已下载，未下载则自动下载
        pool_id = self._get_pool_id(paper)
        if pool_id:
            pool_item = self.storage.load_from_folder("papers_pool", pool_id)
            if pool_item and not pool_item.get("is_pdf_downloaded", False):
                logger.info(f"PDF not downloaded for {paper_id}, auto-downloading...")
                dl_result = self.download_pdf(paper_id)
                if not dl_result.get("success"):
                    return {"success": False, "error": f"PDF auto-download failed: {dl_result.get('error')}"}
                # 重新加载 paper 获取更新后的 pdf_path
                item = self.storage.get_item("papers", paper_id)
                if item:
                    paper = Paper(**item)

        # 开始解析 → PARSING
        self._update_status(paper_id, PaperStatus.PARSING)

        parse_result = ParseResult(
            paper_id=paper_id,
            parser_name="pdfplumber",
            status="parsing",
            started_at=datetime.now().isoformat(),
        )

        if not paper.pdf_path:
            return self._fail(paper_id, parse_result, "No PDF path")

        if not Path(paper.pdf_path).exists():
            return self._fail(paper_id, parse_result, "PDF file missing")

        # T4.12: 多解析器 fallback 链路
        # 1. 先尝试 pdfplumber
        # 2. 如果失败或空文本，尝试 PyMuPDF
        # 3. 仍然空文本 → 标记 scanned_pdf_suspected，不生成正文 chunk

        pages_text, parser_name, quality_flags = self._extract_with_fallback(paper.pdf_path)

        # 文本后处理：合字/连字符/引用标记/页码/页眉页脚
        if pages_text:
            pages_text = [(pn, self._post_processor.process(t)) for pn, t in pages_text]
            pages_text = self._post_processor.remove_headers_footers(pages_text)

        parse_result.parser_name = parser_name
        parse_result.page_count = len(pages_text)
        parse_result.quality_flags = quality_flags

        # 检查是否为扫描件
        if "scanned_pdf_suspected" in quality_flags:
            parse_result.quality_flags = quality_flags
            self.storage.upsert_item("parse_results", parse_result.parse_id, parse_result.model_dump())
            return self._fail(paper_id, parse_result, "Scanned PDF detected, no text extractable")

        if not pages_text:
            return self._fail(paper_id, parse_result, "No text extracted from PDF")

        # 分块
        chunks_data = self._chunk_by_sections(pages_text, paper_id)

        # Contextual Retrieval：每个 chunk 携带论文标题、作者、章节上下文
        # 测试显示：小数据集(<50 chunks)下效果更差，大规模场景下有效
        if self._enable_contextual:
            chunks_data = self._enrich_context(chunks_data, paper)

        # 分块后清洗：过滤公式噪声行、合并碎片
        chunks_data = self._chunk_cleaner.clean(chunks_data)

        # Parent-Child 分块：将子块聚合为 ~2000 token 的父块
        chunks_data = self._create_parent_chunks(chunks_data, paper_id)

        if not chunks_data:
            return self._fail(paper_id, parse_result, "No text extracted from PDF")

        # 分离正文和参考文献
        body_chunks = [c for c in chunks_data if c.get("chunk_type") != ChunkType.REFERENCE.value]
        ref_chunks = [c for c in chunks_data if c.get("chunk_type") == ChunkType.REFERENCE.value]

        parse_result.chunk_count = len(chunks_data)
        parse_result.body_chunk_count = len(body_chunks)
        parse_result.reference_count = len(ref_chunks)

        # 统计 section 数
        sections = {c.get("section_type", "") for c in chunks_data if c.get("section_type")}
        parse_result.section_count = len(sections)

        # 参考文献结构化提取
        if ref_chunks:
            ref_text = "\n".join(c.get("text", "") for c in ref_chunks)
            references = self._extract_references(ref_text, paper_id)
            if references:
                self._save_references(paper_id, references)
                parse_result.reference_count = len(references)

        # 增强质量检查
        quality_flags, diagnostics = self._check_quality_enhanced(
            pages_text, parse_result.section_count, parse_result.chunk_count
        )
        parse_result.quality_flags = quality_flags
        parse_result.diagnostics = diagnostics

        # 保存到 paper_chunks 集合
        self._save_chunks(paper_id, chunks_data)

        # 保存 ParseResult
        parse_result.status = "success"
        parse_result.finished_at = datetime.now().isoformat()
        self.storage.upsert_item("parse_results", parse_result.parse_id, parse_result.model_dump())

        self._update_status(paper_id, PaperStatus.PARSED)

        # 标记 papers_pool 中的 is_parsed
        self._mark_pool_parsed(paper)

        logger.info(f"Parsed paper {paper_id}: {len(body_chunks)} body chunks, {len(ref_chunks)} refs")

        return {
            "success": True,
            "chunk_count": len(chunks_data),
            "body_chunk_count": len(body_chunks),
            "reference_count": len(ref_chunks),
            "page_count": parse_result.page_count,
            "section_count": parse_result.section_count,
            "quality_flags": quality_flags,
            "parse_id": parse_result.parse_id,
        }

    def _fail(self, paper_id: str, parse_result: ParseResult, error: str) -> dict[str, Any]:
        """统一失败处理"""
        self._update_status(paper_id, PaperStatus.FAILED, error)
        parse_result.status = "failed"
        parse_result.error_message = error
        parse_result.finished_at = datetime.now().isoformat()
        self.storage.upsert_item("parse_results", parse_result.parse_id, parse_result.model_dump())
        logger.error(f"Parse failed for {paper_id}: {error}")
        return {"success": False, "error": error, "parse_id": parse_result.parse_id}

    def parse_project_papers(
        self, project_id: str, only_unparsed: bool = True, max_workers: int | None = None
    ) -> dict[str, Any]:
        """解析项目中的所有论文（并行解析）"""
        if max_workers is None:
            max_workers = int(os.environ.get("PARALLEL_WORKERS", "4"))

        papers = self.storage.query("papers", {"project_id": project_id})
        results = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        # 筛选需要解析的论文
        to_parse = []
        for p in papers:
            paper = Paper(**p)
            if only_unparsed and paper.status in (
                PaperStatus.PARSED,
                PaperStatus.CARD_READY,
                PaperStatus.EVIDENCE_READY,
            ):
                results["skipped"] += 1
                continue
            to_parse.append(paper.paper_id)

        results["total"] = len(to_parse)
        if not to_parse:
            return results

        logger.info(f"Parsing {len(to_parse)} papers with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.parse_paper, pid): pid for pid in to_parse}
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    result = future.result()
                    if result.get("success"):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        logger.warning(f"Parse failed for {pid}: {result.get('error')}")
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"Parse exception for {pid}: {e}")

        return results

    def get_chunks(
        self,
        paper_id: str,
        chunk_types: list[str] | None = None,
        exclude_types: list[str] | None = None,
    ) -> list[PaperChunk]:
        """获取论文 chunks，支持类型过滤"""
        # 优先从 paper_chunks 集合读取
        chunks_data = self.storage.load_collection("paper_chunks")
        paper_chunks = [c for c in chunks_data if c.get("paper_id") == paper_id]

        # 兼容旧格式
        if not paper_chunks:
            old_chunks = self.storage.load_collection(f"chunks_{paper_id}")
            if old_chunks:
                # 迁移到新格式
                migrated = self._migrate_old_chunks(old_chunks, paper_id)
                paper_chunks = migrated

        # 类型过滤
        if chunk_types:
            paper_chunks = [c for c in paper_chunks if c.get("chunk_type", "body") in chunk_types]
        if exclude_types:
            paper_chunks = [c for c in paper_chunks if c.get("chunk_type", "body") not in exclude_types]

        # 按 chunk_index 排序
        paper_chunks.sort(key=lambda c: c.get("chunk_index", 0))

        return [PaperChunk(**c) for c in paper_chunks]

    def get_body_chunks(self, paper_id: str) -> list[PaperChunk]:
        """只获取正文 chunks（排除 reference、table、figure_caption）"""
        exclude = [ChunkType.REFERENCE.value, ChunkType.TABLE.value, ChunkType.FIGURE_CAPTION.value]
        return self.get_chunks(paper_id, exclude_types=exclude)

    def get_parse_result(self, paper_id: str) -> ParseResult | None:
        """获取解析结果"""
        items = self.storage.query("parse_results", {"paper_id": paper_id})
        if items:
            return ParseResult(**items[-1])
        return None

    def embed_paper(self, paper_id: str) -> dict[str, Any]:
        """将已解析的论文向量化并存入 Qdrant（chunks + paper_profile）

        云端推理模式下，Qdrant 自动生成 dense + sparse 向量。
        需要先调用 parse_paper 成功后再调用此方法。
        """
        from src.agents_v3.research_workspace.vector_storage import get_vector_storage

        # 获取该论文的所有 chunks
        chunks = self.get_chunks(paper_id)
        if not chunks:
            return {"success": False, "error": "No chunks found, run parse_paper first"}

        chunk_dicts = [c.model_dump() for c in chunks]

        try:
            vector_storage = get_vector_storage()
        except Exception as e:
            return {"success": False, "error": f"Failed to init vector storage: {e}"}

        # 先删除旧的 embeddings
        try:
            vector_storage.delete_by_paper(paper_id)
        except Exception:
            pass  # 集合可能不存在

        # ── 1. 写入 paper_chunks（云端推理自动嵌入）──
        texts = [c["text"] for c in chunk_dicts]
        logger.info(f"Embedding {len(texts)} chunks for paper {paper_id}")

        if vector_storage.use_inference:
            # 云端推理：传文本，Qdrant 自动生成向量
            vector_storage.add_chunks(chunk_dicts, texts, sparse_embeddings=None)
        else:
            # 本地模式：预计算 embeddings
            from src.agents_v3.research_workspace.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            embeddings = embedding_service.embed_texts(texts)
            vector_storage.add_chunks(chunk_dicts, embeddings)

        # ── 2. 写入 paper_profiles（论文级向量）──
        paper = self.storage.get_item("papers", paper_id)
        if paper:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            profile_text = f"{title}. {abstract}".strip()
            if profile_text and len(profile_text) > 10:
                project_id = paper.get("project_id", "")
                vector_storage.add_paper_profiles(
                    paper_ids=[paper_id],
                    texts=[profile_text],
                    metadatas=[{"project_id": project_id, "title": title}],
                )
                logger.info(f"Added paper profile for {paper_id}")

        return {
            "success": True,
            "chunk_count": len(chunk_dicts),
            "cloud_inference": vector_storage.use_inference,
        }

    def search_chunks(
        self, query: str, paper_ids: list[str] | None = None, top_k: int = 5,
        return_parent: bool = True,
    ) -> list[dict[str, Any]]:
        """向量检索最相关的 chunks，支持返回父块（LLM 上下文）

        Args:
            query: 查询文本
            paper_ids: 可选，只检索指定论文
            top_k: 返回数量
            return_parent: 是否用父块文本替换子块文本（给 LLM 更多上下文）
        """
        from src.agents_v3.research_workspace.embedding_service import get_embedding_service
        from src.agents_v3.research_workspace.vector_storage import get_vector_storage

        embedding_service = get_embedding_service()
        vector_storage = get_vector_storage()

        query_embedding = embedding_service.embed_query(query)
        results = vector_storage.search_chunks(query_embedding, top_k=top_k, paper_ids=paper_ids)

        if not return_parent:
            return results

        # 收集需要查找的 parent_id
        parent_ids = set()
        for r in results:
            pid = r.get("metadata", {}).get("parent_id", "")
            if pid:
                parent_ids.add(pid)

        if not parent_ids:
            return results

        # 从 PostgreSQL 批量查找父块
        parent_map: dict[str, str] = {}
        try:
            all_chunks = self.storage.load_collection("paper_chunks")
            for c in all_chunks:
                if c.get("chunk_id") in parent_ids:
                    parent_map[c["chunk_id"]] = c.get("text", "")
        except Exception:
            pass

        # 替换子块文本为父块文本
        for r in results:
            pid = r.get("metadata", {}).get("parent_id", "")
            if pid and pid in parent_map:
                r["child_text"] = r["text"]
                r["text"] = parent_map[pid]
                r["is_parent_context"] = True

        return results

    # ── 质量检查 ──────────────────────────────────────

    def _check_quality(self, pages_text: list[tuple[int, str]]) -> list[str]:
        flags = []
        total_chars = sum(len(t) for _, t in pages_text)
        empty_pages = sum(1 for _, t in pages_text if not t.strip())

        if total_chars < 100:
            flags.append("empty_pdf")
        elif total_chars < 500:
            flags.append("low_text_coverage")

        if empty_pages > len(pages_text) * 0.5:
            flags.append("scanned_pdf_suspected")

        # 检查是否有过多短行（可能是表格或乱码）
        all_lines = []
        for _, t in pages_text:
            all_lines.extend(t.split("\n"))
        short_lines = sum(1 for l in all_lines if 0 < len(l.strip()) < 20)
        if len(all_lines) > 10 and short_lines > len(all_lines) * 0.6:
            flags.append("too_many_short_lines")

        return flags

    # ── 章节检测 ──────────────────────────────────────

    _SECTION_PATTERNS = [
        "abstract", "摘要",
        "introduction", "引言", "导言",
        "related work", "相关工作", "文献综述",
        "background", "背景", "preliminary", "preliminaries",
        "method", "方法", "methodology", "方法论",
        "approach", "approaches",
        "experiment", "实验", "experiments",
        "model", "模型", "estimation", "估计",
        "simulation", "仿真", "simulations",
        "data analysis", "数据分析",
        "proposed method", "proposed model",
        "model selection", "模型选择", "model estimation",
        "simulation results", "simulation settings",
        "result", "结果", "results",
        "discussion", "讨论",
        "conclusion", "结论", "conclusions",
        "limitation", "局限", "limitations",
        "future work", "未来工作", "future direction",
        "acknowledgment", "致谢",
        "reference", "参考文献", "references",
        "appendix", "附录",
    ]

    def _detect_section(self, line: str) -> str | None:
        """检测段落是否是章节标题，返回归一化的 section_type

        支持格式：
        - Abstract / 摘要 （无编号，独占一行）
        - 1 Introduction / 2.1 Methods （编号 + 空格/点 + 标题）
        """
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            return None

        lower = stripped.lower()

        # 带编号的标题：必须以数字开头
        has_number_prefix = bool(re.match(r"^\d+[\.\)]?\s+", stripped))
        if has_number_prefix:
            cleaned = re.sub(r"^\d+[\.\)]?\s+", "", lower).strip()
            if not cleaned or len(cleaned) > 60:
                return None
            # 按长度降序匹配，优先匹配长模式
            for pattern in self._SECTION_PATTERNS:
                if cleaned == pattern or cleaned.startswith(pattern + " "):
                    return _SECTION_TYPE_MAP.get(pattern, pattern)

        # 无编号标题：必须精确匹配，且行首大写（英文）或是中文
        if len(lower) < 30 and (stripped[0].isupper() or "一" <= stripped[0] <= "鿿"):
            for pattern in self._SECTION_PATTERNS:
                if lower == pattern:
                    return _SECTION_TYPE_MAP.get(pattern, pattern)

        return None

    def _estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数"""
        cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
        en_chars = len(text) - cn_chars
        return cn_chars // 2 + en_chars // 4

    # ── 分块 ──────────────────────────────────────────

    @staticmethod
    def _enrich_context(chunks: list[dict[str, Any]], paper: Paper) -> list[dict[str, Any]]:
        """Anthropic Contextual Retrieval：给每个 chunk 前缀论文标题、作者、章节上下文。

        格式: "This chunk is from \"{title}\" by {authors}. Section: {section}.\n\n{original_text}"
        减少 ~67% 失败检索（Anthropic 2024 实验数据）。
        """
        title = (paper.title or "").strip()
        if not title:
            return chunks

        # 取前 3 个作者，避免前缀过长
        author_names = [a.name for a in paper.authors if a.name][:3]
        authors_str = ", ".join(author_names) if author_names else "Unknown"

        for chunk in chunks:
            section = chunk.get("section_title", "") or chunk.get("section_type", "")
            original_text = chunk.get("text", "")
            if not original_text:
                continue

            # 构造上下文前缀
            prefix = f'This chunk is from "{title}" by {authors_str}.'
            if section:
                prefix += f" Section: {section}."
            prefix += "\n\n"

            # 存储原始文本到 metadata
            chunk.setdefault("metadata", {})["original_text"] = original_text
            chunk["text"] = prefix + original_text
            # 重新计算 token 数
            chunk["token_count"] = len(chunk["text"].split())  # 粗估

        return chunks

    def _chunk_by_sections(
        self, pages_text: list[tuple[int, str]], paper_id: str
    ) -> list[dict[str, Any]]:
        """按章节分块，每块 500-900 tokens，带 50-100 token overlap"""
        chunks: list[dict[str, Any]] = []
        current_section_type = ""
        current_text = ""
        current_page_start = 1
        current_page_end = 1
        chunk_idx = 0
        char_offset = 0
        sections_seen: set[str] = set()
        prev_tail = ""  # 用于 overlap

        for page_num, text in pages_text:
            lines = text.split("\n")
            for line in lines:
                section_type = self._detect_section(line)
                if section_type:
                    # Flush current buffer
                    if current_text.strip():
                        new_chunks = self._flush_buffer(
                            current_text.strip(), current_section_type,
                            paper_id, chunk_idx, char_offset,
                            current_page_start, current_page_end, prev_tail,
                        )
                        if new_chunks:
                            prev_tail = self._get_tail(current_text.strip())
                            chunks.extend(new_chunks)
                            chunk_idx += len(new_chunks)
                            char_offset += len(current_text)
                        current_text = ""
                    current_section_type = section_type
                    sections_seen.add(section_type)
                    current_page_start = page_num
                else:
                    current_text += line + "\n"
                    tokens = self._estimate_tokens(current_text)
                    if tokens >= 800:
                        new_chunks = self._flush_buffer(
                            current_text.strip(), current_section_type,
                            paper_id, chunk_idx, char_offset,
                            current_page_start, current_page_end, prev_tail,
                        )
                        if new_chunks:
                            prev_tail = self._get_tail(current_text.strip())
                            chunks.extend(new_chunks)
                            chunk_idx += len(new_chunks)
                            char_offset += len(current_text)
                        current_text = ""
                        current_page_start = page_num
            current_page_end = page_num

        # Flush remaining
        if current_text.strip():
            new_chunks = self._flush_buffer(
                current_text.strip(), current_section_type,
                paper_id, chunk_idx, char_offset,
                current_page_start, current_page_end, prev_tail,
            )
            if new_chunks:
                chunks.extend(new_chunks)

        return chunks

    def _get_tail(self, text: str, tokens: int = 80) -> str:
        """获取文本尾部用于 overlap"""
        words = text.split()
        if len(words) <= tokens:
            return text
        return " ".join(words[-tokens:])

    def _flush_buffer(
        self, text: str, section_type: str, paper_id: str,
        start_idx: int, char_offset: int,
        page_start: int, page_end: int, prev_tail: str = "",
    ) -> list[dict[str, Any]]:
        """将文本缓冲拆分为 500-900 token 的块"""
        # 短文本丢弃（除非是标题/表格/图注）
        if len(text.strip()) < 30 and section_type not in ("title", "abstract"):
            return []

        chunk_type = _SECTION_TO_CHUNK_TYPE.get(section_type, ChunkType.BODY.value)

        tokens = self._estimate_tokens(text)
        if tokens <= 900:
            # 添加 overlap
            chunk_text = text
            if prev_tail and chunk_type == ChunkType.BODY.value:
                overlap_text = prev_tail + " " + text
                if self._estimate_tokens(overlap_text) <= 1000:
                    chunk_text = overlap_text

            return [self._make_chunk(
                paper_id, start_idx, section_type, chunk_type,
                chunk_text, char_offset, page_start, page_end,
            )]

        # Split by paragraphs, then by sentences if needed
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) <= 1 and tokens > 900:
            sentences = re.split(r"(?<=[.!?。！？])\s+", text)
            paragraphs = [s.strip() for s in sentences if s.strip()]

        result: list[dict[str, Any]] = []
        buf = ""
        idx = start_idx
        for para in paragraphs:
            candidate = (buf + " " + para).strip() if buf else para
            if self._estimate_tokens(candidate) > 900 and buf:
                result.append(self._make_chunk(
                    paper_id, idx, section_type, chunk_type,
                    buf, char_offset, page_start, page_end,
                ))
                idx += 1
                char_offset += len(buf) + 1
                buf = para
            else:
                buf = candidate
        if buf:
            result.append(self._make_chunk(
                paper_id, idx, section_type, chunk_type,
                buf, char_offset, page_start, page_end,
            ))
        return result

    def _make_chunk(
        self, paper_id: str, chunk_index: int,
        section_type: str, chunk_type: str,
        text: str, char_offset: int,
        page_start: int, page_end: int,
    ) -> dict[str, Any]:
        """构建标准 chunk 字典"""
        return {
            "chunk_id": f"chunk_{paper_id}_{chunk_index:04d}",
            "paper_id": paper_id,
            "chunk_index": chunk_index,
            "section_title": section_type.replace("_", " ").title() if section_type else "",
            "section_type": section_type,
            "chunk_type": chunk_type,
            "text": text,
            "start_char": char_offset,
            "end_char": char_offset + len(text),
            "page_start": page_start,
            "page_end": page_end,
            "token_count": self._estimate_tokens(text),
            "parser_name": "pdfplumber",
            "quality_flags": [],
            "metadata": {},
        }

    # ── Parent-Child 分块 ──────────────────────────────

    def _create_parent_chunks(
        self, child_chunks: list[dict[str, Any]], paper_id: str, target_tokens: int = 2000
    ) -> list[dict[str, Any]]:
        """将子块聚合为父块（~target_tokens tokens），返回包含父子的完整列表。

        规则：
        - 仅对 body/abstract/method/results 等正文类型创建 parent，reference 跳过
        - 同一 section_type 的连续子块合并为一个父块
        - 每个子块记录 parent_id
        - 父块 chunk_type = "parent"
        """
        # 分离正文块和非正文块
        body_chunks = []
        other_chunks = []
        for c in child_chunks:
            if c.get("chunk_type") == ChunkType.REFERENCE.value:
                other_chunks.append(c)
            else:
                body_chunks.append(c)

        if not body_chunks:
            return child_chunks

        parents: list[dict[str, Any]] = []
        parent_idx = 0

        # 按 section_type 分组，连续同 section 的子块归为一组
        groups: list[list[dict]] = []
        current_group: list[dict] = []
        current_section = body_chunks[0].get("section_type", "")

        for chunk in body_chunks:
            sec = chunk.get("section_type", "")
            group_tokens = sum(self._estimate_tokens(c.get("text", "")) for c in current_group)
            # 新组条件：section 变化 或 当前组已超 target
            if sec != current_section and current_group:
                groups.append(current_group)
                current_group = []
                current_section = sec
            current_group.append(chunk)
            # 如果累积够了就开新组
            if sum(self._estimate_tokens(c.get("text", "")) for c in current_group) >= target_tokens:
                groups.append(current_group)
                current_group = []
        if current_group:
            groups.append(current_group)

        # 为每组创建 parent chunk
        for group in groups:
            if not group:
                continue
            # Contextual Retrieval: 合并时用 original_text，避免重复前缀
            texts = []
            for c in group:
                orig = c.get("metadata", {}).get("original_text")
                texts.append(orig if orig else c.get("text", ""))
            merged_text = "\n\n".join(texts)
            page_start = min(c.get("page_start", 0) for c in group)
            page_end = max(c.get("page_end", 0) for c in group)
            section_type = group[0].get("section_type", "")
            section_title = group[0].get("section_title", "")

            parent_id = f"parent_{paper_id}_{parent_idx:04d}"
            parent_chunk = {
                "chunk_id": parent_id,
                "paper_id": paper_id,
                "chunk_index": -1,  # parent 不参与排序
                "section_title": section_title,
                "section_type": section_type,
                "chunk_type": "parent",
                "text": merged_text,
                "start_char": group[0].get("start_char", 0),
                "end_char": group[-1].get("end_char", 0),
                "page_start": page_start,
                "page_end": page_end,
                "token_count": self._estimate_tokens(merged_text),
                "parser_name": group[0].get("parser_name", "pdfplumber"),
                "quality_flags": [],
                "metadata": {},
            }
            parents.append(parent_chunk)

            # 设置子块的 parent_id
            for child in group:
                child["parent_id"] = parent_id

            parent_idx += 1

        # 合并 parent + child + other
        return parents + body_chunks + other_chunks

    # ── 存储 ──────────────────────────────────────────

    def _save_chunks(self, paper_id: str, chunks: list[dict[str, Any]]) -> None:
        """保存到 paper_chunks 集合"""
        # 加载已有数据，移除该 paper 的旧 chunks
        existing = self.storage.load_collection("paper_chunks")
        filtered = [c for c in existing if c.get("paper_id") != paper_id]
        filtered.extend(chunks)
        self.storage.save_collection("paper_chunks", filtered)

    def _save_references(self, paper_id: str, references: list[Reference]) -> None:
        """保存结构化参考文献到 references 集合"""
        existing = self.storage.load_collection("paper_references")
        filtered = [r for r in existing if r.get("citing_paper_id") != paper_id]
        filtered.extend([r.model_dump() for r in references])
        self.storage.save_collection("paper_references", filtered)

    def _migrate_old_chunks(self, old_chunks: list[dict], paper_id: str) -> list[dict]:
        """迁移旧格式 chunks 到新格式"""
        migrated = []
        for i, c in enumerate(old_chunks):
            new_c = {
                "chunk_id": c.get("chunk_id", f"chunk_{paper_id}_{i:04d}"),
                "paper_id": paper_id,
                "chunk_index": c.get("chunk_index", i),
                "section_title": c.get("section_title", ""),
                "section_type": "",
                "chunk_type": "body",
                "text": c.get("text", ""),
                "start_char": c.get("start_char", 0),
                "end_char": c.get("end_char", 0),
                "page_start": c.get("page_number", c.get("page_start", 0)),
                "page_end": c.get("page_number", c.get("page_end", 0)),
                "token_count": c.get("token_count", 0),
                "parser_name": "pdfplumber",
                "quality_flags": [],
                "metadata": {},
            }
            migrated.append(new_c)
        return migrated

    def _update_status(self, paper_id: str, status: PaperStatus, error: str = "") -> None:
        item = self.storage.get_item("papers", paper_id)
        if item:
            item["status"] = status.value
            if error:
                item["error_message"] = error
            self.storage.upsert_item("papers", paper_id, item)

    def _get_pool_id(self, paper: Paper) -> str:
        """获取论文在 papers_pool 中的 ID"""
        if paper.source_payload:
            pid = paper.source_payload.get("pool_paper_id", "")
            if pid:
                return pid
        if paper.identifiers:
            if paper.identifiers.doi:
                return f"doi_{paper.identifiers.doi.replace('/', '_').replace('.', '_')}"
            if paper.identifiers.arxiv_id:
                return f"arxiv_{paper.identifiers.arxiv_id}"
            if paper.identifiers.openalex_id:
                return f"oa_{paper.identifiers.openalex_id}"
            if paper.identifiers.semantic_scholar_id:
                return f"s2_{paper.identifiers.semantic_scholar_id}"
        return ""

    def _update_pool_field(self, paper: Paper, field: str, value: Any) -> None:
        """更新 papers_pool 中的单个字段"""
        pool_id = self._get_pool_id(paper)
        if not pool_id:
            return
        pool_item = self.storage.load_from_folder("papers_pool", pool_id)
        if pool_item:
            pool_item[field] = value
            self.storage.save_to_folder("papers_pool", pool_id, pool_item)

    def _mark_pool_pdf_downloaded(self, paper: Paper) -> None:
        """标记 papers_pool 中对应记录的 is_pdf_downloaded = True"""
        self._update_pool_field(paper, "is_pdf_downloaded", True)

    def _mark_pool_parsed(self, paper: Paper) -> None:
        """标记 papers_pool 中对应记录的 is_parsed = True"""
        self._update_pool_field(paper, "is_parsed", True)

    # ── 多解析器 fallback ────────────────────────────────

    def _extract_with_fallback(
        self, pdf_path: str
    ) -> tuple[list[tuple[int, str]], str, list[str]]:
        """多解析器 fallback 链路

        流程：
        1. 扫描件预检测 → 直接走 OCR
        2. 遍历文本提取器（pymupdf4llm → PdfPlumber → PyMuPDF → PdfMiner → Docling）
        3. 每个提取器成功后做乱码检测，乱码则尝试下一个
        4. 所有文本提取器失败 → OCR 最终 fallback

        Returns:
            (pages_text, parser_name, quality_flags)
        """
        quality_flags: list[str] = []

        # 阶段 0：扫描件预检测
        scan_result = self._detect_scanned_pdf(pdf_path)
        if scan_result["is_scanned"]:
            quality_flags.append("scanned_pdf_suspected")
            quality_flags.append(f"scan_confidence={scan_result['confidence']:.2f}")
            pages_text, parser_name, ocr_flags = self._try_ocr_fallback(pdf_path)
            quality_flags.extend(ocr_flags)
            return pages_text, parser_name, quality_flags

        # 阶段 1-3：文本提取器 fallback
        for adapter in self._adapters:
            if not adapter.can_parse(pdf_path):
                quality_flags.append(f"{adapter.name}_unavailable")
                continue

            pages_text, flags = adapter.extract_pages(pdf_path)
            quality_flags.extend(flags)

            if not pages_text or not any(t.strip() for _, t in pages_text):
                quality_flags.append(f"{adapter.name}_empty")
                continue

            # 中文乱码检测
            full_text = "\n".join(t for _, t in pages_text)
            if self._detect_garbled_text(full_text):
                quality_flags.append("garbled_text_detected")
                quality_flags.append(f"{adapter.name}_garbled")
                logger.warning(f"Garbled text detected with {adapter.name}: {pdf_path}")
                continue

            # 单词间距质量检测：过多超长无空格词 → 文本质量差，尝试下一个
            if self._detect_poor_spacing(full_text):
                quality_flags.append("poor_word_spacing")
                quality_flags.append(f"{adapter.name}_spacing")
                logger.warning(f"Poor word spacing with {adapter.name}: {pdf_path}")
                continue

            # 成功
            return pages_text, adapter.name, quality_flags

        # 阶段 4：OCR 最终 fallback
        pages_text, parser_name, ocr_flags = self._try_ocr_fallback(pdf_path)
        quality_flags.extend(ocr_flags)
        if pages_text:
            quality_flags.append("ocr_fallback_used")
            return pages_text, parser_name, quality_flags

        logger.warning(f"No text extracted from {pdf_path}, all adapters failed")
        quality_flags.append("all_adapters_failed")
        return [], "none", quality_flags

    def _try_ocr_fallback(
        self, pdf_path: str
    ) -> tuple[list[tuple[int, str]], str, list[str]]:
        """尝试 OCR fallback（当前仅检测，不自动执行 OCR）"""
        flags: list[str] = []
        # PaddleOCR 需要额外依赖，当前只标记
        flags.append("ocr_not_implemented")
        return [], "none", flags

    def _detect_scanned_pdf(self, pdf_path: str) -> dict[str, Any]:
        """检测 PDF 是否为扫描件（基于图片数量和文本量）

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
                if len(text) < 50 and len(images) > 0:
                    image_pages += 1
                elif len(text) >= 50:
                    text_pages += 1
            doc.close()

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

    # ── 中文 PDF 处理 ────────────────────────────────────

    def _detect_garbled_text(self, text: str) -> bool:
        """检测文本是否包含乱码（知网/万方 PDF 常见问题）

        检测策略：
        1. CNKI 特征乱码字符（重复罕见 Unicode 字符）
        2. 控制字符
        3. 替换字符（□■◆◇○●）
        4. 高比例非 CJK 非 ASCII 字符
        """
        if not text or len(text) < 50:
            return False

        # 1. 控制字符检测
        control_chars = sum(1 for c in text if ord(c) < 0x20 and c not in '\n\r\t')
        if control_chars > len(text) * 0.05:
            return True

        # 2. 替换字符检测
        replacement_chars = sum(1 for c in text if c in '□■◆◇○●◈◊■□')
        if replacement_chars > len(text) * 0.02:
            return True

        # 3. CNKI 特征乱码：连续重复的罕见 CJK 扩展区字符
        garbled_pattern = re.compile(r'[\U00020000-\U0002A6DF]{3,}')
        if garbled_pattern.search(text):
            return True

        # 4. 高比例异常字符（非 ASCII、非 CJK 基本区、非常用标点）
        total = len(text)
        abnormal = 0
        for c in text:
            cp = ord(c)
            if cp < 0x80:  # ASCII
                continue
            if 0x4E00 <= cp <= 0x9FFF:  # CJK 基本区
                continue
            if 0x3400 <= cp <= 0x4DBF:  # CJK 扩展 A
                continue
            if 0xFF00 <= cp <= 0xFFEF:  # 全角字符
                continue
            if 0x3000 <= cp <= 0x303F:  # CJK 符号和标点
                continue
            if c in '\n\r\t ':
                continue
            abnormal += 1
        if total > 100 and abnormal / total > 0.3:
            return True

        return False

    def _detect_poor_spacing(self, text: str) -> bool:
        """检测文本是否有严重的单词间距丢失问题

        策略：检查前 5 页中是否有大量超长无空格词（>20字符）
        如果任一页中超长词占比 > 30%，认为间距质量差
        """
        if not text or len(text) < 200:
            return False

        lines = text.split("\n")
        checked = 0
        for line in lines:
            words = line.split()
            if len(words) < 3:
                continue
            long_words = sum(1 for w in words if len(w) > 20 and not re.search(r"[\d\-_]", w))
            if long_words > 0 and long_words / len(words) > 0.3:
                return True
            checked += 1
            if checked > 200:
                break

        return False

    def _detect_watermark(self, pages_text: list[tuple[int, str]]) -> bool:
        """检测 PDF 是否包含水印（知网/万方常见水印）

        检测策略：
        1. 多页重复出现的短文本行
        2. 水印关键词匹配
        """
        if not pages_text or len(pages_text) < 2:
            return False

        # 收集所有非空行
        all_lines: list[str] = []
        for _, text in pages_text:
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) < 30:
                    all_lines.append(stripped)

        if not all_lines:
            return False

        # 1. 水印关键词检测
        watermark_keywords = [
            "知网", "CNKI", "万方", "维普", "Wanfang",
            "仅供", "个人使用", "未经授权", "禁止转载",
        ]
        for line in all_lines:
            for kw in watermark_keywords:
                if kw in line:
                    return True

        # 2. 重复短文本检测：同一条短文本在超过一半页面中出现
        from collections import Counter
        line_counts = Counter(all_lines)
        total_pages = len(pages_text)
        for line, count in line_counts.items():
            if count >= total_pages * 0.5 and len(line) < 20:
                return True

        return False

    # ── 参考文献结构化提取 ────────────────────────────────

    # 参考文献分割模式
    _REF_SPLIT_PATTERNS = [
        re.compile(r'^\[(\d+)\]\s*', re.MULTILINE),        # [1] Author...
        re.compile(r'^(\d+)\.\s+', re.MULTILINE),           # 1. Author...
        re.compile(r'^\[(\d+[-–]\d+)\]\s*', re.MULTILINE),  # [1-3] Author...
    ]

    # DOI 模式
    _DOI_PATTERN = re.compile(r'(10\.\d{4,}/[^\s,;]+)')

    # 年份模式（在括号中或独立出现）
    _YEAR_PATTERN = re.compile(r'\b((?:19|20)\d{2})\b')

    def _extract_references(self, ref_text: str, paper_id: str) -> list[Reference]:
        """从参考文献文本中提取结构化引用

        支持格式：
        - [1] Author. Title. Journal, Year.
        - 1. Author. Title. Journal, Year.
        - Author (Year). Title. Journal.
        """
        if not ref_text or len(ref_text.strip()) < 20:
            return []

        refs: list[Reference] = []

        # 尝试按编号模式分割
        entries = self._split_references(ref_text)

        for i, raw_text in enumerate(entries):
            raw_text = raw_text.strip()
            if not raw_text or len(raw_text) < 10:
                continue

            ref = Reference(
                ref_id=f"ref_{paper_id}_{i:04d}",
                citing_paper_id=paper_id,
                index=i,
                raw_text=raw_text,
            )

            # 提取 DOI
            doi_match = self._DOI_PATTERN.search(raw_text)
            if doi_match:
                ref.doi = doi_match.group(1).rstrip('.')

            # 提取年份
            year_match = self._YEAR_PATTERN.search(raw_text)
            if year_match:
                ref.year = int(year_match.group(1))

            # 提取标题（启发式：第一个句号前的内容，在作者之后）
            ref.title = self._guess_title(raw_text)

            # 提取作者（启发式：在第一个句号或括号之前的部分）
            ref.authors = self._guess_authors(raw_text)

            refs.append(ref)

        return refs

    # 无编号参考文献条目起始模式：Author (Year) 或 Author, Year
    _REF_ENTRY_START = re.compile(
        r'(?:^|\n)\s*'
        r'(?:[A-ZÀ-ÖØ-Þa-z][a-z]*\s+)?'   # 可选的前缀（de, van 等）
        r'[A-ZÀ-ÖØ-Þ][A-Za-z\-]+'          # 姓氏
        r'[,.\s()]?.*?'                       # 分隔符（允许无空格直接跟括号）
        r'(?:\(\s*\d{4}\s*\)|\d{4})'         # 年份：(2019) 或 2019
    )

    def _split_references(self, text: str) -> list[str]:
        """按编号模式分割参考文献条目

        支持格式：
        - [1] Author... / 1. Author...（编号格式）
        - Author (Year). Title. Journal.（无编号格式）
        """
        # 尝试 [N] 模式
        parts = re.split(r'(?:^|\n)\s*\[\d+\]\s*', text)
        if len(parts) > 2:
            return [p.strip() for p in parts if p.strip()]

        # 尝试 N. 模式
        parts = re.split(r'(?:^|\n)\s*\d+\.\s+', text)
        if len(parts) > 2:
            return [p.strip() for p in parts if p.strip()]

        # 尝试无编号格式：按 Author (Year) 模式分割
        entries = self._split_unnumbered_refs(text)
        if len(entries) > 2:
            return entries

        # 尝试按双换行分割
        parts = re.split(r'\n\s*\n', text)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        # 单条或无法分割
        return [text.strip()] if text.strip() else []

    def _split_unnumbered_refs(self, text: str) -> list[str]:
        """按 Author (Year) 模式分割无编号参考文献"""
        # 找到每个条目的起始位置
        starts = []
        for m in self._REF_ENTRY_START.finditer(text):
            # 条目从行首实际内容开始（跳过换行和空格）
            line_start = m.start()
            while line_start < len(text) and text[line_start] in '\n\r\t ':
                line_start += 1
            starts.append(line_start)

        if len(starts) < 2:
            return []

        # 按起始位置分割
        entries = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            entry = text[start:end].strip()
            if entry and len(entry) > 10:
                entries.append(entry)

        return entries

    def _guess_title(self, raw_text: str) -> str:
        """启发式提取参考文献标题

        策略：
        1. 匹配 Author (Year). Title. Journal 格式中的 Title
        2. 回退到第一个句号后的内容
        """
        # 去掉编号前缀
        cleaned = re.sub(r'^\[\d+\]\s*', '', raw_text.strip())
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)

        # 策略 1：找 (Year). 后面的内容作为标题
        year_match = re.search(r'\(\s*\d{4}[a-z]?\s*\)\.\s*', cleaned)
        if year_match:
            after_year = cleaned[year_match.end():]
            # 标题到下一个句号（后跟大写字母或行尾）为止
            title_match = re.match(r'(.+?)\.\s+[A-Z]', after_year)
            if title_match:
                title = title_match.group(1).strip()
            else:
                # 可能标题就是到行尾
                title = after_year.split('.')[0].strip()
            title = title.strip('"\'""''')
            if len(title) > 5:
                return title[:200]

        # 策略 2：第一个句号后的内容（回退）
        parts = cleaned.split('.', 2)
        if len(parts) >= 2:
            title = parts[1].strip()
            title = title.strip('"\'""''')
            if len(title) > 5:
                return title[:200]

        return ""

    def _guess_authors(self, raw_text: str) -> list[str]:
        """启发式提取参考文献作者"""
        # 去掉编号前缀
        cleaned = re.sub(r'^\[\d+\]\s*', '', raw_text.strip())
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)

        # 作者通常在第一个句号之前
        # 对于无编号格式 "Author (Year). Title."，取第一个句号前的部分
        first_sentence = cleaned.split('.', 1)[0].strip()

        # 去掉年份部分：(2019) 或 2019
        first_sentence = re.sub(r'\s*\(\s*\d{4}\s*\)\s*$', '', first_sentence)
        first_sentence = re.sub(r'\s+\d{4}\s*$', '', first_sentence)

        if not first_sentence or len(first_sentence) > 200:
            return []

        # 按逗号或 and 分割
        authors = re.split(r',\s*(?:and\s+)?|\s+and\s+', first_sentence)
        # 过滤掉非作者的片段（太长或包含常见非作者词汇）
        result = []
        non_author_words = {'et al', 'eds', 'eds.', 'vol', 'no', 'pp', 'p'}
        for a in authors:
            a = a.strip()
            if a and len(a) < 60 and a.lower() not in non_author_words:
                result.append(a)

        return result

    # ── 质量报告增强 ────────────────────────────────────

    def _check_quality_enhanced(
        self, pages_text: list[tuple[int, str]], section_count: int, chunk_count: int
    ) -> tuple[list[str], dict[str, Any]]:
        """增强版质量检查，返回 (quality_flags, diagnostics)"""
        flags = self._check_quality(pages_text)
        diagnostics: dict[str, Any] = {}

        full_text = "\n".join(t for _, t in pages_text)

        # 乱码检测
        if self._detect_garbled_text(full_text):
            if "garbled_text_detected" not in flags:
                flags.append("garbled_text_detected")
            diagnostics["garbled_text"] = True

        # 水印检测
        if self._detect_watermark(pages_text):
            flags.append("watermark_suspected")
            diagnostics["watermark"] = True

        # 双栏布局检测
        if self._detect_dual_column(pages_text):
            flags.append("dual_column_detected")
            diagnostics["dual_column"] = True

        # 章节覆盖率
        if pages_text and chunk_count > 0:
            total_lines = sum(len(t.split("\n")) for _, t in pages_text)
            section_ratio = section_count / max(chunk_count, 1)
            if section_ratio < 0.1 and total_lines > 50:
                flags.append("low_section_coverage")
                diagnostics["low_section_coverage"] = True

        diagnostics["total_chars"] = len(full_text)
        diagnostics["total_pages"] = len(pages_text)

        return flags, diagnostics

    def _detect_dual_column(self, pages_text: list[tuple[int, str]]) -> bool:
        """检测是否为双栏布局（基于行长度分布）"""
        if not pages_text:
            return False

        # 采样前 3 页
        sample_pages = pages_text[:3]
        short_line_pairs = 0
        total_line_pairs = 0

        for _, text in sample_pages:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for i in range(len(lines) - 1):
                total_line_pairs += 1
                # 双栏特征：连续两行都很短（< 40 字符），且长度相似
                if len(lines[i]) < 40 and len(lines[i + 1]) < 40:
                    if abs(len(lines[i]) - len(lines[i + 1])) < 10:
                        short_line_pairs += 1

        if total_line_pairs > 10 and short_line_pairs / total_line_pairs > 0.3:
            return True
        return False
