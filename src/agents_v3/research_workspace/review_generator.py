"""文献综述生成器 - 增强版"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    Report,
    ReportType,
    RetrievalScope,
)
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage

# ── 论文数量限制（从环境变量读取）──────────────────────
REVIEW_MAX_PAPERS = int(os.getenv("REVIEW_MAX_PAPERS", "40"))
REVIEW_LOCAL_MAX = int(os.getenv("REVIEW_LOCAL_MAX", "20"))
REVIEW_REMOTE_MAX = int(os.getenv("REVIEW_REMOTE_MAX", "20"))

# ── Prompt ──────────────────────────────────────────

REVIEW_SYSTEM_PROMPT = """你是一个学术文献综述写作专家。根据提供的证据矩阵和论文信息，生成结构化的文献综述。

规则：
1. 综述必须基于提供的证据，不要编造
2. 每个主要章节必须返回使用的 evidence_ids 和 paper_ids
3. 按主题组织内容，展示研究脉络
4. 指出研究不足和未来趋势
5. 证据不足时写入"本综述限制"
6. 使用中文撰写

输出格式（JSON）：
{
  "sections": [
    {
      "section_id": "background",
      "title": "研究背景",
      "content": "段落正文",
      "paper_ids": ["p1"],
      "evidence_ids": ["ev1"]
    },
    {
      "section_id": "methods",
      "title": "主要研究方法",
      "content": "段落正文",
      "paper_ids": ["p1", "p2"],
      "evidence_ids": ["ev1", "ev2"]
    },
    {
      "section_id": "findings",
      "title": "主要研究发现",
      "content": "段落正文",
      "paper_ids": ["p1"],
      "evidence_ids": ["ev1"]
    },
    {
      "section_id": "limitations",
      "title": "研究不足",
      "content": "段落正文",
      "paper_ids": ["p2"],
      "evidence_ids": ["ev2"]
    },
    {
      "section_id": "future_trends",
      "title": "未来研究趋势",
      "content": "段落正文",
      "paper_ids": [],
      "evidence_ids": []
    }
  ],
  "overall_limitations": "本综述的限制说明"
}"""

# 泛化套话检测
_GENERIC_PHRASES = [
    "大量研究表明", "许多研究", "普遍认为", "众多学者", "学界共识",
    "many studies", "numerous researchers", "it is widely accepted",
    "大量文献", "相关研究", "已有研究表明",
]

# 必需章节
_REQUIRED_SECTIONS = {"background", "methods", "findings", "limitations", "future_trends"}


class LiteratureReviewGenerator:
    """基于 Scope 生成文献综述"""

    def __init__(self, storage: JSONStorage | None = None, llm_service: LLMService | None = None):
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

        # 3. 论文数量限制：超过上限时按分数排序截断
        if len(scope.paper_ids) > REVIEW_MAX_PAPERS:
            scope = self._truncate_scope_papers(scope)

        # 4. Collect materials
        materials = self.collect_materials(scope)

        # 5. Check evidence sufficiency
        evidence = materials.get("evidence_records", [])
        if len(evidence) < 2:
            return self._insufficient_evidence_report(project_id, scope, len(evidence))

        # 6. Build evidence matrix
        matrix = self._build_evidence_matrix(evidence, materials.get("paper_cards", []))

        # 7. Generate content
        sections, overall_limitations = self._generate_sections(materials, matrix, opts)

        # 8. Render
        content = self._render_review(sections, materials)

        # 9. Build section_sources
        section_sources = {}
        for s in sections:
            section_sources[s["section_id"]] = {
                "paper_ids": s.get("paper_ids", []),
                "evidence_ids": s.get("evidence_ids", []),
            }

        # 10. Validate
        validation = self._validate_review(sections, scope, materials)

        # 11. Build report
        report = Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.LITERATURE_REVIEW,
            title=f"文献综述 - {scope.summary}",
            content=content,
            scope={
                **scope.model_dump(),
                "section_sources": section_sources,
                "validation_result": validation,
                "overall_limitations": overall_limitations,
            },
            paper_ids=scope.paper_ids,
            evidence_ids=scope.evidence_ids,
        )

        self.storage.upsert_item("reports", report.report_id, report.model_dump())
        logger.info(
            f"Generated literature review: {report.report_id} "
            f"(papers={len(scope.paper_ids)}, evidence={len(evidence)}, "
            f"source_coverage={validation.get('source_coverage', 0):.2f})"
        )
        return report

    # ── 论文数量限制 ───────────────────────────────

    @staticmethod
    def _paper_score(paper: dict) -> float:
        """论文综合得分 = 0.6 * relevance + 0.4 * quality"""
        rel = paper.get("relevance_score", 0.0) or 0.0
        qual = paper.get("quality_score", 0.0) or 0.0
        return 0.6 * rel + 0.4 * qual

    def _truncate_scope_papers(self, scope: RetrievalScope) -> RetrievalScope:
        """当 scope 论文超过上限时，按本地/联网分组排序截断。

        本地论文（upload/bibtex/doi）最多 REVIEW_LOCAL_MAX 篇，
        联网论文（arxiv/openalex/semantic_scholar 等）最多 REVIEW_REMOTE_MAX 篇，
        本地不足时联网补上，总数不超过 REVIEW_MAX_PAPERS。
        """
        local_platforms = {"upload", "bibtex", "doi", "ris"}

        # 加载论文元数据，按来源分组
        local_papers: list[tuple[str, float]] = []  # (paper_id, score)
        remote_papers: list[tuple[str, float]] = []

        for pid in scope.paper_ids:
            p = self.storage.get_item("papers", pid)
            if not p:
                continue
            score = self._paper_score(p)
            platform = (p.get("source_platform") or "").lower()
            if platform in local_platforms:
                local_papers.append((pid, score))
            else:
                remote_papers.append((pid, score))

        # 按分数降序排序
        local_papers.sort(key=lambda x: x[1], reverse=True)
        remote_papers.sort(key=lambda x: x[1], reverse=True)

        # 选取：本地最多 LOCAL_MAX，剩余名额给联网
        selected_local = [pid for pid, _ in local_papers[:REVIEW_LOCAL_MAX]]
        remaining = REVIEW_MAX_PAPERS - len(selected_local)
        selected_remote = [pid for pid, _ in remote_papers[:remaining]]

        selected = selected_local + selected_remote
        logger.info(
            f"Paper truncation: {len(scope.paper_ids)} total -> "
            f"{len(selected_local)} local + {len(selected_remote)} remote = {len(selected)} selected"
        )

        original_count = len(scope.paper_ids)
        scope.paper_ids = selected
        scope.metadata["truncated"] = True
        scope.metadata["original_paper_count"] = original_count
        return scope

    # ── 材料收集 ──────────────────────────────────

    def collect_materials(self, scope: RetrievalScope) -> dict[str, Any]:
        """收集 scope 内所有材料"""
        evidence = self.scope_service.to_evidence_records(scope)
        paper_cards = self.scope_service.to_paper_cards(scope)

        # Paper 元数据
        papers_meta = []
        for pid in scope.paper_ids:
            p = self.storage.get_item("papers", pid)
            if p:
                papers_meta.append(p)

        # Graph context
        graph_context = self.scope_service.to_graph_context(scope)

        return {
            "scope_summary": scope.summary,
            "paper_count": len(scope.paper_ids),
            "paper_ids": scope.paper_ids,
            "evidence_records": evidence,
            "paper_cards": paper_cards,
            "papers_meta": papers_meta,
            "graph_context": graph_context,
        }

    # ── Evidence Matrix ───────────────────────────

    def _build_evidence_matrix(
        self, evidence: list[EvidenceRecord], cards: list[dict]
    ) -> dict[str, Any]:
        """构建结构化证据矩阵"""
        by_topic: dict[str, list] = {}
        by_method: dict[str, list] = {}
        findings = []
        limitations = []
        future_works = []

        for ev in evidence:
            ev_dict = ev.model_dump() if hasattr(ev, "model_dump") else ev

            # Skip empty/unknown
            claim = ev_dict.get("finding", "") or ev_dict.get("limitation", "") or ""
            if not claim or claim == "unknown":
                continue

            # 分类
            if ev_dict.get("finding") and ev_dict["finding"] != "unknown":
                findings.append(ev_dict)
            if ev_dict.get("limitation") and ev_dict["limitation"] != "unknown":
                limitations.append(ev_dict)
            if ev_dict.get("future_work") and ev_dict["future_work"] != "unknown":
                future_works.append(ev_dict)

            # 按 topic 分组
            topic = ev_dict.get("topic", "") or "未分类"
            by_topic.setdefault(topic, []).append(ev_dict)

            # 按 method 分组
            method = ev_dict.get("method", "") or "unknown"
            if method != "unknown":
                by_method.setdefault(method, []).append(ev_dict)

        return {
            "by_topic": by_topic,
            "by_method": by_method,
            "findings": findings,
            "limitations": limitations,
            "future_works": future_works,
        }

    # ── 生成 ──────────────────────────────────────

    def _generate_sections(
        self, materials: dict, matrix: dict, options: dict
    ) -> tuple[list[dict], str]:
        """生成各章节"""
        evidence = materials.get("evidence_records", [])
        cards = materials.get("paper_cards", [])

        # 构建 prompt 输入
        evidence_text = self._build_evidence_text(evidence)
        cards_text = self._build_cards_text(cards)
        matrix_text = self._build_matrix_text(matrix)

        user_prompt = f"""范围：{materials['scope_summary']}
