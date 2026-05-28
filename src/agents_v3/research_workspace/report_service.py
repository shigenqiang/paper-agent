"""报告管理服务 - 增强版"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Report, ReportVersion
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


class ReportService:
    """报告 CRUD、版本管理、来源索引、校验和导出"""

    def __init__(self, storage: JSONStorage | None = None):
        self.storage = storage or get_storage()

    # ── 保存与查询 ──────────────────────────────

    def save_report(self, report: Report) -> Report:
        """保存报告（自动设置 section_sources 和 validation_result）"""
        if not report.section_sources and report.scope.get("section_sources"):
            report.section_sources = report.scope["section_sources"]
        if not report.validation_result and report.scope.get("validation_result"):
            report.validation_result = report.scope["validation_result"]

        report.updated_at = datetime.now().isoformat()
        self.storage.upsert_item("reports", report.report_id, report.model_dump())
        logger.info(f"Saved report: {report.report_id} (v{report.version}, status={report.status})")
        return report

    def list_reports(
        self, project_id: str, report_type: str | None = None,
        status: str | None = None,
    ) -> list[Report]:
        query: dict[str, Any] = {"project_id": project_id}
        if report_type:
            query["type"] = report_type
        items = self.storage.query("reports", query)
        reports = [Report(**i) for i in items]
        if status:
            reports = [r for r in reports if r.status == status]
        return reports

    def get_report(self, report_id: str) -> Report | None:
        item = self.storage.get_item("reports", report_id)
        if item:
            return Report(**item)
        return None

    def update_report_status(self, report_id: str, status: str) -> Report | None:
        report = self.get_report(report_id)
        if not report:
            return None
        report.status = status
        report.updated_at = datetime.now().isoformat()
        self.storage.upsert_item("reports", report_id, report.model_dump())
        logger.info(f"Report {report_id} status -> {status}")
        return report

    def archive_report(self, report_id: str) -> Report | None:
        return self.update_report_status(report_id, "archived")

    def delete_report(self, report_id: str) -> bool:
        report = self.get_report(report_id)
        if not report:
            return False
        # Delete versions
        versions = self.storage.query("report_versions", {"report_id": report_id})
        for v in versions:
            self.storage.delete_item("report_versions", v["version_id"])
        # Delete report
        self.storage.delete_item("reports", report_id)
        logger.info(f"Deleted report {report_id} and {len(versions)} versions")
        return True

    # ── 版本管理 ──────────────────────────────────

    def create_version(
        self, report_id: str, content: str, reason: str
    ) -> ReportVersion | None:
        report = self.get_report(report_id)
        if not report:
            return None

        version = ReportVersion(
            version_id=f"ver_{uuid.uuid4().hex[:8]}",
            report_id=report_id,
            version_number=report.version,
            content=content,
            reason=reason,
            scope_snapshot=report.scope,
            source_snapshot={
                "paper_ids": report.paper_ids,
                "evidence_ids": report.evidence_ids,
                "graph_node_ids": report.graph_node_ids,
                "section_sources": report.section_sources,
            },
            paper_ids=report.paper_ids,
            evidence_ids=report.evidence_ids,
            validation_result=report.validation_result,
        )

        self.storage.upsert_item(
            "report_versions", version.version_id, version.model_dump()
        )

        report.content = content
        report.version += 1
        report.updated_at = datetime.now().isoformat()
        self.storage.upsert_item("reports", report_id, report.model_dump())

        logger.info(f"Created version {version.version_number} for report {report_id}")
        return version

    def list_versions(self, report_id: str) -> list[ReportVersion]:
        items = self.storage.query("report_versions", {"report_id": report_id})
        return sorted(
            [ReportVersion(**i) for i in items],
            key=lambda v: v.version_number,
        )

    def get_version(self, version_id: str) -> ReportVersion | None:
        item = self.storage.get_item("report_versions", version_id)
        if item:
            return ReportVersion(**item)
        return None

    def restore_version(self, report_id: str, version_id: str) -> Report | None:
        version = self.get_version(version_id)
        if not version or version.report_id != report_id:
            return None
        report = self.get_report(report_id)
        if not report:
            return None

        # Save current as version first
        self.create_version(report_id, report.content, "auto-save before restore")

        # Restore
        report.content = version.content
        report.paper_ids = version.paper_ids
        report.evidence_ids = version.evidence_ids
        report.section_sources = version.source_snapshot.get("section_sources", {})
        report.updated_at = datetime.now().isoformat()
        self.storage.upsert_item("reports", report_id, report.model_dump())

        logger.info(f"Restored report {report_id} to version {version.version_number}")
        return report

    # ── 来源索引 ──────────────────────────────────

    def build_source_index(self, report_id: str) -> dict[str, Any]:
        """构建报告来源索引"""
        report = self.get_report(report_id)
        if not report:
            return {}

        # Paper sources
        paper_sources = []
        for pid in report.paper_ids:
            p = self.storage.get_item("papers", pid)
            if p:
                # Find which sections use this paper
                used_in = []
                for sid, sdata in report.section_sources.items():
                    if pid in sdata.get("paper_ids", []):
                        used_in.append(sid)
                paper_sources.append({
                    "paper_id": pid,
                    "title": p.get("title", ""),
                    "authors": p.get("authors", []),
                    "year": p.get("year"),
                    "venue": p.get("venue", ""),
                    "doi": p.get("doi", ""),
                    "url": p.get("url", ""),
                    "citation_key": pid,
                    "used_in_sections": used_in,
                })

        # Evidence sources
        evidence_sources = []
        for eid in report.evidence_ids:
            e = self.storage.get_item("evidence_records", eid)
            if e:
                used_in = []
                for sid, sdata in report.section_sources.items():
                    if eid in sdata.get("evidence_ids", []):
                        used_in.append(sid)
                evidence_sources.append({
                    "evidence_id": eid,
                    "paper_id": e.get("paper_id", ""),
                    "topic": e.get("topic", ""),
                    "finding": e.get("finding", "")[:100] if e.get("finding") else "",
                    "limitation": e.get("limitation", "")[:100] if e.get("limitation") else "",
                    "source_quote": (e.get("source_quote") or "")[:200],
                    "used_in_sections": used_in,
                })

        return {
            "report_id": report_id,
            "project_id": report.project_id,
            "paper_sources": paper_sources,
            "evidence_sources": evidence_sources,
            "section_sources": report.section_sources,
            "created_at": datetime.now().isoformat(),
        }

    # ── 校验 ──────────────────────────────────────

    def validate_report_traceability(self, report_id: str) -> dict[str, Any]:
        """校验报告来源可追溯性"""
        report = self.get_report(report_id)
        if not report:
            return {"valid": False, "error": "report_not_found"}

        issues = []
        warnings = []

        # Check paper_ids exist
        missing_papers = []
        for pid in report.paper_ids:
            if not self.storage.get_item("papers", pid):
                missing_papers.append(pid)
        if missing_papers:
            issues.append({"code": "missing_paper", "severity": "error", "ids": missing_papers})

        # Check evidence_ids exist
        missing_evidence = []
        for eid in report.evidence_ids:
            if not self.storage.get_item("evidence_records", eid):
                missing_evidence.append(eid)
        if missing_evidence:
            issues.append({"code": "missing_evidence", "severity": "error", "ids": missing_evidence})

        # Scope violation check
        scope_papers = set(report.scope.get("paper_ids", []))
        scope_evidence = set(report.scope.get("evidence_ids", []))
        scope_violations = []
        if scope_papers:
            for pid in report.paper_ids:
                if pid not in scope_papers:
                    scope_violations.append({"type": "paper_out_of_scope", "id": pid})
        if scope_evidence:
            for eid in report.evidence_ids:
                if eid not in scope_evidence:
                    scope_violations.append({"type": "evidence_out_of_scope", "id": eid})

        # Section source coverage
        sections = report.section_sources
        if sections:
            sections_with_evidence = sum(1 for s in sections.values() if s.get("evidence_ids"))
            section_coverage = sections_with_evidence / len(sections) if sections else 0
        else:
            section_coverage = 0
            warnings.append({"code": "missing_section_sources", "message": "Report has no section_sources"})

        # Source coverage: what % of paper_ids appear in section_sources
        all_section_papers = set()
        for sdata in sections.values():
            all_section_papers.update(sdata.get("paper_ids", []))
        source_coverage = len(all_section_papers & set(report.paper_ids)) / len(report.paper_ids) if report.paper_ids else 0

        return {
            "valid": len(issues) == 0 and len(scope_violations) == 0,
            "report_id": report_id,
            "issues": issues,
            "warnings": warnings,
            "missing_paper_ids": missing_papers,
            "missing_evidence_ids": missing_evidence,
            "scope_violations": scope_violations,
            "source_coverage": source_coverage,
            "section_source_coverage": section_coverage,
            "checked_at": datetime.now().isoformat(),
        }

    # ── 导出 ──────────────────────────────────────

    def export_markdown(
        self, report_id: str,
        include_source_index: bool = True,
        include_validation: bool = False,
    ) -> str:
        report = self.get_report(report_id)
        if not report:
            return ""

        parts = []

        # Front matter
        parts.append(report.content)

        # Source index
        if include_source_index:
            source_index = self.build_source_index(report_id)
            if source_index.get("paper_sources"):
                parts.append("\n\n## 来源索引\n")
                parts.append("### 使用论文\n")
                for p in source_index["paper_sources"]:
                    authors = ", ".join(p.get("authors", [])[:3])
                    year = p.get("year", "")
                    title = p.get("title", "N/A")
                    doi = p.get("doi", "")
                    ref = f"- [{p['paper_id']}] {authors} ({year}). {title}."
                    if doi:
                        ref += f" DOI: {doi}"
                    parts.append(ref)

                if source_index.get("evidence_sources"):
                    parts.append("\n### 使用证据\n")
                    for e in source_index["evidence_sources"]:
                        line = f"- [{e['evidence_id']}] 论文 {e['paper_id']}"
                        if e.get("finding"):
                            line += f" | 发现: {e['finding'][:60]}"
                        if e.get("source_quote"):
                            line += f" | 引用: {e['source_quote'][:60]}"
                        parts.append(line)

        # Metadata footer
        parts.append(f"\n\n---\n")
        parts.append(f"**报告ID**: {report.report_id}")
        parts.append(f"**项目**: {report.project_id}")
        parts.append(f"**类型**: {report.type.value}")
        parts.append(f"**状态**: {report.status}")
        parts.append(f"**版本**: {report.version}")
        parts.append(f"**论文数**: {len(report.paper_ids)}")
        parts.append(f"**证据数**: {len(report.evidence_ids)}")
        parts.append(f"**生成时间**: {report.created_at}")

        # Validation
        if include_validation and report.validation_result:
            vr = report.validation_result
            parts.append(f"\n**质量校验**: {'通过' if vr.get('valid', True) else '未通过'}")
            if vr.get("source_coverage") is not None:
                parts.append(f"**来源覆盖率**: {vr['source_coverage']:.0%}")

        result = "\n".join(parts)

        # Track export
        if "markdown" not in report.exported_formats:
            report.exported_formats.append("markdown")
            self.storage.upsert_item("reports", report_id, report.model_dump())

        return result

    def export_json(self, report_id: str) -> str:
        """导出完整报告 JSON"""
        report = self.get_report(report_id)
        if not report:
            return "{}"

        source_index = self.build_source_index(report_id)

        export_data = {
            "report_id": report.report_id,
            "project_id": report.project_id,
            "type": report.type.value,
            "title": report.title,
            "status": report.status,
            "version": report.version,
            "content": report.content,
            "scope": report.scope,
            "paper_ids": report.paper_ids,
            "evidence_ids": report.evidence_ids,
            "graph_node_ids": report.graph_node_ids,
            "section_sources": report.section_sources,
            "validation_result": report.validation_result,
            "source_index": source_index,
            "metadata": report.metadata,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
        }

        if "json" not in report.exported_formats:
            report.exported_formats.append("json")
            self.storage.upsert_item("reports", report_id, report.model_dump())

        return json.dumps(export_data, ensure_ascii=False, indent=2)
