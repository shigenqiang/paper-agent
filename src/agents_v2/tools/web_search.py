"""
Web Search Tool - 网络搜索工具

提供通用的网络搜索功能，封装多种搜索来源。
"""

import os

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

from .extended_search import (
    search_semantic_scholar_handler,
    search_crossref_handler,
    search_dblp_handler,
    search_openalex_handler,
)

logger = get_logging_logger(__name__)


async def search(
    query: str,
    max_results: int = 10,
    sources: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    通用网络搜索接口

    Args:
        query: 搜索查询
        max_results: 最大结果数
        sources: 搜索来源列表，默认 ["semantic_scholar", "crossref"]

    Returns:
        搜索结果列表
    """
    if sources is None:
        sources = ["semantic_scholar", "crossref"]

    all_results = []

    for source in sources:
        try:
            if source == "semantic_scholar":
                result = await search_semantic_scholar_handler(query, max_results)
                all_results.extend(result.get("papers", []))
            elif source == "crossref":
                result = await search_crossref_handler(query, max_results)
                all_results.extend(result.get("papers", []))
            elif source == "dblp":
                result = await search_dblp_handler(query, max_results)
                all_results.extend(result.get("papers", []))
            elif source == "openalex":
                result = await search_openalex_handler(query, max_results)
                all_results.extend(result.get("papers", []))
        except Exception as e:
            logger.warning(f"Search source '{source}' failed: {e}")

    # 去重
    seen = set()
    unique_results = []
    for r in all_results:
        rid = r.get("id") or r.get("paper_id") or r.get("title", "")
        if rid not in seen:
            seen.add(rid)
            unique_results.append(r)

    return unique_results[:max_results]


async def search_papers(
    topic: str,
    max_results: int = 10,
    year: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    学术论文搜索

    Args:
        topic: 搜索主题
        max_results: 最大结果数
        year: 出版年份筛选

    Returns:
        论文列表
    """
    return await search_semantic_scholar_handler(topic, max_results, year)


async def search_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
    通过 DOI 搜索论文

    Args:
        doi: DOI 标识符

    Returns:
        论文信息或 None
    """
    results = await search_crossref_handler(doi, max_results=1)
    return results[0] if results else None