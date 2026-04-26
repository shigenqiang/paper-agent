"""
Keyword Sets 单元测试

测试关键词集合的完整性和正确性
"""
import pytest
from src.agents_v2.retrieval.keyword_sets import (
    REASONING_KEYWORDS,
    COMPARISON_KEYWORDS,
    DEFINITION_KEYWORDS,
    FACT_KEYWORDS,
    EXPLORATION_KEYWORDS,
    KEYWORD_GROUPS,
    get_all_keywords,
    validate_keyword_sets
)


class TestKeywordSets:
    """关键词集合测试"""

    def test_all_keyword_sets_nonempty(self):
        """测试所有关键词集合非空"""
        assert len(REASONING_KEYWORDS) > 0
        assert len(COMPARISON_KEYWORDS) > 0
        assert len(DEFINITION_KEYWORDS) > 0
        assert len(FACT_KEYWORDS) > 0
        assert len(EXPLORATION_KEYWORDS) > 0

    def test_keyword_sets_are_lowercase(self):
        """测试英文关键词都是小写"""
        for keywords in [REASONING_KEYWORDS, COMPARISON_KEYWORDS,
                        DEFINITION_KEYWORDS, FACT_KEYWORDS, EXPLORATION_KEYWORDS]:
            for kw in keywords:
                if kw.isalpha():
                    assert kw == kw.lower(), f"Keyword {kw} not lowercase"

    def test_keyword_sets_no_duplicates(self):
        """测试关键词集合内无重复"""
        for keywords, name in KEYWORD_GROUPS:
            assert len(keywords) == len(set(keywords)), f"Duplicate in {name}"

    def test_keyword_groups_structure(self):
        """测试KEYWORD_GROUPS结构"""
        assert len(KEYWORD_GROUPS) == 5
        for keywords, label in KEYWORD_GROUPS:
            assert isinstance(keywords, set)
            assert isinstance(label, str)
            assert label in ["reasoning", "comparison", "definition", "fact", "exploration"]

    def test_priority_order(self):
        """测试优先级顺序"""
        labels = [label for _, label in KEYWORD_GROUPS]
        expected = ["reasoning", "comparison", "definition", "fact", "exploration"]
        assert labels == expected

    def test_get_all_keywords(self):
        """测试获取所有关键词"""
        all_kw = get_all_keywords()
        total = sum(len(kw) for kw, _ in KEYWORD_GROUPS)
        assert len(all_kw) == total

    def test_validate_keyword_sets_valid(self):
        """测试验证通过"""
        assert validate_keyword_sets() is True

    def test_reasoning_keywords_content(self):
        """测试推理关键词内容"""
        # 应该包含中英文常见推理词
        assert "为什么" in REASONING_KEYWORDS
        assert "why" in REASONING_KEYWORDS
        assert "分析" in REASONING_KEYWORDS
        assert "analyze" in REASONING_KEYWORDS

    def test_comparison_keywords_content(self):
        """测试比较关键词内容"""
        assert "对比" in COMPARISON_KEYWORDS
        assert "比较" in COMPARISON_KEYWORDS
        assert "vs" in COMPARISON_KEYWORDS
        assert "compare" in COMPARISON_KEYWORDS

    def test_definition_keywords_content(self):
        """测试定义关键词内容"""
        assert "什么是" in DEFINITION_KEYWORDS
        assert "definition" in DEFINITION_KEYWORDS
        assert "what is" in DEFINITION_KEYWORDS

    def test_fact_keywords_content(self):
        """测试事实查找关键词内容"""
        assert "谁" in FACT_KEYWORDS
        assert "哪一年" in FACT_KEYWORDS
        assert "who" in FACT_KEYWORDS
        assert "when" in FACT_KEYWORDS

    def test_exploration_keywords_content(self):
        """测试探索关键词内容"""
        assert "探索" in EXPLORATION_KEYWORDS
        assert "最新" in EXPLORATION_KEYWORDS
        assert "explore" in EXPLORATION_KEYWORDS
        assert "recent" in EXPLORATION_KEYWORDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])