"""知识图谱社区检测 + Global Search Mixin"""

from __future__ import annotations

import random

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
)
from src.agents_v3.research_workspace.utils import stable_hash

from .graph_utils import _build_adjacency


class GraphCommunityMixin:
    """社区检测（Leiden / Label Propagation）+ Global Search"""

    def detect_communities(
        self, project_id: str, resolution: float = 1.0,
    ) -> dict:
        """社区检测：优先 Leiden，回退 Label Propagation"""
        graph = self.get_graph(project_id)
        if not graph:
            return {"communities": 0, "total_assigned": 0, "community_sizes": []}

        node_map = {n.node_id: n for n in graph.nodes}
        target_nodes = [
            n for n in graph.nodes
            if n.node_type not in (NodeType.PAPER, NodeType.COMMUNITY)
        ]
        if not target_nodes:
            return {"communities": 0, "total_assigned": 0, "community_sizes": []}

        target_ids = {n.node_id for n in target_nodes}

        adj: dict[str, set[str]] = {nid: set() for nid in target_ids}
        for edge in graph.edges:
            if edge.source_id in target_ids and edge.target_id in target_ids:
                adj[edge.source_id].add(edge.target_id)
                adj[edge.target_id].add(edge.source_id)

        communities = self._leiden_communities(adj, resolution)

        if communities is None:
            communities = self._label_propagation(adj)

        community_nodes: dict[int, list[str]] = {}
        for nid, cid in communities.items():
            community_nodes.setdefault(cid, []).append(nid)

        valid_communities = {cid: members for cid, members in community_nodes.items() if len(members) >= 2}

        new_nodes = list(graph.nodes)
        new_edges = list(graph.edges)

        for cid, members in valid_communities.items():
            comm_node_id = f"community:{project_id}:{cid}"
            all_paper_ids: list[str] = []
            member_labels: list[str] = []
            for nid in members:
                node = node_map.get(nid)
                if node:
                    all_paper_ids.extend(node.properties.get("paper_ids", []))
                    member_labels.append(node.label[:30])

            new_nodes.append(GraphNode(
                node_id=comm_node_id,
                node_type=NodeType.COMMUNITY,
                label=f"Community {cid} ({len(members)} nodes)",
                properties={
                    "community_id": cid,
                    "member_count": len(members),
                    "member_node_ids": members,
                    "paper_ids": list(set(all_paper_ids)),
                    "evidence_ids": [],
                },
            ))

            for nid in members:
                edge_id = f"edge:BELONGS_TO_COMMUNITY:{stable_hash(nid)}:{stable_hash(comm_node_id)}"
                new_edges.append(GraphEdge(
                    edge_id=edge_id,
                    source_id=nid,
                    target_id=comm_node_id,
                    edge_type=EdgeType.BELONGS_TO_COMMUNITY,
                ))

        graph.nodes = new_nodes
        graph.edges = new_edges
        self._save_graph(project_id, graph)

        logger.info(
            f"Community detection for {project_id}: "
            f"{len(valid_communities)} communities, "
            f"{sum(len(m) for m in valid_communities.values())} nodes assigned"
        )
        return {
            "communities": len(valid_communities),
            "total_assigned": sum(len(m) for m in valid_communities.values()),
            "community_sizes": [len(m) for m in valid_communities.values()],
        }

    def _leiden_communities(self, adj: dict[str, set[str]], resolution: float) -> dict[str, int] | None:
        """尝试用 Leiden 算法检测社区"""
        try:
            import igraph
            import leidenalg

            node_list = list(adj.keys())
            node_idx = {nid: i for i, nid in enumerate(node_list)}
            edge_list = []
            for nid, neighbors in adj.items():
                for nb in neighbors:
                    if node_idx[nid] < node_idx[nb]:
                        edge_list.append((node_idx[nid], node_idx[nb]))

            if not edge_list:
                return None

            g = igraph.Graph(n=len(node_list), edges=edge_list, directed=False)
            partition = leidenalg.find_partition(
                g, leidenalg.RBConfigurationVertexPartition,
                resolution_parameter=resolution,
            )

            result: dict[str, int] = {}
            for cid, members in enumerate(partition):
                for idx in members:
                    result[node_list[idx]] = cid
            return result
        except ImportError:
            logger.info("leidenalg not installed, falling back to label propagation")
            return None
        except Exception as e:
            logger.warning(f"Leiden detection failed: {e}, falling back to label propagation")
            return None

    def _label_propagation(self, adj: dict[str, set[str]], max_iter: int = 30) -> dict[str, int]:
        """Label Propagation 社区检测（纯 Python 实现）"""
        node_list = list(adj.keys())
        if not node_list:
            return {}

        labels = {nid: i for i, nid in enumerate(node_list)}

        for _ in range(max_iter):
            changed = False
            random.shuffle(node_list)
            for nid in node_list:
                if not adj[nid]:
                    continue
                label_counts: dict[int, int] = {}
                for nb in adj[nid]:
                    label_counts[labels[nb]] = label_counts.get(labels[nb], 0) + 1
                if not label_counts:
                    continue
                max_freq = max(label_counts.values())
                candidates = [l for l, c in label_counts.items() if c == max_freq]
                new_label = random.choice(candidates)
                if labels[nid] != new_label:
                    labels[nid] = new_label
                    changed = True
            if not changed:
                break

        unique_labels = sorted(set(labels.values()))
        label_map = {old: new for new, old in enumerate(unique_labels)}
        return {nid: label_map[lbl] for nid, lbl in labels.items()}

    def build_community_summaries(
        self, project_id: str, token_budget: int = 500,
    ) -> list[dict]:
        """为每个 Community 节点生成 LLM 摘要"""
        from src.agents_v3.research_workspace.llm.service import get_llm_service

        graph = self.get_graph(project_id)
        if not graph:
            return []

        llm = get_llm_service()
        node_map = {n.node_id: n for n in graph.nodes}
        adjacency = _build_adjacency(graph)

        community_nodes = [n for n in graph.nodes if n.node_type == NodeType.COMMUNITY]
        summaries = []

        for comm in community_nodes:
            member_ids = comm.properties.get("member_node_ids", [])
            member_info: list[str] = []
            for mid in member_ids:
                node = node_map.get(mid)
                if node:
                    member_info.append(f"- {node.node_type.value}: {node.label}")

            internal_edges: list[str] = []
            for mid in member_ids:
                for nb, edge in adjacency.get(mid, []):
                    if nb in set(member_ids):
                        src_label = node_map.get(mid, GraphNode(node_id="", node_type=NodeType.PAPER)).label[:20]
                        tgt_label = node_map.get(nb, GraphNode(node_id="", node_type=NodeType.PAPER)).label[:20]
                        internal_edges.append(f"  {src_label} --{edge.edge_type.value}--> {tgt_label}")

            member_text = "\n".join(member_info[:30])
            edge_text = "\n".join(internal_edges[:20])

            prompt = (
                f"Summarize this research community in 2-3 sentences. "
                f"Focus on the main research theme, key methods, and notable findings.\n\n"
                f"Members ({len(member_ids)} total):\n{member_text}\n\n"
                f"Internal relations:\n{edge_text}"
            )

            try:
                summary = llm.invoke(
                    "You are a scientific research analyst. Provide concise community summaries.",
                    prompt,
                )
                comm.properties["summary"] = summary[:token_budget * 2]
                summaries.append({
                    "community_node_id": comm.node_id,
                    "member_count": len(member_ids),
                    "summary": summary[:token_budget * 2],
                })
            except Exception as e:
                logger.warning(f"Community summary generation failed for {comm.node_id}: {e}")

        if summaries:
            self._save_graph(project_id, graph)

        return summaries

    def global_search(
        self, project_id: str, question: str, max_communities: int = 10,
    ) -> dict:
        """GraphRAG Global Search：Map-Reduce over community summaries"""
        from src.agents_v3.research_workspace.llm.service import get_llm_service

        graph = self.get_graph(project_id)
        if not graph:
            return {"answer": "", "sources": [], "community_answers": []}

        llm = get_llm_service()

        community_nodes = [n for n in graph.nodes if n.node_type == NodeType.COMMUNITY]
        if not community_nodes:
            return {"answer": "", "sources": [], "community_answers": []}

        community_answers: list[dict] = []
        for comm in community_nodes[:max_communities]:
            summary = comm.properties.get("summary", "")
            member_ids = comm.properties.get("member_node_ids", [])
            if not summary:
                continue

            map_prompt = (
                f"Based on the following research community summary, answer the question. "
                f"If the summary doesn't contain relevant information, say 'NO_RELEVANCE'.\n\n"
                f"Community Summary ({len(member_ids)} papers):\n{summary}\n\n"
                f"Question: {question}\n\n"
                f"Answer (be concise, cite specific findings):"
            )

            try:
                answer = llm.invoke("You are a research analyst.", map_prompt)
                if "NO_RELEVANCE" not in answer:
                    community_answers.append({
                        "community_id": comm.node_id,
                        "member_count": len(member_ids),
                        "answer": answer.strip(),
                    })
            except Exception as e:
                logger.warning(f"Global search map failed for {comm.node_id}: {e}")

        if not community_answers:
            return {"answer": "", "sources": [], "community_answers": []}

        reduce_input = "\n\n---\n\n".join(
            f"[Community {i+1} ({ca['member_count']} papers)]\n{ca['answer']}"
            for i, ca in enumerate(community_answers)
        )
        reduce_prompt = (
            f"Synthesize the following community-level answers into a comprehensive answer. "
            f"Highlight agreements, contradictions, and knowledge gaps.\n\n"
            f"{reduce_input}\n\n"
            f"Question: {question}\n\n"
            f"Synthesized Answer:"
        )

        try:
            final_answer = llm.invoke(
                "You are a research synthesis expert. Combine multiple perspectives into a coherent answer.",
                reduce_prompt,
            )
        except Exception as e:
            logger.warning(f"Global search reduce failed: {e}")
            final_answer = community_answers[0]["answer"] if community_answers else ""

        return {
            "answer": final_answer.strip(),
            "community_answers": community_answers,
            "sources": [ca["community_id"] for ca in community_answers],
        }
