"""P2 单元测试：创新点报告 — Tree-structured Exploration

不依赖真实 LLM API / PostgreSQL。
使用 FakeLLMService + 内存 mock storage。
"""

import pytest

from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator


# ── Test Explore Innovation Tree ──────────────────────


class TestExploreInnovationTree:

    def test_empty_nodes(self):
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        result = gen._explore_innovation_tree({"nodes": [], "edges": []})
        assert result == []

    def test_no_gap_nodes(self):
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "topic:A", "node_type": "Topic", "label": "Topic A"},
                {"node_id": "method:X", "node_type": "Method", "label": "Method X"},
            ],
            "edges": [
                {"source_id": "topic:A", "target_id": "method:X", "edge_type": "USES_METHOD"},
            ],
        }
        result = gen._explore_innovation_tree(graph_context)
        assert result == []

    def test_finds_cross_entity_chain(self):
        """Gap → Method → Topic → Dataset 应被检测为跨类型链路"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "gap:G1", "node_type": "Gap", "label": "缺少跨模态方法"},
                {"node_id": "method:X", "node_type": "Method", "label": "Method X"},
                {"node_id": "topic:A", "node_type": "Topic", "label": "Topic A"},
                {"node_id": "dataset:D", "node_type": "Dataset", "label": "Dataset D"},
            ],
            "edges": [
                {"source_id": "gap:G1", "target_id": "method:X", "edge_type": "ADDRESSES"},
                {"source_id": "method:X", "target_id": "topic:A", "edge_type": "BELONGS_TO_TOPIC"},
                {"source_id": "topic:A", "target_id": "dataset:D", "edge_type": "USES_DATASET"},
            ],
        }
        result = gen._explore_innovation_tree(graph_context, max_depth=3)
        assert len(result) > 0
        assert any(f["type"] == "cross_entity_chain" for f in result)
        # 应包含 gap_label
        assert any(f.get("gap_label") == "缺少跨模态方法" for f in result)

    def test_short_chain_not_reported(self):
        """只有 2 种实体类型的链路不应报告"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "gap:G1", "node_type": "Gap", "label": "Gap 1"},
                {"node_id": "method:X", "node_type": "Method", "label": "Method X"},
            ],
            "edges": [
                {"source_id": "gap:G1", "target_id": "method:X", "edge_type": "ADDRESSES"},
            ],
        }
        result = gen._explore_innovation_tree(graph_context, max_depth=2)
        # 只有 Gap + Method = 2 types, < 3 threshold
        assert len(result) == 0

    def test_max_depth_limits_exploration(self):
        """max_depth=1 只探索直接邻居"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "gap:G1", "node_type": "Gap", "label": "Gap 1"},
                {"node_id": "method:X", "node_type": "Method", "label": "Method X"},
                {"node_id": "topic:A", "node_type": "Topic", "label": "Topic A"},
                {"node_id": "dataset:D", "node_type": "Dataset", "label": "Dataset D"},
            ],
            "edges": [
                {"source_id": "gap:G1", "target_id": "method:X", "edge_type": "ADDRESSES"},
                {"source_id": "method:X", "target_id": "topic:A", "edge_type": "BELONGS_TO_TOPIC"},
                {"source_id": "topic:A", "target_id": "dataset:D", "edge_type": "USES_DATASET"},
            ],
        }
        result = gen._explore_innovation_tree(graph_context, max_depth=1)
        # depth=1: gap → method only, not enough types
        assert len(result) == 0

    def test_limits_results_to_10(self):
        """结果上限 10 条"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        nodes = [{"node_id": f"gap:G{i}", "node_type": "Gap", "label": f"Gap {i}"} for i in range(15)]
        nodes += [{"node_id": "method:X", "node_type": "Method", "label": "Method X"},
                   {"node_id": "topic:A", "node_type": "Topic", "label": "Topic A"},
                   {"node_id": "dataset:D", "node_type": "Dataset", "label": "Dataset D"}]
        edges = []
        for i in range(15):
            edges.append({"source_id": f"gap:G{i}", "target_id": "method:X", "edge_type": "ADDRESSES"})
        edges.append({"source_id": "method:X", "target_id": "topic:A", "edge_type": "BELONGS_TO_TOPIC"})
        edges.append({"source_id": "topic:A", "target_id": "dataset:D", "edge_type": "USES_DATASET"})

        result = gen._explore_innovation_tree({"nodes": nodes, "edges": edges}, max_depth=3)
        assert len(result) <= 10
