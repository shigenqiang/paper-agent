"""
PubMed Searcher - 生物医学文献搜索

搜索PubMed生物医学数据库。
"""
import json
import logging
import urllib.request
import urllib.parse
import ssl
from typing import Optional

from .base_searcher import BaseSearcher, SearchResult, SearchResponse

logger = logging.getLogger(__name__)


class PubmedSearcher(BaseSearcher):
    """PubMed搜索器"""

    def __init__(self):
        super().__init__("pubmed")

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """搜索PubMed论文

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

            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            search_url = f"{base_url}esearch.fcgi"

            search_query = f"{query}[Title/Abstract]"

            params = urllib.parse.urlencode({
                "db": "pubmed",
                "term": search_query,
                "retmax": max_results,
                "retstart": 0,
                "retmode": "json",
                "datetype": "pdat",
                "reldate": 365
            })

            url = f"{search_url}?{params}"
            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                search_data = json.loads(response.read().decode("utf-8"))

            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return self._create_response(query, [], self.name)

            # 获取详情
            summary_url = f"{base_url}esummary.fcgi"
            summary_params = urllib.parse.urlencode({
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            })

            with urllib.request.urlopen(f"{summary_url}?{summary_params}", timeout=30, context=ssl_context) as response:
                summary_data = json.loads(response.read().decode("utf-8"))

            results = self._parse_pubmed_summary(summary_data, query)

            # 补充摘要（esummary 不包含 abstract，需要用 efetch）
            results = self._fetch_abstracts(results)

            return self._create_response(query, results, self.name)

        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取PubMed论文详情

        Args:
            paper_id: PMID

        Returns:
            SearchResult
        """
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            url = f"{base_url}esummary.fcgi?db=pubmed&id={paper_id}&retmode=json"

            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                summary_data = json.loads(response.read().decode("utf-8"))

            results = self._parse_pubmed_summary(summary_data, "")
            if results:
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Get PubMed paper failed: {e}")
            return None

    def _parse_pubmed_summary(self, summary_data: dict, query: str) -> list:
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

                    abstract = info.get("abstract", "")

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
                        abstract=abstract,
                        authors=authors,
                        year=year,
                        venue="PubMed",
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        citations=citations
                    ))
                except Exception as e:
                    logger.warning(f"解析PubMed论文失败: {e}")
                    continue
        except Exception as e:
            logger.error(f"PubMed摘要解析失败: {e}")

        return results

    def _fetch_abstracts(self, results: list) -> list:
        """使用 efetch API 获取 PubMed 论文摘要"""
        if not results:
            return results

        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # PubMed paper_id 是纯数字字符串，不需要 PMID 前缀
            ids = [r.paper_id for r in results if r.paper_id and r.paper_id.isdigit()]
            if not ids:
                return results

            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = urllib.parse.urlencode({
                "db": "pubmed",
                "id": ",".join(ids),
                "rettype": "xml",
                "retmode": "text"
            })

            url = f"{base_url}?{params}"
            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                xml_data = response.read().decode("utf-8")

            # 解析 XML 提取摘要
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_data)

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
