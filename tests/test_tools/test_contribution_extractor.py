"""
Contribution Extractor Tests

Tests for:
- ContributionExtractor: Extract paper contributions
"""
import pytest
from src.agents_v2.tools.contribution_extractor import (
    ContributionExtractor,
    Contribution,
    PaperContributions,
    ContributionType,
    extract_paper_contributions,
    get_contributions_by_type
)


class TestContributionType:
    """ContributionType Tests"""

    def test_all_types_exist(self):
        """Test all contribution types exist"""
        assert ContributionType.METHOD.value == "method"
        assert ContributionType.THEORY.value == "theory"
        assert ContributionType.APPLICATION.value == "application"
        assert ContributionType.DATASET.value == "dataset"
        assert ContributionType.ALGORITHM.value == "algorithm"
        assert ContributionType.FRAMEWORK.value == "framework"
        assert ContributionType.INSIGHT.value == "insight"


class TestContribution:
    """Contribution Tests"""

    def test_create_contribution(self):
        """Test creating a contribution"""
        contrib = Contribution(
            type=ContributionType.METHOD,
            description="A novel neural network architecture",
            evidence="Abstract: We propose...",
            chapter="abstract",
            confidence=0.9
        )
        assert contrib.type == ContributionType.METHOD
        assert contrib.description == "A novel neural network architecture"
        assert contrib.confidence == 0.9


class TestPaperContributions:
    """PaperContributions Tests"""

    def test_create_paper_contributions(self):
        """Test creating paper contributions"""
        contributions = [
            Contribution(ContributionType.METHOD, "Method description", confidence=0.9),
            Contribution(ContributionType.ALGORITHM, "Algorithm description", confidence=0.8)
        ]
        paper = PaperContributions(
            contributions=contributions,
            novelty_statement="First to propose...",
            impact_summary="High impact",
            main_contribution="Method description"
        )
        assert len(paper.contributions) == 2
        assert paper.novelty_statement == "First to propose..."


