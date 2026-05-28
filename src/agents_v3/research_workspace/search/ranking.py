"""搜索结果排序和融合"""

from __future__ import annotations

import math
import re
from datetime import datetime

from src.agents_v3.research_workspace.search.base import SearchResult

# 来源优先级分
_SOURCE_PRIORITY = {
    "openalex": 0.9,
    "semantic_scholar": 0.8,
    "arxiv": 0.7,
    "pubmed": 0.7,
}

# 权重
_WEIGHTS = {
    "relevance": 0.45,
    "source_priority": 0.15,
    "recency": 0.15,
    "citation": 0.10,
    "metadata_completeness": 0.15,
}

_RRF_K = 60


def _tokenize(text: str) -> set[str]:
    """分词：小写化，按非字母数字分割，保留>=2字符的词"""
    return {w for w in re.split(r"[^\w]+", text.lower()) if len(w) >= 2}


class RankingService:
    """搜索结果排序服务"""

    def __init__(self, query: str = ""):
        self.query_tokens = _tokenize(query) if query else set()

    def rank(self, results: list[SearchResult], query: str = "") -> list[SearchResult]:
        """计算分数并排序"""
        if query:
            self.query_tokens = _tokenize(query)
        for r in results:
            r.relevance_score = self._compute_relevance(r)
            r.quality_score = self._compute_quality(r)
            r.final_score = self._compute_final(r)

        results.sort(key=lambda r: r.final_score, reverse=True)
        for i, r in enumerate(results):
            r.source_rank = i + 1

        return results

    def rrf_fuse(self, source_rankings: list[list[SearchResult]]) -> list[SearchResult]:
        """RRF 多源融合排序"""
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        for ranking in source_rankings:
            for rank, r in enumerate(ranking):
                key = r.result_id
                rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
                result_map[key] = r

        sorted_ids = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        results = []
        for rid in sorted_ids:
            r = result_map[rid]
            r.final_score = rrf_scores[rid]
            results.append(r)

        return results

    def _compute_relevance(self, r: SearchResult) -> float:
        """计算查询相关性分数（关键词匹配）"""
        if not self.query_tokens:
            return self._metadata_completeness(r)

        text_fields = [
            (r.title, 3.0),
            (r.abstract, 1.5),
            (" ".join(r.keywords), 2.0),
            (" ".join(r.concepts), 1.0),
            (r.venue, 0.5),
        ]

        total_weight = 0.0
        match_weight = 0.0
        for text, weight in text_fields:
            if not text:
                continue
            field_tokens = _tokenize(text)
            hits = len(self.query_tokens & field_tokens)
            total_weight += weight
            match_weight += weight * (hits / len(self.query_tokens))

        if total_weight == 0:
            return 0.0

        return min(match_weight / total_weight, 1.0)

    def _compute_quality(self, r: SearchResult) -> float:
        """计算质量分"""
        score = 0.0
        score += _SOURCE_PRIORITY.get(r.source, 0.5) * 0.4
        completeness = sum([
            bool(r.title) * 0.2,
            bool(r.abstract) * 0.3,
            bool(r.authors) * 0.15,
            bool(r.doi) * 0.15,
            bool(r.year) * 0.1,
            bool(r.venue) * 0.1,
        ])
        score += completeness * 0.6
        return min(score, 1.0)

    def _compute_final(self, r: SearchResult) -> float:
        """计算最终分数"""
        recency = self._recency_score(r.year)
        citation = self._citation_score(r.citations)

        return (
            _WEIGHTS["relevance"] * r.relevance_score
            + _WEIGHTS["source_priority"] * _SOURCE_PRIORITY.get(r.source, 0.5)
            + _WEIGHTS["recency"] * recency
            + _WEIGHTS["citation"] * citation
            + _WEIGHTS["metadata_completeness"] * self._metadata_completeness(r)
        )

    @staticmethod
    def _recency_score(year: int | None) -> float:
        if not year:
            return 0.3
        current_year = datetime.now().year
        age = max(0, current_year - year)
        return max(0.0, 1.0 - age / 20.0)

    @staticmethod
    def _citation_score(citations: int | None) -> float:
        if not citations or citations <= 0:
            return 0.0
        return min(1.0, math.log(citations + 1) / math.log(1001))

    @staticmethod
    def _metadata_completeness(r: SearchResult) -> float:
        fields = [r.title, r.abstract, r.authors, r.doi, r.year, r.venue, r.pdf_url]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)
