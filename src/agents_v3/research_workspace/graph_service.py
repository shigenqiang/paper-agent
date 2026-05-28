"""知识图谱服务 - 增强版"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EdgeType,
    EvidenceRecord,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
)
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


# ── 实体归一化 ──────────────────────────────────────

def normalize_label(text: str) -> str:
    """文本归一化：小写、去标点、压缩空格、去复数"""
    t = text.strip().lower()
    t = re.sub(r"[　]", " ", t)  # 全角空格
    t = re.sub(r"[_\-]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    t = t.rstrip(".,;:;")
    # 简单去复数
    if t.endswith("s") and not t.endswith("ss") and len(t) > 3:
        t = t[:-1]
    return t


def stable_hash(text: str) -> str:
    """生成稳定的短哈希"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


# 同义词/缩写映射
_ALIASES: dict[str, str] = {
    "llms": "llm",
    "large language model": "llm",
    "large language models": "llm",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "rag-based approach": "rag",
    "randomized controlled trial": "rct",
    "quasi-experiment": "quasi experimental",
    "randomised controlled trial": "rct",
}


def resolve_alias(normalized: str) -> str:
    """检查同义词映射"""
    return _ALIASES.get(normalized, normalized)


# ── Gap 检测 ──────────────────────────────────────

# Limitation 类型关键词
_LIMITATION_TYPE_KEYWORDS: dict[str, list[str]] = {
    "sample_size": ["sample size", "small sample", "样本量", "样本不足"],
    "single_dataset": ["single dataset", "one dataset", "单数据集", "数据集单一"],
    "short_duration": ["short duration", "short-term", "短期", "时间短"],
    "lack_control_group": ["control group", "lack of control", "缺乏对照"],
    "generalizability": ["generaliz", "外部效度", "推广性", "可推广"],
    "measurement_bias": ["measurement bias", "self-report", "测量偏差"],
    "method_limitation": ["methodology", "method limitation", "方法局限"],
    "domain_limitation": ["domain", "context specific", "领域局限"],
}


def classify_limitation_type(text: str) -> str:
    text_lower = text.lower()
    for ltype, keywords in _LIMITATION_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return ltype
    return "unknown"


def compute_gap_confidence(
    source_types: list[str],
    evidence_strength: str,
    supporting_paper_count: int,
    has_quote: bool,
) -> float:
    base = 0.3
    if "future_work" in source_types:
        base += 0.2
    if "possible_gap" in source_types:
        base += 0.2
    if evidence_strength == "high":
        base += 0.1
    if supporting_paper_count >= 2:
        base += 0.1
    if has_quote:
        base += 0.1
    return min(1.0, base)


# ── GraphService ──────────────────────────────────

