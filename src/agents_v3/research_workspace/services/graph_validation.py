"""知识图谱验证/指标/Consensus Meter Mixin"""

from __future__ import annotations

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EdgeType,
    GraphEdge,
    NodeType,
)
from src.agents_v3.research_workspace.utils import stable_hash



class GraphValidationMixin:
    """图谱验证、质量指标、Consensus Meter"""

    def resolve_graph_scope(
        self,
        project_id: str,
        graph_node_ids: list[str],
        graph_edge_ids: list[str] | None = None,
        hops: int = 1,
    ) -> dict:
        """将用户选择的图谱节点/边解析为 paper_ids + evidence_ids"""
        graph = self.get_graph(project_id)
        if not graph:
            return {"paper_ids": [], "evidence_ids": [], "warnings": ["graph_not_found"]}

        subgraph = self.get_subgraph(project_id, graph_node_ids, hops=hops)

        paper_ids = list(set(subgraph.get("related_paper_ids", [])))
        evidence_ids = list(set(subgraph.get("related_evidence_ids", [])))

        node_map = {n.node_id: n for n in graph.nodes}
        for node_id in graph_node_ids:
            node = node_map.get(node_id)
            if node and node.node_type == NodeType.GAP:
                supporting = node.properties.get("supporting_evidence_ids", [])
                evidence_ids.extend(supporting)
                supporting_papers = node.properties.get("supporting_paper_ids", [])
                paper_ids.extend(supporting_papers)

        paper_ids = list(set(paper_ids))
        evidence_ids = list(set(evidence_ids))

        selected_labels = [node_map[nid].label for nid in graph_node_ids if nid in node_map]
        summary = f"图谱子图范围：{', '.join(selected_labels[:5])}，包含 {len(paper_ids)} 篇论文、{len(evidence_ids)} 条证据"

        warnings = []
        if not paper_ids:
            warnings.append("scope_no_papers")
        if not evidence_ids:
            warnings.append("scope_no_evidence")
        if hops > 2:
            warnings.append("hops_truncated")

        return {
            "paper_ids": paper_ids,
            "evidence_ids": evidence_ids,
            "graph_node_ids": subgraph.get("selected_node_ids", graph_node_ids),
            "graph_edge_ids": [e.get("edge_id", "") for e in subgraph.get("edges", [])],
            "scope_summary": summary,
            "warnings": warnings,
        }

    def validate_graph_traceability(self, project_id: str) -> dict:
        """校验图谱来源追踪质量"""
        graph = self.get_graph(project_id)
        node_map = {n.node_id: n for n in graph.nodes}
        errors: list[dict] = []
        warnings: list[dict] = []

        for edge in graph.edges:
            if edge.source_id not in node_map:
                errors.append({"type": "missing_node", "edge_id": edge.edge_id, "missing": edge.source_id})
            if edge.target_id not in node_map:
                errors.append({"type": "missing_node", "edge_id": edge.edge_id, "missing": edge.target_id})

        non_structural_types = {EdgeType.BELONGS_TO_TOPIC, EdgeType.USES_METHOD, EdgeType.USES_DATASET,
                                EdgeType.REPORTS_FINDING, EdgeType.HAS_LIMITATION, EdgeType.SUGGESTS_GAP,
                                EdgeType.STUDIES_TASK}
        for edge in graph.edges:
            if edge.edge_type in non_structural_types:
                if not edge.properties.get("evidence_ids"):
                    errors.append({"type": "missing_evidence", "edge_id": edge.edge_id})

        for node in graph.nodes:
            if node.node_type == NodeType.PAPER:
                continue
            if not node.properties.get("paper_ids") and not node.properties.get("evidence_ids"):
                warnings.append({"type": "orphan_node", "node_id": node.node_id})

        for node in graph.nodes:
            if node.node_type == NodeType.GAP:
                if not node.properties.get("supporting_evidence_ids"):
                    warnings.append({"type": "gap_no_evidence", "node_id": node.node_id})

        non_paper_nodes = [n for n in graph.nodes if n.node_type != NodeType.PAPER]
        traceable = sum(1 for n in non_paper_nodes if n.properties.get("paper_ids") or n.properties.get("evidence_ids"))
        orphan_count = sum(1 for n in non_paper_nodes if not n.properties.get("paper_ids") and not n.properties.get("evidence_ids"))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metrics": {
                "traceability_coverage": traceable / len(non_paper_nodes) if non_paper_nodes else 1.0,
                "orphan_node_rate": orphan_count / len(non_paper_nodes) if non_paper_nodes else 0.0,
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
            },
        }

    def get_stats(self, project_id: str) -> dict:
        graph = self.get_graph(project_id)
        node_type_counts: dict[str, int] = {}
        edge_type_counts: dict[str, int] = {}

        for node in graph.nodes:
            t = node.node_type.value
            node_type_counts[t] = node_type_counts.get(t, 0) + 1
        for edge in graph.edges:
            t = edge.edge_type.value
            edge_type_counts[t] = edge_type_counts.get(t, 0) + 1

        connected = set()
        for edge in graph.edges:
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        isolated = [n.node_id for n in graph.nodes if n.node_id not in connected]

        total_degree = sum(len([e for e in graph.edges if e.source_id == n.node_id or e.target_id == n.node_id]) for n in graph.nodes)

        return {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "node_type_counts": node_type_counts,
            "edge_type_counts": edge_type_counts,
            "paper_count": node_type_counts.get("Paper", 0),
            "gap_count": node_type_counts.get("Gap", 0),
            "isolated_nodes": isolated,
            "avg_degree": total_degree / len(graph.nodes) if graph.nodes else 0,
        }

    def compute_quality_metrics(self, project_id: str) -> dict:
        """计算图谱质量指标：覆盖度、实体质量、下游价值"""
        graph = self.get_graph(project_id)
        if not graph:
            return {"error": "graph_not_found"}

        papers_in_graph = set()
        evidence_in_graph = set()
        for node in graph.nodes:
            papers_in_graph.update(node.properties.get("paper_ids", []))
            evidence_in_graph.update(node.properties.get("evidence_ids", []))

        total_papers = len([n for n in graph.nodes if n.node_type == NodeType.PAPER])
        total_sections = len(self.storage.query("paper_sections", {"extraction_status": "done"}))
        all_sections = len(self.storage.query("paper_sections", {}))

        non_paper_nodes = [n for n in graph.nodes if n.node_type != NodeType.PAPER]
        traceable = sum(
            1 for n in non_paper_nodes
            if n.properties.get("paper_ids") or n.properties.get("evidence_ids")
        )

        type_label_groups: dict[str, dict[str, int]] = {}
        for node in non_paper_nodes:
            ntype = node.node_type.value
            norm = node.properties.get("normalized_label", node.label.lower())
            type_label_groups.setdefault(ntype, {})
            type_label_groups[ntype][norm] = type_label_groups[ntype].get(norm, 0) + 1

        duplicate_count = 0
        for ntype, labels in type_label_groups.items():
            duplicate_count += sum(1 for c in labels.values() if c > 1)
        total_entity_types = sum(len(labels) for labels in type_label_groups.values())
        duplicate_rate = duplicate_count / total_entity_types if total_entity_types > 0 else 0

        connected = set()
        for edge in graph.edges:
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        isolated = [n for n in graph.nodes if n.node_id not in connected and n.node_type != NodeType.PAPER]

        used_types = set(n.node_type.value for n in graph.nodes)
        available_types = set(t.value for t in NodeType)
        type_utilization = len(used_types) / len(available_types) if available_types else 0

        used_edge_types = set(e.edge_type.value for e in graph.edges)
        available_edge_types = set(t.value for t in EdgeType)
        edge_type_utilization = len(used_edge_types) / len(available_edge_types) if available_edge_types else 0

        return {
            "coverage": {
                "paper_count": total_papers,
                "papers_with_connections": len(papers_in_graph),
                "evidence_in_graph": len(evidence_in_graph),
                "section_extraction_rate": total_sections / all_sections if all_sections > 0 else 0,
                "traceability_rate": traceable / len(non_paper_nodes) if non_paper_nodes else 1.0,
            },
            "entity_quality": {
                "total_entity_types": total_entity_types,
                "duplicate_entity_count": duplicate_count,
                "duplicate_rate": round(duplicate_rate, 4),
                "isolated_non_paper_nodes": len(isolated),
            },
            "structure": {
                "node_type_utilization": round(type_utilization, 4),
                "edge_type_utilization": round(edge_type_utilization, 4),
                "used_node_types": sorted(used_types),
                "used_edge_types": sorted(used_edge_types),
                "avg_degree": round(
                    sum(1 for e in graph.edges for _ in (e.source_id, e.target_id)) / len(graph.nodes), 2
                ) if graph.nodes else 0,
            },
        }

    def build_consensus_meter(
        self,
        project_id: str,
        claim_node_ids: list[str] | None = None,
        min_confidence: float = 0.3,
    ) -> list[dict]:
        """对 Finding 节点做多论文立场聚合（Consensus Meter）"""
        from src.agents_v3.research_workspace.llm.prompts import CLAIM_STANCE_PROMPT
        from src.agents_v3.research_workspace.llm.service import get_llm_service

        graph = self.get_graph(project_id)
        if not graph:
            return []

        llm = get_llm_service()
        node_map = {n.node_id: n for n in graph.nodes}

        finding_nodes = [n for n in graph.nodes if n.node_type == NodeType.FINDING]
        if claim_node_ids:
            finding_nodes = [n for n in finding_nodes if n.node_id in claim_node_ids]

        claim_clusters: dict[str, list] = {}
        for node in finding_nodes:
            norm = node.properties.get("normalized_label", node.label.lower())
            claim_clusters.setdefault(norm, []).append(node)

        results = []
        stance_edges: list[GraphEdge] = []
        for norm_label, cluster_nodes in claim_clusters.items():
            if len(cluster_nodes) < 2:
                continue

            representative = cluster_nodes[0]
            claim_text = representative.properties.get("claim", representative.label)

            stances: list[dict] = []
            for node in cluster_nodes:
                finding_text = node.properties.get("claim", node.label)
                paper_ids = node.properties.get("paper_ids", [])
                paper_id = paper_ids[0] if paper_ids else "unknown"

                if finding_text == claim_text:
                    continue

                try:
                    prompt = CLAIM_STANCE_PROMPT.user_template.format(
                        claim=claim_text, paper_id=paper_id, finding=finding_text,
                    )
                    result = llm.invoke_json(CLAIM_STANCE_PROMPT.system_prompt, prompt)
                    if result and "stance" in result:
                        stances.append({
                            "node_id": node.node_id,
                            "paper_id": paper_id,
                            "stance": result["stance"],
                            "confidence": result.get("confidence", 0.5),
                            "reason": result.get("reason", ""),
                        })
                except Exception as e:
                    logger.warning(f"Stance classification failed for {node.node_id}: {e}")

            for s in stances:
                edge_type = EdgeType.SUPPORTS if s["stance"] == "supports" else (
                    EdgeType.CONTRADICTS if s["stance"] == "contradicts" else None
                )
                if edge_type is None:
                    continue
                edge_id = f"edge:{edge_type.value}:{stable_hash(s['node_id'])}:{stable_hash(representative.node_id)}"
                if edge_id not in graph.edges:
                    stance_edges.append(GraphEdge(
                        edge_id=edge_id,
                        source_id=s["node_id"],
                        target_id=representative.node_id,
                        edge_type=edge_type,
                        properties={
                            "confidence": s["confidence"],
                            "reason": s.get("reason", ""),
                            "paper_ids": [s["paper_id"]],
                        },
                    ))

            supports = [s for s in stances if s["stance"] == "supports"]
            contradicts = [s for s in stances if s["stance"] == "contradicts"]
            neutral = [s for s in stances if s["stance"] == "neutral"]

            total = len(stances)
            if total == 0:
                continue

            # 按 evidence_strength 加权
            strength_weights = {"high": 1.0, "medium": 0.7, "low": 0.4}
            support_weight = 0.0
            contradict_weight = 0.0
            for s in supports:
                node = node_map.get(s["node_id"])
                strength = node.properties.get("evidence_strength", "medium") if node else "medium"
                support_weight += strength_weights.get(strength, 0.7)
            for s in contradicts:
                node = node_map.get(s["node_id"])
                strength = node.properties.get("evidence_strength", "medium") if node else "medium"
                contradict_weight += strength_weights.get(strength, 0.7)

            total_weight = support_weight + contradict_weight
            if total_weight > 0:
                consensus_score = (support_weight - contradict_weight) / total_weight
            else:
                consensus_score = 0.0
            agreement_rate = max(support_weight, contradict_weight) / total_weight if total_weight > 0 else 0

            results.append({
                "claim_node_id": representative.node_id,
                "claim_text": claim_text[:200],
                "total_papers": len(set(
                    pid for n in cluster_nodes for pid in n.properties.get("paper_ids", [])
                )),
                "supports": len(supports),
                "contradicts": len(contradicts),
                "neutral": len(neutral),
                "consensus_score": round(consensus_score, 3),
                "agreement_rate": round(agreement_rate, 3),
                "stances": stances,
            })

        if stance_edges:
            graph.edges.extend(stance_edges)
            self._save_graph(project_id, graph)
            logger.info(f"Persisted {len(stance_edges)} stance edges (SUPPORTS/CONTRADICTS)")

        results.sort(key=lambda x: abs(x["consensus_score"]), reverse=True)
        return results

    def compute_downstream_value(self, project_id: str) -> dict:
        """下游模块对图谱的使用率指标"""
        graph = self.get_graph(project_id)
        if not graph:
            return {"error": "graph_not_found"}

        node_map = {n.node_id: n for n in graph.nodes}

        # 1. QA 使用率：检查 QA 回答中引用图谱节点的比例
        qa_records = self.storage.query("qa_history", {"project_id": project_id})
        qa_total = len(qa_records)
        qa_with_graph = sum(
            1 for r in qa_records
            if r.get("graph_node_ids") or r.get("graph_paths")
        )

        # 2. 综述主题覆盖：检查综述 section 中涉及的 Topic 节点比例
        review_records = self.storage.query("reports", {"project_id": project_id, "report_type": "review"})
        topic_nodes = [n for n in graph.nodes if n.node_type == NodeType.TOPIC]
        total_topics = len(topic_nodes)
        covered_topics = set()
        for review in review_records:
            for ref in review.get("graph_node_ids", []):
                node = node_map.get(ref)
                if node and node.node_type == NodeType.TOPIC:
                    covered_topics.add(node.node_id)

        # 3. 创新点 Gap 覆盖：检查创新点报告中引用的 Gap 节点比例
        innovation_records = self.storage.query("reports", {"project_id": project_id, "report_type": "innovation"})
        gap_nodes = [n for n in graph.nodes if n.node_type == NodeType.GAP]
        total_gaps = len(gap_nodes)
        covered_gaps = set()
        for innov in innovation_records:
            for ref in innov.get("graph_node_ids", []):
                node = node_map.get(ref)
                if node and node.node_type == NodeType.GAP:
                    covered_gaps.add(node.node_id)

        return {
            "qa_usage": {
                "total_queries": qa_total,
                "queries_with_graph": qa_with_graph,
                "graph_usage_rate": round(qa_with_graph / qa_total, 3) if qa_total > 0 else 0,
            },
            "review_coverage": {
                "total_topics": total_topics,
                "covered_topics": len(covered_topics),
                "topic_coverage_rate": round(len(covered_topics) / total_topics, 3) if total_topics > 0 else 0,
            },
            "innovation_coverage": {
                "total_gaps": total_gaps,
                "covered_gaps": len(covered_gaps),
                "gap_coverage_rate": round(len(covered_gaps) / total_gaps, 3) if total_gaps > 0 else 0,
            },
        }
