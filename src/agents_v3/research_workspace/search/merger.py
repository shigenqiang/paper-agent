"""多源搜索结果去重合并"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.search.base import SearchResult
from src.agents_v3.research_workspace.search.dedup import (
    DedupDecision,
    DedupService,
    _jaccard_similarity,
    normalize_title,
)


# 字段合并优先级：来源越可靠越优先
_SOURCE_PRIORITY = {
    "openalex": 4,
    "semantic_scholar": 3,
    "arxiv": 2,
    "pubmed": 1,
}


class SearchResultMerger:
    """多源搜索结果去重合并器"""

    def __init__(self):
        self.dedup_service = DedupService()

    def merge(self, results: list[SearchResult]) -> list[SearchResult]:
        """去重合并多源结果，返回去重后的列表"""
        if not results:
            return []

        # Group by dedup key
        groups: dict[str, list[SearchResult]] = {}
        no_key: list[SearchResult] = []

        for r in results:
            key = self._make_group_key(r)
            if key:
                groups.setdefault(key, []).append(r)
            else:
                no_key.append(r)

        # Merge each group
        merged: list[SearchResult] = []
        for group in groups.values():
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged.append(self._merge_group(group))

        # Check for possible duplicates across groups by title similarity
        merged = self._dedup_by_title_similarity(merged)

        merged.extend(no_key)
        return merged

    def _make_group_key(self, result: SearchResult) -> str | None:
        """生成分组 key"""
        if result.dedup_key:
            return result.dedup_key

        if result.doi:
            from src.agents_v3.research_workspace.search.dedup import normalize_doi
            return f"doi:{normalize_doi(result.doi)}"

        if result.arxiv_id:
            from src.agents_v3.research_workspace.search.dedup import normalize_arxiv_id
            return f"arxiv:{normalize_arxiv_id(result.arxiv_id)}"

        if result.openalex_id:
            return f"openalex:{result.openalex_id}"

        if result.semantic_scholar_id:
            return f"s2:{result.semantic_scholar_id}"

        title = normalize_title(result.title)
        if title and result.year:
            from src.agents_v3.research_workspace.search.dedup import first_author_key
            fa = first_author_key(result.authors)
            if fa:
                return f"tya:{title}|{result.year}|{fa}"
            return f"title_year:{title}|{result.year}"

        return None

    def _merge_group(self, group: list[SearchResult]) -> SearchResult:
        """合并一组重复结果"""
        # Sort by source priority (higher = better)
        group.sort(
            key=lambda r: _SOURCE_PRIORITY.get(r.source, 0),
            reverse=True,
        )

        best = group[0].model_copy()
        sources = [r.source for r in group]
        source_ids: dict[str, str] = {}

        for r in group:
            # Record source IDs
            if r.source == "openalex" and r.openalex_id:
                source_ids["openalex"] = r.openalex_id
            if r.source == "arxiv" and r.arxiv_id:
                source_ids["arxiv"] = r.arxiv_id

            # Merge fields by priority
            if not best.doi and r.doi:
                best.doi = r.doi
            if not best.arxiv_id and r.arxiv_id:
                best.arxiv_id = r.arxiv_id
            if not best.openalex_id and r.openalex_id:
                best.openalex_id = r.openalex_id
            if not best.url and r.url:
                best.url = r.url

            # PDF URL: prefer arxiv > openalex > others
            if r.pdf_url:
                if not best.pdf_url or r.source == "arxiv":
                    best.pdf_url = r.pdf_url

            # Abstract: take longest
            if r.abstract and len(r.abstract) > len(best.abstract or ""):
                best.abstract = r.abstract

            # Citations: take max
            if r.citations is not None:
                if best.citations is None or r.citations > best.citations:
                    best.citations = r.citations

            # Venue: prefer higher priority source
            if r.venue and (
                not best.venue
                or _SOURCE_PRIORITY.get(r.source, 0) > _SOURCE_PRIORITY.get(best.source, 0)
            ):
                best.venue = r.venue

            # Authors: prefer longer list
            if len(r.authors) > len(best.authors):
                best.authors = r.authors

        best.source = "+".join(sorted(set(sources)))
        best.source_payload = {
            "sources": list(set(sources)),
            "source_ids": source_ids,
        }

        logger.debug(f"Merged {len(group)} results for: {best.title[:50]}")
        return best

    def _dedup_by_title_similarity(self, results: list[SearchResult]) -> list[SearchResult]:
        """基于标题相似度的二次去重"""
        if len(results) <= 1:
            return results

        keep: list[bool] = [True] * len(results)

        for i in range(len(results)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(results)):
                if not keep[j]:
                    continue

                title_i = normalize_title(results[i].title)
                title_j = normalize_title(results[j].title)
                if not title_i or not title_j:
                    continue

                sim = _jaccard_similarity(title_i, title_j)
                if sim >= 0.85:
                    # 优先保留：来源优先级 > 年份更新 > 引用数更高
                    ri, rj = results[i], results[j]
                    pi = _SOURCE_PRIORITY.get(ri.source, 0)
                    pj = _SOURCE_PRIORITY.get(rj.source, 0)
                    if pj != pi:
                        if pj > pi:
                            keep[i] = False
                        else:
                            keep[j] = False
                    else:
                        # 同源：保留更新的版本
                        yi = ri.year or 0
                        yj = rj.year or 0
                        if yj > yi:
                            keep[i] = False
                        elif yi > yj:
                            keep[j] = False
                        else:
                            # 同年：保留引用更高的
                            ci = ri.citations or 0
                            cj = rj.citations or 0
                            if cj > ci:
                                keep[i] = False
                            else:
                                keep[j] = False
                    logger.debug(f"Title dedup: {sim:.2f} between '{results[i].title[:30]}' and '{results[j].title[:30]}'")

        return [r for r, k in zip(results, keep) if k]
