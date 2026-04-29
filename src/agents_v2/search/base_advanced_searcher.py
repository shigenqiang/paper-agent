"""
BASE Advanced Searcher - Bielefeld Academic Search Engine

BASE 是欧洲最大的学术搜索平台之一，索引了超过 10 亿条学术资源。
免费 API，但需要遵守使用条款。
"""
import logging
from typing import List, Optional
from .base_searcher import BaseSearcher, SearchResult, SearchResponse

logger = logging.getLogger(__name__)


class BASEAdvancedSearcher(BaseSearcher):
    """BASE 学术搜索器"""

    BASE_URL = "https://api.base-search.net/Search/Records"

    def __init__(self):
        self.api_key = None  # 可选：使用 BASE API key 获取更高限额

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """
        搜索学术论文/资源

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            import httpx

            params = {
                "query": query,
                "rows": min(max_results, 50),
                "start": 0,
                "format": "json",
                "filter": "scientific_lit:yes"  # 只搜索学术文献
            }

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    headers=headers,
                    params=params
                )

                response.raise_for_status()
                data = response.json()

            results = []
            records = data.get("response", {}).get("docs", [])

            for record in records:
                try:
                    # BASE 字段映射
                    title = record.get("title", "")
                    authors_raw = record.get("authors", [])
                    if isinstance(authors_raw, str):
                        authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
                    elif isinstance(authors_raw, list):
                        authors = authors_raw
                    else:
                        authors = []

                    # 年份
                    year = record.get("year", "") or ""
                    if isinstance(year, list):
                        year = str(year[0]) if year else ""

                    # 来源
                    sources = []
                    if record.get("source_id"):
                        sources.append(f"base:{record.get('source_id')}")
                    if record.get("repository"):
                        sources.append(f"repository:{record.get('repository')}")

                    result = SearchResult(
                        paper_id=record.get("id", "") or record.get("doi", ""),
                        title=title,
                        authors=authors,
                        abstract=record.get("abstract", "") or "",
                        year=year,
                        venue=record.get("publishers", [""])[0] if record.get("publishers") else "",
                        url=record.get("link", "") or "",
                        doi=record.get("doi", ""),
                        citations=0,  # BASE 不提供引用数
                        sources=sources if sources else ["base"]
                    )
                    results.append(result)

                except Exception as e:
                    logger.debug(f"Failed to parse BASE record: {e}")
                    continue

            logger.info(f"BASEAdvanced search: {query} -> {len(results)} results")
            return SearchResponse(source="base", query=query, results=results, total=len(results))

        except Exception as e:
            logger.error(f"BASEAdvanced search failed: {e}")
            return SearchResponse(source="base", query=query, results=[], total=0)
