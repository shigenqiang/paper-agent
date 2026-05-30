"""arXiv API 搜索适配器"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from loguru import logger

from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchField, SearchQuery, SearchResult

ARXIV_FIELD_PREFIX = {
    SearchField.ALL: "all",
    SearchField.TITLE: "ti",
    SearchField.AUTHOR: "au",
    SearchField.ABSTRACT: "abs",
}

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


class ArxivClient(BaseSearchAdapter):
    """arXiv API 搜索适配器"""

    def __init__(self, max_results: int = 20, min_interval: float = 3.0):
        self.max_results = max_results
        self.min_interval = min_interval
        self._last_request_time: float = 0.0

    @property
    def source_name(self) -> str:
        return "arxiv"

    @property
    def supported_fields(self) -> set[SearchField]:
        return {SearchField.ALL, SearchField.TITLE, SearchField.AUTHOR, SearchField.ABSTRACT}

    def search(self, query: SearchQuery) -> list[SearchResult]:
        self._rate_limit()
        params = self._build_params(query)
        url = f"{ARXIV_API_URL}?{params}"
        logger.info(f"arXiv search: {query.query}")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PaperAgent/1.0 (research-tool)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                xml_data = resp.read()
            results = self._parse_response(xml_data)
            # Year post-filter (arXiv API doesn't support year filtering)
            results = self._filter_by_year(results, query.year_from, query.year_to)
            # Set source_rank
            for i, r in enumerate(results):
                r.source_rank = i + 1
            return results[:query.limit]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After", "")
                logger.warning(f"arXiv 429, Retry-After: {retry_after}")
                if retry_after.isdigit():
                    time.sleep(int(retry_after))
            logger.error(f"arXiv search failed: HTTP {e.code}")
            return []
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _build_params(self, query: SearchQuery) -> str:
        field = self._resolve_field(query.field)
        prefix = ARXIV_FIELD_PREFIX[field]
        # 先去掉已有引号，再统一加引号，避免嵌套引号导致 HTTP 400
        q_body = query.query.strip().strip('"').strip("'")
        # 截断过长查询（arXiv 限制约 300 字符）
        if len(q_body) > 200:
            q_body = q_body[:200].rsplit(" ", 1)[0]
        if " " in q_body:
            q_body = f'"{q_body}"'
        q = urllib.parse.quote(f"{prefix}:{q_body}")
        limit = min(query.limit, self.max_results)
        return f"search_query={q}&start={query.offset}&max_results={limit}&sortBy=relevance&sortOrder=descending"

    def _filter_by_year(
        self, results: list[SearchResult], year_from: int | None, year_to: int | None
    ) -> list[SearchResult]:
        if not year_from and not year_to:
            return results
        filtered = []
        for r in results:
            if r.year is None:
                filtered.append(r)  # Keep papers without year
                continue
            if year_from and r.year < year_from:
                continue
            if year_to and r.year > year_to:
                continue
            filtered.append(r)
        return filtered

    def _parse_response(self, xml_data: bytes) -> list[SearchResult]:
        root = ET.fromstring(xml_data)
        results = []

        for entry in root.findall(f"{ATOM_NS}entry"):
            title = self._get_text(entry, f"{ATOM_NS}title").replace("\n", " ").strip()
            abstract = self._get_text(entry, f"{ATOM_NS}summary").replace("\n", " ").strip()

            authors = []
            for author_elem in entry.findall(f"{ATOM_NS}author"):
                name = self._get_text(author_elem, f"{ATOM_NS}name")
                if name:
                    authors.append(name)

            entry_id = self._get_text(entry, f"{ATOM_NS}id")
            arxiv_id = self._extract_arxiv_id(entry_id)

            doi = ""
            for link in entry.findall(f"{ATOM_NS}link"):
                href = link.get("href", "")
                if "doi.org" in href:
                    doi = href.split("doi.org/")[-1]

            pdf_url = ""
            for link in entry.findall(f"{ATOM_NS}link"):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")

            published = self._get_text(entry, f"{ATOM_NS}published")
            year = self._parse_year(published)

            venue = ""
            primary_cat = entry.find("{http://arxiv.org/schemas/atom}primary_category")
            if primary_cat is not None:
                venue = primary_cat.get("term", "")

            if title:
                results.append(SearchResult(
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=abstract,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    url=entry_id,
                    pdf_url=pdf_url,
                    language="en",
                    publication_type="article",
                    source="arxiv",
                    venue=venue,
                    source_payload={"entry_id": entry_id, "primary_category": venue},
                ))

        return results

    @staticmethod
    def _get_text(elem: ET.Element, tag: str) -> str:
        child = elem.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    @staticmethod
    def _extract_arxiv_id(url: str) -> str:
        match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?$", url)
        return match.group(1) if match else ""

    @staticmethod
    def _parse_year(date_str: str) -> int | None:
        match = re.match(r"(\d{4})", date_str)
        return int(match.group(1)) if match else None
