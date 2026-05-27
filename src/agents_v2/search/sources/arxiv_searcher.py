"""
ArXiv Searcher - ArXiv学术搜索

搜索arXiv.org的学术论文。

限制说明:
- 官方建议: 请求间隔至少3秒
- 每小时最多: 1000次请求
- 每日建议: 不超过10000次
- 返回格式: Atom XML
"""


from src.agents_v2.logging_config import get_logging_logger

import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import ssl
from typing import Optional

from .enhanced_base_searcher import EnhancedBaseSearcher, PlatformConfig
from .base_searcher import SearchResult, SearchResponse

logger = get_logging_logger(__name__)


class ArxivSearcher(EnhancedBaseSearcher):
    """ArXiv搜索器 - 计算机科学/物理/数学预印本"""

    BASE_URL = "http://export.arxiv.org/api/query"
    SSL_CONTEXT = None

    def __init__(self, rate_manager=None):
        config = PlatformConfig(
            name="arxiv",
            min_interval=3.0,        # 官方建议3秒间隔
            max_requests_per_hour=1000,
            max_requests_per_day=10000,
        )
        super().__init__("arxiv", platform_config=config, rate_manager=rate_manager)

        # 创建SSL上下文（类级别缓存）
        if ArxivSearcher.SSL_CONTEXT is None:
            ArxivSearcher.SSL_CONTEXT = ssl.create_default_context()
            ArxivSearcher.SSL_CONTEXT.check_hostname = False
            ArxivSearcher.SSL_CONTEXT.verify_mode = ssl.CERT_NONE

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        start: int = 0,
        categories: list = None
    ) -> SearchResponse:
        """搜索ArXiv论文

        Args:
            query: 搜索查询
            max_results: 最大结果数 (最大2000)
            sort_by: 排序方式 (relevance, lastUpdatedDate, submittedDate)
            start: 结果起始位置
            categories: 分类过滤 (如 ["cs.AI", "cs.LG"])

        Returns:
            SearchResponse
        """
        try:
            # 构建搜索查询
            search_parts = []
            if categories:
                cat_filter = "+OR+".join([f"cat:{c}" for c in categories])
                search_parts.append(f"({cat_filter})")

            search_parts.append(f"all:{query}")

            search_query = "+AND+".join(search_parts) if len(search_parts) > 1 else query

            params = {
                "search_query": search_query,
                "start": start,
                "max_results": min(max_results, 2000),
                "sortBy": sort_by,
                "sortOrder": "descending"
            }

            url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

            # 速率控制
            await self.rate_manager.acquire(self.name, self.platform_config)

            # 发送请求（使用urllib因为arXiv不支持HTTPS或需要特殊处理）
            response_data = await self._fetch_arxiv(url)

            if "error" in response_data:
                return self._create_response(query, [], self.name, response_data["error"])

            # 解析结果
            results = self._parse_arxiv_response(response_data.get("data", ""), query)
            return self._create_response(query, results, self.name)

        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    async def _fetch_arxiv(self, url: str) -> dict:
        """获取ArXiv数据"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self._sync_fetch(url)
            )
            return {"data": data}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                self.rate_manager.record_rate_limit(self.name, self.platform_config)
                return {"error": "Rate limit exceeded"}
            return {"error": f"HTTP {e.code}"}
        except Exception as e:
            return {"error": str(e)}

    def _sync_fetch(self, url: str) -> str:
        """同步获取数据（在线程池中运行）"""
        with urllib.request.urlopen(
            url,
            timeout=30,
            context=ArxivSearcher.SSL_CONTEXT
        ) as response:
            return response.read().decode("utf-8")

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取ArXiv论文详情

        Args:
            paper_id: ArXiv ID (如 "2301.00001" 或完整URL)

        Returns:
            SearchResult
        """
        try:
            # 清理paper_id
            if "/" in paper_id:
                paper_id = paper_id.split("/")[-1]
            if paper_id.endswith(".pdf"):
                paper_id = paper_id[:-4]

            url = f"{self.BASE_URL}?id_list={paper_id}"

            await self.rate_manager.acquire(self.name, self.platform_config)

            response_data = await self._fetch_arxiv(url)

            if "error" in response_data:
                return None

            results = self._parse_arxiv_response(response_data.get("data", ""), "")
            return results[0] if results else None

        except Exception as e:
            logger.error(f"Get ArXiv paper failed: {e}")
            return None

    def _parse_arxiv_response(self, xml_data: str, query: str) -> list:
        """解析arXiv XML响应"""
        results = []

        try:
            root = ET.fromstring(xml_data)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                try:
                    paper_id = entry.find("atom:id", ns)
                    if paper_id is None:
                        continue
                    paper_id = paper_id.text.split("/")[-1]

                    title_elem = entry.find("atom:title", ns)
                    title = " ".join(title_elem.text.split()) if title_elem is not None and title_elem.text else ""

                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name_elem = author.find("atom:name", ns)
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text)

                    published_elem = entry.find("atom:published", ns)
                    published = published_elem.text if published_elem is not None else ""
                    year = int(published[:4]) if published and len(published) >= 4 else 2024

                    summary_elem = entry.find("atom:summary", ns)
                    abstract = " ".join(summary_elem.text.split()) if summary_elem is not None and summary_elem.text else ""

                    url = entry.find("atom:id", ns)
                    url = url.text if url is not None else ""

                    # 解析分类
                    categories = []
                    for cat in entry.findall("atom:category", ns):
                        term = cat.get("term")
                        if term:
                            categories.append(term)

                    # PDF链接
                    pdf_url = ""
                    for link in entry.findall("atom:link", ns):
                        if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                            pdf_url = link.get("href", "")
                            break

                    results.append(SearchResult(
                        paper_id=paper_id,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        year=year,
                        venue="arXiv",
                        url=url,
                        citations=0,  # ArXiv不提供引用数
                        raw_data={
                            "arxiv_url": url,
                            "pdf_url": pdf_url,
                            "categories": categories,
                            "updated": published,
                        }
                    ))

                except Exception as e:
                    logger.warning(f"解析arXiv论文失败: {e}")
                    continue

        except ET.ParseError as e:
            logger.error(f"XML解析失败: {e}")

        return results

    async def get_by_category(
        self,
        category: str,
        max_results: int = 50,
        year_filter: int = None
    ) -> SearchResponse:
        """按分类获取最新论文

        Args:
            category: ArXiv分类 (如 "cs.AI", "math.CO")
            max_results: 最大结果数
            year_filter: 年份过滤

        Returns:
            SearchResponse
        """
        query = f"cat:{category}"
        if year_filter:
            query = f"cat:{category}+AND+all:{year_filter}"

        return await self.search(
            query,
            max_results=max_results,
            sort_by="submittedDate"
        )

    async def get_recent_papers(
        self,
        query: str,
        days: int = 7,
        max_results: int = 50
    ) -> SearchResponse:
        """获取最近N天的论文

        Args:
            query: 搜索查询
            days: 最近天数
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        # ArXiv API不直接支持日期过滤，使用submittedDate排序后截取
        results = await self.search(
            query,
            max_results=min(max_results, 100),
            sort_by="submittedDate"
        )

        # 注意：这里无法精确按日期过滤，返回排序后的结果
        return results

    async def search_batch(
        self,
        queries: list,
        max_results_per_query: int = 10
    ) -> list:
        """批量搜索（带速率控制）

        Args:
            queries: 查询列表
            max_results_per_query: 每个查询的结果数

        Returns:
            SearchResponse列表
        """
        import asyncio

        # 并行执行所有查询
        tasks = [
            self.search(query, max_results_per_query)
            for query in queries
        ]
        return await asyncio.gather(*tasks)