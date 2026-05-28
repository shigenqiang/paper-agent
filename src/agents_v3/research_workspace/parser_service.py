"""论文解析服务"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Paper, PaperChunk, PaperStatus
from src.agents_v3.research_workspace.storage import get_storage


class ParserService:
    """PDF 解析与分块"""

    def __init__(self):
        self.storage = get_storage()

    def parse_paper(self, paper_id: str) -> dict[str, Any]:
        item = self.storage.get_item("papers", paper_id)
        if not item:
            return {"success": False, "error": "Paper not found"}

        paper = Paper(**item)
        if not paper.pdf_path:
            self._update_status(paper_id, PaperStatus.FAILED, "No PDF path")
            return {"success": False, "error": "No PDF file"}

        try:
            from pathlib import Path
            if not Path(paper.pdf_path).exists():
                self._update_status(paper_id, PaperStatus.FAILED, "PDF file missing")
                return {"success": False, "error": "PDF file not found"}

            chunks = self._extract_chunks(paper.pdf_path, paper_id)
            self._save_chunks(paper_id, chunks)
            self._update_status(paper_id, PaperStatus.PARSED)
            logger.info(f"Parsed paper {paper_id}: {len(chunks)} chunks")
            return {"success": True, "chunk_count": len(chunks)}
        except Exception as e:
            self._update_status(paper_id, PaperStatus.FAILED, str(e))
            return {"success": False, "error": str(e)}

    def parse_project_papers(
        self, project_id: str, only_unparsed: bool = True
    ) -> dict[str, Any]:
        papers = self.storage.query("papers", {"project_id": project_id})
        results = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        for p in papers:
            paper = Paper(**p)
            if only_unparsed and paper.status in (
                PaperStatus.PARSED,
                PaperStatus.CARD_READY,
                PaperStatus.EVIDENCE_READY,
            ):
                results["skipped"] += 1
                continue

            results["total"] += 1
            result = self.parse_paper(paper.paper_id)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1

        return results

    def get_chunks(self, paper_id: str) -> list[PaperChunk]:
        chunks_data = self.storage.load_collection(f"chunks_{paper_id}")
        return [PaperChunk(**c) for c in chunks_data]

    def _extract_chunks(self, pdf_path: str, paper_id: str) -> list[dict[str, Any]]:
        try:
            import pdfplumber
            chunks = []
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    full_text += text + "\n"

            # Simple chunking by paragraphs
            paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
            offset = 0
            for i, para in enumerate(paragraphs):
                chunk_id = f"chunk_{paper_id}_{i:04d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "paper_id": paper_id,
                    "section_title": "",
                    "text": para,
                    "start_char": offset,
                    "end_char": offset + len(para),
                    "token_count": len(para.split()),
                })
                offset += len(para) + 2

            return chunks
        except ImportError:
            # Fallback: return empty chunks if pdfplumber not installed
            logger.warning("pdfplumber not installed, using stub")
            return [{
                "chunk_id": f"chunk_{paper_id}_0000",
                "paper_id": paper_id,
                "section_title": "full_text",
                "text": "[PDF parsing requires pdfplumber]",
                "start_char": 0,
                "end_char": 0,
                "token_count": 0,
            }]

    def _save_chunks(self, paper_id: str, chunks: list[dict[str, Any]]) -> None:
        self.storage.save_collection(f"chunks_{paper_id}", chunks)

    def _update_status(self, paper_id: str, status: PaperStatus, error: str = "") -> None:
        item = self.storage.get_item("papers", paper_id)
        if item:
            item["status"] = status.value
            if error:
                item["error_message"] = error
            self.storage.upsert_item("papers", paper_id, item)
