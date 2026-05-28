"""解析器章节识别和分块测试"""

import pytest

from src.agents_v3.research_workspace.parser_service import ParserService


@pytest.fixture
def parser(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.storage._storage", None
    )
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.parser_service.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return ParserService()


class TestSectionDetection:
    def test_detects_abstract(self, parser):
        assert parser._detect_section("Abstract") == "abstract"

    def test_detects_numbered_section(self, parser):
        assert parser._detect_section("1. Introduction") == "introduction"

    def test_detects_chinese_section(self, parser):
        assert parser._detect_section("摘要") == "abstract"

    def test_rejects_long_line(self, parser):
        assert parser._detect_section("This is a very long line that is definitely not a section header at all") is None

    def test_rejects_normal_text(self, parser):
        assert parser._detect_section("The results show that performance improved.") is None

    def test_detects_methods(self, parser):
        assert parser._detect_section("3. Methodology") == "method"

    def test_detects_references(self, parser):
        assert parser._detect_section("References") == "reference"

    def test_detects_discussion(self, parser):
        assert parser._detect_section("Discussion") == "discussion"

    def test_detects_conclusion(self, parser):
        assert parser._detect_section("Conclusions") == "conclusion"


class TestTokenEstimation:
    def test_english_text(self, parser):
        tokens = parser._estimate_tokens("Hello world this is a test")
        assert 2 <= tokens <= 10

    def test_chinese_text(self, parser):
        tokens = parser._estimate_tokens("这是一个测试文本")
        assert tokens >= 2

    def test_empty_text(self, parser):
        assert parser._estimate_tokens("") == 0


class TestChunkBySections:
    def test_basic_chunking(self, parser):
        pages = [(1, "Abstract\nThis is the abstract text.\n\nIntroduction\nSome intro text here.")]
        chunks = parser._chunk_by_sections(pages, "paper1")
        assert len(chunks) >= 1
        assert chunks[0]["paper_id"] == "paper1"
        assert "page_start" in chunks[0]
        assert "chunk_type" in chunks[0]
        assert "section_type" in chunks[0]

    def test_section_type_recorded(self, parser):
        long_text = "This is a detailed description of the research methodology used. " * 10
        pages = [(1, f"Methods\n{long_text}\n\nResults\nThe results were very positive and showed clear improvement. " * 5)]
        chunks = parser._chunk_by_sections(pages, "paper1")
        section_types = {c["section_type"] for c in chunks}
        assert "method" in section_types or "result" in section_types

    def test_references_get_reference_type(self, parser):
        body = "This is the main body text of the paper discussing important findings. " * 5
        ref = "[1] Smith et al. A comprehensive study of machine learning. Journal of AI, 2020. " * 3
        pages = [(1, f"{body}\n\nReferences\n{ref}")]
        chunks = parser._chunk_by_sections(pages, "paper1")
        ref_chunks = [c for c in chunks if c["chunk_type"] == "reference"]
        assert len(ref_chunks) >= 1

    def test_long_text_splits(self, parser):
        long_para = "This is a sentence about research. " * 200
        pages = [(1, f"Introduction\n{long_para}")]
        chunks = parser._chunk_by_sections(pages, "paper1")
        assert len(chunks) >= 2
        for c in chunks:
            assert c["token_count"] <= 1200

    def test_chunk_index_sequential(self, parser):
        pages = [(1, "Abstract\nShort abstract.\n\nIntroduction\nBody text here. " * 50)]
        chunks = parser._chunk_by_sections(pages, "paper1")
        for i, c in enumerate(chunks):
            assert c["chunk_index"] == i

    def test_short_text_discarded(self, parser):
        pages = [(1, "Introduction\nHi.\n\nResults\nOK.")]
        chunks = parser._chunk_by_sections(pages, "paper1")
        # Very short non-abstract text should be discarded
        for c in chunks:
            if c["section_type"] != "abstract":
                assert len(c["text"].strip()) >= 30 or c["section_type"] in ("title", "abstract")
