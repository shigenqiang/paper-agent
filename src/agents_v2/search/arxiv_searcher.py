"""
ArXiv Searcher - ArXiv学术搜索

搜索arXiv.org的学术论文。
"""
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import ssl
from typing import Optional

from .base_searcher import BaseSearcher, SearchResult, SearchResponse

logger = logging.getLogger(__name__)


class ArxivSearcher(BaseSearcher):
    """ArXiv搜索器"""

    def __init__(self):
        super().__init__("arxiv")

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """搜索ArXiv论文

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            base_url = "http://export.arxiv.org/api/query"
            search_query = f"ti:{query} OR abs:{query}"

            params = urllib.parse.urlencode({
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance"
            })

            url = f"{base_url}?{params}"
            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                data = response.read().decode("utf-8")

            results = self._parse_arxiv_response(data, query)
            return self._create_response(query, results, self.name)

        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取ArXiv论文详情

        Args:
            paper_id: ArXiv ID (如 2301.00001)

        Returns:
            SearchResult
        """
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                data = response.read().decode("utf-8")

            results = self._parse_arxiv_response(data, "")
            if results:
                return results[0]
            return None
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
                    paper_id = entry.find("atom:id", ns).text.split("/")[-1]

                    title = entry.find("atom:title", ns).text or ""
                    title = " ".join(title.split())

                    authors = [
                        author.find("atom:name", ns).text
                        for author in entry.findall("atom:author", ns)
                        if author.find("atom:name", ns) is not None
                    ]

                    published = entry.find("atom:published", ns).text or ""
                    year = int(published[:4]) if published else 2024

                    abstract = entry.find("atom:summary", ns).text or ""
                    abstract = " ".join(abstract.split())

                    url = entry.find("atom:id", ns).text or ""

                    results.append(SearchResult(
                        paper_id=paper_id,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        year=year,
                        venue="arXiv",
                        url=url,
                        citations=0
                    ))
                except Exception as e:
                    logger.warning(f"解析arXiv论文失败: {e}")
                    continue
        except Exception as e:
            logger.error(f"XML解析失败: {e}")

        return results
