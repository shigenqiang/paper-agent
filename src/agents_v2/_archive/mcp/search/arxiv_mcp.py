"""
ArXiv MCP - ArXiv论文搜索MCP协议实现

基于Model Context Protocol的ArXiv论文搜索。
支持完整的ArXiv API搜索参数。
"""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import xml.etree.ElementTree as ET

import aiohttp

logger = logging.getLogger(__name__)


class SearchField(Enum):
    """搜索字段枚举"""
    ALL = "all"           # 全部字段
    TITLE = "ti"         # 标题
    AUTHOR = "au"        # 作者
    ABSTRACT = "abs"     # 摘要
    COMMENT = "co"        # 评论
    CATEGORY = "cat"     # 分类
    JOURNAL_REF = "jr"    # 期刊引用


class SortBy(Enum):
    """排序方式"""
    RELEVANCE = "relevance"
    SUBMITTED_DATE = "submittedDate"
    LAST_UPDATED_DATE = "lastUpdatedDate"


@dataclass
class ArxivQuery:
    """ArXiv查询结构

    支持多种查询构建方式：

    1. 简单查询:
       ArxivQuery("machine learning")

    2. 字段查询:
       ArxivQuery().title("transformer").author("Hinton")

    3. 组合查询:
       ArxivQuery().title("neural").AND().author("LeCun")

    4. 日期范围:
       ArxivQuery("deep learning").date_range("2024-01-01", "2024-12-31")
    """
    _query_parts: List[str] = field(default_factory=list)
    _date_from: Optional[str] = None
    _date_to: Optional[str] = None

    def __init__(self, query: str = ""):
        """初始化查询

        Args:
            query: 初始查询字符串（会自动添加到all字段）
        """
        self._query_parts = []
        self._date_from = None
        self._date_to = None
        if query:
            self._query_parts.append(f"all:{query}")

    def all(self, text: str) -> "ArxivQuery":
        """搜索全部字段"""
        self._query_parts.append(f"all:{text}")
        return self

    def title(self, text: str) -> "ArxivQuery":
        """搜索标题"""
        self._query_parts.append(f"ti:{text}")
        return self

    def author(self, name: str) -> "ArxivQuery":
        """搜索作者"""
        self._query_parts.append(f"au:{name}")
        return self

    def abstract(self, text: str) -> "ArxivQuery":
        """搜索摘要"""
        self._query_parts.append(f"abs:{text}")
        return self

    def comment(self, text: str) -> "ArxivQuery":
        """搜索评论"""
        self._query_parts.append(f"co:{text}")
        return self

    def category(self, cat: str) -> "ArxivQuery":
        """搜索分类"""
        self._query_parts.append(f"cat:{cat}")
        return self

    def journal_ref(self, text: str) -> "ArxivQuery":
        """搜索期刊引用"""
        self._query_parts.append(f"jr:{text}")
        return self

    def AND(self) -> "ArxivQuery":
        """AND运算符"""
        self._query_parts.append("AND")
        return self

    def OR(self) -> "ArxivQuery":
        """OR运算符"""
        self._query_parts.append("OR")
        return self

    def AND_NOT(self) -> "ArxivQuery":
        """AND NOT运算符"""
        self._query_parts.append("ANDNOT")
        return self

    def date_range(self, from_date: str, to_date: str) -> "ArxivQuery":
        """日期范围

        Args:
            from_date: 开始日期 (YYYY-MM-DD)
            to_date: 结束日期 (YYYY-MM-DD)
        """
        self._date_from = from_date
        self._date_to = to_date
        return self

    def date_from(self, from_date: str) -> "ArxivQuery":
        """开始日期"""
        self._date_from = from_date
        return self

    def date_to(self, to_date: str) -> "ArxivQuery":
        """结束日期"""
        self._date_to = to_date
        return self

    def phrase(self, text: str) -> "ArxivQuery":
        """精确短语（用引号包裹）"""
        self._query_parts.append(f'"{text}"')
        return self

    def build(self) -> str:
        """构建查询字符串"""
        if not self._query_parts:
            return ""

        # 构建基础查询
        query = " ".join(self._query_parts)

        # 添加日期范围
        if self._date_from or self._date_to:
            date_parts = []
            if self._date_from and self._date_to:
                date_parts.append(f"submittedDate:[{self._date_from} TO {self._date_to}]")
            elif self._date_from:
                date_parts.append(f"submittedDate:[{self._date_from} TO *]")
            elif self._date_to:
                date_parts.append(f"submittedDate:[* TO {self._date_to}]")

            if date_parts:
                query = f"({query}) AND ({' OR '.join(date_parts)})"

        return query

    def __str__(self) -> str:
        """返回查询字符串"""
        return self.build()


