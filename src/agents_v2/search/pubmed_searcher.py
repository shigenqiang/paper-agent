"""
PubMed Searcher - 生物医学文献搜索

搜索PubMed生物医学数据库。

限制说明:
- 免费版: 每秒3次请求
- 有API Key: 每秒10次请求
- API Key环境变量: NCBI_API_KEY
- 需要注册获取: https://account.ncbi.nlm.nih.gov/
"""

from src.agents_v2.logging_config import get_logging_logger

import json

import urllib.request
import urllib.parse
import urllib.error
import ssl
import asyncio
from typing import Optional

from .enhanced_base_searcher import EnhancedBaseSearcher, PlatformConfig
from .base_searcher import SearchResult, SearchResponse

logger = get_logging_logger(__name__)

logger = get_logging_logger(__name__)


class PubmedSearcher(EnhancedBaseSearcher):
    """PubMed搜索器 - 生物医学文献"""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    SSL_CONTEXT = None

    def __init__(self, rate_manager=None, api_key: str = None):
        config = PlatformConfig(
            name="pubmed",
            min_interval=0.33,        # 免费版3次/秒
            max_requests_per_second=3,
            max_requests_per_hour=10000,
            use_api_key=True,
            api_key_env_var="NCBI_API_KEY",
        )
        super().__init__("pubmed", platform_config=config, rate_manager=rate_manager)
        self._custom_api_key = api_key

        if PubmedSearcher.SSL_CONTEXT is None:
            PubmedSearcher.SSL_CONTEXT = ssl.create_default_context()
            PubmedSearcher.SSL_CONTEXT.check_hostname = False
            PubmedSearcher.SSL_CONTEXT.verify_mode = ssl.CERT_NONE

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
        mesh_filter: str = None
    ) -> SearchResponse:
        """搜索PubMed论文

        Args:
            query: 搜索查询
            max_results: 最大结果数
            year_filter: 年份过滤 (如 "2024[DP]" 或 "2020:2024[DP]")
            mesh_filter: MeSH主题词过滤

        Returns:
            SearchResponse
        """
        try:
            # 构建搜索查询
            search_parts = []
            if mesh_filter:
                search_parts.append(mesh_filter)
            search_parts.append(f"{query}[Title/Abstract]")
            search_query = " AND ".join(search_parts) if len(search_parts) > 1 else query

            # 构建参数
            params = {
                "db": "pubmed",
                "term": search_query,
                "retmax": min(max_results, 100),
                "retstart": 0,
                "retmode": "json",
                "usehistory": "y"
            }

            # 添加API Key
            if self.api_key:
                params["api_key"] = self.api_key

            # 添加日期过滤
            if year_filter:
                params["datetype"] = "pdat"
                params["reldate"] = "365"  # 最近一年

            headers = self._build_headers({"Content-Type": "application/x-www-form-urlencoded"})

            # 速率控制
            await self.rate_manager.acquire(self.name, self.platform_config)

            # 执行搜索
            response_data = await self._sync_get(
                f"{self.ESEARCH_URL}?{urllib.parse.urlencode(params)}"
            )

            search_data = json.loads(response_data)
            id_list = search_data.get("esearchresult", {}).get("idlist", [])

            if not id_list:
                return self._create_response(query, [], self.name)

            # 获取详情
            papers = await self._fetch_details(id_list, max_results)
            return self._create_response(query, papers, self.name)

        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    async def _fetch_details(self, pmids: list, max_results: int) -> list:
        """获取论文详情"""
        try:
            # 速率控制
            await self.rate_manager.acquire(self.name, self.platform_config)

            params = {
                "db": "pubmed",
                "id": ",".join(pmids[:max_results]),
                "retmode": "json"
            }

            if self.api_key:
                params["api_key"] = self.api_key

            response_data = await self._sync_get(
                f"{self.ESUMMARY_URL}?{urllib.parse.urlencode(params)}"
            )

            summary_data = json.loads(response_data)
            results = self._parse_pubmed_summary(summary_data)

            # 获取摘要（esummary不包含abstract）
            results = await self._fetch_abstracts(results)

            return results

        except Exception as e:
            logger.error(f"Fetch PubMed details failed: {e}")
            return []

    async def _fetch_abstracts(self, results: list) -> list:
        """使用 efetch API 获取 PubMed 论文摘要"""
        if not results:
            return results

        try:
            # 获取纯数字的PMID
            ids = [r.paper_id for r in results if r.paper_id.isdigit()]
            if not ids:
                return results

            # 速率控制
            await self.rate_manager.acquire(self.name, self.platform_config)

            params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "rettype": "xml",
                "retmode": "text"
            }

            if self.api_key:
                params["api_key"] = self.api_key

            response_data = await self._sync_get(
                f"{self.EFETCH_URL}?{urllib.parse.urlencode(params)}"
            )

            # 解析XML提取摘要
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response_data)

            abstract_map = {}
            for article in root.findall(".//PubmedArticle"):
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else None
                if not pmid:
                    continue

                abstract_parts = []
                for abs_text in article.findall(".//AbstractText"):
                    text = abs_text.text
                    if text:
                        label = abs_text.get("Label")
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)

                if abstract_parts:
                    abstract_map[pmid] = " ".join(abstract_parts)

            # 更新结果
            for r in results:
                if r.paper_id in abstract_map:
                    r.abstract = abstract_map[r.paper_id]

        except Exception as e:
            logger.warning(f"获取PubMed摘要失败: {e}")

        return results

    async def _sync_get(self, url: str) -> str:
        """同步HTTP GET（在线程池中运行）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_fetch(url)
        )

    def _sync_fetch(self, url: str) -> str:
        """同步获取数据"""
        with urllib.request.urlopen(
            url,
            timeout=30,
            context=PubmedSearcher.SSL_CONTEXT
        ) as response:
            return response.read().decode("utf-8")

    def _parse_pubmed_summary(self, summary_data: dict) -> list:
        """解析PubMed摘要响应"""
        results = []
        try:
            result = summary_data.get("result", {})
            for pmid, info in result.items():
                if pmid == "uids":
                    continue

                try:
                    authors = []
                    author_list = info.get("authors", [])
                    for auth in author_list:
                        if "name" in auth:
                            authors.append(auth["name"])

                    try:
                        pubdate = info.get("pubdate", "2024")
                        year = int(pubdate[:4]) if pubdate else 2024
                    except (ValueError, TypeError):
                        year = 2024

                    try:
                        citations = int(info.get("pmcrefcount", 0) or 0)
                    except (ValueError, TypeError):
                        citations = 0

                    results.append(SearchResult(
                        paper_id=pmid,
                        title=info.get("title", ""),
                        abstract=info.get("abstract", ""),
                        authors=authors,
                        year=year,
                        venue=info.get("source", ""),
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        citations=citations,
                        doi="",
                        raw_data={
                            "pmid": pmid,
                            "elocationid": info.get("elocationid", ""),
                            "pubtype": info.get("pubtype", []),
                        }
                    ))
                except Exception as e:
                    logger.warning(f"解析PubMed论文失败: {e}")
                    continue
        except Exception as e:
            logger.error(f"PubMed摘要解析失败: {e}")

        return results

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取PubMed论文详情

        Args:
            paper_id: PMID

        Returns:
            SearchResult
        """
        try:
            await self.rate_manager.acquire(self.name, self.platform_config)

            params = {
                "db": "pubmed",
                "id": paper_id,
                "retmode": "json"
            }

            if self.api_key:
                params["api_key"] = self.api_key

            response_data = await self._sync_get(
                f"{self.ESUMMARY_URL}?{urllib.parse.urlencode(params)}"
            )

            summary_data = json.loads(response_data)
            results = self._parse_pubmed_summary(summary_data)

            if results:
                result = results[0]
                # 获取摘要
                abstract_results = await self._fetch_abstracts([result])
                return abstract_results[0] if abstract_results else result
            return None

        except Exception as e:
            logger.error(f"Get PubMed paper failed: {e}")
            return None

    async def get_citations(self, pmid: str, max_results: int = 50) -> SearchResponse:
        """获取论文的引用（被引用的论文）"""
        try:
            # 使用efetch获取引用
            await self.rate_manager.acquire(self.name, self.platform_config)

            params = {
                "db": "pubmed",
                "id": pmid,
                "rettype": "xml",
                "retmode": "text"
            }

            if self.api_key:
                params["api_key"] = self.api_key

            response_data = await self._sync_get(
                f"{self.EFETCH_URL}?{urllib.parse.urlencode(params)}"
            )

            # 解析XML - PubMed不直接提供引用列表，需要通过API单独查询
            # 这里返回空列表，实际应用中需要使用其他API
            return self._create_response(f"citations:{pmid}", [], f"{self.name}_citations")

        except Exception as e:
            logger.error(f"Get citations failed: {e}")
            return self._create_response(f"citations:{pmid}", [], f"{self.name}_citations", str(e))

    async def search_by_author(
        self,
        author: str,
        max_results: int = 50
    ) -> SearchResponse:
        """按作者搜索论文

        Args:
            author: 作者名
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        return await self.search(f"{author}[Author]", max_results)

    async def search_by_doi(self, doi: str) -> SearchResponse:
        """按DOI搜索论文

        Args:
            doi: DOI

        Returns:
            SearchResponse
        """
        return await self.search(f"{doi}[DOI]", max_results=1)