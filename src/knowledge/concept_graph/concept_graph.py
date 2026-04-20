"""概念图谱主类"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class ConceptNode:
    """概念节点"""
    id: str
    name: str
    definition: str
    parent_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class ConceptEdge:
    """概念边"""
    source_id: str
    target_id: str
    relation_type: str
    properties: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class ConceptGraph(BaseModel):
    """概念图谱"""

    nodes: Dict[str, ConceptNode] = {}
    edges: List[ConceptEdge] = []
    root_concepts: List[str] = []

    def add_node(self, node: ConceptNode) -> None:
        """添加概念节点"""
        self.nodes[node.id] = node
        if node.parent_id is None:
            self.root_concepts.append(node.id)

    def add_edge(self, edge: ConceptEdge) -> None:
        """添加概念边"""
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[ConceptNode]:
        """获取概念节点"""
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> List[ConceptNode]:
        """获取子概念"""
        return [
            node for node in self.nodes.values()
            if node.parent_id == node_id
        ]

    def get_parents(self, node_id: str) -> List[ConceptNode]:
        """获取父概念"""
        node = self.get_node(node_id)
        if node and node.parent_id:
            parent = self.get_node(node.parent_id)
            if parent:
                return [parent]
        return []

    def get_subtree(self, node_id: str) -> List[ConceptNode]:
        """获取概念子树"""
        subtree = []
        node = self.get_node(node_id)
        if node:
            subtree.append(node)
            for child in self.get_children(node_id):
                subtree.extend(self.get_subtree(child.id))
        return subtree

    def find_concepts_by_name(self, name: str) -> List[ConceptNode]:
        """根据名称查找概念"""
        return [
            node for node in self.nodes.values()
            if name.lower() in node.name.lower()
        ]
