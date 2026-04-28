"""
Semantic Scholar Searcher - 语义学术搜索

搜索Semantic Scholar学术数据库。
支持真实GraphQL API接入。
"""
import logging
import os
from typing import Optional

from .base_searcher import BaseSearcher, SearchResult, SearchResponse

logger = logging.getLogger(__name__)


class SemanticScholarSearcher(BaseSearcher):
    """Semantic Scholar搜索器 - AI增强学术搜索"""

    API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        super().__init__("semantic_scholar")

    async def _make_request(self, url: str, params: dict = None) -> dict:
        """发送HTTP请求"""
        import aiohttp

        headers = {"x-api-key": self.API_KEY} if self.API_KEY else {}
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 429:
                    logger.warning("Semantic Scholar API rate limit exceeded")
                    return {"data": [], "error": "Rate limit exceeded"}
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Semantic Scholar API error: {resp.status} - {text}")
                    return {"data": [], "error": f"API error: {resp.status}"}
                return await resp.json()

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """搜索Semantic Scholar论文

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            url = f"{self.BASE_URL}/paper/search"
            params = {
                "query": query,
                "limit": min(max_results, 100),
                "fields": "title,abstract,authors,year,citationCount,venue,externalIds,openAccessPdf,tldr"
            }

            data = await self._make_request(url, params)

            if "error" in data:
                return self._create_response(query, [], self.name, data["error"])

            papers = [self._parse_paper(p) for p in data.get("data", [])]
            return self._create_response(query, papers, self.name)

        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    def _parse_paper(self, paper: dict) -> SearchResult:
        """解析论文数据"""
        authors = []
        for author in paper.get("authors", [])[:10]:
            if isinstance(author, dict):
                authors.append(author.get("name", ""))
            else:
                authors.append(str(author))

        external_ids = paper.get("externalIds", {}) or {}
        doi = external_ids.get("DOI", "")

        venue = paper.get("venue", "")
        if not venue and paper.get("year"):
            venue = f"({paper.get('year')})"

        return SearchResult(
            paper_id=paper.get("paperId", ""),
            title=paper.get("title", ""),
            abstract=paper.get("abstract", "") or "",
            authors=authors,
            year=paper.get("year", 0) or 0,
            venue=venue,
            url=f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
            citations=paper.get("citationCount", 0) or 0,
            doi=doi,
            raw_data=paper
        )

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取Semantic Scholar论文详情

        Args:
            paper_id: Paper ID

        Returns:
            SearchResult
        """
        try:
            url = f"{self.BASE_URL}/paper/{paper_id}"
            params = {
                "fields": "title,abstract,authors,year,citationCount,venue,externalIds,openAccessPdf,tldr,references"
            }

            data = await self._make_request(url, params)
            if "error" in data:
                return None

            return self._parse_paper(data)

        except Exception as e:
            logger.error(f"Get Semantic Scholar paper failed: {e}")
            return None

    async def get_citations(self, paper_id: str, max_results: int = 50) -> SearchResponse:
        """获取论文引用

        Args:
            paper_id: 论文ID
            max_results: 最大结果数

        Returns:
            SearchResponse: 引用列表
        """
        try:
            url = f"{self.BASE_URL}/paper/{paper_id}/citations"
            params = {
                "limit": min(max_results, 100),
                "fields": "title,abstract,authors,year,citationCount,venue,externalIds"
            }

            data = await self._make_request(url, params)

            if "error" in data:
                return self._create_response(f"citations:{paper_id}", [], f"{self.name}_citations", data["error"])

            citations = [self._parse_paper(c.get("citingPaper", {})) for c in data.get("data", [])]
            return self._create_response(f"citations:{paper_id}", citations, f"{self.name}_citations")

        except Exception as e:
            logger.error(f"Get citations failed: {e}")
            return self._create_response(f"citations:{paper_id}", [], f"{self.name}_citations", str(e))

    async def get_references(self, paper_id: str, max_results: int = 50) -> SearchResponse:
        """获取论文参考文献

        Args:
            paper_id: 论文ID
            max_results: 最大结果数

        Returns:
            SearchResponse: 参考文献列表
        """
        try:
            url = f"{self.BASE_URL}/paper/{paper_id}/references"
            params = {
                "limit": min(max_results, 100),
                "fields": "title,abstract,authors,year,citationCount,venue,externalIds"
            }

            data = await self._make_request(url, params)

            if "error" in data:
                return self._create_response(f"references:{paper_id}", [], f"{self.name}_references", data["error"])

            references = [self._parse_paper(r.get("citedPaper", {})) for r in data.get("data", [])]
            return self._create_response(f"references:{paper_id}", references, f"{self.name}_references")

        except Exception as e:
            logger.error(f"Get references failed: {e}")
            return self._create_response(f"references:{paper_id}", [], f"{self.name}_references", str(e))

    async def get_similar_papers(self, paper_id: str, max_results: int = 10) -> SearchResponse:
        """获取相似论文

        Args:
            paper_id: 论文ID
            max_results: 最大结果数

        Returns:
            SearchResponse: 相似论文列表
        """
        try:
            url = f"{self.BASE_URL}/paper/{paper_id}/similar"
            params = {
                "limit": min(max_results, 20),
                "fields": "title,abstract,authors,year,citationCount,venue,externalIds"
            }

            data = await self._make_request(url, params)

            if "error" in data:
                return self._create_response(f"similar:{paper_id}", [], f"{self.name}_similar", data["error"])

            similar = [self._parse_paper(p) for p in data.get("data", [])]
            return self._create_response(f"similar:{paper_id}", similar, f"{self.name}_similar")

        except Exception as e:
            logger.error(f"Get similar papers failed: {e}")
            return self._create_response(f"similar:{paper_id}", [], f"{self.name}_similar", str(e))
