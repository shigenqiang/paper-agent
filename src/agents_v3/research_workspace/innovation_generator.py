"""创新点报告生成器 - LLM 驱动"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm_service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    InnovationPoint,
    Report,
    ReportType,
    RetrievalScope,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import get_storage

GENERIC_PHRASES = [
    "多模态", "深度学习", "大模型", "扩展样本", "跨学科",
    "优化算法", "提高准确率", "multimodal", "deep learning",
    "large model", "expand sample", "interdisciplinary",
]

INNOVATION_SYSTEM_PROMPT = """你是一个学术研究创新分析专家。请根据提供的论文证据和研究空白，分析可行的创新方向。

要求：
1. 创新点必须有具体证据支撑，不能是泛化表述
2. 分析图谱中的 Gap（缺失边、低连接组合）
3. 评估可行性和风险
4. 使用中文撰写

输出格式（JSON）：
{
  "innovation_points": [
    {
      "name": "创新点名称",
      "description": "详细描述",
      "why_innovative": "为什么是创新",
      "research_foundation": "现有研究基础",
      "gap": "研究空白",
      "feasibility": "可行性评估",
      "risk": "风险评估",
      "possible_topic": "可能的论文题目"
    }
  ]
}"""


class InnovationReportGenerator:
    """基于 Scope 生成创新点报告"""

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
        scope = self.scope_service.resolve(project_id, scope_payload)
        gap_signals = self.collect_gap_signals(scope)
        candidates = self._generate_with_llm(gap_signals)
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
            "scope_summary": scope.summary,
        }

    def detect_graph_gaps(self, graph_context: dict[str, Any]) -> list[dict[str, Any]]:
        edges = graph_context.get("edges", [])

        topic_methods: dict[str, set[str]] = {}
        for e in edges:
            if e.get("edge_type") == "USES_METHOD":
                source = e.get("source_id", "")
                for e2 in edges:
                    if e2.get("source_id") == source and e2.get("edge_type") == "BELONGS_TO_TOPIC":
                        topic = e2.get("target_id", "")
                        if topic not in topic_methods:
                            topic_methods[topic] = set()
                        topic_methods[topic].add(e.get("target_id", ""))

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

    def _generate_with_llm(self, gap_signals: dict[str, Any]) -> list[InnovationPoint]:
        limitations = gap_signals.get("limitations", [])
        graph_gaps = gap_signals.get("graph_gaps", [])
        evidence = gap_signals.get("evidence_records", [])

        # 构建上下文
        limit_text = "\n".join(f"- {l['limitation']} (出现 {l['count']} 次)" for l in limitations[:10])
        gap_text = "\n".join(f"- {g.get('description', '')}" for g in graph_gaps[:10])
        evidence_text = "\n".join(
            f"[{e.paper_id}] {e.finding or ''} | 局限: {e.limitation or ''}"
            for e in evidence[:20]
            if e.finding or e.limitation
        )

        user_prompt = f"""范围：{gap_signals.get('scope_summary', '未知')}

共同局限：
{limit_text or '无'}

图谱 Gap：
{gap_text or '无'}

证据记录：
{evidence_text or '无'}

请分析可行的创新方向。"""

        try:
            result = self.llm.invoke_json(INNOVATION_SYSTEM_PROMPT, user_prompt)
            candidates = []
            for ip_data in result.get("innovation_points", []):
                if self._is_generic(ip_data.get("description", "")):
                    continue
                ip = InnovationPoint(
                    innovation_id=f"ip_{uuid.uuid4().hex[:8]}",
                    name=ip_data.get("name", ""),
                    description=ip_data.get("description", ""),
                    why_innovative=ip_data.get("why_innovative", ""),
                    research_foundation=ip_data.get("research_foundation", ""),
                    gap=ip_data.get("gap", ""),
                    supporting_papers=gap_signals.get("paper_ids", [])[:3],
                    feasibility=ip_data.get("feasibility", "medium"),
                    risk=ip_data.get("risk", ""),
                    possible_topic=ip_data.get("possible_topic", ""),
                )
                candidates.append(ip)
            return candidates if candidates else self._generate_fallback(gap_signals)
        except Exception as e:
            logger.error(f"LLM innovation generation failed: {e}")
            return self._generate_fallback(gap_signals)

    def _generate_fallback(self, gap_signals: dict[str, Any]) -> list[InnovationPoint]:
        """LLM 失败时的降级生成"""
        candidates = []
        limitations = gap_signals.get("limitations", [])
        graph_gaps = gap_signals.get("graph_gaps", [])

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
            if c.research_foundation:
                parts.append(f"**研究基础**: {c.research_foundation}\n")
            if c.feasibility:
                parts.append(f"**可行性**: {c.feasibility}\n")
            if c.risk:
                parts.append(f"**风险**: {c.risk}\n")
            if c.possible_topic:
                parts.append(f"**可能题目**: {c.possible_topic}\n")
            if c.supporting_papers:
                parts.append(f"**支撑论文**: {', '.join(c.supporting_papers[:5])}\n")
            if c.scores:
                parts.append(f"**评分**: {c.scores}\n")

        return "".join(parts)

    def _is_generic(self, text: str) -> bool:
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in GENERIC_PHRASES)
