"""Europe PMC API 搜索适配器

免费无Key，无限速，JSON直接返回。
API: https://www.ebi.ac.uk/europepmc/webservices/rest/search
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchField, SearchQuery, SearchResult

EPMC_API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class EuropePMCClient(BaseSearchAdapter):
    """Europe PMC API 搜索适配器"""

    def __init__(self, min_interval: float = 0.5):
        self.min_interval = min_interval
        self._last_request_time: float = 0.0

    @property
    def source_name(self) -> str:
        return "europepmc"

    @property
    def supported_fields(self) -> set[SearchField]:
        return {SearchField.ALL}

    def search(self, query: SearchQuery) -> list[SearchResult]:
        self._rate_limit()
        params = self._build_params(query)
        url = f"{EPMC_API_URL}?{params}"
        logger.info(f"Europe PMC search: {query.query}")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PaperAgent/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = self._parse_response(data)
            for i, r in enumerate(results):
                r.source_rank = i + 1
            return results[:query.limit]
        except Exception as e:
            logger.error(f"Europe PMC search failed: {e}")
            return []

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _build_params(self, query: SearchQuery) -> str:
        parts = [f"query={urllib.parse.quote(query.query)}"]
        parts.append(f"pageSize={min(query.limit, 100)}")
        if query.offset > 0:
            parts.append(f"cursorMark={query.offset}")
        parts.append("format=json")
        parts.append("resultType=core")

        if query.year_from or query.year_to:
            year_filter = ""
            if query.year_from and query.year_to:
                year_filter = f"(PUB_YEAR:[{query.year_from} TO {query.year_to}])"
            elif query.year_from:
                year_filter = f"(PUB_YEAR:[{query.year_from} TO 3000])"
            elif query.year_to:
                year_filter = f"(PUB_YEAR:[0 TO {query.year_to}])"
            if year_filter:
                parts[0] = f"query={urllib.parse.quote(query.query + ' ' + year_filter)}"

        return "&".join(parts)

    def _parse_response(self, data: dict[str, Any]) -> list[SearchResult]:
        results = []
        for item in data.get("resultList", {}).get("result", []):
            result = self._parse_paper(item)
            if result:
                results.append(result)
        return results

    def _parse_paper(self, paper: dict[str, Any]) -> SearchResult | None:
        title = (paper.get("title") or "").strip()
        if not title:
            return None

        # Authors - Europe PMC returns "A V, B D, C A." as a single string
        author_string = paper.get("authorString", "") or ""
        authors = [a.strip() for a in author_string.split(",") if a.strip()]

        # Year
        year = paper.get("pubYear")

        # Venue
        venue = paper.get("journalTitle", "") or ""

        # Abstract (may contain HTML tags)
        abstract = re.sub(r"<[^>]+>", " ", paper.get("abstractText", "") or "").strip()
        abstract = re.sub(r"\s+", " ", abstract)

        # DOI
        doi = paper.get("doi", "") or ""

        # PubMed ID
        pmid = paper.get("pmid", "") or ""

        # PMC ID
        pmcid = paper.get("pmcid", "") or ""

        # Citations
        citations = paper.get("citedByCount")

        # Keywords
        keyword_list = paper.get("keywordList", {}).get("keyword", []) or []
        keywords = [k for k in keyword_list if k]

        # Open access
        is_oa = paper.get("isOpenAccess", "") == "Y"

        # Full text URLs
        pdf_url = ""
        full_text_urls = paper.get("fullTextUrlList", {}).get("fullTextUrl", []) or []
        for ft in full_text_urls:
            url = ft.get("url", "")
            if url and ("pdf" in url.lower() or ft.get("documentStyle") == "pdf"):
                pdf_url = url
                break
        # Fallback: first available URL
        if not pdf_url and full_text_urls:
            pdf_url = full_text_urls[0].get("url", "")

        # Source (MED / PMC / etc.)
        source_db = paper.get("source", "") or ""

        return SearchResult(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            doi=doi,
            pubmed_id=pmid,
            url=f"https://europepmc.org/article/MED/{pmid}" if pmid else "",
            pdf_url=pdf_url,
            citations=citations,
            topics=keywords,
            keywords=keywords,
            source="europepmc",
            source_payload={
                "pmcid": pmcid,
                "is_oa": is_oa,
                "source_db": source_db,
                "author_string": author_string,
            },
        )
