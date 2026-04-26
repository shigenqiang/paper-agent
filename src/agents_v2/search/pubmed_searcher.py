"""
PubMed Searcher - 生物医学文献搜索

搜索PubMed生物医学数据库。
"""
import logging
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
            results = self._mock_search(query, max_results)
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
            return SearchResult(
                paper_id=paper_id,
                title=f"PubMed Paper {paper_id}",
                abstract="This is a biomedical research abstract.",
                authors=["Researcher A", "Researcher B"],
                year=2023,
                venue="PubMed",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{paper_id}/",
                citations=20,
                doi=f"10.1234/pubmed.{paper_id}"
            )
        except Exception as e:
            logger.error(f"Get PubMed paper failed: {e}")
            return None

    def _mock_search(self, query: str, max_results: int) -> list:
        """模拟搜索结果"""
        return [
            SearchResult(
                paper_id=f"PMID{35000000 + i}",
                title=f"{query} - Biomedical Study {i}",
                abstract=f"Abstract for biomedical study {i} about {query}...",
                authors=[f"Dr. {j}" for j in ["Smith", "Johnson"]],
                year=2021 + i % 4,
                venue="Nature Medicine" if i % 2 == 0 else "Cell",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{35000000 + i}/",
                citations=i * 3
            )
            for i in range(1, min(max_results + 1, 11))
        ]
