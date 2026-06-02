"""Retrieval Scope 解析服务 - 增强版"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    RetrievalScope,
    ScopeType,
)
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage
from src.agents_v3.research_workspace.utils import normalize_label


def _split_multi(text: str) -> set[str]:
    """拆分多值字段（逗号、分号、顿号），返回归一化 set"""
    parts = re.split(r"[,;、/]", text)
    return {normalize_label(p) for p in parts if p.strip() and p.strip().lower() not in ("unknown", "n/a", "")}


class RetrievalScopeService:
    """解析和管理 QA 检索范围"""

    def __init__(self, storage: JSONStorage | None = None):
        self.storage = storage or get_storage()

    def _get_project_paper_ids(self, project_id: str) -> list[str]:
        """获取项目下所有 paper_id"""
        papers = self.storage.query("papers", {"project_id": project_id})
        return [p.get("paper_id", "") for p in papers]

    def resolve(self, project_id: str, scope_payload: dict[str, Any]) -> RetrievalScope:
        scope_type = ScopeType(scope_payload.get("type", "all_project"))
        warnings: list[str] = []
        empty_reason = ""
        suggested_actions: list[str] = []
        invalid_selection: list[dict] = []
        explain: dict[str, Any] = {"papers": {}, "evidence": {}}

        # 获取项目 included 论文索引
        all_papers = self.storage.query("papers", {"project_id": project_id})
        included_papers = {p["paper_id"]: p for p in all_papers if p.get("included", True)}
        included_ids = set(included_papers.keys())

        scope = RetrievalScope(
            scope_type=scope_type,
            project_id=project_id,
        )

        # ── 按类型解析基础范围 ──────────────────────

        if scope_type == ScopeType.ALL_PROJECT:
            scope.paper_ids = sorted(included_ids)
            if not scope.paper_ids:
                empty_reason = "no_included_papers"
                suggested_actions = ["import_papers", "reinclude_excluded"]

        elif scope_type == ScopeType.SELECTED_PAPERS:
            selected = scope_payload.get("selected_paper_ids", [])
            scope.paper_ids, invalid_selection = self._validate_selected_papers(
                project_id, selected, included_papers
            )
            if not scope.paper_ids:
                empty_reason = "no_valid_selected_papers"
                suggested_actions = ["select_included_papers"]

        elif scope_type == ScopeType.TOPIC_GROUP:
            topic_ids = scope_payload.get("selected_topic_ids", [])
            scope.topic_ids = topic_ids
            scope.paper_ids = self._find_papers_by_topics(
                project_id, topic_ids, included_ids
            )
            if not scope.paper_ids:
                empty_reason = "no_matching_topic"
                suggested_actions = ["try_different_topics", "clear_topic_filter"]

        elif scope_type == ScopeType.METHOD_GROUP:
            method_ids = scope_payload.get("selected_method_ids", [])
            scope.method_ids = method_ids
            scope.paper_ids = self._find_papers_by_methods(
                project_id, method_ids, included_ids
            )
            if not scope.paper_ids:
                empty_reason = "no_matching_method"
                suggested_actions = ["try_different_methods", "clear_method_filter"]

        elif scope_type == ScopeType.GRAPH_SUBGRAPH:
            node_ids = scope_payload.get("selected_graph_node_ids", [])
            scope.graph_node_ids = node_ids
            hops = self._clamp_hops(scope_payload.get("graph_hops", 1), warnings)
            scope.paper_ids = self._find_papers_by_graph_nodes(
                project_id, node_ids, hops, included_ids
            )
            if not scope.paper_ids:
                empty_reason = "no_matching_graph_subgraph"
                suggested_actions = ["build_knowledge_graph", "select_different_nodes"]

        elif scope_type == ScopeType.YEAR_RANGE:
            time_range = scope_payload.get("time_range", [])
            scope.time_range = time_range
            scope.paper_ids = self._find_papers_by_year_range(
                project_id, time_range, included_ids
            )
            if not scope.paper_ids:
                if not time_range or len(time_range) < 2:
                    empty_reason = "invalid_time_range"
                    suggested_actions = ["provide_valid_year_range"]
                else:
                    empty_reason = "no_papers_after_year_filter"
                    suggested_actions = ["expand_year_range"]

        # ── 交叉过滤 ──────────────────────────────

        # Topic 过滤（非 topic_group 类型时）
        if scope_payload.get("selected_topic_ids") and scope_type != ScopeType.TOPIC_GROUP:
            filter_topics = scope_payload["selected_topic_ids"]
            scope.paper_ids = self._filter_papers_by_topics(
                scope.paper_ids, filter_topics
            )

        # Method 过滤（非 method_group 类型时）
        if scope_payload.get("selected_method_ids") and scope_type != ScopeType.METHOD_GROUP:
            filter_methods = scope_payload["selected_method_ids"]
            scope.paper_ids = self._filter_papers_by_methods(
                scope.paper_ids, filter_methods
            )

        # Year 过滤（非 year_range 类型时）
        if scope_payload.get("time_range") and scope_type != ScopeType.YEAR_RANGE:
            scope.paper_ids = self._filter_by_year(
                scope.paper_ids, scope_payload["time_range"]
            )

        # ── 解析 evidence_ids ──────────────────────

        if scope.paper_ids:
            scope.evidence_ids = self._get_evidence_ids(
                project_id, scope.paper_ids, scope.topic_ids, scope.method_ids
            )
        else:
            scope.evidence_ids = []

        # ── Build explain ──────────────────────────

        for pid in scope.paper_ids:
            paper = included_papers.get(pid, {})
            explain["papers"][pid] = {
                "included_by": self._explain_paper_inclusion(pid, scope, scope_payload),
                "title": paper.get("title", ""),
            }

        for eid in scope.evidence_ids:
            ev = self.storage.get_item("evidence_records", eid)
            if ev:
                explain["evidence"][eid] = {
                    "included_by": f"paper:{ev.get('paper_id', '')}",
                    "source_quote_available": bool(ev.get("source_quote")),
                }

        # ── Build summary ──────────────────────────

        scope.summary = self.summarize(scope)

        logger.info(
            f"Resolved scope: {scope.summary} "
            f"(papers={len(scope.paper_ids)}, evidence={len(scope.evidence_ids)})"
        )

        # 附加诊断信息到 scope metadata
        scope.metadata = {
            "empty_reason": empty_reason,
            "warnings": warnings,
            "suggested_actions": suggested_actions,
            "invalid_selection": invalid_selection,
            "explain": explain,
        }

        return scope

    # ── 论文验证 ──────────────────────────────────

    def _validate_selected_papers(
        self,
        project_id: str,
        selected_ids: list[str],
        included_papers: dict[str, dict],
    ) -> tuple[list[str], list[dict]]:
        """验证选中的论文：存在、属于项目、included"""
        valid = []
        invalid = []
        seen = set()

        for pid in selected_ids:
            if pid in seen:
                continue
            seen.add(pid)

            paper = self.storage.get_item("papers", pid)
            if not paper:
                invalid.append({"id": pid, "reason": "not_found"})
                continue
            if paper.get("project_id") != project_id:
                invalid.append({"id": pid, "reason": "project_mismatch"})
                continue
            if not paper.get("included", True):
                invalid.append({"id": pid, "reason": "excluded"})
                continue
            valid.append(pid)

        return sorted(valid), invalid

    # ── Topic/Method 查找 ────────────────────────

    def _find_papers_by_topics(
        self, project_id: str, topic_ids: list[str], included_ids: set[str]
    ) -> list[str]:
        if not topic_ids:
            return []
        normalized_targets = {normalize_label(t) for t in topic_ids}

        # 优先从图谱 Topic 节点解析
        graph_papers = self._find_papers_from_graph_topics(project_id, normalized_targets)
        if graph_papers:
            return sorted(graph_papers & included_ids)

        # Fallback 到 evidence
        paper_ids_proj = self._get_project_paper_ids(project_id)
        evidence = self.storage.query("evidence_records", {"paper_id": paper_ids_proj}) if paper_ids_proj else []
        paper_ids: set[str] = set()
        for e in evidence:
            if e.get("paper_id") not in included_ids:
                continue
            ev_topics = _split_multi(e.get("topic", ""))
            if ev_topics & normalized_targets:
                paper_ids.add(e["paper_id"])
        return sorted(paper_ids)

    def _find_papers_from_graph_topics(self, project_id: str, targets: set[str]) -> set[str]:
        """从图谱 Topic 节点找相关论文"""
        from src.agents_v3.research_workspace.services.graph_service import GraphService
        gs = GraphService(storage=self.storage)
        graph = gs.get_graph(project_id)
        if not graph.nodes:
            return set()

        paper_ids: set[str] = set()
        for node in graph.nodes:
            if node.node_type.value != "Topic":
                continue
            norm = normalize_label(node.label)
            if norm in targets or any(t in norm for t in targets):
                paper_ids.update(node.properties.get("paper_ids", []))
        return paper_ids

    def _find_papers_by_methods(
        self, project_id: str, method_ids: list[str], included_ids: set[str]
    ) -> list[str]:
        if not method_ids:
            return []
        normalized_targets = {normalize_label(m) for m in method_ids}

        paper_ids_proj = self._get_project_paper_ids(project_id)
        evidence = self.storage.query("evidence_records", {"paper_id": paper_ids_proj}) if paper_ids_proj else []
        paper_ids: set[str] = set()
        for e in evidence:
            if e.get("paper_id") not in included_ids:
                continue
            ev_methods = _split_multi(e.get("method", ""))
            if ev_methods & normalized_targets:
                paper_ids.add(e["paper_id"])
        return sorted(paper_ids)

    def _find_papers_by_graph_nodes(
        self, project_id: str, node_ids: list[str], hops: int, included_ids: set[str]
    ) -> list[str]:
        from src.agents_v3.research_workspace.services.graph_service import GraphService
        gs = GraphService(storage=self.storage)
        subgraph = gs.get_subgraph(project_id, node_ids, hops=hops)

        paper_ids: set[str] = set()
        for pid in subgraph.get("related_paper_ids", []):
            if pid in included_ids:
                paper_ids.add(pid)

        # Fallback: 从节点 properties 提取
        if not paper_ids:
            for n in subgraph.get("nodes", []):
                if n.get("node_type") == "Paper":
                    pid = n.get("node_id", "").replace("paper:", "")
                    if pid in included_ids:
                        paper_ids.add(pid)
                for pid in n.get("properties", {}).get("paper_ids", []):
                    if pid in included_ids:
                        paper_ids.add(pid)

        return sorted(paper_ids)

    def _find_papers_by_year_range(
        self, project_id: str, time_range: list[str], included_ids: set[str]
    ) -> list[str]:
        if len(time_range) < 2:
            return []
        try:
            min_year, max_year = int(time_range[0]), int(time_range[1])
        except (ValueError, IndexError):
            return []
        if min_year > max_year:
            min_year, max_year = max_year, min_year

        papers = self.storage.query("papers", {"project_id": project_id})
        return sorted(
            p["paper_id"] for p in papers
            if p.get("paper_id") in included_ids
            and (p.get("dates") or {}).get("year")
            and min_year <= p["dates"]["year"] <= max_year
        )

    # ── 交叉过滤 ──────────────────────────────────

    def _filter_papers_by_topics(self, paper_ids: list[str], topic_ids: list[str]) -> list[str]:
        if not topic_ids:
            return paper_ids
        normalized_targets = {normalize_label(t) for t in topic_ids}
        evidence = self.storage.query("evidence_records", {})
        matching_pids: set[str] = set()
        for e in evidence:
            if e.get("paper_id") not in paper_ids:
                continue
            ev_topics = _split_multi(e.get("topic", ""))
            if ev_topics & normalized_targets:
                matching_pids.add(e["paper_id"])
        return sorted(matching_pids)

    def _filter_papers_by_methods(self, paper_ids: list[str], method_ids: list[str]) -> list[str]:
        if not method_ids:
            return paper_ids
        normalized_targets = {normalize_label(m) for m in method_ids}
        evidence = self.storage.query("evidence_records", {})
        matching_pids: set[str] = set()
        for e in evidence:
            if e.get("paper_id") not in paper_ids:
                continue
            ev_methods = _split_multi(e.get("method", ""))
            if ev_methods & normalized_targets:
                matching_pids.add(e["paper_id"])
        return sorted(matching_pids)

    def _filter_by_year(self, paper_ids: list[str], time_range: list[str]) -> list[str]:
        if len(time_range) < 2:
            return paper_ids
        try:
            min_year, max_year = int(time_range[0]), int(time_range[1])
        except (ValueError, IndexError):
            return paper_ids
        result = []
        for pid in paper_ids:
            paper = self.storage.get_item("papers", pid)
            year = (paper.get("dates") or {}).get("year")
            if paper and year and min_year <= year <= max_year:
                result.append(pid)
        return result

    # ── Evidence 解析 ────────────────────────────

    def _get_evidence_ids(
        self, project_id: str, paper_ids: list[str],
        topic_ids: list[str], method_ids: list[str],
    ) -> list[str]:
        paper_ids_proj = self._get_project_paper_ids(project_id)
        evidence = self.storage.query("evidence_records", {"paper_id": paper_ids_proj}) if paper_ids_proj else []
        paper_set = set(paper_ids)
        result = []
        for e in evidence:
            if e.get("paper_id") not in paper_set:
                continue
            result.append(e["evidence_id"])
        return sorted(result)

    # ── 工具方法 ──────────────────────────────────

    def _clamp_hops(self, hops: int, warnings: list[str]) -> int:
        if hops < 0:
            return 0
        if hops > 2:
            warnings.append(f"graph_hops {hops} clamped to 2")
            return 2
        return hops

    def _explain_paper_inclusion(
        self, paper_id: str, scope: RetrievalScope, payload: dict
    ) -> list[str]:
        reasons = []
        if scope.scope_type == ScopeType.ALL_PROJECT:
            reasons.append("all_project")
        if paper_id in (payload.get("selected_paper_ids") or []):
            reasons.append("selected")
        if scope.topic_ids:
            reasons.append(f"topic:{','.join(scope.topic_ids[:3])}")
        if scope.method_ids:
            reasons.append(f"method:{','.join(scope.method_ids[:3])}")
        if scope.time_range:
            reasons.append(f"year:{scope.time_range[0]}-{scope.time_range[-1]}")
        if scope.graph_node_ids:
            reasons.append("graph_subgraph")
        return reasons

    # ── 公开查询方法 ──────────────────────────────

    def to_paper_ids(self, scope: RetrievalScope) -> list[str]:
        return scope.paper_ids

    def to_evidence_records(self, scope: RetrievalScope) -> list[EvidenceRecord]:
        """严格返回 scope.evidence_ids 内的记录，禁止空 scope fallback"""
        if not scope.paper_ids and scope.metadata.get("empty_reason"):
            return []

        if scope.evidence_ids:
            records = []
            for eid in scope.evidence_ids:
                item = self.storage.get_item("evidence_records", eid)
                if item:
                    records.append(EvidenceRecord(**item))
            return records

        # Fallback: 用 paper_ids 过滤
        paper_ids_proj = self._get_project_paper_ids(scope.project_id)
        all_evidence = self.storage.query("evidence_records", {"paper_id": paper_ids_proj}) if paper_ids_proj else []
        paper_set = set(scope.paper_ids)
        records = [EvidenceRecord(**e) for e in all_evidence if e.get("paper_id") in paper_set]

        if scope.topic_ids:
            topic_set = {normalize_label(t) for t in scope.topic_ids}
            records = [r for r in records if _split_multi(r.topic) & topic_set]
        if scope.method_ids:
            method_set = {normalize_label(m) for m in scope.method_ids}
            records = [r for r in records if _split_multi(r.method) & method_set]

        return records

    def to_paper_cards(self, scope: RetrievalScope, max_cards: int = 50) -> list[dict]:
        """获取 scope 内的 paper cards"""
        cards = []
        for pid in scope.paper_ids[:max_cards]:
            items = self.storage.query("paper_cards", {"paper_id": pid, "active": True})
            cards.extend(items)
        return cards

    def to_graph_context(self, scope: RetrievalScope, hops: int = 1) -> dict[str, Any]:
        from src.agents_v3.research_workspace.services.graph_service import GraphService
        gs = GraphService(storage=self.storage)

        if scope.graph_node_ids:
            return gs.get_subgraph(scope.project_id, scope.graph_node_ids, hops=min(hops, 2))

        # 非 graph scope: 返回 paper 相关节点
        graph = gs.get_graph(scope.project_id)
        paper_node_ids = {f"paper:{pid}" for pid in scope.paper_ids}
        nodes = [n for n in graph.nodes if n.node_id in paper_node_ids]
        edges = [e for e in graph.edges if e.source_id in paper_node_ids or e.target_id in paper_node_ids]

        return {
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump() for e in edges],
            "related_paper_ids": scope.paper_ids,
            "related_evidence_ids": scope.evidence_ids,
        }

    def build_scope_guard(self, scope: RetrievalScope) -> dict[str, Any]:
        """构建 ScopeGuard 白名单"""
        return {
            "project_id": scope.project_id,
            "allowed_paper_ids": set(scope.paper_ids),
            "allowed_evidence_ids": set(scope.evidence_ids),
            "allowed_graph_node_ids": set(scope.graph_node_ids),
            "allow_empty": bool(scope.metadata.get("empty_reason")),
        }

    def validate_against_scope(
        self, guard: dict[str, Any], refs: dict[str, list[str]]
    ) -> dict[str, Any]:
        """校验引用是否越界"""
        violations = []
        allowed_papers = guard.get("allowed_paper_ids", set())
        allowed_evidence = guard.get("allowed_evidence_ids", set())

        for pid in refs.get("paper_ids", []):
            if pid not in allowed_papers:
                violations.append({"kind": "paper", "id": pid, "reason": "out_of_scope"})

        for eid in refs.get("evidence_ids", []):
            if eid not in allowed_evidence:
                violations.append({"kind": "evidence", "id": eid, "reason": "out_of_scope"})

        return {
            "valid": len(violations) == 0,
            "scope_leak_count": len(violations),
            "violations": violations,
        }

    def get_scope_filters(self, project_id: str) -> dict[str, Any]:
        """获取前端可选范围"""
        all_papers = self.storage.query("papers", {"project_id": project_id})
        included = [p for p in all_papers if p.get("included", True)]
        paper_ids = {p["paper_id"] for p in included}

        # Papers
        papers = [
            {"id": p["paper_id"], "title": p.get("title", ""), "year": (p.get("dates") or {}).get("year"), "included": True}
            for p in included
        ]

        # Topics from graph or evidence
        from src.agents_v3.research_workspace.services.graph_service import GraphService
        gs = GraphService(storage=self.storage)
        graph = gs.get_graph(project_id)

        topics: list[dict] = []
        methods: list[dict] = []
        if graph.nodes:
            for n in graph.nodes:
                if n.node_type.value == "Topic":
                    topics.append({
                        "id": n.node_id, "label": n.label,
                        "paper_count": len(n.properties.get("paper_ids", [])),
                    })
                elif n.node_type.value == "Method":
                    methods.append({
                        "id": n.node_id, "label": n.label,
                        "paper_count": len(n.properties.get("paper_ids", [])),
                    })
        else:
            # Fallback to evidence
            paper_ids_proj = self._get_project_paper_ids(project_id)
            evidence = self.storage.query("evidence_records", {"paper_id": paper_ids_proj}) if paper_ids_proj else []
            topic_counts: dict[str, int] = {}
            method_counts: dict[str, int] = {}
            for e in evidence:
                if e.get("paper_id") not in paper_ids:
                    continue
                for t in _split_multi(e.get("topic", "")):
                    topic_counts[t] = topic_counts.get(t, 0) + 1
                for m in _split_multi(e.get("method", "")):
                    method_counts[m] = method_counts.get(m, 0) + 1
            topics = [{"id": t, "label": t, "paper_count": c} for t, c in topic_counts.items()]
            methods = [{"id": m, "label": m, "paper_count": c} for m, c in method_counts.items()]

        # Years
        year_counts: dict[int, int] = {}
        for p in included:
            y = (p.get("dates") or {}).get("year")
            if y:
                year_counts[y] = year_counts.get(y, 0) + 1
        years = [{"year": y, "paper_count": c} for y, c in sorted(year_counts.items())]

        return {
            "papers": papers,
            "topics": sorted(topics, key=lambda t: -t.get("paper_count", 0)),
            "methods": sorted(methods, key=lambda m: -m.get("paper_count", 0)),
            "years": years,
        }

    def summarize(self, scope: RetrievalScope) -> str:
        parts = [f"项目 {scope.project_id}"]

        if scope.scope_type == ScopeType.ALL_PROJECT:
            parts.append("全项目论文")
        elif scope.scope_type == ScopeType.SELECTED_PAPERS:
            parts.append(f"选中 {len(scope.paper_ids)} 篇论文")
        elif scope.scope_type == ScopeType.TOPIC_GROUP:
            parts.append(f"主题: {', '.join(scope.topic_ids[:3])}")
        elif scope.scope_type == ScopeType.METHOD_GROUP:
            parts.append(f"方法: {', '.join(scope.method_ids[:3])}")
        elif scope.scope_type == ScopeType.GRAPH_SUBGRAPH:
            parts.append(f"图谱子图 ({len(scope.graph_node_ids)} 个节点)")
        elif scope.scope_type == ScopeType.YEAR_RANGE:
            parts.append(f"年份范围: {scope.time_range}")

        parts.append(f"包含 {len(scope.paper_ids)} 篇论文、{len(scope.evidence_ids)} 条证据")
        return "，".join(parts)
