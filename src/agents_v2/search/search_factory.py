"""
Search Factory - 搜索器工厂

统一创建和管理多种搜索器。
"""
from typing import Dict, List, Optional

from .base_searcher import BaseSearcher, SearchResult, SearchResponse
from .arxiv_searcher import ArxivSearcher
from .pubmed_searcher import PubmedSearcher
from .semantic_scholar_searcher import SemanticScholarSearcher
from .openalex_searcher import OpenAlexSearcher
from .search_result_merger import (
    SearchResultMerger,
    MergedSearchResult,
    MergeConfig,
    merge_search_results,
)


class SearchFactory:
    """搜索器工厂"""

    _searchers: Dict[str, BaseSearcher] = {}

    @classmethod
    def register(cls, name: str, searcher: BaseSearcher) -> None:
        """注册搜索器

        Args:
            name: 搜索器名称
            searcher: 搜索器实例
        """
        cls._searchers[name] = searcher

    @classmethod
    def get(cls, name: str) -> Optional[BaseSearcher]:
        """获取搜索器

        Args:
            name: 搜索器名称

        Returns:
            BaseSearcher or None
        """
        if name not in cls._searchers:
            # 自动创建
            if name == "arxiv":
                cls._searchers[name] = ArxivSearcher()
            elif name == "pubmed":
                cls._searchers[name] = PubmedSearcher()
            elif name == "semantic_scholar":
                cls._searchers[name] = SemanticScholarSearcher()
            elif name == "openalex":
                cls._searchers[name] = OpenAlexSearcher()
            else:
                return None
        return cls._searchers[name]

    @classmethod
    def list_searchers(cls) -> List[str]:
        """列出所有已注册的搜索器

        Returns:
            List of searcher names
        """
        return list(cls._searchers.keys())

    @classmethod
    async def search_all(cls, query: str, max_results: int = 10) -> List[SearchResponse]:
        """使用所有搜索器搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            List of SearchResponse
        """
        responses = []
        for name in ["arxiv", "pubmed", "semantic_scholar", "openalex"]:
            searcher = cls.get(name)
            if searcher:
                result = await searcher.search(query, max_results)
                responses.append(result)
        return responses

    @classmethod
    async def search_with(cls, names: List[str], query: str,
                         max_results: int = 10) -> List[SearchResponse]:
        """使用指定的搜索器搜索

        Args:
            names: 搜索器名称列表
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            List of SearchResponse
        """
        responses = []
        for name in names:
            searcher = cls.get(name)
            if searcher:
                result = await searcher.search(query, max_results)
                responses.append(result)
        return responses

    @classmethod
    async def search_merged(cls, query: str, max_results: int = 10,
                           config: Optional[MergeConfig] = None) -> List[MergedSearchResult]:
        """使用所有搜索器搜索并合并去重

        Args:
            query: 搜索查询
            max_results: 最大结果数
            config: 合并配置

        Returns:
            合并去重排序后的结果列表
        """
        responses = await cls.search_all(query, max_results)
        return await merge_search_results(responses, config)

    @classmethod
    def get_merger(cls, config: Optional[MergeConfig] = None) -> SearchResultMerger:
        """获取结果合并器

        Args:
            config: 合并配置

        Returns:
            SearchResultMerger实例
        """
        return SearchResultMerger(config)


def get_searcher(name: str) -> Optional[BaseSearcher]:
    """便捷函数：获取搜索器"""
    return SearchFactory.get(name)


async def search_all(query: str, max_results: int = 10) -> List[SearchResponse]:
    """便捷函数：使用所有搜索器搜索"""
    return await SearchFactory.search_all(query, max_results)


async def search_merged(query: str, max_results: int = 10,
                       config: Optional[MergeConfig] = None) -> List[MergedSearchResult]:
    """便捷函数：使用所有搜索器搜索并合并去重"""
    return await SearchFactory.search_merged(query, max_results, config)
