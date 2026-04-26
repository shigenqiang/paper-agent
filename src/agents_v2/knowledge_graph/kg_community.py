"""
知识图谱社区检测模块

实现:
1. Leiden算法 - 高精度层次化社区检测
2. Louvain算法 - 经典模块度优化算法
3. Label Propagation - 大规模快速检测
4. 社区层次结构管理
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


class CommunityAlgorithm(str, Enum):
    """社区检测算法"""
    LEIDEN = "leiden"
    LOUVAIN = "louvain"
    LABEL_PROPAGATION = "label_propagation"


@dataclass
class Community:
    """社区"""
    community_id: str
    level: int
    members: List[str]  # 节点ID列表
    keywords: List[str] = field(default_factory=list)
    summary: str = ""
    quality_score: float = 0.0  # 模块度分数

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass
class CommunityHierarchy:
    """社区层次结构"""
    levels: Dict[int, List[Community]]  # level -> communities
    node_to_community: Dict[str, Dict[int, str]]  # node_id -> {level: community_id}

    def get_community(self, node_id: str, level: int = 0) -> Optional[str]:
        """获取节点所属社区"""
        return self.node_to_community.get(node_id, {}).get(level)

    def get_all_communities(self) -> List[Community]:
        """获取所有层级的所有社区"""
        communities = []
        for level_communities in self.levels.values():
            communities.extend(level_communities)
        return communities


class BaseCommunityDetector:
    """社区检测基类"""

    def detect(self, edges: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        检测社区

        Args:
            edges: 边列表 [(source, target), ...]

        Returns:
            {
                "communities": [Community, ...],
                "hierarchy": CommunityHierarchy,
                "modularity": float
            }
        """
        raise NotImplementedError

    def _build_adjacency(self, edges: List[Tuple[str, str]]) -> Dict[str, Set[str]]:
        """构建邻接表"""
        adj = defaultdict(set)
        for src, dst in edges:
            adj[src].add(dst)
            adj[dst].add(src)
        return dict(adj)

    def _compute_modularity(
        self,
        edges: List[Tuple[str, str]],
        partition: Dict[str, str]
    ) -> float:
        """
        计算模块度 (Newman-Girvan)

        Q = 1/(2m) * sum_ij [A_ij - k_i*k_j/(2m)] * delta(c_i, c_j)

        Args:
            edges: 边列表
            partition: 划分 {node_id: community_id}

        Returns:
            模块度分数 [-0.5, 1]
        """
        if not edges:
            return 0.0

        # 统计
        m = len(edges)  # 边数量
        total_weight = 2 * m

        # 节点度数
        degree = defaultdict(int)
        for src, dst in edges:
            degree[src] += 1
            degree[dst] += 1

        # 按社区分组节点
        communities = defaultdict(list)
        for node, comm_id in partition.items():
            communities[comm_id].append(node)

        # 计算模块度
        q = 0.0
        for comm_nodes in communities.values():
            for i in comm_nodes:
                for j in comm_nodes:
                    # A_ij = 1 if edge exists
                    a_ij = 1 if (i, j) in edges or (j, i) in edges else 0
                    # k_i * k_j / (2m)
                    expected = (degree[i] * degree[j]) / total_weight
                    q += a_ij - expected

        return q / total_weight


