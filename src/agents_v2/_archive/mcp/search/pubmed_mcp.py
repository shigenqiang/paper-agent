"""
PubMed MCP - PubMed生物医学文献搜索MCP协议实现

基于Model Context Protocol的PubMed文献搜索。
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class PubmedArticle:
    """PubMed文章"""
    pmid: str
    title: str
    authors: List[str]
    abstract: str
    journal: str
    pub_date: datetime
    mesh_terms: List[str]
    doi: Optional[str] = None


@dataclass
class PubmedSearchResult:
    """PubMed搜索结果"""
    articles: List[PubmedArticle]
    total_count: int
    query: str
    search_time: float


class PubmedMCPClient:
    """PubMed MCP客户端

    提供PubMed文献搜索、元数据获取、MeSH词获取等功能。
    基于PubMed E-utilities: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        """初始化PubMed MCP客户端

        Args:
            api_key: NCBI API密钥（可选，用于提高请求限制）
            timeout: 请求超时时间
        """
        self.api_key = api_key
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def search_articles(
        self,
        query: str,
        max_results: int = 10,
        mesh_filter: Optional[List[str]] = None
    ) -> PubmedSearchResult:
        """搜索PubMed文献

        Args:
            query: 搜索查询
            max_results: 最大返回数量
            mesh_filter: MeSH词过滤器

        Returns:
            PubmedSearchResult: 搜索结果
        """
        import time
        start_time = time.time()

        # 1. 搜索获取PMIDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 10000),
            "retmode": "xml",
            "sort": "relevance"
        }
        if self.api_key:
            search_params["api_key"] = self.api_key

        session = await self._get_session()
        xml_content = await self._fetch(self.ESEARCH_URL, search_params)

        # 2. 解析PMIDs
        pmids = self._parse_pmids(xml_content)

        if not pmids:
            return PubmedSearchResult(
                articles=[],
                total_count=0,
                query=query,
                search_time=time.time() - start_time
            )

        # 3. 获取文章详情
        articles = await self._fetch_articles(pmids[:max_results])

        return PubmedSearchResult(
            articles=articles,
            total_count=len(articles),
            query=query,
            search_time=time.time() - start_time
        )

    async def _fetch(self, url: str, params: Dict[str, Any]) -> str:
        """发送HTTP请求

        Args:
            url: 请求URL
            params: 查询参数

        Returns:
            str: XML响应内容
        """
        session = await self._get_session()

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"PubMed API返回状态码: {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"PubMed API请求失败: {e}")
            return ""

    def _parse_pmids(self, xml_content: str) -> List[str]:
        """解析PMID列表

        Args:
            xml_content: XML内容

        Returns:
            List[str]: PMID列表
        """
        pmids = []

        try:
            root = ET.fromstring(xml_content)
            for id_list in root.findall(".//IdList"):
                for id_elem in id_list.findall("Id"):
                    if id_elem.text:
                        pmids.append(id_elem.text)

        except ET.ParseError as e:
            logger.error(f"XML解析失败: {e}")

        return pmids

    async def _fetch_articles(self, pmids: List[str]) -> List[PubmedArticle]:
        """批量获取文章详情

        Args:
            pmids: PMID列表

        Returns:
            List[PubmedArticle]: 文章列表
        """
        if not pmids:
            return []

        # 构建查询参数
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }
        if self.api_key:
            params["api_key"] = self.api_key

        xml_content = await self._fetch(self.EFETCH_URL, params)

        return self._parse_articles(xml_content)

    def _parse_articles(self, xml_content: str) -> List[PubmedArticle]:
        """解析文章XML

        Args:
            xml_content: XML内容

        Returns:
            List[PubmedArticle]: 文章列表
        """
        articles = []

        try:
            root = ET.fromstring(xml_content)
            for article in root.findall(".//PubmedArticle"):
                pubmed_article = self._parse_article(article)
                if pubmed_article:
                    articles.append(pubmed_article)

        except ET.ParseError as e:
            logger.error(f"XML解析失败: {e}")

        return articles

    def _parse_article(self, article: ET.Element) -> Optional[PubmedArticle]:
        """解析单个文章

        Args:
            article: XML元素

        Returns:
            PubmedArticle或None
        """
        try:
            # PMID
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""

            # 标题
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else ""

            # 作者
            authors = []
            for author in article.findall(".//Author"):
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                if last_name is not None and last_name.text:
                    name = last_name.text
                    if fore_name is not None and fore_name.text:
                        name = f"{fore_name.text} {name}"
                    authors.append(name)

            # 摘要
            abstract_parts = []
            abstract_elem = article.find("Abstract")
            if abstract_elem is not None:
                for abstract_text in abstract_elem.findall("AbstractText"):
                    if abstract_text.text:
                        abstract_parts.append(abstract_text.text)
            abstract = " ".join(abstract_parts)

            # 期刊
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""

            # 日期
            pub_date = datetime.now()
            article_date = article.find(".//ArticleDate")
            if article_date is None:
                article_date = article.find(".//PubDate")
            if article_date is not None:
                year = article_date.find("Year")
                month = article_date.find("Month")
                day = article_date.find("Day")
                try:
                    year_val = int(year.text) if year is not None and year.text else 2000
                    month_val = int(month.text) if month is not None and month.text else 1
                    day_val = int(day.text) if day is not None and day.text else 1
                    pub_date = datetime(year_val, month_val, day_val)
                except (ValueError, TypeError):
                    pass

            # MeSH词
            mesh_terms = []
            for mesh_heading in article.findall(".//MeshHeading"):
                descriptor = mesh_heading.find("DescriptorName")
                if descriptor is not None and descriptor.text:
                    mesh_terms.append(descriptor.text)

            # DOI
            doi = None
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi" and article_id.text:
                    doi = article_id.text
                    break

            return PubmedArticle(
                pmid=pmid,
                title=title,
                authors=authors,
                abstract=abstract,
                journal=journal,
                pub_date=pub_date,
                mesh_terms=mesh_terms,
                doi=doi
            )

        except Exception as e:
            logger.error(f"解析文章失败: {e}")
            return None

    async def get_mesh_terms(self, pmid: str) -> List[str]:
        """获取文章的MeSH词

        Args:
            pmid: 文章PMID

        Returns:
            List[str]: MeSH词列表
        """
        articles = await self._fetch_articles([pmid])
        if articles:
            return articles[0].mesh_terms
        return []


# 便捷函数
async def search_pubmed(
    query: str,
    max_results: int = 10
) -> PubmedSearchResult:
    """搜索PubMed文献的便捷函数

    Args:
        query: 搜索查询
        max_results: 最大返回数量

    Returns:
        PubmedSearchResult: 搜索结果
    """
    client = PubmedMCPClient()
    try:
        return await client.search_articles(query, max_results)
    finally:
        await client.close()


async def get_pubmed_article(pmid: str) -> Optional[PubmedArticle]:
    """获取单个PubMed文章

    Args:
        pmid: 文章PMID

    Returns:
        PubmedArticle或None
    """
    client = PubmedMCPClient()
    try:
        result = await client.search_articles(f"{pmid}[pmid]", max_results=1)
        return result.articles[0] if result.articles else None
    finally:
        await client.close()
