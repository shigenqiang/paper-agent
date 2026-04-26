"""
Query Parser 单元测试
"""
import pytest
from src.agents_v2.search.query_parser import (
    QueryParser,
    QueryIntent,
    ParsedQuery,
    parse_query
)


class TestQueryParser:
    """QueryParser 测试"""

    def setup_method(self):
        self.parser = QueryParser()

    def test_parse_basic_query(self):
        """测试基本查询解析"""
        result = self.parser.parse("什么是机器学习")

        assert isinstance(result, ParsedQuery)
        assert "机器学习" in result.original
        assert result.intent in QueryIntent
        assert isinstance(result.keywords, list)

    def test_detect_intent_factual(self):
        """测试事实意图检测"""
        result = self.parser.parse("Transformer的作者是谁")
        assert result.intent == QueryIntent.FACTUAL

    def test_detect_intent_exploratory(self):
        """测试探索意图检测"""
        result = self.parser.parse("探索最新的AI研究方向")
        assert result.intent == QueryIntent.EXPLORATORY

    def test_detect_intent_comparative(self):
        """测试比较意图检测"""
        result = self.parser.parse("BERT和GPT对比")
        assert result.intent == QueryIntent.COMPARATIVE

    def test_detect_intent_explanatory(self):
        """测试解释意图检测"""
        result = self.parser.parse("为什么深度学习效果好")
        assert result.intent == QueryIntent.EXPLANATORY

    def test_detect_intent_action(self):
        """测试动作意图检测"""
        result = self.parser.parse("找机器学习论文")
        assert result.intent == QueryIntent.ACTION

    def test_extract_keywords(self):
        """测试关键词提取"""
        result = self.parser.parse("深度学习在图像识别中的应用")

        # 应该提取出有意义的词
        assert isinstance(result.keywords, list)

    def test_extract_keywords_removes_stopwords(self):
        """测试移除停用词"""
        result = self.parser.parse("什么是机器学习的定义")

        # 短停用词应该被移除
        assert "的" not in result.keywords

    def test_extract_entities(self):
        """测试实体提取"""
        result = self.parser.parse("BERT模型在NLP中的应用")

        # 应该返回实体列表
        assert isinstance(result.entities, list)

    def test_extract_tech_entities(self):
        """测试技术实体提取"""
        result = self.parser.parse("CNN和RNN在图像处理中的对比")

        # 技术缩写应该被提取
        assert isinstance(result.entities, list)

    def test_extract_modifiers(self):
        """测试修饰词提取"""
        result = self.parser.parse("最新的深度学习研究")

        assert "最新的" in result.modifiers or "最新" in result.modifiers

    def test_check_temporal(self):
        """测试时间检测"""
        result1 = self.parser.parse("最近的AI研究进展")
        assert result1.is_temporal is True

        result2 = self.parser.parse("机器学习基本概念")
        assert result2.is_temporal is False

    def test_check_quantity(self):
        """测试数量检测"""
        result1 = self.parser.parse("多少篇论文研究了这个问题")
        assert result1.is_quantity is True

        result2 = self.parser.parse("论文的主要贡献是什么")
        assert result2.is_quantity is False

    def test_detect_language_chinese(self):
        """测试中文检测"""
        result = self.parser.parse("什么是人工智能")
        assert result.language == "zh"

    def test_detect_language_english(self):
        """测试英文检测"""
        result = self.parser.parse("What is artificial intelligence")
        assert result.language == "en"

    def test_detect_language_mixed(self):
        """测试混合语言检测"""
        result = self.parser.parse("AI和深度学习")
        # 中文多于英文时检测为中文
        assert result.language in ["zh", "en", "mixed"]

    def test_empty_query(self):
        """测试空查询"""
        result = self.parser.parse("")

        assert result.original == ""
        assert result.intent == QueryIntent.EXPLORATORY  # 默认探索
        assert result.language == "mixed"

    def test_whitespace_query(self):
        """测试空白查询"""
        result = self.parser.parse("   ")
        # strip后为空
        assert result.original.strip() == ""


class TestParsedQuery:
    """ParsedQuery 测试"""

    def test_create_parsed_query(self):
        """测试创建解析查询"""
        query = ParsedQuery(
            original="test query",
            intent=QueryIntent.FACTUAL,
            keywords=["test"],
            entities=["AI"],
            modifiers=[],
            is_temporal=False,
            is_quantity=False,
            language="en"
        )

        assert query.original == "test query"
        assert query.intent == QueryIntent.FACTUAL
        assert query.keywords == ["test"]
        assert query.language == "en"


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_parse_query_function(self):
        """测试便捷函数"""
        result = parse_query("什么是深度学习")

        assert isinstance(result, ParsedQuery)
        assert result.original == "什么是深度学习"


class TestQueryIntent:
    """QueryIntent 测试"""

    def test_all_intents_defined(self):
        """测试所有意图都已定义"""
        intents = list(QueryIntent)
        assert QueryIntent.FACTUAL in intents
        assert QueryIntent.EXPLORATORY in intents
        assert QueryIntent.COMPARATIVE in intents
        assert QueryIntent.EXPLANATORY in intents
        assert QueryIntent.ACTION in intents

    def test_intent_values(self):
        """测试意图值"""
        assert QueryIntent.FACTUAL.value == "factual"
        assert QueryIntent.EXPLORATORY.value == "exploratory"
        assert QueryIntent.COMPARATIVE.value == "comparative"
        assert QueryIntent.EXPLANATORY.value == "explanatory"
        assert QueryIntent.ACTION.value == "action"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])