class LouvainDetector(BaseCommunityDetector):
    """
    Louvain社区检测算法

    优点:
    - 模块度优化，精度较高
    - 支持层次化社区
    - O(n log n) 时间复杂度

    原理:
    1. 初始化：每个节点独立社区
    2. 迭代：将节点移动到能最大提升模块度的邻居社区
    3. 压缩：合并同一社区内节点
    4. 重复直到收敛
    """

    def __init__(self, resolution: float = 1.0, random_seed: int = 42):
        """
        Args:
            resolution: 分辨率参数，控制社区大小
                       resolution > 1: 较多小社区
                       resolution < 1: 较少大社区
            random_seed: 随机种子
        """
        self.resolution = resolution
        self.random_seed = random_seed

    def detect(self, edges: List[Tuple[str, str]]) -> Dict[str, Any]:
        """执行Louvain社区检测"""
        import random
        random.seed(self.random_seed)

        # 构建邻接表
        adj = self._build_adjacency(edges)
        nodes = list(adj.keys())

        if not nodes:
            return self._empty_result()

        # 初始化：每个节点独立社区
        partition = {node: node for node in nodes}
        node_to_community = {node: node for node in nodes}

        # 计算总边权重
        m = len(edges)
        if m == 0:
            return self._empty_result()

        # 计算节点权重（度数）
        weight = {node: len(neighbors) for node, neighbors in adj.items()}

        # 迭代优化
        improved = True
        iteration = 0
        max_iterations = 100

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for node in nodes:
                current_comm = partition[node]
                current_gain = self._compute_gain(
                    adj, partition, weight, m, node, current_comm
                )

                best_comm = current_comm
                best_gain = current_gain

                # 检查所有邻居社区
                for neighbor in adj[node]:
                    neighbor_comm = partition[neighbor]
                    if neighbor_comm == current_comm:
                        continue

                    gain = self._compute_gain(
                        adj, partition, weight, m, node, neighbor_comm
                    )

                    if gain > best_gain:
                        best_gain = gain
                        best_comm = neighbor_comm

                # 如果有正增益，移动节点
                if best_gain > 1e-10:
                    partition[node] = best_comm
                    improved = True

        # 构建社区
        communities = self._build_communities(partition)

        # 构建层次结构
        hierarchy = CommunityHierarchy(
            levels={0: communities},
            node_to_community={
                node: {0: comm_id}
                for node, comm_id in partition.items()
            }
        )

        modularity = self._compute_modularity(edges, partition)

        return {
            "communities": communities,
            "hierarchy": hierarchy,
            "modularity": modularity,
            "iteration": iteration
        }

    def _compute_gain(
        self,
        adj: Dict[str, Set[str]],
        partition: Dict[str, str],
        weight: Dict[str, int],
        m: int,
        node: str,
        target_comm: str
    ) -> float:
        """
        计算将节点移动到目标社区的模块度增益

        ΔQ = [Σ_in + 2*k_i,in] / (2*m) - [Σ_tot + 2*k_i] / (2*m)]² * resolution
             - [Σ_in / (2*m) - (Σ_tot / (2*m))² * resolution]
        """
        # 社区内总权重
        sigma_tot = 0.0
        for n in partition:
            if partition[n] == target_comm:
                sigma_tot += weight[n]

        # 社区内边权重（包含目标社区内所有节点的邻居连接）
        sigma_in = 0.0
        for neighbor in adj[node]:
            if partition[neighbor] == target_comm:
                sigma_in += 1

        # 节点总权重
        k_i = weight[node]

        # Ki_in 是节点到社区内节点的边数
        k_i_in = sum(1 for neighbor in adj[node] if partition[neighbor] == target_comm)

        # 模块度增益
        delta_q = (
            (sigma_in + 2 * k_i_in) / (2 * m)
            - ((sigma_tot + k_i) / (2 * m)) ** 2 * self.resolution
        ) - (
            sigma_in / (2 * m)
            - (sigma_tot / (2 * m)) ** 2 * self.resolution
        )

        return delta_q

    def _build_communities(self, partition: Dict[str, str]) -> List[Community]:
        """构建社区列表"""
        community_members = defaultdict(list)
        for node, comm_id in partition.items():
            community_members[comm_id].append(node)

        communities = []
        for comm_id, members in community_members.items():
            comm = Community(
                community_id=comm_id,
                level=0,
                members=members,
                quality_score=0.0
            )
            communities.append(comm)

        return communities

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "communities": [],
            "hierarchy": CommunityHierarchy(levels={}, node_to_community={}),
            "modularity": 0.0,
            "iteration": 0
        }


