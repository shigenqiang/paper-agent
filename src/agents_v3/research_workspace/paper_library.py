"""论文库管理服务"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Paper, PaperStatus
from src.agents_v3.research_workspace.storage import get_storage


class PaperLibraryService:
    """项目论文库管理"""

    def __init__(self):
        self.storage = get_storage()

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
    ) -> Paper:
        paper_id = f"paper_{uuid.uuid4().hex[:8]}"
        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=metadata.get("title", ""),
            authors=metadata.get("authors", []),
            year=metadata.get("year"),
            venue=metadata.get("venue", ""),
            doi=metadata.get("doi", ""),
            abstract=metadata.get("abstract", ""),
            url=metadata.get("url", ""),
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
            papers.append(paper)
        return papers

    def _parse_bibtex(self, text: str) -> list[dict[str, Any]]:
        entries = []
        # Split by @ to find entries
        parts = text.split("@")
        for part in parts[1:]:  # Skip first empty part
            # Find entry type and key
            match = re.match(r'\w+\{([^,]+),', part)
            if not match:
                continue
            key = match.group(1).strip()
            entry: dict[str, Any] = {"key": key}
            # Find all fields
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
