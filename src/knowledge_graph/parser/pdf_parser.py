"""
PDF学术论文解析器
Academic Paper PDF Parser
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from ..schema.academic_kg_schema import ParsedDocument


@dataclass
class PDFMetadata:
    """PDF元数据"""
    title: str = ""
    authors: List[str] = None
    abstract: str = ""
    keywords: List[str] = None
    doi: str = ""
    year: int = None
    venue: str = ""
    raw_metadata: Dict = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []
        if self.raw_metadata is None:
            self.raw_metadata = {}


class PDFAcademicParser:
    """学术论文PDF解析器"""

    def __init__(self):
        self.pdfplumber_parser = None
        self.pymupdf_parser = None

        if PDFPLUMBER_AVAILABLE:
            self.pdfplumber_parser = PDFPlumberParser()

        if PYMUPDF_AVAILABLE:
            self.pymupdf_parser = PyMuPDFParser()

    def parse(self, file_path: str) -> ParsedDocument:
        """解析学术文档"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".pdf":
            return self._parse_pdf(file_path)
        elif path.suffix.lower() in [".txt", ".md"]:
            return self._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def _parse_pdf(self, file_path: str) -> ParsedDocument:
        """解析PDF文件"""
        if self.pdfplumber_parser:
            return self.pdfplumber_parser.parse(file_path)
        elif self.pymupdf_parser:
            return self.pymupdf_parser.parse(file_path)
        else:
            raise RuntimeError("No PDF parser available. Install pdfplumber or PyMuPDF.")

    def _parse_text(self, file_path: str) -> ParsedDocument:
        """解析文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = self._extract_basic_metadata(content)

        return ParsedDocument(
            file_path=file_path,
            content=content,
            metadata=metadata,
            pages=[{"page_num": 1, "text": content}],
            sections=self._extract_sections(content)
        )

    def _extract_basic_metadata(self, content: str) -> Dict[str, Any]:
        """提取基本元数据"""
        return {
            "title": self._extract_title(content),
            "authors": self._extract_authors(content),
            "abstract": self._extract_abstract(content),
            "keywords": self._extract_keywords(content)
        }

    def _extract_title(self, content: str) -> str:
        """提取论文标题"""
        lines = content.split("\n")
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if len(line) > 10 and len(line) < 300:
                return line
        return "Unknown Title"

    def _extract_authors(self, content: str) -> List[str]:
        """提取作者列表"""
        authors = []

        # 尝试从开头提取
        author_pattern = r"([A-Z][a-z]+ [A-Z][a-z]+)"
        matches = re.findall(author_pattern, content[:2000])
        authors.extend(matches[:10])

        return authors

    def _extract_abstract(self, content: str) -> str:
        """提取摘要"""
        abstract_pattern = r"(?:Abstract|Luogo)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z])"
        match = re.search(abstract_pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        keyword_pattern = r"(?:Keywords?|Index Terms)\s*[:\-]?\s*(.+?)(?:\n\n|\n)"
        match = re.search(keyword_pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            keywords_text = match.group(1)
            keywords = re.split(r"[,;·]", keywords_text)
            return [k.strip() for k in keywords if k.strip()]
        return []


class PDFPlumberParser:
    """基于pdfplumber的解析器"""

    def parse(self, file_path: str) -> ParsedDocument:
        """解析PDF"""
        if not PDFPLUMBER_AVAILABLE:
            raise RuntimeError("pdfplumber not available")

        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            # 提取文本
            full_text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )

            # 提取元数据
            raw_metadata = pdf.metadata or {}
            metadata = self._extract_metadata(raw_metadata, full_text)

            # 提取页面信息
            pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                pages.append({
                    "page_num": i + 1,
                    "text": text,
                    "tables": tables
                })

            # 提取文档结构
            sections = self._extract_sections(full_text)

        return ParsedDocument(
            file_path=file_path,
            content=full_text,
            metadata=metadata,
            pages=pages,
            sections=sections
        )

    def _extract_metadata(self, raw_metadata: Dict, full_text: str) -> Dict:
        """提取元数据"""
        metadata = {
            "title": raw_metadata.get("Title", ""),
            "authors": self._parse_authors(raw_metadata.get("Author", "")),
            "abstract": "",
            "keywords": [],
            "doi": raw_metadata.get("DOI", ""),
            "year": raw_metadata.get("CreationDate", "")
        }

        # 从文本中提取摘要
        metadata["abstract"] = self._extract_abstract(full_text)
        metadata["keywords"] = self._extract_keywords(full_text)

        return metadata

    def _parse_authors(self, author_string: str) -> List[str]:
        """解析作者字符串"""
        if not author_string:
            return []

        # 常见分隔符
        for sep in [";", ",", "and", "&"]:
            if sep in author_string:
                authors = author_string.split(sep)
                return [a.strip() for a in authors if a.strip()]

        return [author_string.strip()]

    def _extract_abstract(self, text: str) -> str:
        """提取摘要"""
        patterns = [
            r"(?:Abstract)\s*[:\-]?\s*(.+?)(?:\n\n|\n\n\n)",
            r"(?:摘要)\s*[:\-]?\s*(.+?)(?:\n\n|\n\n\n)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        patterns = [
            r"(?:Keywords?|Index Terms)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z])",
            r"(?:关键词)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z])",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                keywords_text = match.group(1)
                keywords = re.split(r"[,;·\n]", keywords_text)
                return [k.strip() for k in keywords if k.strip() and len(k.strip()) > 1]

        return []

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """提取文档章节"""
        sections = {}

        # 常见章节标题
        section_patterns = [
            r"(?m)^(1\.\s+(?:Introduction|简介))\s*$",
            r"(?m)^(2\.\s+(?:Related Work|相关工作))\s*$",
            r"(?m)^(3\.\s+(?:Methodology|方法))\s*$",
            r"(?m)^(4\.\s+(?:Experiment|实验))\s*$",
            r"(?m)^(5\.\s+(?:Conclusion|结论))\s*$",
            r"(?m)^(References|参考文献)\s*$",
        ]

        section_names = []
        for pattern in section_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            section_names.extend(matches)

        return sections


class PyMuPDFParser:
    """基于PyMuPDF的解析器"""

    def parse(self, file_path: str) -> ParsedDocument:
        """解析PDF"""
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF not available")

        import fitz

        doc = fitz.open(file_path)

        # 提取文本
        full_text = ""
        pages = []

        for i, page in enumerate(doc):
            text = page.get_text()
            full_text += text + "\n"
            pages.append({
                "page_num": i + 1,
                "text": text,
                "tables": []
            })

        # 提取元数据
        raw_metadata = doc.metadata
        metadata = self._extract_metadata(raw_metadata, full_text)

        # 提取章节结构
        sections = self._extract_sections(full_text)

        doc.close()

        return ParsedDocument(
            file_path=file_path,
            content=full_text,
            metadata=metadata,
            pages=pages,
            sections=sections
        )

    def _extract_metadata(self, raw_metadata: Dict, full_text: str) -> Dict:
        """提取元数据"""
        metadata = {
            "title": raw_metadata.get("title", ""),
            "authors": [],
            "abstract": "",
            "keywords": [],
            "doi": "",
            "year": None
        }

        # 从文本中提取更多信息
        if not metadata["title"]:
            metadata["title"] = self._extract_title(full_text)

        metadata["abstract"] = self._extract_abstract(full_text)

        return metadata

    def _extract_title(self, text: str) -> str:
        """提取标题"""
        lines = text.split("\n")
        for line in lines[:20]:
            line = line.strip()
            if 10 < len(line) < 200 and not line.endswith("."):
                return line
        return "Unknown Title"

    def _extract_abstract(self, text: str) -> str:
        """提取摘要"""
        patterns = [
            r"(?:Abstract)\s*[:\-]?\s*(.+?)(?:\n\n|\n\n\n)",
            r"(?:摘要)\s*[:\-]?\s*(.+?)(?:\n\n|\n\n\n)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """提取章节"""
        sections = {}
        return sections
