"""
CrossRef Searcher - CrossRef 学术搜索

CrossRef 是出版商和学术组织的联盟，提供 DOI 解析和元数据搜索。
免费 API，每小时 100 次请求。
"""
import logging
from typing import List, Optional
from .base_searcher import BaseSearcher, SearchResult, SearchResponse

logger = logging.getLogger(__name__)


class CrossRefSearcher(BaseSearcher):
    """CrossRef 学术搜索器"""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, mailto: str = "paper-agent@example.com"):
        """
        初始化 CrossRef 搜索器

        Args:
            mailto: 用于 User-Agent，建议使用真实邮箱以提高 API 限制
        """
        self.mailto = mailto

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """
        搜索学术论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            import httpx

            headers = {
                "User-Agent": f"Paper-Agent/1.0 (mailto:{self.mailto})"
            }

            params = {
                "query": query,
                "rows": max_results,
                "sort": "relevance"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    headers=headers,
                    params=params
                )

                if response.status_code == 429:
                    logger.warning("CrossRef rate limit reached")
                    return SearchResponse(source="crossref", query=query, results=[], total=0)

                response.raise_for_status()
                data = response.json()

            items = data.get("message", {}).get("items", [])
            results = []

            for item in items:
                try:
                    # 提取作者
                    authors = []
                    for author in item.get("author", []):
                        given = author.get("given", "")
                        family = author.get("family", "")
                        if given or family:
                            authors.append(f"{given} {family}".strip())

                    # 提取年份
                    published = item.get("published-print") or item.get("published-online") or {}
                    date_parts = published.get("date-parts", [[None]])
                    year = date_parts[0][0] if date_parts and date_parts[0] else None

                    # 提取期刊/会议
                    container = item.get("container-title", [])
                    venue = container[0] if container else ""

                    # 提取 DOI 和 URL
                    doi = item.get("DOI", "")
                    url = f"https://doi.org/{doi}" if doi else ""

                    # 提取引用数
                    citations = item.get("is-referenced-by-count", 0)

                    # 提取摘要
                    abstract = item.get("abstract", "") or ""
                    # 清理 HTML 标签
                    import re
                    abstract = re.sub(r'<[^>]+>', '', abstract)

                    result = SearchResult(
                        paper_id=doi,
                        title=item.get("title", [""])[0] if item.get("title") else "",
                        authors=authors,
                        abstract=abstract,
                        year=int(year) if year else 0,
                        venue=venue,
                        url=url,
                        doi=doi,
                        citations=citations
                    )
                    results.append(result)

                except Exception as e:
                    logger.debug(f"Failed to parse CrossRef item: {e}")
                    continue

            logger.info(f"CrossRef search: {query} -> {len(results)} results")
            return SearchResponse(source="crossref", query=query, results=results, total=len(results))

        except Exception as e:
            logger.error(f"CrossRef search failed: {e}")
            return SearchResponse(source="crossref", query=query, results=[], total=0)
