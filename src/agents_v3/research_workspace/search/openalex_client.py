"""OpenAlex API 搜索适配器"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchField, SearchQuery, SearchResult

OPENALEX_API_URL = "https://api.openalex.org/works"


class OpenAlexClient(BaseSearchAdapter):
    """OpenAlex API 搜索适配器"""

    def __init__(self, email: str = "", min_interval: float = 0.5):
        self.email = email
        self.min_interval = min_interval

    @property
    def source_name(self) -> str:
        return "openalex"

    @property
    def supported_fields(self) -> set[SearchField]:
        return {SearchField.ALL, SearchField.TITLE}

    def search(self, query: SearchQuery) -> list[SearchResult]:
        params = self._build_params(query)
        url = f"{OPENALEX_API_URL}?{params}"
        logger.info(f"OpenAlex search: {query.query}")

        try:
            headers = {"User-Agent": f"PaperAgent/1.0 (mailto:{self.email})" if self.email else "PaperAgent/1.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = self._parse_response(data)
            for i, r in enumerate(results):
                r.source_rank = i + 1
            return results[:query.limit]
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return []

    def search_by_doi(self, doi: str) -> SearchResult | None:
        """通过 DOI 查询单篇论文"""
        url = f"{OPENALEX_API_URL}/doi:{doi}"
        try:
            headers = {"User-Agent": f"PaperAgent/1.0 (mailto:{self.email})" if self.email else "PaperAgent/1.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return self._parse_work(data)
        except Exception as e:
            logger.error(f"OpenAlex DOI lookup failed: {e}")
            return None

    def _build_params(self, query: SearchQuery) -> str:
        field = self._resolve_field(query.field)
        if field == SearchField.TITLE:
            parts = [f"filter=title.search:{urllib.parse.quote(query.query)}"]
        else:
            # OpenAlex author filter 不可靠，ALL 和 AUTHOR 都用 search= 全文搜索
            parts = [f"search={urllib.parse.quote(query.query)}"]

        if query.year_from or query.year_to:
            year_filter = ""
            if query.year_from and query.year_to:
                year_filter = f"publication_year:{query.year_from}-{query.year_to}"
            elif query.year_from:
                year_filter = f"publication_year:{query.year_from}-"
            elif query.year_to:
                year_filter = f"publication_year:-{query.year_to}"
            parts.append(f"filter={year_filter}")

        parts.append(f"per_page={min(query.limit, 50)}")
        if query.offset > 0:
            page = query.offset // query.limit + 1
            parts.append(f"page={page}")
        parts.append("sort=relevance_score:desc")

        if self.email:
            parts.append(f"mailto={self.email}")

        return "&".join(parts)

    def _parse_response(self, data: dict[str, Any]) -> list[SearchResult]:
        results = []
        for work in data.get("results", []):
            result = self._parse_work(work)
            if result:
                results.append(result)
        return results

    def _parse_work(self, work: dict[str, Any]) -> SearchResult | None:
        title = (work.get("title") or "").strip()
        if not title:
            return None

        # Authors
        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        # DOI
        doi = (work.get("doi") or "")
        doi = doi.replace("https://doi.org/", "")

        # Year
        year = work.get("publication_year")

        # Venue
        venue = ""
        primary_loc = work.get("primary_location") or {}
        source = primary_loc.get("source") or {}
        venue = source.get("display_name", "")

        # Abstract from inverted index
        abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))

        # PDF URL
        pdf_url = ""
        best_oa = work.get("best_oa_location") or {}
        pdf_url = best_oa.get("pdf_url", "") or ""

        # Citations
        citations = work.get("cited_by_count")

        # Topics (OpenAlex concepts → topics)
        topics = [c.get("display_name", "") for c in work.get("concepts", []) if c.get("display_name")]

        # OpenAlex ID
        openalex_id = (work.get("id") or "").replace("https://openalex.org/", "")

        # Language & type
        language = work.get("language", "") or ""
        publication_type = work.get("type", "") or ""

        return SearchResult(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            doi=doi,
            openalex_id=openalex_id,
            url=work.get("id", ""),
            pdf_url=pdf_url,
            citations=citations,
            topics=topics,
            language=language,
            publication_type=publication_type,
            source="openalex",
            source_payload={"openalex_id": openalex_id},
        )

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
        """从 OpenAlex inverted index 恢复摘要文本"""
        if not inverted_index:
            return ""
        # inverted_index: {"word": [pos1, pos2, ...], ...}
        positions: list[tuple[int, str]] = []
        for word, pos_list in inverted_index.items():
            for pos in pos_list:
                positions.append((pos, word))
        positions.sort()
        return " ".join(w for _, w in positions)
