"""论文库管理服务"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Paper, PaperStatus
from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchQuery, SearchResult, SearchSession
from src.agents_v3.research_workspace.search.dedup import build_existing_keys, make_dedup_key
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


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
        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=meta.get("title", path.stem),
            authors=meta.get("authors", []),
            year=meta.get("year"),
            venue=meta.get("venue", ""),
            doi=meta.get("doi", ""),
            abstract=meta.get("abstract", ""),
            source="upload",
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
        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=metadata.get("title", ""),
            authors=metadata.get("authors", []),
            year=metadata.get("year"),
            venue=metadata.get("venue", ""),
            doi=metadata.get("doi", ""),
            arxiv_id=metadata.get("arxiv_id", ""),
            abstract=metadata.get("abstract", ""),
            url=metadata.get("url", ""),
            pdf_url=metadata.get("pdf_url", ""),
            source=source,
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

    def search_and_import(
        self,
        project_id: str,
        query: SearchQuery,
    ) -> list[Paper]:
        """搜索并导入到项目（自动去重）"""
        results = self.search_papers(query)
        papers = []
        for r in results:
            meta = {
                "title": r.title,
                "authors": r.authors,
                "year": r.year,
                "venue": r.venue,
                "doi": r.doi,
                "arxiv_id": r.arxiv_id,
                "abstract": r.abstract,
                "url": r.url,
                "pdf_url": r.pdf_url,
            }
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
                {"doi": doi, "title": f"DOI: {doi}"},
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
        """搜索并暂存结果（不入库），返回 SearchSession"""
        results = self.search_papers(query)
        session = SearchSession(
            project_id=project_id,
            query=query.model_dump(),
            results=results,
            status="pending",
        )
        storage = self.storage
        storage.upsert_item("search_sessions", session.session_id, session.model_dump())
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
            meta = {
                "title": r.title,
                "authors": r.authors,
                "year": r.year,
                "venue": r.venue,
                "doi": r.doi,
                "arxiv_id": r.arxiv_id,
                "abstract": r.abstract,
                "url": r.url,
                "pdf_url": r.pdf_url,
            }
            paper = self.add_paper_metadata(project_id, meta, source=r.source)
            if paper:
                papers.append(paper)

        # Update session
        session.selected_result_ids = result_ids
        session.status = "committed"
        self.storage.upsert_item("search_sessions", session_id, session.model_dump())

        logger.info(f"Committed {len(papers)} papers from session {session_id}")
        return papers
