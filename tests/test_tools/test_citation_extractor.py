"""
Citation Extractor 单元测试
"""
import pytest
from src.agents_v2.tools.citation_extractor import (
    CitationExtractor,
    extract_citations
)


class TestCitationExtractor:
    """CitationExtractor 测试"""

    def setup_method(self):
        self.extractor = CitationExtractor()

    def test_extract_single_citation(self):
        """测试单个引用"""
        text = "As shown in [1], our method works."
        result = self.extractor.extract(text)
        assert "1" in result

    def test_extract_multiple_citations(self):
        """测试多个逗号分隔的引用"""
        text = "See [1,2,3] for details."
        result = self.extractor.extract(text)
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_extract_range_citation(self):
        """测试范围引用"""
        text = "See papers [1-5] for background."
        result = self.extractor.extract(text)
        assert "1" in result
        assert "2" in result
        assert "3" in result
        assert "4" in result
        assert "5" in result

    def test_extract_mixed_citations(self):
        """测试混合引用"""
        text = "As shown in [1] and [2,3] and [4-6],"
        result = self.extractor.extract(text)
        assert len(result) >= 6

    def test_extract_no_citations(self):
        """测试无引用"""
        text = "This paper has no citations."
        result = self.extractor.extract(text)
        assert len(result) == 0

    def test_extract_duplicates_removed(self):
        """测试去重"""
        text = "[1] and [1] again"
        result = self.extractor.extract(text)
        assert result.count("1") == 1

    def test_expand_single(self):
        """测试单引用展开"""
        result = self.extractor._expand_citation("1")
        assert result == ["1"]

    def test_expand_range(self):
        """测试范围展开"""
        result = self.extractor._expand_citation("1-3")
        assert result == ["1", "2", "3"]

    def test_expand_mixed(self):
        """测试混合展开"""
        result = self.extractor._expand_citation("1,3-5")
        assert result == ["1", "3", "4", "5"]


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_extract_citations_function(self):
        """测试便捷函数"""
        text = "See [1,2] for details."
        result = extract_citations(text)
        assert "1" in result
        assert "2" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])