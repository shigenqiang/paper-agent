"""
流程图/架构图解析器 - Diagram Parser

功能:
- 检测节点和边
- 构建图结构
- 生成文本描述
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from src.agents_v2.logging_config import get_logging_logger

import json

logger = get_logging_logger(__name__)


@dataclass
class DiagramNode:
    """图表节点"""
    id: str
    label: str
    node_type: str  # start/end/process/decision/io
    position: Tuple[int, int] = (0, 0)
    metadata: Dict = field(default_factory=dict)


@dataclass
class DiagramEdge:
    """图表边"""
    source: str
    target: str
    label: str = ""
    edge_type: str = "arrow"  # arrow/dashed/bold


@dataclass
class DiagramResult:
    """图表解析结果"""
    nodes: List[DiagramNode]
    edges: List[DiagramEdge]
    description: str
    key_info: List[str]
    graph_representation: Dict
    confidence: float


class DiagramParser:
    """流程图/架构图解析器"""

    def __init__(self, llm: Any = None):
        """初始化解析器

        Args:
            llm: 可选的LLM实例
        """
        self.llm = llm
        self.node_detector = NodeDetector()
        self.edge_detector = EdgeDetector()

    async def parse(self, image: Any) -> DiagramResult:
        """解析流程图/架构图

        Args:
            image: PIL.Image或图像路径

        Returns:
            DiagramResult: 解析结果
        """
        # 1. 检测节点和边
        nodes = await self.node_detector.detect(image)
        edges = await self.edge_detector.detect(image, nodes)

        # 2. 构建图结构
        graph = self._build_graph(nodes, edges)

        # 3. 生成描述
        description = await self._generate_description(nodes, edges)

        # 4. 提取关键信息
        key_info = self._extract_key_info(graph, nodes)

        return DiagramResult(
            nodes=nodes,
            edges=edges,
            description=description,
            key_info=key_info,
            graph_representation=graph,
            confidence=0.8 if nodes else 0.3
        )

    def _build_graph(self, nodes: List[DiagramNode], edges: List[DiagramEdge]) -> Dict:
        """构建图结构

        Args:
            nodes: 节点列表
            edges: 边列表

        Returns:
            Dict: 图表示
        """
        try:
            import networkx as nx

            G = nx.DiGraph()

            # 添加节点
            for node in nodes:
                G.add_node(node.id, label=node.label, type=node.node_type)

            # 添加边
            for edge in edges:
                G.add_edge(edge.source, edge.target, label=edge.label, type=edge.edge_type)

            # 计算拓扑顺序
            try:
                topo_order = list(nx.topological_sort(G))
            except:
                topo_order = [n.id for n in nodes]

            return {
                "nodes": {n.id: {"label": n.label, "type": n.node_type} for n in nodes},
                "edges": [(e.source, e.target, {"label": e.label}) for e in edges],
                "topological_order": topo_order,
                "node_count": len(nodes),
                "edge_count": len(edges)
            }

        except ImportError:
            logger.warning("networkx未安装，使用简单图表示")
            return {
                "nodes": [{"id": n.id, "label": n.label, "type": n.node_type} for n in nodes],
                "edges": [{"from": e.source, "to": e.target, "label": e.label} for e in edges],
                "node_count": len(nodes),
                "edge_count": len(edges)
            }

    async def _generate_description(self, nodes: List[DiagramNode], edges: List[DiagramEdge]) -> str:
        """生成图表的文本描述

        Args:
            nodes: 节点列表
            edges: 边列表

        Returns:
            str: 描述文本
        """
        if not self.llm:
            return self._simple_description(nodes, edges)

        try:
            node_labels = [n.label for n in nodes]
            edge_list = [(e.source, e.target, e.label) for e in edges]

            prompt = f"""
根据以下流程图信息，生成简洁准确的描述：

节点：{node_labels}
边：{edge_list}

描述这个流程图的工作流程（2-4句话）。
"""
            result = await self.llm.agenerate([prompt])
            return result.generations[0][0].text.strip()

        except Exception as e:
            logger.error(f"生成描述失败: {e}")
            return self._simple_description(nodes, edges)

    def _simple_description(self, nodes: List[DiagramNode], edges: List[DiagramEdge]) -> str:
        """生成简单描述"""
        if not nodes:
            return "空流程图"

        start_nodes = [n for n in nodes if n.node_type == "start"]
        end_nodes = [n for n in nodes if n.node_type == "end"]

        description = f"流程图包含{len(nodes)}个节点和{len(edges)}条边。"

        if start_nodes:
            description += f" 从'{start_nodes[0].label}'开始。"

        if end_nodes:
            description += f" 到'{end_nodes[0].label}'结束。"

        return description

    def _extract_key_info(self, graph: Dict, nodes: List[DiagramNode]) -> List[str]:
        """提取关键信息

        Args:
            graph: 图结构
            nodes: 节点列表

        Returns:
            List[str]: 关键信息列表
        """
        key_info = []

        # 节点类型统计
        type_counts = {}
        for node in nodes:
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

        for node_type, count in type_counts.items():
            key_info.append(f"{node_type}节点: {count}个")

        # 关键路径
        if "topological_order" in graph and graph["topological_order"]:
            path = " → ".join(graph["topological_order"][:5])
            if len(graph["topological_order"]) > 5:
                path += " → ..."
            key_info.append(f"关键路径: {path}")

        return key_info


class NodeDetector:
    """节点检测器"""

    async def detect(self, image: Any) -> List[DiagramNode]:
        """检测图像中的节点

        Args:
            image: PIL.Image或图像路径

        Returns:
            List[DiagramNode]: 检测到的节点列表
        """
        # 简化实现：返回空列表
        # 实际应用中应该使用目标检测模型（如YOLO）
        logger.info("使用简单节点检测，实际应用需要目标检测模型")

        return []


class EdgeDetector:
    """边检测器"""

    async def detect(self, image: Any, nodes: List[DiagramNode]) -> List[DiagramEdge]:
        """检测图像中的边

        Args:
            image: PIL.Image或图像路径
            nodes: 已检测的节点

        Returns:
            List[DiagramEdge]: 检测到的边列表
        """
        # 简化实现：返回空列表
        logger.info("使用简单边检测，实际应用需要线条检测模型")

        return []


# 便捷函数
async def parse_diagram(image: Any, llm: Any = None) -> DiagramResult:
    """解析图表的便捷函数

    Args:
        image: PIL.Image或图像路径
        llm: 可选的LLM实例

    Returns:
        DiagramResult: 解析结果
    """
    parser = DiagramParser(llm=llm)
    return await parser.parse(image)