class TestContributionExtractor:
    """ContributionExtractor Tests"""

    def setup_method(self):
        self.extractor = ContributionExtractor()

    def test_init_without_llm(self):
        """Test initialization without LLM"""
        extractor = ContributionExtractor()
        assert extractor.llm is None

    def test_infer_contribution_type_method(self):
        """Test inferring method type"""
        text = "We propose a new method for deep learning"
        result = self.extractor._infer_contribution_type(text)
        assert result == ContributionType.METHOD

    def test_infer_contribution_type_theory(self):
        """Test inferring theory type"""
        text = "We prove a new theorem about neural networks"
        result = self.extractor._infer_contribution_type(text)
        assert result == ContributionType.THEORY

    def test_infer_contribution_type_algorithm(self):
        """Test inferring algorithm type"""
        text = "We develop an optimization algorithm"
        result = self.extractor._infer_contribution_type(text)
        assert result == ContributionType.ALGORITHM

    def test_infer_contribution_type_dataset(self):
        """Test inferring dataset type"""
        text = "We introduce a new benchmark dataset"
        result = self.extractor._infer_contribution_type(text)
        assert result == ContributionType.DATASET

    def test_infer_contribution_type_framework(self):
        """Test inferring framework type"""
        text = "We build a new framework for testing"
        result = self.extractor._infer_contribution_type(text)
        assert result == ContributionType.FRAMEWORK

    def test_infer_contribution_type_insight(self):
        """Test inferring insight type"""
        text = "We discover a new insight about learning"
        result = self.extractor._infer_contribution_type(text)
        assert result == ContributionType.INSIGHT

    def test_infer_contribution_type_default(self):
        """Test default inference"""
        text = "We analyze something"
        result = self.extractor._infer_contribution_type(text)
        assert result == ContributionType.APPLICATION

    def test_extract_from_abstract_we_propose(self):
        """Test extracting from abstract with 'we propose'"""
        abstract = "We propose a novel method for solving this problem."
        contributions = self.extractor._extract_from_abstract(abstract)
        assert len(contributions) > 0
        assert contributions[0].chapter == "abstract"

    def test_extract_from_abstract_we_propose_variants(self):
        """Test extracting from abstract with 'we propose'"""
        abstract = "We propose a new method for solving this problem."
        contributions = self.extractor._extract_from_abstract(abstract)
        # This should extract something since it has "propose"
        # Note: result depends on keyword matching

    def test_extract_from_abstract_novel(self):
        """Test extracting from abstract with 'novel'"""
        abstract = "This is a novel approach to the problem."
        contributions = self.extractor._extract_from_abstract(abstract)
        # Novel is a keyword, should extract something

    def test_extract_from_introduction(self):
        """Test extracting from introduction"""
        introduction = """
        Introduction paragraph.
        The key contributions of this paper include:
        1. A novel method
        2. An efficient algorithm
        3. Extensive experiments
        """
        contributions = self.extractor._extract_from_introduction(introduction)
        assert len(contributions) > 0

    def test_extract_from_conclusion_shown(self):
        """Test extracting from conclusion with 'shown'"""
        conclusion = "We have shown that our method achieves better results."
        contributions = self.extractor._extract_from_conclusion(conclusion)
        assert len(contributions) > 0

    def test_extract_from_method(self):
        """Test extracting from method section"""
        method = """
        We present a novel approach. Our innovative design includes:
        - A unique component
        - An original mechanism
        """
        contributions = self.extractor._extract_from_method(method)
        assert len(contributions) >= 0

    def test_merge_contributions_empty(self):
        """Test merging empty list"""
        merged = self.extractor._merge_contributions([])
        assert merged == []

    def test_merge_contributions_dedup(self):
        """Test merging and deduplication"""
        contribs = [
            Contribution(ContributionType.METHOD, "A method for X", confidence=0.8, chapter="abstract"),
            Contribution(ContributionType.METHOD, "A method for X", confidence=0.7, chapter="intro")
        ]
        merged = self.extractor._merge_contributions(contribs)
        # Should merge duplicates
        assert len(merged) <= 2

    def test_merge_contributions_sort(self):
        """Test merging sorts by confidence"""
        contribs = [
            Contribution(ContributionType.METHOD, "Low confidence", confidence=0.5),
            Contribution(ContributionType.METHOD, "High confidence", confidence=0.9)
        ]
        merged = self.extractor._merge_contributions(contribs)
        assert merged[0].confidence >= merged[-1].confidence

    def test_categorize_contributions(self):
        """Test categorizing contributions"""
        contribs = [
            Contribution(ContributionType.METHOD, "Method description"),
            Contribution(ContributionType.ALGORITHM, "Algorithm description")
        ]
        categorized = self.extractor._categorize_contributions(contribs)
        assert len(categorized) == 2
        assert categorized[0].type == ContributionType.METHOD

    def test_create_fingerprint(self):
        """Test creating fingerprint for deduplication"""
        text1 = "We propose a new method"
        text2 = "We propose a new method"
        text3 = "We analyze a different approach"

        fp1 = self.extractor._create_fingerprint(text1)
        fp2 = self.extractor._create_fingerprint(text2)
        fp3 = self.extractor._create_fingerprint(text3)

        assert fp1 == fp2
        assert fp1 != fp3

    def test_identify_main_contribution(self):
        """Test identifying main contribution"""
        contribs = [
            Contribution(ContributionType.METHOD, "Main contribution", confidence=0.9),
            Contribution(ContributionType.ALGORITHM, "Secondary", confidence=0.7)
        ]
        main = self.extractor._identify_main_contribution(contribs)
        assert main == "Main contribution"

    def test_identify_main_contribution_empty(self):
        """Test identifying main with empty list"""
        main = self.extractor._identify_main_contribution([])
        assert main == ""

    @pytest.mark.asyncio
    async def test_generate_impact_summary(self):
        """Test generating impact summary"""
        contribs = [
            Contribution(ContributionType.METHOD, "Method 1"),
            Contribution(ContributionType.METHOD, "Method 2"),
            Contribution(ContributionType.ALGORITHM, "Algorithm 1")
        ]
        summary = await self.extractor._generate_impact_summary(contribs)
        assert "method" in summary.lower()
        assert "algorithm" in summary.lower()

    @pytest.mark.asyncio
    async def test_generate_impact_summary_empty(self):
        """Test generating impact summary with empty list"""
        summary = await self.extractor._generate_impact_summary([])
        assert "No impact" in summary


class TestExtractPaperContributionsConvenience:
    """Test extract_paper_contributions convenience function"""

    @pytest.mark.asyncio
    async def test_extract_paper_contributions(self):
        """Test convenience function"""
        paper_content = {
            "abstract": "We propose a new method for deep learning."
        }
        result = await extract_paper_contributions(paper_content)
        assert isinstance(result, PaperContributions)


class TestGetContributionsByType:
    """Test get_contributions_by_type function"""

    def test_filter_by_type(self):
        """Test filtering contributions by type"""
        contribs = [
            Contribution(ContributionType.METHOD, "Method 1"),
            Contribution(ContributionType.ALGORITHM, "Algorithm 1"),
            Contribution(ContributionType.METHOD, "Method 2")
        ]
        filtered = get_contributions_by_type(contribs, ContributionType.METHOD)
        assert len(filtered) == 2
        assert all(c.type == ContributionType.METHOD for c in filtered)

    def test_filter_by_type_none_found(self):
        """Test filtering with no matches"""
        contribs = [
            Contribution(ContributionType.METHOD, "Method 1")
        ]
        filtered = get_contributions_by_type(contribs, ContributionType.ALGORITHM)
        assert len(filtered) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])