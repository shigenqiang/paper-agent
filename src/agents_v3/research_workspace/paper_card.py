"""论文卡片生成器"""

from __future__ import annotations

import json
import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import PaperCard, PaperStatus, SourceSpan
from src.agents_v3.research_workspace.storage import get_storage


class PaperCardGenerator:
    """从论文 chunks 生成结构化卡片"""

    def __init__(self):
        self.storage = get_storage()

    def generate(self, paper_id: str) -> PaperCard | None:
        paper_data = self.storage.get_item("papers", paper_id)
        if not paper_data:
            return None

        chunks_data = self.storage.load_collection(f"chunks_{paper_id}")
        if not chunks_data:
            logger.warning(f"No chunks for paper {paper_id}")
            return None

        # Build card from chunks
        full_text = " ".join(c.get("text", "") for c in chunks_data)
        card = self._extract_card(paper_id, paper_data, chunks_data, full_text)

        # Save card
        self.storage.upsert_item("paper_cards", card.card_id, card.model_dump())

        # Update paper status
        paper_data["status"] = PaperStatus.CARD_READY.value
        self.storage.upsert_item("papers", paper_id, paper_data)

        logger.info(f"Generated card for paper {paper_id}")
        return card

    def batch_generate(
        self, project_id: str, only_missing: bool = True
    ) -> list[PaperCard]:
        papers = self.storage.query("papers", {"project_id": project_id})
        cards = []

        for p in papers:
            if only_missing and p.get("status") in (
                PaperStatus.CARD_READY.value,
                PaperStatus.EVIDENCE_READY.value,
            ):
                # Check if card already exists
                existing = self.storage.query("paper_cards", {"paper_id": p["paper_id"]})
                if existing:
                    continue

            card = self.generate(p["paper_id"])
            if card:
                cards.append(card)

        return cards

    def _extract_card(
        self,
        paper_id: str,
        paper_data: dict[str, Any],
        chunks: list[dict[str, Any]],
        full_text: str,
    ) -> PaperCard:
        # Simple extraction based on text patterns
        # In production, this would use LLM
        card_id = f"card_{uuid.uuid4().hex[:8]}"

        # Extract key findings from chunks
        key_findings = self._extract_list_from_text(full_text, ["finding", "result", "showed", "found"])
        limitations = self._extract_list_from_text(full_text, ["limitation", "weakness", "constraint"])
        future_work = self._extract_list_from_text(full_text, ["future", "next", "extend"])

        # Build source spans
        source_spans = []
        for i, chunk in enumerate(chunks[:3]):  # Top 3 chunks
            source_spans.append(SourceSpan(
                field="key_findings",
                chunk_id=chunk.get("chunk_id", f"chunk_{i}"),
                quote=chunk.get("text", "")[:200],
            ))

        return PaperCard(
            card_id=card_id,
            paper_id=paper_id,
            project_id=paper_data.get("project_id", ""),
            research_question="unknown",
            method="unknown",
            data_or_sample="unknown",
            key_findings=key_findings if key_findings else ["unknown"],
            limitations=limitations if limitations else ["unknown"],
            future_work=future_work if future_work else ["unknown"],
            topics=[],
            possible_gaps=[],
            source_spans=source_spans,
            confidence=0.5,
        )

    def _extract_list_from_text(self, text: str, keywords: list[str]) -> list[str]:
        results = []
        sentences = text.split(".")
        for sent in sentences:
            lower = sent.lower()
            if any(kw in lower for kw in keywords):
                clean = sent.strip()
                if 10 < len(clean) < 500:
                    results.append(clean)
                    if len(results) >= 3:
                        break
        return results
