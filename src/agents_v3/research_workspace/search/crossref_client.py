"""CrossRef API 搜索适配器"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchField, SearchQuery, SearchResult

CROSSREF_FIELD_PARAM = {
    SearchField.ALL: "query",
    SearchField.TITLE: "query.title",
    SearchField.AUTHOR: "query.author",
}

CROSSREF_API_URL = "https://api.crossref.org/works"


class CrossRefClient(BaseSearchAdapter):
    """CrossRef API 搜索适配器"""

    def __init__(self, mailto: str = ""):
        self.mailto = mailto

    @property
    def source_name(self) -> str:
        return "crossref"

    @property
    def supported_fields(self) -> set[SearchField]:
        return {SearchField.ALL, SearchField.TITLE, SearchField.AUTHOR}

    def search(self, query: SearchQuery) -> list[SearchResult]:
        params = self._build_params(query)
        url = f"{CROSSREF_API_URL}?{params}"
        logger.info(f"CrossRef search: {query.query}")

        try:
            headers = self._make_headers()
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = self._parse_response(data)
            for i, r in enumerate(results):
                r.source_rank = i + 1
            return results[:query.limit]
        except Exception as e:
            logger.error(f"CrossRef search failed: {e}")
            return []

    def search_by_doi(self, doi: str) -> SearchResult | None:
        """通过 DOI 查询元数据"""
        clean_doi = doi.strip()
        url = f"{CROSSREF_API_URL}/{urllib.parse.quote(clean_doi, safe='/')}"
        try:
            headers = self._make_headers()
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            work = data.get("message", {})
            return self._parse_work(work)
        except Exception as e:
            logger.error(f"CrossRef DOI lookup failed: {e}")
            return None

    def _make_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "PaperAgent/1.0 (research-tool)"}
        if self.mailto:
            headers["User-Agent"] = f"PaperAgent/1.0 (mailto:{self.mailto})"
        return headers

    def _build_params(self, query: SearchQuery) -> str:
        field = self._resolve_field(query.field)
        param = CROSSREF_FIELD_PARAM[field]
        parts = [f"{param}={urllib.parse.quote(query.query)}"]
        parts.append(f"rows={min(query.limit, 50)}")

        if query.year_from or query.year_to:
            filters = []
            if query.year_from:
                filters.append(f"from-pub-date:{query.year_from}")
            if query.year_to:
                filters.append(f"until-pub-date:{query.year_to}")
            parts.append(f"filter={','.join(filters)}")

        parts.append("sort=relevance")
        parts.append("order=desc")

        if self.mailto:
            parts.append(f"mailto={self.mailto}")

        return "&".join(parts)

    def _parse_response(self, data: dict[str, Any]) -> list[SearchResult]:
        results = []
        items = data.get("message", {}).get("items", [])
        for work in items:
            result = self._parse_work(work)
            if result:
                results.append(result)
        return results

    def _parse_work(self, work: dict[str, Any]) -> SearchResult | None:
        # Title
        title_list = work.get("title", [])
        title = title_list[0].strip() if title_list else ""
        if not title:
            return None

        # Authors
        authors = []
        for author in work.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if family:
                authors.append(f"{given} {family}".strip())

        # DOI
        doi = (work.get("DOI") or "").strip()

        # Year
        year = None
        date_parts = work.get("published-print", {}).get("date-parts") or \
                     work.get("published-online", {}).get("date-parts") or \
                     work.get("created", {}).get("date-parts")
        if date_parts and date_parts[0] and date_parts[0][0]:
            year = date_parts[0][0]

        # Venue
        venue_list = work.get("container-title", [])
        venue = venue_list[0] if venue_list else ""

        # Abstract (CrossRef returns JATS XML)
        abstract = (work.get("abstract") or "").strip()
        if abstract:
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()

        # URL
        url = work.get("URL", "")

        return SearchResult(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            abstract=abstract,
            url=url,
            source="crossref",
            source_payload={"crossref_doi": doi},
        )
