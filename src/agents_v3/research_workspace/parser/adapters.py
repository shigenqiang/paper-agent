"""PDF 解析器适配器协议与实现"""

from __future__ import annotations

from typing import Protocol

from loguru import logger


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

        left_count = sum(1 for b in valid if (b[0] + b[2]) / 2 < mid)
        right_count = sum(1 for b in valid if (b[0] + b[2]) / 2 > mid)

        if left_count < 2 or right_count < 2:
            return None

        balance = min(left_count, right_count) / max(left_count, right_count)
        if balance < 0.3:
            return None

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
