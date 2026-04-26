"""
Base Searcher - 搜索基类定义

定义搜索器接口和通用功能。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    """搜索结果"""
    paper_id: str
    title: str
    abstract: str = ""
    authors: List[str] = None
    year: int = 0
    venue: str = ""
    url: str = ""
    citations: int = 0
    doi: str = ""
    raw_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.raw_data is None:
            self.raw_data = {}


@dataclass
class SearchResponse:
    """搜索响应"""
    query: str
    total: int
    results: List[SearchResult]
    source: str
    error: Optional[str] = None

    def __post_init__(self):
        if self.error is None:
            self.error = ""


class BaseSearcher(ABC):
    """搜索器基类"""

    def __init__(self, name: str):
        self.name = name
        self.max_results = 10

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """执行搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            SearchResponse
        """
        pass

    async def get_paper(self, paper_id: str) -> Optional[SearchResult]:
        """获取单个论文详情

        Args:
            paper_id: 论文ID

        Returns:
            SearchResult or None
        """
        return None

    def _create_response(self, query: str, results: List[SearchResult],
                        source: str, error: str = "") -> SearchResponse:
        """创建搜索响应"""
        return SearchResponse(
            query=query,
            total=len(results),
            results=results,
            source=source,
            error=error
        )
