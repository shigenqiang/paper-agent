"""
PDF解析器 - 论文PDF文档深度解析

功能:
1. PDF文本提取
2. 表格检测与提取
3. 图表识别
4. 参考文献解析
5. 论文结构化（标题、摘要、正文、引用）
"""
from src.agents_v2.logging_config import get_logging_logger

import re

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = get_logging_logger(__name__)


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
    layout_type: str = "unknown"  # "single_column", "double_column", "mixed"
    page_dimensions: Tuple[float, float] = (0, 0)  # width, height in points


class LayoutDetector:
    """PDF布局检测器"""

    def __init__(self):
        self.column_threshold = 0.45  # 页面宽度比例阈值
        self.min_column_height = 100   # 最小栏高度（像素）

    def detect_layout(self, page_text: str, page_width: float, page_height: float) -> str:
        """检测页面布局类型

        Returns:
            "single_column": 单栏布局
            "double_column": 双栏布局
            "mixed": 混合格局
        """
        if not page_text:
            return "single_column"

        lines = page_text.split('\n')

        # 检查是否有明显的两栏特征
        left_aligned = 0
        right_aligned = 0
        center_aligned = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 估算行起始位置比例
            # 这里用字符数来估算（简化版）
            indent_ratio = len(line) / max(len(page_text.split('\n')[0]), 1) if page_text.split('\n') else 0.5

            if indent_ratio < 0.35:
                left_aligned += 1
            elif indent_ratio > 0.65:
                right_aligned += 1
            else:
                center_aligned += 1

        total_lines = len([l for l in lines if l.strip()])

        if total_lines < 10:
            return "single_column"

        left_ratio = left_aligned / total_lines
        right_ratio = right_aligned / total_lines

        # 双栏特征：左对齐和右对齐的比例都较高
        if left_ratio > 0.3 and right_ratio > 0.3:
            return "double_column"
        elif left_ratio > 0.4 or right_ratio > 0.4:
            return "mixed"
        else:
            return "single_column"

    def should_use_two_column_extraction(self, page_text: str) -> bool:
        """判断是否需要使用双栏提取"""
        # 检测常见的双栏论文特征
        double_column_indicators = [
            '1 Introduction',
            '2 Related',
            '3 Method',
            '4 Experiment',
            '5 Conclusion',
            '1.',
            '2.',
            'REFERENCES',
        ]

        text_lower = page_text.lower()
        matches = sum(1 for ind in double_column_indicators if ind in text_lower)

        return matches >= 2

    def extract_text_blocks(self, page_text: str, layout: str) -> List[Tuple[str, int]]:
        """提取文本块

        Returns:
            List of (text_block, block_column) tuples
            block_column: 0 = left, 1 = right, -1 = full width
        """
        if layout == "single_column":
            return [(page_text, -1)]

        blocks = []
        lines = page_text.split('\n')

        # 简单的分栏逻辑：按页面的水平位置估计
        # 实际应用中应该使用更精确的位置信息
        if layout == "double_column":
            mid_point = len(max(lines, key=len)) // 2

            left_lines = []
            right_lines = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                # 估算行属于左栏还是右栏
                # 通过分析缩进和内容分布
                leading_spaces = len(line) - len(line.lstrip())

                if leading_spaces > 10:
                    # 明显缩进，可能属于右栏
                    right_lines.append(line)
                else:
                    # 检查内容分布
                    words = stripped.split()
                    if len(stripped) < mid_point:
                        left_lines.append(line)
                    else:
                        # 长行可能跨两栏或者是右栏
                        if any(c.isdigit() for c in stripped[:10]):
                            right_lines.append(line)
                        else:
                            left_lines.append(line)

            if left_lines:
                blocks.append(('\n'.join(left_lines), 0))
            if right_lines:
                blocks.append(('\n'.join(right_lines), 1))

        return blocks if blocks else [(page_text, -1)]

    def is_cross_column_title(self, line: str, page_text: str) -> bool:
        """检测是否跨栏标题（如章节标题居中）"""
        line_stripped = line.strip()

        # 常见的跨栏标题特征
        cross_column_patterns = [
            r'^\d+\s+[A-Z]',  # "1 Introduction"
            r'^[A-Z][a-z]+\s+[A-Z]',  # "Related Work"
            r'^\s*[A-Z]{5,}\s*$',  # 全大写单词
        ]

        for pattern in cross_column_patterns:
            if re.match(pattern, line_stripped):
                return True

        return False

    def is_footnote(self, line: str, page_height: float, footnotes_start_y: float = 0.7) -> bool:
        """检测是否是脚注（位于页面底部）"""
        # 脚注通常在页面底部70%以后开始
        # 这需要实际的y坐标信息，这里做启发式判断
        if len(line) < 100 and re.match(r'^\d+\s+', line):
            # 数字开头的短行，可能是脚注引用
            return True
        return False


