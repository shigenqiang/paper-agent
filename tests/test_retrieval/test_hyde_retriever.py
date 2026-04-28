"""
HyDE Retriever Tests

Tests for:
- HypotheticalDocumentGenerator: Generate hypothetical documents
- HyDERetriever: HyDE-based retrieval
- MultiFacetHyDE: Multi-facet HyDE retrieval
"""
import pytest
from src.agents_v2.retrieval.hyde_retriever import (
    HypotheticalDocumentGenerator,
    HypotheticalDocument,
    HyDERetriever,
    MultiFacetHyDE,
    hyde_search
)


class TestHypotheticalDocument:
    """HypotheticalDocument Tests"""

    def test_create_document(self):
        """Test creating a hypothetical document"""
        doc = HypotheticalDocument(
            content="This is a hypothetical answer about deep learning.",
            query="What is deep learning?",
            confidence=0.7,
            generation_method="test",
            facets=["method", "application"]
        )
        assert doc.content == "This is a hypothetical answer about deep learning."
        assert doc.query == "What is deep learning?"
        assert doc.confidence == 0.7
        assert doc.generation_method == "test"
        assert "method" in doc.facets


class TestHypotheticalDocumentGenerator:
    """HypotheticalDocumentGenerator Tests"""

    def setup_method(self):
        self.generator = HypotheticalDocumentGenerator()

    def test_init_without_llm(self):
        """Test initialization without LLM"""
        gen = HypotheticalDocumentGenerator()
        assert gen.llm is None

    def test_init_with_llm(self):
        """Test initialization with LLM"""
        class MockLLM:
            pass
        mock_llm = MockLLM()
        gen = HypotheticalDocumentGenerator(llm=mock_llm)
        assert gen.llm is mock_llm

    def test_generate_simple(self):
        """Test simple generation without LLM"""
        doc = self.generator._generate_simple("What is machine learning?")
        assert doc.content != ""
        assert doc.query == "What is machine learning?"
        assert doc.confidence == 0.3
        assert doc.generation_method == "simple"

    def test_extract_facets_method(self):
        """Test extracting method facets"""
        content = "We propose a new method for deep learning using neural networks."
        facets = self.generator._extract_facets(content)
        assert "method" in facets

    def test_extract_facets_dataset(self):
        """Test extracting dataset facets"""
        content = "We evaluate on the ImageNet dataset and CIFAR-10 dataset."
        facets = self.generator._extract_facets(content)
        assert "dataset" in facets

    def test_extract_facets_result(self):
        """Test extracting result facets"""
        content = "Our method achieves 95% accuracy on the test set."
        facets = self.generator._extract_facets(content)
        assert "result" in facets

    def test_extract_facets_general(self):
        """Test general facets when no keywords found"""
        content = "This paper discusses various topics."
        facets = self.generator._extract_facets(content)
        assert "general" in facets


class TestHyDERetriever:
    """HyDERetriever Tests"""

    def setup_method(self):
        # Create a mock base retriever
        class MockRetriever:
            async def retrieve(self, query, top_k):
                # Return mock documents
                class MockDoc:
                    def __init__(self, content, doc_id):
                        self.content = content
                        self.doc_id = doc_id
                return [MockDoc(f"Document about {query}", i) for i in range(top_k)]
        self.mock_retriever = MockRetriever()
        self.retriever = HyDERetriever(
            base_retriever=self.mock_retriever,
            embedder=None,
            llm=None
        )

    def test_init(self):
        """Test initialization"""
        assert self.retriever.base_retriever is not None
        assert self.retriever.embedder is None
        assert self.retriever.generator is not None

    def test_get_doc_id_with_doc_id(self):
        """Test getting doc ID when doc has doc_id attribute"""
        class MockDoc:
            doc_id = "test_doc_123"
        doc = MockDoc()
        doc_id = self.retriever._get_doc_id(doc, 0)
        assert doc_id == "test_doc_123"

    def test_get_doc_id_with_id(self):
        """Test getting doc ID when doc has id attribute"""
        class MockDoc:
            id = "test_id_456"
        doc = MockDoc()
        doc_id = self.retriever._get_doc_id(doc, 0)
        assert doc_id == "test_id_456"

    def test_get_doc_id_fallback(self):
        """Test getting doc ID with fallback"""
        class MockDoc:
            pass
        doc = MockDoc()
        doc_id = self.retriever._get_doc_id(doc, 5)
        assert doc_id == "doc_5"

    def test_fuse_results_empty(self):
        """Test fusing empty results"""
        fused = self.retriever._fuse_results([], [], [], 10)
        assert fused == []

    def test_fuse_results_original_only(self):
        """Test fusing with original results only"""
        class MockDoc:
            def __init__(self, content, doc_id):
                self.content = content
                self.doc_id = doc_id

        original_results = [
            MockDoc("Doc 1", "doc_1"),
            MockDoc("Doc 2", "doc_2")
        ]
        fused = self.retriever._fuse_results(original_results, [], [0.5, 0.6], 10)
        assert len(fused) == 2


class TestMultiFacetHyDE:
    """MultiFacetHyDE Tests"""

    def setup_method(self):
        class MockRetriever:
            async def retrieve(self, query, top_k):
                class MockDoc:
                    def __init__(self, content, doc_id):
                        self.content = content
                        self.doc_id = doc_id
                return [MockDoc(f"Doc about {query}", i) for i in range(min(top_k, 5))]
        mock_base = MockRetriever()
        self.hyde = HyDERetriever(mock_base, None, None)
        self.multi_facet = MultiFacetHyDE(self.hyde)

    def test_init(self):
        """Test initialization"""
        assert self.multi_facet.hyde_retriever is not None


class TestHydeSearchConvenience:
    """Test hyde_search convenience function"""

    @pytest.mark.asyncio
    async def test_hyde_search(self):
        """Test convenience function"""
        class MockRetriever:
            async def retrieve(self, query, top_k):
                return []
        result = await hyde_search(
            query="test query",
            retriever=MockRetriever(),
            embedder=None,
            llm=None
        )
        # Should return a list (empty or mocked)
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])