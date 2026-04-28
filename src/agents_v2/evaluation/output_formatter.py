"""
输出格式化器 - Output Formatter

功能:
1. Markdown渲染
2. JSON导出
3. 多格式支持
4. 定制化模板

设计原则:
- 灵活的格式化选项
- 支持多种输出格式
- 可扩展的模板系统
"""
import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class OutputFormat(str, Enum):
    """输出格式"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    TEXT = "text"
    LATEX = "latex"


class MarkdownStyle(str, Enum):
    """Markdown风格"""
    STANDARD = "standard"
    ACADEMIC = "academic"
    MINIMAL = "minimal"


@dataclass
class FormattedOutput:
    """格式化输出"""
    content: str
    format: OutputFormat
    metadata: Dict[str, Any]


class OutputFormatter:
    """输出格式化器"""

    def __init__(self, style: MarkdownStyle = MarkdownStyle.STANDARD):
        self.style = style

    def format_markdown(
        self,
        data: Dict[str, Any],
        title: Optional[str] = None,
        include_metadata: bool = True
    ) -> str:
        """格式化Markdown输出

        Args:
            data: 待格式化的数据
            title: 标题
            include_metadata: 是否包含元数据

        Returns:
            str: Markdown格式字符串
        """
        parts = []

        if title:
            parts.append(f"# {title}")
            parts.append("")

        if include_metadata:
            parts.append(self._format_metadata(data))
            parts.append("")

        parts.append(self._format_content(data))

        return "\n".join(parts)

    def _format_metadata(self, data: Dict[str, Any]) -> str:
        """格式化元数据"""
        lines = ["---"]

        if "timestamp" in data:
            lines.append(f"timestamp: {data['timestamp']}")
        if "source" in data:
            lines.append(f"source: {data['source']}")
        if "version" in data:
            lines.append(f"version: {data['version']}")

        lines.append("---")
        return "\n".join(lines)

    def _format_content(self, data: Dict[str, Any]) -> str:
        """格式化内容"""
        if isinstance(data, dict):
            return self._format_dict(data)
        elif isinstance(data, list):
            return self._format_list(data)
        else:
            return str(data)

    def _format_dict(self, data: Dict[str, Any], level: int = 0) -> str:
        """格式化字典"""
        lines = []
        indent = "  " * level

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent}- **{key}**:")
                lines.append(self._format_dict(value, level + 1))
            elif isinstance(value, list):
                lines.append(f"{indent}- **{key}**:")
                lines.append(self._format_list(value, level + 1))
            else:
                lines.append(f"{indent}- **{key}**: {value}")

        return "\n".join(lines)

    def _format_list(self, data: List[Any], level: int = 0) -> str:
        """格式化列表"""
        lines = []
        indent = "  " * level

        for item in data:
            if isinstance(item, dict):
                lines.append(f"{indent}- {self._format_dict(item, level + 1)}")
            else:
                lines.append(f"{indent}- {item}")

        return "\n".join(lines)

    def format_json(
        self,
        data: Dict[str, Any],
        pretty: bool = True,
        include_metadata: bool = True
    ) -> str:
        """格式化JSON输出

        Args:
            data: 待格式化的数据
            pretty: 是否美化输出
            include_metadata: 是否包含元数据

        Returns:
            str: JSON格式字符串
        """
        output = data.copy()

        if include_metadata:
            output["_metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "format": "json",
                "version": "1.0"
            }

        if pretty:
            return json.dumps(output, indent=2, ensure_ascii=False)
        return json.dumps(output, ensure_ascii=False)

    def format_html(
        self,
        data: Dict[str, Any],
        title: Optional[str] = None,
        style: str = "default"
    ) -> str:
        """格式化HTML输出

        Args:
            data: 待格式化的数据
            title: 页面标题
            style: CSS样式

        Returns:
            str: HTML格式字符串
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{title or 'Output'}</title>",
            "<style>",
            self._get_html_css(style),
            "</style>",
            "</head>",
            "<body>"
        ]

        if title:
            html_parts.append(f"<h1>{title}</h1>")

        html_parts.append(self._dict_to_html_table(data))
        html_parts.extend(["</body>", "</html>"])

        return "\n".join(html_parts)

    def _get_html_css(self, style: str) -> str:
        """获取CSS样式"""
        base_css = """
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; border-bottom: 2px solid #007bff; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #007bff; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .metadata { background-color: #f9f9f9; padding: 10px; border-radius: 5px; }
        """
        return base_css

    def _dict_to_html_table(self, data: Dict[str, Any]) -> str:
        """将字典转换为HTML表格"""
        if not data:
            return "<p>No data</p>"

        rows = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            rows.append(f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>")

        return f"<table><tbody>{"".join(rows)}</tbody></table>"

    def format_latex(
        self,
        data: Dict[str, Any],
        title: Optional[str] = None
    ) -> str:
        """格式化LaTeX输出

        Args:
            data: 待格式化的数据
            title: 文档标题

        Returns:
            str: LaTeX格式字符串
        """
        parts = [
            "\\documentclass{article}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage{amsmath}",
            "\\usepackage{hyperref}",
            "\\usepackage{graphicx}",
            "\\begin{document}"
        ]

        if title:
            parts.append(f"\\title{{{title}}}")
            parts.append("\\maketitle")

        if isinstance(data, dict):
            for key, value in data.items():
                parts.append(f"\\section*{{{key}}}")
                if isinstance(value, dict):
                    for k, v in value.items():
                        parts.append(f"\\subsection*{{{k}}}")
                        parts.append(str(v))
                else:
                    parts.append(str(value))

        parts.append("\\end{document}")
        return "\n".join(parts)

    def format_academic_paper(
        self,
        title: str,
        abstract: str,
        sections: Dict[str, str],
        references: Optional[List[str]] = None
    ) -> str:
        """格式化学术论文

        Args:
            title: 论文标题
            abstract: 摘要
            sections: 章节字典 {section_name: content}
            references: 参考文献列表

        Returns:
            str: Markdown格式学术论文
        """
        parts = []

        # 标题
        parts.append(f"# {title}")
        parts.append("")
        parts.append(f"**摘要**: {abstract}")
        parts.append("")

        # 关键词
        parts.append("**关键词**: 深度学习, 机器学习, 人工智能")
        parts.append("")

        # 章节
        for section_name, content in sections.items():
            parts.append(f"## {section_name}")
            parts.append("")
            parts.append(content)
            parts.append("")

        # 参考文献
        if references:
            parts.append("## 参考文献")
            parts.append("")
            for i, ref in enumerate(references, 1):
                parts.append(f"[{i}] {ref}")

        return "\n".join(parts)

    def format_api_response(
        self,
        success: bool,
        data: Any,
        message: Optional[str] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """格式化API响应

        Args:
            success: 是否成功
            data: 响应数据
            message: 消息
            error: 错误信息

        Returns:
            Dict: 标准API响应格式
        """
        response = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        if message:
            response["message"] = message

        if error:
            response["error"] = error

        return response


# 便捷函数
def format_output(
    data: Dict[str, Any],
    format: OutputFormat = OutputFormat.MARKDOWN,
    **kwargs
) -> str:
    """便捷输出格式化函数

    Args:
        data: 待格式化的数据
        format: 输出格式
        **kwargs: 额外参数

    Returns:
        str: 格式化后的字符串
    """
    formatter = OutputFormatter()

    if format == OutputFormat.MARKDOWN:
        return formatter.format_markdown(data, **kwargs)
    elif format == OutputFormat.JSON:
        return formatter.format_json(data, **kwargs)
    elif format == OutputFormat.HTML:
        return formatter.format_html(data, **kwargs)
    elif format == OutputFormat.LATEX:
        return formatter.format_latex(data, **kwargs)
    else:
        return str(data)
