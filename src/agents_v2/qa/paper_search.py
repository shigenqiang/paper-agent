"""论文搜索Agent - 从arXiv和PubMed搜索统计学论文"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json

from .base_qa_agent import BaseQAAgent

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """论文数据结构"""
    paper_id: str
    title: str
    authors: List[str]
    year: int
    abstract: str = ""
    url: str = ""
    source: str = ""  # arxiv, pubmed
    citations: int = 0
    keywords: List[str] = field(default_factory=list)
    methodology: str = ""
    key_contributions: List[str] = field(default_factory=list)
    results: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "url": self.url,
            "source": self.source,
            "citations": self.citations,
            "keywords": self.keywords,
            "methodology": self.methodology,
            "key_contributions": self.key_contributions,
            "results": self.results
        }


@dataclass
class SearchResult:
    """搜索结果"""
    papers: List[Paper]
    total_count: int
    search_time: float
    query: str
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class PaperSearchAgent(BaseQAAgent):
    """
    论文搜索Agent

    支持的数据源:
    - arXiv: 机器学习、统计理论
    - PubMed: 生物统计、医学应用

    搜索策略:
    1. 多关键词组合
    2. 时间范围筛选
    3. 相关性排序
    4. 去重和过滤
    """

    def __init__(self):
        super().__init__(
            name="PaperSearchAgent",
            description="论文搜索Agent - 从arXiv和PubMed搜索统计学论文"
        )

    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行论文搜索

        Args:
            query: 搜索查询
            context: 包含 source, time_range, max_results 等

        Returns:
            搜索结果字典
        """
        self.logger.info(f"搜索论文: {query}")

        context = context or {}
        source = context.get("source", "all")  # all, arxiv, pubmed
        time_range = context.get("time_range", 365)  # 天数
        max_results = context.get("max_results", 10)
        page = context.get("page", 1)

        results = SearchResult(
            papers=[],
            total_count=0,
            search_time=0.0,
            query=query,
            filters_applied={"source": source, "time_range": time_range, "page": page}
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # 根据source决定搜索哪些数据源
            tasks = []

            if source in ["all", "arxiv"]:
                tasks.append(self._search_arxiv(query, time_range, max_results, page))

            if source in ["all", "pubmed"]:
                tasks.append(self._search_pubmed(query, time_range, max_results, page))

            # 并行执行搜索
            search_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 聚合结果
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    self.logger.error(f"搜索出错: {result}")
                    results.errors.append(str(result))
                else:
                    results.papers.extend(result)

            # 去重
            results.papers = self._deduplicate_papers(results.papers)

            # 排序
            results.papers = self._rank_papers(results.papers, query)

            results.total_count = len(results.papers)
            results.search_time = asyncio.get_event_loop().time() - start_time

            self.logger.info(f"找到 {results.total_count} 篇论文")

            return {
                "success": True,
                "papers": [p.to_dict() for p in results.papers],
                "total_count": results.total_count,
                "search_time": results.search_time,
                "query": query,
                "errors": results.errors
            }

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "papers": [],
                "total_count": 0
            }

    async def _search_arxiv(
        self,
        query: str,
        time_range: int = 365,
        max_results: int = 10,
        page: int = 1
    ) -> List[Paper]:
        """搜索arXiv"""
        try:
            import urllib.request
            import urllib.parse
            import xml.etree.ElementTree as ET
            import ssl

            # 创建SSL上下文（忽略证书验证）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 构建arXiv API查询 - 使用更宽泛的类别搜索
            base_url = "http://export.arxiv.org/api/query"
            # 搜索标题和摘要，不限制类别
            search_query = f"ti:{query} OR abs:{query}"
            start_date = datetime.now() - timedelta(days=time_range)
            date_query = f"submittedDate:[{start_date.strftime('%Y%m%d')} TO NOW]"

            start = (page - 1) * max_results

            params = urllib.parse.urlencode({
                "search_query": f"({search_query}) AND {date_query}",
                "start": start,
                "max_results": max_results,
                "sortBy": "relevance"
            })

            url = f"{base_url}?{params}"
            self.logger.debug(f"arXiv URL: {url}")

            # 发起请求
            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                data = response.read().decode("utf-8")

            # 解析XML
            papers = self._parse_arxiv_xml(data, query)
            self.logger.info(f"arXiv找到 {len(papers)} 篇论文")
            return papers

        except Exception as e:
            self.logger.error(f"arXiv搜索失败: {e}")
            return []

    async def _search_pubmed(
        self,
        query: str,
        time_range: int = 365,
        max_results: int = 10,
        page: int = 1
    ) -> List[Paper]:
        """搜索PubMed"""
        try:
            import urllib.request
            import urllib.parse
            import xml.etree.ElementTree as ET
            import ssl

            # 创建SSL上下文（忽略证书验证）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # PubMed E-utilities
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            search_url = f"{base_url}esearch.fcgi"

            # 直接搜索标题和摘要，不添加额外限制
            search_query = f"{query}[Title/Abstract]"

            params = urllib.parse.urlencode({
                "db": "pubmed",
                "term": search_query,
                "retmax": max_results,
                "retstart": (page - 1) * max_results,
                "retmode": "json",
                "datetype": "pdat",
                "reldate": time_range
            })

            url = f"{search_url}?{params}"
            self.logger.debug(f"PubMed Search URL: {url}")

            # 获取ID列表
            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                import json as json_lib
                search_data = json_lib.loads(response.read().decode("utf-8"))

            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            # 获取详情
            summary_url = f"{base_url}esummary.fcgi"
            summary_params = urllib.parse.urlencode({
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            })

            with urllib.request.urlopen(f"{summary_url}?{summary_params}", timeout=30, context=ssl_context) as response:
                summary_data = json_lib.loads(response.read().decode("utf-8"))

            # 解析结果
            papers = self._parse_pubmed_summary(summary_data, query)
            self.logger.info(f"PubMed找到 {len(papers)} 篇论文")
            return papers

        except Exception as e:
            self.logger.error(f"PubMed搜索失败: {e}")
            return []

    def _parse_arxiv_xml(self, xml_data: str, query: str) -> List[Paper]:
        """解析arXiv XML响应"""
        papers = []
        try:
            root = ET.fromstring(xml_data)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                try:
                    paper_id = entry.find("atom:id", ns).text.split("/")[-1]

                    title = entry.find("atom:title", ns).text or ""
                    title = " ".join(title.split())  # 清理空白

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

                    # 提取关键词/类别
                    categories = [
                        cat.get("term")
                        for cat in entry.findall("atom:category", ns)
                    ]

                    paper = Paper(
                        paper_id=paper_id,
                        title=title,
                        authors=authors,
                        year=year,
                        abstract=abstract,
                        url=url,
                        source="arxiv",
                        keywords=categories,
                        methodology=self._extract_methodology(abstract),
                        key_contributions=self._extract_contributions(abstract)
                    )
                    papers.append(paper)

                except Exception as e:
                    self.logger.warning(f"解析论文失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"XML解析失败: {e}")

        return papers

    def _parse_pubmed_summary(self, summary_data: Dict, query: str) -> List[Paper]:
        """解析PubMed摘要响应"""
        papers = []
        try:
            result = summary_data.get("result", {})
            for pmid, info in result.items():
                if pmid == "uids":
                    continue

                try:
                    # 提取作者
                    authors = []
                    author_list = info.get("authors", [])
                    for auth in author_list:
                        if "name" in auth:
                            authors.append(auth["name"])

                    # 提取摘要（如果可用）
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

                    paper = Paper(
                        paper_id=pmid,
                        title=info.get("title", ""),
                        authors=authors,
                        year=year,
                        abstract=abstract,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        source="pubmed",
                        citations=citations,
                        methodology=self._extract_methodology(abstract),
                        key_contributions=self._extract_contributions(abstract)
                    )
                    papers.append(paper)

                except Exception as e:
                    self.logger.warning(f"解析PubMed论文失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"PubMed摘要解析失败: {e}")

        return papers

    def _extract_methodology(self, text: str) -> str:
        """从摘要中提取方法关键词"""
        methods = []
        method_keywords = [
            "markov chain monte carlo", "mcmc", "bayesian", "neural network",
            "deep learning", "regression", "classification", "clustering",
            "hierarchical model", "mixed model", "survival analysis",
            "causal inference", "propensity score", "bootstrap"
        ]

        text_lower = text.lower()
        for method in method_keywords:
            if method in text_lower:
                methods.append(method)

        return ", ".join(methods) if methods else "未明确说明"

    def _extract_contributions(self, text: str) -> List[str]:
        """从摘要中提取主要贡献"""
        contributions = []

        # 简单规则：提取包含"propose", "develop", "introduce"等的句子
        sentences = text.split(". ")
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in ["propose", "develop", "introduce", "present", "new"]):
                contributions.append(sent.strip()[:200])  # 限制长度

        return contributions[:3]  # 最多3个贡献

    def _deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """去除重复论文"""
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            # 使用标题标准化后去重
            normalized_title = paper.title.lower().strip()
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_papers.append(paper)

        return unique_papers

    def _rank_papers(self, papers: List[Paper], query: str) -> List[Paper]:
        """根据相关性排序"""
        query_terms = set(query.lower().split())

        def relevance_score(paper: Paper) -> float:
            score = 0.0

            # 标题匹配
            title_lower = paper.title.lower()
            for term in query_terms:
                if term in title_lower:
                    score += 3.0

            # 摘要匹配
            abstract_lower = paper.abstract.lower()
            for term in query_terms:
                if term in abstract_lower:
                    score += 1.0

            # 引用数（归一化）
            try:
                citations = int(paper.citations) if paper.citations else 0
            except (ValueError, TypeError):
                citations = 0
            score += min(citations / 100, 2.0)

            # 最新论文加分
            if paper.year >= 2024:
                score += 1.0
            elif paper.year >= 2023:
                score += 0.5

            return score

        return sorted(papers, key=relevance_score, reverse=True)

    def search_by_keywords(
        self,
        keywords: List[str],
        source: str = "all"
    ) -> List[Paper]:
        """
        基于关键词列表搜索（同步方法）

        适用于每日推送等场景
        """
        query = " ".join(keywords)
        # 同步调用
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            self.execute(query, {"source": source, "max_results": 20})
        )

        return [Paper(**p) for p in result.get("papers", [])]