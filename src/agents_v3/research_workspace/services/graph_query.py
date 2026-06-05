"""知识图谱查询 Mixin — 读取、搜索、上下文构建"""

from __future__ import annotations

from loguru import logger

from src.agents_v3.research_workspace.models import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
)

from .graph_utils import _build_adjacency


class GraphQueryMixin:
    """图谱读取/查询 API"""

    def get_graph(self, project_id: str) -> KnowledgeGraph:
        """读取图谱，优先从 graphs collection，兼容旧格式"""
        graphs = self.storage.query("graphs", {"project_id": project_id})
        if graphs:
            return KnowledgeGraph(**graphs[0])
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
        adjacency = _build_adjacency(graph)

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
        adjacency = _build_adjacency(graph)
        node_map = {n.node_id: n for n in graph.nodes}
        edge_map = {e.edge_id: e for e in graph.edges}

        paths: list[dict] = []
        queue = [(source_id, [source_id], [])]

        while queue:
            current, node_path, edge_path = queue.pop(0)
            if current == target_id:
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

    def search_nodes(
        self,
        project_id: str,
        query: str,
        node_types: list[str] | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """简单 label 包含匹配搜索节点"""
        graph = self.get_graph(project_id)
        if not graph:
            return []
        query_lower = query.lower().strip()
        results = []
        for node in graph.nodes:
            if node_types and node.node_type.value not in node_types:
                continue
            label = node.label.lower()
            normalized = node.properties.get("normalized_label", "").lower()
            if query_lower in label or query_lower in normalized:
                results.append({
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "label": node.label,
                    "paper_count": len(node.properties.get("paper_ids", [])),
                    "evidence_count": len(node.properties.get("evidence_ids", [])),
                })
        return results[:top_k]

    def build_graph_context(
        self,
        project_id: str,
        graph_node_ids: list[str],
        hops: int = 1,
        token_budget: int = 4000,
    ) -> dict:
        """为 QA 构建紧凑的 GraphRAG 上下文"""
        scope = self.resolve_graph_scope(project_id, graph_node_ids, hops=hops)
        graph = self.get_graph(project_id)
        node_map = {n.node_id: n for n in graph.nodes}

        relations = []
        subgraph = self.get_subgraph(project_id, graph_node_ids, hops=hops)
        for edge in subgraph.get("edges", []):
            src = node_map.get(edge.get("source_id", ""))
            tgt = node_map.get(edge.get("target_id", ""))
            if src and tgt:
                ev_ids = edge.get("properties", {}).get("evidence_ids", [])[:2]
                relations.append(
                    f"{src.label} --{edge.get('edge_type', '')}--> {tgt.label}"
                    + (f" ({', '.join(ev_ids)})" if ev_ids else "")
                )

        context_parts = [
            "[Graph Scope]",
            f"Selected: {', '.join(node_map[nid].label for nid in graph_node_ids if nid in node_map)}",
            f"Hops: {hops}",
            f"Related papers: {', '.join(scope['paper_ids'][:10])}",
            f"Related evidence: {len(scope['evidence_ids'])} records",
            "",
            "[Key Relations]",
            *relations[:20],
        ]

        text = "\n".join(context_parts)
        estimated_tokens = len(text) // 2

        return {
            "context_text": text,
            "paper_ids": scope["paper_ids"],
            "evidence_ids": scope["evidence_ids"],
            "estimated_tokens": estimated_tokens,
            "warnings": scope.get("warnings", []),
        }

    def build_graph_summary(self, project_id: str) -> dict:
        """为全局问题生成 Topic/Gap 层面的摘要"""
        graph = self.get_graph(project_id)
        if not graph:
            return {}

        topic_nodes = [n for n in graph.nodes if n.node_type == NodeType.TOPIC]
        topic_stats = []
        for t in sorted(topic_nodes, key=lambda n: len(n.properties.get("paper_ids", [])), reverse=True):
            topic_stats.append({
                "label": t.label,
                "paper_count": len(t.properties.get("paper_ids", [])),
                "evidence_count": len(t.properties.get("evidence_ids", [])),
            })

        method_nodes = [n for n in graph.nodes if n.node_type == NodeType.METHOD]
        method_stats = []
        for m in sorted(method_nodes, key=lambda n: len(n.properties.get("paper_ids", [])), reverse=True):
            method_stats.append({
                "label": m.label,
                "paper_count": len(m.properties.get("paper_ids", [])),
            })

        gap_nodes = [n for n in graph.nodes if n.node_type == NodeType.GAP]
        gap_stats = []
        for g in sorted(gap_nodes, key=lambda n: n.properties.get("confidence", 0), reverse=True):
            gap_stats.append({
                "label": g.label,
                "confidence": g.properties.get("confidence", 0),
                "supporting_paper_count": len(g.properties.get("supporting_paper_ids", [])),
            })

        task_nodes = [n for n in graph.nodes if n.node_type == NodeType.TASK]
        task_stats = []
        for t in sorted(task_nodes, key=lambda n: len(n.properties.get("paper_ids", [])), reverse=True):
            task_stats.append({
                "label": t.label,
                "paper_count": len(t.properties.get("paper_ids", [])),
            })

        return {
            "top_topics": topic_stats[:10],
            "top_methods": method_stats[:10],
            "top_gaps": gap_stats[:10],
            "top_tasks": task_stats[:10],
            "total_papers": len([n for n in graph.nodes if n.node_type == NodeType.PAPER]),
            "total_evidence": len(set(
                eid for n in graph.nodes
                for eid in n.properties.get("evidence_ids", [])
            )),
        }

    def local_search(
        self, project_id: str, question: str, seed_node_ids: list[str],
        hops: int = 2, max_communities: int = 3,
    ) -> dict:
        """GraphRAG Local Search: 实体中心检索 + 社区上下文 + LLM 生成"""
        from src.agents_v3.research_workspace.llm.service import get_llm_service

        llm = get_llm_service()
        graph = self.get_graph(project_id)
        if not graph or not graph.nodes:
            return {"answer": "", "sources": [], "context_nodes": []}

        node_map = {n.node_id: n for n in graph.nodes}

        # 1. 多跳邻居展开
        subgraph = self.get_subgraph(project_id, seed_node_ids, hops=hops)

        # 2. 提取关联的社区节点
        community_ids = []
        for n in subgraph.get("nodes", []):
            if n.get("node_type") == "Community":
                community_ids.append(n["node_id"])

        # 3. 构建上下文文本
        context_parts = []
        non_paper = [n for n in subgraph.get("nodes", []) if not n.get("node_id", "").startswith("paper:")]
        if non_paper:
            context_parts.append("[相关实体]")
            for n in non_paper[:20]:
                label = n.get("label", "?")[:40]
                ntype = n.get("node_type", "?")
                context_parts.append(f"  {ntype}: {label}")

        edges = subgraph.get("edges", [])
        if edges:
            context_parts.append("[关系]")
            label_map = {n["node_id"]: n.get("label", "?")[:30] for n in subgraph.get("nodes", [])}
            for e in edges[:20]:
                src = label_map.get(e.get("source_id", ""), "?")
                tgt = label_map.get(e.get("target_id", ""), "?")
                rel = e.get("edge_type", "?")
                context_parts.append(f"  {src} --{rel}--> {tgt}")

        # 4. 社区摘要
        for cid in community_ids[:max_communities]:
            node = node_map.get(cid)
            if node and node.properties.get("summary"):
                context_parts.append(f"[社区摘要] {node.properties['summary'][:200]}")

        context_text = "\n".join(context_parts) if context_parts else "无相关图谱上下文"

        # 5. LLM 生成
        prompt = (
            f"基于以下图谱上下文回答问题。引用具体的实体和关系。\n\n"
            f"{context_text}\n\n问题: {question}\n回答:"
        )
        answer = llm.invoke("你是学术研究分析专家。基于知识图谱回答问题。", prompt)

        related_papers: set[str] = set()
        related_evidence: set[str] = set()
        for n in subgraph.get("nodes", []):
            for pid in n.get("properties", {}).get("paper_ids", []):
                related_papers.add(pid)
            for eid in n.get("properties", {}).get("evidence_ids", []):
                related_evidence.add(eid)

        return {
            "answer": answer,
            "sources": list(related_papers)[:10],
            "evidence_ids": list(related_evidence)[:10],
            "context_nodes": [n["node_id"] for n in non_paper[:10]],
        }
