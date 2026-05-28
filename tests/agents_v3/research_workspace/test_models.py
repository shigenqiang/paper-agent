"""数据模型测试"""

import pytest

from src.agents_v3.research_workspace.models import (
    EvidenceRecord,
    GraphEdge,
    GraphNode,
    InnovationPoint,
    KnowledgeGraph,
    NodeType,
    EdgeType,
    Paper,
    PaperCard,
    PaperChunk,
    PaperStatus,
    Project,
    QARequest,
    QAResponse,
    Report,
    ReportType,
    ReportVersion,
    RetrievalScope,
    ScopeType,
    SourceSpan,
)


class TestProject:
    def test_create_project(self):
        p = Project(project_id="p1", name="Test Project")
        assert p.project_id == "p1"
        assert p.name == "Test Project"
        assert p.description == ""

    def test_project_with_all_fields(self):
        p = Project(
            project_id="p1",
            name="Test",
            description="desc",
            discipline="CS",
            education_level="master",
            research_goal="goal",
        )
        assert p.discipline == "CS"
        assert p.education_level == "master"

    def test_project_metadata(self):
        p = Project(project_id="p1", name="Test", metadata={"key": "value"})
        assert p.metadata["key"] == "value"


class TestPaper:
    def test_create_paper(self):
        p = Paper(paper_id="p1", project_id="proj1")
        assert p.paper_id == "p1"
        assert p.status == PaperStatus.IMPORTED
        assert p.included is True

    def test_paper_status_enum(self):
        for status in PaperStatus:
            p = Paper(paper_id="p1", project_id="proj1", status=status)
            assert p.status == status

    def test_paper_with_authors(self):
        p = Paper(
            paper_id="p1",
            project_id="proj1",
            authors=["Alice", "Bob"],
            year=2024,
        )
        assert len(p.authors) == 2
        assert p.year == 2024


class TestPaperChunk:
    def test_create_chunk(self):
        c = PaperChunk(chunk_id="c1", paper_id="p1", text="hello")
        assert c.chunk_id == "c1"
        assert c.token_count == 0


class TestPaperCard:
    def test_create_card(self):
        card = PaperCard(card_id="c1", paper_id="p1", project_id="proj1")
        assert card.confidence == 0.0
        assert card.research_question == "unknown"

    def test_card_with_source_spans(self):
        span = SourceSpan(field="key_findings", chunk_id="ch1", quote="found X")
        card = PaperCard(
            card_id="c1",
            paper_id="p1",
            project_id="proj1",
            source_spans=[span],
        )
        assert len(card.source_spans) == 1
        assert card.source_spans[0].quote == "found X"


class TestEvidenceRecord:
    def test_create_evidence(self):
        e = EvidenceRecord(evidence_id="e1", project_id="proj1", paper_id="p1")
        assert e.evidence_strength == "medium"

    def test_evidence_with_details(self):
        e = EvidenceRecord(
            evidence_id="e1",
            project_id="proj1",
            paper_id="p1",
            topic="LLM feedback",
            finding="improved learning",
            source_chunk_id="ch1",
        )
        assert e.topic == "LLM feedback"


class TestGraphNode:
    def test_create_node(self):
        n = GraphNode(node_id="topic:llm", node_type=NodeType.TOPIC, label="LLM")
        assert n.node_type == NodeType.TOPIC

    def test_all_node_types(self):
        for nt in NodeType:
            n = GraphNode(node_id=f"{nt.value}:1", node_type=nt)
            assert n.node_type == nt


class TestGraphEdge:
    def test_create_edge(self):
        e = GraphEdge(
            edge_id="e1",
            source_id="paper:p1",
            target_id="topic:llm",
            edge_type=EdgeType.BELONGS_TO_TOPIC,
        )
        assert e.edge_type == EdgeType.BELONGS_TO_TOPIC


class TestKnowledgeGraph:
    def test_create_graph(self):
        g = KnowledgeGraph(project_id="proj1")
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_graph_with_nodes_and_edges(self):
        node = GraphNode(node_id="t1", node_type=NodeType.TOPIC, label="LLM")
        edge = GraphEdge(
            edge_id="e1",
            source_id="p1",
            target_id="t1",
            edge_type=EdgeType.BELONGS_TO_TOPIC,
        )
        g = KnowledgeGraph(project_id="proj1", nodes=[node], edges=[edge])
        assert len(g.nodes) == 1
        assert len(g.edges) == 1


class TestRetrievalScope:
    def test_create_scope(self):
        s = RetrievalScope(
            scope_type=ScopeType.ALL_PROJECT, project_id="proj1"
        )
        assert s.scope_type == ScopeType.ALL_PROJECT

    def test_scope_with_papers(self):
        s = RetrievalScope(
            scope_type=ScopeType.SELECTED_PAPERS,
            project_id="proj1",
            paper_ids=["p1", "p2"],
        )
        assert len(s.paper_ids) == 2


class TestQA:
    def test_qa_request(self):
        r = QARequest(question="What are the limitations?")
        assert r.question == "What are the limitations?"

    def test_qa_response(self):
        r = QAResponse(
            answer="The limitations are...",
            intent="limitation_analysis",
            scope_summary="Based on 3 papers",
        )
        assert r.intent == "limitation_analysis"


class TestReport:
    def test_create_report(self):
        r = Report(
            report_id="r1",
            project_id="proj1",
            type=ReportType.LITERATURE_REVIEW,
        )
        assert r.version == 1

    def test_innovation_point(self):
        ip = InnovationPoint(
            innovation_id="ip1",
            name="New approach",
            description="A novel method",
        )
        assert ip.name == "New approach"

    def test_report_version(self):
        rv = ReportVersion(
            version_id="v1",
            report_id="r1",
            content="updated content",
            reason="fix typos",
        )
        assert rv.report_id == "r1"
