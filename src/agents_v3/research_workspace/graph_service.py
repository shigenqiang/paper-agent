"""知识图谱服务"""

from __future__ import annotations

import uuid
from collections import defaultdict
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
from src.agents_v3.research_workspace.storage import get_storage


class GraphService:
    """知识图谱构建与查询"""

    def __init__(self):
        self.storage = get_storage()

    def build_project_graph(self, project_id: str) -> KnowledgeGraph:
        evidence_data = self.storage.query("evidence_records", {"project_id": project_id})
        evidence_records = [EvidenceRecord(**e) for e in evidence_data]

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        for ev in evidence_records:
            # Paper node
            paper_node_id = f"paper:{ev.paper_id}"
            if paper_node_id not in nodes:
                nodes[paper_node_id] = GraphNode(
                    node_id=paper_node_id,
                    node_type=NodeType.PAPER,
                    label=ev.paper_id,
                )

            # Topic nodes
            if ev.topic:
                for topic in ev.topic.split(","):
                    topic = topic.strip()
                    if not topic:
                        continue
                    topic_id = f"topic:{topic.lower().replace(' ', '_')}"
                    if topic_id not in nodes:
                        nodes[topic_id] = GraphNode(
                            node_id=topic_id,
                            node_type=NodeType.TOPIC,
                            label=topic,
                        )
                    edge_id = f"{paper_node_id}->{topic_id}"
                    if edge_id not in edges:
                        edges[edge_id] = GraphEdge(
                            edge_id=edge_id,
                            source_id=paper_node_id,
                            target_id=topic_id,
                            edge_type=EdgeType.BELONGS_TO_TOPIC,
                        )

            # Method nodes
            if ev.method and ev.method != "unknown":
                method_id = f"method:{ev.method.lower().replace(' ', '_')}"
                if method_id not in nodes:
                    nodes[method_id] = GraphNode(
                        node_id=method_id,
                        node_type=NodeType.METHOD,
                        label=ev.method,
                    )
                edge_id = f"{paper_node_id}->{method_id}"
                if edge_id not in edges:
                    edges[edge_id] = GraphEdge(
                        edge_id=edge_id,
                        source_id=paper_node_id,
                        target_id=method_id,
                        edge_type=EdgeType.USES_METHOD,
                    )

            # Finding nodes
            if ev.finding and ev.finding != "unknown":
                finding_id = f"finding:{uuid.uuid4().hex[:8]}"
                nodes[finding_id] = GraphNode(
                    node_id=finding_id,
                    node_type=NodeType.FINDING,
                    label=ev.finding[:50],
                )
                edge_id = f"{paper_node_id}->{finding_id}"
                edges[edge_id] = GraphEdge(
                    edge_id=edge_id,
                    source_id=paper_node_id,
                    target_id=finding_id,
                    edge_type=EdgeType.REPORTS_FINDING,
                )

            # Limitation nodes
            if ev.limitation and ev.limitation != "unknown":
                limit_id = f"limitation:{uuid.uuid4().hex[:8]}"
                nodes[limit_id] = GraphNode(
                    node_id=limit_id,
                    node_type=NodeType.LIMITATION,
                    label=ev.limitation[:50],
                )
                edge_id = f"{paper_node_id}->{limit_id}"
                edges[edge_id] = GraphEdge(
                    edge_id=edge_id,
                    source_id=paper_node_id,
                    target_id=limit_id,
                    edge_type=EdgeType.HAS_LIMITATION,
                )

        graph = KnowledgeGraph(
            project_id=project_id,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )

        # Save graph
        self.storage.save_collection(
            f"graph_{project_id}",
            [graph.model_dump()],
        )

        logger.info(f"Built graph for {project_id}: {len(nodes)} nodes, {len(edges)} edges")
        return graph

    def get_graph(self, project_id: str) -> KnowledgeGraph:
        graphs = self.storage.load_collection(f"graph_{project_id}")
        if graphs:
            return KnowledgeGraph(**graphs[0])
        return KnowledgeGraph(project_id=project_id)

    def get_node(self, project_id: str, node_id: str) -> GraphNode | None:
        graph = self.get_graph(project_id)
        for node in graph.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_neighbors(self, project_id: str, node_id: str, hops: int = 1) -> dict[str, Any]:
        graph = self.get_graph(project_id)
        adjacency = self._build_adjacency(graph)

        visited = set()
        current_level = {node_id}
        result_nodes = []
        result_edges = []

        for _ in range(hops):
            next_level = set()
            for nid in current_level:
                if nid in visited:
                    continue
                visited.add(nid)
                for neighbor_id, edge in adjacency.get(nid, []):
                    if neighbor_id not in visited:
                        next_level.add(neighbor_id)
                        result_edges.append(edge)
            current_level = next_level

        # Collect nodes
        node_map = {n.node_id: n for n in graph.nodes}
        for nid in visited:
            if nid in node_map:
                result_nodes.append(node_map[nid])

        return {
            "nodes": [n.model_dump() for n in result_nodes],
            "edges": [e.model_dump() for e in result_edges],
        }

    def get_subgraph(self, project_id: str, node_ids: list[str], hops: int = 1) -> dict[str, Any]:
        graph = self.get_graph(project_id)
        all_nodes = set()
        all_edges = set()

        for node_id in node_ids:
            neighbors = self.get_neighbors(project_id, node_id, hops)
            for n in neighbors["nodes"]:
                all_nodes.add(n["node_id"])
            for e in neighbors["edges"]:
                all_edges.add(e["edge_id"])

        node_map = {n.node_id: n for n in graph.nodes}
        edge_map = {e.edge_id: e for e in graph.edges}

        return {
            "nodes": [node_map[nid].model_dump() for nid in all_nodes if nid in node_map],
            "edges": [edge_map[eid].model_dump() for eid in all_edges if eid in edge_map],
        }

    def find_paths(
        self, project_id: str, source_id: str, target_id: str, max_hops: int = 3
    ) -> list[list[str]]:
        graph = self.get_graph(project_id)
        adjacency = self._build_adjacency(graph)

        paths = []
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)
            if current == target_id:
                paths.append(path)
                continue
            if len(path) > max_hops:
                continue

            for neighbor_id, _ in adjacency.get(current, []):
                if neighbor_id not in path:
                    queue.append((neighbor_id, path + [neighbor_id]))

        return paths

    def _build_adjacency(self, graph: KnowledgeGraph) -> dict[str, list[tuple[str, GraphEdge]]]:
        adj: dict[str, list[tuple[str, GraphEdge]]] = defaultdict(list)
        for edge in graph.edges:
            adj[edge.source_id].append((edge.target_id, edge))
            adj[edge.target_id].append((edge.source_id, edge))
        return adj
