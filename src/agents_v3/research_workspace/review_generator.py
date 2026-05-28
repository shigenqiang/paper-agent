"""文献综述生成器"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    Report,
    ReportType,
    RetrievalScope,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import get_storage


class LiteratureReviewGenerator:
    """基于 Scope 生成文献综述"""

    def __init__(self):
        self.storage = get_storage()
        self.scope_service = RetrievalScopeService()

    def generate(
        self,
        project_id: str,
        scope_payload: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> Report:
        opts = options or {}
        scope = self.scope_service.resolve(project_id, scope_payload)
        materials = self.collect_materials(scope)
        outline = self.build_outline(materials)
        content = self.generate_sections(outline, materials, opts)
        content = self.attach_citations(content, materials)

        report = Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.LITERATURE_REVIEW,
            title=f"文献综述 - {scope.summary}",
            content=content,
            scope=scope.model_dump(),
            paper_ids=scope.paper_ids,
            evidence_ids=scope.evidence_ids,
        )

        self.storage.upsert_item("reports", report.report_id, report.model_dump())
        logger.info(f"Generated literature review: {report.report_id}")
        return report

    def collect_materials(self, scope: RetrievalScope) -> dict[str, Any]:
        evidence = self.scope_service.to_evidence_records(scope)
        paper_cards = []
        for pid in scope.paper_ids:
            cards = self.storage.query("paper_cards", {"paper_id": pid})
            paper_cards.extend(cards)

        return {
            "scope_summary": scope.summary,
            "paper_count": len(scope.paper_ids),
            "evidence_records": evidence,
            "paper_cards": paper_cards,
        }

    def build_outline(self, materials: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"section": "研究背景", "key": "background"},
            {"section": "主题划分", "key": "topics"},
            {"section": "代表性文献", "key": "representative"},
            {"section": "主要研究方法", "key": "methods"},
            {"section": "主要发现", "key": "findings"},
            {"section": "研究不足", "key": "limitations"},
            {"section": "未来趋势", "key": "future"},
            {"section": "参考文献", "key": "references"},
        ]

    def generate_sections(
        self,
        outline: list[dict[str, str]],
        materials: dict[str, Any],
        options: dict[str, Any],
    ) -> str:
        parts = []
        evidence = materials.get("evidence_records", [])
        cards = materials.get("paper_cards", [])

        parts.append(f"# 文献综述\n")
        parts.append(f"**生成范围**: {materials['scope_summary']}\n")
        parts.append(f"**使用论文数量**: {materials['paper_count']}\n")

        for item in outline:
            section = item["section"]
            key = item["key"]
            parts.append(f"\n## {section}\n")

            if key == "background":
                parts.append("本综述基于选定范围内的论文进行分析。\n")
            elif key == "topics":
                topics = self._extract_topics(evidence)
                for t in topics:
                    parts.append(f"- {t}\n")
            elif key == "methods":
                methods = self._extract_methods(evidence)
                for m in methods:
                    parts.append(f"- {m}\n")
            elif key == "findings":
                findings = self._extract_findings(evidence)
                for f in findings:
                    parts.append(f"- {f}\n")
            elif key == "limitations":
                limits = self._extract_limitations(evidence)
                for l in limits:
                    parts.append(f"- {l}\n")
            elif key == "future":
                futures = self._extract_future_work(evidence)
                for f in futures:
                    parts.append(f"- {f}\n")
            elif key == "references":
                for pid in materials.get("paper_ids", []):
                    card = next((c for c in cards if c.get("paper_id") == pid), None)
                    if card:
                        parts.append(f"- [{pid}] {card.get('title', 'N/A')}\n")

        return "".join(parts)

    def attach_citations(self, text: str, materials: dict[str, Any]) -> str:
        return text

    def validate_review(self, report: Report) -> dict[str, Any]:
        issues = []
        if not report.scope:
            issues.append("缺少 scope_summary")
        if not report.paper_ids:
            issues.append("缺少 paper_ids")
        if not report.evidence_ids:
            issues.append("缺少 evidence_ids")
        return {"valid": len(issues) == 0, "issues": issues}

    def _extract_topics(self, evidence: list[EvidenceRecord]) -> list[str]:
        topics = set()
        for e in evidence:
            if e.topic:
                topics.add(e.topic)
        return list(topics)[:10]

    def _extract_methods(self, evidence: list[EvidenceRecord]) -> list[str]:
        methods = set()
        for e in evidence:
            if e.method and e.method != "unknown":
                methods.add(e.method)
        return list(methods)[:10]

    def _extract_findings(self, evidence: list[EvidenceRecord]) -> list[str]:
        findings = []
        for e in evidence:
            if e.finding and e.finding != "unknown":
                findings.append(e.finding)
        return list(dict.fromkeys(findings))[:10]

    def _extract_limitations(self, evidence: list[EvidenceRecord]) -> list[str]:
        limits = []
        for e in evidence:
            if e.limitation and e.limitation != "unknown":
                limits.append(e.limitation)
        return list(dict.fromkeys(limits))[:10]

    def _extract_future_work(self, evidence: list[EvidenceRecord]) -> list[str]:
        futures = []
        for e in evidence:
            if e.future_work and e.future_work != "unknown":
                futures.append(e.future_work)
        return list(dict.fromkeys(futures))[:10]
