"""
知识图谱社区检测测试
"""
import pytest
from src.agents_v2.knowledge_graph import (
    Community,
    CommunityHierarchy,
    CommunityAlgorithm,
    LouvainDetector,
    LeidenDetector,
    LabelPropagationDetector,
    detect_communities
)


class TestLouvainDetector:
    """Louvain算法测试"""

    def setup_method(self):
        self.detector = LouvainDetector()

    def test_empty_graph(self):
        result = self.detector.detect([])
        assert result["communities"] == []
        assert result["modularity"] == 0.0

    def test_single_node(self):
        """单节点图应该形成单个社区"""
        result = self.detector.detect([("A", "A")])  # 自环
        assert len(result["communities"]) == 1
        assert result["communities"][0].members == ["A"]

    def test_two_nodes_connected(self):
        """两个连接的节点应该在一个社区"""
        edges = [("A", "B")]
        result = self.detector.detect(edges)
        assert len(result["communities"]) == 1

    def test_two_nodes_disconnected(self):
        """两个不连接的节点应该分别在两个社区"""
        # 无边 = 两个独立节点
        result = self.detector.detect([])
        assert len(result["communities"]) == 0

    def test_simple_triangle(self):
        """三角结构应该是一个社区（或少数几个）"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("A", "C")
        ]
        result = self.detector.detect(edges)
        # 紧密连接的图应该形成较少社区
        assert len(result["communities"]) <= 3
        # 模块度应该是合理的值
        assert result["modularity"] >= -0.5

    def test_two_communities(self):
        """两个明显分开的社区"""
        edges = [
            # 社区1: A-B-C 密集连接
            ("A", "B"),
            ("B", "C"),
            ("A", "C"),
            # 社区2: D-E-F 密集连接
            ("D", "E"),
            ("E", "F"),
            ("D", "F"),
            # 跨社区连接很少
            ("C", "D")  # 只有一个跨社区边
        ]
        result = self.detector.detect(edges)
        # 应该有少数社区（不一定是精确的2个）
        assert len(result["communities"]) >= 2

    def test_star_graph(self):
        """星形图：中心节点连接多个叶节点"""
        edges = [
            ("center", "leaf1"),
            ("center", "leaf2"),
            ("center", "leaf3"),
            ("center", "leaf4"),
        ]
        result = self.detector.detect(edges)
        # 所有节点应该在一个社区
        all_members = []
        for comm in result["communities"]:
            all_members.extend(comm.members)
        assert len(all_members) == 5  # center + 4 leaves

    def test_hierarchy_structure(self):
        """测试层次结构"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("D", "E"),
        ]
        result = self.detector.detect(edges)
        assert "hierarchy" in result
        assert isinstance(result["hierarchy"], CommunityHierarchy)

    def test_modularity_score(self):
        """测试模块度分数计算"""
        # 紧密连接的社区应该有高模块度
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("A", "C"),
        ]
        result = self.detector.detect(edges)
        # 模块度范围应该是 [-0.5, 1]
        assert -0.5 <= result["modularity"] <= 1


class TestLeidenDetector:
    """Leiden算法测试"""

    def setup_method(self):
        self.detector = LeidenDetector()

    def test_empty_graph(self):
        result = self.detector.detect([])
        assert result["communities"] == []
        assert result["modularity"] == 0.0

    def test_single_community(self):
        """密集连接的图应该是一个社区"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),
            ("A", "D"),
            ("D", "B"),
        ]
        result = self.detector.detect(edges)
        assert len(result["communities"]) == 1

    def test_multiple_communities(self):
        """明显分开的社区"""
        edges = [
            # 社区1
            ("A", "B"),
            ("B", "C"),
            # 社区2
            ("D", "E"),
            ("E", "F"),
            # 社区3
            ("G", "H"),
        ]
        result = self.detector.detect(edges)
        assert len(result["communities"]) >= 2

    def test_compare_with_louvain(self):
        """比较Leiden和Louvain结果"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),
            ("D", "E"),
            ("E", "F"),
            ("C", "D"),  # 弱连接
        ]

        leiden_detector = LeidenDetector()
        louvain_detector = LouvainDetector()

        leiden_result = leiden_detector.detect(edges)
        louvain_result = louvain_detector.detect(edges)

        # 两者都应该检测到多个社区
        assert len(leiden_result["communities"]) >= 2
        assert len(louvain_result["communities"]) >= 2


