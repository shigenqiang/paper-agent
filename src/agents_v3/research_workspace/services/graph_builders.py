"""知识图谱构建 Mixin — 全量/增量构建、节点/边创建"""

from __future__ import annotations

import re

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EdgeType,
    EvidenceRecord,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
)
from src.agents_v3.research_workspace.utils import normalize_label, stable_hash

from .graph_utils import (
    classify_limitation_type,
    compute_gap_confidence,
    resolve_alias,
)


class GraphBuilderMixin:
    """图谱构建：全量构建、增量更新、节点/边创建辅助"""

    def build_project_graph(self, project_id: str, force: bool = False) -> KnowledgeGraph:
        """全量构建项目知识图谱"""
        from src.agents_v3.research_workspace.evaluation.logging_utils import log_operation
        with log_operation("graph.build", project_id=project_id, force=force):
            return self._build_project_graph_impl(project_id, force)

    def _build_project_graph_impl(self, project_id: str, force: bool = False) -> KnowledgeGraph:
        """全量构建项目知识图谱（实际实现）"""
        papers_data = self.storage.query("papers", {"project_id": project_id})
        included_paper_ids = {p["paper_id"] for p in papers_data if p.get("included", True)}
        paper_ids = list(included_paper_ids)

        evidence_data = self.storage.query("evidence_records", {"paper_id": paper_ids}) if paper_ids else []
        evidence_records = [EvidenceRecord(**e) for e in evidence_data]

        cards_data = self.storage.query("paper_cards", {"paper_id": paper_ids, "is_active": True}) if paper_ids else []

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        for p in papers_data:
            if not p.get("included", True):
                continue
            pid = p["paper_id"]
            node_id = f"paper:{pid}"

            # 从 papers_pool 获取完整元数据
            pool = self.storage.get_item("papers_pool", pid) or {}
            identifiers = pool.get("identifiers") or p.get("identifiers") or {}
            identifiers = identifiers if isinstance(identifiers, dict) else {}
            dates = pool.get("dates") or p.get("dates") or {}
            dates = dates if isinstance(dates, dict) else {}
            source = pool.get("source") or p.get("source") or {}
            source = source if isinstance(source, dict) else {}
            title = pool.get("title", "") or p.get("title", "") or pid
            authors_raw = pool.get("authors") or p.get("authors") or []
            authors_raw = authors_raw if isinstance(authors_raw, list) else []
            author_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors_raw]
            year = pool.get("year") or dates.get("year")
            doi = pool.get("doi", "") or identifiers.get("doi", "")
            venue = pool.get("venue", "") or source.get("venue", "")

            nodes[node_id] = GraphNode(
                node_id=node_id,
                node_type=NodeType.PAPER,
                label=title[:80],
                properties={
                    "paper_ids": [pid],
                    "evidence_ids": [],
                    "title": title,
                    "authors": author_names,
                    "year": year,
                    "doi": doi,
                    "venue": venue,
                    "included": True,
                },
            )

        for ev in evidence_records:
            paper_node_id = f"paper:{ev.paper_id}"
            self._ensure_paper_node(nodes, ev.paper_id)

            if ev.topic:
                for topic in self._split_multi(ev.topic):
                    self._add_topic_node(nodes, edges, paper_node_id, topic, ev)

            if ev.method and ev.method.lower() not in ("unknown", ""):
                for method in self._split_multi(ev.method):
                    self._add_method_node(nodes, edges, paper_node_id, method, ev)

            if ev.research_question and ev.research_question.lower() not in ("unknown", ""):
                self._add_task_node(nodes, edges, paper_node_id, ev.research_question, ev)

            if ev.data_or_sample and ev.data_or_sample.lower() not in ("unknown", ""):
                self._add_dataset_node(nodes, edges, paper_node_id, ev.data_or_sample, ev)

            if ev.finding and ev.finding.lower() not in ("unknown", ""):
                self._add_finding_node(nodes, edges, paper_node_id, ev)

            if ev.limitation and ev.limitation.lower() not in ("unknown", ""):
                self._add_limitation_node(nodes, edges, paper_node_id, ev)

        for card in cards_data:
            # 完整卡片数据在 extraction JSONB 字段中
            card_content = card.get("extraction", card) if isinstance(card.get("extraction"), dict) else card
            pid = card_content.get("paper_id", "")
            paper_node_id = f"paper:{pid}"
            for gap_text in card_content.get("possible_gaps", []):
                if gap_text and gap_text.lower() != "unknown":
                    self._add_gap_candidate_from_text(nodes, edges, paper_node_id, pid, gap_text, "possible_gap")
            for fw_text in card_content.get("future_work", []):
                if fw_text and fw_text.lower() != "unknown":
                    self._add_gap_candidate_from_text(nodes, edges, paper_node_id, pid, fw_text, "future_work")

        self._build_from_sections(nodes, edges, paper_ids)
        self._build_author_nodes(nodes, edges, papers_data)
        self._build_venue_nodes(nodes, edges, papers_data)
        self._build_cites_edges(nodes, edges, papers_data, paper_ids)
        self._aggregate_gaps(nodes, edges, evidence_records)

        graph = KnowledgeGraph(
            project_id=project_id,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )

        self._save_graph(project_id, graph)

        logger.info(f"Built graph for {project_id}: {len(nodes)} nodes, {len(edges)} edges")
        return graph

    def incremental_update(
        self, project_id: str, new_paper_ids: list[str],
    ) -> KnowledgeGraph:
        """增量更新：只处理新增论文，合并到现有图谱"""
        if not new_paper_ids:
            return self.get_graph(project_id)

        existing_graph = self.get_graph(project_id)
        existing_node_map = {n.node_id: n for n in existing_graph.nodes}
        existing_edge_map = {e.edge_id: e for e in existing_graph.edges}

        new_papers_data = self.storage.query("papers", {"paper_id": new_paper_ids})
        new_paper_id_set = set(new_paper_ids)

        evidence_data = self.storage.query("evidence_records", {"paper_id": new_paper_ids})
        evidence_records = [EvidenceRecord(**e) for e in evidence_data]

        cards_data = self.storage.query("paper_cards", {"paper_id": new_paper_ids, "is_active": True})

        new_nodes: dict[str, GraphNode] = {}
        new_edges: dict[str, GraphEdge] = {}

        for p in new_papers_data:
            if not p.get("included", True):
                continue
            pid = p["paper_id"]
            node_id = f"paper:{pid}"
            identifiers = p.get("identifiers", {})
            dates = p.get("dates", {})
            source = p.get("source", {})
            authors_raw = p.get("authors", [])
            author_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors_raw]
            new_nodes[node_id] = GraphNode(
                node_id=node_id,
                node_type=NodeType.PAPER,
                label=p.get("title", pid)[:80],
                properties={
                    "paper_ids": [pid],
                    "evidence_ids": [],
                    "title": p.get("title", ""),
                    "authors": author_names,
                    "year": dates.get("year"),
                    "doi": identifiers.get("doi", ""),
                    "venue": source.get("venue", ""),
                    "included": True,
                },
            )

        for ev in evidence_records:
            paper_node_id = f"paper:{ev.paper_id}"
            self._ensure_paper_node(new_nodes, ev.paper_id)
            if ev.topic:
                for topic in self._split_multi(ev.topic):
                    self._add_topic_node(new_nodes, new_edges, paper_node_id, topic, ev)
            if ev.method and ev.method.lower() not in ("unknown", ""):
                for method in self._split_multi(ev.method):
                    self._add_method_node(new_nodes, new_edges, paper_node_id, method, ev)
            if ev.research_question and ev.research_question.lower() not in ("unknown", ""):
                self._add_task_node(new_nodes, new_edges, paper_node_id, ev.research_question, ev)
            if ev.data_or_sample and ev.data_or_sample.lower() not in ("unknown", ""):
                self._add_dataset_node(new_nodes, new_edges, paper_node_id, ev.data_or_sample, ev)
            if ev.finding and ev.finding.lower() not in ("unknown", ""):
                self._add_finding_node(new_nodes, new_edges, paper_node_id, ev)
            if ev.limitation and ev.limitation.lower() not in ("unknown", ""):
                self._add_limitation_node(new_nodes, new_edges, paper_node_id, ev)

        for card in cards_data:
            card_content = card.get("extraction", card) if isinstance(card.get("extraction"), dict) else card
            pid = card_content.get("paper_id", "")
            paper_node_id = f"paper:{pid}"
            for gap_text in card_content.get("possible_gaps", []):
                if gap_text and gap_text.lower() != "unknown":
                    self._add_gap_candidate_from_text(new_nodes, new_edges, paper_node_id, pid, gap_text, "possible_gap")
            for fw_text in card_content.get("future_work", []):
                if fw_text and fw_text.lower() != "unknown":
                    self._add_gap_candidate_from_text(new_nodes, new_edges, paper_node_id, pid, fw_text, "future_work")

        self._build_from_sections(new_nodes, new_edges, new_paper_ids)
        self._build_author_nodes(new_nodes, new_edges, new_papers_data)
        self._build_venue_nodes(new_nodes, new_edges, new_papers_data)
        self._build_cites_edges(new_nodes, new_edges, new_papers_data, new_paper_ids)
        self._aggregate_gaps(new_nodes, new_edges, evidence_records)

        for nid, node in new_nodes.items():
            if nid in existing_node_map:
                for key in ("paper_ids", "evidence_ids", "source_chunk_ids", "source_quotes"):
                    for item in node.properties.get(key, []):
                        if item not in existing_node_map[nid].properties.get(key, []):
                            existing_node_map[nid].properties.setdefault(key, []).append(item)
            else:
                existing_node_map[nid] = node

        for eid, edge in new_edges.items():
            if eid in existing_edge_map:
                for key in ("paper_ids", "evidence_ids", "source_chunk_ids"):
                    for item in edge.properties.get(key, []):
                        if item not in existing_edge_map[eid].properties.get(key, []):
                            existing_edge_map[eid].properties.setdefault(key, []).append(item)
            else:
                existing_edge_map[eid] = edge

        graph = KnowledgeGraph(
            project_id=project_id,
            nodes=list(existing_node_map.values()),
            edges=list(existing_edge_map.values()),
        )
        self._save_graph(project_id, graph)

        logger.info(
            f"Incremental update for {project_id}: "
            f"added {len(new_nodes)} nodes, {len(new_edges)} edges. "
            f"Total: {len(existing_node_map)} nodes, {len(existing_edge_map)} edges"
        )
        return graph

    def remove_paper(self, project_id: str, paper_id: str) -> KnowledgeGraph:
        """移除论文及其孤立节点/边"""
        graph = self.get_graph(project_id)
        paper_node_id = f"paper:{paper_id}"

        # 1. 从所有节点的 paper_ids 中移除该 paper
        nodes_to_remove: set[str] = set()
        for node in graph.nodes:
            pids = node.properties.get("paper_ids", [])
            if paper_id in pids:
                pids.remove(paper_id)
                if node.node_id == paper_node_id:
                    nodes_to_remove.add(node.node_id)
                elif not pids and node.node_type != NodeType.COMMUNITY:
                    nodes_to_remove.add(node.node_id)

        # 2. 移除关联边
        edges_to_remove: set[str] = set()
        for edge in graph.edges:
            if edge.source_id in nodes_to_remove or edge.target_id in nodes_to_remove:
                edges_to_remove.add(edge.edge_id)
            elif paper_id in edge.properties.get("paper_ids", []):
                edge.properties["paper_ids"].remove(paper_id)

        # 3. 过滤
        graph.nodes = [n for n in graph.nodes if n.node_id not in nodes_to_remove]
        graph.edges = [e for e in graph.edges if e.edge_id not in edges_to_remove]

        self._save_graph(project_id, graph)
        logger.info(
            f"remove_paper({project_id}, {paper_id}): "
            f"removed {len(nodes_to_remove)} nodes, {len(edges_to_remove)} edges"
        )
        return graph

    # ── 节点构建辅助 ──────────────────────────────

    def _ensure_paper_node(self, nodes: dict[str, GraphNode], paper_id: str) -> None:
        node_id = f"paper:{paper_id}"
        if node_id not in nodes:
            pool = self.storage.get_item("papers_pool", paper_id) or {}
            title = pool.get("title", "") or paper_id
            authors_raw = pool.get("authors", []) or []
            author_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors_raw]
            nodes[node_id] = GraphNode(
                node_id=node_id,
                node_type=NodeType.PAPER,
                label=title[:80],
                properties={
                    "paper_ids": [paper_id],
                    "evidence_ids": [],
                    "title": title,
                    "authors": author_names,
                    "year": pool.get("year"),
                    "doi": pool.get("doi", ""),
                    "venue": pool.get("venue", ""),
                },
            )

    def _add_topic_node(
        self, nodes: dict, edges: dict, paper_node_id: str, topic: str, ev: EvidenceRecord
    ) -> None:
        normalized = resolve_alias(normalize_label(topic))
        if not normalized:
            return
        topic_id = f"topic:{stable_hash(normalized)}"

        if topic_id not in nodes:
            nodes[topic_id] = GraphNode(
                node_id=topic_id,
                node_type=NodeType.TOPIC,
                label=topic.strip()[:50],
                properties={
                    "normalized_label": normalized,
                    "paper_ids": [],
                    "evidence_ids": [],
                    "source_chunk_ids": [],
                    "source_quotes": [],
                },
            )
        node = nodes[topic_id]
        self._merge_provenance(node, ev)

        edge_id = f"edge:BELONGS_TO_TOPIC:{stable_hash(paper_node_id)}:{stable_hash(topic_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id,
                source_id=paper_node_id,
                target_id=topic_id,
                edge_type=EdgeType.BELONGS_TO_TOPIC,
            )
        self._merge_edge_provenance(edges[edge_id], ev)

    def _add_method_node(
        self, nodes: dict, edges: dict, paper_node_id: str, method: str, ev: EvidenceRecord
    ) -> None:
        normalized = resolve_alias(normalize_label(method))
        if not normalized:
            return
        method_id = f"method:{stable_hash(normalized)}"

        if method_id not in nodes:
            nodes[method_id] = GraphNode(
                node_id=method_id,
                node_type=NodeType.METHOD,
                label=method.strip()[:50],
                properties={
                    "normalized_label": normalized,
                    "paper_ids": [],
                    "evidence_ids": [],
                    "source_chunk_ids": [],
                    "source_quotes": [],
                },
            )
        self._merge_provenance(nodes[method_id], ev)

        edge_id = f"edge:USES_METHOD:{stable_hash(paper_node_id)}:{stable_hash(method_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id,
                source_id=paper_node_id,
                target_id=method_id,
                edge_type=EdgeType.USES_METHOD,
            )
        self._merge_edge_provenance(edges[edge_id], ev)

    def _add_task_node(
        self, nodes: dict, edges: dict, paper_node_id: str, research_question: str, ev: EvidenceRecord
    ) -> None:
        if not research_question or research_question.strip().lower() in ("", "unknown", "n/a"):
            return
        for rq in self._split_multi(research_question):
            normalized = resolve_alias(normalize_label(rq))
            if not normalized:
                continue
            task_id = f"task:{stable_hash(normalized)}"

            if task_id not in nodes:
                nodes[task_id] = GraphNode(
                    node_id=task_id,
                    node_type=NodeType.TASK,
                    label=rq.strip()[:50],
                    properties={
                        "normalized_label": normalized,
                        "paper_ids": [],
                        "evidence_ids": [],
                        "source_chunk_ids": [],
                        "source_quotes": [],
                    },
                )
            self._merge_provenance(nodes[task_id], ev)

            edge_id = f"edge:STUDIES_TASK:{stable_hash(paper_node_id)}:{stable_hash(task_id)}"
            if edge_id not in edges:
                edges[edge_id] = GraphEdge(
                    edge_id=edge_id,
                    source_id=paper_node_id,
                    target_id=task_id,
                    edge_type=EdgeType.STUDIES_TASK,
                )
            self._merge_edge_provenance(edges[edge_id], ev)

    def _add_dataset_node(
        self, nodes: dict, edges: dict, paper_node_id: str, data_or_sample: str, ev: EvidenceRecord
    ) -> None:
        normalized = normalize_label(data_or_sample)[:60]
        if not normalized:
            return
        dataset_id = f"dataset:{stable_hash(normalized)}"

        if dataset_id not in nodes:
            nodes[dataset_id] = GraphNode(
                node_id=dataset_id,
                node_type=NodeType.DATASET,
                label=data_or_sample.strip()[:50],
                properties={
                    "normalized_label": normalized,
                    "paper_ids": [],
                    "evidence_ids": [],
                    "source_chunk_ids": [],
                    "source_quotes": [],
                },
            )
        self._merge_provenance(nodes[dataset_id], ev)

        edge_id = f"edge:USES_DATASET:{stable_hash(paper_node_id)}:{stable_hash(dataset_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id,
                source_id=paper_node_id,
                target_id=dataset_id,
                edge_type=EdgeType.USES_DATASET,
            )
        self._merge_edge_provenance(edges[edge_id], ev)

    def _add_finding_node(
        self, nodes: dict, edges: dict, paper_node_id: str, ev: EvidenceRecord
    ) -> None:
        claim = ev.finding.strip()
        normalized = normalize_label(claim)[:80]
        finding_id = f"finding:{stable_hash(normalized)}"

        if finding_id not in nodes:
            nodes[finding_id] = GraphNode(
                node_id=finding_id,
                node_type=NodeType.FINDING,
                label=claim[:50],
                properties={
                    "normalized_label": normalized,
                    "claim": claim,
                    "paper_ids": [],
                    "evidence_ids": [],
                    "source_chunk_ids": [],
                    "source_quotes": [],
                    "evidence_strength": ev.evidence_strength,
                },
            )
        self._merge_provenance(nodes[finding_id], ev)

        edge_id = f"edge:REPORTS_FINDING:{stable_hash(paper_node_id)}:{stable_hash(finding_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id,
                source_id=paper_node_id,
                target_id=finding_id,
                edge_type=EdgeType.REPORTS_FINDING,
            )
        self._merge_edge_provenance(edges[edge_id], ev)

    def _add_limitation_node(
        self, nodes: dict, edges: dict, paper_node_id: str, ev: EvidenceRecord
    ) -> None:
        claim = ev.limitation.strip()
        normalized = normalize_label(claim)[:80]
        limit_id = f"limitation:{stable_hash(normalized)}"

        if limit_id not in nodes:
            ltype = classify_limitation_type(claim)
            nodes[limit_id] = GraphNode(
                node_id=limit_id,
                node_type=NodeType.LIMITATION,
                label=claim[:50],
                properties={
                    "normalized_label": normalized,
                    "claim": claim,
                    "limitation_type": ltype,
                    "paper_ids": [],
                    "evidence_ids": [],
                    "source_chunk_ids": [],
                    "source_quotes": [],
                    "evidence_strength": ev.evidence_strength,
                },
            )
        self._merge_provenance(nodes[limit_id], ev)

        edge_id = f"edge:HAS_LIMITATION:{stable_hash(paper_node_id)}:{stable_hash(limit_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id,
                source_id=paper_node_id,
                target_id=limit_id,
                edge_type=EdgeType.HAS_LIMITATION,
            )
        self._merge_edge_provenance(edges[edge_id], ev)

    def _add_gap_candidate_from_text(
        self, nodes: dict, edges: dict, paper_node_id: str, paper_id: str, text: str, source_type: str
    ) -> None:
        normalized = normalize_label(text)[:80]
        if not normalized:
            return
        gap_id = f"gap:{stable_hash(normalized)}"

        if gap_id not in nodes:
            nodes[gap_id] = GraphNode(
                node_id=gap_id,
                node_type=NodeType.GAP,
                label=text.strip()[:50],
                properties={
                    "normalized_label": normalized,
                    "gap_statement": text.strip(),
                    "source_types": [],
                    "supporting_evidence_ids": [],
                    "supporting_paper_ids": [],
                    "supporting_limitation_ids": [],
                    "confidence": 0.0,
                    "status": "candidate",
                },
            )
        node = nodes[gap_id]
        props = node.properties
        if source_type not in props.get("source_types", []):
            props.setdefault("source_types", []).append(source_type)
        if paper_id not in props.get("supporting_paper_ids", []):
            props.setdefault("supporting_paper_ids", []).append(paper_id)

    def _build_from_sections(
        self, nodes: dict, edges: dict, paper_ids: list[str]
    ) -> None:
        """从 paper_sections 的 JSONB 提取结果构建节点和边"""
        if not paper_ids:
            return
        sections = self.storage.query("paper_sections", {"paper_id": paper_ids})
        if not sections:
            return

        # 按 paper_id 索引 evidence records，用于边的可追溯性
        ev_records = self.storage.query("evidence_records", {"paper_id": paper_ids})
        ev_by_paper: dict[str, list[dict]] = {}
        for ev in ev_records:
            pid = ev.get("paper_id", "")
            if pid:
                ev_by_paper.setdefault(pid, []).append(ev)

        for section in sections:
            if section.get("extraction_status") != "done":
                continue

            pid = section.get("paper_id", "")
            paper_node_id = f"paper:{pid}"
            self._ensure_paper_node(nodes, pid)

            entities = section.get("entities", [])
            relations = section.get("relations", [])
            claims = section.get("claims", [])

            for entity in entities:
                etype = (entity.get("type") or "").strip()
                name = (entity.get("name") or "").strip()
                if not name or not etype:
                    continue
                description = entity.get("description", "")

                if etype == "Method":
                    self._add_method_node_from_section(nodes, edges, paper_node_id, name, description, section)
                elif etype == "Dataset":
                    self._add_dataset_node_from_section(nodes, edges, paper_node_id, name, description, section)
                elif etype == "Task":
                    self._add_task_node_from_section(nodes, edges, paper_node_id, name, description, section)
                elif etype == "Finding":
                    self._add_finding_node_from_section(nodes, edges, paper_node_id, name, description, section)
                elif etype == "Limitation":
                    self._add_limitation_node_from_section(nodes, edges, paper_node_id, name, description, section)
                elif etype == "Topic":
                    self._add_topic_node_from_section(nodes, edges, paper_node_id, name, description, section)
                elif etype == "Metric":
                    self._add_metric_node_from_section(nodes, edges, paper_node_id, name, description, section)

            entity_name_to_id: dict[str, str] = {}
            for entity in entities:
                name = (entity.get("name") or "").strip().lower()
                etype = (entity.get("type") or "").strip()
                if name and etype:
                    entity_name_to_id[name] = f"{etype.lower()}:{stable_hash(resolve_alias(normalize_label(name)))}"

            for rel in relations:
                self._add_relation_edge(nodes, edges, rel, entity_name_to_id, paper_node_id, section)

            for claim in claims:
                claim_text = (claim.get("claim") or "").strip()
                if claim_text and claim_text.lower() not in ("unknown", "n/a"):
                    self._add_finding_node_from_section(
                        nodes, edges, paper_node_id, claim_text,
                        claim.get("evidence_quote", ""), section,
                    )

        # 统一为所有 section 来源的边关联 evidence_id（paper_id 级关联）
        if ev_by_paper:
            for edge in edges.values():
                for pid in edge.properties.get("paper_ids", []):
                    if pid in ev_by_paper:
                        edge_ev = edge.properties.setdefault("evidence_ids", [])
                        for ev in ev_by_paper[pid]:
                            ev_id = ev.get("evidence_id", "")
                            if ev_id and ev_id not in edge_ev:
                                edge_ev.append(ev_id)

    # ── Section 来源的节点构建辅助 ──────────────────

    def _add_method_node_from_section(
        self, nodes: dict, edges: dict, paper_node_id: str,
        method: str, description: str, section: dict,
    ) -> None:
        normalized = resolve_alias(normalize_label(method))
        if not normalized:
            return
        method_id = f"method:{stable_hash(normalized)}"
        if method_id not in nodes:
            nodes[method_id] = GraphNode(
                node_id=method_id, node_type=NodeType.METHOD,
                label=method.strip()[:50],
                properties={
                    "normalized_label": normalized, "description": description,
                    "paper_ids": [], "evidence_ids": [],
                    "source_chunk_ids": [], "source_quotes": [],
                },
            )
        node = nodes[method_id]
        pid = section.get("paper_id", "")
        if pid not in node.properties.get("paper_ids", []):
            node.properties.setdefault("paper_ids", []).append(pid)
        chunk_ids = section.get("chunk_ids", [])
        for cid in chunk_ids:
            if cid not in node.properties.get("source_chunk_ids", []):
                node.properties.setdefault("source_chunk_ids", []).append(cid)

        edge_id = f"edge:USES_METHOD:{stable_hash(paper_node_id)}:{stable_hash(method_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id, source_id=paper_node_id,
                target_id=method_id, edge_type=EdgeType.USES_METHOD,
            )
        if pid not in edges[edge_id].properties.get("paper_ids", []):
            edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    def _add_dataset_node_from_section(
        self, nodes: dict, edges: dict, paper_node_id: str,
        dataset: str, description: str, section: dict,
    ) -> None:
        normalized = resolve_alias(normalize_label(dataset))[:60]
        if not normalized:
            return
        dataset_id = f"dataset:{stable_hash(normalized)}"
        if dataset_id not in nodes:
            nodes[dataset_id] = GraphNode(
                node_id=dataset_id, node_type=NodeType.DATASET,
                label=dataset.strip()[:50],
                properties={
                    "normalized_label": normalized, "description": description,
                    "paper_ids": [], "evidence_ids": [],
                    "source_chunk_ids": [], "source_quotes": [],
                },
            )
        node = nodes[dataset_id]
        pid = section.get("paper_id", "")
        if pid not in node.properties.get("paper_ids", []):
            node.properties.setdefault("paper_ids", []).append(pid)

        edge_id = f"edge:USES_DATASET:{stable_hash(paper_node_id)}:{stable_hash(dataset_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id, source_id=paper_node_id,
                target_id=dataset_id, edge_type=EdgeType.USES_DATASET,
            )
        if pid not in edges[edge_id].properties.get("paper_ids", []):
            edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    def _add_task_node_from_section(
        self, nodes: dict, edges: dict, paper_node_id: str,
        task: str, description: str, section: dict,
    ) -> None:
        normalized = resolve_alias(normalize_label(task))
        if not normalized:
            return
        task_id = f"task:{stable_hash(normalized)}"
        if task_id not in nodes:
            nodes[task_id] = GraphNode(
                node_id=task_id, node_type=NodeType.TASK,
                label=task.strip()[:50],
                properties={
                    "normalized_label": normalized, "description": description,
                    "paper_ids": [], "evidence_ids": [],
                    "source_chunk_ids": [], "source_quotes": [],
                },
            )
        node = nodes[task_id]
        pid = section.get("paper_id", "")
        if pid not in node.properties.get("paper_ids", []):
            node.properties.setdefault("paper_ids", []).append(pid)

        edge_id = f"edge:STUDIES_TASK:{stable_hash(paper_node_id)}:{stable_hash(task_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id, source_id=paper_node_id,
                target_id=task_id, edge_type=EdgeType.STUDIES_TASK,
            )
        if pid not in edges[edge_id].properties.get("paper_ids", []):
            edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    def _add_finding_node_from_section(
        self, nodes: dict, edges: dict, paper_node_id: str,
        name: str, description: str, section: dict,
    ) -> None:
        claim = name.strip()
        normalized = normalize_label(claim)[:80]
        if not normalized:
            return
        pid = section.get("paper_id", "")
        finding_id = f"finding:{stable_hash(normalized)}"
        if finding_id not in nodes:
            nodes[finding_id] = GraphNode(
                node_id=finding_id, node_type=NodeType.FINDING,
                label=claim[:50],
                properties={
                    "normalized_label": normalized, "claim": claim,
                    "description": description,
                    "paper_ids": [], "evidence_ids": [],
                    "source_chunk_ids": [], "source_quotes": [],
                },
            )
        node = nodes[finding_id]
        if pid not in node.properties.get("paper_ids", []):
            node.properties.setdefault("paper_ids", []).append(pid)

        edge_id = f"edge:REPORTS_FINDING:{stable_hash(paper_node_id)}:{stable_hash(finding_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id, source_id=paper_node_id,
                target_id=finding_id, edge_type=EdgeType.REPORTS_FINDING,
            )
        if pid not in edges[edge_id].properties.get("paper_ids", []):
            edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    def _add_limitation_node_from_section(
        self, nodes: dict, edges: dict, paper_node_id: str,
        name: str, description: str, section: dict,
    ) -> None:
        claim = name.strip()
        normalized = normalize_label(claim)[:80]
        if not normalized:
            return
        pid = section.get("paper_id", "")
        limit_id = f"limitation:{stable_hash(normalized)}"
        if limit_id not in nodes:
            ltype = classify_limitation_type(claim)
            nodes[limit_id] = GraphNode(
                node_id=limit_id, node_type=NodeType.LIMITATION,
                label=claim[:50],
                properties={
                    "normalized_label": normalized, "claim": claim,
                    "limitation_type": ltype, "description": description,
                    "paper_ids": [], "evidence_ids": [],
                    "source_chunk_ids": [], "source_quotes": [],
                },
            )
        node = nodes[limit_id]
        if pid not in node.properties.get("paper_ids", []):
            node.properties.setdefault("paper_ids", []).append(pid)

        edge_id = f"edge:HAS_LIMITATION:{stable_hash(paper_node_id)}:{stable_hash(limit_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id, source_id=paper_node_id,
                target_id=limit_id, edge_type=EdgeType.HAS_LIMITATION,
            )
        if pid not in edges[edge_id].properties.get("paper_ids", []):
            edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    def _add_topic_node_from_section(
        self, nodes: dict, edges: dict, paper_node_id: str,
        topic: str, description: str, section: dict,
    ) -> None:
        normalized = resolve_alias(normalize_label(topic))
        if not normalized:
            return
        topic_id = f"topic:{stable_hash(normalized)}"
        if topic_id not in nodes:
            nodes[topic_id] = GraphNode(
                node_id=topic_id, node_type=NodeType.TOPIC,
                label=topic.strip()[:50],
                properties={
                    "normalized_label": normalized, "description": description,
                    "paper_ids": [], "evidence_ids": [],
                    "source_chunk_ids": [], "source_quotes": [],
                },
            )
        node = nodes[topic_id]
        pid = section.get("paper_id", "")
        if pid not in node.properties.get("paper_ids", []):
            node.properties.setdefault("paper_ids", []).append(pid)

        edge_id = f"edge:BELONGS_TO_TOPIC:{stable_hash(paper_node_id)}:{stable_hash(topic_id)}"
        if edge_id not in edges:
            edges[edge_id] = GraphEdge(
                edge_id=edge_id, source_id=paper_node_id,
                target_id=topic_id, edge_type=EdgeType.BELONGS_TO_TOPIC,
            )
        if pid not in edges[edge_id].properties.get("paper_ids", []):
            edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    def _add_metric_node_from_section(
        self, nodes: dict, edges: dict, paper_node_id: str,
        metric: str, description: str, section: dict,
    ) -> None:
        normalized = resolve_alias(normalize_label(metric))
        if not normalized:
            return
        metric_id = f"metric:{stable_hash(normalized)}"
        if metric_id not in nodes:
            nodes[metric_id] = GraphNode(
                node_id=metric_id, node_type=NodeType.METRIC,
                label=metric.strip()[:50],
                properties={
                    "normalized_label": normalized, "description": description,
                    "paper_ids": [], "evidence_ids": [],
                    "source_chunk_ids": [], "source_quotes": [],
                },
            )
        node = nodes[metric_id]
        pid = section.get("paper_id", "")
        if pid not in node.properties.get("paper_ids", []):
            node.properties.setdefault("paper_ids", []).append(pid)

    # ── Author 节点 + AUTHORED_BY 边 ──────────────────

    def _build_author_nodes(
        self, nodes: dict, edges: dict, papers_data: list[dict],
    ) -> None:
        for p in papers_data:
            if not p.get("included", True):
                continue
            pid = p["paper_id"]
            paper_node_id = f"paper:{pid}"
            authors_raw = p.get("authors", [])

            for author_data in authors_raw:
                if isinstance(author_data, dict):
                    name = author_data.get("name", "").strip()
                else:
                    name = str(author_data).strip()

                if not name or name.lower() in ("unknown", "n/a", ""):
                    continue

                normalized = normalize_label(name)
                if not normalized:
                    continue

                author_id = f"author:{stable_hash(normalized)}"

                if author_id not in nodes:
                    nodes[author_id] = GraphNode(
                        node_id=author_id,
                        node_type=NodeType.AUTHOR,
                        label=name[:50],
                        properties={
                            "normalized_label": normalized,
                            "paper_ids": [],
                            "evidence_ids": [],
                        },
                    )
                node = nodes[author_id]
                if pid not in node.properties.get("paper_ids", []):
                    node.properties.setdefault("paper_ids", []).append(pid)

                edge_id = f"edge:AUTHORED_BY:{stable_hash(paper_node_id)}:{stable_hash(author_id)}"
                if edge_id not in edges:
                    edges[edge_id] = GraphEdge(
                        edge_id=edge_id,
                        source_id=paper_node_id,
                        target_id=author_id,
                        edge_type=EdgeType.AUTHORED_BY,
                    )
                if pid not in edges[edge_id].properties.get("paper_ids", []):
                    edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    # ── Venue 节点 + PUBLISHED_IN 边 ──────────────────

    def _build_venue_nodes(
        self, nodes: dict, edges: dict, papers_data: list[dict],
    ) -> None:
        """从 Paper.venue 构建 Venue 节点 + PUBLISHED_IN 边"""
        for p in papers_data:
            if not p.get("included", True):
                continue
            pid = p["paper_id"]
            venue = (p.get("source", {}).get("venue", "") or "").strip()
            if not venue or venue.lower() in ("unknown", "n/a", ""):
                continue

            normalized = normalize_label(venue)
            if not normalized:
                continue

            venue_id = f"venue:{stable_hash(normalized)}"

            if venue_id not in nodes:
                nodes[venue_id] = GraphNode(
                    node_id=venue_id,
                    node_type=NodeType.VENUE,
                    label=venue[:50],
                    properties={
                        "normalized_label": normalized,
                        "paper_ids": [],
                        "evidence_ids": [],
                    },
                )
            node = nodes[venue_id]
            if pid not in node.properties.get("paper_ids", []):
                node.properties.setdefault("paper_ids", []).append(pid)

            paper_node_id = f"paper:{pid}"
            edge_id = f"edge:PUBLISHED_IN:{stable_hash(paper_node_id)}:{stable_hash(venue_id)}"
            if edge_id not in edges:
                edges[edge_id] = GraphEdge(
                    edge_id=edge_id,
                    source_id=paper_node_id,
                    target_id=venue_id,
                    edge_type=EdgeType.PUBLISHED_IN,
                )
            if pid not in edges[edge_id].properties.get("paper_ids", []):
                edges[edge_id].properties.setdefault("paper_ids", []).append(pid)

    # ── CITES 边 + GhostPaper 节点 ──────────────────

    def _build_cites_edges(
        self, nodes: dict, edges: dict, papers_data: list[dict], paper_ids: list[str],
    ) -> None:
        references = self.storage.load_collection("paper_references")
        if not references:
            return

        doi_to_pid: dict[str, str] = {}
        title_to_pid: dict[str, str] = {}
        for p in papers_data:
            pid = p["paper_id"]
            doi = (p.get("identifiers", {}).get("doi", "") or "").strip().lower()
            if doi:
                doi_to_pid[doi] = pid
            title = normalize_label(p.get("title", ""))
            if title:
                title_to_pid[title] = pid

        ghost_citation_counts: dict[str, int] = {}
        ghost_info: dict[str, dict] = {}

        for ref in references:
            citing_pid = ref.get("citing_paper_id", "")
            if citing_pid not in paper_ids:
                continue

            cited_pid = ""
            ref_doi = (ref.get("doi", "") or "").strip().lower()
            ref_title = normalize_label(ref.get("title", ""))

            if ref_doi and ref_doi in doi_to_pid:
                cited_pid = doi_to_pid[ref_doi]
            elif ref_title and ref_title in title_to_pid:
                cited_pid = title_to_pid[ref_title]

            if cited_pid and cited_pid != citing_pid:
                citing_node_id = f"paper:{citing_pid}"
                cited_node_id = f"paper:{cited_pid}"
                edge_id = f"edge:CITES:{stable_hash(citing_node_id)}:{stable_hash(cited_node_id)}"
                if edge_id not in edges:
                    edges[edge_id] = GraphEdge(
                        edge_id=edge_id,
                        source_id=citing_node_id,
                        target_id=cited_node_id,
                        edge_type=EdgeType.CITES,
                    )
                if citing_pid not in edges[edge_id].properties.get("paper_ids", []):
                    edges[edge_id].properties.setdefault("paper_ids", []).append(citing_pid)
            elif not cited_pid and (ref_doi or ref_title):
                ghost_key = ref_doi if ref_doi else ref_title
                if ghost_key:
                    ghost_citation_counts[ghost_key] = ghost_citation_counts.get(ghost_key, 0) + 1
                    if ghost_key not in ghost_info:
                        ghost_info[ghost_key] = {
                            "title": ref.get("title", ghost_key[:80]),
                            "doi": ref_doi,
                            "authors": ref.get("authors", []),
                            "year": ref.get("year"),
                        }

        for ghost_key, count in ghost_citation_counts.items():
            if count < 2:
                continue

            info = ghost_info.get(ghost_key, {})
            ghost_id = f"ghost:{stable_hash(ghost_key)}"
            if ghost_id in nodes:
                continue

            nodes[ghost_id] = GraphNode(
                node_id=ghost_id,
                node_type=NodeType.GHOST_PAPER,
                label=(info.get("title", "") or ghost_key)[:50],
                properties={
                    "paper_ids": [],
                    "evidence_ids": [],
                    "cited_by_count": count,
                    "doi": info.get("doi", ""),
                    "year": info.get("year"),
                    "source": "reference_extraction",
                },
            )

            for ref in references:
                citing_pid = ref.get("citing_paper_id", "")
                if citing_pid not in paper_ids:
                    continue
                ref_doi = (ref.get("doi", "") or "").strip().lower()
                ref_title = normalize_label(ref.get("title", ""))
                match_key = ref_doi if ref_doi else ref_title
                if match_key == ghost_key:
                    citing_node_id = f"paper:{citing_pid}"
                    edge_id = f"edge:CITES:{stable_hash(citing_node_id)}:{stable_hash(ghost_id)}"
                    if edge_id not in edges:
                        edges[edge_id] = GraphEdge(
                            edge_id=edge_id,
                            source_id=citing_node_id,
                            target_id=ghost_id,
                            edge_type=EdgeType.CITES,
                        )

        cite_count = sum(1 for e in edges.values() if e.edge_type == EdgeType.CITES)
        ghost_count = sum(1 for n in nodes.values() if n.node_type == NodeType.GHOST_PAPER)
        logger.info(f"Citation network: {cite_count} CITES edges, {ghost_count} GhostPaper nodes")

    def _add_relation_edge(
        self, nodes: dict, edges: dict, rel: dict,
        entity_name_to_id: dict[str, str], paper_node_id: str, section: dict,
    ) -> None:
        source_name = (rel.get("source_name") or "").strip().lower()
        target_name = (rel.get("target_name") or "").strip().lower()
        rel_type = (rel.get("type") or "").strip().upper()

        if not source_name or not target_name or not rel_type:
            return

        valid_types = {
            "USES_METHOD", "USES_DATASET", "REPORTS_FINDING", "HAS_LIMITATION",
            "STUDIES_TASK", "BELONGS_TO_TOPIC", "EVALUATED_ON", "COMPARE",
            "USED_FOR", "EXTENDS", "EVALUATED_BY", "TRAINED_WITH", "ACHIEVES",
        }
        if rel_type not in valid_types:
            return

        source_id = entity_name_to_id.get(source_name)
        target_id = entity_name_to_id.get(target_name)

        if not source_id and source_name in ("this paper", "this study", "the paper"):
            source_id = paper_node_id
        if not target_id and target_name in ("this paper", "this study", "the paper"):
            target_id = paper_node_id

        if not source_id or not target_id:
            return

        # 确保两端节点都存在
        if source_id not in nodes and source_id != paper_node_id:
            return
        if target_id not in nodes and target_id != paper_node_id:
            return

        edge_id = f"edge:{rel_type}:{stable_hash(source_id)}:{stable_hash(target_id)}"
        if edge_id not in edges:
            try:
                edge_type = EdgeType(rel_type)
            except ValueError:
                return
            edges[edge_id] = GraphEdge(
                edge_id=edge_id, source_id=source_id,
                target_id=target_id, edge_type=edge_type,
            )
        pid = section.get("paper_id", "")
        if pid not in edges[edge_id].properties.get("paper_ids", []):
            edges[edge_id].properties.setdefault("paper_ids", []).append(pid)
        evidence_quote = rel.get("evidence_quote", "")
        if evidence_quote:
            quotes = edges[edge_id].properties.setdefault("source_quotes", [])
            if len(quotes) < 3 and evidence_quote not in quotes:
                quotes.append(evidence_quote[:100])

    def _aggregate_gaps(
        self, nodes: dict, edges: dict, evidence_records: list[EvidenceRecord]
    ) -> None:
        """跨论文聚合 limitation / future_work / possible_gap → Gap 节点"""
        clusters: dict[str, dict[str, list[str]]] = {
            "limitation": {},
            "future_work": {},
            "possible_gap": {},
        }
        for nid, node in list(nodes.items()):
            if node.node_type == NodeType.LIMITATION:
                norm = node.properties.get("normalized_label", "")
                if norm:
                    clusters["limitation"].setdefault(norm, []).append(nid)
            elif node.node_type == NodeType.GAP:
                for st in ("future_work", "possible_gap"):
                    if st in node.properties.get("source_types", []):
                        norm = node.properties.get("normalized_label", "")
                        if norm:
                            clusters[st].setdefault(norm, []).append(nid)
                        break

        for source_type, type_clusters in clusters.items():
            for norm, node_ids in type_clusters.items():
                if len(node_ids) < 2:
                    continue

                all_paper_ids = set()
                for nid in node_ids:
                    for pid in nodes[nid].properties.get("paper_ids", []) + nodes[nid].properties.get("supporting_paper_ids", []):
                        all_paper_ids.add(pid)
                if len(all_paper_ids) < 2:
                    continue

                aggregated_gap_id = f"gap:agg:{stable_hash(norm)}"
                if aggregated_gap_id in nodes:
                    continue

                evidence_ids = []
                for nid in node_ids:
                    evidence_ids.extend(nodes[nid].properties.get("evidence_ids", []) +
                                        nodes[nid].properties.get("supporting_evidence_ids", []))
                evidence_ids = list(set(evidence_ids))

                best_text = ""
                for nid in node_ids:
                    candidate = nodes[nid].properties.get("gap_statement", nodes[nid].label)
                    if len(candidate) > len(best_text):
                        best_text = candidate

                nodes[aggregated_gap_id] = GraphNode(
                    node_id=aggregated_gap_id,
                    node_type=NodeType.GAP,
                    label=best_text[:50],
                    properties={
                        "normalized_label": norm,
                        "gap_statement": best_text,
                        "source_types": [source_type],
                        "supporting_evidence_ids": evidence_ids,
                        "supporting_paper_ids": list(all_paper_ids),
                        "supporting_limitation_ids": node_ids if source_type == "limitation" else [],
                        "confidence": compute_gap_confidence([source_type], "medium", len(all_paper_ids), True),
                        "status": "candidate",
                        "aggregated": True,
                    },
                )

                for nid in node_ids:
                    edge_id = f"edge:SUGGESTS_GAP:{stable_hash(nid)}:{stable_hash(aggregated_gap_id)}"
                    if edge_id not in edges:
                        edges[edge_id] = GraphEdge(
                            edge_id=edge_id,
                            source_id=nid,
                            target_id=aggregated_gap_id,
                            edge_type=EdgeType.SUGGESTS_GAP,
                        )
                    src_node = nodes[nid]
                    for eid in src_node.properties.get("evidence_ids", []) + src_node.properties.get("supporting_evidence_ids", []):
                        if eid not in edges[edge_id].properties.get("evidence_ids", []):
                            edges[edge_id].properties.setdefault("evidence_ids", []).append(eid)

    # ── Provenance 合并 ───────────────────────────

    def _merge_provenance(self, node: GraphNode, ev: EvidenceRecord) -> None:
        props = node.properties
        if ev.paper_id not in props.get("paper_ids", []):
            props.setdefault("paper_ids", []).append(ev.paper_id)
        if ev.evidence_id not in props.get("evidence_ids", []):
            props.setdefault("evidence_ids", []).append(ev.evidence_id)
        if ev.source_chunk_id and ev.source_chunk_id not in props.get("source_chunk_ids", []):
            props.setdefault("source_chunk_ids", []).append(ev.source_chunk_id)
        if ev.source_quote:
            quotes = props.setdefault("source_quotes", [])
            if len(quotes) < 3 and ev.source_quote not in quotes:
                quotes.append(ev.source_quote[:100])

    def _merge_edge_provenance(self, edge: GraphEdge, ev: EvidenceRecord) -> None:
        props = edge.properties
        if ev.paper_id not in props.get("paper_ids", []):
            props.setdefault("paper_ids", []).append(ev.paper_id)
        if ev.evidence_id not in props.get("evidence_ids", []):
            props.setdefault("evidence_ids", []).append(ev.evidence_id)
        if ev.source_chunk_id:
            props.setdefault("source_chunk_ids", []).append(ev.source_chunk_id)
        props.setdefault("evidence_strengths", []).append(ev.evidence_strength)

    def _split_multi(self, text: str) -> list[str]:
        parts = re.split(r"[,;、/]", text)
        return [p.strip() for p in parts if p.strip() and p.strip().lower() not in ("unknown", "n/a")]
