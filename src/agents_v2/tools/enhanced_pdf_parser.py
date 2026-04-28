"""
Enhanced PDF Parser - 多引擎PDF解析器

支持:
1. Marker - PDF转Markdown/LaTeX，保留公式和代码
2. Nougat - 学术论文公式识别 (Meta出品)
3. pdfplumber - 表格精确提取
4. PyMuPDF - 基础文本提取

架构:
    EnhancedPDFParser
        ├── MarkerPDFParser (公式、代码)
        ├── NougatPDFParser (学术公式)
        ├── TableExtractor (表格)
        └── LayoutAnalyzer (布局)
"""
import asyncio
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class PDFParserType(Enum):
    """PDF解析器类型"""
    MARKER = "marker"
    NOUGAT = "nougat"
    PDFPLUMBER = "pdfplumber"
    PYMUPDF = "pymupdf"
    AUTO = "auto"  # 自动选择最佳解析器


@dataclass
class Formula:
    """公式"""
    type: str  # "inline" 或 "display"
    latex: str
    mathml: str = ""
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    page: int = 0


@dataclass
class Table:
    """表格"""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    page: int = 0
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    caption: str = ""
    source: str = ""  # "pdfplumber", "marker"


@dataclass
class Figure:
    """图表"""
    filename: str = ""
    path: str = ""
    caption: str = ""
    alt_text: str = ""
    page: int = 0
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)


@dataclass
class PDFContent:
    """PDF内容结构"""
    text: str = ""
    markdown: str = ""
    latex: str = ""
    formulas: List[Formula] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    pages: int = 0
    layout_type: str = "unknown"


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    content: Optional[PDFContent] = None
    parser_used: str = ""
    error: str = ""
    warnings: List[str] = field(default_factory=list)


