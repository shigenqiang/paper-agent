"""知识图谱模型：节点、边、类型化节点"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agents_v3.research_workspace.models.enums import EdgeType, NodeType


class GraphNode(BaseModel):
    node_id: str
    node_type: NodeType
    label: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    project_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ── 类型化知识图谱节点 ─────────────────────────────────


class KGNodeBase(BaseModel):
    """KG 节点基类"""
    node_id: str
    node_type: NodeType
    label: str = ""
    description: str = ""
    confidence: float = 1.0
    source_paper_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class PaperNode(KGNodeBase):
    node_type: Literal[NodeType.PAPER] = NodeType.PAPER
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    abstract: str = ""
    citation_count: int = 0
    fwci: float = 0.0


class TaskNode(KGNodeBase):
    node_type: Literal[NodeType.TASK] = NodeType.TASK
    task_domain: str = ""


class MethodNode(KGNodeBase):
    node_type: Literal[NodeType.METHOD] = NodeType.METHOD
    method_type: str = ""
    input_type: str = ""
    output_type: str = ""


class MaterialNode(KGNodeBase):
    node_type: Literal[NodeType.DATASET] = NodeType.DATASET
    data_type: str = ""
    size: str = ""
    domain: str = ""


class MetricNode(KGNodeBase):
    node_type: Literal[NodeType.METRIC] = NodeType.METRIC
    metric_type: str = ""
    higher_is_better: bool = True


class FindingNode(KGNodeBase):
    node_type: Literal[NodeType.FINDING] = NodeType.FINDING
    evidence_quote: str = ""
    source_chunk_id: str = ""
    evidence_strength: str = "medium"


class LimitationNode(KGNodeBase):
    node_type: Literal[NodeType.LIMITATION] = NodeType.LIMITATION
    limitation_type: str = ""
    evidence_quote: str = ""


class GapNode(KGNodeBase):
    node_type: Literal[NodeType.GAP] = NodeType.GAP
    gap_type: str = ""
    potential_impact: str = ""


class TopicNode(KGNodeBase):
    node_type: Literal[NodeType.TOPIC] = NodeType.TOPIC
    keywords: list[str] = Field(default_factory=list)


class AuthorNode(KGNodeBase):
    node_type: Literal[NodeType.AUTHOR] = NodeType.AUTHOR
    affiliations: list[str] = Field(default_factory=list)
    h_index: int = 0


class VenueNode(KGNodeBase):
    node_type: Literal[NodeType.VENUE] = NodeType.VENUE
    venue_type: str = ""
    impact_factor: float = 0.0


class InnovationNode(KGNodeBase):
    node_type: Literal[NodeType.INNOVATION] = NodeType.INNOVATION
    innovation_type: str = ""
    why_innovative: str = ""
    feasibility: str = ""
    risk: str = ""
    supporting_papers: list[str] = Field(default_factory=list)


class KGEdge(BaseModel):
    """类型化 KG 边"""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    confidence: float = 1.0
    evidence: str = ""
    source_chunk_id: str = ""
    source_paper_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
