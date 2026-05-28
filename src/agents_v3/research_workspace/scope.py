"""Retrieval Scope 解析服务"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    KnowledgeGraph,
    RetrievalScope,
    ScopeType,
)
from src.agents_v3.research_workspace.storage import get_storage


class RetrievalScopeService:
    """解析和管理 QA 检索范围"""

    def __init__(self):
        self.storage = get_storage()

    def resolve(self, project_id: str, scope_payload: dict[str, Any]) -> RetrievalScope:
        scope_type = ScopeType(scope_payload.get("type", "all_project"))

        scope = RetrievalScope(
            scope_type=scope_type,
            project_id=project_id,
        )

        if scope_type == ScopeType.ALL_PROJECT:
            papers = self.storage.query("papers", {"project_id": project_id, "included": True})
            scope.paper_ids = [p["paper_id"] for p in papers]

        elif scope_type == ScopeType.SELECTED_PAPERS:
            scope.paper_ids = scope_payload.get("selected_paper_ids", [])

        elif scope_type == ScopeType.TOPIC_GROUP:
            topic_ids = scope_payload.get("selected_topic_ids", [])
            scope.topic_ids = topic_ids
            # Find papers with these topics
            scope.paper_ids = self._find_papers_by_topics(project_id, topic_ids)

        elif scope_type == ScopeType.METHOD_GROUP:
            method_ids = scope_payload.get("selected_method_ids", [])
            scope.method_ids = method_ids
            scope.paper_ids = self._find_papers_by_methods(project_id, method_ids)

        elif scope_type == ScopeType.GRAPH_SUBGRAPH:
            node_ids = scope_payload.get("selected_graph_node_ids", [])
            hops = scope_payload.get("graph_hops", 1)
            scope.graph_node_ids = node_ids
            scope.paper_ids = self._find_papers_by_graph_nodes(project_id, node_ids, hops)

        elif scope_type == ScopeType.YEAR_RANGE:
            time_range = scope_payload.get("time_range", [])
            scope.time_range = time_range
            scope.paper_ids = self._find_papers_by_year_range(project_id, time_range)

        # Apply time range filter if specified
        if scope_payload.get("time_range") and scope_type not in (ScopeType.YEAR_RANGE,):
            time_range = scope_payload["time_range"]
            scope.paper_ids = self._filter_by_year(scope.paper_ids, time_range)

        # Get evidence records
        scope.evidence_ids = self._get_evidence_ids(project_id, scope.paper_ids, scope.topic_ids)

        # Build summary
        scope.summary = self.summarize(scope)

        logger.info(f"Resolved scope: {scope.summary}")
        return scope

    def to_paper_ids(self, scope: RetrievalScope) -> list[str]:
        return scope.paper_ids

    def to_evidence_records(self, scope: RetrievalScope) -> list[EvidenceRecord]:
        if scope.evidence_ids:
            records = []
            for eid in scope.evidence_ids:
                item = self.storage.get_item("evidence_records", eid)
                if item:
                    records.append(EvidenceRecord(**item))
            return records

        # Fallback: query by project
        all_evidence = self.storage.query("evidence_records", {"project_id": scope.project_id})
        records = [EvidenceRecord(**e) for e in all_evidence]

        if scope.paper_ids:
            records = [r for r in records if r.paper_id in scope.paper_ids]
        if scope.topic_ids:
            records = [r for r in records if r.topic in scope.topic_ids]

        return records

    def to_graph_context(self, scope: RetrievalScope) -> dict[str, Any]:
        graphs = self.storage.load_collection(f"graph_{scope.project_id}")
        if not graphs:
            return {"nodes": [], "edges": []}

        graph = KnowledgeGraph(**graphs[0])

        if scope.graph_node_ids:
            # Return subgraph around selected nodes
            from src.agents_v3.research_workspace.graph_service import GraphService
            gs = GraphService()
            return gs.get_subgraph(scope.project_id, scope.graph_node_ids, hops=1)

        # Filter by paper_ids
        paper_node_ids = {f"paper:{pid}" for pid in scope.paper_ids}
        nodes = [n for n in graph.nodes if n.node_id in paper_node_ids]
        edges = [e for e in graph.edges if e.source_id in paper_node_ids or e.target_id in paper_node_ids]

        return {
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump() for e in edges],
        }

    def summarize(self, scope: RetrievalScope) -> str:
        parts = [f"项目 {scope.project_id}"]

        if scope.scope_type == ScopeType.ALL_PROJECT:
            parts.append("全项目论文")
        elif scope.scope_type == ScopeType.SELECTED_PAPERS:
            parts.append(f"选中 {len(scope.paper_ids)} 篇论文")
        elif scope.scope_type == ScopeType.TOPIC_GROUP:
            parts.append(f"主题: {', '.join(scope.topic_ids)}")
        elif scope.scope_type == ScopeType.METHOD_GROUP:
            parts.append(f"方法: {', '.join(scope.method_ids)}")
        elif scope.scope_type == ScopeType.GRAPH_SUBGRAPH:
            parts.append(f"图谱子图 ({len(scope.graph_node_ids)} 个节点)")
        elif scope.scope_type == ScopeType.YEAR_RANGE:
            parts.append(f"年份范围: {scope.time_range}")

        if scope.time_range and scope.scope_type != ScopeType.YEAR_RANGE:
            parts.append(f"年份: {scope.time_range[0]}-{scope.time_range[-1]}")

        return "，".join(parts)

    def _find_papers_by_topics(self, project_id: str, topic_ids: list[str]) -> list[str]:
        evidence = self.storage.query("evidence_records", {"project_id": project_id})
        paper_ids = set()
        for e in evidence:
            if e.get("topic") in topic_ids:
                paper_ids.add(e["paper_id"])
        return list(paper_ids)

    def _find_papers_by_methods(self, project_id: str, method_ids: list[str]) -> list[str]:
        evidence = self.storage.query("evidence_records", {"project_id": project_id})
        paper_ids = set()
        for e in evidence:
            if e.get("method") in method_ids:
                paper_ids.add(e["paper_id"])
        return list(paper_ids)

    def _find_papers_by_graph_nodes(self, project_id: str, node_ids: list[str], hops: int) -> list[str]:
        graphs = self.storage.load_collection(f"graph_{project_id}")
        if not graphs:
            return []

        graph = KnowledgeGraph(**graphs[0])
        from src.agents_v3.research_workspace.graph_service import GraphService
        gs = GraphService()
        subgraph = gs.get_subgraph(project_id, node_ids, hops)

        paper_ids = set()
        for n in subgraph["nodes"]:
            if n["node_type"] == "Paper":
                pid = n["node_id"].replace("paper:", "")
                paper_ids.add(pid)

        return list(paper_ids)

    def _find_papers_by_year_range(self, project_id: str, time_range: list[str]) -> list[str]:
        if len(time_range) < 2:
            return []
        min_year, max_year = int(time_range[0]), int(time_range[1])
        papers = self.storage.query("papers", {"project_id": project_id})
        return [
            p["paper_id"] for p in papers
            if p.get("year") and min_year <= p["year"] <= max_year
        ]

    def _filter_by_year(self, paper_ids: list[str], time_range: list[str]) -> list[str]:
        if len(time_range) < 2:
            return paper_ids
        min_year, max_year = int(time_range[0]), int(time_range[1])
        result = []
        for pid in paper_ids:
            paper = self.storage.get_item("papers", pid)
            if paper and paper.get("year") and min_year <= paper["year"] <= max_year:
                result.append(pid)
        return result

    def _get_evidence_ids(self, project_id: str, paper_ids: list[str], topic_ids: list[str]) -> list[str]:
        evidence = self.storage.query("evidence_records", {"project_id": project_id})
        result = []
        for e in evidence:
            if paper_ids and e.get("paper_id") not in paper_ids:
                continue
            if topic_ids and e.get("topic") not in topic_ids:
                continue
            result.append(e["evidence_id"])
        return result
