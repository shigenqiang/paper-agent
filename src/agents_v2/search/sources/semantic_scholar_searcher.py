"""
Semantic Scholar Searcher - 语义学术搜索

搜索Semantic Scholar学术数据库。

限制说明:
- 免费版: 每秒5次请求
- 需要API Key获得更高配额
- API Key环境变量: SEMANTIC_SCHOLAR_API_KEY
"""


from src.agents_v2.logging_config import get_logging_logger

import os
from typing import Optional

from .enhanced_base_searcher import EnhancedBaseSearcher, PlatformConfig, RetryConfig
from .base_searcher import SearchResult, SearchResponse

logger = get_logging_logger(__name__)


class SemanticScholarSearcher(EnhancedBaseSearcher):
    """Semantic Scholar搜索器 - AI增强学术搜索"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

    # 请求字段
    PAPER_SEARCH_FIELDS = (
        "paperId,title,abstract,authors,year,citationCount,venue,"
        "externalIds,openAccessPdf,tldr,venue"
    )
    PAPER_DETAIL_FIELDS = (
        "paperId,title,abstract,authors,year,citationCount,venue,"
        "externalIds,openAccessPdf,tldr,references,citations"
    )

    def __init__(self, rate_manager=None, api_key: str = None):
        config = PlatformConfig(
            name="semantic_scholar",
            min_interval=0.2,         # 免费版5次/秒，即0.2秒间隔
            max_requests_per_second=5,
            max_requests_per_hour=18000,
            max_requests_per_day=100000,
            use_api_key=True,
            api_key_env_var="SEMANTIC_SCHOLAR_API_KEY",
        )
        super().__init__("semantic_scholar", platform_config=config, rate_manager=rate_manager)
        self._custom_api_key = api_key

    @property
    def api_key(self) -> Optional[str]:
        if self._custom_api_key:
            return self._custom_api_key
        return super().api_key

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_filter: str = None,
        venue_filter: str = None
    ) -> SearchResponse:
        """搜索Semantic Scholar论文

        Args:
            query: 搜索查询
            max_results: 最大结果数 (最大100)
            year_filter: 年份过滤 (如 "2024" 或 "2023-2024")
            venue_filter: 期刊/会议过滤

        Returns:
            SearchResponse
        """
        try:
            url = f"{self.BASE_URL}/paper/search"
            params = {
                "query": query,
                "limit": min(max_results, 100),
                "fields": self.PAPER_SEARCH_FIELDS
            }

            # 添加过滤
            filters = []
            if year_filter:
                filters.append(f"year:{year_filter}")
            if venue_filter:
                filters.append(f"venue:{venue_filter}")

            if filters:
                params["filter"] = ",".join(filters)

            headers = self._build_headers()

            data = await self._make_request(url, params, headers)

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

        # 构建URL
        paper_id = paper.get("paperId", "")
        url = f"https://www.semanticscholar.org/paper/{paper_id}"

        # TLDR摘要
        tldr = paper.get("tldr", {})
        abstract = tldr.get("text", "") if isinstance(tldr, dict) else (paper.get("abstract", "") or "")

        return SearchResult(
            paper_id=paper_id,
            title=paper.get("title", ""),
            abstract=abstract,
            authors=authors,
            year=paper.get("year", 0) or 0,
            venue=venue,
            url=url,
            citations=paper.get("citationCount", 0) or 0,
            doi=doi,
            raw_data={
                "s2_paper_id": paper_id,
                "external_ids": external_ids,
                "open_access_pdf": paper.get("openAccessPdf", {}),
                "tldr": tldr,
            }
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
            params = {"fields": self.PAPER_DETAIL_FIELDS}

            headers = self._build_headers()

            data = await self._make_request(url, params, headers)

            if "error" in data:
                logger.error(f"Get paper failed: {data['error']}")
                return None

            return self._parse_paper(data)

        except Exception as e:
            logger.error(f"Get Semantic Scholar paper failed: {e}")
            return None

    async def get_citations(
        self,
        paper_id: str,
        max_results: int = 50
    ) -> SearchResponse:
        """获取论文引用（被引用的论文）

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
                "fields": self.PAPER_SEARCH_FIELDS
            }

            headers = self._build_headers()

            data = await self._make_request(url, params, headers)

            if "error" in data:
                return self._create_response(f"citations:{paper_id}", [], f"{self.name}_citations", data["error"])

            citations = [self._parse_paper(c.get("citingPaper", {})) for c in data.get("data", [])]
            return self._create_response(f"citations:{paper_id}", citations, f"{self.name}_citations")

        except Exception as e:
            logger.error(f"Get citations failed: {e}")
            return self._create_response(f"citations:{paper_id}", [], f"{self.name}_citations", str(e))

    async def get_references(
        self,
        paper_id: str,
        max_results: int = 50
    ) -> SearchResponse:
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
                "fields": self.PAPER_SEARCH_FIELDS
            }

            headers = self._build_headers()

            data = await self._make_request(url, params, headers)

            if "error" in data:
                return self._create_response(f"references:{paper_id}", [], f"{self.name}_references", data["error"])

            references = [self._parse_paper(r.get("citedPaper", {})) for r in data.get("data", [])]
            return self._create_response(f"references:{paper_id}", references, f"{self.name}_references")

        except Exception as e:
            logger.error(f"Get references failed: {e}")
            return self._create_response(f"references:{paper_id}", [], f"{self.name}_references", str(e))

    async def get_similar_papers(
        self,
        paper_id: str,
        max_results: int = 10
    ) -> SearchResponse:
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
                "fields": self.PAPER_SEARCH_FIELDS
            }

            headers = self._build_headers()

            data = await self._make_request(url, params, headers)

            if "error" in data:
                return self._create_response(f"similar:{paper_id}", [], f"{self.name}_similar", data["error"])

            similar = [self._parse_paper(p) for p in data.get("data", [])]
            return self._create_response(f"similar:{paper_id}", similar, f"{self.name}_similar")

        except Exception as e:
            logger.error(f"Get similar papers failed: {e}")
            return self._create_response(f"similar:{paper_id}", [], f"{self.name}_similar", str(e))

    async def batch_get_papers(self, paper_ids: list) -> list:
        """批量获取论文详情

        Args:
            paper_ids: 论文ID列表

        Returns:
            SearchResult列表
        """
        import asyncio

        tasks = [self.get_paper(pid) for pid in paper_ids]
        return await asyncio.gather(*tasks)