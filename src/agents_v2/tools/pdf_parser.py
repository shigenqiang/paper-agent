"""
PDF解析器 - 论文PDF文档深度解析

功能:
1. PDF文本提取
2. 表格检测与提取
3. 图表识别
4. 参考文献解析
5. 论文结构化（标题、摘要、正文、引用）
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PDFMetadata:
    """PDF元数据"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    publication_date: str = ""
    doi: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""


@dataclass
class PDFSection:
    """PDF章节"""
    title: str
    level: int  # 1 = 一级标题, 2 = 二级标题, etc
    start_page: int
    end_page: int
    content: str = ""


@dataclass
class PDFReference:
    """参考文献条目"""
    index: int
    authors: List[str] = field(default_factory=list)
    title: str = ""
    journal: str = ""
    year: str = ""
    volume: str = ""
    pages: str = ""
    doi: str = ""
    raw_text: str = ""


@dataclass
class PDFTable:
    """检测到的表格"""
    page: int
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    caption: str = ""


@dataclass
class PDFParseResult:
    """PDF解析结果"""
    success: bool
    metadata: PDFMetadata = field(default_factory=PDFMetadata)
    sections: List[PDFSection] = field(default_factory=list)
    references: List[PDFReference] = field(default_factory=list)
    tables: List[PDFTable] = field(default_factory=list)
    full_text: str = ""
    num_pages: int = 0
    error: Optional[str] = None


