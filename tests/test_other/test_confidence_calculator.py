"""
Confidence Calculator 单元测试

测试置信度计算器的功能
"""
import pytest
from src.agents_v2.retrieval.confidence_calculator import (
    ConfidenceCalculator,
    calculate_confidence
)


# 测试用的关键词组
TEST_KEYWORD_GROUPS = [
    ({"为什么", "分析"}, "reasoning"),
    ({"对比", "比较"}, "comparison"),
    ({"什么是", "定义"}, "definition"),
    ({"谁", "哪一年"}, "fact"),
    ({"探索", "研究"}, "exploration"),
]


class TestConfidenceCalculator:
    """ConfidenceCalculator 测试"""

    def setup_method(self):
        """设置测试"""
        self.calculator = ConfidenceCalculator(TEST_KEYWORD_GROUPS)

    def test_calculator_init(self):
        """测试计算器初始化"""
        assert self.calculator is not None
        assert len(self.calculator.keyword_groups) == 5

    def test_high_confidence_single_keyword(self):
        """测试单个关键词的高置信度"""
        confidence = self.calculator.calculate("什么是AI", "definition")
        assert 0 < confidence <= 1.0

    def test_high_confidence_multiple_keywords(self):
        """测试多个关键词的高置信度"""
        confidence = self.calculator.calculate("为什么分析原因", "reasoning")
        assert confidence > 0.5

    def test_no_keyword_match_long_query(self):
        """测试无匹配但长查询（>20字符）"""
        # LONG_QUERY_THRESHOLD = 20, needs > 20 chars
        long_text = "这是一个非常长的无关查询句子用于测试探索功能"  # 22 chars
        assert len(long_text) > 20
        confidence = self.calculator.calculate(long_text, None)
        assert confidence == 0.6  # Heuristic for exploration

    def test_no_keyword_match_short_query(self):
        """测试无匹配但短查询"""
        confidence = self.calculator.calculate("无关", None)
        assert confidence == 0.5  # Default

    def test_heuristic_exploration_confidence(self):
        """测试探索启发式置信度"""
        # 长查询 -> 探索
        confidence = self.calculator.calculate(
            "这是一个非常长的查询句子用来测试启发式规则是否正常工作",
            "exploration"
        )
        assert confidence == 0.6

    def test_heuristic_fact_confidence(self):
        """测试事实查找启发式置信度"""
        # 短查询 -> 事实
        confidence = self.calculator.calculate("AI是什么", "fact")
        assert confidence == 0.6

    def test_count_matches_for_label(self):
        """测试特定标签的计数"""
        count = self.calculator._count_matches_for_label("为什么分析", "reasoning")
        assert count == 2

    def test_count_matches_no_match(self):
        """测试无匹配时计数为0"""
        count = self.calculator._count_matches_for_label("无关", "reasoning")
        assert count == 0

    def test_calculate_convenience_function(self):
        """测试便捷函数"""
        confidence = calculate_confidence("什么是AI", "definition", TEST_KEYWORD_GROUPS)
        assert 0 < confidence <= 1.0


class TestConfidenceCalculatorEdgeCases:
    """边界情况测试"""

    def test_empty_query(self):
        """测试空查询"""
        calculator = ConfidenceCalculator(TEST_KEYWORD_GROUPS)
        # Empty string classified as fact (not > 20) -> 0.6 heuristic
        confidence = calculator.calculate("", "fact")
        assert confidence == 0.6

    def test_unknown_label(self):
        """测试未知标签"""
        calculator = ConfidenceCalculator(TEST_KEYWORD_GROUPS)
        confidence = calculator.calculate("测试", "unknown")
        assert confidence == 0.5

    def test_none_label_with_long_query(self):
        """测试长查询无标签"""
        calculator = ConfidenceCalculator(TEST_KEYWORD_GROUPS)
        long_query = "A" * 30  # 超过20字符
        confidence = calculator.calculate(long_query, None)
        assert confidence == 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])