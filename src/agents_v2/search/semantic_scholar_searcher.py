"""
Semantic Scholar Searcher - 语义学术搜索

搜索Semantic Scholar学术数据库。
"""
import logging
from typing import Optional

from .base_searcher import BaseSearcher, SearchResult, SearchResponse

logger = logging.getLogger(__name__)


class SemanticScholarSearcher(BaseSearcher):
    """Semantic Scholar搜索器"""

    def __init__(self):
        super().__init__("semantic_scholar")

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """搜索Semantic Scholar论文

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        try:
            results = self._mock_search(query, max_results)
            return self._create_response(query, results, self.name)

        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return self._create_response(query, [], self.name, str(e))

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取Semantic Scholar论文详情

        Args:
            paper_id: Paper ID

        Returns:
            SearchResult
        """
        try:
            return SearchResult(
                paper_id=paper_id,
                title=f"Semantic Scholar Paper {paper_id}",
                abstract="This paper is from Semantic Scholar database.",
                authors=["Academic A", "Academic B"],
                year=2023,
                venue="ICML",
                url=f"https://www.semanticscholar.org/paper/{paper_id}",
                citations=50,
                doi=f"10.1234/ss.{paper_id}"
            )
        except Exception as e:
            logger.error(f"Get Semantic Scholar paper failed: {e}")
            return None

    async def get_citations(self, paper_id: str, max_results: int = 50) -> SearchResponse:
        """获取论文引用

        Args:
            paper_id: 论文ID
            max_results: 最大结果数

        Returns:
            SearchResponse: 引用列表
        """
        try:
            citations = [
                SearchResult(
                    paper_id=f"citation_{i}",
                    title=f"Citing Paper {i}",
                    abstract=f"This paper cites {paper_id}...",
                    authors=[f"Author {j}" for j in range(2)],
                    year=2022 + i % 3,
                    venue="NeurIPS",
                    citations=i * 2
                )
                for i in range(1, min(max_results + 1, 21))
            ]
            return self._create_response(f"citations:{paper_id}", citations, f"{self.name}_citations")

        except Exception as e:
            logger.error(f"Get citations failed: {e}")
            return self._create_response(f"citations:{paper_id}", [], f"{self.name}_citations", str(e))

    def _mock_search(self, query: str, max_results: int) -> list:
        """模拟搜索结果"""
        return [
            SearchResult(
                paper_id=f"ss_{i}",
                title=f"{query} - Research Paper {i}",
                abstract=f"Abstract for paper {i} about {query}...",
                authors=[f"Researcher {j}" for j in range(3)],
                year=2020 + i % 5,
                venue="ICML" if i % 2 == 0 else "NeurIPS",
                url=f"https://www.semanticscholar.org/paper/ss_{i}",
                citations=i * 10
            )
            for i in range(1, min(max_results + 1, 11))
        ]
