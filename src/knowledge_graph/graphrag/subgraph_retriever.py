"""
子图检索器
Subgraph Retriever
"""

from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass
import numpy as np

from ..schema.academic_kg_schema import Entity, Relation
from ..storage.neo4j_client import Neo4jClient, SubgraphResult
from ..storage.vector_store import VectorStoreClient
from ..embedding.text_embedder import TextEmbedder


@dataclass
class Community:
    """社区"""
    id: int
    nodes: List[Dict]
    edges: List[Dict]
    description: str = ""


@dataclass
class CommunitySummary:
    """社区摘要"""
    community_id: int
    description: str
    core_entities: List[str]
    key_relations: List[str]
    summary_text: str


class SubgraphRetriever:
    """子图检索器"""

    def __init__(
        self,
        neo4j_client: Optional[Neo4jClient] = None,
        vector_store: Optional[VectorStoreClient] = None,
        text_embedder: Optional[TextEmbedder] = None
    ):
        self.neo4j = neo4j_client
        self.vector_store = vector_store
        self.text_embedder = text_embedder or TextEmbedder()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        depth: int = 2
    ) -> List[CommunitySummary]:
        """检索相关子图"""
        # 1. 向量相似度检索相关实体
        similar_entities = self._search_entities_by_vector(query, top_k)

        # 2. 对每个实体进行子图检索
        subgraphs = []
        for entity in similar_entities:
            subgraph = self._get_local_subgraph(entity["id"], depth)
            if subgraph.nodes:
                subgraphs.append(subgraph)

        if not subgraphs:
            return []

        # 3. 子图融合
        fused_subgraph = self._fuse_subgraphs(subgraphs)

        # 4. 社区检测
        communities = self._detect_communities(fused_subgraph)

        # 5. 生成社区摘要
        community_summaries = self._generate_summaries(communities)

        return community_summaries

    def _search_entities_by_vector(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """基于向量搜索实体"""
        if not self.vector_store:
            # 使用文本嵌入搜索
            return self._search_entities_by_text(query, top_k)

        query_embedding = self.text_embedder.embed_text(query)
        results = self.vector_store.search(
            query_vector=query_embedding.tolist(),
            top_k=top_k
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "metadata": r.metadata
            }
            for r in results
        ]

    def _search_entities_by_text(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """基于文本搜索实体（当没有向量存储时）"""
        if not self.neo4j:
            return []

        # 从Neo4j获取实体
        all_entities = []
        for entity_type in ["Paper", "Author", "Institution", "Venue"]:
            entities = self.neo4j.find_entities_by_type(entity_type, limit=top_k * 2)
            all_entities.extend(entities)

        if not all_entities:
            return []

        # 计算文本相似度
        similarities = []
        query_lower = query.lower()

        for entity in all_entities:
            entity_name = entity.get("name", "").lower()
            score = self._text_similarity(query_lower, entity_name)

            if score > 0.1:  # 阈值
                similarities.append({
                    "id": entity.get("id"),
                    "score": score,
                    "metadata": entity
                })

        # 排序并返回top_k
        similarities.sort(key=lambda x: x["score"], reverse=True)
        return similarities[:top_k]

    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度"""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        union = len(words1 | words2)

        return overlap / union if union else 0.0

    def _get_local_subgraph(
        self,
        center_id: str,
        depth: int = 2
    ) -> SubgraphResult:
        """获取局部子图"""
        if not self.neo4j:
            return SubgraphResult(nodes=[], edges=[], center_id=center_id)

        return self.neo4j.query_subgraph(center_id=center_id, depth=depth)

    def _fuse_subgraphs(self, subgraphs: List[SubgraphResult]) -> SubgraphResult:
        """融合多个子图"""
        all_nodes = []
        all_edges = []
        seen_nodes = set()
        seen_edges = set()

        for subgraph in subgraphs:
            for node in subgraph.nodes:
                node_id = node.get("id")
                if node_id and node_id not in seen_nodes:
                    all_nodes.append(node)
                    seen_nodes.add(node_id)

            for edge in subgraph.edges:
                edge_key = f"{edge.get('source')}_{edge.get('type')}_{edge.get('target')}"
                if edge_key not in seen_edges:
                    all_edges.append(edge)
                    seen_edges.add(edge_key)

        return SubgraphResult(
            nodes=all_nodes,
            edges=all_edges,
            center_id=subgraphs[0].center_id if subgraphs else ""
        )

    def _detect_communities(self, subgraph: SubgraphResult) -> List[Community]:
        """社区检测"""
        try:
            import networkx as nx
            from networkx.algorithms.community import louvain_communities
        except ImportError:
            # 如果没有networkx，返回简单分组
            return self._simple_community_detection(subgraph)

        # 转换为NetworkX图
        G = nx.Graph()

        for node in subgraph.nodes:
            G.add_node(
                node.get("id"),
                **{k: v for k, v in node.items() if k != "id"}
            )

        for edge in subgraph.edges:
            G.add_edge(
                edge.get("source"),
                edge.get("target"),
                **{k: v for k, v in edge.items() if k not in ["source", "target"]}
            )

        # Louvain社区检测
        try:
            communities = louvain_communities(G)
        except Exception:
            return self._simple_community_detection(subgraph)

        result = []
        for i, community in enumerate(communities):
            nodes = [G.nodes[node] for node in community]
            edges = [
                {
                    "source": u,
                    "target": v,
                    **G.edges[u, v]
                }
                for u, v in G.subgraph(community).edges()
            ]

            result.append(Community(
                id=i,
                nodes=nodes,
                edges=edges,
                description=""
            ))

        return result

    def _simple_community_detection(
        self,
        subgraph: SubgraphResult
    ) -> List[Community]:
        """简单的社区检测（当没有networkx时）"""
        if not subgraph.nodes:
            return []

        # 按类型简单分组
        type_groups: Dict[str, List[Dict]] = {}

        for node in subgraph.nodes:
            node_type = node.get("type", "unknown")
            if node_type not in type_groups:
                type_groups[node_type] = []
            type_groups[node_type].append(node)

        communities = []
        for i, (node_type, nodes) in enumerate(type_groups.items()):
            node_ids = [n.get("id") for n in nodes]
            communities.append(Community(
                id=i,
                nodes=nodes,
                edges=[e for e in subgraph.edges
                       if e.get("source") in node_ids
                       or e.get("target") in node_ids],
                description=f"Type: {node_type}"
            ))

        return communities

    def _generate_summaries(
        self,
        communities: List[Community]
    ) -> List[CommunitySummary]:
        """生成社区摘要"""
        summaries = []

        for community in communities:
            # 提取核心实体
            core_entities = [
                node.get("name", node.get("id", ""))
                for node in community.nodes[:5]
            ]

            # 提取关键关系
            key_relations = list(set([
                edge.get("type", "")
                for edge in community.edges
            ]))

            # 生成描述
            node_names = [n.get("name", "") for n in community.nodes[:3]]
            description = f"包含 {len(community.nodes)} 个实体，如 {', '.join(node_names)}"

            summaries.append(CommunitySummary(
                community_id=community.id,
                description=description,
                core_entities=core_entities,
                key_relations=key_relations,
                summary_text=description
            ))

        return summaries

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5
    ) -> List[List[str]]:
        """查找两个实体之间的路径"""
        if not self.neo4j:
            return []

        path_result = self.neo4j.find_shortest_path(
            source_id=source_id,
            target_id=target_id,
            max_length=max_length
        )

        if not path_result:
            return []

        # 提取路径节点序列
        paths = []
        for path in path_result.get("nodes", []):
            path_ids = [n.get("id") for n in path]
            paths.append(path_ids)

        return paths
