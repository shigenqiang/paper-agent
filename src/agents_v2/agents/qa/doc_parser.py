"""
学术文档解析器 - Academic Document Parser

支持 PDF/Markdown/HTML 格式的学术文档解析，
提取元数据（标题、作者、摘要、参考文献、页码等）。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
from src.agents_v2.logging_config import get_logging_logger

import re

logger = get_logging_logger(__name__)


@dataclass
class ParsedDocument:
    """解析后的文档"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    references: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class DocumentParser:
    """学术文档解析器

    支持多种格式的学术文档解析：
    - PDF: 使用 pdfplumber 或 PyMuPDF
    - Markdown: 直接解析
    - HTML: 使用 BeautifulSoup
    """

    SUPPORTED_FORMATS = {"pdf", "markdown", "md", "html", "htm"}

    def __init__(self):
        self.pdf_parser = None
        self._init_parsers()

    def _init_parsers(self):
        """初始化各格式解析器"""
        # PDF 解析器
        try:
            import pdfplumber
            self.pdf_parser = pdfplumber
            logger.info("pdfplumber available")
        except ImportError:
            try:
                import pymupdf
                self.pdf_parser = pymupdf
                logger.info("pymupdf available")
            except ImportError:
                logger.warning("No PDF parser available (pdfplumber/pymupdf)")

        # Markdown/HTML 解析器
        try:
            from bs4 import BeautifulSoup
            self.html_parser = BeautifulSoup
            logger.info("BeautifulSoup available")
        except ImportError:
            logger.warning("BeautifulSoup not available")
            self.html_parser = None

    def parse(self, file_path: str) -> ParsedDocument:
        """解析学术文档

        Args:
            file_path: 文档路径

        Returns:
            ParsedDocument: 解析结果
        """
        path = Path(file_path)
        ext = path.suffix.lower().lstrip(".")

        if ext not in self.SUPPORTED_FORMATS:
            return ParsedDocument(
                content="",
                errors=[f"Unsupported format: {ext}"]
            )

        try:
            if ext == "pdf":
                return self._parse_pdf(file_path)
            elif ext in ("markdown", "md"):
                return self._parse_markdown(file_path)
            elif ext in ("html", "htm"):
                return self._parse_html(file_path)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return ParsedDocument(content="", errors=[str(e)])

    def _parse_pdf(self, file_path: str) -> ParsedDocument:
        """解析 PDF 文档"""
        if self.pdf_parser is None:
            return ParsedDocument(
                content="",
                errors=["No PDF parser available"]
            )

        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                text_pages = []
                metadata = {}
                sections = []
                references = []

                # 提取元数据
                if pdf.metadata:
                    metadata = {
                        "title": pdf.metadata.get("Title", ""),
                        "authors": pdf.metadata.get("Author", ""),
                        "subject": pdf.metadata.get("Subject", ""),
                        "creator": pdf.metadata.get("Creator", ""),
                    }

                # 按页提取文本
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    text_pages.append({
                        "page_num": i + 1,
                        "text": text,
                        "width": page.width,
                        "height": page.height,
                    })

                full_text = "\n\n".join(p["text"] for p in text_pages)

                # 提取摘要（假设在文档开头）
                abstract = self._extract_abstract(full_text)
                if abstract:
                    metadata["abstract"] = abstract

                # 提取章节结构
                sections = self._extract_sections(full_text)

                # 提取参考文献
                references = self._extract_references(full_text)

                return ParsedDocument(
                    content=full_text,
                    metadata={
                        **metadata,
                        "total_pages": len(pdf.pages),
                        "file_path": file_path,
                    },
                    sections=sections,
                    references=references,
                )

        except ImportError:
            # pdfplumber 不可用，尝试 PyMuPDF
            return self._parse_pdf_pymupdf(file_path)
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return ParsedDocument(content="", errors=[str(e)])

    def _parse_pdf_pymupdf(self, file_path: str) -> ParsedDocument:
        """使用 PyMuPDF 解析 PDF"""
        try:
            import pymupdf

            doc = pymupdf.open(file_path)
            text_pages = []
            metadata = {}

            # 提取元数据
            if doc.metadata:
                metadata = {
                    "title": doc.metadata.get("title", ""),
                    "authors": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                }

            # 按页提取
            for i, page in enumerate(doc):
                text = page.get_text() or ""
                text_pages.append({
                    "page_num": i + 1,
                    "text": text,
                })

            full_text = "\n\n".join(p["text"] for p in text_pages)

            # 提取摘要
            abstract = self._extract_abstract(full_text)
            if abstract:
                metadata["abstract"] = abstract

            # 提取章节
            sections = self._extract_sections(full_text)

            # 提取参考文献
            references = self._extract_references(full_text)

            return ParsedDocument(
                content=full_text,
                metadata={
                    **metadata,
                    "total_pages": len(doc),
                    "file_path": file_path,
                },
                sections=sections,
                references=references,
            )

        except Exception as e:
            logger.error(f"PyMuPDF parsing failed: {e}")
            return ParsedDocument(content="", errors=[str(e)])

    def _parse_markdown(self, file_path: str) -> ParsedDocument:
        """解析 Markdown 文档"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            metadata = {}
            sections = []
            references = []

            # 提取 YAML front matter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    front_matter = parts[1]
                    content = parts[2]
                    for line in front_matter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip()] = value.strip()

            # 提取标题
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if title_match:
                metadata["title"] = title_match.group(1).strip()

            # 提取章节结构
            sections = self._extract_sections(content)

            # 提取参考文献
            references = self._extract_references(content)

            return ParsedDocument(
                content=content,
                metadata=metadata,
                sections=sections,
                references=references,
            )

        except Exception as e:
            logger.error(f"Markdown parsing failed: {e}")
            return ParsedDocument(content="", errors=[str(e)])

    def _parse_html(self, file_path: str) -> ParsedDocument:
        """解析 HTML 文档"""
        if self.html_parser is None:
            return ParsedDocument(
                content="",
                errors=["BeautifulSoup not available"]
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = self.html_parser(html_content, "html.parser")

            # 提取标题
            title = ""
            if soup.title:
                title = soup.title.string or ""
            metadata = {"title": title}

            # 提取文本（移除脚本和样式）
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)

            # 提取章节（基于 h1-h6 标签）
            sections = []
            for i, tag in enumerate(soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])):
                sections.append({
                    "level": int(tag.name[1]),
                    "title": tag.get_text(strip=True),
                    "index": i,
                })

            return ParsedDocument(
                content=text,
                metadata=metadata,
                sections=sections,
                references=[],
            )

        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return ParsedDocument(content="", errors=[str(e)])

    def _extract_abstract(self, text: str) -> Optional[str]:
        """提取摘要

        策略：
        1. 查找 "Abstract" 或 "摘要" 标题
        2. 提取到下一节标题前的文本
        """
        patterns = [
            r"(?:^|\n)(?:Abstract|摘要)\s*\n(.*?)(?=\n\s*(?:1\.|Introduction|一、|二、))",
            r"(?:^|\n)(?:Abstract|摘要)\s*[:：]?\s*(.*?)(?=\n\s*\n)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            if match:
                abstract = match.group(1).strip()
                if len(abstract) > 50:  # 摘要应该有最低长度
                    return abstract

        return None

    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """提取章节结构

        识别常见的学术论文章节标题。
        """
        sections = []

        # 中英文标题模式
        section_patterns = [
            # 英文标题
            r"(?m)^(1\.\s+\w+.+)$",
            r"(?m)^(2\.\s+\w+.+)$",
            r"(?m)^(3\.\s+\w+.+)$",
            r"(?m)^(4\.\s+\w+.+)$",
            r"(?m)^(5\.\s+\w+.+)$",
            r"(?m)^([A-Z][A-Z\s]+)$",  # 全大写标题
            # 中文标题
            r"(?m)^(一、.+)$",
            r"(?m)^(二、.+)$",
            r"(?m)^(三、.+)$",
            r"(?m)^(四、.+)$",
            r"(?m)^(五、.+)$",
            r"(?m)^(第[一二三四五]章\s+.+)$",
            # 通用标题
            r"(?m)^(#{1,6}\s+.+)$",  # Markdown 标题
        ]

        current_section = None
        for pattern in section_patterns:
            for match in re.finditer(pattern, text):
                title = match.group(1).strip()

                # 跳过太短的标题
                if len(title) < 3:
                    continue

                # 判断层级
                level = 1
                if title.startswith("#"):
                    level = len(title.split()[0])
                    title = " ".join(title.split()[1:])

                sections.append({
                    "title": title,
                    "level": level,
                    "position": match.start(),
                })

        # 按位置排序
        sections.sort(key=lambda x: x["position"])

        return sections[:50]  # 限制返回数量

    def _extract_references(self, text: str) -> List[Dict[str, Any]]:
        """提取参考文献

        策略：
        1. 查找 "References" 或 "参考文献" 标题
        2. 解析每个参考文献条目
        """
        references = []

        # 查找参考文献部分开始
        ref_patterns = [
            r"(?:^|\n)(?:References|参考文献|Reference|Bibliography)\s*\n",
        ]

        ref_start = -1
        for pattern in ref_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                ref_start = match.end()
                break

        if ref_start == -1:
            return references

        ref_text = text[ref_start:]
        if len(ref_text) > 50000:  # 限制处理长度
            ref_text = ref_text[:50000]

        # 解析参考文献条目
        # 常见格式：
        # [1] Authors. Title. Venue. Year.
        # [1] Authors. "Title". Venue, Year.
        entry_pattern = r"\[\d+\]\s*([^\[\]\n]+)"

        for match in re.finditer(entry_pattern, ref_text):
            entry = match.group(1).strip()
            if len(entry) > 20:  # 过滤太短的条目
                references.append({
                    "text": entry,
                    "position": ref_start + match.start(),
                })

        return references[:100]  # 限制返回数量


# 便捷函数
def parse_document(file_path: str) -> ParsedDocument:
    """解析文档的便捷函数"""
    parser = DocumentParser()
    return parser.parse(file_path)