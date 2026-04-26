"""
Score Parser 单元测试

测试LLM分数解析功能
"""
import pytest
from src.agents_v2.retrieval.score_parser import (
    ScoreParser,
    parse_llm_score,
    parse_llm_boolean
)


class TestScoreParser:
    """ScoreParser 测试"""

    def test_parse_decimal(self):
        """测试解析小数"""
        assert ScoreParser.parse_score("0.8") == 0.8
        assert ScoreParser.parse_score("0.5") == 0.5
        assert ScoreParser.parse_score(".7") == 0.7

    def test_parse_integer_out_of_10(self):
        """测试解析整数（超过1的）"""
        assert ScoreParser.parse_score("8") == 0.8
        assert ScoreParser.parse_score("9") == 0.9

    def test_parse_integer_0_or_1(self):
        """测试解析0或1"""
        assert ScoreParser.parse_score("0") == 0.0
        assert ScoreParser.parse_score("1") == 1.0

    def test_parse_with_text(self):
        """测试从文本中提取分数"""
        assert ScoreParser.parse_score("Score: 0.75") == 0.75
        assert ScoreParser.parse_score("The score is 0.6 out of 1") == 0.6

    def test_parse_default(self):
        """测试解析失败时返回默认值"""
        assert ScoreParser.parse_score("no number here") == 0.5
        assert ScoreParser.parse_score("invalid") == 0.5
        assert ScoreParser.parse_score("no number", default=0.8) == 0.8

    def test_parse_number_greater_than_1(self):
        """测试大于1的数字被除以10"""
        assert ScoreParser.parse_score("8") == 0.8
        assert ScoreParser.parse_score("15") == 1.0  # 15/10=1.5 clamped to 1.0

    def test_parse_no_negative_handling(self):
        """测试负数无法解析"""
        # "-0.5" parses as 0.5 (ignores minus), but then gets clamped
        assert ScoreParser.parse_score("-0.5") == 0.5

    def test_parse_boolean_yes(self):
        """测试解析是/否 - 是"""
        assert ScoreParser.parse_boolean("是") is True
        assert ScoreParser.parse_boolean("是，需要检索") is True
        assert ScoreParser.parse_boolean("需要") is True

    def test_parse_boolean_no(self):
        """测试解析是/否 - 否"""
        assert ScoreParser.parse_boolean("否") is False
        assert ScoreParser.parse_boolean("否，不需要") is False

    def test_parse_boolean_both(self):
        """测试同时包含是/否"""
        assert ScoreParser.parse_boolean("是，但否") is True


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_parse_llm_score(self):
        """测试便捷分数解析"""
        assert parse_llm_score("0.8") == 0.8

    def test_parse_llm_boolean(self):
        """测试便捷布尔解析"""
        assert parse_llm_boolean("是") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])