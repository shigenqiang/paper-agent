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
    """BASE 学术搜索器

    注意：BASE API (api.base-search.net) 已停止公开服务。
    当前实现会跳过搜索并返回空结果，避免产生 404 错误日志。
    """

    BASE_URL = "https://api.base-search.net/Search/Records"
    _api_available = None

    def __init__(self):
        self.api_key = None

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """
        搜索学术论文/资源

        BASE API 已停止公开服务，此方法会先探测 API 可用性。
        如果不可用，直接返回空结果而不产生错误日志。

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        # 如果已确认 API 不可用，直接返回空结果
        if BASEAdvancedSearcher._api_available is False:
            return SearchResponse(source="base", query=query, results=[], total=0)

        try:
            import httpx

            params = {
                "query": query,
                "rows": min(max_results, 50),
                "start": 0,
                "format": "json",
                "filter": "scientific_lit:yes"
            }

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    headers=headers,
                    params=params
                )

                # 如果返回 404，标记 API 不可用
                if response.status_code == 404:
                    logger.warning("BASE API returned 404 - service discontinued, disabling future requests")
                    BASEAdvancedSearcher._api_available = False
                    return SearchResponse(source="base", query=query, results=[], total=0)

                response.raise_for_status()
                data = response.json()

            BASEAdvancedSearcher._api_available = True

            results = []
            records = data.get("response", {}).get("docs", [])

            for record in records:
                try:
                    title = record.get("title", "")
                    authors_raw = record.get("authors", [])
                    if isinstance(authors_raw, str):
                        authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
                    elif isinstance(authors_raw, list):
                        authors = authors_raw
                    else:
                        authors = []

                    year = record.get("year", "") or ""
                    if isinstance(year, list):
                        year = str(year[0]) if year else ""

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
                        citations=0,
                        sources=sources if sources else ["base"]
                    )
                    results.append(result)

                except Exception as e:
                    logger.debug(f"Failed to parse BASE record: {e}")
                    continue

            logger.info(f"BASEAdvanced search: {query} -> {len(results)} results")
            return SearchResponse(source="base", query=query, results=results, total=len(results))

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("BASE API returned 404 - disabling future requests")
                BASEAdvancedSearcher._api_available = False
            else:
                logger.error(f"BASEAdvanced search failed: {e}")
            return SearchResponse(source="base", query=query, results=[], total=0)
        except Exception as e:
            logger.debug(f"BASEAdvanced search unavailable: {e}")
            return SearchResponse(source="base", query=query, results=[], total=0)
