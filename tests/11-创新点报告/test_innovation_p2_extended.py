"""P2 扩展测试：创新点报告深层分支覆盖

覆盖：循环图处理、单节点路径、多种 Gap 类型
"""

import pytest

from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator


class TestExploreInnovationTreeCycles:

    def test_cyclic_graph_no_infinite_loop(self):
        """循环图不应导致无限循环"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "gap:G1", "node_type": "Gap", "label": "Gap 1"},
                {"node_id": "method:X", "node_type": "Method", "label": "Method X"},
                {"node_id": "topic:A", "node_type": "Topic", "label": "Topic A"},
            ],
            "edges": [
                {"source_id": "gap:G1", "target_id": "method:X", "edge_type": "SUGGESTS_GAP"},
                {"source_id": "method:X", "target_id": "topic:A", "edge_type": "BELONGS_TO_TOPIC"},
                {"source_id": "topic:A", "target_id": "method:X", "edge_type": "USES_METHOD"},  # 循环
            ],
        }
        # 应在有限时间内完成，不卡死
        result = gen._explore_innovation_tree(graph_context, max_depth=3)
        assert isinstance(result, list)

    def test_self_loop_node(self):
        """自环节点不应导致问题"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "gap:G1", "node_type": "Gap", "label": "Gap 1"},
                {"node_id": "method:X", "node_type": "Method", "label": "Method X"},
            ],
            "edges": [
                {"source_id": "gap:G1", "target_id": "method:X", "edge_type": "SUGGESTS_GAP"},
                {"source_id": "method:X", "target_id": "method:X", "edge_type": "CONJUNCTION"},  # 自环
            ],
        }
        result = gen._explore_innovation_tree(graph_context, max_depth=3)
        assert isinstance(result, list)

    def test_multiple_gaps_independent(self):
        """多个 Gap 独立探索，结果合并"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "gap:G1", "node_type": "Gap", "label": "Gap 1"},
                {"node_id": "gap:G2", "node_type": "Gap", "label": "Gap 2"},
                {"node_id": "method:X", "node_type": "Method", "label": "Method X"},
                {"node_id": "topic:A", "node_type": "Topic", "label": "Topic A"},
                {"node_id": "dataset:D", "node_type": "Dataset", "label": "Dataset D"},
            ],
            "edges": [
                {"source_id": "gap:G1", "target_id": "method:X", "edge_type": "SUGGESTS_GAP"},
                {"source_id": "method:X", "target_id": "topic:A", "edge_type": "BELONGS_TO_TOPIC"},
                {"source_id": "topic:A", "target_id": "dataset:D", "edge_type": "USES_DATASET"},
                {"source_id": "gap:G2", "target_id": "topic:A", "edge_type": "SUGGESTS_GAP"},
            ],
        }
        result = gen._explore_innovation_tree(graph_context, max_depth=3)
        # G1 路径有 3+ types，应有发现
        assert len(result) > 0

    def test_finding_node_type_included(self):
        """Finding 类型节点也应被检测为跨类型链路"""
        gen = InnovationReportGenerator.__new__(InnovationReportGenerator)
        graph_context = {
            "nodes": [
                {"node_id": "gap:G1", "node_type": "Gap", "label": "Gap 1"},
                {"node_id": "finding:F1", "node_type": "Finding", "label": "Finding 1"},
                {"node_id": "topic:A", "node_type": "Topic", "label": "Topic A"},
                {"node_id": "dataset:D", "node_type": "Dataset", "label": "Dataset D"},
            ],
            "edges": [
                {"source_id": "gap:G1", "target_id": "finding:F1", "edge_type": "SUGGESTS_GAP"},
                {"source_id": "finding:F1", "target_id": "topic:A", "edge_type": "BELONGS_TO_TOPIC"},
                {"source_id": "topic:A", "target_id": "dataset:D", "edge_type": "USES_DATASET"},
            ],
        }
        result = gen._explore_innovation_tree(graph_context, max_depth=3)
        assert any(f["type"] == "cross_entity_chain" for f in result)
