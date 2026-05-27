"""
Data models for PaperAgent v3.

Based on AGENT.md product definition:
- Paper Card: structured summary of one paper
- Evidence Table: structured basis for reviews and reports
- Knowledge Graph: nodes (Paper, Author, Topic, Method, etc.) and edges
- Retrieval Scope: scope-based QA selection
- Literature Review / Innovation-Point Report: two formal artifacts
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# ========== Paper ==========


@dataclass
class PaperMetadata:
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    abstract: str | None = None
    keywords: list[str] = field(default_factory=list)
    source: str | None = None  # upload / search / doi / bibtex


@dataclass
class PaperChunk:
    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    paper_id: str = ""
    section: str = ""  # abstract / introduction / method / results / conclusion
    text: str = ""
    embedding: list[float] | None = None
    page: int | None = None


@dataclass
class Paper:
    paper_id: str = field(default_factory=lambda: f"p_{uuid.uuid4().hex[:8]}")
    metadata: PaperMetadata = field(default_factory=lambda: PaperMetadata(title=""))
    full_text: str = ""
    chunks: list[PaperChunk] = field(default_factory=list)
    pdf_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ========== Paper Card ==========


@dataclass
class PaperCard:
    """Structured summary of one paper (AGENT.md §2)."""

    paper_id: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str = ""
    research_question: str = ""
    method: str = ""
    dataset_or_sample: str = ""
    key_findings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    future_work: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    possible_innovation_points: list[str] = field(default_factory=list)


# ========== Evidence Table ==========


@dataclass
class EvidenceRecord:
    """One row of the evidence table (AGENT.md §3)."""

    evidence_id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    paper_id: str = ""
    research_question: str = ""
    method: str = ""
    data_or_sample: str = ""
    finding: str = ""
    limitation: str = ""
    future_work: str = ""
    topic: str = ""
    evidence_strength: str = ""  # strong / moderate / weak
    citation_context: str = ""


# ========== Knowledge Graph ==========


class NodeType(str, Enum):
    PAPER = "Paper"
    AUTHOR = "Author"
    TOPIC = "Topic"
    TASK = "Task"
    METHOD = "Method"
    DATASET = "Dataset"
    FINDING = "Finding"
    LIMITATION = "Limitation"
    GAP = "Gap"
    INNOVATION = "InnovationPoint"


class RelationType(str, Enum):
    BELONGS_TO_TOPIC = "BELONGS_TO_TOPIC"
    STUDIES_TASK = "STUDIES_TASK"
    USES_METHOD = "USES_METHOD"
    USES_DATASET = "USES_DATASET"
    REPORTS_FINDING = "REPORTS_FINDING"
    HAS_LIMITATION = "HAS_LIMITATION"
    SUGGESTS_GAP = "SUGGESTS_GAP"
    SUPPORTS_INNOVATION = "SUPPORTS_INNOVATION"
    CITES = "CITES"
    AUTHORED_BY = "AUTHORED_BY"


@dataclass
class KGNode:
    node_id: str = field(default_factory=lambda: f"n_{uuid.uuid4().hex[:8]}")
    node_type: NodeType = NodeType.PAPER
    label: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KGEdge:
    edge_id: str = field(default_factory=lambda: f"e_{uuid.uuid4().hex[:8]}")
    source_id: str = ""
    target_id: str = ""
    relation: RelationType = RelationType.BELONGS_TO_TOPIC
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeGraph:
    """Project-level knowledge graph."""

    nodes: list[KGNode] = field(default_factory=list)
    edges: list[KGEdge] = field(default_factory=list)

    def add_node(self, node: KGNode) -> KGNode:
        self.nodes.append(node)
        return node

    def add_edge(self, edge: KGEdge) -> KGEdge:
        self.edges.append(edge)
        return edge

    def get_neighbors(self, node_id: str, hops: int = 1) -> list[KGNode]:
        """Get neighbor nodes within N hops."""
        visited = set()
        current = {node_id}
        for _ in range(hops):
            next_level = set()
            for edge in self.edges:
                if edge.source_id in current and edge.target_id not in visited:
                    next_level.add(edge.target_id)
                if edge.target_id in current and edge.source_id not in visited:
                    next_level.add(edge.source_id)
            visited.update(current)
            current = next_level
        return [n for n in self.nodes if n.node_id in visited]

    def get_subgraph(self, node_ids: list[str], hops: int = 1) -> KnowledgeGraph:
        """Extract a subgraph around given node IDs."""
        neighbor_ids = set(node_ids)
        for nid in node_ids:
            for n in self.get_neighbors(nid, hops):
                neighbor_ids.add(n.node_id)
        nodes = [n for n in self.nodes if n.node_id in neighbor_ids]
        edges = [
            e
            for e in self.edges
            if e.source_id in neighbor_ids and e.target_id in neighbor_ids
        ]
        return KnowledgeGraph(nodes=nodes, edges=edges)


# ========== Retrieval Scope ==========


@dataclass
class RetrievalScope:
    """Scope-based QA selection (AGENT.md §5)."""

    project_id: str = ""
    selected_paper_ids: list[str] = field(default_factory=list)
    selected_topic_ids: list[str] = field(default_factory=list)
    selected_graph_node_ids: list[str] = field(default_factory=list)
    include_neighbors: bool = True
    graph_hops: int = 2
    time_range: list[int] | None = None  # [start_year, end_year]


# ========== Project ==========


@dataclass
class Project:
    """Research project owning a paper library."""

    project_id: str = field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    papers: list[Paper] = field(default_factory=list)
    paper_cards: list[PaperCard] = field(default_factory=list)
    evidence_table: list[EvidenceRecord] = field(default_factory=list)
    knowledge_graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ========== QA ==========


@dataclass
class QAQuestion:
    question: str = ""
    scope: RetrievalScope | None = None


@dataclass
class QAAnswer:
    answer: str = ""
    scope_description: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    uncertainty: str = ""
    next_actions: list[str] = field(default_factory=list)


# ========== Reports ==========


@dataclass
class LiteratureReview:
    """Formal artifact 1 (AGENT.md §1)."""

    title: str = ""
    research_background: str = ""
    topic_clusters: str = ""
    representative_papers: str = ""
    main_methods: str = ""
    main_findings: str = ""
    limitations: str = ""
    future_trends: str = ""
    references: str = ""
    full_text: str = ""


@dataclass
class InnovationPoint:
    """One innovation point (AGENT.md §2)."""

    name: str = ""
    description: str = ""
    why_innovative: str = ""
    existing_research: str = ""
    research_gap: str = ""
    supporting_papers: list[str] = field(default_factory=list)
    contradictory_evidence: str = ""
    feasibility: str = ""
    risk: str = ""
    possible_topic: str = ""


@dataclass
class InnovationReport:
    """Formal artifact 2 (AGENT.md §2)."""

    title: str = ""
    innovation_points: list[InnovationPoint] = field(default_factory=list)
    full_text: str = ""
