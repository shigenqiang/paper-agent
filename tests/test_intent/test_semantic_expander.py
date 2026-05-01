"""
语义关键词扩展器单元测试
"""
import pytest
from src.agents_v2.routing import (
    SemanticKeywordExpander,
    ExpansionResult,
    expand_keywords,
    expand_query,
)


class TestSemanticKeywordExpander:
    """SemanticKeywordExpander 测试"""

    def setup_method(self):
        self.expander = SemanticKeywordExpander()

    def test_expand_single_word(self):
        """测试单单词扩展"""
        result = self.expander.expand("论文")
        assert "论文" in result.expanded
        assert len(result.expanded) > 1

    def test_expand_synonyms(self):
        """测试同义词扩展"""
        result = self.expander.expand("搜索")
        assert "搜索" in result.expanded
        assert "查找" in result.expanded
        assert "检索" in result.expanded

    def test_expand_abbreviations(self):
        """测试缩写扩展"""
        result = self.expander.expand("NLP")
        assert "NLP" in result.expanded
        assert "Natural Language Processing" in result.expanded

    def test_expand_english(self):
        """测试英文扩展"""
        result = self.expander.expand("机器学习")
        assert "machine learning" in result.expanded
        assert "ML" in result.expanded

    def test_categories(self):
        """测试分类结果"""
        result = self.expander.expand("深度学习")
        assert "deep learning" in result.categories.get("english", [])

    def test_confidence(self):
        """测试置信度"""
        result = self.expander.expand("深度学习")
        assert result.confidence > 0

    def test_expand_query(self):
        """测试查询扩展"""
        terms = self.expander.expand_query("深度学习 机器学习")
        assert "深度学习" in terms
        assert "机器学习" in terms
        assert "deep learning" in terms

    def test_no_duplicates(self):
        """测试无重复"""
        result = self.expander.expand("论文")
        # 检查是否有重复
        assert len(result.expanded) == len(set(result.expanded))

    def test_empty_string(self):
        """测试空字符串"""
        result = self.expander.expand("")
        assert result.original == ""
        assert len(result.expanded) == 0


class TestExpansionResult:
    """ExpansionResult 测试"""

    def test_all_terms(self):
        """测试所有术语"""
        result = ExpansionResult(
            original="test",
            expanded=["test", "testing", "exam"]
        )
        assert len(result.all_terms) == 3

    def test_to_dict(self):
        """测试转换为字典"""
        result = ExpansionResult(
            original="test",
            expanded=["test"],
            categories={"synonyms": ["exam"]}
        )
        d = result.to_dict()
        assert d["original"] == "test"
        assert "synonyms" in d["categories"]


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_expand_keywords(self):
        """测试expand_keywords函数"""
        result = expand_keywords("论文")
        assert "论文" in result.expanded

    def test_expand_query(self):
        """测试expand_query函数"""
        terms = expand_query("深度学习")
        assert len(terms) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])