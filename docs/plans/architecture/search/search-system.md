# Search System 学术搜索系统详解

> 位置: `src/agents_v2/search/` 和 `src/agents_v2/paper_search/`

## 一、架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    学术搜索系统 (Academic Search System)                     │
└─────────────────────────────────────────────────────────────────────────────┘

                           ┌─────────────────────┐
                           │   QueryRouter       │
                           │   (查询路由)         │
                           └──────────┬──────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  arXiv          │      │  PubMed          │      │  Semantic Scholar│
│  searcher.py    │      │  searcher.py    │      │  searcher.py    │
│                 │      │                 │      │                 │
│  API: arXiv.org │      │  API: NCBI       │      │  API: S2         │
└─────────────────┘      └─────────────────┘      └─────────────────┘
          │                           │                           │
          └───────────────────────────┼───────────────────────────┘
                                      │
                             ┌────────┴────────┐
                             ▼                 ▼
                    ┌─────────────────┐  ┌─────────────────┐
                    │ OpenAlex        │  │  CrossRef       │
                    │ searcher.py    │  │  searcher.py    │
                    └─────────────────┘  └─────────────────┘
                                      │
                             ┌────────┴────────┐
                             ▼
                    ┌─────────────────┐
                    │ SearchResultMerger│
                    │ (结果合并)        │
                    └────────┬──────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  PaperSearchAgent│
                    │  (聚合搜索)      │
                    └─────────────────┘
```

## 二、Searcher 基类

```python
# search/base_searcher.py

class BaseSearcher(ABC):
    """学术搜索器基类"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    @abstractmethod
    async def search(self, query: str, max_results: int = 20) -> List[Paper]:
        """执行搜索，返回论文列表"""
        pass

    @abstractmethod
    def parse_response(self, raw_response: Any) -> List[Paper]:
        """解析 API 响应"""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称"""
        pass

    def _rate_limit(self):
        """速率限制"""
        ...
```

## 三、各搜索器实现

### 3.1 arXiv Searcher

```python
# search/arxiv_searcher.py

class ArxivSearcher(BaseSearcher):
    """arXiv 学术论文搜索"""

    BASE_URL = "http://export.arxiv.org/api/query"

    async def search(self, query: str, max_results: int = 20) -> List[Paper]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance"
        }

        response = await self._fetch(self.BASE_URL, params)
        return self.parse_response(response)

    def parse_response(self, xml_text: str) -> List[Paper]:
        """解析 Atom XML 响应"""
        root = ET.fromstring(xml_text)
        papers = []

        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            paper = Paper(
                id=entry.find("{http://www.w3.org/2005/Atom}id").text,
                title=entry.find("{http://www.w3.org/2005/Atom}title").text,
                summary=entry.find("{http://www.w3.org/2005/Atom}summary").text,
                authors=[a.text for a in entry.findall("{http://www.w3.org/2005/Atom}author")],
                published=entry.find("{http://www.w3.org/2005/Atom}published").text,
                categories=self._parse_categories(entry),
                pdf_url=self._extract_pdf_url(entry)
            )
            papers.append(paper)

        return papers

    def _extract_pdf_url(self, entry) -> str:
        for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
            if link.get("title") == "pdf":
                return link.get("href")
```

### 3.2 PubMed Searcher

```python
# search/pubmed_searcher.py

class PubMedSearcher(BaseSearcher):
    """PubMed 生物医学文献搜索"""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    async def search(self, query: str, max_results: int = 20) -> List[Paper]:
        # Step 1: 搜索 PMID
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }
        search_result = await self._fetch(self.BASE_URL, search_params)
        pmid_list = search_result["esearchresult"]["idlist"]

        # Step 2: 获取摘要
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmid_list),
            "retmode": "json"
        }
        summaries = await self._fetch(self.SUMMARY_URL, summary_params)

        return self._parse_summaries(summaries)
```

### 3.3 Semantic Scholar Searcher

```python
# search/semantic_scholar_searcher.py

