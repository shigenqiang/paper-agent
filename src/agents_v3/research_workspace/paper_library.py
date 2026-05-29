"""论文库管理服务"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    Author,
    CitationInfo,
    OpenAccessInfo,
    Paper,
    PaperClassification,
    PaperDates,
    PaperIdentifiers,
    PaperSource,
    PaperStatus,
)
from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchQuery, SearchResult, SearchSession
from src.agents_v3.research_workspace.search.dedup import build_existing_keys, make_dedup_key
from src.agents_v3.research_workspace.search.ranking import RankingService
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


def search_result_to_meta(r: SearchResult) -> dict[str, Any]:
    """将 SearchResult 转换为 Paper 构造用的元数据 dict"""
    return {
        "title": r.title,
        "authors": [{"name": a} for a in r.authors],
        "dates": {"year": r.year},
        "source": {"venue": r.venue},
        "identifiers": {
            "doi": r.doi,
            "arxiv_id": r.arxiv_id,
            "pubmed_id": r.pubmed_id,
            "openalex_id": r.openalex_id,
            "semantic_scholar_id": r.semantic_scholar_id,
        },
        "abstract": r.abstract,
        "url": r.url,
        "open_access": {"pdf_url": r.pdf_url},
        "classification": {
            "concepts": r.concepts,
            "keywords": r.keywords,
        },
        "citation": {"citation_count": r.citations},
    }


class PaperLibraryService:
    """项目论文库管理"""

    def __init__(
        self,
        storage: JSONStorage | None = None,
        search_adapters: list[BaseSearchAdapter] | None = None,
    ):
        self.storage = storage or get_storage()
        self.search_adapters = search_adapters or []

    def add_uploaded_paper(
        self,
        project_id: str,
        file_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> Paper:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        paper_id = f"paper_{uuid.uuid4().hex[:8]}"
        dest_dir = self.storage.data_dir / "files" / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{paper_id}.pdf"

        import shutil
        shutil.copy2(file_path, dest_path)

        meta = metadata or {}
        authors_raw = meta.get("authors", [])
        authors = [
            Author(name=a) if isinstance(a, str) else Author(**a)
            for a in authors_raw
        ]

        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=meta.get("title", path.stem),
            abstract=meta.get("abstract", ""),
            authors=authors,
            dates=PaperDates(year=meta.get("year")),
            source=PaperSource(venue=meta.get("venue", "")),
            identifiers=PaperIdentifiers(
                doi=meta.get("doi", ""),
                arxiv_id=meta.get("arxiv_id", ""),
            ),
            source_platform="upload",
            status=PaperStatus.UPLOADED,
            pdf_path=str(dest_path),
        )
        self.storage.upsert_item("papers", paper_id, paper.model_dump())
        logger.info(f"Added paper {paper_id} to project {project_id}")
        return paper

    def add_paper_metadata(
        self,
        project_id: str,
        metadata: dict[str, Any],
        source: str = "import",
    ) -> Paper | None:
        # 去重检查
        existing = self.storage.query("papers", {"project_id": project_id})
        existing_keys = build_existing_keys(existing)
        if make_dedup_key(metadata) in existing_keys:
            logger.info(f"Duplicate skipped: {metadata.get('title', '')[:50]}")
            return None

        paper_id = f"paper_{uuid.uuid4().hex[:8]}"

        # 兼容处理：authors 可能是 list[str] 或 list[Author] 或 list[dict]
        authors_raw = metadata.get("authors", [])
        authors = []
        for a in authors_raw:
            if isinstance(a, str):
                authors.append(Author(name=a))
            elif isinstance(a, dict):
                authors.append(Author(**a))
            elif isinstance(a, Author):
                authors.append(a)
            else:
                authors.append(Author(name=str(a)))

        # 兼容处理：identifiers 可能是 dict 或 PaperIdentifiers
        ids_raw = metadata.get("identifiers")
        if isinstance(ids_raw, PaperIdentifiers):
            identifiers = ids_raw
        elif isinstance(ids_raw, dict):
            identifiers = PaperIdentifiers(**ids_raw)
        else:
            identifiers = PaperIdentifiers(
                doi=metadata.get("doi", ""),
                arxiv_id=metadata.get("arxiv_id", ""),
                pubmed_id=metadata.get("pubmed_id", ""),
                openalex_id=metadata.get("openalex_id", ""),
                semantic_scholar_id=metadata.get("semantic_scholar_id", ""),
            )

        # 兼容处理：dates
        dates_raw = metadata.get("dates")
        if isinstance(dates_raw, PaperDates):
            dates = dates_raw
        elif isinstance(dates_raw, dict):
            dates = PaperDates(**dates_raw)
        else:
            dates = PaperDates(year=metadata.get("year"))

        # 兼容处理：source
        source_raw = metadata.get("source_info") or metadata.get("source")
        if isinstance(source_raw, PaperSource):
            paper_source = source_raw
        elif isinstance(source_raw, dict):
            paper_source = PaperSource(**source_raw)
        else:
            paper_source = PaperSource(venue=metadata.get("venue", ""))

        # 兼容处理：open_access
        oa_raw = metadata.get("open_access")
        if isinstance(oa_raw, OpenAccessInfo):
            oa = oa_raw
        elif isinstance(oa_raw, dict):
            oa = OpenAccessInfo(**oa_raw)
        else:
            oa = OpenAccessInfo(pdf_url=metadata.get("pdf_url", ""))

        # 兼容处理：classification
        cls_raw = metadata.get("classification")
        if isinstance(cls_raw, PaperClassification):
            classification = cls_raw
        elif isinstance(cls_raw, dict):
            classification = PaperClassification(**cls_raw)
        else:
            classification = PaperClassification(
                concepts=metadata.get("concepts", []),
                keywords=metadata.get("keywords", []),
            )

        # 兼容处理：citation
        cit_raw = metadata.get("citation")
        if isinstance(cit_raw, CitationInfo):
            citation = cit_raw
        elif isinstance(cit_raw, dict):
            citation = CitationInfo(**cit_raw)
        else:
            citation = CitationInfo(citation_count=metadata.get("citations"))

        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=metadata.get("title", ""),
            abstract=metadata.get("abstract", ""),
            authors=authors,
            identifiers=identifiers,
            dates=dates,
            source=paper_source,
            open_access=oa,
            classification=classification,
            citation=citation,
            url=metadata.get("url", ""),
            source_platform=source if isinstance(source, str) else "",
            status=PaperStatus.IMPORTED,
        )
        self.storage.upsert_item("papers", paper_id, paper.model_dump())
        logger.info(f"Imported paper {paper_id}: {paper.title}")
        return paper

    def add_search_results(
        self,
        project_id: str,
        results: list[dict[str, Any]],
    ) -> list[Paper]:
        papers = []
        for r in results:
            paper = self.add_paper_metadata(project_id, r, source="search")
            if paper:
                papers.append(paper)
        return papers

    def search_papers(
        self,
        query: SearchQuery,
    ) -> list[SearchResult]:
        """调用已注册的搜索适配器，返回结果（不去重，不入库）"""
        all_results: list[SearchResult] = []
        for adapter in self.search_adapters:
            try:
                results = adapter.search(query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Search adapter {adapter.source_name} failed: {e}")
        return all_results

    # ── 搜索缓存 ──────────────────────────────────────

    @staticmethod
    def _make_cache_key(query: SearchQuery) -> str:
        """根据查询参数生成缓存 key"""
        parts = [
            query.query.strip().lower(),
            ",".join(sorted(query.sources)),
            str(query.year_from or ""),
            str(query.year_to or ""),
            str(query.limit),
        ]
        raw = "|".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> list[SearchResult] | None:
        """查找缓存的搜索结果"""
        items = self.storage.load_collection("search_cache")
        for item in items:
            if item.get("cache_key") == cache_key:
                results = [SearchResult(**r) for r in item.get("results", [])]
                logger.info(f"Search cache hit: {cache_key} ({len(results)} results)")
                return results
        return None

    def _store_cache(self, cache_key: str, query: SearchQuery, results: list[SearchResult]) -> None:
        """存储搜索结果到缓存"""
        items = self.storage.load_collection("search_cache")
        # 移除旧缓存
        items = [i for i in items if i.get("cache_key") != cache_key]
        items.append({
            "cache_key": cache_key,
            "query": query.model_dump(),
            "results": [r.model_dump(exclude_defaults=True) for r in results],
            "cached_at": datetime.now().isoformat(),
            "result_count": len(results),
        })
        # 只保留最近 50 条缓存
        if len(items) > 50:
            items = items[-50:]
        self.storage.save_collection("search_cache", items)
        logger.info(f"Cached search results: {cache_key} ({len(results)} results)")

    def search_and_import(
        self,
        project_id: str,
        query: SearchQuery,
    ) -> list[Paper]:
        """搜索并导入到项目（自动去重）"""
        results = self.search_papers(query)
        papers = []
        for r in results:
            meta = search_result_to_meta(r)
            paper = self.add_paper_metadata(project_id, meta, source=r.source)
            if paper:
                papers.append(paper)
        return papers

    def list_papers(
        self,
        project_id: str,
        filters: dict[str, Any] | None = None,
    ) -> list[Paper]:
        query = {"project_id": project_id}
        if filters:
            query.update(filters)
        items = self.storage.query("papers", query)
        return [Paper(**i) for i in items]

    def get_paper(self, paper_id: str) -> Paper | None:
        item = self.storage.get_item("papers", paper_id)
        if item:
            return Paper(**item)
        return None

    def update_paper(self, paper_id: str, **updates: Any) -> Paper | None:
        item = self.storage.get_item("papers", paper_id)
        if not item:
            return None
        item.update(updates)
        item["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("papers", paper_id, item)
        return Paper(**item)

    def mark_included(self, paper_id: str) -> Paper | None:
        return self.update_paper(paper_id, included=True, exclude_reason="")

    def mark_excluded(self, paper_id: str, reason: str) -> Paper | None:
        return self.update_paper(paper_id, included=False, exclude_reason=reason)

    def import_doi_list(
        self,
        project_id: str,
        doi_list: list[str],
    ) -> list[Paper]:
        papers = []
        for doi in doi_list:
            paper = self.add_paper_metadata(
                project_id,
                {"title": f"DOI: {doi}", "identifiers": PaperIdentifiers(doi=doi)},
                source="doi",
            )
            if paper:
                papers.append(paper)
        return papers

    def import_bibtex(
        self,
        project_id: str,
        bibtex_text: str,
    ) -> list[Paper]:
        papers = []
        entries = self._parse_bibtex(bibtex_text)
        for entry in entries:
            paper = self.add_paper_metadata(project_id, entry, source="bibtex")
            if paper:
                papers.append(paper)
        return papers

    def _parse_bibtex(self, text: str) -> list[dict[str, Any]]:
        entries = []
        parts = text.split("@")
        for part in parts[1:]:
            match = re.match(r'\w+\{([^,]+),', part)
            if not match:
                continue
            key = match.group(1).strip()
            entry: dict[str, Any] = {"key": key}
            for field_match in re.finditer(r'(\w+)\s*=\s*\{([^}]*)\}', part):
                field_name = field_match.group(1).lower()
                field_value = field_match.group(2).strip()
                if field_name == "author":
                    entry["authors"] = [a.strip() for a in field_value.split(" and ")]
                elif field_name == "year":
                    try:
                        entry["year"] = int(field_value)
                    except ValueError:
                        pass
                elif field_name == "title":
                    entry["title"] = field_value
                elif field_name == "journal":
                    entry["venue"] = field_value
                elif field_name == "doi":
                    entry["doi"] = field_value
            entries.append(entry)
        return entries

    # ── 搜索暂存与提交 ──────────────────────────────

    def search_candidates(
        self,
        project_id: str,
        query: SearchQuery,
    ) -> SearchSession:
        """搜索并暂存结果（不入库），返回 SearchSession。支持缓存。"""
        cache_key = self._make_cache_key(query)

        # 尝试缓存
        if query.use_cache and not query.force_refresh:
            cached = self._check_cache(cache_key)
            if cached is not None:
                session = SearchSession(
                    project_id=project_id,
                    query=query.model_dump(),
                    results=cached,
                    status="pending",
                )
                storage = self.storage
                session_data = session.model_dump()
                session_data["results"] = [r.model_dump(exclude_defaults=True) for r in session.results]
                storage.upsert_item("search_sessions", session.session_id, session_data)
                logger.info(f"Created search session {session.session_id} from cache: {len(cached)} results")
                return session

        # 缓存未命中，调用 API
        results = self.search_papers(query)
        ranking = RankingService(query=query.query)
        results = ranking.rank(results, query=query.query)

        # 存入缓存
        self._store_cache(cache_key, query, results)
        session = SearchSession(
            project_id=project_id,
            query=query.model_dump(),
            results=results,
            status="pending",
        )
        storage = self.storage
        session_data = session.model_dump()
        session_data["results"] = [r.model_dump(exclude_defaults=True) for r in session.results]
        storage.upsert_item("search_sessions", session.session_id, session_data)
        logger.info(f"Created search session {session.session_id}: {len(results)} results")
        return session

    def get_search_session(self, session_id: str) -> SearchSession | None:
        item = self.storage.get_item("search_sessions", session_id)
        if item:
            return SearchSession(**item)
        return None

    def list_search_sessions(self, project_id: str) -> list[SearchSession]:
        items = self.storage.query("search_sessions", {"project_id": project_id})
        return [SearchSession(**i) for i in items]

    def commit_search_results(
        self,
        project_id: str,
        session_id: str,
        result_ids: list[str],
    ) -> list[Paper]:
        """将选中的搜索结果提交入库"""
        session = self.get_search_session(session_id)
        if not session:
            logger.error(f"Search session not found: {session_id}")
            return []

        results_by_id = {r.result_id: r for r in session.results}
        papers = []
        for rid in result_ids:
            r = results_by_id.get(rid)
            if not r:
                continue
            meta = search_result_to_meta(r)
            paper = self.add_paper_metadata(project_id, meta, source=r.source)
            if paper:
                papers.append(paper)

        # Update session
        session.selected_result_ids = result_ids
        session.status = "committed"
        self.storage.upsert_item("search_sessions", session_id, session.model_dump())

        logger.info(f"Committed {len(papers)} papers from session {session_id}")
        return papers
