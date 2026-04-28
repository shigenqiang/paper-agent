"""
Marker PDF Parser - 基于Marker的增强PDF解析

功能:
1. PDF转Markdown（保留公式和代码）
2. LaTeX公式提取
3. 表格结构化提取
4. 图表描述生成

Marker特点:
- 开源 (VikParuchuri/marker)
- 公式→LaTeX，代码块保留
- 支持GPU/CPU/MPS加速
"""
import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MarkerConfig:
    """Marker配置"""

    def __init__(
        self,
        model_name: str = "vikparuchuri/marker",
        max_pages: int = 50,
        output_format: str = "markdown",  # markdown, text, json
        use_gpu: bool = True,
        dtype: str = "float16",  # float32, float16, int8
        lang: str = "en",  # en, zh, mixed
    ):
        self.model_name = model_name
        self.max_pages = max_pages
        self.output_format = output_format
        self.use_gpu = use_gpu
        self.dtype = dtype
        self.lang = lang

    @classmethod
    def from_env(cls) -> "MarkerConfig":
        """从环境变量创建配置"""
        return cls(
            model_name=os.getenv("MARKER_MODEL", "vikparuchuri/marker"),
            max_pages=int(os.getenv("MARKER_MAX_PAGES", "50")),
            output_format=os.getenv("MARKER_OUTPUT_FORMAT", "markdown"),
            use_gpu=os.getenv("MARKER_USE_GPU", "true").lower() == "true",
            dtype=os.getenv("MARKER_DTYPE", "float16"),
            lang=os.getenv("MARKER_LANG", "en"),
        )


