"""
Search Result Merger - 搜索结果去重与排序优化

提供跨源搜索结果的去重、评分和排序功能。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import re

from .base_searcher import SearchResult, SearchResponse


@dataclass
class MergedSearchResult:
    """合并后的搜索结果"""
    paper_id: str
    title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    year: int = 0
    venue: str = ""
    url: str = ""
    citations: int = 0
    doi: str = ""
    sources: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    source_scores: Dict[str, float] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_search_result(self) -> SearchResult:
        """转换为标准SearchResult"""
        return SearchResult(
            paper_id=self.paper_id,
            title=self.title,
            abstract=self.abstract,
            authors=self.authors,
            year=self.year,
            venue=self.venue,
            url=self.url,
            citations=self.citations,
            doi=self.doi,
            raw_data=self.raw_data
        )


@dataclass
class MergeConfig:
    """合并配置"""
    # 标题相似度阈值 (0-1)，超过则认为是重复
    title_similarity_threshold: float = 0.85
    # 是否启用DOI精确去重
    enable_doi_dedup: bool = True
    # 是否启用标题模糊去重
    enable_title_dedup: bool = True
    # 引用数权重
    citation_weight: float = 0.3
    # 年份权重
    year_weight: float = 0.2
    # 来源数权重
    source_weight: float = 0.2
    # 相关度权重
    relevance_weight: float = 0.3
    # 最小相关度阈值
    min_relevance_threshold: float = 0.1
    # 默认年份权重（用于缺失年份）
    default_year: int = 2020


class SearchResultMerger:
    """搜索结果合并器"""

    def __init__(self, config: Optional[MergeConfig] = None):
        self.config = config or MergeConfig()

    def merge(self, responses: List[SearchResponse]) -> List[MergedSearchResult]:
        """合并多个搜索源的响应

        Args:
            responses: 搜索响应列表

        Returns:
            合并去重后的结果列表
        """
        # 步骤1：收集所有结果
        all_results: List[Tuple[SearchResult, str]] = []
        for response in responses:
            if response.error:
                continue
            for result in response.results:
                all_results.append((result, response.source))

        if not all_results:
            return []

        # 步骤2：DOI精确去重
        doi_map: Dict[str, List[Tuple[SearchResult, str]]] = {}
        for result, source in all_results:
            if result.doi:
                doi = self._normalize_doi(result.doi)
                if doi:
                    doi_map.setdefault(doi, []).append((result, source))

        # 步骤3：基于DOI合并
        merged: Dict[str, MergedSearchResult] = {}
        for doi, items in doi_map.items():
            merged_result = self._merge_results(items)
            merged[doi] = merged_result

        # 步骤4：标题去重（处理无DOI结果）
        for result, source in all_results:
            if not result.doi or not self.config.enable_doi_dedup:
                # 尝试用DOI匹配
                if result.doi:
                    doi = self._normalize_doi(result.doi)
                    if doi in merged:
                        continue
                # 尝试用标题匹配
                if self.config.enable_title_dedup:
                    title_key = self._normalize_title_key(result.title)
                    matched = False
                    for existing_key, existing in merged.items():
                        existing_title_key = self._normalize_title_key(existing.title)
                        if self._calculate_similarity(title_key, existing_title_key) >= \
                           self.config.title_similarity_threshold:
                            # 合并到已有结果
                            self._merge_single_into(title_key, source, result, merged[existing_key])
                            matched = True
                            break
                    if matched:
                        continue
                # 新结果
                merged_result = self._create_merged_result(result, source)
                key = f"new_{result.paper_id}"
                merged[key] = merged_result

        # 步骤5：计算综合评分
        results = list(merged.values())
        self._calculate_relevance_scores(results)

        # 步骤6：排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        # 过滤低相关度结果
        results = [r for r in results
                   if r.relevance_score >= self.config.min_relevance_threshold]

        return results

    def _normalize_doi(self, doi: str) -> str:
        """标准化DOI"""
        # 移除URL前缀
        doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi)
        # 转换为小写
        return doi.lower().strip()

    def _normalize_title_key(self, title: str) -> str:
        """生成标题标准化键"""
        # 转小写
        title = title.lower()
        # 移除特殊字符
        title = re.sub(r'[^\w\s]', ' ', title)
        # 移除多余空格
        title = ' '.join(title.split())
        return title

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度（Jaccard）"""
        words1 = set(s1.split())
        words2 = set(s2.split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def _merge_results(self, items: List[Tuple[SearchResult, str]]) -> MergedSearchResult:
        """合并同一论文的多条结果"""
        # 使用第一条作为基础
        base_result, base_source = items[0]

        # 收集所有来源
        sources = [base_source]
        all_authors: Set[str] = set(base_result.authors or [])
        max_citations = base_result.citations
        all_raw_data: Dict[str, Any] = {"sources": {base_source: base_result.raw_data}}

        for result, source in items[1:]:
            sources.append(source)
            all_authors.update(result.authors or [])
            max_citations = max(max_citations, result.citations)
            all_raw_data["sources"][source] = result.raw_data

            # 选择最完整的摘要
            if not base_result.abstract and result.abstract:
                base_result.abstract = result.abstract

            # 选择最早的年份
            if result.year > 0 and (base_result.year == 0 or result.year < base_result.year):
                base_result.year = result.year

            # 选择有URL的结果
            if not base_result.url and result.url:
                base_result.url = result.url

        return MergedSearchResult(
            paper_id=base_result.paper_id,
            title=base_result.title,
            abstract=base_result.abstract,
            authors=list(all_authors),
            year=base_result.year or self.config.default_year,
            venue=base_result.venue,
            url=base_result.url,
            citations=max_citations,
            doi=base_result.doi,
            sources=sources,
            raw_data=all_raw_data
        )

    def _create_merged_result(self, result: SearchResult, source: str) -> MergedSearchResult:
        """从单条结果创建合并结果"""
        return MergedSearchResult(
            paper_id=result.paper_id,
            title=result.title,
            abstract=result.abstract,
            authors=result.authors or [],
            year=result.year or self.config.default_year,
            venue=result.venue,
            url=result.url,
            citations=result.citations,
            doi=result.doi,
            sources=[source],
            source_scores={source: 1.0}
        )

    def _merge_single_into(self, title_key: str, source: str,
                          result: SearchResult, merged: MergedSearchResult):
        """将单条结果合并到已有合并结果"""
        if source not in merged.sources:
            merged.sources.append(source)
        if result.abstract and not merged.abstract:
            merged.abstract = result.abstract
        if result.year > 0 and (merged.year == 0 or result.year < merged.year):
            merged.year = result.year
        if result.url and not merged.url:
            merged.url = result.url
        merged.citations = max(merged.citations, result.citations)
        merged.authors = list(set(merged.authors) | set(result.authors or []))
        merged.source_scores[source] = 1.0

    def _calculate_relevance_scores(self, results: List[MergedSearchResult]):
        """计算综合相关度评分"""
        if not results:
            return

        # 归一化因子
        max_citations = max(r.citations for r in results) or 1
        current_year = 2026
        max_source_count = max(len(r.sources) for r in results) or 1

        for result in results:
            # 1. 引用数评分 (归一化)
            citation_score = result.citations / max_citations if max_citations > 0 else 0

            # 2. 年份评分 (越近越高，使用指数衰减)
            years_ago = current_year - result.year
            year_score = max(0, 1 - (years_ago / 20))  # 20年后分数为0

            # 3. 来源数评分 (跨源越多越好)
            source_score = len(result.sources) / max_source_count if max_source_count > 0 else 0

            # 4. 来源质量评分
            source_quality = self._get_source_quality_scores(result.sources)
            quality_score = sum(source_quality.values()) / len(source_quality) if source_quality else 0

            # 综合评分
            result.relevance_score = (
                self.config.citation_weight * citation_score +
                self.config.year_weight * year_score +
                self.config.source_weight * source_score +
                self.config.relevance_weight * quality_score
            )

            # 存储各维度评分用于调试
            result.source_scores["citation"] = citation_score
            result.source_scores["year"] = year_score
            result.source_scores["source"] = source_score
            result.source_scores["quality"] = quality_score

    def _get_source_quality_scores(self, sources: List[str]) -> Dict[str, float]:
        """获取各来源质量评分"""
        quality_map = {
            "semantic_scholar": 0.95,  # 有引用数据和详情
            "openalex": 0.9,          # 开放获取，数据全面
            "arxiv": 0.85,             # 预印本，快速
            "pubmed": 0.9,             # 医学文献权威
        }
        return {s: quality_map.get(s, 0.7) for s in sources}


async def merge_search_results(
    responses: List[SearchResponse],
    config: Optional[MergeConfig] = None
) -> List[MergedSearchResult]:
    """便捷函数：合并搜索结果

    Args:
        responses: 搜索响应列表
        config: 合并配置

    Returns:
        合并去重排序后的结果
    """
    merger = SearchResultMerger(config)
    return merger.merge(responses)


def deduplicate_by_doi(results: List[SearchResult]) -> List[SearchResult]:
    """仅通过DOI去重

    Args:
        results: 搜索结果列表

    Returns:
        去重后的结果
    """
    seen_dois: Set[str] = set()
    unique: List[SearchResult] = []

    for result in results:
        if result.doi:
            doi = result.doi.lower().strip()
            if doi in seen_dois:
                continue
            seen_dois.add(doi)
        unique.append(result)

    return unique
