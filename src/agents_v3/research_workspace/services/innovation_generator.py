"""创新点报告生成器 - 增强版"""

from __future__ import annotations

import re
import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    InnovationPoint,
    Report,
    ReportType,
    RetrievalScope,
)
from src.agents_v3.research_workspace.services.scope import RetrievalScopeService
from src.agents_v3.research_workspace.utils import normalize_label
from src.agents_v3.research_workspace.storage import get_storage

# ── 泛化检测 ──────────────────────────────────────────

GENERIC_PHRASES = [
    "多模态", "深度学习", "大模型", "扩展样本", "跨学科",
    "优化算法", "提高准确率", "multimodal", "deep learning",
    "large model", "expand sample", "interdisciplinary",
    "扩大样本", "加强研究", "进一步探索", "需要更多研究",
    "提高效率", "改进方法", "融合多种方法",
]

# 显式 gap 关键词
_GAP_KEYWORDS = [
    "lack", "limited", "insufficient", "few", "missing", "no ",
    "缺乏", "不足", "尚未", "很少", "没有", "未",
    "future work", "should", "explore", "need",
    "未来", "建议", "需要", "可以",
]

# ── Prompt ──────────────────────────────────────────

INNOVATION_SYSTEM_PROMPT = """你是一个学术研究创新分析专家。根据提供的研究信号和证据，分析可行的创新方向。

规则：
1. 创新点必须有具体证据支撑，不能是泛化表述
2. 不得引用输入中不存在的 paper_id 或 evidence_id
3. 每个创新点必须说明来源信号和支撑证据
4. 评估可行性和风险时要考虑具体约束
5. possible_topic 必须具体到对象、方法、场景
6. 使用中文撰写

你将收到预先构建的创新信号骨架。你的职责是：
- 将骨架改写为自然语言描述
- 补全 why_innovative、research_foundation、feasibility、risk
- 生成 possible_topic
- 不要自造 paper_id 或 evidence_id

输出格式（JSON）：
{
  "innovation_points": [
    {
      "name": "创新点名称",
      "description": "详细描述",
      "why_innovative": "为什么是创新",
      "research_foundation": "现有研究基础",
      "feasibility": "可行性评估",
      "risk": "风险评估",
      "possible_topic": "可能的论文题目"
    }
  ]
}"""