class MarkerConverter:
    """Marker转换器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._enabled = None

    def is_available(self) -> bool:
        if self._enabled is not None:
            return self._enabled

        try:
            result = subprocess.run(
                ["marker", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._enabled = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            self._enabled = False

        return self._enabled

    async def convert(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """转换PDF"""
        if not self.is_available():
            return {"success": False, "error": "Marker not available"}

        try:
            import tempfile
            import aiohttp

            if output_dir is None:
                output_dir = tempfile.mkdtemp()

            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            # 构建命令
            cmd = ["marker", "--markdown", "--output_dir", output_dir, file_path]

            if not self.config.get("use_gpu", True):
                cmd.insert(1, "--no-gpu")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=300
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return {"success": False, "error": f"Marker failed: {error_msg}"}

            # 读取输出
            stem = path.stem
            md_file = Path(output_dir) / f"{stem}.md"
            tex_file = Path(output_dir) / f"{stem}.tex"

            result = {
                "success": True,
                "markdown": md_file.read_text(encoding="utf-8") if md_file.exists() else "",
                "latex": tex_file.read_text(encoding="utf-8") if tex_file.exists() else "",
            }

            # 提取公式
            result["formulas"] = self._extract_formulas(result.get("latex", ""))

            return result

        except asyncio.TimeoutError:
            return {"success": False, "error": "Conversion timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_formulas(self, latex: str) -> List[Dict[str, str]]:
        """从LaTeX提取公式"""
        formulas = []

        # 显示公式: $$...$$
        for match in re.finditer(r"\$\$([\s\S]+?)\$\$", latex):
            formulas.append({
                "type": "display",
                "latex": match.group(1).strip(),
            })

        # 行内公式: $...$
        remaining = re.sub(r"\$\$[\s\S]+?\$\$", "", latex)
        for match in re.finditer(r"\$([^$\n]+?)\$", remaining):
            latex_content = match.group(1).strip()
            if latex_content and not re.match(r"^\d+\.?\d*", latex_content):
                formulas.append({
                    "type": "inline",
                    "latex": latex_content,
                })

        return formulas


class NougatConverter:
    """Nougat转换器 - Meta出品的学术论文公式识别"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._enabled = None

    def is_available(self) -> bool:
        if self._enabled is not None:
            return self._enabled

        try:
            result = subprocess.run(
                ["nougat", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._enabled = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            self._enabled = False

        return self._enabled

    async def convert(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """转换PDF"""
        if not self.is_available():
            return {"success": False, "error": "Nougat not available"}

        try:
            import tempfile

            if output_dir is None:
                output_dir = tempfile.mkdtemp()

            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            # Nougat输出格式: .mmd (MultiMarkdown)
            output_path = Path(output_dir) / f"{path.stem}.mmd"

            cmd = [
                "nougat",
                str(path),
                "-o", output_dir,
                "-m", "0",  # 模式: 0=页面batch
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=300
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return {"success": False, "error": f"Nougat failed: {error_msg}"}

            # 读取输出
            mmd_file = Path(output_dir) / f"{path.stem}.mmd"

            if mmd_file.exists():
                content = mmd_file.read_text(encoding="utf-8")
                return {
                    "success": True,
                    "markdown": content,
                    "latex": self._mmd_to_latex(content),
                    "formulas": self._extract_formulas(content),
                }
            else:
                return {"success": False, "error": "Output file not generated"}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Conversion timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _mmd_to_latex(self, mmd_content: str) -> str:
        """将MultiMarkdown转换为LaTeX"""
        latex = mmd_content

        # 处理显示公式
        latex = re.sub(r"\$\$([\s\S]+?)\$\$", r"\\[\1\\]", latex)

        # 处理行内公式
        latex = re.sub(r"\$([^\$]+?)\$", r"\\(\1\\)", latex)

        return latex

    def _extract_formulas(self, content: str) -> List[Dict[str, str]]:
        """提取公式"""
        formulas = []

        # 显示公式
        for match in re.finditer(r"\$\$([\s\S]+?)\$\$", content):
            formulas.append({
                "type": "display",
                "latex": match.group(1).strip(),
            })

        # 行内公式
        remaining = re.sub(r"\$\$[\s\S]+?\$\$", "", content)
        for match in re.finditer(r"\$([^\$]+?)\$", remaining):
            latex_content = match.group(1).strip()
            if latex_content:
                formulas.append({
                    "type": "inline",
                    "latex": latex_content,
                })

        return formulas


class TableExtractor:
    """表格提取器"""

    def __init__(self):
        self._available = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            import pdfplumber
            self._available = True
        except ImportError:
            self._available = False

        return self._available

    async def extract_tables(
        self,
        file_path: str,
    ) -> List[Table]:
        """提取表格"""
        if not self.is_available():
            return []

        try:
            import pdfplumber

            tables = []

            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()

                    for table_data in page_tables:
                        if not table_data:
                            continue

                        table = Table(
                            headers=[],
                            rows=[],
                            page=page_num + 1,
                            source="pdfplumber",
                        )

                        if table_data:
                            # 第一行作为表头
                            if len(table_data) > 0:
                                table.headers = [str(h) if h else "" for h in table_data[0]]
                                table.rows = [
                                    [str(c) if c else "" for c in row]
                                    for row in table_data[1:]
                                    if row
                                ]

                        # 获取表格位置
                        if hasattr(page, "tables"):
                            for t in page.tables:
                                if t.get("cells") == table_data:
                                    table.bbox = t.get("bbox", (0, 0, 0, 0))
                                    break

                        tables.append(table)

            return tables

        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            return []

    async def extract_tables_with_marker(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
    ) -> List[Table]:
        """使用Marker提取表格"""
        try:
            import tempfile
            import subprocess

            if output_dir is None:
                output_dir = tempfile.mkdtemp()

            path = Path(file_path)

            # 运行marker只提取表格
            cmd = ["marker", "--markdown", "--output_dir", output_dir, file_path]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=300
            )

            if process.returncode != 0:
                return []

            # 读取表格
            tables_dir = Path(output_dir) / "tables"
            if not tables_dir.exists():
                return []

            tables = []
            for table_file in tables_dir.glob("*.csv"):
                try:
                    content = table_file.read_text(encoding="utf-8")
                    lines = content.strip().split("\n")

                    if not lines:
                        continue

                    table = Table(
                        headers=[],
                        rows=[],
                        source="marker",
                        caption=table_file.stem,
                    )

                    # 解析CSV
                    import csv
                    import io

                    reader = csv.reader(io.StringIO(content))
                    rows_list = list(reader)

                    if rows_list:
                        table.headers = [str(h) for h in rows_list[0]]
                        table.rows = [[str(c) for c in row] for row in rows_list[1:] if row]

                    tables.append(table)

                except Exception as e:
                    logger.warning(f"Failed to parse table {table_file}: {e}")

            return tables

        except Exception as e:
            logger.error(f"Marker table extraction failed: {e}")
            return []


class EnhancedPDFParser:
    """
    增强PDF解析器

    自动选择最佳解析器组合:
    - Marker: 公式、代码、布局
    - Nougat: 学术公式（更精确）
    - pdfplumber: 表格
    """

    def __init__(
        self,
        preferred_parsers: Optional[List[PDFParserType]] = None,
        use_gpu: bool = True,
    ):
        self.preferred_parsers = preferred_parsers or [
            PDFParserType.MARKER,
            PDFParserType.NOUGAT,
            PDFParserType.PDFPLUMBER,
        ]
        self.use_gpu = use_gpu

        # 初始化各解析器
        self.marker = MarkerConverter({"use_gpu": use_gpu})
        self.nougat = NougatConverter()
        self.table_extractor = TableExtractor()

    async def parse(
        self,
        file_path: str,
        include_tables: bool = True,
        include_formulas: bool = True,
        include_layout: bool = True,
    ) -> ParseResult:
        """
        解析PDF文件

        Args:
            file_path: PDF文件路径
            include_tables: 是否提取表格
            include_formulas: 是否提取公式
            include_layout: 是否分析布局

        Returns:
            ParseResult
        """
        path = Path(file_path)
        if not path.exists():
            return ParseResult(
                success=False,
                error=f"File not found: {file_path}"
            )

        content = PDFContent()
        warnings = []
        parser_used = []

        # 1. 提取文本和公式 (优先使用Marker)
        if PDFParserType.MARKER in self.preferred_parsers and self.marker.is_available():
            result = await self.marker.convert(file_path)
            if result.get("success"):
                content.markdown = result.get("markdown", "")
                content.latex = result.get("latex", "")
                content.formulas = [
                    Formula(type=f["type"], latex=f["latex"])
                    for f in result.get("formulas", [])
                ]
                parser_used.append("marker")
            else:
                warnings.append(f"Marker failed: {result.get('error')}")

        # 如果Marker失败，尝试Nougat
        if not content.markdown and PDFParserType.NOUGAT in self.preferred_parsers:
            if self.nougat.is_available():
                result = await self.nougat.convert(file_path)
                if result.get("success"):
                    content.markdown = result.get("markdown", "")
                    content.latex = result.get("latex", "")
                    content.formulas = [
                        Formula(type=f["type"], latex=f["latex"])
                        for f in result.get("formulas", [])
                    ]
                    parser_used.append("nougat")
                else:
                    warnings.append(f"Nougat failed: {result.get('error')}")

        # 2. 提取表格
        if include_tables:
            tables = await self.table_extractor.extract_tables(file_path)
            if tables:
                content.tables = tables
                parser_used.append("pdfplumber")
            else:
                # 尝试Marker提取表格
                marker_tables = await self.table_extractor.extract_tables_with_marker(file_path)
                if marker_tables:
                    content.tables = marker_tables
                    parser_used.append("marker_tables")

        # 3. 提取基本文本 (fallback)
        if not content.markdown:
            text_result = await self._extract_basic_text(file_path)
            if text_result:
                content.text = text_result
                parser_used.append("pymupdf")

        # 4. 布局分析
        if include_layout:
            layout = await self._analyze_layout(file_path)
            content.metadata["layout"] = layout

        # 5. 元数据
        metadata = await self._extract_metadata(file_path)
        content.metadata.update(metadata)
        content.pages = metadata.get("pages", 0)

        return ParseResult(
            success=bool(content.text or content.markdown),
            content=content,
            parser_used="+".join(parser_used) if parser_used else "none",
            warnings=warnings
        )

    async def _extract_basic_text(self, file_path: str) -> str:
        """提取基本文本 (使用PyMuPDF)"""
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            return "\n\n".join(text_parts)

        except ImportError:
            try:
                from PyPDF2 import PdfReader

                text_parts = []
                reader = PdfReader(file_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                return "\n\n".join(text_parts)

            except Exception as e:
                logger.error(f"Basic text extraction failed: {e}")
                return ""

        except Exception as e:
            logger.error(f"Basic text extraction failed: {e}")
            return ""

    async def _analyze_layout(self, file_path: str) -> Dict[str, Any]:
        """分析页面布局"""
        try:
            import pdfplumber

            layouts = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages[:5]):  # 只分析前5页
                    page_text = page.extract_text() or ""

                    # 检测是否为双栏布局
                    is_double_column = self._detect_double_column(page_text)
                    layouts.append({
                        "page": i + 1,
                        "type": "double_column" if is_double_column else "single_column",
                        "width": page.width,
                        "height": page.height,
                    })

            # 确定整体布局
            double_column_count = sum(1 for l in layouts if l["type"] == "double_column")
            overall_layout = "double_column" if double_column_count > len(layouts) / 2 else "single_column"

            return {
                "overall": overall_layout,
                "pages": layouts,
            }

        except Exception as e:
            logger.error(f"Layout analysis failed: {e}")
            return {"overall": "unknown", "pages": []}

    def _detect_double_column(self, text: str) -> bool:
        """检测双栏布局"""
        if not text:
            return False

        lines = text.split("\n")
        if len(lines) < 10:
            return False

        # 检测缩进模式
        left_indent = 0
        right_indent = 0

        for line in lines[:20]:
            stripped = line.strip()
            if not stripped:
                continue

            leading_spaces = len(line) - len(line.lstrip())

            if leading_spaces < 20:
                left_indent += 1
            elif leading_spaces > 40:
                right_indent += 1

        return left_indent > 5 and right_indent > 5

    async def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取元数据"""
        metadata = {
            "title": "",
            "authors": [],
            "abstract": "",
            "keywords": [],
            "doi": "",
            "pages": 0,
        }

        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            metadata["pages"] = len(reader.pages)

            if hasattr(reader, "metadata") and reader.metadata:
                pdf_meta = reader.metadata
                if "/Title" in pdf_meta:
                    metadata["title"] = pdf_meta["/Title"]
                if "/Author" in pdf_meta:
                    authors_str = pdf_meta["/Author"]
                    metadata["authors"] = [a.strip() for a in authors_str.split(",")]

        except Exception:
            pass

        return metadata

    async def extract_formulas_only(self, file_path: str) -> List[Formula]:
        """只提取公式"""
        result = await self.parse(file_path, include_tables=False)
        if result.success and result.content:
            return result.content.formulas
        return []

    async def extract_tables_only(self, file_path: str) -> List[Table]:
        """只提取表格"""
        result = await self.parse(file_path, include_formulas=False)
        if result.success and result.content:
            return result.content.tables
        return []


# 便捷函数
async def parse_pdf(
    file_path: str,
    include_tables: bool = True,
    include_formulas: bool = True,
) -> ParseResult:
    """解析PDF文件"""
    parser = EnhancedPDFParser()
    return await parser.parse(file_path, include_tables, include_formulas)


async def extract_formulas(file_path: str) -> List[Formula]:
    """提取公式"""
    parser = EnhancedPDFParser()
    return await parser.extract_formulas_only(file_path)


async def extract_tables(file_path: str) -> List[Table]:
    """提取表格"""
    parser = EnhancedPDFParser()
    return await parser.extract_tables_only(file_path)


def get_tool_spec():
    """获取工具规格"""
    from .tool_spec import ToolSpec, ParameterSpec, ParameterType

    return ToolSpec(
        name="enhanced_pdf_parse",
        description="增强PDF解析，支持Marker/Nougat公式识别和表格提取",
        parameters=[
            ParameterSpec(
                name="file_path",
                description="PDF文件路径",
                type=ParameterType.STRING,
                required=True,
            ),
            ParameterSpec(
                name="include_tables",
                description="是否提取表格",
                type=ParameterType.BOOLEAN,
                required=False,
                default=True,
            ),
            ParameterSpec(
                name="include_formulas",
                description="是否提取公式",
                type=ParameterType.BOOLEAN,
                required=False,
                default=True,
            ),
        ],
        handler=parse_pdf,
        category="document",
    )
