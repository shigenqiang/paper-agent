"""文献综述生成器 - LLM 驱动"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm_service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    Report,
    ReportType,
    RetrievalScope,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import get_storage

REVIEW_SYSTEM_PROMPT = """你是一个学术文献综述写作专家。请根据提供的论文证据，生成结构化的文献综述。

要求：
1. 综述必须基于提供的证据，不要编造
2. 按主题组织内容，展示研究脉络
3. 指出研究不足和未来趋势
4. 保持学术严谨性
5. 使用中文撰写

输出格式（JSON）：
{
  "background": "研究背景段落",
  "topic_clusters": [
    {"topic": "主题名", "papers": ["论文ID"], "summary": "该主题综述"}
  ],
  "methods": "主要研究方法段落",
  "findings": "主要发现段落",
  "limitations": "研究不足段落",
  "future_trends": "未来趋势段落"
}"""


class LiteratureReviewGenerator:
    """基于 Scope 生成文献综述"""

    def __init__(self, llm_service: LLMService | None = None):
        self.storage = get_storage()
        self.scope_service = RetrievalScopeService()
        self.llm = llm_service or get_llm_service()

    def generate(
        self,
        project_id: str,
        scope_payload: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> Report:
        opts = options or {}
        scope = self.scope_service.resolve(project_id, scope_payload)
        materials = self.collect_materials(scope)
        content = self._generate_with_llm(materials, opts)

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
            "paper_ids": scope.paper_ids,
            "evidence_records": evidence,
            "paper_cards": paper_cards,
        }

    def _generate_with_llm(self, materials: dict[str, Any], options: dict[str, Any]) -> str:
        evidence = materials.get("evidence_records", [])
        cards = materials.get("paper_cards", [])

        # 构建证据摘要
        evidence_text = self._build_evidence_text(evidence)
        cards_text = self._build_cards_text(cards)

        user_prompt = f"""范围：{materials['scope_summary']}
论文数量：{materials['paper_count']}

论文卡片：
{cards_text}

证据记录：
{evidence_text}

请生成结构化的文献综述。"""

        try:
            result = self.llm.invoke_json(REVIEW_SYSTEM_PROMPT, user_prompt)
            return self._render_review(result, materials)
        except Exception as e:
            logger.error(f"LLM review generation failed: {e}")
            return self._generate_fallback(materials)

    def _build_evidence_text(self, evidence: list[EvidenceRecord]) -> str:
        parts = []
        for e in evidence[:30]:
            part = f"[{e.paper_id}]"
            if e.topic:
                part += f" 主题:{e.topic}"
            if e.method:
                part += f" 方法:{e.method}"
            if e.finding and e.finding != "unknown":
                part += f" 发现:{e.finding}"
            if e.limitation and e.limitation != "unknown":
                part += f" 局限:{e.limitation}"
            parts.append(part)
        return "\n".join(parts) if parts else "无证据"

    def _build_cards_text(self, cards: list[dict]) -> str:
        parts = []
        for c in cards[:20]:
            part = f"[{c.get('paper_id', '?')}] {c.get('title', '未知')}"
            if c.get("research_question") and c["research_question"] != "unknown":
                part += f" | 问题:{c['research_question']}"
            parts.append(part)
        return "\n".join(parts) if parts else "无卡片"

    def _render_review(self, result: dict[str, Any], materials: dict[str, Any]) -> str:
        parts = []
        parts.append(f"# 文献综述\n")
        parts.append(f"**生成范围**: {materials['scope_summary']}\n")
        parts.append(f"**使用论文数量**: {materials['paper_count']}\n")

        if result.get("background"):
            parts.append(f"\n## 研究背景\n{result['background']}\n")

        if result.get("topic_clusters"):
            parts.append("\n## 主题划分\n")
            for tc in result["topic_clusters"]:
                parts.append(f"### {tc.get('topic', '未命名主题')}\n")
                parts.append(f"{tc.get('summary', '')}\n")
                if tc.get("papers"):
                    parts.append(f"相关论文: {', '.join(tc['papers'])}\n")

        if result.get("methods"):
            parts.append(f"\n## 主要研究方法\n{result['methods']}\n")

        if result.get("findings"):
            parts.append(f"\n## 主要发现\n{result['findings']}\n")

        if result.get("limitations"):
            parts.append(f"\n## 研究不足\n{result['limitations']}\n")

        if result.get("future_trends"):
            parts.append(f"\n## 未来趋势\n{result['future_trends']}\n")

        # 参考文献
        parts.append("\n## 参考文献\n")
        for pid in materials.get("paper_ids", []):
            card = next((c for c in materials.get("paper_cards", []) if c.get("paper_id") == pid), None)
            if card:
                parts.append(f"- [{pid}] {card.get('title', 'N/A')}")

        return "\n".join(parts)

    def _generate_fallback(self, materials: dict[str, Any]) -> str:
        """LLM 失败时的降级生成"""
        evidence = materials.get("evidence_records", [])
        parts = []
        parts.append(f"# 文献综述\n")
        parts.append(f"**生成范围**: {materials['scope_summary']}\n")
        parts.append(f"**使用论文数量**: {materials['paper_count']}\n")

        parts.append("\n## 主要研究发现\n")
        findings = list({e.finding for e in evidence if e.finding and e.finding != "unknown"})
        for f in findings[:10]:
            parts.append(f"- {f}")

        parts.append("\n## 研究不足\n")
        limitations = list({e.limitation for e in evidence if e.limitation and e.limitation != "unknown"})
        for l in limitations[:10]:
            parts.append(f"- {l}")

        parts.append("\n## 参考文献\n")
        for pid in materials.get("paper_ids", []):
            parts.append(f"- [{pid}]")

        return "\n".join(parts)

    def validate_review(self, report: Report) -> dict[str, Any]:
        issues = []
        if not report.scope:
            issues.append("缺少 scope_summary")
        if not report.paper_ids:
            issues.append("缺少 paper_ids")
        if not report.evidence_ids:
            issues.append("缺少 evidence_ids")
        return {"valid": len(issues) == 0, "issues": issues}