class GraphService:
    """知识图谱构建与查询"""

    def __init__(self, storage: JSONStorage | None = None):
        self.storage = storage or get_storage()

    # ── 构建 ──────────────────────────────────────

    def build_project_graph(self, project_id: str, force: bool = False) -> KnowledgeGraph:
        """全量构建项目知识图谱"""
        # 加载数据
        evidence_data = self.storage.query("evidence_records", {"project_id": project_id})
        evidence_records = [EvidenceRecord(**e) for e in evidence_data]

        # 排除 excluded papers
        papers_data = self.storage.query("papers", {"project_id": project_id})
        included_paper_ids = {p["paper_id"] for p in papers_data if p.get("included", True)}
        evidence_records = [e for e in evidence_records if e.paper_id in included_paper_ids]

        # 加载 cards 用于补充
        cards_data = self.storage.query("paper_cards", {"project_id": project_id, "active": True})

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        # 构建 Paper 节点
        for p in papers_data:
            if not p.get("included", True):
                continue
            pid = p["paper_id"]
            node_id = f"paper:{pid}"
            nodes[node_id] = GraphNode(
                node_id=node_id,
                node_type=NodeType.PAPER,
                label=p.get("title", pid)[:80],
                properties={
                    "paper_ids": [pid],
                    "evidence_ids": [],
                    "title": p.get("title", ""),
                    "authors": p.get("authors", []),
                    "year": p.get("year"),
                    "doi": p.get("doi", ""),
                    "venue": p.get("venue", ""),
                    "included": True,
                },
            )

        # 从 evidence 构建节点和边
        for ev in evidence_records:
            paper_node_id = f"paper:{ev.paper_id}"
            self._ensure_paper_node(nodes, ev.paper_id)

            # Topic
            if ev.topic:
                for topic in self._split_multi(ev.topic):
                    self._add_topic_node(nodes, edges, paper_node_id, topic, ev)

            # Method
            if ev.method and ev.method.lower() not in ("unknown", ""):
                for method in self._split_multi(ev.method):
                    self._add_method_node(nodes, edges, paper_node_id, method, ev)

            # Dataset
            if ev.data_or_sample and ev.data_or_sample.lower() not in ("unknown", ""):
                self._add_dataset_node(nodes, edges, paper_node_id, ev.data_or_sample, ev)

            # Finding
            if ev.finding and ev.finding.lower() not in ("unknown", ""):
                self._add_finding_node(nodes, edges, paper_node_id, ev)

            # Limitation
            if ev.limitation and ev.limitation.lower() not in ("unknown", ""):
                self._add_limitation_node(nodes, edges, paper_node_id, ev)

        # 从 cards 补充 possible_gaps 和 future_work
        for card in cards_data:
            pid = card.get("paper_id", "")
            paper_node_id = f"paper:{pid}"
            for gap_text in card.get("possible_gaps", []):
                if gap_text and gap_text.lower() != "unknown":
                    self._add_gap_candidate_from_text(nodes, edges, paper_node_id, pid, gap_text, "possible_gap")
            for fw_text in card.get("future_work", []):
                if fw_text and fw_text.lower() != "unknown":
                    self._add_gap_candidate_from_text(nodes, edges, paper_node_id, pid, fw_text, "future_work")

        # Gap 聚合
        self._aggregate_gaps(nodes, edges, evidence_records)

        graph = KnowledgeGraph(
            project_id=project_id,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )

        # 保存到统一 graphs collection
        self._save_graph(project_id, graph)

        logger.info(f"Built graph for {project_id}: {len(nodes)} nodes, {len(edges)} edges")
        return graph

    # ── 节点构建辅助 ──────────────────────────────

    def _ensure_paper_node(self, nodes: dict[str, GraphNode], paper_id: str) -> None:
        node_id = f"paper:{paper_id}"
        if node_id not in nodes:
            nodes[node_id] = GraphNode(
                node_id=node_id,
                node_type=NodeType.PAPER,
                label=paper_id,
                properties={"paper_ids": [paper_id], "evidence_ids": []},
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
        finding_id = f"finding:{ev.paper_id}:{stable_hash(normalized)}"

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
        limit_id = f"limitation:{ev.paper_id}:{stable_hash(normalized)}"

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

    def _aggregate_gaps(
        self, nodes: dict, edges: dict, evidence_records: list[EvidenceRecord]
    ) -> None:
        """从 limitation 聚合 Gap 节点"""
        # 收集所有 limitation 的 normalized text
        limitation_clusters: dict[str, list[str]] = {}  # normalized -> [limitation node_ids]
        for nid, node in list(nodes.items()):
            if node.node_type == NodeType.LIMITATION:
                norm = node.properties.get("normalized_label", "")
                if norm:
                    limitation_clusters.setdefault(norm, []).append(nid)

        # 对于出现 >= 2 次的 limitation，创建 Gap
        for norm, lim_ids in limitation_clusters.items():
            if len(lim_ids) < 2:
                continue
            gap_id = f"gap:{stable_hash(norm)}"
            if gap_id in nodes:
                continue

            # 收集来源
            paper_ids = []
            evidence_ids = []
            for lim_id in lim_ids:
                lim_node = nodes[lim_id]
                paper_ids.extend(lim_node.properties.get("paper_ids", []))
                evidence_ids.extend(lim_node.properties.get("evidence_ids", []))

            paper_ids = list(set(paper_ids))
            evidence_ids = list(set(evidence_ids))

            nodes[gap_id] = GraphNode(
                node_id=gap_id,
                node_type=NodeType.GAP,
                label=nodes[lim_ids[0]].properties.get("claim", norm)[:50],
                properties={
                    "normalized_label": norm,
                    "gap_statement": nodes[lim_ids[0]].properties.get("claim", norm),
                    "source_types": ["limitation"],
                    "supporting_evidence_ids": evidence_ids,
                    "supporting_paper_ids": paper_ids,
                    "supporting_limitation_ids": lim_ids,
                    "confidence": compute_gap_confidence(["limitation"], "medium", len(paper_ids), True),
                    "status": "candidate",
                },
            )

            # 创建 SUGGESTS_GAP 边
            for lim_id in lim_ids:
                edge_id = f"edge:SUGGESTS_GAP:{stable_hash(lim_id)}:{stable_hash(gap_id)}"
                if edge_id not in edges:
                    edges[edge_id] = GraphEdge(
                        edge_id=edge_id,
                        source_id=lim_id,
                        target_id=gap_id,
                        edge_type=EdgeType.SUGGESTS_GAP,
                    )
                lim_node = nodes[lim_id]
                for eid in lim_node.properties.get("evidence_ids", []):
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

    # ── 工具 ──────────────────────────────────────

    def _split_multi(self, text: str) -> list[str]:
        parts = re.split(r"[,;、/]", text)
        return [p.strip() for p in parts if p.strip() and p.strip().lower() not in ("unknown", "n/a")]

    # ── 查询 ──────────────────────────────────────

    def get_graph(self, project_id: str) -> KnowledgeGraph:
        """读取图谱，优先从 graphs collection，兼容旧格式"""
        graphs = self.storage.query("graphs", {"project_id": project_id})
        if graphs:
            return KnowledgeGraph(**graphs[0])
        # 兼容旧格式
        old = self.storage.load_collection(f"graph_{project_id}")
        if old:
            return KnowledgeGraph(**old[0])
        return KnowledgeGraph(project_id=project_id)

    def get_node(self, project_id: str, node_id: str) -> GraphNode | None:
        graph = self.get_graph(project_id)
        for node in graph.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_neighbors(
        self, project_id: str, node_id: str, hops: int = 1,
        node_types: list[str] | None = None, edge_types: list[str] | None = None,
    ) -> dict:
        graph = self.get_graph(project_id)
        adjacency = self._build_adjacency(graph)

        hops = min(hops, 2)
        visited: set[str] = set()
        current_level = {node_id}
        result_nodes: list[GraphNode] = []
        result_edges: list[GraphEdge] = []

        for _ in range(hops):
            next_level: set[str] = set()
            for nid in current_level:
                if nid in visited:
                    continue
                visited.add(nid)
                for neighbor_id, edge in adjacency.get(nid, []):
                    if neighbor_id in visited:
                        continue
                    if edge_types and edge.edge_type.value not in edge_types:
                        continue
                    if node_types:
                        neighbor_node = next((n for n in graph.nodes if n.node_id == neighbor_id), None)
                        if neighbor_node and neighbor_node.node_type.value not in node_types:
                            continue
                    next_level.add(neighbor_id)
                    result_edges.append(edge)
            current_level = next_level
        # Add remaining nodes from last expansion
        visited.update(current_level)

        node_map = {n.node_id: n for n in graph.nodes}
        for nid in visited:
            if nid in node_map:
                result_nodes.append(node_map[nid])

        return {
            "nodes": [n.model_dump() for n in result_nodes],
            "edges": [e.model_dump() for e in result_edges],
        }

    def get_subgraph(
        self, project_id: str, node_ids: list[str], hops: int = 1,
        node_types: list[str] | None = None, edge_types: list[str] | None = None,
    ) -> dict:
        """获取子图，返回节点、边和关联的 paper/evidence"""
        graph = self.get_graph(project_id)
        hops = min(hops, 2)
        warnings: list[str] = []

        all_node_ids: set[str] = set()
        all_edge_ids: set[str] = set()

        for node_id in node_ids:
            neighbors = self.get_neighbors(project_id, node_id, hops, node_types, edge_types)
            for n in neighbors["nodes"]:
                all_node_ids.add(n["node_id"])
            for e in neighbors["edges"]:
                all_edge_ids.add(e["edge_id"])

        node_map = {n.node_id: n for n in graph.nodes}
        edge_map = {e.edge_id: e for e in graph.edges}

        result_nodes = [node_map[nid].model_dump() for nid in all_node_ids if nid in node_map]
        result_edges = [edge_map[eid].model_dump() for eid in all_edge_ids if eid in edge_map]

        # 收集关联 paper_ids 和 evidence_ids
        related_paper_ids: set[str] = set()
        related_evidence_ids: set[str] = set()
        for n in result_nodes:
            props = n.get("properties", {})
            for pid in props.get("paper_ids", []):
                related_paper_ids.add(pid)
            for eid in props.get("evidence_ids", []):
                related_evidence_ids.add(eid)
        for e in result_edges:
            props = e.get("properties", {})
            for pid in props.get("paper_ids", []):
                related_paper_ids.add(pid)
            for eid in props.get("evidence_ids", []):
                related_evidence_ids.add(eid)

        return {
            "project_id": project_id,
            "nodes": result_nodes,
            "edges": result_edges,
            "related_paper_ids": list(related_paper_ids),
            "related_evidence_ids": list(related_evidence_ids),
            "selected_node_ids": node_ids,
            "hops": hops,
            "warnings": warnings,
        }

    def find_paths(
        self, project_id: str, source_id: str, target_id: str, max_hops: int = 3
    ) -> list[dict]:
        """查找路径，返回 node_ids、edge_ids 和 explanation"""
        graph = self.get_graph(project_id)
        adjacency = self._build_adjacency(graph)
        node_map = {n.node_id: n for n in graph.nodes}
        edge_map = {e.edge_id: e for e in graph.edges}

        paths: list[dict] = []
        queue = [(source_id, [source_id], [])]

        while queue:
            current, node_path, edge_path = queue.pop(0)
            if current == target_id:
                # 解释
                explanation = self._explain_path(node_path, node_map)
                related_pids = set()
                related_eids = set()
                for nid in node_path:
                    n = node_map.get(nid)
                    if n:
                        related_pids.update(n.properties.get("paper_ids", []))
                        related_eids.update(n.properties.get("evidence_ids", []))
                paths.append({
                    "node_ids": node_path,
                    "edge_ids": edge_path,
                    "path_length": len(node_path) - 1,
                    "related_paper_ids": list(related_pids),
                    "related_evidence_ids": list(related_eids),
                    "explanation": explanation,
                })
                if len(paths) >= 10:
                    break
                continue
            if len(node_path) > max_hops:
                continue
            for neighbor_id, edge in adjacency.get(current, []):
                if neighbor_id not in node_path:
                    queue.append((neighbor_id, node_path + [neighbor_id], edge_path + [edge.edge_id]))

        return paths

    def _explain_path(self, node_ids: list[str], node_map: dict) -> str:
        """为路径生成简单解释"""
        if len(node_ids) < 2:
            return ""
        types = [node_map.get(nid, GraphNode(node_id="", node_type=NodeType.PAPER)).node_type.value for nid in node_ids]
        labels = [node_map.get(nid, GraphNode(node_id="", node_type=NodeType.PAPER)).label[:30] for nid in node_ids]
        return " -> ".join(f"{t}:{l}" for t, l in zip(types, labels))

    def find_gaps(self, project_id: str, min_confidence: float = 0.5) -> list[dict]:
        """查找 Gap 节点"""
        graph = self.get_graph(project_id)
        gaps = []
        for node in graph.nodes:
            if node.node_type == NodeType.GAP:
                conf = node.properties.get("confidence", 0)
                if conf >= min_confidence:
                    gaps.append(node.model_dump())
        gaps.sort(key=lambda g: g.get("properties", {}).get("confidence", 0), reverse=True)
        return gaps

    def validate_graph_traceability(self, project_id: str) -> dict:
        """校验图谱来源追踪质量"""
        graph = self.get_graph(project_id)
        node_map = {n.node_id: n for n in graph.nodes}
        errors: list[dict] = []
        warnings: list[dict] = []

        # 检查边的端点是否存在
        for edge in graph.edges:
            if edge.source_id not in node_map:
                errors.append({"type": "missing_node", "edge_id": edge.edge_id, "missing": edge.source_id})
            if edge.target_id not in node_map:
                errors.append({"type": "missing_node", "edge_id": edge.edge_id, "missing": edge.target_id})

        # 检查非结构性边是否有 evidence_ids
        non_structural_types = {EdgeType.BELONGS_TO_TOPIC, EdgeType.USES_METHOD, EdgeType.USES_DATASET,
                                EdgeType.REPORTS_FINDING, EdgeType.HAS_LIMITATION, EdgeType.SUGGESTS_GAP}
        for edge in graph.edges:
            if edge.edge_type in non_structural_types:
                if not edge.properties.get("evidence_ids"):
                    errors.append({"type": "missing_evidence", "edge_id": edge.edge_id})

        # 检查非 Paper 节点是否有来源
        for node in graph.nodes:
            if node.node_type == NodeType.PAPER:
                continue
            if not node.properties.get("paper_ids") and not node.properties.get("evidence_ids"):
                warnings.append({"type": "orphan_node", "node_id": node.node_id})

        # 检查 Gap 节点
        for node in graph.nodes:
            if node.node_type == NodeType.GAP:
                if not node.properties.get("supporting_evidence_ids"):
                    warnings.append({"type": "gap_no_evidence", "node_id": node.node_id})

        # 计算指标
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

    # ── 内部工具 ──────────────────────────────────

    def _build_adjacency(self, graph: KnowledgeGraph) -> dict[str, list[tuple[str, GraphEdge]]]:
        from collections import defaultdict
        adj: dict[str, list[tuple[str, GraphEdge]]] = defaultdict(list)
        for edge in graph.edges:
            adj[edge.source_id].append((edge.target_id, edge))
            adj[edge.target_id].append((edge.source_id, edge))
        return adj

    def _save_graph(self, project_id: str, graph: KnowledgeGraph) -> None:
        """保存到统一 graphs collection"""
        graph_data = graph.model_dump()
        graph_data["graph_id"] = f"kg_{project_id}"
        graph_data["version"] = 1
        self.storage.upsert_item("graphs", f"kg_{project_id}", graph_data)
        # 同时保存到旧格式兼容
        self.storage.save_collection(f"graph_{project_id}", [graph_data])
