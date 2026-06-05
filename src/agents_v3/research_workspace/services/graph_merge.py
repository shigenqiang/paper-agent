"""知识图谱实体合并 Mixin"""

from __future__ import annotations

from loguru import logger

from src.agents_v3.research_workspace.models import (
    KnowledgeGraph,
    NodeType,
)

from .graph_utils import _cosine_similarity, _levenshtein


class GraphMergeMixin:
    """实体消歧：L2 编辑距离 + L3 嵌入相似度"""

    def merge_similar_entities(
        self,
        project_id: str,
        similarity_threshold: float = 0.85,
        edit_distance_threshold: int = 2,
    ) -> dict:
        """
        分层实体消歧：
        L1: 精确匹配（normalize_label + alias）— 已在构建时处理
        L2: 编辑距离 ≤ threshold
        L3: embedding 余弦相似度 ≥ threshold
        """
        graph = self.get_graph(project_id)
        if not graph:
            return {"merged_pairs": 0, "details": []}

        by_type: dict[str, list[str]] = {}
        node_map = {n.node_id: n for n in graph.nodes}
        for node in graph.nodes:
            if node.node_type == NodeType.PAPER:
                continue
            by_type.setdefault(node.node_type.value, []).append(node.node_id)

        merged_pairs: list[dict] = []
        merged_set: set[str] = set()

        for ntype, nids in by_type.items():
            if len(nids) < 2:
                continue

            labels = [node_map[nid].label.lower().strip() for nid in nids]

            # L2: 编辑距离（前缀分桶优化）
            from collections import defaultdict
            buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
            for nid, label in zip(nids, labels):
                prefix = label[:3] if len(label) >= 3 else label
                buckets[prefix].append((nid, label))

            for bucket in buckets.values():
                for i in range(len(bucket)):
                    if bucket[i][0] in merged_set:
                        continue
                    for j in range(i + 1, len(bucket)):
                        if bucket[j][0] in merged_set:
                            continue
                        dist = _levenshtein(bucket[i][1], bucket[j][1])
                        if 0 < dist <= edit_distance_threshold:
                            self._merge_node(node_map, graph, bucket[i][0], bucket[j][0])
                            merged_set.add(bucket[j][0])
                            merged_pairs.append({
                                "source": bucket[i][0], "target": bucket[j][0],
                                "method": "edit_distance", "distance": dist,
                            })

            # L3: Embedding 相似度
            remaining = [nid for nid in nids if nid not in merged_set]
            if len(remaining) < 2:
                continue

            _ACADEMIC_TYPES = {"Topic", "Method", "Finding", "Task", "Metric", "Limitation", "Gap"}

            try:
                if ntype in _ACADEMIC_TYPES:
                    try:
                        import os
                        _specter2_cached = any(
                            "specter2" in name.lower()
                            for name in os.listdir(os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"))
                            if os.path.isdir(os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub", name))
                        ) if os.path.isdir(os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")) else False

                        if not _specter2_cached:
                            raise RuntimeError("SPECTER2 model not cached locally")

                        from src.agents_v3.research_workspace.storage.embedding_provider import get_specter2_provider
                        provider = get_specter2_provider()
                        texts = [
                            (node_map[nid].label + " " + node_map[nid].properties.get("description", "")).strip()
                            for nid in remaining
                        ]
                        logger.info(f"L3 merge for {ntype}: using SPECTER2 ({provider.dimension}d)")
                    except Exception as specter_err:
                        logger.warning(f"SPECTER2 unavailable for {ntype}, falling back to MiniLM: {specter_err}")
                        from src.agents_v3.research_workspace.storage.embedding_provider import get_embedding_provider
                        provider = get_embedding_provider()
                        texts = [node_map[nid].label for nid in remaining]
                        logger.info(f"L3 merge for {ntype}: using MiniLM fallback ({provider.dimension}d)")
                else:
                    from src.agents_v3.research_workspace.storage.embedding_provider import get_embedding_provider
                    provider = get_embedding_provider()
                    texts = [node_map[nid].label for nid in remaining]
                    logger.info(f"L3 merge for {ntype}: using MiniLM ({provider.dimension}d)")

                embeddings = provider.embed_texts(texts)

                # numpy 批量计算余弦相似度
                try:
                    import numpy as np
                    mat = np.array(embeddings)
                    norms = np.linalg.norm(mat, axis=1, keepdims=True)
                    mat_norm = mat / np.maximum(norms, 1e-8)
                    sim_matrix = mat_norm @ mat_norm.T

                    pairs = np.argwhere(
                        (sim_matrix >= similarity_threshold) & (np.triu(sim_matrix, k=1) > 0)
                    )
                    for idx in pairs:
                        i, j = int(idx[0]), int(idx[1])
                        if remaining[i] in merged_set or remaining[j] in merged_set:
                            continue
                        self._merge_node(node_map, graph, remaining[i], remaining[j])
                        merged_set.add(remaining[j])
                        merged_pairs.append({
                            "source": remaining[i], "target": remaining[j],
                            "method": "embedding_similarity",
                            "similarity": round(float(sim_matrix[i, j]), 4),
                        })
                except ImportError:
                    # numpy 不可用，回退到 Python 循环
                    for i in range(len(remaining)):
                        if remaining[i] in merged_set:
                            continue
                        for j in range(i + 1, len(remaining)):
                            if remaining[j] in merged_set:
                                continue
                            sim = _cosine_similarity(embeddings[i], embeddings[j])
                            if sim >= similarity_threshold:
                                self._merge_node(node_map, graph, remaining[i], remaining[j])
                                merged_set.add(remaining[j])
                                merged_pairs.append({
                                    "source": remaining[i], "target": remaining[j],
                                    "method": "embedding_similarity", "similarity": round(sim, 4),
                                })
            except Exception as e:
                logger.warning(f"Embedding similarity merge failed for {ntype}: {e}")

        if merged_pairs:
            graph.nodes = [n for n in graph.nodes if n.node_id not in merged_set]
            self._save_graph(project_id, graph)
            logger.info(f"Merged {len(merged_pairs)} entity pairs in project {project_id}")

        return {
            "merged_pairs": len(merged_pairs),
            "details": merged_pairs[:50],
        }

    def _merge_node(
        self, node_map: dict, graph: KnowledgeGraph, keep_id: str, merge_id: str,
    ) -> None:
        """将 merge_id 节点的 provenance 合并到 keep_id 节点"""
        keep_node = node_map.get(keep_id)
        merge_node = node_map.get(merge_id)
        if not keep_node or not merge_node:
            return

        for key in ("paper_ids", "evidence_ids", "source_chunk_ids", "source_quotes"):
            existing = keep_node.properties.get(key, [])
            for item in merge_node.properties.get(key, []):
                if item not in existing:
                    existing.append(item)
            keep_node.properties[key] = existing

        for edge in graph.edges:
            if edge.source_id == merge_id:
                edge.source_id = keep_id
            if edge.target_id == merge_id:
                edge.target_id = keep_id
