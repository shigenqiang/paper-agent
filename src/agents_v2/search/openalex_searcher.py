"""
OpenAlex Searcher - 开源学术搜索

基于 OpenAlex API 的跨学科学术论文搜索。
API 文档: https://docs.openalex.org/
"""
import logging
from typing import Optional

from .base_searcher import BaseSearcher, SearchResult, SearchResponse

logger = logging.getLogger(__name__)


class OpenAlexSearcher(BaseSearcher):
    """OpenAlex学术搜索器 - 跨学科免费API"""

    BASE_URL = "https://api.openalex.org"

    def __init__(self):
        super().__init__("openalex")

    async def _make_request(self, url: str, params: dict = None) -> dict:
        """发送HTTP请求"""
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            "Accept": "application/json",
            "User-Agent": "PaperAgent/1.0 (https://github.com/paper-agent; mailto:contact@paper-agent.ai)"
        }

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 429:
                    logger.warning("OpenAlex API rate limit exceeded")
                    return {"results": [], "meta": {"error": "Rate limit exceeded"}}
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"OpenAlex API error: {resp.status} - {text}")
                    return {"results": [], "meta": {"error": f"API error: {resp.status}"}}
                return await resp.json()

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_filter: str = None,
        venue_filter: str = None,
        author_filter: str = None
    ) -> SearchResponse:
        """搜索OpenAlex论文

        Args:
            query: 搜索查询
            max_results: 最大结果数
            year_filter: 年份过滤 (如 "2024" 或 "2020-2024")
            venue_filter: 发表 venue 过滤
            author_filter: 作者过滤

        Returns:
            SearchResponse
        """
        try:
            url = f"{self.BASE_URL}/works"
            params = {
                "search": query,
                "per-page": min(max_results, 200),
                "select": "id,title,authorships,abstract_inverted_index,publication_year,cited_by_count,concepts,open_access,type,doi,primary_location"
            }

            filters = []
            if year_filter:
                filters.append(f"publication_year:{year_filter}")
            if venue_filter:
                filters.append(f"primary_location.source.display_name:{venue_filter}")
            if author_filter:
                filters.append(f"authorships.author.display_name:{author_filter}")

            if filters:
                params["filter"] = ",".join(filters)

            data = await self._make_request(url, params)

            if "meta" in data and "error" in data["meta"]:
                return self._create_response(query, [], self.name, data["meta"]["error"])

            papers = [self._parse_work(w) for w in data.get("results", [])]
            return self._create_response(query, papers, self.name)

        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    def _parse_work(self, work: dict) -> SearchResult:
        """解析OpenAlex论文格式"""
        work_id = work.get("id", "").split("/")[-1] if work.get("id") else ""

        authors = []
        for auth in work.get("authorships", [])[:10]:
            author = auth.get("author", {})
            if author:
                authors.append(author.get("display_name", ""))
            else:
                institutions = auth.get("institutions", [])
                if institutions:
                    authors.append(institutions[0].get("display_name", ""))

        concepts = [c.get("display_name", "") for c in work.get("concepts", [])[:5]]

        primary_loc = work.get("primary_location", {}) or {}
        source = primary_loc.get("source", {}) or {}
        venue = source.get("display_name", "")

        doi = work.get("doi", "")
        if doi:
            doi = doi.split("/")[-1] if "/" in doi else doi

        return SearchResult(
            paper_id=work_id,
            title=work.get("title", "") or "",
            abstract=self._reconstruct_abstract(work.get("abstract_inverted_index")),
            authors=authors,
            year=work.get("publication_year", 0) or 0,
            venue=venue,
            url=doi if doi.startswith("10.") else f"https://openalex.org/{work_id}",
            citations=work.get("cited_by_count", 0) or 0,
            doi=doi,
            raw_data={
                "openalex_id": work_id,
                "concepts": concepts,
                "type": work.get("type", ""),
                "open_access": work.get("open_access", {}),
                "keywords": concepts
            }
        )

    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """重建摘要文本"""
        if not inverted_index:
            return ""

        try:
            words = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    words.append((pos, word))
            words.sort(key=lambda x: x[0])
            return " ".join([w[1] for w in words])
        except Exception:
            return str(inverted_index)

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取OpenAlex论文详情

        Args:
            paper_id: OpenAlex Paper ID

        Returns:
            SearchResult
        """
        try:
            url = f"{self.BASE_URL}/works/{paper_id}"
            params = {
                "select": "id,title,authorships,abstract_inverted_index,publication_year,cited_by_count,concepts,open_access,type,doi,primary_location"
            }

            data = await self._make_request(url, params)

            if "id" not in data:
                return None

            return self._parse_work(data)

        except Exception as e:
            logger.error(f"Get OpenAlex paper failed: {e}")
            return None

    async def get_author_papers(
        self,
        author_id: str,
        max_results: int = 50
    ) -> SearchResponse:
        """获取某作者的所有论文

        Args:
            author_id: OpenAlex Author ID
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            url = f"{self.BASE_URL}/authors/{author_id}/works"
            params = {
                "per-page": min(max_results, 200),
                "select": "id,title,authorships,abstract_inverted_index,publication_year,cited_by_count,concepts,open_access,type,doi,primary_location"
            }

            data = await self._make_request(url, params)

            if "meta" in data and "error" in data["meta"]:
                return self._create_response(f"author:{author_id}", [], self.name, data["meta"]["error"])

            papers = [self._parse_work(w) for w in data.get("results", [])]
            return self._create_response(f"author:{author_id}", papers, self.name)

        except Exception as e:
            logger.error(f"Get author papers failed: {e}")
            return self._create_response(f"author:{author_id}", [], self.name, str(e))

    async def get_venue_papers(
        self,
        venue: str,
        max_results: int = 50,
        year_filter: str = None
    ) -> SearchResponse:
        """获取某 venue/期刊/会议的所有论文

        Args:
            venue: 期刊/会议名称
            max_results: 最大结果数
            year_filter: 年份过滤

        Returns:
            SearchResponse
        """
        try:
            params = {
                "search": venue,
                "per-page": min(max_results, 200),
                "select": "id,title,authorships,abstract_inverted_index,publication_year,cited_by_count,concepts,open_access,type,doi,primary_location",
                "filter": f"primary_location.source.display_name:{venue}"
            }

            if year_filter:
                params["filter"] += f",publication_year:{year_filter}"

            url = f"{self.BASE_URL}/works"
            data = await self._make_request(url, params)

            if "meta" in data and "error" in data["meta"]:
                return self._create_response(f"venue:{venue}", [], self.name, data["meta"]["error"])

            papers = [self._parse_work(w) for w in data.get("results", [])]
            return self._create_response(f"venue:{venue}", papers, self.name)

        except Exception as e:
            logger.error(f"Get venue papers failed: {e}")
            return self._create_response(f"venue:{venue}", [], self.name, str(e))
