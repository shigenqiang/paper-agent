"""
Reference Parser 单元测试
"""
import pytest
from src.agents_v2.tools.reference_parser import (
    ReferenceParser,
    ReferenceSectionParser,
    ParsedReference,
    parse_reference
)


class TestReferenceParser:
    """ReferenceParser 测试"""

    def setup_method(self):
        self.parser = ReferenceParser()

    def test_parse_simple_reference(self):
        """测试简单参考文献"""
        raw = "Smith, J. and Johnson, A. Deep Learning Methods. Nature, 2020."
        ref = self.parser.parse(1, raw)

        assert ref.index == 1
        assert ref.year == "2020"
        # Title or journal should be extracted
        assert ref.title or ref.journal

    def test_parse_reference_with_doi(self):
        """测试带DOI的参考文献"""
        raw = "Brown, C. A novel approach. CVPR 2021. doi: 10.1109/CVPR.2021.00001"
        ref = self.parser.parse(1, raw)

        assert ref.index == 1
        assert ref.doi == "10.1109/CVPR.2021.00001"
        assert ref.year == "2021"

    def test_parse_reference_with_year_in_brackets(self):
        """测试带括号年份的参考文献"""
        raw = "Smith, J. (2019) New Method for X. Journal A, 5(2): 1-10."
        ref = self.parser.parse(1, raw)

        assert ref.index == 1
        assert ref.year == "2019"

    def test_parse_authors(self):
        """测试作者解析"""
        raw = "Smith, J. and Johnson, A. and Brown, B. The Title. Journal, 2020."
        ref = self.parser.parse(1, raw)

        assert len(ref.authors) >= 1


class TestReferenceSectionParser:
    """ReferenceSectionParser 测试"""

    def setup_method(self):
        self.parser = ReferenceSectionParser()

    def test_parse_section(self):
        """测试参考文献部分解析"""
        text = """
Some previous content.

References

[1] Smith, J. First Paper. Nature, 2020.
[2] Brown, C. Second Paper. Science, 2021.
[3] Johnson, A. Third Paper. Cell, 2022.
"""
        refs = self.parser.parse_section(text)

        assert len(refs) >= 2
        assert refs[0].index == 1
        assert refs[1].index == 2

    def test_parse_empty_section(self):
        """测试空参考文献部分"""
        text = "No references here."
        refs = self.parser.parse_section(text)
        assert len(refs) == 0


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_parse_reference_function(self):
        """测试便捷函数"""
        raw = "Smith, J. Title. Journal, 2020."
        ref = parse_reference(1, raw)
        assert ref.index == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])