@dataclass
class ArxivPaper:
    """ArXiv论文"""
    id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published: datetime
    updated: datetime
    pdf_url: str
    doi: Optional[str] = None
    comment: Optional[str] = None
    journal_ref: Optional[str] = None


@dataclass
class ArxivSearchResult:
    """ArXiv搜索结果"""
    papers: List[ArxivPaper]
    total_results: int
    query: str
    search_time: float


class ArxivMCPClient:
    """ArXiv MCP客户端

    提供ArXiv论文搜索、下载、元数据获取等功能。
    基于ArXiv API: https://export.arxiv.org/api/query

    支持的搜索参数:
    - 搜索字段: ti, au, abs, co, cat, jr, all
    - 布尔运算: AND, OR, ANDNOT
    - 日期范围: submittedDate:[from TO to]
    - 排序: relevance, submittedDate, lastUpdatedDate
    """

    BASE_URL = "https://export.arxiv.org/api/query"
    MAX_RESULTS = 100

    # 常用ArXiv分类
    CATEGORIES = {
        # 计算机科学
        "cs.AI": "Artificial Intelligence",
        "cs.CL": "Computation and Language",
        "cs.CV": "Computer Vision",
        "cs.LG": "Machine Learning",
        "cs.NE": "Neural and Evolutionary Computing",
        "cs.IR": "Information Retrieval",
        "cs.SE": "Software Engineering",
        "cs.CR": "Cryptography and Security",
        "cs.DB": "Databases",
        "cs.DC": "Distributed Computing",
        "cs.HC": "Human-Computer Interaction",
        "cs.RO": "Robotics",
        "cs.NI": "Networking and Internet Architecture",
        # 物理学
        "physics.gen-ph": "General Physics",
        "physics.comp-ph": "Computational Physics",
        # 数学
        "math.ST": "Statistics Theory",
        "math.IT": "Information Theory",
        # 统计学
        "stat.ML": "Machine Learning (Statistics)",
        "stat.TH": "Statistics Theory",
    }

    def __init__(self, timeout: float = 30.0, max_retries: int = 3):
        """初始化ArXiv MCP客户端

        Args:
            timeout: 请求超时时间
            max_retries: 最大重试次数
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def search_papers(
        self,
        query: Union[str, ArxivQuery],
        max_results: int = 10,
        categories: Optional[List[str]] = None,
        sort_by: str = "relevance",
        start: int = 0
    ) -> ArxivSearchResult:
        """搜索ArXiv论文

        Args:
            query: 搜索查询（字符串或ArxivQuery对象）
            max_results: 最大返回数量
            categories: 限定的分类列表（会与查询组合）
            sort_by: 排序方式 (relevance, submittedDate, lastUpdatedDate)
            start: 结果起始位置（用于分页）

        Returns:
            ArxivSearchResult: 搜索结果

        示例:
            # 简单搜索
            client.search_papers("machine learning")

            # 字段搜索
            client.search_papers(ArxivQuery().title("transformer").author("Vaswani"))

            # 组合查询
            client.search_papers(ArxivQuery().title("neural").AND().author("Hinton"))

            # 日期范围
            client.search_papers(ArxivQuery("deep learning").date_range("2024-01-01", "2024-12-31"))

            # 分类过滤
            client.search_papers("neural network", categories=["cs.LG", "cs.AI"])
        """
        import time
        start_time = time.time()

        # 构建查询
        if isinstance(query, ArxivQuery):
            search_query = query.build()
        else:
            search_query = self._build_query(query, categories)

        # 构建URL参数
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": min(max_results, self.MAX_RESULTS),
            "sortBy": sort_by,
            "sortOrder": "descending"
        }

        # 发送请求
        xml_content = await self._fetch(params)

        # 解析响应
        papers = self._parse_xml(xml_content)

        return ArxivSearchResult(
            papers=papers,
            total_results=len(papers),
            query=str(query),
            search_time=time.time() - start_time
        )

    def _build_query(
        self,
        query: str,
        categories: Optional[List[str]] = None
    ) -> str:
        """构建搜索查询

        Args:
            query: 用户查询
            categories: 分类列表

        Returns:
            str: 构建的查询字符串
        """
        # 如果查询已经包含字段前缀，直接使用
        prefixes = ["ti:", "au:", "abs:", "co:", "cat:", "all:", "jr:", "id:"]
        if any(query.startswith(p) for p in prefixes):
            parts = [query]
        else:
            parts = [f"all:{query}"]

        # 添加分类过滤
        if categories:
            cat_parts = [f"cat:{cat}" for cat in categories]
            parts.append(f"({' OR '.join(cat_parts)})")

        return " AND ".join(parts)

    async def search_by_title(
        self,
        title: str,
        max_results: int = 10
    ) -> ArxivSearchResult:
        """按标题搜索

        Args:
            title: 标题关键词
            max_results: 最大结果数

        Returns:
            ArxivSearchResult: 搜索结果
        """
        return await self.search_papers(
            ArxivQuery().title(title),
            max_results=max_results
        )

    async def search_by_author(
        self,
        author: str,
        max_results: int = 10
    ) -> ArxivSearchResult:
        """按作者搜索

        Args:
            author: 作者姓名
            max_results: 最大结果数

        Returns:
            ArxivSearchResult: 搜索结果
        """
        return await self.search_papers(
            ArxivQuery().author(author),
            max_results=max_results
        )

    async def search_by_category(
        self,
        category: str,
        max_results: int = 10
    ) -> ArxivSearchResult:
        """按分类搜索

        Args:
            category: ArXiv分类 (如 cs.AI, cs.LG)
            max_results: 最大结果数

        Returns:
            ArxivSearchResult: 搜索结果
        """
        return await self.search_papers(
            ArxivQuery().category(category),
            max_results=max_results
        )

    async def search_recent(
        self,
        query: str,
        days: int = 30,
        max_results: int = 10
    ) -> ArxivSearchResult:
        """搜索最近更新的论文

        Args:
            query: 搜索查询
            days: 最近天数
            max_results: 最大结果数

        Returns:
            ArxivSearchResult: 搜索结果
        """
        from datetime import timedelta

        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        return await self.search_papers(
            ArxivQuery(query).date_range(from_date, to_date),
            max_results=max_results,
            sort_by="submittedDate"
        )

    async def _fetch(self, params: Dict[str, Any]) -> str:
        """发送HTTP请求

        Args:
            params: 查询参数

        Returns:
            str: XML响应内容
        """
        session = await self._get_session()

        for attempt in range(self.max_retries):
            try:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"ArXiv API返回状态码: {response.status}")
            except asyncio.TimeoutError:
                logger.warning(f"ArXiv API超时，重试 {attempt + 1}/{self.max_retries}")
            except Exception as e:
                logger.error(f"ArXiv API请求失败: {e}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        return ""

    def _parse_xml(self, xml_content: str) -> List[ArxivPaper]:
        """解析XML响应

        Args:
            xml_content: XML内容

        Returns:
            List[ArxivPaper]: 论文列表
        """
        papers = []

        try:
            root = ET.fromstring(xml_content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                paper = self._parse_entry(entry, ns)
                if paper:
                    papers.append(paper)

        except ET.ParseError as e:
            logger.error(f"XML解析失败: {e}")

        return papers

    def _parse_entry(self, entry: ET.Element, ns: Dict[str, str]) -> Optional[ArxivPaper]:
        """解析单个论文条目

        Args:
            entry: XML元素
            ns: 命名空间

        Returns:
            ArxivPaper或None
        """
        try:
            # ID
            paper_id = entry.find("atom:id", ns).text
            arxiv_id = paper_id.split("/")[-1] if "/" in paper_id else paper_id

            # 标题
            title = entry.find("atom:title", ns).text
            title = self._clean_text(title) if title else ""

            # 作者
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None and name.text:
                    authors.append(name.text)

            # 摘要
            summary = entry.find("atom:summary", ns)
            abstract = self._clean_text(summary.text) if summary is not None and summary.text else ""

            # 分类
            categories = []
            for cat in entry.findall("atom:category", ns):
                if cat.get("term"):
                    categories.append(cat.get("term"))

            # 日期
            published_str = entry.find("atom:published", ns).text
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

            updated_str = entry.find("atom:updated", ns).text
            updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))

            # PDF链接
            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")
                    break

            # DOI
            doi = None
            for elem in entry.findall("arxiv:doi", ns):
                if elem.text:
                    doi = elem.text
                    break

            # 评论
            comment = None
            for elem in entry.findall("arxiv:comment", ns):
                if elem.text:
                    comment = self._clean_text(elem.text)
                    break

            # 期刊引用
            journal_ref = None
            for elem in entry.findall("arxiv:journal_ref", ns):
                if elem.text:
                    journal_ref = elem.text
                    break

            return ArxivPaper(
                id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                categories=categories,
                published=published,
                updated=updated,
                pdf_url=pdf_url,
                doi=doi,
                comment=comment,
                journal_ref=journal_ref
            )

        except Exception as e:
            logger.error(f"解析论文条目失败: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """清理文本

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        # 移除多余空白
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def list_categories(self) -> Dict[str, str]:
        """列出所有支持的分类

        Returns:
            Dict[str, str]: 分类代码 -> 分类名称
        """
        return self.CATEGORIES.copy()