class MarkerPDFParser:
    """
    Marker PDF解析器

    将PDF转换为Markdown/LaTeX，保留公式和代码结构。
    """

    def __init__(self, config: Optional[MarkerConfig] = None):
        self.config = config or MarkerConfig.from_env()
        self._enabled = None  # 延迟检查

    def is_available(self) -> bool:
        """检查Marker是否可用"""
        if self._enabled is not None:
            return self._enabled

        try:
            # 检查marker命令是否可用
            result = subprocess.run(
                ["marker", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._enabled = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            self._enabled = False

        if not self._enabled:
            logger.warning(
                "Marker not available. Install: pip install marker-pdf"
                " or see: https://github.com/VikParuchuri/marker"
            )

        return self._enabled

    async def convert_file(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        转换PDF文件

        Args:
            file_path: PDF文件路径
            output_dir: 输出目录，默认为临时目录

        Returns:
            包含转换结果的字典
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Marker not available",
                "markdown": "",
                "latex": "",
                "tables": [],
                "images": [],
            }

        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            # 创建临时输出目录
            if output_dir is None:
                import tempfile

                output_dir = tempfile.mkdtemp()

            output_path = Path(output_dir)

            # 构建marker命令
            cmd = self._build_marker_command(file_path, str(output_path))
            logger.info(f"Running marker: {' '.join(cmd)}")

            # 执行转换
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=300
            )  # 5分钟超时

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Marker failed: {error_msg}")
                return {
                    "success": False,
                    "error": f"Marker conversion failed: {error_msg}",
                    "markdown": "",
                    "latex": "",
                    "tables": [],
                    "images": [],
                }

            # 读取输出文件
            result = self._parse_marker_output(output_path, path.stem)

            logger.info(f"Marker conversion completed: {path.stem}")
            return result

        except asyncio.TimeoutError:
            logger.error(f"Marker conversion timed out: {file_path}")
            return {
                "success": False,
                "error": "Conversion timed out (5 min limit)",
                "markdown": "",
                "latex": "",
                "tables": [],
                "images": [],
            }
        except Exception as e:
            logger.error(f"Marker conversion error: {e}")
            return {
                "success": False,
                "error": str(e),
                "markdown": "",
                "latex": "",
                "tables": [],
                "images": [],
            }

    def _build_marker_command(
        self, file_path: str, output_dir: str
    ) -> List[str]:
        """构建marker命令"""
        cmd = ["marker"]

        # 输出格式
        if self.config.output_format == "json":
            cmd.append("--json")
        elif self.config.output_format == "markdown":
            cmd.append("--markdown")

        # GPU设置
        if not self.config.use_gpu:
            cmd.append("--no-gpu")

        # 数据类型
        if self.config.dtype:
            cmd.extend(["--dtype", self.config.dtype])

        # 语言
        if self.config.lang == "zh":
            cmd.extend(["--lang", "zh"])

        # 最大页数
        if self.config.max_pages:
            cmd.extend(["--max", str(self.config.max_pages)])

        # 输出目录
        cmd.extend(["--output_dir", output_dir])

        # 输入文件
        cmd.append(file_path)

        return cmd

    def _parse_marker_output(
        self, output_dir: Path, stem: str
    ) -> Dict[str, Any]:
        """解析marker输出"""
        result = {
            "success": True,
            "markdown": "",
            "latex": "",
            "tables": [],
            "images": [],
            "metadata": {},
        }

        # 读取Markdown输出
        md_file = output_dir / f"{stem}.md"
        if md_file.exists():
            result["markdown"] = md_file.read_text(encoding="utf-8")

        # 读取LaTeX输出
        tex_file = output_dir / f"{stem}.tex"
        if tex_file.exists():
            result["latex"] = tex_file.read_text(encoding="utf-8")

        # 读取表格
        tables_dir = output_dir / "tables"
        if tables_dir.exists():
            for table_file in tables_dir.glob("*.csv"):
                try:
                    content = table_file.read_text(encoding="utf-8")
                    result["tables"].append(
                        {
                            "filename": table_file.name,
                            "content": content,
                            "rows": len(content.split("\n")),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to read table {table_file}: {e}")

        # 读取图像
        images_dir = output_dir / "images"
        if images_dir.exists():
            for img_file in images_dir.glob("*"):
                if img_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]:
                    result["images"].append(
                        {
                            "filename": img_file.name,
                            "path": str(img_file),
                            "size": img_file.stat().st_size,
                        }
                    )

        # 读取元数据
        meta_file = output_dir / f"{stem}_meta.json"
        if meta_file.exists():
            import json

            try:
                result["metadata"] = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return result

    async def extract_formulas(
        self, file_path: str
    ) -> List[Dict[str, Any]]:
        """
        提取PDF中的公式

        Returns:
            公式列表，每个包含:
            - type: "inline" 或 "display"
            - latex: LaTeX代码
            - bbox: 边界框 (可选)
        """
        # 使用marker转换
        result = await self.convert_file(file_path)

        if not result["success"]:
            return []

        formulas = []
        latex = result.get("latex", "")

        # 解析LaTeX中的公式
        import re

        # 行内公式: $...$
        inline_pattern = r"\$([^\$]+)\$"
        for match in re.finditer(inline_pattern, latex):
            formulas.append(
                {
                    "type": "inline",
                    "latex": match.group(1),
                    "bbox": None,
                }
            )

        # 显示公式: $$...$$ 或 \[...\]
        display_pattern = r"\$\$([^\$]+)\$\$|\\\[([^\]]+)\\\]"
        for match in re.finditer(display_pattern, latex):
            formula_text = match.group(1) or match.group(2)
            formulas.append(
                {
                    "type": "display",
                    "latex": formula_text,
                    "bbox": None,
                }
            )

        # 同时检查Markdown中的公式块
        md = result.get("markdown", "")
        math_pattern = r"```math\n([\s\S]*?)```|\$\$([\s\S]*?)\$\$"
        for match in re.finditer(math_pattern, md):
            formula_text = match.group(1) or match.group(2)
            if formula_text:
                formulas.append(
                    {
                        "type": "display",
                        "latex": formula_text.strip(),
                        "bbox": None,
                    }
                )

        return formulas

    async def extract_tables_structured(
        self, file_path: str
    ) -> List[Dict[str, Any]]:
        """
        提取结构化表格

        Returns:
            表格列表，每个包含:
            - headers: 表头
            - rows: 数据行
            - caption: 表格标题 (如果提取到)
        """
        result = await self.convert_file(file_path)

        if not result["success"]:
            return []

        tables = []

        for table_info in result.get("tables", []):
            content = table_info.get("content", "")
            if not content:
                continue

            lines = content.strip().split("\n")
            if not lines:
                continue

            # 尝试解析CSV格式
            headers = []
            rows = []

            if lines:
                # 第一行作为表头
                headers = [h.strip() for h in lines[0].split(",")]

            for line in lines[1:]:
                if not line.strip():
                    continue
                # 处理CSV中的逗号分隔（可能引号内包含逗号）
                row = self._parse_csv_line(line)
                if row:
                    rows.append([cell.strip() for cell in row])

            tables.append(
                {
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "source": table_info.get("filename", ""),
                }
            )

        return tables

    def _parse_csv_line(self, line: str) -> List[str]:
        """解析CSV行，处理引号内的逗号"""
        import csv

        try:
            reader = csv.reader([line])
            return list(reader)[0]
        except Exception:
            # 回退到简单逗号分割
            return [cell.strip() for cell in line.split(",")]


class MarkerLatexExtractor:
    """
    从已转换的内容中提取LaTeX公式

    适用于已有Markdown/LaTeX内容的情况
    """

    @staticmethod
    def extract_formulas_from_latex(latex_content: str) -> List[Dict[str, str]]:
        """从LaTeX内容提取公式"""
        import re

        formulas = []

        # 显示公式: $$...$$
        for match in re.finditer(r"\$\$([\s\S]+?)\$\$", latex_content):
            formulas.append(
                {
                    "type": "display",
                    "latex": match.group(1).strip(),
                }
            )

        # 行内公式: $...$
        # 需要排除已经匹配的显示公式
        remaining = re.sub(r"\$\$[\s\S]+?\$\$", "", latex_content)
        for match in re.finditer(r"\$([^$\n]+?)\$", remaining):
            formulas.append(
                {
                    "type": "inline",
                    "latex": match.group(1).strip(),
                }
            )

        return formulas

    @staticmethod
    def extract_formulas_from_markdown(
        md_content: str,
    ) -> List[Dict[str, Any]]:
        """从Markdown内容提取公式"""
        import re

        formulas = []

        # 数学公式块: ```math ... ```
        math_block_pattern = r"```math\n([\s\S]*?)```"
        for match in re.finditer(math_block_pattern, md_content):
            formulas.append(
                {
                    "type": "display",
                    "latex": match.group(1).strip(),
                    "original": match.group(0),
                }
            )

        # 双美元公式: $$...$$
        for match in re.finditer(r"\$\$([\s\S]+?)\$\$", md_content):
            formulas.append(
                {
                    "type": "display",
                    "latex": match.group(1).strip(),
                    "original": match.group(0),
                }
            )

        # 单美元公式: $...$
        # 排除已匹配的
        temp = re.sub(r"\$\$[\s\S]+?\$\$", "", md_content)
        temp = re.sub(r"```math[\s\S]*?```", "", temp)
        for match in re.finditer(r"\$([^$\n]+?)\$", temp):
            latex = match.group(1).strip()
            # 排除非公式用法
            if latex and not re.match(r"^\d+\.?\d*", latex):
                formulas.append(
                    {
                        "type": "inline",
                        "latex": latex,
                        "original": match.group(0),
                    }
                )

        return formulas

    @staticmethod
    def convert_latex_to_mathml(latex: str) -> str:
        """
        将LaTeX转换为MathML

        注意: 这是基础实现，专业转换建议使用mathJax或KaTeX
        """
        # 简单的替换映射
        replacements = {
            "\\frac{a}{b}": "<mfrac><mi>a</mi><mi>b</mi></mfrac>",
            "\\sqrt{x}": "<msqrt><mi>x</mi></msqrt>",
            "\\sum": "<mo>∑</mo>",
            "\\int": "<mo>∫</mo>",
            "\\alpha": "<mi>α</mi>",
            "\\beta": "<mi>β</mi>",
            "\\gamma": "<mi>γ</mi>",
            "\\theta": "<mi>θ</mi>",
            "\\pi": "<mi>π</mi>",
        }

        mathml = latex
        for latex_sym, mathml_sym in replacements.items():
            mathml = mathml.replace(latex_sym, mathml_sym)

        return f"<math xmlns='http://www.w3.org/1998/Math/MathML'>{mathml}</math>"


async def convert_pdf_with_marker(
    file_path: str,
    output_dir: Optional[str] = None,
    config: Optional[MarkerConfig] = None,
) -> Dict[str, Any]:
    """
    便捷函数: 使用Marker转换PDF

    Args:
        file_path: PDF文件路径
        output_dir: 输出目录
        config: Marker配置

    Returns:
        转换结果
    """
    parser = MarkerPDFParser(config)
    return await parser.convert_file(file_path, output_dir)


async def extract_paper_formulas(
    file_path: str,
) -> List[Dict[str, Any]]:
    """
    便捷函数: 提取论文中的公式

    Args:
        file_path: PDF文件路径

    Returns:
        公式列表
    """
    parser = MarkerPDFParser()
    return await parser.extract_formulas(file_path)


async def extract_paper_tables(
    file_path: str,
) -> List[Dict[str, Any]]:
    """
    便捷函数: 提取论文中的表格

    Args:
        file_path: PDF文件路径

    Returns:
        表格列表
    """
    parser = MarkerPDFParser()
    return await parser.extract_tables_structured(file_path)


def get_tool_spec():
    """获取工具规格"""
    from .tool_spec import ToolSpec, ParameterSpec, ParameterType

    return ToolSpec(
        name="marker_convert",
        description="使用Marker将PDF转换为Markdown/LaTeX，保留公式和代码",
        parameters=[
            ParameterSpec(
                name="file_path",
                description="PDF文件路径",
                type=ParameterType.STRING,
                required=True,
            ),
            ParameterSpec(
                name="output_format",
                description="输出格式: markdown, text, json",
                type=ParameterType.STRING,
                required=False,
                default="markdown",
            ),
            ParameterSpec(
                name="use_gpu",
                description="是否使用GPU加速",
                type=ParameterType.BOOLEAN,
                required=False,
                default=True,
            ),
        ],
        handler=convert_pdf_with_marker,
        category="document",
    )
