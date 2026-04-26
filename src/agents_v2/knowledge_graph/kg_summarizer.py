"""
知识图谱子图摘要生成模块

功能:
1. 子图提取 (Subgraph Extraction)
2. 子图摘要生成 (Subgraph Summarization)
3. 实体描述生成 (Entity Description Generation)
4. GraphRAG上下文构建
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """图节点"""
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """图边"""
    source: str
    target: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subgraph:
    """子图"""
    nodes: Dict[str, GraphNode]
    edges: List[GraphEdge]

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[str]:
        """获取邻居节点"""
        neighbors = []
        for edge in self.edges:
            if edge.source == node_id:
                neighbors.append(edge.target)
            elif edge.target == node_id:
                neighbors.append(edge.source)
        return neighbors

    def get_outgoing_relations(self, node_id: str) -> List[Tuple[str, str]]:
        """获取出边关系 (relation, target)"""
        return [
            (edge.relation, edge.target)
            for edge in self.edges
            if edge.source == node_id
        ]

    def get_incoming_relations(self, node_id: str) -> List[Tuple[str, str]]:
        """获取入边关系 (relation, source)"""
        return [
            (edge.relation, edge.source)
            for edge in self.edges
            if edge.target == node_id
        ]


@dataclass
class EntityContext:
    """实体上下文"""
    entity_id: str
    entity_type: str
    name: str
    description: str
    properties: Dict[str, Any]
    neighbors: List[str]
    relations_as_source: List[Tuple[str, str]]  # (relation, target)
    relations_as_target: List[Tuple[str, str]]  # (relation, source)


@dataclass
class SubgraphSummary:
    """子图摘要"""
    subgraph: Subgraph
    summary_text: str
    entity_contexts: List[EntityContext]
    key_relations: List[Tuple[str, str, str]]  # (source, relation, target)
    statistics: Dict[str, int]


class SubgraphExtractor:
    """
    子图提取器

    从知识图谱中提取相关子图
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []

    def add_node(
        self,
        node_id: str,
        node_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加节点"""
        self._nodes[node_id] = GraphNode(
            id=node_id,
            type=node_type,
            properties=properties or {}
        )

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加边"""
        self._edges.append(GraphEdge(
            source=source,
            target=target,
            relation=relation,
            properties=properties or {}
        ))

    def extract_subgraph(
        self,
        center_nodes: List[str],
        depth: int = 2,
        max_nodes: int = 100
    ) -> Subgraph:
        """
        提取子图

        Args:
            center_nodes: 中心节点列表
            depth: 扩展深度
            max_nodes: 最大节点数

        Returns:
            Subgraph
        """
        if not center_nodes:
            return Subgraph(nodes={}, edges=[])

        # BFS扩展
        visited: Set[str] = set()
        current_level: Set[str] = set(center_nodes)
        visited.update(center_nodes)

        for _ in range(depth):
            if len(visited) >= max_nodes:
                break

            next_level = set()
            for node_id in current_level:
                for edge in self._edges:
                    if edge.source == node_id and edge.target not in visited:
                        next_level.add(edge.target)
                    elif edge.target == node_id and edge.source not in visited:
                        next_level.add(edge.source)

            visited.update(next_level)
            current_level = next_level

            if not current_level:
                break

        # 构建子图
        subgraph_nodes = {
            node_id: self._nodes[node_id]
            for node_id in visited
            if node_id in self._nodes
        }

        subgraph_edges = [
            edge for edge in self._edges
            if edge.source in visited and edge.target in visited
        ]

        return Subgraph(nodes=subgraph_nodes, edges=subgraph_edges)

    def extract_ego_network(self, node_id: str, depth: int = 1) -> Subgraph:
        """提取节点ego网络"""
        return self.extract_subgraph([node_id], depth)


class GraphSentenceGenerator:
    """
    图形句子生成器

    将图结构转换为自然语言描述
    """

    def __init__(self):
        self.relation_templates: Dict[str, str] = {
            "CITES": "{source} 引用了 {target}",
            "AUTHORED_BY": "{target} 由 {source} 撰写",
            "PUBLISHED_IN": "{source} 发表在 {target}",
            "HAS_METHOD": "{source} 使用了 {target} 方法",
            "REFERENCES": "{source} 引用了 {target}",
            "RELATED_TO": "{source} 与 {target} 相关",
        }

    def generate_sentence(
        self,
        source_name: str,
        relation: str,
        target_name: str
    ) -> str:
        """生成单个关系的句子"""
        template = self.relation_templates.get(
            relation,
            "{source} 与 {target} 存在 {relation} 关系"
        )
        return template.format(
            source=source_name,
            target=target_name,
            relation=relation
        )

    def generate_entity_description(
        self,
        entity: GraphNode,
        relations_as_source: List[Tuple[str, str]],
        relations_as_target: List[Tuple[str, str]]
    ) -> str:
        """
        生成实体描述

        Args:
            entity: 实体节点
            relations_as_source: 作为源的relation列表
            relations_as_target: 作为目标的relation列表

        Returns:
            描述文本
        """
        parts = []

        # 基本信息
        name = entity.properties.get("name", entity.properties.get("title", entity.id))
        parts.append(f"{name}是一个{entity.type}类型的实体")

        # 属性描述
        key_props = ["year", "citation_count", "venue", "abstract"]
        for prop in key_props:
            if prop in entity.properties:
                parts.append(f"其{prop}为{entity.properties[prop]}")

        # 关系描述
        if relations_as_source:
            source_relations = [f"{r}了{t}" for r, t in relations_as_source]
            parts.append(f"它{'、'.join(source_relations)}")

        if relations_as_target:
            target_relations = [f"被{r}于{t}" for r, t in relations_as_target]
            parts.append(f"它{'、'.join(target_relations)}")

        return "，".join(parts)

    def generate_subgraph_description(self, subgraph: Subgraph) -> str:
        """
        生成子图的整体描述

        Returns:
            描述文本
        """
        if not subgraph.nodes:
            return "空子图"

        # 统计信息
        node_types: Dict[str, int] = defaultdict(int)
        relation_types: Dict[str, int] = defaultdict(int)

        for node in subgraph.nodes.values():
            node_types[node.type] += 1

        for edge in subgraph.edges:
            relation_types[edge.relation] += 1

        # 生成描述
        parts = []

        # 节点统计
        node_stats = ", ".join([f"{t}类型节点{n}个" for t, n in node_types.items()])
        parts.append(f"该子图包含{len(subgraph.nodes)}个节点({node_stats})")

        # 边统计
        parts.append(f"和{len(subgraph.edges)}条边")

        # 关系统计
        if relation_types:
            rel_stats = ", ".join([f"{r}关系{r}条" for r, c in relation_types.items()])
            parts.append(f"其中{rel_stats}")

        return "，".join(parts) + "。"


class EntityDescriptionGenerator:
    """
    实体描述生成器

    为实体生成详细描述
    """

    def __init__(self):
        self.type_display_names: Dict[str, str] = {
            "Paper": "论文",
            "Author": "作者",
            "Venue": "会议/期刊",
            "Method": "方法",
            "Field": "领域"
        }

    def generate_description(
        self,
        entity: GraphNode,
        context: List[Tuple[str, str, str]]  # [(relation, neighbor_name, direction), ...]
    ) -> str:
        """
        生成实体描述

        Args:
            entity: 实体节点
            context: 上下文关系

        Returns:
            描述文本
        """
        parts = []

        # 名称和类型
        name = entity.properties.get("name", entity.properties.get("title", entity.id))
        type_name = self.type_display_names.get(entity.type, entity.type)
        parts.append(f"{name}是{type_name}")

        # 关键属性
        if entity.type == "Paper":
            if "year" in entity.properties:
                parts.append(f"发表年份为{entity.properties['year']}")
            if "citation_count" in entity.properties:
                parts.append(f"被引用次数为{entity.properties['citation_count']}")
            if "venue" in entity.properties:
                parts.append(f"发表在{entity.properties['venue']}")

        elif entity.type == "Author":
            if "institution" in entity.properties:
                parts.append(f"来自{entity.properties['institution']}")
            if "h_index" in entity.properties:
                parts.append(f"h指数为{entity.properties['h_index']}")

        # 关系上下文
        outgoing = [(r, n) for r, n, d in context if d == "out"]
        incoming = [(r, n) for r, n, d in context if d == "in"]

        if outgoing:
            rel_str = "、".join([f"{r}{n}" for r, n in outgoing[:3]])
            parts.append(f"该实体{rel_str}")

        if incoming:
            rel_str = "、".join([f"被{n}{r}" for r, n in incoming[:3]])
            parts.append(f"该实体{rel_str}")

        return "，".join(parts) + "。" if parts else f"{name}的相关信息。"


class SubgraphSummarizer:
    """
    子图摘要生成器

    整合子图提取、句子生成、描述生成等功能
    """

    def __init__(self):
        self.extractor = SubgraphExtractor()
        self.sentence_generator = GraphSentenceGenerator()
        self.description_generator = EntityDescriptionGenerator()

    def build_subgraph(
        self,
        entities: List[Tuple[str, str, Dict]],
        relations: List[Tuple[str, str, str, Dict]]
    ) -> None:
        """
        构建子图结构

        Args:
            entities: [(entity_id, entity_type, properties), ...]
            relations: [(source_id, target_id, relation_type, properties), ...]
        """
        for entity_id, entity_type, properties in entities:
            self.extractor.add_node(entity_id, entity_type, properties)

        for source, target, relation, properties in relations:
            self.extractor.add_edge(source, target, relation, properties)

    def summarize(
        self,
        center_entities: List[str],
        depth: int = 2,
        max_nodes: int = 50
    ) -> SubgraphSummary:
        """
        生成子图摘要

        Args:
            center_entities: 中心实体ID列表
            depth: 扩展深度
            max_nodes: 最大节点数

        Returns:
            SubgraphSummary
        """
        subgraph = self.extractor.extract_subgraph(center_entities, depth, max_nodes)

        # 生成实体上下文
        entity_contexts = []
        for node_id, node in subgraph.nodes.items():
            neighbors = subgraph.get_neighbors(node_id)
            rels_source = subgraph.get_outgoing_relations(node_id)
            rels_target = subgraph.get_incoming_relations(node_id)

            # 获取邻居名称
            neighbor_names = []
            for neighbor_id in neighbors:
                neighbor_node = subgraph.get_node(neighbor_id)
                if neighbor_node:
                    name = neighbor_node.properties.get("name", neighbor_node.properties.get("title", neighbor_id))
                    neighbor_names.append(name)

            # 生成描述
            name = node.properties.get("name", node.properties.get("title", node_id))
            description = self.description_generator.generate_description(
                node,
                [(r, t, "out") for r, t in rels_source] +
                [(r, s, "in") for r, s in rels_target]
            )

            entity_contexts.append(EntityContext(
                entity_id=node_id,
                entity_type=node.type,
                name=name,
                description=description,
                properties=node.properties,
                neighbors=neighbor_names,
                relations_as_source=rels_source,
                relations_as_target=rels_target
            ))

        # 提取关键关系
        key_relations = [
            (edge.source, edge.relation, edge.target)
            for edge in subgraph.edges
        ]

        # 生成子图描述
        graph_description = self.sentence_generator.generate_subgraph_description(subgraph)

        # 生成摘要文本
        summary_parts = [graph_description]

        # 添加实体描述
        if entity_contexts:
            entity_descs = [ctx.description for ctx in entity_contexts[:5]]
            summary_parts.extend(entity_descs)

        summary_text = "\n".join(summary_parts)

        # 统计信息
        statistics = {
            "total_nodes": len(subgraph.nodes),
            "total_edges": len(subgraph.edges),
            "entity_types": len(set(ctx.entity_type for ctx in entity_contexts))
        }

        return SubgraphSummary(
            subgraph=subgraph,
            summary_text=summary_text,
            entity_contexts=entity_contexts,
            key_relations=key_relations,
            statistics=statistics
        )

    def generate_context_for_rag(
        self,
        query: str,
        entities: List[str],
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        为GraphRAG生成上下文

        Args:
            query: 查询文本
            entities: 相关实体列表
            depth: 扩展深度

        Returns:
            {
                "subgraph_summary": SubgraphSummary,
                "context_text": str,
                "entity_map": Dict[str, str]
            }
        """
        summary = self.summarize(entities, depth)

        # 构建entity_map
        entity_map = {
            ctx.entity_id: ctx.name
            for ctx in summary.entity_contexts
        }

        # 构建context_text
        context_parts = [f"查询相关上下文:\n{summary.summary_text}\n"]

        for ctx in summary.entity_contexts:
            context_parts.append(f"\n{ctx.name}: {ctx.description}")

        context_text = "\n".join(context_parts)

        return {
            "subgraph_summary": summary,
            "context_text": context_text,
            "entity_map": entity_map
        }
