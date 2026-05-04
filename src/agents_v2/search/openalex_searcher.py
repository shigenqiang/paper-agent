"""
OpenAlex Searcher - 开源学术搜索

基于 OpenAlex API 的跨学科学术论文搜索。
API 文档: https://docs.openalex.org/

限制说明:
- 无明确每日限制，但建议合理使用
- 最小请求间隔: 0.5秒
- 最大并发: 建议2-3个请求/秒
"""

from src.agents_v2.logging_config import get_logging_logger

from typing import List, Optional

from .enhanced_base_searcher import EnhancedBaseSearcher, PlatformConfig
from .base_searcher import SearchResult, SearchResponse

logger = get_logging_logger(__name__)


class OpenAlexSearcher(EnhancedBaseSearcher):
    """OpenAlex学术搜索器 - 跨学科免费API"""

    BASE_URL = "https://api.openalex.org"
    API_FIELDS = (
        "id,title,authorships,abstract_inverted_index,publication_year,"
        "cited_by_count,concepts,open_access,type,doi,primary_location,"
        "biblio"
    )

    def __init__(self, rate_manager=None):
        config = PlatformConfig(
            name="openalex",
            min_interval=0.5,
            max_requests_per_second=2,
            max_requests_per_hour=7200,
        )
        super().__init__("openalex", platform_config=config, rate_manager=rate_manager)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_filter: str = None,
        venue_filter: str = None,
        author_filter: str = None,
        concept_filter: str = None
    ) -> SearchResponse:
        """搜索OpenAlex论文

        Args:
            query: 搜索查询
            max_results: 最大结果数 (最大200)
            year_filter: 年份过滤 (如 "2024" 或 "2020-2024")
            venue_filter: 发表 venue 过滤 (期刊/会议名)
            author_filter: 作者过滤
            concept_filter: 概念/主题过滤

        Returns:
            SearchResponse
        """
        try:
            url = f"{self.BASE_URL}/works"
            params = {
                "search": query,
                "per-page": min(max_results, 200),
                "select": self.API_FIELDS,
            }

            # 构建过滤条件
            filters = []
            if year_filter:
                filters.append(f"publication_year:{year_filter}")
            if venue_filter:
                filters.append(f"primary_location.source.display_name:{venue_filter}")
            if author_filter:
                filters.append(f"authorships.author.display_name:{author_filter}")
            if concept_filter:
                filters.append(f"concepts.display_name:{concept_filter}")

            if filters:
                params["filter"] = ",".join(filters)

            # 排序: 相关度优先 (只支持 descending)
            params["sort"] = "relevance_score:desc"

            headers = self._build_headers()

            data = await self._make_request(url, params, headers)

            # 处理错误
            if "error" in data:
                return self._create_response(query, [], self.name, data["error"])

            # 检查是否为空结果
            if "results" not in data or not data["results"]:
                return self._create_response(query, [], self.name)

            # 解析结果
            papers = [self._parse_work(w) for w in data["results"]]
            return self._create_response(query, papers, self.name)

        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    def _parse_work(self, work: dict) -> SearchResult:
        """解析OpenAlex论文格式"""
        work_id = work.get("id", "").split("/")[-1] if work.get("id") else ""

        # 解析作者
        authors = []
        for auth in work.get("authorships", [])[:10]:
            author = auth.get("author", {})
            if author:
                authors.append(author.get("display_name", ""))
            else:
                institutions = auth.get("institutions", [])
                if institutions:
                    first_inst = next((i for i in institutions if i.get("display_name")), None)
                    if first_inst:
                        authors.append(first_inst.get("display_name", ""))

        # 解析venue/source
        primary_loc = work.get("primary_location") or {}
        source = primary_loc.get("source") or {}
        venue = source.get("display_name", "")

        # 解析DOI
        doi = work.get("doi") or ""
        if doi and "/" in doi:
            doi = doi.split("/")[-1]

        # 重建摘要
        abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))

        # 引用数
        citations = work.get("cited_by_count", 0) or 0

        # URL: 优先使用DOI链接
        url = ""
        if doi and doi.startswith("10."):
            url = f"https://doi.org/{doi}"
        elif work_id:
            url = f"https://openalex.org/{work_id}"

        # 概念/关键词
        concepts = [c.get("display_name", "") for c in work.get("concepts", [])[:5]]

        return SearchResult(
            paper_id=work_id,
            title=work.get("title") or "",
            abstract=abstract,
            authors=authors,
            year=work.get("publication_year", 0) or 0,
            venue=venue,
            url=url,
            citations=citations,
            doi=doi,
            raw_data={
                "openalex_id": work_id,
                "concepts": concepts,
                "type": work.get("type", ""),
                "open_access": work.get("open_access", {}),
                "biblio": work.get("biblio", {}),
                "keywords": concepts,
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
            return str(inverted_index)[:500]

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取OpenAlex论文详情

        Args:
            paper_id: OpenAlex Paper ID (如 "W2987654321")

        Returns:
            SearchResult or None
        """
        try:
            url = f"{self.BASE_URL}/works/{paper_id}"
            params = {"select": self.API_FIELDS}

            data = await self._make_request(url, params, self._build_headers())

            if "error" in data:
                logger.error(f"Get OpenAlex paper failed: {data['error']}")
                return None

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
            author_id: OpenAlex Author ID (如 "A123456789")
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            url = f"{self.BASE_URL}/authors/{author_id}/works"
            params = {
                "per-page": min(max_results, 200),
                "select": self.API_FIELDS,
                "sort": "publication_year:desc"
            }

            data = await self._make_request(url, params, self._build_headers())

            if "error" in data:
                return self._create_response(f"author:{author_id}", [], self.name, data["error"])

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
                "select": self.API_FIELDS,
                "filter": f"primary_location.source.display_name:{venue}",
                "sort": "publication_year:desc"
            }

            if year_filter:
                params["filter"] += f",publication_year:{year_filter}"

            url = f"{self.BASE_URL}/works"
            data = await self._make_request(url, params, self._build_headers())

            if "error" in data:
                return self._create_response(f"venue:{venue}", [], self.name, data["error"])

            papers = [self._parse_work(w) for w in data.get("results", [])]
            return self._create_response(f"venue:{venue}", papers, self.name)

        except Exception as e:
            logger.error(f"Get venue papers failed: {e}")
            return self._create_response(f"venue:{venue}", [], self.name, str(e))

    async def get_related_papers(
        self,
        paper_id: str,
        max_results: int = 10
    ) -> SearchResponse:
        """获取相关论文（基于概念相似度）

        Args:
            paper_id: OpenAlex Paper ID
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            # 获取原论文的概念
            paper = await self.get_paper(paper_id)
            if not paper:
                return self._create_response(f"related:{paper_id}", [], self.name, "Paper not found")

            concepts = paper.raw_data.get("concepts", [])[:3]
            if not concepts:
                return self._create_response(f"related:{paper_id}", [], self.name, "No concepts found")

            # 使用概念搜索相关论文
            concept_filter = "|".join(concepts)
            params = {
                "filter": f"concepts.id:{concept_filter}",
                "per-page": max_results,
                "select": self.API_FIELDS,
                "sort": "cited_by_count:desc"
            }

            url = f"{self.BASE_URL}/works"
            data = await self._make_request(url, params, self._build_headers())

            if "error" in data:
                return self._create_response(f"related:{paper_id}", [], self.name, data["error"])

            # 排除原论文
            papers = [self._parse_work(w) for w in data.get("results", [])
                      if w.get("id", "").split("/")[-1] != paper_id][:max_results]

            return self._create_response(f"related:{paper_id}", papers, self.name)

        except Exception as e:
            logger.error(f"Get related papers failed: {e}")
            return self._create_response(f"related:{paper_id}", [], self.name, str(e))

    async def batch_search(
        self,
        queries: list,
        max_results_per_query: int = 10
    ) -> list:
        """批量搜索多个查询

        Args:
            queries: 查询列表
            max_results_per_query: 每个查询的最大结果数

        Returns:
            搜索响应列表
        """
        import asyncio

        tasks = [
            self.search(query, max_results_per_query)
            for query in queries
        ]

        return await asyncio.gather(*tasks)

    async def get_papers_by_doi(self, dois: List[str]) -> List[Optional[SearchResult]]:
        """根据DOI批量获取论文

        Args:
            dois: DOI列表

        Returns:
            SearchResult列表
        """
        import asyncio

        tasks = [
            self.search(f"doi:{doi}", max_results=1)
            for doi in dois
        ]

        responses = await asyncio.gather(*tasks)
        return [r.results[0] if r.results else None for r in responses]


from typing import List  # 修复导入