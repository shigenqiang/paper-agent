"""知识图谱 Gap 检测 Mixin"""

from __future__ import annotations

from loguru import logger

from src.agents_v3.research_workspace.models import NodeType

from .graph_utils import _build_adjacency


class GraphGapMixin:
    """Gap 检测：基础 + 增强"""

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

    def find_research_gaps_enhanced(self, project_id: str) -> dict:
        """
        增强的 Gap 检测：
        1. future_work 和 possible_gaps 聚合
        2. Method-Dataset 稀疏矩阵
        3. 稀疏区域检测（低连接度节点）
        """
        graph = self.get_graph(project_id)
        if not graph:
            return {"gaps": [], "method_dataset_matrix": {}, "sparse_regions": []}

        node_map = {n.node_id: n for n in graph.nodes}
        adjacency = _build_adjacency(graph)

        gap_nodes = [n for n in graph.nodes if n.node_type == NodeType.GAP]
        future_work_gaps = [
            n for n in gap_nodes
            if "future_work" in n.properties.get("source_types", [])
        ]
        possible_gaps = [
            n for n in gap_nodes
            if "possible_gap" in n.properties.get("source_types", [])
        ]
        limitation_gaps = [
            n for n in gap_nodes
            if "limitation" in n.properties.get("source_types", [])
        ]

        method_nodes = [n for n in graph.nodes if n.node_type == NodeType.METHOD]
        dataset_nodes = [n for n in graph.nodes if n.node_type == NodeType.DATASET]

        method_papers: dict[str, set[str]] = {}
        for m in method_nodes:
            method_papers[m.node_id] = set(m.properties.get("paper_ids", []))
        dataset_papers: dict[str, set[str]] = {}
        for d in dataset_nodes:
            dataset_papers[d.node_id] = set(d.properties.get("paper_ids", []))

        sparse_pairs: list[dict] = []
        for m in method_nodes:
            for d in dataset_nodes:
                shared = method_papers[m.node_id] & dataset_papers[d.node_id]
                if not shared:
                    sparse_pairs.append({
                        "method": m.label,
                        "dataset": d.label,
                        "method_id": m.node_id,
                        "dataset_id": d.node_id,
                    })

        sparse_nodes: list[dict] = []
        for node in graph.nodes:
            if node.node_type == NodeType.PAPER:
                continue
            degree = len(adjacency.get(node.node_id, []))
            if degree <= 1 and node.node_type not in (NodeType.GAP, NodeType.COMMUNITY):
                sparse_nodes.append({
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "label": node.label,
                    "degree": degree,
                    "paper_count": len(node.properties.get("paper_ids", [])),
                })

        temporal_gaps = self._detect_temporal_gaps(graph, node_map)

        return {
            "gaps": {
                "future_work": [n.model_dump() for n in future_work_gaps],
                "possible_gaps": [n.model_dump() for n in possible_gaps],
                "from_limitations": [n.model_dump() for n in limitation_gaps],
                "total": len(gap_nodes),
            },
            "method_dataset_matrix": {
                "total_methods": len(method_nodes),
                "total_datasets": len(dataset_nodes),
                "sparse_pairs_count": len(sparse_pairs),
                "sparse_pairs": sparse_pairs[:20],
            },
            "sparse_regions": {
                "count": len(sparse_nodes),
                "nodes": sparse_nodes[:20],
            },
            "temporal_gaps": temporal_gaps,
        }

    def _detect_temporal_gaps(self, graph, node_map) -> list[dict]:
        """时间维度 Gap 检测：declining methods, stale topics, unpaired datasets"""
        from datetime import datetime

        current_year = datetime.now().year
        temporal_gaps: list[dict] = []

        method_nodes = [n for n in graph.nodes if n.node_type == NodeType.METHOD]
        topic_nodes = [n for n in graph.nodes if n.node_type == NodeType.TOPIC]
        dataset_nodes = [n for n in graph.nodes if n.node_type == NodeType.DATASET]

        # 1. 方法热度下降
        for m in method_nodes:
            paper_ids = m.properties.get("paper_ids", [])
            if len(paper_ids) < 2:
                continue
            years = self._get_paper_years(paper_ids, node_map)
            if years and current_year - max(years) >= 3:
                temporal_gaps.append({
                    "type": "declining_method",
                    "description": f"方法 {m.label} 最近论文年份为 {max(years)}，已 {current_year - max(years)} 年无新进展",
                    "method": m.label,
                    "last_year": max(years),
                    "confidence": 0.6,
                })

        # 2. 主题过时
        for t in topic_nodes:
            paper_ids = t.properties.get("paper_ids", [])
            if len(paper_ids) < 2:
                continue
            years = self._get_paper_years(paper_ids, node_map)
            if years and current_year - max(years) >= 5:
                temporal_gaps.append({
                    "type": "stale_topic",
                    "description": f"主题 {t.label} 最近论文年份为 {max(years)}，可能已过时",
                    "topic": t.label,
                    "last_year": max(years),
                    "confidence": 0.5,
                })

        # 3. 数据集未搭配新方法
        for d in dataset_nodes:
            d_years = self._get_paper_years(d.properties.get("paper_ids", []), node_map)
            if not d_years:
                continue
            d_max = max(d_years)
            for m in method_nodes:
                m_years = self._get_paper_years(m.properties.get("paper_ids", []), node_map)
                if not m_years:
                    continue
                m_max = max(m_years)
                if m_max - d_max >= 3:
                    temporal_gaps.append({
                        "type": "dataset_method_gap",
                        "description": f"数据集 {d.label} 最新年份 {d_max}，但方法 {m.label} 有 {m_max} 年论文，可尝试用新方法在该数据集上验证",
                        "dataset": d.label,
                        "method": m.label,
                        "dataset_year": d_max,
                        "method_year": m_max,
                        "confidence": 0.5,
                    })

        return temporal_gaps

    @staticmethod
    def _get_paper_years(paper_ids: list[str], node_map) -> list[int]:
        """从 paper_ids 提取年份列表"""
        years = []
        for pid in paper_ids:
            paper_node = node_map.get(f"paper:{pid}")
            if paper_node:
                year = paper_node.properties.get("year")
                if year:
                    years.append(int(year))
        return years
