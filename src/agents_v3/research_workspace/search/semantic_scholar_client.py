"""Semantic Scholar API 搜索适配器

注意: 无 API Key 时免费限额极低(约1请求/秒)，连续请求易触发 429 限速且冷却期较长。
当前无法获取 API Key，该源默认不可用，需用户自行申请 Key 后启用。
申请地址: https://www.semanticscholar.org/product/api#api-key-form
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchField, SearchQuery, SearchResult

S2_API_URL = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,abstract,authors,year,venue,citationCount,influentialCitationCount,fieldsOfStudy,openAccessPdf,externalIds,tldr,publicationTypes,language"


class SemanticScholarClient(BaseSearchAdapter):
    """Semantic Scholar API 搜索适配器"""

    def __init__(self, api_key: str = "", min_interval: float = 1.0):
        self.api_key = api_key
        self.min_interval = min_interval
        self._last_request_time: float = 0.0

    @property
    def source_name(self) -> str:
        return "semantic_scholar"

    @property
    def supported_fields(self) -> set[SearchField]:
        return {SearchField.ALL}

    def search(self, query: SearchQuery) -> list[SearchResult]:
        self._rate_limit()
        params = self._build_params(query)
        url = f"{S2_API_URL}/paper/search?{params}"
        logger.info(f"Semantic Scholar search: {query.query}")

        try:
            headers = {"User-Agent": "PaperAgent/1.0 (research-tool)"}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = self._parse_response(data)
            for i, r in enumerate(results):
                r.source_rank = i + 1
            return results[:query.limit]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else 3
                logger.warning(f"S2 429, retrying in {wait}s...")
                time.sleep(wait)
                # 重试一次
                try:
                    req2 = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req2, timeout=20) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    results = self._parse_response(data)
                    for i, r in enumerate(results):
                        r.source_rank = i + 1
                    return results[:query.limit]
                except Exception:
                    pass
            logger.error(f"Semantic Scholar search failed: HTTP {e.code}")
            return []
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _build_params(self, query: SearchQuery) -> str:
        parts = [f"query={urllib.parse.quote(query.query)}"]
        parts.append(f"limit={min(query.limit, 100)}")
        if query.offset > 0:
            parts.append(f"offset={query.offset}")
        parts.append(f"fields={S2_FIELDS}")

        if query.year_from or query.year_to:
            year_filter = ""
            if query.year_from and query.year_to:
                year_filter = f"{query.year_from}-{query.year_to}"
            elif query.year_from:
                year_filter = f"{query.year_from}-"
            elif query.year_to:
                year_filter = f"-{query.year_to}"
            parts.append(f"year={year_filter}")

        return "&".join(parts)

    def _parse_response(self, data: dict[str, Any]) -> list[SearchResult]:
        results = []
        for paper in data.get("data", []):
            result = self._parse_paper(paper)
            if result:
                results.append(result)
        return results

    def _parse_paper(self, paper: dict[str, Any]) -> SearchResult | None:
        title = (paper.get("title") or "").strip()
        if not title:
            return None

        # Authors
        authors = []
        for author in paper.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # External IDs
        ext_ids = paper.get("externalIds") or {}
        doi = ext_ids.get("DOI", "") or ""
        arxiv_id = ext_ids.get("ArXiv", "") or ""
        pubmed_id = ext_ids.get("PubMed", "") or ""

        # Semantic Scholar ID
        s2_id = paper.get("paperId", "")

        # Year
        year = paper.get("year")

        # Venue
        venue = paper.get("venue", "") or ""

        # Abstract
        abstract = paper.get("abstract", "") or ""

        # PDF URL
        oa = paper.get("openAccessPdf") or {}
        pdf_url = oa.get("url", "") or ""

        # Citations
        citations = paper.get("citationCount")

        # Influential citations
        influential = paper.get("influentialCitationCount")

        # Fields of study
        fields = paper.get("fieldsOfStudy") or []
        concepts = [f for f in fields if f]

        # TLDR
        tldr_data = paper.get("tldr") or {}
        tldr = tldr_data.get("text", "") or ""

        # Language & publication type
        language = paper.get("language", "") or ""
        pub_types = paper.get("publicationTypes") or []
        publication_type = pub_types[0] if pub_types else ""

        return SearchResult(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            doi=doi,
            arxiv_id=arxiv_id,
            pubmed_id=pubmed_id,
            semantic_scholar_id=s2_id,
            url=f"https://www.semanticscholar.org/paper/{s2_id}",
            pdf_url=pdf_url,
            citations=citations,
            concepts=concepts,
            language=language,
            publication_type=publication_type,
            source="semantic_scholar",
            source_payload={
                "s2_id": s2_id,
                "influential_citations": influential,
                "tldr": tldr,
            },
        )
