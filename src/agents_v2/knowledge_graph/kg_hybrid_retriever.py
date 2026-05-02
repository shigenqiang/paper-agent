"""
知识图谱混合检索模块

功能:
1. 向量相似度检索 (Vector Search)
2. 图遍历扩展 (Graph Traversal)
3. MMR去重重排序 (Maximal Marginal Relevance)
4. 混合检索融合 (Hybrid Search)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import math

logger = get_logging_logger(__name__)


class RetrievalMethod(str, Enum):
    """检索方法"""
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"


@dataclass
class RetrievalResult:
    """检索结果"""
    entity_id: str
    entity_type: str
    score: float
    method: RetrievalMethod  # 来源方法
    path: List[str] = field(default_factory=list)  # 图路径（如果来自图检索）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryContext:
    """查询上下文"""
    query: str
    entities: List[str] = field(default_factory=list)  # 提取的实体
    relations: List[Tuple[str, str, str]] = field(default_factory=list)  # (source, relation, target)
    embeddings: Optional[List[float]] = None


class VectorSearcher:
    """
    向量检索器

    支持多种向量数据库的后端
    当前实现为抽象接口
    """

    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim
        self._embeddings: Dict[str, List[float]] = {}  # 内存存储（演示用）

    def add(self, entity_id: str, embedding: List[float]) -> None:
        """添加向量"""
        self._embeddings[entity_id] = embedding

    def search(
        self,
        query_embedding: List[float],
        top_k: int,
        exclude_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        搜索最近邻

        Args:
            query_embedding: 查询向量
            top_k: 返回数量
            exclude_ids: 排除的实体ID

        Returns:
            [(entity_id, score), ...]
        """
        if not self._embeddings:
            return []

        exclude_ids = exclude_ids or set()

        # 计算余弦相似度
        scores = []
        for entity_id, embedding in self._embeddings.items():
            if entity_id in exclude_ids:
                continue

            score = self._cosine_similarity(query_embedding, embedding)
            scores.append((entity_id, score))

        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if len(v1) != len(v2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class GraphTraverser:
    """
    图遍历器

    基于Neo4j的图遍历
    """

    def __init__(self):
        # 内存图存储（演示用）
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Tuple[str, str, str]] = []  # (source, target, relation)
        self._adj: Dict[str, Dict[str, Set[str]]] = {}  # node -> {neighbor -> {relations}}
        from collections import defaultdict
        self._adj = defaultdict(lambda: defaultdict(set))

    def add_node(
        self,
        node_id: str,
        node_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加节点"""
        self._nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "properties": properties or {}
        }
        if node_id not in self._adj:
            self._adj[node_id] = {}

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str
    ) -> None:
        """添加边（双向）"""
        if source_id not in self._nodes:
            self.add_node(source_id, "Unknown")
        if target_id not in self._nodes:
            self.add_node(target_id, "Unknown")

        # 添加到边列表
        self._edges.append((source_id, target_id, relation))

        # 添加到邻接表（双向）
        if target_id not in self._adj[source_id]:
            self._adj[source_id][target_id] = set()
        self._adj[source_id][target_id].add(relation)

        # 双向添加
        if source_id not in self._adj[target_id]:
            self._adj[target_id][source_id] = set()
        self._adj[target_id][source_id].add(relation)

    def find_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        relation_types: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        查找邻居节点

        Args:
            node_id: 起始节点
            depth: 深度
            relation_types: 关系类型过滤

        Returns:
            邻居节点集合
        """
        if node_id not in self._adj:
            return set()

        visited = set()
        current_level = {node_id}
        relation_types = relation_types or None

        for _ in range(depth):
            next_level = set()
            for node in current_level:
                if node in visited:
                    continue

                for neighbor, relations in self._adj.get(node, {}).items():
                    if neighbor in visited:
                        continue
                    # 关系过滤
                    if relation_types is None or relations & relation_types:
                        next_level.add(neighbor)

            visited.update(current_level)
            current_level = next_level

        # 返回所有层的邻居（不包括起始节点）
        result = set()
        for level in range(1, depth + 1):
            level_nodes = set()
            current = {node_id}
            for _ in range(level):
                next_nodes = set()
                for n in current:
                    next_nodes.update(self._adj.get(n, {}).keys())
                level_nodes.update(next_nodes)
                current = next_nodes
            result.update(level_nodes)

        result.discard(node_id)
        return result

    def find_paths(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3
    ) -> List[List[str]]:
        """
        查找路径

        Returns:
            路径列表，每条路径是节点ID列表
        """
        if start_id not in self._adj or end_id not in self._adj:
            return []

        paths = []

        def dfs(current: str, target: str, path: List[str], visited: Set[str]):
            if current == target:
                paths.append(path.copy())
                return

            if len(path) >= max_depth:
                return

            for neighbor in self._adj.get(current, {}):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                path.append(neighbor)
                dfs(neighbor, target, path, visited)
                path.pop()
                visited.remove(neighbor)

        dfs(start_id, end_id, [start_id], {start_id})

        return paths

    def get_subgraph(
        self,
        node_ids: Set[str],
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        获取子图

        Returns:
            {
                "nodes": [...],
                "edges": [...]
            }
        """
        # 扩展节点集合
        expanded = node_ids.copy()
        for node_id in node_ids:
            neighbors = self.find_neighbors(node_id, depth)
            expanded.update(neighbors)

        # 收集节点
        nodes = [
            self._nodes[n]
            for n in expanded
            if n in self._nodes
        ]

        # 收集边
        edges = [
            {"source": s, "target": t, "relation": r}
            for s, t, r in self._edges
            if s in expanded and t in expanded
        ]

        return {"nodes": nodes, "edges": edges}


class MMRReranker:
    """
    Maximal Marginal Relevance (MMR) 重排序

    在相关性和多样性之间取得平衡

    MMR = argmax [λ * sim(query, doc) - (1-λ) * max(sim(doc_i, doc_j))]
    """

    def __init__(self, lambda_param: float = 0.5):
        """
        Args:
            lambda_param: 相关性权重
                        λ 接近 1: 重视相关性
                        λ 接近 0: 重视多样性
        """
        self.lambda_param = lambda_param
        self._embeddings: Dict[str, List[float]] = {}

    def set_embeddings(self, embeddings: Dict[str, List[float]]) -> None:
        """设置文档嵌入向量"""
        self._embeddings = embeddings

    def rerank(
        self,
        query_embedding: List[float],
        candidates: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """
        MMR重排序

        Args:
            query_embedding: 查询向量
            candidates: 候选结果
            top_k: 返回数量

        Returns:
            重排序后的结果
        """
        if not candidates:
            return []

        selected = []
        remaining = candidates.copy()

        while len(selected) < top_k and remaining:
            best_score = -float('inf')
            best_candidate = None
            best_index = -1

            for i, candidate in enumerate(remaining):
                # 相关性分数
                relevance = candidate.score

                # 多样性分数：与已选中文档的最大相似度
                diversity = 0.0
                if selected:
                    cand_emb = self._embeddings.get(candidate.entity_id)
                    if cand_emb:
                        max_sim = max(
                            self._cosine_similarity(
                                cand_emb,
                                self._embeddings.get(s.entity_id, [0] * len(cand_emb))
                            )
                            for s in selected
                        )
                        diversity = max_sim

                # MMR分数
                mmr_score = (
                    self.lambda_param * relevance
                    - (1 - self.lambda_param) * diversity
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate
                    best_index = i

            if best_candidate is not None:
                selected.append(best_candidate)
                remaining.pop(best_index)

        return selected

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if len(v1) != len(v2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class HybridRetriever:
    """
    混合检索器

    结合向量检索和图遍历，通过MMR融合结果
    """

    def __init__(
        self,
        vector_weight: float = 0.5,
        graph_weight: float = 0.3,
        mmr_lambda: float = 0.5
    ):
        """
        Args:
            vector_weight: 向量检索权重
            graph_weight: 图遍历权重
            mmr_lambda: MMR lambda参数
        """
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.vector_searcher = VectorSearcher()
        self.graph_traverser = GraphTraverser()
        self.mmr_reranker = MMRReranker(lambda_param=mmr_lambda)

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        embedding: List[float],
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加实体"""
        self.vector_searcher.add(entity_id, embedding)
        self.graph_traverser.add_node(entity_id, entity_type, properties)

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation: str
    ) -> None:
        """添加关系"""
        self.graph_traverser.add_edge(source_id, target_id, relation)

    def retrieve(
        self,
        query_embedding: List[float],
        initial_entities: Optional[List[str]] = None,
        top_k: int = 10,
        depth: int = 2,
        use_mmr: bool = True
    ) -> List[RetrievalResult]:
        """
        混合检索

        流程:
        1. 向量检索获取候选
        2. 如果有初始实体，图扩展
        3. MMR融合
        4. 返回top_k结果

        Args:
            query_embedding: 查询向量
            initial_entities: 初始实体列表（用于图扩展）
            top_k: 返回数量
            depth: 图扩展深度
            use_mmr: 是否使用MMR

        Returns:
            检索结果
        """
        all_results: Dict[str, RetrievalResult] = {}

        # 1. 向量检索
        vector_results = self.vector_searcher.search(
            query_embedding,
            top_k=top_k * 2  # 获取更多用于后续筛选
        )

        for entity_id, score in vector_results:
            all_results[entity_id] = RetrievalResult(
                entity_id=entity_id,
                entity_type=self.graph_traverser._nodes.get(entity_id, {}).get("type", "Unknown"),
                score=score * self.vector_weight,
                method=RetrievalMethod.VECTOR_ONLY
            )

        # 2. 图扩展
        if initial_entities:
            for entity_id in initial_entities:
                neighbors = self.graph_traverser.find_neighbors(
                    entity_id,
                    depth=depth
                )

                for neighbor_id in neighbors:
                    if neighbor_id in all_results:
                        # 增加已有实体的分数
                        all_results[neighbor_id].score += self.graph_weight
                    else:
                        all_results[neighbor_id] = RetrievalResult(
                            entity_id=neighbor_id,
                            entity_type=self.graph_traverser._nodes.get(neighbor_id, {}).get("type", "Unknown"),
                            score=self.graph_weight,
                            method=RetrievalMethod.GRAPH_ONLY
                        )

        # 3. 转换为列表并排序
        candidates = list(all_results.values())
        candidates.sort(key=lambda x: x.score, reverse=True)

        # 4. MMR重排序
        if use_mmr and candidates:
            self.mmr_reranker.set_embeddings(self.vector_searcher._embeddings)
            candidates = self.mmr_reranker.rerank(
                query_embedding,
                candidates,
                top_k
            )

        return candidates[:top_k]

    def get_subgraph(
        self,
        entity_ids: List[str],
        depth: int = 1
    ) -> Dict[str, Any]:
        """获取相关子图"""
        entity_set = set(entity_ids)
        return self.graph_traverser.get_subgraph(entity_set, depth)


class EntityLinker:
    """
    实体链接器

    从查询文本中提取并链接实体
    """

    def __init__(self):
        self.entity_patterns = {
            # 论文: #1, Paper XXX
            "paper": [
                r"paper\s+['\"]?([^'\"]+)['\"]?",
                r"Paper['\"]?\s+([^,\.]+)",
                r"#(\d+)"  # 引用编号
            ],
            # 作者: Author Name
            "author": [
                r"by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
                r"author\s+([A-Z][a-z]+\s+[A-Z][a-z]+)"
            ],
            # 方法: CNN, Transformer等
            "method": [
                r"\b(CNN|RNN|LSTM|GAN|Transformer|BERT|GPT)\b",
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:model|network|architecture)\b"
            ]
        }

    def extract_entities(self, query: str) -> List[Tuple[str, str]]:
        """
        从查询中提取实体

        Returns:
            [(entity_name, entity_type), ...]
        """
        import re
        results = []

        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[-1]
                    results.append((match.strip(), entity_type))

        return results

    def link_entities(
        self,
        entities: List[Tuple[str, str]],
        known_entities: Dict[str, str]  # entity_name -> entity_id
    ) -> List[str]:
        """
        链接实体到知识图谱

        Returns:
            entity_ids列表
        """
        entity_ids = []

        for entity_name, entity_type in entities:
            # 精确匹配
            if entity_name in known_entities:
                entity_ids.append(known_entities[entity_name])
                continue

            # 模糊匹配（双向包含检查）
            matched = False
            for known_name, entity_id in known_entities.items():
                e_lower = entity_name.lower()
                k_lower = known_name.lower()
                # entity_name在known_name中 或 known_name在entity_name中
                if e_lower in k_lower or k_lower in e_lower:
                    entity_ids.append(entity_id)
                    matched = True
                    break

        return entity_ids

        return entity_ids
