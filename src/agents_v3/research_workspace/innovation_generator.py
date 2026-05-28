"""创新点报告生成器"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    InnovationPoint,
    Report,
    ReportType,
    RetrievalScope,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import get_storage

# 泛化短语黑名单
GENERIC_PHRASES = [
    "多模态", "深度学习", "大模型", "扩展样本", "跨学科",
    "优化算法", "提高准确率", "multimodal", "deep learning",
    "large model", "expand sample", "interdisciplinary",
]


class InnovationReportGenerator:
    """基于 Scope 生成创新点报告"""

    def __init__(self):
        self.storage = get_storage()
        self.scope_service = RetrievalScopeService()

    def generate(
        self,
        project_id: str,
        scope_payload: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> Report:
        scope = self.scope_service.resolve(project_id, scope_payload)
        gap_signals = self.collect_gap_signals(scope)
        candidates = self.generate_candidates(gap_signals)
        scored = self.score_candidates(candidates)
        content = self.render_report(scored)

        report = Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.INNOVATION_REPORT,
            title=f"创新点报告 - {scope.summary}",
            content=content,
            scope=scope.model_dump(),
            paper_ids=scope.paper_ids,
            evidence_ids=scope.evidence_ids,
        )

        self.storage.upsert_item("reports", report.report_id, report.model_dump())
        logger.info(f"Generated innovation report: {report.report_id}")
        return report

    def collect_gap_signals(self, scope: RetrievalScope) -> dict[str, Any]:
        evidence = self.scope_service.to_evidence_records(scope)
        graph_context = self.scope_service.to_graph_context(scope)

        return {
            "evidence_records": evidence,
            "limitations": self.aggregate_limitations(evidence),
            "graph_gaps": self.detect_graph_gaps(graph_context),
            "paper_ids": scope.paper_ids,
        }

    def detect_graph_gaps(self, graph_context: dict[str, Any]) -> list[dict[str, Any]]:
        nodes = graph_context.get("nodes", [])
        edges = graph_context.get("edges", [])

        # Find topics with few methods
        topic_methods: dict[str, set[str]] = {}
        for e in edges:
            if e.get("edge_type") == "USES_METHOD":
                source = e.get("source_id", "")
                target = e.get("target_id", "")
                if "paper:" in source:
                    # Find connected topics
                    for e2 in edges:
                        if e2.get("source_id") == source and e2.get("edge_type") == "BELONGS_TO_TOPIC":
                            topic = e2.get("target_id", "")
                            if topic not in topic_methods:
                                topic_methods[topic] = set()
                            topic_methods[topic].add(target)

        gaps = []
        for topic, methods in topic_methods.items():
            if len(methods) < 2:
                gaps.append({
                    "type": "method_gap",
                    "topic": topic,
                    "description": f"主题 {topic} 只有 {len(methods)} 种方法",
                })

        return gaps

    def aggregate_limitations(self, evidence: list[EvidenceRecord]) -> list[dict[str, Any]]:
        limit_counts: dict[str, int] = {}
        for e in evidence:
            if e.limitation and e.limitation != "unknown":
                limit_counts[e.limitation] = limit_counts.get(e.limitation, 0) + 1

        return [
            {"limitation": k, "count": v}
            for k, v in sorted(limit_counts.items(), key=lambda x: -x[1])
        ]

    def generate_candidates(self, gap_signals: dict[str, Any]) -> list[InnovationPoint]:
        candidates = []
        evidence = gap_signals.get("evidence_records", [])
        limitations = gap_signals.get("limitations", [])
        graph_gaps = gap_signals.get("graph_gaps", [])

        # From limitations
        for lim in limitations[:3]:
            if self._is_generic(lim["limitation"]):
                continue
            ip = InnovationPoint(
                innovation_id=f"ip_{uuid.uuid4().hex[:8]}",
                name=f"解决: {lim['limitation'][:30]}",
                description=f"针对 {lim['limitation']} 的改进方案",
                why_innovative=f"该不足被 {lim['count']} 篇论文提及",
                gap=lim["limitation"],
                supporting_papers=gap_signals.get("paper_ids", [])[:3],
                feasibility="medium",
            )
            candidates.append(ip)

        # From graph gaps
        for gap in graph_gaps[:3]:
            ip = InnovationPoint(
                innovation_id=f"ip_{uuid.uuid4().hex[:8]}",
                name=f"填补: {gap.get('topic', '未知')}",
                description=gap.get("description", ""),
                why_innovative="图谱分析发现方法-主题连接缺失",
                gap=gap.get("description", ""),
                supporting_papers=gap_signals.get("paper_ids", [])[:3],
                feasibility="medium",
            )
            candidates.append(ip)

        # Fallback: generic from future work
        if not candidates:
            for e in evidence[:3]:
                if e.future_work and e.future_work != "unknown":
                    ip = InnovationPoint(
                        innovation_id=f"ip_{uuid.uuid4().hex[:8]}",
                        name=f"探索: {e.future_work[:30]}",
                        description=e.future_work,
                        why_innovative="基于论文 future work 方向",
                        supporting_papers=[e.paper_id],
                        feasibility="low",
                    )
                    candidates.append(ip)

        return candidates

    def score_candidates(self, candidates: list[InnovationPoint]) -> list[InnovationPoint]:
        for c in candidates:
            scores = {
                "evidence_strength": 0.5,
                "novelty": 0.5,
                "feasibility": 0.5,
            }
            if len(c.supporting_papers) >= 2:
                scores["evidence_strength"] = 0.8
            if c.gap and not self._is_generic(c.gap):
                scores["novelty"] = 0.7
            c.scores = scores
        return sorted(candidates, key=lambda c: -sum(c.scores.values()))

    def render_report(self, candidates: list[InnovationPoint]) -> str:
        parts = ["# 创新点报告\n"]
        parts.append(f"**发现 {len(candidates)} 个创新方向**\n")

        for i, c in enumerate(candidates, 1):
            parts.append(f"\n## {i}. {c.name}\n")
            parts.append(f"**描述**: {c.description}\n")
            parts.append(f"**创新性**: {c.why_innovative}\n")
            if c.gap:
                parts.append(f"**研究空白**: {c.gap}\n")
            if c.supporting_papers:
                parts.append(f"**支撑论文**: {', '.join(c.supporting_papers[:5])}\n")
            if c.scores:
                parts.append(f"**评分**: {c.scores}\n")

        return "".join(parts)

    def _is_generic(self, text: str) -> bool:
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in GENERIC_PHRASES)
