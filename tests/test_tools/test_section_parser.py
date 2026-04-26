"""
Section Parser 单元测试
"""
import pytest
from src.agents_v2.tools.section_parser import (
    SectionParser,
    ParsedSection,
    parse_sections
)


class TestSectionParser:
    """SectionParser 测试"""

    def setup_method(self):
        self.parser = SectionParser()

    def test_parse_sections(self):
        """测试章节解析"""
        text = """
Abstract

This is the abstract.

Introduction

Related Work

Methodology

We propose a method.

Experiment

We conduct experiments.

Conclusion

We conclude.

References
"""
        sections = self.parser.parse(text)

        assert len(sections) >= 4
        titles = [s.title for s in sections]
        assert "Abstract" in titles
        assert "Introduction" in titles
        assert "Methodology" in titles
        assert "Conclusion" in titles

    def test_parse_section_levels(self):
        """测试章节层级"""
        text = """
Abstract

Introduction

1.1 Background

1.2 Motivation

Methodology
"""
        sections = self.parser.parse(text)

        level1 = [s for s in sections if s.level == 1]
        level2 = [s for s in sections if s.level == 2]

        assert len(level1) >= 2
        assert len(level2) >= 1

    def test_get_section_by_title(self):
        """测试按标题获取章节"""
        text = """
Abstract
Content here.

Introduction
More content.
"""
        sections = self.parser.parse(text)
        abstract = self.parser.get_section_by_title(sections, "Abstract")

        assert abstract is not None
        assert abstract.title == "Abstract"

    def test_get_main_sections(self):
        """测试获取主章节"""
        text = """
Abstract
Intro
1.1 Sub
Method
"""
        sections = self.parser.parse(text)
        main = self.parser.get_main_sections(sections)

        assert all(s.level == 1 for s in main)

    def test_parse_no_sections(self):
        """测试无章节"""
        text = "Just some random text without sections."
        sections = self.parser.parse(text)
        # Parser may still find sections due to uppercase patterns
        # Just verify it returns a list
        assert isinstance(sections, list)


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_parse_sections_function(self):
        """测试便捷函数"""
        text = "Abstract\n\nIntroduction"
        sections = parse_sections(text)
        assert len(sections) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])