class PDFParser:
    """
    PDF解析器

    支持:
    - 文本提取
    - 结构化解析（标题、作者、摘要）
    - 章节检测
    - 参考文献提取
    - 表格检测
    - 双栏布局检测与正确提取
    """

    def __init__(self):
        self.text = ""
        self.layout_detector = LayoutDetector()
        self.layout_type = "unknown"
        self.page_texts = []  # 保存每页的文本用于布局分析

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
        """从PyPDF2 reader提取内容（支持双栏布局检测）"""
        self.text = ""
        self.page_texts = []

        # 提取所有页面的文本，同时收集布局信息
        page_widths = []
        page_heights = []

        for page in reader.pages:
            text = page.extract_text()

            # 获取页面尺寸
            if hasattr(page, 'mediabox'):
                mediabox = page.mediabox
                page_widths.append(float(mediabox.width))
                page_heights.append(float(mediabox.height))

            if text:
                self.page_texts.append(text)
                self.text += text + "\n\n"

        # 检测整体布局类型
        self.layout_type = self._detect_overall_layout()

        # 解析元数据
        metadata = self._extract_metadata(reader)

        # 提取章节（考虑双栏布局）
        sections = self._extract_sections_with_layout()

        # 提取参考文献
        references = self._extract_references(self.text)

        # 获取典型页面尺寸
        avg_width = sum(page_widths) / len(page_widths) if page_widths else 612  # 默认 letter 宽度
        avg_height = sum(page_heights) / len(page_heights) if page_heights else 792  # 默认 letter 高度

        return PDFParseResult(
            success=True,
            metadata=metadata,
            sections=sections,
            references=references,
            full_text=self.text,
            num_pages=len(reader.pages),
            layout_type=self.layout_type,
            page_dimensions=(avg_width, avg_height)
        )

    def _detect_overall_layout(self) -> str:
        """检测整体布局类型"""
        if not self.page_texts:
            return "unknown"

        double_column_count = 0
        single_column_count = 0

        for page_text in self.page_texts[:5]:  # 只检查前5页
            # 估算页面宽度（基于最长的行）
            max_line_len = max(len(line) for line in page_text.split('\n')) if page_text else 0

            # 双栏论文通常行较短（~40-60字符），单栏行较长（~80+字符）
            if max_line_len < 70 and self.layout_detector.should_use_two_column_extraction(page_text):
                double_column_count += 1
            else:
                single_column_count += 1

        if double_column_count > single_column_count:
            return "double_column"
        elif single_column_count > double_column_count:
            return "single_column"
        else:
            return "mixed"

    def _extract_sections_with_layout(self) -> List[PDFSection]:
        """考虑布局的章节提取"""
        sections = []

        # 使用文本重组：如果是双栏，先尝试按阅读顺序合并
        processed_text = self.text

        if self.layout_type == "double_column":
            processed_text = self._reorder_double_column_text()

        # 然后进行章节提取
        return self._extract_sections(processed_text)

    def _reorder_double_column_text(self) -> str:
        """重新排序双栏文本（按阅读顺序）"""
        if len(self.page_texts) < 2:
            return self.text

        reordered_lines = []

        for page_text in self.page_texts:
            lines = page_text.split('\n')

            # 分离可能属于不同栏的内容
            left_content = []
            right_content = []
            cross_column_titles = []

            for line in lines:
                stripped = line.strip()

                if self.layout_detector.is_cross_column_title(stripped, page_text):
                    cross_column_titles.append(line)
                elif len(stripped) < 50 and re.match(r'^\d+\.\d+\s', stripped):
                    # 子章节标题，通常是左对齐
                    cross_column_titles.append(line)
                else:
                    # 估算属于哪一栏
                    leading_spaces = len(line) - len(line.lstrip())
                    if leading_spaces > 15:
                        right_content.append(line)
                    else:
                        left_content.append(line)

            # 先添加跨栏标题，再按左右顺序添加内容
            reordered_lines.extend(cross_column_titles)
            reordered_lines.extend(left_content)
            reordered_lines.extend(right_content)

        return '\n'.join(reordered_lines)

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
