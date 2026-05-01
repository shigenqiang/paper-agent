"""
内置插件集合

提供开箱即用的工具插件:
1. WebSearchPlugin - 网页搜索
2. PDFParserPlugin - PDF解析
3. CitationPlugin - 引用格式化
"""
from typing import Any, Dict, List, Optional
import logging
import json

from .plugins import (
    ToolPlugin, PluginMetadata, PluginType, PluginState
)

logger = logging.getLogger(__name__)


class WebSearchPlugin(ToolPlugin):
    """
    网页搜索插件

    封装Web搜索功能，支持多搜索引擎。
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._active = False

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web_search",
            version="1.0.0",
            description="网页搜索工具，支持DuckDuckGo/Bing等搜索引擎",
            author="Paper Agent",
            plugin_type=PluginType.TOOL,
            entry_point="WebSearchPlugin",
            tags=["search", "web", "retrieval"],
        )

    def initialize(self, config: Dict[str, Any]) -> bool:
        self._config = config
        logger.info("WebSearchPlugin initialized")
        return True

    def activate(self) -> bool:
        self._active = True
        logger.info("WebSearchPlugin activated")
        return True

    def deactivate(self) -> bool:
        self._active = False
        return True

    def get_tool_spec(self) -> Dict[str, Any]:
        return {
            "name": "web_search",
            "description": "搜索网页获取最新信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """执行搜索"""
        try:
            from ...search.paper_search import PaperSearch
            searcher = PaperSearch()
            results = await searcher.search(query, max_results=max_results)
            return {
                "success": True,
                "results": results,
                "query": query,
            }
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"success": False, "error": str(e)}


class PDFParserPlugin(ToolPlugin):
    """
    PDF解析插件

    从PDF文件提取文本和元数据。
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._active = False

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="pdf_parser",
            version="1.0.0",
            description="PDF文件解析，提取文本、元数据和引用",
            author="Paper Agent",
            plugin_type=PluginType.TOOL,
            entry_point="PDFParserPlugin",
            tags=["pdf", "parser", "extraction"],
        )

    def initialize(self, config: Dict[str, Any]) -> bool:
        self._config = config
        return True

    def activate(self) -> bool:
        self._active = True
        return True

    def deactivate(self) -> bool:
        self._active = False
        return True

    def get_tool_spec(self) -> Dict[str, Any]:
        return {
            "name": "pdf_parser",
            "description": "解析PDF文件，提取文本内容和元数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "PDF文件路径"
                    },
                    "extract_references": {
                        "type": "boolean",
                        "description": "是否提取参考文献",
                        "default": True
                    }
                },
                "required": ["file_path"]
            }
        }

    async def execute(self, file_path: str, extract_references: bool = True) -> Dict[str, Any]:
        """解析PDF"""
        try:
            import os
            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}

            text = ""
            metadata = {}

            # 尝试使用PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                metadata = {
                    "pages": len(reader.pages),
                    "metadata": reader.metadata if reader.metadata else {},
                }
            except ImportError:
                # 降级：读取原始字节
                with open(file_path, 'rb') as f:
                    content = f.read()
                    text = f"[PDF文件: {file_path}, 大小: {len(content)} bytes]"
                    metadata = {"size": len(content)}

            references = []
            if extract_references and text:
                import re
                ref_pattern = re.compile(r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|\Z)', re.DOTALL)
                references = [
                    {"id": m.group(1), "text": m.group(2).strip()[:200]}
                    for m in ref_pattern.finditer(text)
                ][:20]

            return {
                "success": True,
                "text": text[:10000],
                "metadata": metadata,
                "references": references,
            }

        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return {"success": False, "error": str(e)}


class CitationPlugin(ToolPlugin):
    """
    引用格式化插件

    支持APA/MLA/IEEE/Chicago等引用格式。
    """

    FORMATS = {
        "apa": "{authors} ({year}). {title}. {journal}.",
        "mla": "{authors}. \"{title}.\" {journal}, {year}.",
        "ieee": "{authors}, \"{title},\" {journal}, {year}.",
        "chicago": "{authors}. \"{title}.\" {journal} ({year}).",
    }

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._active = False

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="citation",
            version="1.0.0",
            description="学术引用格式化工具，支持APA/MLA/IEEE/Chicago格式",
            author="Paper Agent",
            plugin_type=PluginType.TOOL,
            entry_point="CitationPlugin",
            tags=["citation", "reference", "format"],
        )

    def initialize(self, config: Dict[str, Any]) -> bool:
        self._config = config
        return True

    def activate(self) -> bool:
        self._active = True
        return True

    def deactivate(self) -> bool:
        self._active = False
        return True

    def get_tool_spec(self) -> Dict[str, Any]:
        return {
            "name": "citation_format",
            "description": "将论文信息格式化为指定引用格式",
            "parameters": {
                "type": "object",
                "properties": {
                    "authors": {"type": "string", "description": "作者"},
                    "title": {"type": "string", "description": "论文标题"},
                    "journal": {"type": "string", "description": "期刊/会议"},
                    "year": {"type": "string", "description": "年份"},
                    "format": {
                        "type": "string",
                        "enum": ["apa", "mla", "ieee", "chicago"],
                        "description": "引用格式",
                        "default": "apa"
                    }
                },
                "required": ["authors", "title", "year"]
            }
        }

    async def execute(
        self,
        authors: str = "",
        title: str = "",
        journal: str = "",
        year: str = "",
        format: str = "apa",
        **kwargs
    ) -> Dict[str, Any]:
        """格式化引用"""
        template = self.FORMATS.get(format, self.FORMATS["apa"])

        citation = template.format(
            authors=authors or "Unknown",
            title=title or "Untitled",
            journal=journal or "",
            year=year or "n.d.",
        )

        return {
            "success": True,
            "citation": citation,
            "format": format,
        }