# 便捷函数
async def search_arxiv(
    query: Union[str, ArxivQuery],
    max_results: int = 10,
    categories: Optional[List[str]] = None
) -> ArxivSearchResult:
    """搜索ArXiv论文的便捷函数

    Args:
        query: 搜索查询
        max_results: 最大返回数量
        categories: 限定的分类列表

    Returns:
        ArxivSearchResult: 搜索结果
    """
    client = ArxivMCPClient()
    try:
        return await client.search_papers(query, max_results, categories)
    finally:
        await client.close()


async def get_arxiv_paper(paper_id: str) -> Optional[ArxivPaper]:
    """获取单个ArXiv论文

    Args:
        paper_id: 论文ID (如 2301.00001)

    Returns:
        ArxivPaper或None
    """
    client = ArxivMCPClient()
    try:
        result = await client.search_papers(f"id:{paper_id}", max_results=1)
        return result.papers[0] if result.papers else None
    finally:
        await client.close()


async def search_arxiv_by_author(
    author: str,
    max_results: int = 10
) -> ArxivSearchResult:
    """按作者搜索ArXiv论文的便捷函数

    Args:
        author: 作者姓名
        max_results: 最大结果数

    Returns:
        ArxivSearchResult: 搜索结果
    """
    client = ArxivMCPClient()
    try:
        return await client.search_by_author(author, max_results)
    finally:
        await client.close()


async def search_arxiv_recent(
    query: str,
    days: int = 30,
    max_results: int = 10
) -> ArxivSearchResult:
    """搜索最近ArXiv论文的便捷函数

    Args:
        query: 搜索查询
        days: 最近天数
        max_results: 最大结果数

    Returns:
        ArxivSearchResult: 搜索结果
    """
    client = ArxivMCPClient()
    try:
        return await client.search_recent(query, days, max_results)
    finally:
        await client.close()