论文数量：{materials['paper_count']}

证据矩阵（按主题分组）：
{matrix_text}

论文卡片：
{cards_text}

证据详情：
{evidence_text}

请生成结构化的文献综述，输出 JSON。每个章节必须标注使用的 evidence_ids。"""

        try:
            result = self.llm.invoke_json(REVIEW_SYSTEM_PROMPT, user_prompt)
            sections = result.get("sections", [])
            overall_limitations = result.get("overall_limitations", "")

            # 验证 sections 有必需章节
            section_ids = {s.get("section_id", "") for s in sections}
            if not (_REQUIRED_SECTIONS & section_ids):
                logger.warning("LLM output missing required sections, using fallback")
                return self._generate_fallback_sections(materials, matrix)

            return sections, overall_limitations

        except Exception as e:
            logger.error(f"LLM review generation failed: {e}")
            return self._generate_fallback_sections(materials, matrix)

    def _generate_fallback_sections(
        self, materials: dict, matrix: dict
    ) -> tuple[list[dict], str]:
        """LLM 失败时的降级生成"""
        evidence = materials.get("evidence_records", [])
        sections = []

        # Background
        sections.append({
            "section_id": "background",
            "title": "研究背景",
            "content": f"本综述基于 {materials['paper_count']} 篇论文的证据进行分析。",
            "paper_ids": materials.get("paper_ids", [])[:5],
            "evidence_ids": [],
        })

        # Findings
        findings = matrix.get("findings", [])
        if findings:
            lines = []
            eids = []
            for f in findings[:8]:
                fid = f.get("evidence_id", "")
                text = f.get("finding", "")
                pid = f.get("paper_id", "")
                if text and text != "unknown":
                    lines.append(f"- {text} [{pid}]")
                    if fid:
                        eids.append(fid)
            sections.append({
                "section_id": "findings",
                "title": "主要研究发现",
                "content": "\n".join(lines),
                "paper_ids": list({f.get("paper_id", "") for f in findings[:8] if f.get("paper_id")}),
                "evidence_ids": eids,
            })

        # Limitations
        limitations = matrix.get("limitations", [])
        if limitations:
            lines = []
            eids = []
            for l in limitations[:8]:
                lid = l.get("evidence_id", "")
                text = l.get("limitation", "")
                pid = l.get("paper_id", "")
                if text and text != "unknown":
                    lines.append(f"- {text} [{pid}]")
                    if lid:
                        eids.append(lid)
            sections.append({
                "section_id": "limitations",
                "title": "研究不足",
                "content": "\n".join(lines),
                "paper_ids": list({l.get("paper_id", "") for l in limitations[:8] if l.get("paper_id")}),
                "evidence_ids": eids,
            })

        # Methods
        by_method = matrix.get("by_method", {})
        if by_method:
            lines = []
            for method, ev_list in by_method.items():
                pids = list({e.get("paper_id", "") for e in ev_list if e.get("paper_id")})
                lines.append(f"- {method}: {len(ev_list)} 条证据, 涉及 {len(pids)} 篇论文")
            sections.append({
                "section_id": "methods",
                "title": "主要研究方法",
                "content": "\n".join(lines),
                "paper_ids": materials.get("paper_ids", [])[:5],
                "evidence_ids": [],
            })

        # Future trends
        future_works = matrix.get("future_works", [])
        if future_works:
            lines = [f"- {fw.get('future_work', '')}" for fw in future_works[:5] if fw.get("future_work", "") != "unknown"]
            sections.append({
                "section_id": "future_trends",
                "title": "未来研究趋势",
                "content": "\n".join(lines) if lines else "当前证据不足以总结未来趋势。",
                "paper_ids": [],
                "evidence_ids": [fw.get("evidence_id", "") for fw in future_works[:5] if fw.get("evidence_id")],
            })

        overall_limitations = "本综述基于规则提取生成，未经过 LLM 深度分析。"
        return sections, overall_limitations

    # ── 渲染 ──────────────────────────────────────

    def _render_review(self, sections: list[dict], materials: dict) -> str:
        """渲染为 Markdown"""
        parts = []
        parts.append("# 文献综述\n")
        parts.append(f"**生成范围**: {materials['scope_summary']}")
        parts.append(f"**使用论文数量**: {materials['paper_count']}\n")

        for s in sections:
            title = s.get("title", "未命名章节")
            content = s.get("content", "")
            eids = s.get("evidence_ids", [])
            pids = s.get("paper_ids", [])

            parts.append(f"\n## {title}\n")
            parts.append(content)

            # 来源标记
            source_parts = []
            if eids:
                source_parts.append(f"证据: {', '.join(eids[:5])}")
            if pids:
                source_parts.append(f"论文: {', '.join(pids[:5])}")
            if source_parts:
                parts.append(f"\n[{'; '.join(source_parts)}]")

        # 参考文献
        parts.append("\n\n## 参考文献\n")
        papers_meta = materials.get("papers_meta", [])
        for p in papers_meta:
            pid = p.get("paper_id", "")
            title = p.get("title", "N/A")
            identifiers = p.get("identifiers", {})
            dates = p.get("dates", {})
            source = p.get("source", {})
            authors_raw = p.get("authors", [])
            author_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors_raw]
            authors = ", ".join(author_names[:3])
            year = dates.get("year", "")
            venue = source.get("venue", "")
            doi = identifiers.get("doi", "")
            ref = f"- [{pid}] {authors} ({year}). {title}."
            if venue:
                ref += f" {venue}."
            if doi:
                ref += f" DOI: {doi}"
            parts.append(ref)

        return "\n".join(parts)

    # ── 校验 ──────────────────────────────────────

    def _validate_review(
        self, sections: list[dict], scope: RetrievalScope, materials: dict
    ) -> dict[str, Any]:
        """校验综述质量"""
        issues = []
        warnings = []

        # 结构完整性
        section_ids = {s.get("section_id", "") for s in sections}
        missing = _REQUIRED_SECTIONS - section_ids
        if missing:
            issues.append({"type": "missing_sections", "sections": list(missing)})

        # 来源覆盖率
        sections_with_evidence = sum(1 for s in sections if s.get("evidence_ids"))
        source_coverage = sections_with_evidence / len(sections) if sections else 0

        # Scope 校验
        allowed_papers = set(scope.paper_ids)
        allowed_evidence = set(scope.evidence_ids)
        scope_violations = []
        for s in sections:
            for pid in s.get("paper_ids", []):
                if pid and pid not in allowed_papers:
                    scope_violations.append({"type": "paper_out_of_scope", "id": pid, "section": s.get("section_id")})
            for eid in s.get("evidence_ids", []):
                if eid and eid not in allowed_evidence:
                    scope_violations.append({"type": "evidence_out_of_scope", "id": eid, "section": s.get("section_id")})

        # 泛化套话检测
        all_content = " ".join(s.get("content", "") for s in sections)
        generic_hits = [p for p in _GENERIC_PHRASES if p in all_content]

        # 参考文献覆盖率
        used_papers = set()
        for s in sections:
            used_papers.update(s.get("paper_ids", []))
        ref_coverage = len(used_papers & allowed_papers) / len(allowed_papers) if allowed_papers else 0

        return {
            "valid": len(issues) == 0 and len(scope_violations) == 0,
            "issues": issues,
            "warnings": warnings,
            "source_coverage": source_coverage,
            "scope_violations": scope_violations,
            "generic_text_hits": generic_hits,
            "reference_coverage": ref_coverage,
            "section_count": len(sections),
        }

    # ── 空范围/证据不足 ──────────────────────────

    def _empty_scope_report(self, project_id: str, scope: RetrievalScope, empty_reason: str) -> Report:
        messages = {
            "no_included_papers": "当前项目没有已纳入的论文，无法生成综述。",
            "no_valid_selected_papers": "选中的论文均无效，无法生成综述。",
            "no_matching_topic": "当前范围内没有匹配所选主题的论文。",
            "no_matching_method": "当前范围内没有匹配所选方法的论文。",
        }
        content = f"# 文献综述\n\n**无法生成**: {messages.get(empty_reason, '当前范围为空。')}\n"
        return Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.LITERATURE_REVIEW,
            title=f"文献综述 - {scope.summary}",
            content=content,
            scope={**scope.model_dump(), "empty_reason": empty_reason},
            paper_ids=[],
            evidence_ids=[],
        )

    def _insufficient_evidence_report(self, project_id: str, scope: RetrievalScope, evidence_count: int) -> Report:
        content = (
            f"# 文献综述\n\n"
            f"**生成范围**: {scope.summary}\n"
            f"**无法生成**: 当前范围内仅有 {evidence_count} 条证据，不足以生成可靠综述。\n\n"
            f"建议：\n"
            f"- 先为论文生成卡片和证据表\n"
            f"- 扩大选择范围\n"
            f"- 导入更多论文\n"
        )
        return Report(
            report_id=f"report_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            type=ReportType.LITERATURE_REVIEW,
            title=f"文献综述 - {scope.summary}",
            content=content,
            scope=scope.model_dump(),
            paper_ids=scope.paper_ids,
            evidence_ids=scope.evidence_ids,
        )

    # ── 上下文构建 ──────────────────────────────

    def _build_evidence_text(self, evidence: list[EvidenceRecord]) -> str:
        parts = []
        for e in evidence[:30]:
            e_dict = e.model_dump() if hasattr(e, "model_dump") else e
            eid = e_dict.get("evidence_id", "?")
            pid = e_dict.get("paper_id", "?")
            part = f"[{eid}] 论文 {pid}"
            if e_dict.get("topic"):
                part += f" | 主题:{e_dict['topic']}"
            if e_dict.get("method") and e_dict["method"] != "unknown":
                part += f" | 方法:{e_dict['method']}"
            if e_dict.get("finding") and e_dict["finding"] != "unknown":
                part += f" | 发现:{e_dict['finding'][:80]}"
            if e_dict.get("limitation") and e_dict["limitation"] != "unknown":
                part += f" | 局限:{e_dict['limitation'][:80]}"
            if e_dict.get("source_quote"):
                part += f" | 引用:{e_dict['source_quote'][:60]}"
            parts.append(part)
        return "\n".join(parts) if parts else "无证据"

    def _build_cards_text(self, cards: list[dict]) -> str:
        parts = []
        for c in cards[:15]:
            pid = c.get("paper_id", "?")
            part = f"[{pid}] {c.get('title', '未知')}"
            if c.get("method") and c["method"] != "unknown":
                part += f" | 方法:{c['method']}"
            if c.get("research_question") and c["research_question"] != "unknown":
                part += f" | 问题:{c['research_question'][:50]}"
            parts.append(part)
        return "\n".join(parts) if parts else "无卡片"

    def _build_matrix_text(self, matrix: dict) -> str:
        """将 evidence matrix 渲染为紧凑文本"""
        parts = []
        for topic, ev_list in matrix.get("by_topic", {}).items():
            pids = list({e.get("paper_id", "") for e in ev_list if e.get("paper_id")})
            findings = [e.get("finding", "")[:50] for e in ev_list if e.get("finding", "") not in ("", "unknown")]
            parts.append(f"主题:{topic} | 论文:{','.join(pids[:5])} | 发现数:{len(findings)}")
        return "\n".join(parts) if parts else "无分组信息"

    # ── 兼容旧接口 ──────────────────────────────

    def validate_review(self, report: Report) -> dict[str, Any]:
        """兼容旧接口"""
        issues = []
        if not report.scope:
            issues.append("缺少 scope")
        if not report.paper_ids:
            issues.append("缺少 paper_ids")
        if not report.evidence_ids:
            issues.append("缺少 evidence_ids")
        return {"valid": len(issues) == 0, "issues": issues}
