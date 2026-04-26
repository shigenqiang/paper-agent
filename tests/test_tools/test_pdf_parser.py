"""
PDF解析器测试
"""
import pytest
from src.agents_v2.tools.pdf_parser import (
    PDFParser,
    PDFMetadata,
    PDFSection,
    PDFReference,
    PDFParseResult
)


class TestPDFParser:
    """PDF解析器测试"""

    def test_parser_init(self):
        """测试解析器初始化"""
        parser = PDFParser()
        assert parser is not None
        assert parser.text == ""

    def test_extract_citations(self):
        """测试引用提取"""
        parser = PDFParser()

        text = "As shown in [1] and [2], our method outperforms [3,4] and [5-7]."
        citations = parser.extract_citations(text)

        assert "1" in citations
        assert "2" in citations
        assert "3" in citations
        assert "4" in citations
        assert "5" in citations
        assert "6" in citations
        assert "7" in citations

    def test_parse_reference(self):
        """测试参考文献解析"""
        parser = PDFParser()

        raw_text = "Smith, J. and Johnson, A. Deep Learning Methods. Nature, 2020."
        ref = parser._parse_reference(1, raw_text)

        assert ref.index == 1
        assert ref.title == "Deep Learning Methods"
        assert ref.year == "2020"

    def test_parse_reference_with_doi(self):
        """测试带DOI的参考文献解析"""
        parser = PDFParser()

        raw_text = "[1] Brown, C. A novel approach. CVPR 2021. doi: 10.1109/CVPR.2021.00001"
        ref = parser._parse_reference(1, raw_text)

        assert ref.index == 1
        assert ref.doi == "10.1109/CVPR.2021.00001"
        assert ref.year == "2021"

    def test_extract_sections(self):
        """测试章节提取"""
        parser = PDFParser()

        text = """
Abstract

This paper presents a new method.

Introduction

Related Work

Methodology

We propose an approach.

Experiment

Results show improvement.

Conclusion

We conclude that.

References
"""
        sections = parser._extract_sections(text)

        assert len(sections) > 0
        titles = [s.title for s in sections]
        assert "Abstract" in titles
        assert "Introduction" in titles
        assert "Methodology" in titles

    def test_metadata_class(self):
        """测试元数据类"""
        metadata = PDFMetadata()
        metadata.title = "Test Paper"
        metadata.authors = ["John Doe", "Jane Smith"]
        metadata.abstract = "This is an abstract."
        metadata.keywords = ["AI", "ML"]
        metadata.doi = "10.1234/test"

        assert metadata.title == "Test Paper"
        assert len(metadata.authors) == 2
        assert metadata.doi == "10.1234/test"

    def test_pdf_section_class(self):
        """测试章节类"""
        section = PDFSection(
            title="Introduction",
            level=1,
            start_page=0,
            end_page=5,
            content="Introduction content"
        )

        assert section.title == "Introduction"
        assert section.level == 1
        assert section.content == "Introduction content"

    def test_pdf_reference_class(self):
        """测试参考文献类"""
        ref = PDFReference(
            index=1,
            authors=["Smith J."],
            title="A Study",
            year="2021",
            doi="10.1234/test"
        )

        assert ref.index == 1
        assert ref.year == "2021"

    def test_parse_result_class(self):
        """测试解析结果类"""
        result = PDFParseResult(
            success=True,
            num_pages=10,
            full_text="Extracted text..."
        )

        assert result.success is True
        assert result.num_pages == 10
        assert "Extracted text" in result.full_text

    def test_parse_nonexistent_file(self):
        """测试解析不存在的文件"""
        import asyncio

        async def run_test():
            parser = PDFParser()
            result = await parser.parse_file("/nonexistent/file.pdf")
            assert result.success is False
            assert "not found" in result.error.lower()

        asyncio.run(run_test())

    def test_citation_expansion(self):
        """测试引用范围扩展"""
        parser = PDFParser()

        text = "See papers [1-3] for details."
        citations = parser.extract_citations(text)

        assert "1" in citations
        assert "2" in citations
        assert "3" in citations