class InnovationReportGenerator:
    """基于 Scope 生成创新点报告"""

    def __init__(self, storage=None, llm_service: LLMService | None = None):
        self.storage = storage or get_storage()
        self.scope_service = RetrievalScopeService(storage=self.storage)
        self.llm = llm_service or get_llm_service()

    def generate(
        self,
        project_id: str,
        scope_payload: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> Report:
        opts = options or {}

        # 1. Resolve scope
        scope = self.scope_service.resolve(project_id, scope_payload)

        # 2. Check empty scope
        empty_reason = scope.metadata.get("empty_reason", "")
        if empty_reason:
            return self._empty_scope_report(project_id, scope, empty_reason)

        # 3. Collect signals
        signals = self.collect_signals(scope)

        # 4. Check evidence sufficiency
        evidence = signals.get("evidence_records", [])
        if len(evidence) < 2:
            return self._insufficient_evidence_report(project_id, scope, len(evidence))

        # 5. Build candidate skeletons from signals
        skeletons = self._build_candidate_skeletons(signals)

        # 6. Generate with LLM (or fallback)
        candidates = self._generate_candidates(skeletons, signals)

        # 7. Score
        scored = self._score_candidates(candidates, signals)

        # 8. Filter generic
        filtered = [c for c in scored if not self._is_generic(c.get("description", ""))]

        # 9. Validate
        validation = self._validate_candidates(filtered, scope, signals)

        # 10. Render
        content = self._render_report(filtered, signals, validation)

        # 11. Build report
        used_papers = set()
        used_evidence = set()
        for c in filtered:
            used_papers.update(c.get("supporting_papers", []))
            used_evidence.update(c.get("supporting_evidence_ids", []))

        report = Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.INNOVATION_REPORT,
            title=f"创新点报告 - {scope.summary}",
            content=content,
            scope={
                **scope.model_dump(),
                "innovation_metadata": {
                    "candidates": filtered,
                    "source_signals": {
                        "common_limitations": len(signals.get("common_limitations", [])),
                        "future_work_clusters": len(signals.get("future_work_clusters", [])),
                        "graph_gaps": len(signals.get("graph_gaps", [])),
                        "explicit_gaps": len(signals.get("explicit_gaps", [])),
                    },
                    "validation_result": validation,
                },
            },
            paper_ids=sorted(used_papers),
            evidence_ids=sorted(used_evidence),
        )

        self.storage.upsert_item("reports", report.report_id, report.model_dump())
        logger.info(
            f"Generated innovation report: {report.report_id} "
            f"(candidates={len(filtered)}, signals={len(skeletons)})"
        )
        return report

    # ── 信号收集 ──────────────────────────────────

    def collect_signals(self, scope: RetrievalScope) -> dict[str, Any]:
        evidence = self.scope_service.to_evidence_records(scope)
        paper_cards = self.scope_service.to_paper_cards(scope)
        graph_context = self.scope_service.to_graph_context(scope)

        common_limitations = self._aggregate_limitations(evidence)
        future_work_clusters = self._aggregate_future_works(evidence)
        graph_gaps = self._detect_graph_gaps(graph_context)
        explicit_gaps = self._detect_explicit_gaps(evidence)

        return {
            "evidence_records": evidence,
            "paper_cards": paper_cards,
            "common_limitations": common_limitations,
            "future_work_clusters": future_work_clusters,
            "graph_gaps": graph_gaps,
            "explicit_gaps": explicit_gaps,
            "paper_ids": scope.paper_ids,
            "scope_summary": scope.summary,
            "graph_context": graph_context,
        }

    def _aggregate_limitations(self, evidence: list[EvidenceRecord]) -> list[dict]:
        """聚合共同局限"""
        clusters: dict[str, dict] = {}
        for ev in evidence:
            lim = (ev.limitation or "").strip()
            if not lim or lim.lower() in ("unknown", "none", ""):
                continue
            key = normalize_label(lim)[:80]
            if key not in clusters:
                clusters[key] = {
                    "text": lim,
                    "normalized": key,
                    "evidence_ids": [],
                    "paper_ids": [],
                    "count": 0,
                }
            clusters[key]["evidence_ids"].append(ev.evidence_id)
            clusters[key]["paper_ids"].append(ev.paper_id)
            clusters[key]["count"] += 1

        # 只保留 >= 2 篇论文提及的，或有 source_quote 的
        result = []
        for c in clusters.values():
            unique_papers = len(set(c["paper_ids"]))
            if unique_papers >= 2 or c["count"] >= 2:
                c["paper_ids"] = list(set(c["paper_ids"]))
                c["confidence"] = min(0.9, 0.4 + 0.1 * unique_papers)
                result.append(c)

        return sorted(result, key=lambda x: -x["count"])

    def _aggregate_future_works(self, evidence: list[EvidenceRecord]) -> list[dict]:
        """聚合 future_work 方向"""
        clusters: dict[str, dict] = {}
        for ev in evidence:
            fw = (ev.future_work or "").strip()
            if not fw or fw.lower() in ("unknown", "none", ""):
                continue
            key = normalize_label(fw)[:80]
            if key not in clusters:
                clusters[key] = {
                    "text": fw,
                    "normalized": key,
                    "evidence_ids": [],
                    "paper_ids": [],
                    "count": 0,
                }
            clusters[key]["evidence_ids"].append(ev.evidence_id)
            clusters[key]["paper_ids"].append(ev.paper_id)
            clusters[key]["count"] += 1

        result = []
        for c in clusters.values():
            c["paper_ids"] = list(set(c["paper_ids"]))
            c["confidence"] = min(0.85, 0.3 + 0.15 * len(set(c["paper_ids"])))
            result.append(c)

        return sorted(result, key=lambda x: -x["count"])

    def _detect_graph_gaps(self, graph_context: dict) -> list[dict]:
        """从图谱检测 gap"""
        gaps = []
        nodes = graph_context.get("nodes", [])
        edges = graph_context.get("edges", [])

        # Gap 节点
        for n in nodes:
            if n.get("node_type") == "Gap":
                props = n.get("properties", {})
                if props.get("confidence", 0) >= 0.5:
                    gaps.append({
                        "type": "graph_gap",
                        "description": props.get("gap_statement", n.get("label", "")),
                        "supporting_evidence_ids": props.get("supporting_evidence_ids", []),
                        "supporting_paper_ids": props.get("supporting_paper_ids", []),
                        "confidence": props.get("confidence", 0.5),
                        "graph_node_id": n.get("node_id", ""),
                    })

        # Topic-Method 覆盖矩阵
        topic_methods: dict[str, set[str]] = {}
        for e in edges:
            if e.get("edge_type") == "USES_METHOD":
                paper_id = e.get("source_id", "")
                method_id = e.get("target_id", "")
                for e2 in edges:
                    if e2.get("source_id") == paper_id and e2.get("edge_type") == "BELONGS_TO_TOPIC":
                        topic = e2.get("target_id", "")
                        topic_methods.setdefault(topic, set()).add(method_id)

        for topic, methods in topic_methods.items():
            if len(methods) < 2:
                gaps.append({
                    "type": "method_gap",
                    "description": f"主题 {topic.split(':')[-1]} 仅有 {len(methods)} 种方法覆盖",
                    "topic": topic,
                    "confidence": 0.4,
                })

        return gaps

    def _detect_explicit_gaps(self, evidence: list[EvidenceRecord]) -> list[dict]:
        """从 limitation/future_work 中检测显式 gap 表述"""
        gaps = []
        for ev in evidence:
            for field_name in ("limitation", "future_work"):
                text = getattr(ev, field_name, "") or ""
                if not text or text.lower() in ("unknown", ""):
                    continue
                text_lower = text.lower()
                if any(kw in text_lower for kw in _GAP_KEYWORDS):
                    gaps.append({
                        "type": "explicit_gap",
                        "description": text[:100],
                        "source_field": field_name,
                        "evidence_id": ev.evidence_id,
                        "paper_id": ev.paper_id,
                        "confidence": 0.6,
                    })
        return gaps

    # ── 候选骨架构建 ──────────────────────────────

    def _build_candidate_skeletons(self, signals: dict) -> list[dict]:
        """从信号构建候选骨架（LLM 不能自造来源）"""
        skeletons = []

        # 从共同局限
        for lim in signals.get("common_limitations", [])[:5]:
            if self._is_generic(lim["text"]):
                continue
            skeletons.append({
                "name": f"解决: {lim['text'][:40]}",
                "gap": lim["text"],
                "source_signal_type": "common_limitation",
                "supporting_evidence_ids": lim["evidence_ids"][:5],
                "supporting_paper_ids": lim["paper_ids"][:5],
                "confidence": lim.get("confidence", 0.5),
            })

        # 从 future_work
        for fw in signals.get("future_work_clusters", [])[:5]:
            if self._is_generic(fw["text"]):
                continue
            skeletons.append({
                "name": f"探索: {fw['text'][:40]}",
                "gap": fw["text"],
                "source_signal_type": "future_work_cluster",
                "supporting_evidence_ids": fw["evidence_ids"][:5],
                "supporting_paper_ids": fw["paper_ids"][:5],
                "confidence": fw.get("confidence", 0.5),
            })

        # 从 graph gaps
        for gap in signals.get("graph_gaps", [])[:3]:
            if self._is_generic(gap.get("description", "")):
                continue
            skeletons.append({
                "name": f"填补: {gap.get('description', '')[:40]}",
                "gap": gap.get("description", ""),
                "source_signal_type": gap.get("type", "graph_gap"),
                "supporting_evidence_ids": gap.get("supporting_evidence_ids", []),
                "supporting_paper_ids": gap.get("supporting_paper_ids", []),
                "graph_node_id": gap.get("graph_node_id", ""),
                "confidence": gap.get("confidence", 0.4),
            })

        # 从显式 gaps
        for gap in signals.get("explicit_gaps", [])[:3]:
            skeletons.append({
                "name": f"方向: {gap['description'][:40]}",
                "gap": gap["description"],
                "source_signal_type": "explicit_gap",
                "supporting_evidence_ids": [gap.get("evidence_id", "")],
                "supporting_paper_ids": [gap.get("paper_id", "")],
                "confidence": gap.get("confidence", 0.5),
            })

        # 去重
        seen = set()
        unique = []
        for s in skeletons:
            key = normalize_label(s["gap"])[:50]
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique

    # ── 候选生成 ──────────────────────────────────

    def _generate_candidates(self, skeletons: list[dict], signals: dict) -> list[dict]:
        """生成候选（LLM 或 fallback）"""
        if not skeletons:
            return []

        # 构建 evidence 索引
        evidence_map = {}
        for ev in signals.get("evidence_records", []):
            evidence_map[ev.evidence_id] = ev

        if self.llm:
            try:
                return self._generate_with_llm(skeletons, signals, evidence_map)
            except Exception as e:
                logger.error(f"LLM innovation generation failed: {e}")

        return self._generate_fallback(skeletons, evidence_map)

    def _generate_with_llm(
        self, skeletons: list[dict], signals: dict, evidence_map: dict
    ) -> list[dict]:
        # 构建骨架文本
        skeleton_text = ""
        for i, s in enumerate(skeletons[:8]):
            skeleton_text += f"\n骨架 {i+1}: {s['name']}\n"
            skeleton_text += f"  研究空白: {s['gap']}\n"
            skeleton_text += f"  来源类型: {s['source_signal_type']}\n"
            skeleton_text += f"  支撑论文: {', '.join(s.get('supporting_paper_ids', [])[:3])}\n"
            skeleton_text += f"  支撑证据: {', '.join(s.get('supporting_evidence_ids', [])[:3])}\n"

        # 证据摘要
        evidence_text = ""
        for ev in signals.get("evidence_records", [])[:15]:
            ev_dict = ev.model_dump() if hasattr(ev, "model_dump") else ev
            evidence_text += f"[{ev_dict.get('evidence_id', '?')}] {ev_dict.get('paper_id', '?')}"
            if ev_dict.get("finding") and ev_dict["finding"] != "unknown":
                evidence_text += f" | 发现:{ev_dict['finding'][:60]}"
            if ev_dict.get("limitation") and ev_dict["limitation"] != "unknown":
                evidence_text += f" | 局限:{ev_dict['limitation'][:60]}"
            evidence_text += "\n"

        user_prompt = f"""范围：{signals.get('scope_summary', '未知')}

预构建的创新信号骨架：
{skeleton_text}

证据详情：
{evidence_text}

请将以上骨架改写为完整的创新点分析。每个创新点必须引用骨架中提供的 evidence_ids，不要自造新的 ID。"""

        result = self.llm.invoke_json(INNOVATION_SYSTEM_PROMPT, user_prompt)

        candidates = []
        for i, ip_data in enumerate(result.get("innovation_points", [])):
            if i >= len(skeletons):
                break
            skeleton = skeletons[i]
            candidates.append({
                "innovation_id": f"ip_{uuid.uuid4().hex[:8]}",
                "name": ip_data.get("name", skeleton["name"]),
                "description": ip_data.get("description", skeleton["gap"]),
                "why_innovative": ip_data.get("why_innovative", ""),
                "research_foundation": ip_data.get("research_foundation", ""),
                "gap": skeleton["gap"],
                "supporting_papers": skeleton.get("supporting_papers", skeleton.get("supporting_paper_ids", [])),
                "supporting_evidence_ids": skeleton.get("supporting_evidence_ids", []),
                "limiting_evidence_ids": [],
                "feasibility": ip_data.get("feasibility", "medium"),
                "risk": ip_data.get("risk", ""),
                "possible_topic": ip_data.get("possible_topic", ""),
                "source_signal_type": skeleton["source_signal_type"],
                "confidence": skeleton.get("confidence", 0.5),
                "scores": {},
            })

        return candidates if candidates else self._generate_fallback(skeletons, evidence_map)

    def _generate_fallback(self, skeletons: list[dict], evidence_map: dict) -> list[dict]:
        """LLM 失败时的降级生成"""
        candidates = []
        for s in skeletons[:5]:
            candidates.append({
                "innovation_id": f"ip_{uuid.uuid4().hex[:8]}",
                "name": s["name"],
                "description": s["gap"],
                "why_innovative": f"基于 {s['source_signal_type']} 信号",
                "research_foundation": "",
                "gap": s["gap"],
                "supporting_papers": s.get("supporting_paper_ids", []),
                "supporting_evidence_ids": s.get("supporting_evidence_ids", []),
                "limiting_evidence_ids": [],
                "feasibility": "medium",
                "risk": "需要进一步验证",
                "possible_topic": "",
                "source_signal_type": s["source_signal_type"],
                "confidence": s.get("confidence", 0.4),
                "scores": {},
            })
        return candidates

    # ── 评分 ──────────────────────────────────────

    def _score_candidates(self, candidates: list[dict], signals: dict) -> list[dict]:
        for c in candidates:
            scores = {}

            # Novelty: 非泛化 + 有 gap 具体描述
            novelty = 0.4
            if c.get("gap") and not self._is_generic(c["gap"]):
                novelty += 0.3
            if c.get("source_signal_type") in ("common_limitation", "explicit_gap"):
                novelty += 0.1
            scores["novelty"] = min(1.0, novelty)

            # Evidence: 支撑论文和证据数量
            evidence_score = 0.3
            sp_count = len(set(c.get("supporting_papers", [])))
            se_count = len(set(c.get("supporting_evidence_ids", [])))
            if sp_count >= 2:
                evidence_score += 0.3
            elif sp_count >= 1:
                evidence_score += 0.15
            if se_count >= 2:
                evidence_score += 0.2
            elif se_count >= 1:
                evidence_score += 0.1
            scores["evidence"] = min(1.0, evidence_score)

            # Feasibility
            feasibility = c.get("feasibility", "medium")
            if isinstance(feasibility, str):
                scores["feasibility"] = {"high": 0.8, "medium": 0.5, "low": 0.3}.get(feasibility.lower(), 0.5)
            else:
                scores["feasibility"] = 0.5

            # Risk
            risk_text = c.get("risk", "")
            if risk_text and not self._is_generic(risk_text):
                scores["risk"] = 0.6  # Has specific risk assessment
            else:
                scores["risk"] = 0.3

            # Specificity
            specificity = 0.3
            if c.get("possible_topic") and len(c["possible_topic"]) > 10:
                specificity += 0.3
            if c.get("research_foundation") and len(c["research_foundation"]) > 10:
                specificity += 0.2
            if c.get("description") and len(c["description"]) > 20:
                specificity += 0.2
            scores["specificity"] = min(1.0, specificity)

            # Total
            scores["total"] = (
                0.25 * scores["novelty"]
                + 0.25 * scores["evidence"]
                + 0.2 * scores["feasibility"]
                + 0.1 * scores["risk"]
                + 0.2 * scores["specificity"]
            )

            c["scores"] = scores
            c["confidence"] = max(c.get("confidence", 0.4), scores["total"])

        return sorted(candidates, key=lambda c: -c["scores"].get("total", 0))

    # ── 校验 ──────────────────────────────────────

    def _validate_candidates(
        self, candidates: list[dict], scope: RetrievalScope, signals: dict
    ) -> dict:
        allowed_papers = set(scope.paper_ids)
        allowed_evidence = set(scope.evidence_ids)

        scope_violations = 0
        missing_evidence = 0
        generic_count = 0

        for c in candidates:
            for pid in c.get("supporting_papers", []):
                if pid and pid not in allowed_papers:
                    scope_violations += 1
            for eid in c.get("supporting_evidence_ids", []):
                if eid and eid not in allowed_evidence:
                    scope_violations += 1
                elif eid and eid not in {ev.evidence_id for ev in signals.get("evidence_records", [])}:
                    missing_evidence += 1
            if self._is_generic(c.get("description", "")):
                generic_count += 1

        return {
            "passed": scope_violations == 0,
            "candidate_count": len(candidates),
            "scope_violation_count": scope_violations,
            "missing_evidence_count": missing_evidence,
            "generic_candidate_count": generic_count,
        }

    # ── 渲染 ──────────────────────────────────────

    def _render_report(
        self, candidates: list[dict], signals: dict, validation: dict
    ) -> str:
        parts = ["# 创新点报告\n"]
        parts.append(f"**发现 {len(candidates)} 个创新方向**\n")

        # 信号摘要
        parts.append("## 信号来源\n")
        parts.append(f"- 共同局限: {len(signals.get('common_limitations', []))} 个")
        parts.append(f"- 未来方向: {len(signals.get('future_work_clusters', []))} 个")
        parts.append(f"- 图谱 Gap: {len(signals.get('graph_gaps', []))} 个")
        parts.append(f"- 显式空白: {len(signals.get('explicit_gaps', []))} 个\n")

        # 创新点列表
        for i, c in enumerate(candidates, 1):
            parts.append(f"\n## {i}. {c.get('name', '未命名')}\n")
            parts.append(f"**描述**: {c.get('description', '')}\n")
            if c.get("why_innovative"):
                parts.append(f"**创新性**: {c['why_innovative']}\n")
            if c.get("gap"):
                parts.append(f"**研究空白**: {c['gap']}\n")
            if c.get("research_foundation"):
                parts.append(f"**研究基础**: {c['research_foundation']}\n")
            if c.get("feasibility"):
                parts.append(f"**可行性**: {c['feasibility']}\n")
            if c.get("risk"):
                parts.append(f"**风险**: {c['risk']}\n")
            if c.get("possible_topic"):
                parts.append(f"**可能题目**: {c['possible_topic']}\n")

            # 来源
            sp = c.get("supporting_papers", [])
            se = c.get("supporting_evidence_ids", [])
            if sp:
                parts.append(f"**支撑论文**: {', '.join(sp[:5])}")
            if se:
                parts.append(f"**支撑证据**: {', '.join(se[:5])}")

            # 评分
            scores = c.get("scores", {})
            if scores:
                parts.append(f"\n**评分**: 新颖性={scores.get('novelty', 0):.2f}, "
                             f"证据={scores.get('evidence', 0):.2f}, "
                             f"可行性={scores.get('feasibility', 0):.2f}, "
                             f"具体性={scores.get('specificity', 0):.2f}, "
                             f"综合={scores.get('total', 0):.2f}")

        # 质量校验
        parts.append("\n\n## 质量校验\n")
        parts.append(f"- 候选数量: {validation.get('candidate_count', 0)}")
        parts.append(f"- Scope 越界: {validation.get('scope_violation_count', 0)}")
        parts.append(f"- 泛化候选: {validation.get('generic_candidate_count', 0)}")

        return "\n".join(parts)

    # ── 空范围/证据不足 ──────────────────────────

    def _empty_scope_report(self, project_id: str, scope: RetrievalScope, empty_reason: str) -> Report:
        content = f"# 创新点报告\n\n**无法生成**: 当前范围为空 ({empty_reason})\n"
        return Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.INNOVATION_REPORT,
            title=f"创新点报告 - {scope.summary}",
            content=content,
            scope={**scope.model_dump(), "empty_reason": empty_reason},
            paper_ids=[], evidence_ids=[],
        )

    def _insufficient_evidence_report(self, project_id: str, scope: RetrievalScope, evidence_count: int) -> Report:
        content = (
            f"# 创新点报告\n\n"
            f"**无法生成**: 当前范围内仅有 {evidence_count} 条证据，不足以生成可靠创新点。\n\n"
            f"建议: 先生成论文卡片和证据表，或扩大选择范围。\n"
        )
        return Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.INNOVATION_REPORT,
            title=f"创新点报告 - {scope.summary}",
            content=content,
            scope=scope.model_dump(),
            paper_ids=scope.paper_ids, evidence_ids=scope.evidence_ids,
        )

    # ── 工具 ──────────────────────────────────────

    def _is_generic(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in GENERIC_PHRASES)

    # ── 兼容旧接口 ──────────────────────────────

    def aggregate_limitations(self, evidence: list[EvidenceRecord]) -> list[dict]:
        return self._aggregate_limitations(evidence)

    def detect_graph_gaps(self, graph_context: dict) -> list[dict]:
        return self._detect_graph_gaps(graph_context)

    def score_candidates(self, candidates):
        """兼容旧接口"""
        if candidates and isinstance(candidates[0], dict):
            return self._score_candidates(candidates, {})
        # InnovationPoint objects
        dicts = []
        for c in candidates:
            d = c.model_dump() if hasattr(c, "model_dump") else c
            dicts.append(d)
        scored = self._score_candidates(dicts, {})
        # Convert back to InnovationPoint
        result = []
        for d in scored:
            result.append(InnovationPoint(**{k: v for k, v in d.items() if k in InnovationPoint.model_fields}))
        return result

    def render_report(self, candidates) -> str:
        """兼容旧接口"""
        if candidates and isinstance(candidates[0], dict):
            return self._render_report(candidates, {}, {})
        dicts = [c.model_dump() if hasattr(c, "model_dump") else c for c in candidates]
        return self._render_report(dicts, {}, {})