class LeidenDetector(BaseCommunityDetector):
    """
    Leiden社区检测算法

    Louvain的改进版本，更快更稳定，产生更紧密连接的社区

    改进:
    1. 使用更快的局部移动
    2. 产生的社区更连接（不会产生孤立节点）
    3. 自然支持层次化

    参考: Traag et al. (2019) "From Louvain to Leiden: Guaranteeing well-connected communities"
    """

    def __init__(self, resolution: float = 1.0, random_seed: int = 42):
        self.resolution = resolution
        self.random_seed = random_seed
        import random as _random
        self._random = _random

    def detect(self, edges: List[Tuple[str, str]]) -> Dict[str, Any]:
        """执行Leiden社区检测"""
        self._random.seed(self.random_seed)

        adj = self._build_adjacency(edges)
        nodes = list(adj.keys())

        if not nodes:
            return self._empty_result()

        # 第一阶段：类似Louvain的局部移动
        partition = self._local_move(adj, nodes)

        # 第二阶段：细化划分
        refined = self._refine_partition(adj, nodes, partition)

        # 构建最终社区
        communities = self._build_communities(refined)

        hierarchy = CommunityHierarchy(
            levels={0: communities},
            node_to_community={
                node: {0: comm_id}
                for node, comm_id in partition.items()
            }
        )

        modularity = self._compute_modularity(edges, partition)

        return {
            "communities": communities,
            "hierarchy": hierarchy,
            "modularity": modularity
        }

    def _local_move(
        self,
        adj: Dict[str, Set[str]],
        nodes: List[str]
    ) -> Dict[str, str]:
        """局部移动阶段"""
        self._random.seed(self.random_seed)
        partition = {node: node for node in nodes}
        m = sum(len(neighbors) for neighbors in adj.values()) // 2

        improved = True
        iteration = 0

        while improved and iteration < 100:
            improved = False
            iteration += 1

            # 随机顺序访问节点
            self._random.shuffle(nodes)

            for node in nodes:
                current_comm = partition[node]
                neighbors = list(adj[node])
                if not neighbors:
                    continue

                best_comm = current_comm
                best_gain = 0.0

                for neighbor in neighbors:
                    neighbor_comm = partition[neighbor]
                    if neighbor_comm == current_comm:
                        continue

                    gain = self._calculate_modularity_gain(
                        adj, partition, m, node, neighbor_comm
                    )

                    if gain > best_gain:
                        best_gain = gain
                        best_comm = neighbor_comm

                if best_gain > 1e-10:
                    partition[node] = best_comm
                    improved = True

        return partition

    def _refine_partition(
        self,
        adj: Dict[str, Set[str]],
        nodes: List[str],
        partition: Dict[str, str]
    ) -> Dict[str, str]:
        """
        细化划分阶段

        将未完全连接的节点移动到更合适的社区
        """
        refined = partition.copy()
        communities = set(partition.values())

        for comm in communities:
            comm_nodes = [n for n in nodes if partition[n] == comm]

            # 检查社区内是否有弱连接节点
            for node in comm_nodes:
                node_neighbors = adj[node]
                same_comm_neighbors = [
                    n for n in node_neighbors
                    if partition[n] == comm
                ]

                # 如果节点与社区内节点的连接比例较低，考虑移动
                if len(node_neighbors) > 0:
                    connection_ratio = len(same_comm_neighbors) / len(node_neighbors)
                    if connection_ratio < 0.5:
                        # 寻找更合适的社区
                        for neighbor in node_neighbors:
                            neighbor_comm = partition[neighbor]
                            if neighbor_comm != comm:
                                refined[node] = neighbor_comm
                                break

        return refined

    def _contract_graph(
        self,
        adj: Dict[str, Set[str]],
        partition: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        压缩网络阶段

        将同一社区内的节点压缩为超级节点
        """
        # 按社区分组
        communities = defaultdict(list)
        for node, comm_id in partition.items():
            communities[comm_id].append(node)

        # 创建社区ID映射
        comm_nodes = list(communities.keys())
        node_to_super = {}
        for i, comm_id in enumerate(comm_nodes):
            for node in communities[comm_id]:
                node_to_super[node] = i

        # 构建压缩后的边
        super_edges = set()
        for src, neighbors in adj.items():
            src_super = node_to_super[src]
            for dst in neighbors:
                dst_super = node_to_super[dst]
                if src_super != dst_super:
                    super_edges.add((src_super, dst_super))

        return {
            "nodes": comm_nodes,
            "edges": list(super_edges),
            "mapping": node_to_super
        }

    def _expand_hierarchy(
        self,
        adj: Dict[str, Set[str]],
        partition: Dict[str, str],
        sub_result: Dict[str, Any]
    ) -> List[Community]:
        """展开层次结构"""
        communities = []

        for comm in sub_result["communities"]:
            # 找到该社区包含的原始节点
            members = [
                node for node, p in partition.items()
                if p == comm.community_id
            ]

            if members:
                expanded_comm = Community(
                    community_id=comm.community_id,
                    level=comm.level,
                    members=members,
                    keywords=comm.keywords,
                    summary=comm.summary,
                    quality_score=comm.quality_score
                )
                communities.append(expanded_comm)

        return communities

    def _calculate_modularity_gain(
        self,
        adj: Dict[str, Set[str]],
        partition: Dict[str, str],
        m: int,
        node: str,
        target_comm: str
    ) -> float:
        """计算模块度增益"""
        if m == 0:
            return 0.0

        # 社区内权重
        sigma_tot = sum(
            len(adj[n])
            for n in partition if partition[n] == target_comm
        )

        # Ki_in
        k_i_in = sum(
            1 for neighbor in adj[node]
            if partition[neighbor] == target_comm
        )

        k_i = len(adj[node])

        return (
            (sigma_tot + 2 * k_i_in) / (2 * m)
            - ((sigma_tot + k_i) / (2 * m)) ** 2 * self.resolution
        ) - (
            sigma_tot / (2 * m)
            - (sigma_tot / (2 * m)) ** 2 * self.resolution
        )

    def _build_communities(self, partition: Dict[str, str]) -> List[Community]:
        community_members = defaultdict(list)
        for node, comm_id in partition.items():
            community_members[comm_id].append(node)

        return [
            Community(
                community_id=comm_id,
                level=0,
                members=members,
                quality_score=0.0
            )
            for comm_id, members in community_members.items()
        ]

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "communities": [],
            "hierarchy": CommunityHierarchy(levels={}, node_to_community={}),
            "modularity": 0.0
        }


class LabelPropagationDetector(BaseCommunityDetector):
    """
    Label Propagation 社区检测算法

    优点:
    - O(m) 时间复杂度，近线性
    - 适合大规模图
    - 简单易实现

    缺点:
    - 不保证收敛到最优解
    - 结果不稳定
    """

    def __init__(self, max_iterations: int = 100, random_seed: int = 42):
        self.max_iterations = max_iterations
        self.random_seed = random_seed
        import random as _random
        self._random = _random

    def detect(self, edges: List[Tuple[str, str]]) -> Dict[str, Any]:
        """执行标签传播"""
        import random

        adj = self._build_adjacency(edges)
        nodes = list(adj.keys())

        if not nodes:
            return self._empty_result()

        # 初始化：每个节点标签为自身ID
        labels = {node: i for i, node in enumerate(nodes)}

        # 迭代传播
        for iteration in range(self.max_iterations):
            # 随机顺序
            self._random.seed(self.random_seed + iteration)
            self._random.shuffle(nodes)

            new_labels = labels.copy()
            changed = False

            for node in nodes:
                neighbor_labels = [
                    labels[neighbor]
                    for neighbor in adj[node]
                ]

                if not neighbor_labels:
                    continue

                # 统计邻居标签出现次数
                label_counts = defaultdict(int)
                for label in neighbor_labels:
                    label_counts[label] += 1

                # 选择出现次数最多的标签
                # 如果有多个，随机选择
                max_count = max(label_counts.values())
                candidates = [
                    label for label, count in label_counts.items()
                    if count == max_count
                ]
                new_label = self._random.choice(candidates)

                if new_label != labels[node]:
                    new_labels[node] = new_label
                    changed = True

            labels = new_labels

            if not changed:
                break

        # 构建社区
        label_to_members = defaultdict(list)
        for node, label in labels.items():
            label_to_members[label].append(node)

        communities = [
            Community(
                community_id=f"lp_comm_{i}",
                level=0,
                members=members,
                quality_score=0.0
            )
            for i, members in enumerate(label_to_members.values())
        ]

        hierarchy = CommunityHierarchy(
            levels={0: communities},
            node_to_community={
                node: {0: f"lp_comm_{labels[node]}"}
                for node in nodes
            }
        )

        partition = {node: f"lp_comm_{labels[node]}" for node in nodes}
        modularity = self._compute_modularity(edges, partition)

        return {
            "communities": communities,
            "hierarchy": hierarchy,
            "modularity": modularity,
            "iterations": iteration + 1
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "communities": [],
            "hierarchy": CommunityHierarchy(levels={}, node_to_community={}),
            "modularity": 0.0,
            "iterations": 0
        }


def detect_communities(
    edges: List[Tuple[str, str]],
    algorithm: CommunityAlgorithm = CommunityAlgorithm.LEIDEN,
    **kwargs
) -> Dict[str, Any]:
    """
    便捷函数：检测社区

    Args:
        edges: 边列表
        algorithm: 算法选择
        **kwargs: 算法特定参数

    Returns:
        社区检测结果
    """
    if algorithm == CommunityAlgorithm.LEIDEN:
        detector = LeidenDetector(**kwargs)
    elif algorithm == CommunityAlgorithm.LOUVAIN:
        detector = LouvainDetector(**kwargs)
    elif algorithm == CommunityAlgorithm.LABEL_PROPAGATION:
        detector = LabelPropagationDetector(**kwargs)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    return detector.detect(edges)