class PDFParser:
    """
    PDF解析器

    支持:
    - 文本提取
    - 结构化解析（标题、作者、摘要）
    - 章节检测
    - 参考文献提取
    - 表格检测
    """

    def __init__(self):
        self.text = ""

    async def parse_file(self, file_path: str) -> PDFParseResult:
        """
        解析PDF文件

        Args:
            file_path: PDF文件路径

        Returns:
            PDFParseResult
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return PDFParseResult(success=False, error=f"File not found: {file_path}")

            # 根据可用库选择解析方法
            try:
                from PyPDF2 import PdfReader
                return await self._parse_with_pypdf(file_path)
            except ImportError:
                try:
                    import pdfplumber
                    return await self._parse_with_pdfplumber(file_path)
                except ImportError:
                    return PDFParseResult(
                        success=False,
                        error="No PDF library available. Install PyPDF2: pip install PyPDF2"
                    )

        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return PDFParseResult(success=False, error=str(e))

    async def parse_bytes(self, pdf_bytes: bytes) -> PDFParseResult:
        """
        从字节流解析PDF

        Args:
            pdf_bytes: PDF文件字节数据

        Returns:
            PDFParseResult
        """
        try:
            try:
                from PyPDF2 import PdfReader
                import io
                reader = PdfReader(io.BytesIO(pdf_bytes))
                return await self._extract_from_pypdf_reader(reader)
            except ImportError:
                return PDFParseResult(
                    success=False,
                    error="PyPDF2 not available. Install: pip install PyPDF2"
                )
        except Exception as e:
            logger.error(f"PDF parsing from bytes failed: {e}")
            return PDFParseResult(success=False, error=str(e))

    async def _parse_with_pypdf(self, file_path: str) -> PDFParseResult:
        """使用PyPDF2解析"""
        from PyPDF2 import PdfReader
        import io

        reader = PdfReader(file_path)
        return await self._extract_from_pypdf_reader(reader)

    async def _extract_from_pypdf_reader(self, reader) -> PDFParseResult:
        """从PyPDF2 reader提取内容"""
        self.text = ""

        # 提取所有页面的文本
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.text += text + "\n\n"

        # 解析元数据
        metadata = self._extract_metadata(reader)

        # 提取章节
        sections = self._extract_sections(self.text)

        # 提取参考文献
        references = self._extract_references(self.text)

        return PDFParseResult(
            success=True,
            metadata=metadata,
            sections=sections,
            references=references,
            full_text=self.text,
            num_pages=len(reader.pages)
        )

    async def _parse_with_pdfplumber(self, file_path: str) -> PDFParseResult:
        """使用pdfplumber解析"""
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            self.text = ""
            tables = []

            for i, page in enumerate(pdf.pages):
                # 提取文本
                text = page.extract_text()
                if text:
                    self.text += text + "\n\n"

                # 提取表格
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table:
                        parsed_table = self._parse_table(table, i)
                        tables.append(parsed_table)

            # 解析元数据
            metadata = self._extract_metadata_from_text()

            # 提取章节
            sections = self._extract_sections(self.text)

            # 提取参考文献
            references = self._extract_references(self.text)

            return PDFParseResult(
                success=True,
                metadata=metadata,
                sections=sections,
                references=references,
                tables=tables,
                full_text=self.text,
                num_pages=len(pdf.pages)
            )

    def _extract_metadata(self, reader) -> PDFMetadata:
        """从PDF reader提取元数据"""
        metadata = PDFMetadata()

        # PyPDF2元数据
        if hasattr(reader, 'metadata'):
            pdf_meta = reader.metadata
            if pdf_meta:
                if '/Title' in pdf_meta:
                    metadata.title = pdf_meta['/Title']
                if '/Author' in pdf_meta:
                    authors_str = pdf_meta['/Author']
                    metadata.authors = [a.strip() for a in authors_str.split(',')]

        # 从文本提取
        return self._extract_metadata_from_text()

    def _extract_metadata_from_text(self) -> PDFMetadata:
        """从文本内容提取元数据"""
        metadata = PDFMetadata()

        # 提取标题（通常在第一页顶部）
        lines = self.text.split('\n')[:20]
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:
                # 跳过明显的非标题行
                if line.startswith('Abstract') or line.startswith('摘要'):
                    break
                if re.match(r'^\d+$', line):  # 页码
                    continue
                if len(line) < 100 and not line.endswith(':'):
                    metadata.title = line
                    break

        # 提取摘要
        abstract_match = re.search(
            r'(?:Abstract|摘要)\s*[:：]?\s*(.*?)(?=\n\s*(?:Keywords|关键词|1\.|Introduction))',
            self.text,
            re.DOTALL | re.IGNORECASE
        )
        if abstract_match:
            metadata.abstract = abstract_match.group(1).strip()

        # 提取关键词
        keywords_match = re.search(
            r'(?:Keywords|关键词)\s*[:：]?\s*(.*?)(?:\n|$)',
            self.text,
            re.IGNORECASE
        )
        if keywords_match:
            kw_text = keywords_match.group(1)
            metadata.keywords = [k.strip() for k in re.split(r'[,，;；]', kw_text) if k.strip()]

        # 提取DOI
        doi_match = re.search(
            r'doi[:\s]*(?:https?://)?(?:dx\.)?doi\.org/(.*?)(?:\s|$)',
            self.text,
            re.IGNORECASE
        )
        if doi_match:
            metadata.doi = doi_match.group(1).strip()

        # 提取作者（从文本）
        author_match = re.search(
            r'(?:Authors?|作者)\s*[:：]?\s*(.*?)(?:\n|$)',
            self.text,
            re.IGNORECASE
        )
        if author_match:
            authors_str = author_match.group(1)
            metadata.authors = [a.strip() for a in re.split(r'[,，;；\n]', authors_str) if a.strip()]

        return metadata

    def _extract_sections(self, text: str) -> List[PDFSection]:
        """提取章节"""
        sections = []

        # 常见章节标题模式
        section_patterns = [
            (r'^Abstract$', 1),
            (r'^Introduction$', 1),
            (r'^Background$', 1),
            (r'^Related Work$', 1),
            (r'^Preliminaries$', 1),
            (r'^Methodology$', 1),
            (r'^Approach$', 1),
            (r'^Proposed Method$', 1),
            (r'^Algorithm$', 1),
            (r'^Experiment(?:al Results)?$', 1),
            (r'^Results$', 1),
            (r'^Discussion$', 1),
            (r'^Conclusion(?:s)?$', 1),
            (r'^References$', 1),
            # 二级标题
            (r'^\d+\.\d+\s+[A-Z]', 2),
            (r'^[A-Z][a-z]+\s+[A-Z]', 2),
        ]

        lines = text.split('\n')
        current_section = None

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检查是否是章节标题
            matched = False
            for pattern, level in section_patterns:
                if re.match(pattern, line, re.MULTILINE | re.IGNORECASE):
                    # 保存之前的章节
                    if current_section:
                        current_section.content = text[current_section.start_page:i]

                    current_section = PDFSection(
                        title=line,
                        level=level,
                        start_page=i,
                        end_page=i
                    )
                    sections.append(current_section)
                    matched = True
                    break

            if current_section:
                current_section.end_page = i

        return sections

    def _extract_references(self, text: str) -> List[PDFReference]:
        """提取参考文献"""
        references = []

        # 查找参考文献部分
        ref_section_match = re.search(
            r'(?:References|Bibliography|参考文献)\s*\n(.*)',
            text,
            re.DOTALL | re.IGNORECASE
        )

        if not ref_section_match:
            return references

        ref_text = ref_section_match.group(1)

        # 按编号分割参考文献
        ref_pattern = r'\[(\d+)\]\s*(.*?)(?=\n\[\d+\]|$)'
        matches = re.finditer(ref_pattern, ref_text, re.DOTALL)

        for match in matches:
            index = int(match.group(1))
            raw_text = match.group(2).strip()

            ref = self._parse_reference(index, raw_text)
            references.append(ref)

        # 如果没找到编号格式，尝试作者年份格式
        if not references:
            ref_pattern = r'\[([^\]]+)\]\s*(.*?)(?=\n\s*\[|$)'
            matches = re.finditer(ref_pattern, ref_text, re.DOTALL)
            index = 1
            for match in matches:
                raw_text = match.group(2).strip()
                if len(raw_text) > 20:  # 过滤掉太短的
                    ref = self._parse_reference(index, raw_text)
                    references.append(ref)
                    index += 1

        return references

    def _parse_reference(self, index: int, raw_text: str) -> PDFReference:
        """解析单条参考文献"""
        ref = PDFReference(index=index, raw_text=raw_text)

        # 常见格式: "Smith, J. and Johnson, A. Deep Learning Methods. Nature, 2020."

        # 年份提取
        year_match = re.search(r'\((\d{4})\)|(\d{4})', raw_text)
        if year_match:
            ref.year = year_match.group(1) or year_match.group(2)

        # DOI提取
        doi_match = re.search(r'doi[:\s]*(.+?)(?:\s|$)', raw_text, re.IGNORECASE)
        if doi_match:
            ref.doi = doi_match.group(1).strip().rstrip('.,')

        # 解析：找到作者和标题的分隔
        # "Smith, J. and Johnson, A. Deep Learning Methods. Nature, 2020."
        # 策略：找到". "后面是大写字母开头且不是"and"的部分，这通常是标题的开始

        # 标题通常在". "之后（前面是作者部分）
        # 找出所有". "后面跟着大写字母的位置
        sentence_ends = [(m.start(), m.end()) for m in re.finditer(r'\.\s+[A-Z]', raw_text)]

        for end_pos, next_pos in sentence_ends:
            potential_title_start = next_pos
            # 检查这部分是不是"and"
            after_dot = raw_text[potential_title_start:]
            if after_dot.startswith('and '):
                continue

            # 找到了！这是标题的开始（. 后面是大写字母，说明是新句子的开始）
            author_part = raw_text[:end_pos]
            # 从匹配位置开始，但去掉". "得到标题开头
            title_and_rest = raw_text[end_pos+2:]  # 跳过". "或". D"

            # 标题通常是句子，到下一个". "结束
            title_match = re.match(r'^([^.]+)\.\s*(.*)', title_and_rest)
            if title_match:
                ref.title = title_match.group(1).strip()

                # 解析作者
                # "Smith, J. and Johnson, A." -> ["Smith, J.", "Johnson, A."]
                author_part = author_part.strip()
                ref.authors = [a.strip() for a in re.split(r'\s+and\s+', author_part) if a.strip()]

                # 解析期刊（标题之后的部分）
                rest = title_match.group(2).strip()
                # 去掉开头的标点和空格
                rest = re.sub(r'^[\[\],:\s]+', '', rest)
                # 提取年份
                rest_year = re.search(r'(\d{4})', rest)
                if rest_year:
                    ref.year = rest_year.group(1)
                    ref.journal = rest[:rest_year.start()].strip().rstrip(',').strip()
                else:
                    ref.journal = rest

                break

        return ref

    def _parse_table(self, table: List[List[str]], page: int) -> PDFTable:
        """解析表格"""
        if not table:
            return PDFTable(page=page, bbox=(0, 0, 0, 0))

        headers = table[0] if table else []
        rows = table[1:] if len(table) > 1 else []

        return PDFTable(
            page=page,
            bbox=(0, 0, 0, 0),  # bbox需要在pdfplumber中获取
            headers=headers,
            rows=rows
        )

    def extract_citations(self, text: str) -> List[str]:
        """提取正文中引用的参考文献ID"""
        # 匹配 [1], [1,2], [1-3] 等格式
        pattern = r'\[(\d+(?:[,-]\d+)*)\]'
        matches = re.finditer(pattern, text)

        citations = []
        for match in matches:
            citation = match.group(1)
            # 解析范围，如 "1-3" 扩展为 "1,2,3"
            if '-' in citation:
                parts = citation.split('-')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    start, end = int(parts[0]), int(parts[1])
                    citations.extend(str(i) for i in range(start, end + 1))
            else:
                citations.extend(citation.split(','))

        return list(set(citations))


# 便捷函数
async def parse_pdf(file_path: str) -> PDFParseResult:
    """解析PDF文件"""
    parser = PDFParser()
    return await parser.parse_file(file_path)


async def parse_pdf_bytes(pdf_bytes: bytes) -> PDFParseResult:
    """从字节解析PDF"""
    parser = PDFParser()
    return await parser.parse_bytes(pdf_bytes)


# 注册为工具
def get_tool_spec():
    """获取工具规格"""
    from .tool_spec import ToolSpec, ParameterSpec, ParameterType

    return ToolSpec(
        name="parse_pdf",
        description="解析PDF论文文档，提取文本、标题、作者、摘要、章节、参考文献和表格",
        parameters=[
            ParameterSpec(
                name="file_path",
                description="PDF文件路径",
                type=ParameterType.STRING,
                required=True
            )
        ],
        handler=parse_pdf,
        category="document"
    )
