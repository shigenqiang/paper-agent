"""
MCP模块 - Model Context Protocol

MCP客户端和工具实现。
"""
from .client import (
    MCPClient,
    MCPClientPool,
    MCPConnectionState,
    MCPMessage
)

from .search.arxiv_mcp import ArxivMCPClient, ArxivPaper, ArxivSearchResult
from .search.pubmed_mcp import PubmedMCPClient, PubmedArticle, PubmedSearchResult

__all__ = [
    # 核心客户端
    "MCPClient",
    "MCPClientPool",
    "MCPConnectionState",
    "MCPMessage",

    # ArXiv搜索
    "ArxivMCPClient",
    "ArxivPaper",
    "ArxivSearchResult",

    # PubMed搜索
    "PubmedMCPClient",
    "PubmedArticle",
    "PubmedSearchResult",
]