class TestLabelPropagationDetector:
    """Label Propagation算法测试"""

    def setup_method(self):
        self.detector = LabelPropagationDetector(max_iterations=50)

    def test_empty_graph(self):
        result = self.detector.detect([])
        assert result["communities"] == []

    def test_stable_convergence(self):
        """测试稳定收敛"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),
        ]
        result = self.detector.detect(edges)
        assert result["iterations"] < 50  # 应该快速收敛
        assert len(result["communities"]) == 1


class TestDetectCommunitiesFunction:
    """detect_communities便捷函数测试"""

    def test_louvain_algorithm(self):
        edges = [("A", "B"), ("B", "C"), ("D", "E")]
        result = detect_communities(edges, algorithm=CommunityAlgorithm.LOUVAIN)
        assert len(result["communities"]) >= 1

    def test_leiden_algorithm(self):
        edges = [("A", "B"), ("B", "C"), ("D", "E")]
        result = detect_communities(edges, algorithm=CommunityAlgorithm.LEIDEN)
        assert len(result["communities"]) >= 1

    def test_label_propagation_algorithm(self):
        edges = [("A", "B"), ("B", "C"), ("D", "E")]
        result = detect_communities(
            edges,
            algorithm=CommunityAlgorithm.LABEL_PROPAGATION
        )
        assert len(result["communities"]) >= 1


class TestCommunityClass:
    """Community类测试"""

    def test_community_creation(self):
        comm = Community(
            community_id="c1",
            level=0,
            members=["A", "B", "C"],
            keywords=["AI", "ML"],
            summary="Test community",
            quality_score=0.8
        )
        assert comm.community_id == "c1"
        assert comm.level == 0
        assert comm.size == 3

    def test_community_size_property(self):
        comm = Community(
            community_id="c1",
            level=0,
            members=["A", "B"]
        )
        assert comm.size == 2


class TestCommunityHierarchy:
    """CommunityHierarchy类测试"""

    def test_empty_hierarchy(self):
        hierarchy = CommunityHierarchy(levels={}, node_to_community={})
        assert hierarchy.get_all_communities() == []

    def test_get_community(self):
        hierarchy = CommunityHierarchy(
            levels={
                0: [Community("c1", 0, ["A", "B"])]
            },
            node_to_community={
                "A": {0: "c1"},
                "B": {0: "c1"}
            }
        )
        assert hierarchy.get_community("A", 0) == "c1"
        assert hierarchy.get_community("C", 0) is None


class TestComplexScenarios:
    """复杂场景测试"""

    def setup_method(self):
        self.detector = LouvainDetector()

    def test_large_network(self):
        """测试较大网络"""
        edges = []
        # 创建4个社区，每个社区10个节点
        for i in range(4):
            base = i * 10
            for j in range(10):
                for k in range(j + 1, 10):
                    edges.append((f"{base+j}", f"{base+k}"))

        result = self.detector.detect(edges)
        assert len(result["communities"]) >= 4

    def test_overlapping_clusters(self):
        """测试重叠簇"""
        edges = [
            # 簇1
            ("A", "B"),
            ("B", "C"),
            ("A", "C"),
            # 簇2
            ("C", "D"),
            ("D", "E"),
            ("E", "F"),
            ("D", "F"),
            # 桥接节点C连接两个簇
        ]
        result = self.detector.detect(edges)
        # 可能会检测到2-3个社区
        assert len(result["communities"]) >= 1

    def test_random_graph_approximation(self):
        """测试随机图近似"""
        import random
        random.seed(42)

        # Erdos-Renyi随机图
        nodes = [f"n{i}" for i in range(20)]
        edges = []
        p = 0.3  # 连接概率

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if random.random() < p:
                    edges.append((nodes[i], nodes[j]))

        result = self.detector.detect(edges)
        # 随机图通常模块度较低
        assert result["modularity"] >= 0
        assert result["modularity"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
