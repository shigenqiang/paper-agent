"""证据表服务"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    PaperCard,
    PaperStatus,
    RetrievalScope,
)
from src.agents_v3.research_workspace.storage import get_storage


class EvidenceTableService:
    """从论文卡片生成证据记录"""

    def __init__(self, storage=None):
        self.storage = storage or get_storage()

    def _get_project_paper_ids(self, project_id: str) -> list[str]:
        """获取项目下所有 paper_id"""
        papers = self.storage.query("papers", {"project_id": project_id})
        return [p.get("paper_id", "") for p in papers]

    def build_for_project(self, project_id: str) -> list[EvidenceRecord]:
        paper_ids = self._get_project_paper_ids(project_id)
        cards = self.storage.query("paper_cards", {"paper_id": paper_ids}) if paper_ids else []
        evidence_records = []

        for card_data in cards:
            card = PaperCard(**card_data)
            records = self._card_to_evidence(card)
            evidence_records.extend(records)

        # Save all evidence
        for record in evidence_records:
            self.storage.upsert_item(
                "evidence_records", record.evidence_id, record.model_dump()
            )

        logger.info(f"Built {len(evidence_records)} evidence records for project {project_id}")
        return evidence_records

    def build_for_paper(self, paper_id: str) -> list[EvidenceRecord]:
        cards = self.storage.query("paper_cards", {"paper_id": paper_id})
        if not cards:
            return []

        card = PaperCard(**cards[0])
        records = self._card_to_evidence(card)

        for record in records:
            self.storage.upsert_item(
                "evidence_records", record.evidence_id, record.model_dump()
            )

        return records

    def query(
        self, project_id: str, filters: dict[str, Any] | None = None
    ) -> list[EvidenceRecord]:
        paper_ids = self._get_project_paper_ids(project_id)
        if not paper_ids:
            return []
        query: dict[str, Any] = {"paper_id": paper_ids}
        if filters:
            query.update(filters)
        items = self.storage.query("evidence_records", query)
        return [EvidenceRecord(**i) for i in items]

    def query_by_scope(self, scope: RetrievalScope) -> list[EvidenceRecord]:
        paper_ids = self._get_project_paper_ids(scope.project_id)
        all_evidence = self.storage.query("evidence_records", {"paper_id": paper_ids}) if paper_ids else []
        records = [EvidenceRecord(**e) for e in all_evidence]

        if scope.paper_ids:
            records = [r for r in records if r.paper_id in scope.paper_ids]

        if scope.topic_ids:
            records = [r for r in records if r.topic in scope.topic_ids]

        if scope.method_ids:
            records = [r for r in records if r.method in scope.method_ids]

        return records

    def _card_to_evidence(self, card: PaperCard) -> list[EvidenceRecord]:
        records = []

        # Create evidence from key findings
        for i, finding in enumerate(card.key_findings):
            if finding == "unknown":
                continue
            record = EvidenceRecord(
                evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                paper_id=card.paper_id,
                topic=", ".join(card.topics) if card.topics else "",
                research_question=card.research_question,
                method=card.method,
                data_or_sample=card.data_or_sample,
                finding=finding,
                source_chunk_id=card.source_spans[i].chunk_id if i < len(card.source_spans) else "",
                source_quote=card.source_spans[i].quote if i < len(card.source_spans) else "",
            )
            records.append(record)

        # Create evidence from limitations
        for limitation in card.limitations:
            if limitation == "unknown":
                continue
            record = EvidenceRecord(
                evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                paper_id=card.paper_id,
                topic=", ".join(card.topics) if card.topics else "",
                method=card.method,
                limitation=limitation,
            )
            records.append(record)

        # If no evidence created, create a summary record
        if not records:
            record = EvidenceRecord(
                evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                paper_id=card.paper_id,
                topic=", ".join(card.topics) if card.topics else "",
                research_question=card.research_question,
                method=card.method,
                finding="No specific findings extracted",
                evidence_strength="low",
            )
            records.append(record)

        return records


def normalize_topics(cards: list[PaperCard]) -> dict[str, list[str]]:
    """规范化主题：合并近似主题"""
    topic_map: dict[str, list[str]] = {}

    for card in cards:
        for topic in card.topics:
            normalized = topic.lower().strip()
            # Simple normalization rules
            aliases = {
                "llm feedback": "feedback mechanism",
                "ai feedback": "feedback mechanism",
                "automatic feedback": "feedback mechanism",
            }
            normalized = aliases.get(normalized, normalized)

            if normalized not in topic_map:
                topic_map[normalized] = []
            if card.paper_id not in topic_map[normalized]:
                topic_map[normalized].append(card.paper_id)

    return topic_map
