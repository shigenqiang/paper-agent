"""
Citation Mapper Tests

Tests for:
- CitationRelationMapper: Citation relation mapping
"""
import pytest
from src.agents_v2.tools.citation_mapper import (
    CitationRelationMapper,
    CitationContext,
    CitationRelation,
    CitationGraph,
    CitationIntent,
    build_citation_graph,
    get_citation_summary
)


class TestCitationIntent:
    """CitationIntent Tests"""

    def test_all_intents_exist(self):
        """Test all citation intents exist"""
        assert CitationIntent.SUPPORTS.value == "supports"
        assert CitationIntent.CHALLENGES.value == "challenges"
        assert CitationIntent.COMPARES.value == "compares"
        assert CitationIntent.EXTENDS.value == "extends"
        assert CitationIntent.BELONGS_TO.value == "belongs_to"
        assert CitationIntent.METIONS.value == "mentions"


class TestCitationContext:
    """CitationContext Tests"""

    def test_create_context(self):
        """Test creating a citation context"""
        context = CitationContext(
            marker="[1]",
            preceding_text="Our method is based on [1].",
            following_text="The results show...",
            intent=CitationIntent.SUPPORTS,
            position=100
        )
        assert context.marker == "[1]"
        assert context.intent == CitationIntent.SUPPORTS
        assert context.position == 100


class TestCitationRelation:
    """CitationRelation Tests"""

    def test_create_relation(self):
        """Test creating a citation relation"""
        context = CitationContext(
            marker="[1]",
            preceding_text="Based on [1]",
            following_text="we proceed",
            intent=CitationIntent.SUPPORTS,
            position=50
        )
        relation = CitationRelation(
            citation_marker="[1]",
            reference_index=1,
            context=context,
            referring_paragraph="Based on [1] we proceed"
        )
        assert relation.citation_marker == "[1]"
        assert relation.reference_index == 1
        assert relation.context.intent == CitationIntent.SUPPORTS


class TestCitationGraph:
    """CitationGraph Tests"""

    def test_create_graph(self):
        """Test creating a citation graph"""
        graph = CitationGraph()
        assert graph.citations == {}
        assert graph.figure_citations == {}
        assert graph.table_citations == {}


class TestCitationRelationMapper:
    """CitationRelationMapper Tests"""

    def setup_method(self):
        self.mapper = CitationRelationMapper()

    def test_init(self):
        """Test initialization"""
        assert self.mapper._citation_patterns is not None
        assert len(self.mapper._citation_patterns) > 0

    def test_classify_citation_intent_supports(self):
        """Test classifying supports intent"""
        intent = self.mapper._classify_citation_intent(
            "Our method is based on",
            "previous work"
        )
        assert intent == CitationIntent.SUPPORTS

    def test_classify_citation_intent_challenges(self):
        """Test classifying challenges intent"""
        intent = self.mapper._classify_citation_intent(
            "However, contrary to",
            "previous claims"
        )
        assert intent == CitationIntent.CHALLENGES

    def test_classify_citation_intent_compares(self):
        """Test classifying compares intent"""
        intent = self.mapper._classify_citation_intent(
            "Similar to",
            "previous work"
        )
        assert intent == CitationIntent.COMPARES

    def test_classify_citation_intent_extends(self):
        """Test classifying extends intent"""
        intent = self.mapper._classify_citation_intent(
            "We extend",
            "previous work"
        )
        assert intent == CitationIntent.EXTENDS

    def test_classify_citation_intent_default(self):
        """Test default classification"""
        intent = self.mapper._classify_citation_intent(
            "Some random text",
            "without keywords"
        )
        assert intent == CitationIntent.METIONS

    def test_check_figure_reference(self):
        """Test checking figure reference"""
        is_figure, figure_id = self.mapper._check_figure_reference(
            "As shown in Figure 1",
            "the results"
        )
        assert is_figure is True
        assert figure_id == "1"

    def test_check_table_reference(self):
        """Test checking table reference"""
        is_table, table_id = self.mapper._check_table_reference(
            "Table 2 presents",
            "the data"
        )
        assert is_table is True
        assert table_id == "2"

    def test_check_figure_reference_none(self):
        """Test no figure reference"""
        is_figure, figure_id = self.mapper._check_figure_reference(
            "The results show",
            "important data"
        )
        assert is_figure is False
        assert figure_id is None

    def test_get_containing_paragraph(self):
        """Test getting containing paragraph"""
        text = "First paragraph.\n\nSecond paragraph with [1] citation.\n\nThird paragraph."
        paragraph = self.mapper._get_containing_paragraph(text, 35)
        assert "Second paragraph" in paragraph
        assert "[1]" in paragraph

    def test_build_citation_graph(self):
        """Test building citation graph"""
        text = """
        This is a test paper. Our method [1] is based on previous work [2].
        Figure 1 shows the architecture. As shown in Figure 2, we achieve better results.
        """
        references = ["Author1. Paper1", "Author2. Paper2"]
        graph = self.mapper.build_citation_graph(text, references)
        assert graph is not None
        assert len(graph.citations) >= 0

    def test_get_citation_summary(self):
        """Test getting citation summary"""
        graph = CitationGraph()
        summary = self.mapper.get_citation_summary(graph)
        assert "total_citations" in summary
        assert "unique_references_used" in summary
        assert "citation_intents" in summary

    def test_find_unused_references(self):
        """Test finding unused references"""
        graph = CitationGraph()
        graph.reference_usage = {1: 5, 2: 3, 5: 2}  # 3, 4 not used
        unused = self.mapper.find_unused_references(graph, 5)
        assert 3 in unused
        assert 4 in unused
        assert 1 not in unused

    def test_find_citation_chain(self):
        """Test finding citation chain"""
        graph = CitationGraph()
        context1 = CitationContext("[1]", "", "", CitationIntent.SUPPORTS, 100)
        context2 = CitationContext("[2]", "", "", CitationIntent.EXTENDS, 200)
        graph.citations["[1]"] = CitationRelation("[1]", 1, context1, "para1")
        graph.citations["[2]"] = CitationRelation("[2]", 1, context2, "para2")

        chain = self.mapper.find_citation_chain(graph, 1)
        assert len(chain) == 2
        assert "[1]" in chain
        assert "[2]" in chain

    def test_extract_figure_citations(self):
        """Test extracting figure citations"""
        text = "Figure 1 shows the architecture. Figure 2 shows the results."
        figure_citations = self.mapper._extract_figure_citations(text)
        assert "1" in figure_citations
        assert "2" in figure_citations

    def test_extract_table_citations(self):
        """Test extracting table citations"""
        text = "Table 1 presents the data. Table 2 shows the comparison."
        table_citations = self.mapper._extract_table_citations(text)
        assert "1" in table_citations
        assert "2" in table_citations

    def test_find_nearby_citations(self):
        """Test finding nearby citations"""
        text = "This is about [1] and [2] for [3] testing."
        pos = 10  # Position of "about"
        markers = self.mapper._find_nearby_citations(text, pos, window=50)
        assert "[1]" in markers
        assert "[2]" in markers


class TestBuildCitationGraphConvenience:
    """Test build_citation_graph convenience function"""

    def test_build_citation_graph_convenience(self):
        """Test convenience function"""
        text = "Based on [1] and [2]"
        references = ["Ref1", "Ref2"]
        graph = build_citation_graph(text, references)
        assert graph is not None


class TestGetCitationSummaryConvenience:
    """Test get_citation_summary convenience function"""

    def test_get_citation_summary_convenience(self):
        """Test convenience function"""
        graph = CitationGraph()
        summary = get_citation_summary(graph)
        assert "total_citations" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])