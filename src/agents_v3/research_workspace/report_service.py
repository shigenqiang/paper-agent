"""报告管理服务"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import Report, ReportVersion
from src.agents_v3.research_workspace.storage import get_storage


class ReportService:
    """报告 CRUD 和版本管理"""

    def __init__(self):
        self.storage = get_storage()

    def save_report(self, report: Report) -> Report:
        self.storage.upsert_item("reports", report.report_id, report.model_dump())
        logger.info(f"Saved report: {report.report_id}")
        return report

    def list_reports(
        self, project_id: str, report_type: str | None = None
    ) -> list[Report]:
        query: dict[str, Any] = {"project_id": project_id}
        if report_type:
            query["type"] = report_type
        items = self.storage.query("reports", query)
        return [Report(**i) for i in items]

    def get_report(self, report_id: str) -> Report | None:
        item = self.storage.get_item("reports", report_id)
        if item:
            return Report(**item)
        return None

    def create_version(
        self, report_id: str, content: str, reason: str
    ) -> ReportVersion | None:
        report = self.get_report(report_id)
        if not report:
            return None

        version = ReportVersion(
            version_id=f"ver_{uuid.uuid4().hex[:8]}",
            report_id=report_id,
            content=content,
            reason=reason,
        )

        # Save version
        self.storage.upsert_item(
            "report_versions", version.version_id, version.model_dump()
        )

        # Update report
        report.content = content
        report.version += 1
        report.updated_at = datetime.now().isoformat()
        self.storage.upsert_item("reports", report_id, report.model_dump())

        logger.info(f"Created version for report {report_id}")
        return version

    def export_markdown(self, report_id: str) -> str:
        report = self.get_report(report_id)
        if not report:
            return ""

        parts = [report.content]
        parts.append(f"\n\n---\n")
        parts.append(f"**报告ID**: {report.report_id}\n")
        parts.append(f"**项目**: {report.project_id}\n")
        parts.append(f"**类型**: {report.type.value}\n")
        parts.append(f"**版本**: {report.version}\n")
        parts.append(f"**论文数**: {len(report.paper_ids)}\n")
        parts.append(f"**证据数**: {len(report.evidence_ids)}\n")
        parts.append(f"**生成时间**: {report.created_at}\n")

        return "".join(parts)
