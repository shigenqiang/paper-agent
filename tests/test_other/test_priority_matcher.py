"""
Priority Matcher 单元测试

测试优先级匹配器的功能
"""
import pytest
from src.agents_v2.retrieval.priority_matcher import (
    PriorityMatcher,
    create_priority_matcher
)


class TestPriorityMatcher:
    """PriorityMatcher 测试"""

    def setup_method(self):
        """设置测试"""
        self.groups = [
            ({"为什么", "why"}, "reasoning"),
            ({"对比", "compare"}, "comparison"),
            ({"什么是", "what is"}, "definition"),
            ({"谁", "who"}, "fact"),
        ]
        self.matcher = PriorityMatcher(self.groups)

    def test_matcher_init(self):
        """测试匹配器初始化"""
        assert self.matcher is not None
        assert len(self.matcher.keyword_groups) == 4

    def test_match_first_priority(self):
        """测试匹配第一个优先级"""
        # "为什么" 是第一个优先级的词
        result = self.matcher.match("为什么机器学习效果好")
        assert result == "reasoning"

    def test_match_second_priority(self):
        """测试匹配第二个优先级"""
        result = self.matcher.match("对比Python和Java")
        assert result == "comparison"

    def test_match_no_match(self):
        """测试无匹配"""
        result = self.matcher.match("这是一个无关的查询")
        assert result is None

    def test_match_is_case_insensitive(self):
        """测试大小写不敏感"""
        result = self.matcher.match("WHY为什么")
        assert result == "reasoning"

    def test_match_with_count(self):
        """测试带计数的匹配"""
        label, count = self.matcher.match_with_count("为什么为什么分析")
        assert label == "reasoning"
        assert count >= 1

    def test_match_confidence(self):
        """测试置信度计算"""
        # self.groups reasoning={"为什么", "why"}, count=1 -> 0.5
        conf = self.matcher.get_match_confidence("为什么", "reasoning")
        assert conf == 0.5

    def test_match_confidence_multiple(self):
        """测试多个关键词匹配的高置信度"""
        # 添加更多该组的词
        conf = self.matcher.get_match_confidence("为什么 why", "reasoning")
        assert conf == 1.0  # 2 matches -> 1.0

    def test_create_priority_matcher(self):
        """测试工厂函数"""
        matcher = create_priority_matcher(self.groups)
        assert matcher is not None
        assert len(matcher.keyword_groups) == 4

    def test_contains_any_true(self):
        """测试包含任意关键词 - 真"""
        result = self.matcher._contains_any("为什么", {"为什么", "怎么"})
        assert result is True

    def test_contains_any_false(self):
        """测试包含任意关键词 - 假"""
        result = self.matcher._contains_any("测试", {"为什么", "怎么"})
        assert result is False

    def test_count_matches(self):
        """测试计数匹配"""
        count = self.matcher._count_matches("为什么分析原因", {"为什么", "分析", "原因"})
        assert count == 3

    def test_count_matches_none(self):
        """测试计数匹配 - 无匹配"""
        count = self.matcher._count_matches("测试", {"为什么", "分析"})
        assert count == 0

    def test_empty_keyword_set(self):
        """测试空关键词集合"""
        groups = [({}, "empty")]
        matcher = PriorityMatcher(groups)
        result = matcher.match("任何文本")
        assert result is None


class TestPriorityMatcherEdgeCases:
    """边界情况测试"""

    def test_empty_text(self):
        """测试空文本"""
        groups = [({"为什么"}, "reasoning")]
        matcher = PriorityMatcher(groups)
        result = matcher.match("")
        assert result is None

    def test_single_char_keyword(self):
        """测试单字符关键词"""
        groups = [({"比"}, "comparison")]
        matcher = PriorityMatcher(groups)
        result = matcher.match("这个比那个好")
        assert result == "comparison"

    def test_overlapping_keywords(self):
        """测试重叠关键词（都被匹配）"""
        groups = [
            ({"什么是", "什么"}, "definition"),
            ({"什么"}, "fact"),
        ]
        matcher = PriorityMatcher(groups)
        # 应该返回第一个匹配的
        result = matcher.match("什么是AI")
        assert result == "definition"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])