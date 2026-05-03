"""
知识图谱可视化器
Knowledge Graph Visualizer
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..storage.neo4j_client import SubgraphResult


@dataclass
class VisualizationConfig:
    """可视化配置"""
    layout: str = "force"           # force, circular, hierarchical
    show_labels: bool = True
    node_size_by_degree: bool = True
    max_nodes: int = 100
    edge_width_range: Tuple[int, int] = (1, 5)
    node_size_range: Tuple[int, int] = (10, 50)


class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.layout_algorithms = {
            "force": self._force_directed_layout,
            "circular": self._circular_layout,
            "hierarchical": self._hierarchical_layout
        }

    def visualize(
        self,
        subgraph: SubgraphResult,
        layout: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成可视化配置"""
        layout = layout or self.config.layout

        # 数据预处理
        if len(subgraph.nodes) > self.config.max_nodes:
            subgraph = self._prune_subgraph(subgraph, self.config.max_nodes)

        # 计算布局
        layout_func = self.layout_algorithms.get(layout, self._force_directed_layout)
        positions = layout_func(subgraph)

        # 构建ECharts配置
        echarts_config = self._build_echarts_config(subgraph, positions)

        return echarts_config

    def visualize_as_networkx(
        self,
        subgraph: SubgraphResult
    ) -> "nx.Graph":
        """转换为networkx图"""
        try:
            import networkx as nx
        except ImportError:
            return None

        G = nx.Graph()

        # 添加节点
        for node in subgraph.nodes:
            G.add_node(
                node.get("id"),
                **{k: v for k, v in node.items() if k != "id"}
            )

        # 添加边
        for edge in subgraph.edges:
            G.add_edge(
                edge.get("source"),
                edge.get("target"),
                **{k: v for k, v in edge.items() if k not in ["source", "target"]}
            )

        return G

    def _prune_subgraph(
        self,
        subgraph: SubgraphResult,
        max_nodes: int
    ) -> SubgraphResult:
        """裁剪子图"""
        if len(subgraph.nodes) <= max_nodes:
            return subgraph

        # 按度数保留最重要的节点
        node_degree: Dict[str, int] = {}

        for edge in subgraph.edges:
            source = edge.get("source")
            target = edge.get("target")

            node_degree[source] = node_degree.get(source, 0) + 1
            node_degree[target] = node_degree.get(target, 0) + 1

        # 排序并保留top_k
        sorted_nodes = sorted(
            node_degree.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_nodes]

        top_node_ids = set(node_id for node_id, _ in sorted_nodes)

        # 过滤节点
        filtered_nodes = [
            n for n in subgraph.nodes
            if n.get("id") in top_node_ids
        ]

        # 过滤边
        filtered_edges = [
            e for e in subgraph.edges
            if e.get("source") in top_node_ids and e.get("target") in top_node_ids
        ]

        return SubgraphResult(
            nodes=filtered_nodes,
            edges=filtered_edges,
            center_id=subgraph.center_id
        )

    def _force_directed_layout(
        self,
        subgraph: SubgraphResult
    ) -> Dict[str, Tuple[float, float]]:
        """力导向布局"""
        try:
            import networkx as nx
            from networkx.drawing.layout import spring_layout
        except ImportError:
            return self._simple_layout(subgraph)

        G = self._to_networkx_simple(subgraph)

        try:
            pos = spring_layout(G, k=2, iterations=50)
        except Exception:
            return self._simple_layout(subgraph)

        return {node_id: (x, y) for node_id, (x, y) in pos.items()}

    def _circular_layout(
        self,
        subgraph: SubgraphResult
    ) -> Dict[str, Tuple[float, float]]:
        """圆形布局"""
        try:
            import networkx as nx
            from networkx.drawing.layout import circular_layout
        except ImportError:
            return self._simple_layout(subgraph)

        G = self._to_networkx_simple(subgraph)

        try:
            pos = circular_layout(G)
        except Exception:
            return self._simple_layout(subgraph)

        return {node_id: (x, y) for node_id, (x, y) in pos.items()}

    def _hierarchical_layout(
        self,
        subgraph: SubgraphResult
    ) -> Dict[str, Tuple[float, float]]:
        """层级布局"""
        positions = {}

        # 按层级排列
        nodes = subgraph.nodes
        n = len(nodes)

        for i, node in enumerate(nodes):
            level = i // 10
            level_size = 10

            x = (i % level_size) - level_size / 2
            y = level * 1.5

            positions[node.get("id")] = (x * 0.5, y)

        return positions

    def _simple_layout(
        self,
        subgraph: SubgraphResult
    ) -> Dict[str, Tuple[float, float]]:
        """简单网格布局"""
        positions = {}
        nodes = subgraph.nodes
        n = len(nodes)

        cols = int(n ** 0.5) + 1

        for i, node in enumerate(nodes):
            x = (i % cols) * 1.5
            y = (i // cols) * 1.5
            positions[node.get("id")] = (x, y)

        return positions

    def _to_networkx_simple(self, subgraph: SubgraphResult):
        """转换为简化的networkx图"""
        import networkx as nx

        G = nx.Graph()

        for node in subgraph.nodes:
            G.add_node(node.get("id"))

        for edge in subgraph.edges:
            G.add_edge(edge.get("source"), edge.get("target"))

        return G

    def _build_echarts_config(
        self,
        subgraph: SubgraphResult,
        positions: Dict[str, Tuple[float, float]]
    ) -> Dict[str, Any]:
        """构建ECharts配置"""
        # 统计度数
        node_degree: Dict[str, int] = {}
        for edge in subgraph.edges:
            source = edge.get("source")
            target = edge.get("target")
            node_degree[source] = node_degree.get(source, 0) + 1
            node_degree[target] = node_degree.get(target, 0) + 1

        # 构建节点
        nodes = []
        for node in subgraph.nodes:
            node_id = node.get("id")
            x, y = positions.get(node_id, (0, 0))
            degree = node_degree.get(node_id, 0)

            # 计算节点大小
            if self.config.node_size_by_degree:
                size_range = self.config.node_size_range
                max_degree = max(node_degree.values()) if node_degree else 1
                size = size_range[0] + (degree / max_degree) * (size_range[1] - size_range[0])
            else:
                size = (size_range[0] + size_range[1]) / 2

            nodes.append({
                "id": node_id,
                "name": node.get("name", node_id),
                "category": node.get("type", "unknown"),
                "symbolSize": size,
                "x": x,
                "y": y,
                "value": degree,
                "itemStyle": {
                    "color": self._get_node_color(node.get("type", "unknown"))
                }
            })

        # 构建边
        links = []
        for edge in subgraph.edges:
            source = edge.get("source")
            target = edge.get("target")

            # 计算边的宽度
            width_range = self.config.edge_width_range
            degree = node_degree.get(source, 0) + node_degree.get(target, 0)
            width = width_range[0] + (degree / 20) * (width_range[1] - width_range[0])
            width = min(width, width_range[1])

            links.append({
                "source": source,
                "target": target,
                "name": edge.get("type", ""),
                "lineStyle": {
                    "width": width,
                    "color": self._get_edge_color(edge.get("type", ""))
                }
            })

        # 提取类别
        categories = []
        seen_types = set()
        for node in subgraph.nodes:
            node_type = node.get("type", "unknown")
            if node_type not in seen_types:
                seen_types.add(node_type)
                categories.append({"name": node_type})

        return {
            "tooltip": {
                "trigger": "item",
                "formatter": " {b} "
            },
            "legend": [
                {
                    "data": [c["name"] for c in categories]
                }
            ],
            "series": [
                {
                    "type": "graph",
                    "layout": self.config.layout,
                    "data": nodes,
                    "links": links,
                    "categories": categories,
                    "roam": True,
                    "label": {
                        "show": self.config.show_labels,
                        "position": "right"
                    },
                    "edgeSymbol": ["circle", "arrow"],
                    "edgeSymbolSize": 5,
                    "lineStyle": {
                        "curveness": 0.3
                    },
                    "emphasis": {
                        "focus": "adjacency"
                    },
                    "force": {
                        "repulsion": 100,
                        "edgeLength": 100
                    }
                }
            ]
        }

    def _get_node_color(self, node_type: str) -> str:
        """获取节点颜色"""
        colors = {
            "Paper": "#5470c8",
            "Author": "#73c0de",
            "Institution": "#ffc0b3",
            "Venue": "#95d475",
            "Keyword": "#ff9f43",
            "Method": "#a4a4a4",
            "Dataset": "#9c27b0"
        }
        return colors.get(node_type, "#999999")

    def _get_edge_color(self, edge_type: str) -> str:
        """获取边的颜色"""
        return "#999999"

    def export_to_html(
        self,
        subgraph: SubgraphResult,
        output_path: str
    ):
        """导出为HTML文件"""
        vis_config = self.visualize(subgraph)

        html_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Knowledge Graph Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        #chart {{
            width: 100%;
            height: 800px;
        }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        var chart = echarts.init(document.getElementById('chart'));
        var option = {config};
        chart.setOption(option);
        window.addEventListener('resize', function() {{
            chart.resize();
        }});
    </script>
</body>
</html>
'''

        import json
        config_str = json.dumps(vis_config, indent=2)
        html_content = html_template.format(config=config_str)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