class SemanticScholarSearcher(BaseSearcher):
    """Semantic Scholar 学术搜索"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    HEADERS = {
        "x-api-key": os.getenv("S2_API_KEY", "")
    }

    async def search(self, query: str, max_results: int = 20) -> List[Paper]:
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,citationCount,influentialCitationCount,venue"
        }

        response = await self._fetch(
            self.BASE_URL,
            params,
            headers=self.HEADERS
        )

        return self.parse_response(response)
```

### 3.4 OpenAlex Searcher

```python
# search/openalex_searcher.py

class OpenAlexSearcher(BaseSearcher):
    """OpenAlex 开放学术数据搜索"""

    BASE_URL = "https://api.openalex.org/works"

    async def search(self, query: str, max_results: int = 20) -> List[Paper]:
        params = {
            "search": query,
            "per_page": max_results,
            "filter": "open_access:true"
        }

        response = await self._fetch(self.BASE_URL, params)
        return self._parse_response(response)
```

### 3.5 CrossRef Searcher

```python
# search/crossref_searcher.py

class CrossRefSearcher(BaseSearcher):
    """CrossRef DOI 和元数据搜索"""

    BASE_URL = "https://api.crossref.org/works"

    async def search(self, query: str, max_results: int = 20) -> List[Paper]:
        params = {
            "query": query,
            "rows": max_results,
            "select": "DOI,title,author,published,container-title"
        }

        response = await self._fetch(
            self.BASE_URL,
            params,
            headers={"User-Agent": "PaperAgent/1.0"}
        )

        return self._parse_response(response)
```

## 四、结果合并

```python
# search/search_result_merger.py

class SearchResultMerger:
    """多源搜索结果合并与去重"""

    def merge(self, results: Dict[str, List[Paper]]) -> List[Paper]:
        """
        合并多个来源的结果
        1. 按相关性评分排序
        2. 去重 (相同 DOI)
        3. 合并作者列表
        """
        all_papers = []

        for source, papers in results.items():
            for paper in papers:
                paper.source = source
                all_papers.append(paper)

        # 按相关性排序
        all_papers.sort(key=lambda p: p.relevance_score, reverse=True)

        # 去重
        seen_dois = set()
        unique_papers = []
        for paper in all_papers:
            if paper.doi and paper.doi not in seen_dois:
                seen_dois.add(paper.doi)
                unique_papers.append(paper)
            elif not paper.doi:
                unique_papers.append(paper)

        return unique_papers

    def deduplicate(self, papers: List[Paper]) -> List[Paper]:
        """基于 DOI 和标题去重"""
        ...
```

## 五、PaperSearchAgent (聚合搜索)

```python
# paper_search/paper_search.py

class PaperSearchAgent:
    """多源论文搜索 Agent"""

    def __init__(self, llm_config: LLMConfig):
        self.searchers = {
            "arxiv": ArxivSearcher(),
            "pubmed": PubMedSearcher(),
            "semantic_scholar": SemanticScholarSearcher(),
            "openalex": OpenAlexSearcher(),
            "crossref": CrossRefSearcher()
        }
        self.merger = SearchResultMerger()

    async def search(self, query: str, sources: List[str] = None, max_results: int = 20) -> dict:
        """
        并行搜索多个来源
        """
        if sources is None:
            sources = list(self.searchers.keys())

        # 并行执行
        tasks = []
        for source in sources:
            if source in self.searchers:
                tasks.append(self._search_source(source, query, max_results))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        valid_results = {s: r for s, r in zip(sources, results) if not isinstance(r, Exception)}
        merged_papers = self.merger.merge(valid_results)

        return {
            "papers": merged_papers[:max_results],
            "total": len(merged_papers),
            "sources": sources
        }

    async def _search_source(self, source: str, query: str, max_results: int):
        return await self.searchers[source].search(query, max_results)
```

## 六、搜索参数配置

| 数据源 | API 限制 | 速率限制 | 特殊参数 |
|--------|----------|----------|----------|
| arXiv | 3000 请求/小时 | 3s/请求 | sortBy |
| PubMed | 无明确限制 | 3/s (建议) | esearch/esummary |
| Semantic Scholar | 100 请求/分钟 | 600ms/请求 | 需要 API Key |
| OpenAlex | 无限制 | 50/秒 | filter |
| CrossRef | 50/秒 | 50/秒 | User-Agent 必须 |

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/search/` 和 `src/agents_v2/paper_search/`